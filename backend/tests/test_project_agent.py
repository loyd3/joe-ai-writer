"""Durable, approval-only project agent regression tests (no external model)."""
import asyncio
import json
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.models import User, Project, Document, AIMemory


@pytest.fixture
def store():
    engine = create_engine('sqlite://', poolclass=StaticPool,
                           connect_args={'check_same_thread': False})
    from app.models.project_agent import AgentRun  # intended RED: missing implementation
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([User(id=1, username='owner', is_active=True),
                    User(id=2, username='other', is_active=True)])
        db.add_all([Project(id=1, owner_id=1, title='Novel'),
                    Project(id=2, owner_id=2, title='Private')])
        db.add_all([Document(id=1, project_id=1, title='One', content=[
            {'id': 'b1', 'type': 'paragraph', 'content': 'old hero', 'props': {'align': 'left'}},
            {'id': 'b2', 'type': 'paragraph', 'content': 'untouched'}]),
            Document(id=2, project_id=2, title='Secret', content=[])])
        db.add(AIMemory(project_id=1, notes='old notes'))
        db.commit()
    yield factory
    engine.dispose()


def execute(store, actions, instruction='Investigate and improve this project freely'):
    from app.services.project_agent_service import create_run, claim_run, execute_run
    with store() as db:
        run = create_run(db, 1, 1, instruction, None)
        run_id = run.id
    calls = []
    async def model(messages, **kwargs):
        calls.append(messages)
        return json.dumps(actions[len(calls) - 1])
    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    return run_id, calls


def action(tool, **args):
    return {'tool': tool, 'args': args}


def patch(old='old', new='new'):
    return action('propose_document_patch', document_id=1, block_id='b1',
                  old_text=old, new_text=new, reason='Improve consistency')


def test_generate_documents_from_settings_uses_batch_api(store, monkeypatch):
    """多篇正文走既有 batch_generate，不把全文交回模型。"""
    from app.services.ai_writing_service import AIWritingService
    from app.services.project_agent_service import get_run

    seen = []

    async def fake_batch(db, **kwargs):
        seen.append(kwargs.get("custom_instruction") or "")
        title = kwargs["outline_nodes"][0]["title"]
        yield json.dumps({
            "type": "chapter_complete",
            "chapter_title": title,
            "chapter_content": f"## {title}\n\n本章正文。",
        }, ensure_ascii=False)

    monkeypatch.setattr(AIWritingService, "batch_generate", staticmethod(fake_batch))
    with store() as db:
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        memory.outline = [
            {"title": "初遇", "description": "雨天"},
            {"title": "靠近", "description": "琴房"},
        ]
        db.commit()
    run_id, calls = execute(
        store,
        [
            action("generate_documents_from_settings", custom_instruction="只写本章"),
            action("finish", answer="已生成初遇和靠近"),
        ],
        instruction="根据设定生成多篇文章",
    )
    assert len(calls) == 2
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "applied"
        titles = {doc.title for doc in db.query(Document).filter_by(project_id=1)}
        assert {"初遇", "靠近"} <= titles
        body = json.dumps(
            [doc.content for doc in db.query(Document).filter(Document.title.in_(["初遇", "靠近"]))],
            ensure_ascii=False,
        )
        assert "本章正文" in body
        assert "本章正文" not in json.dumps(calls[-1], ensure_ascii=False)
        assert seen and all("必须符合本项目的规则" in item for item in seen)
        assert any("只写本章" in item for item in seen)


def test_arbitrary_multistep_staged_patch_memory_apply_revert(store):
    from app.services.project_agent_service import get_run, transition
    run_id, calls = execute(store, [
        action('list_project'), action('read_document', document_id=1),
        patch(), patch('new', 'brave'), action('read_memory'),
        action('propose_memory_patch', field='notes', before='old notes', after='new notes', reason='Consistency'),
        action('finish', answer='Reviewed and prepared coordinated edits')])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'  # finish 后自动写入
        assert len(run.changes) == 2
        assert 'brave hero' in json.dumps(calls[-1])
        assert db.get(Document, 1).content[0] == {
            'id': 'b1', 'type': 'paragraph', 'content': 'brave hero', 'props': {'align': 'left'}}
        transition(db, 1, 1, run_id, 'apply')  # idempotent
        assert db.query(AIMemory).filter_by(project_id=1).one().notes == 'new notes'
        transition(db, 1, 1, run_id, 'revert')
        assert db.get(Document, 1).content[0]['content'] == 'old hero'
        transition(db, 1, 1, run_id, 'revert')


def test_block_rewrite_stages_full_content_without_old_text(store):
    from app.services.project_agent_service import get_run, transition
    run_id, _ = execute(store, [
        action('read_document', document_id=1),
        action('propose_block_rewrite', document_id=1, block_id='b1',
               new_content='rewritten hero arc', reason='Polish the paragraph'),
        action('finish', answer='Rewrote the opening')])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert run.changes[0]['before'] == 'old hero'
        assert run.changes[0]['after'] == 'rewritten hero arc'
        assert db.get(Document, 1).content[0]['content'] == 'rewritten hero arc'
        transition(db, 1, 1, run_id, 'apply')  # idempotent
        assert db.get(Document, 1).content[0]['content'] == 'rewritten hero arc'


def test_selection_focus_preloads_only_target_blocks(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run
    with store() as db:
        run = create_run(
            db, 1, 1, "请只润色选中段落", None,
            focus={"document_id": 1, "selection": "old hero", "block_ids": ["b1"]},
        )
        run_id = run.id
    calls = []

    async def model(messages, **kwargs):
        calls.append(messages)
        return json.dumps({
            "tool": "propose_block_rewrite",
            "args": {
                "document_id": 1,
                "block_id": "b1",
                "new_content": "brave hero",
                "reason": "polish",
            },
        }) if len(calls) == 1 else json.dumps({"tool": "finish", "args": {"answer": "已润色选中段"}})

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    blob = json.dumps(calls[0], ensure_ascii=False)
    assert "禁止再调用 read_document" in blob or "禁止 read_document" in blob
    assert "block_id=b1" in blob
    assert "目标已锁定" in blob
    assert "禁止追问" in blob
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "applied"
        assert run.changes[0]["after"] == "brave hero"
        assert db.get(Document, 1).content[0]["content"] == "brave hero"


def test_selection_focus_rejects_ask_which_blocks(store):
    """选区已锁定时，模型追问「哪几段」会被纠正并要求直接改写。"""
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run
    with store() as db:
        doc = db.get(Document, 1)
        doc.content = [
            {"id": "b1", "type": "paragraph", "content": "失恋姑娘与橘猫", "props": {}},
            {"id": "b2", "type": "paragraph", "content": "高管裸奔", "props": {}},
            {"id": "b3", "type": "paragraph", "content": "张阿姨黑猫", "props": {}},
        ]
        db.commit()
        run = create_run(
            db, 1, 1, "请扩写选中的三段", None,
            focus={
                "document_id": 1,
                "selection": "失恋姑娘与橘猫\n高管裸奔\n张阿姨黑猫",
                "block_ids": ["b1", "b2", "b3"],
            },
        )
        run_id = run.id
    calls = []

    async def model(messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            return (
                "我这边没有收到具体是哪三段的标识。能告诉我你选中的是哪三个段落吗？\n"
                "```json\n"
                '{"tool":"finish","args":{"answer":"请告诉我是哪三段"}}\n'
                "```"
            )
        if len(calls) == 2:
            blob = json.dumps(messages, ensure_ascii=False)
            assert "目标段落已锁定" in blob or "禁止追问" in blob
            assert "block_id=b1" in blob
            return json.dumps({
                "tool": "propose_block_rewrite",
                "args": {
                    "document_id": 1,
                    "block_id": "b1",
                    "new_content": "失恋姑娘与橘猫（扩写）",
                    "reason": "expand",
                },
            }, ensure_ascii=False)
        return json.dumps({"tool": "finish", "args": {"answer": "已扩写第一段，其余可继续"}}, ensure_ascii=False)

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "applied"
        assert run.changes[0]["after"] == "失恋姑娘与橘猫（扩写）"
        assert db.get(Document, 1).content[0]["content"] == "失恋姑娘与橘猫（扩写）"
    assert len(calls) >= 2


def test_read_document_observation_is_clipped(store):
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool
    long = "字" * 2000
    with store() as db:
        doc = db.get(Document, 1)
        doc.content = [{"id": "b1", "type": "paragraph", "content": long, "props": {}}]
        db.commit()
        ctx = ProjectAgentContext(1, 1)
        data = execute_tool(ctx, db, "read_document", {"document_id": 1, "offset": 0, "limit": 50})
    assert data["limit"] <= 20
    assert len(data["blocks"][0]["content"]) < 900
    assert data["blocks"][0]["content"].endswith("…")
    # 完整正文仍在暂存，可 rewrite
    assert len(ctx.read_documents[1][0]["content"]) == 2000


def test_focus_preloads_current_article_for_this_piece(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run
    with store() as db:
        run = create_run(db, 1, 1, "润色当前文档焦点段落", None, focus={"document_id": 1})
        run_id = run.id
    calls = []

    async def model(messages, **kwargs):
        calls.append(messages)
        # 即使误调 list_project，也应看到焦点提示；此处直接空参 finish 也应成功
        if len(calls) == 1:
            return json.dumps({"tool": "list_project", "args": {}})
        return json.dumps({"tool": "finish", "args": {}})

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    blob = json.dumps(calls, ensure_ascii=False)
    assert "document_id=1" in blob
    assert "old hero" in blob
    assert "禁止" in blob or "不要" in blob
    # list_project 的 observation 应点明焦点文档
    assert "focus_document_id" in blob or "已预读" in blob
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "completed"
        # finish 无 answer 时用默认兜底，不应失败
        assert run.answer


def test_create_and_revert_rejects_edited_created_document(store):
    from app.services.project_agent_service import transition, get_run
    run_id, _ = execute(store, [action('propose_create_document', title='Plan', text='A new plan', reason='Planning'),
                                action('finish', answer='Plan drafted')])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'  # 新建文档也自动写入
        change = run.changes[0]
        doc = db.get(Document, change['target_id'])
        doc.title = 'Human edited'
        db.commit()
        with pytest.raises(HTTPException) as error:
            transition(db, 1, 1, run_id, 'revert')
        assert error.value.status_code == 409
        assert db.get(Document, doc.id).title == 'Human edited'


def test_apply_conflict_is_atomic_including_read_dependencies(store):
    """残留 proposed 时若设定已被人改，apply 仍 409 且正文不落库。"""
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import transition
    with store() as db:
        run = AgentRun(
            user_id=1,
            project_id=1,
            conversation_id='conflict',
            instruction='Ready',
            status='proposed',
            changes=[
                {
                    'id': 'c1', 'kind': 'document_patch', 'document_id': 1, 'block_id': 'b1',
                    'title': 'One', 'before': 'old hero', 'after': 'new hero', 'reason': 'x',
                    'target_id': 1,
                },
                {
                    'id': 'c2', 'kind': 'memory_patch', 'field': 'notes',
                    'before': 'old notes', 'after': 'new', 'reason': 'Improve',
                },
            ],
        )
        db.add(run)
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        memory.notes = 'human'
        db.commit()
        run_id = run.id
        with pytest.raises(HTTPException) as error:
            transition(db, 1, 1, run_id, 'apply')
        assert error.value.status_code == 409
        assert db.get(Document, 1).content[0]['content'] == 'old hero'
        assert memory.notes == 'human'


@pytest.mark.parametrize('bad', [action('run_sql', sql='delete from users'),
    action('read_document', document_id=2), action('read_document', document_id=True),
    action('read_document', document_id=1, extra='no'),
    action('propose_document_patch', document_id=1, block_id='b1', old_text='old', new_text='x', reason='Unread'),
    action('propose_memory_patch', field='project_id', before=1, after=2, reason='Escape')])
def test_unsafe_or_unread_actions_fail_without_proposals(store, bad):
    from app.services.project_agent_service import get_run
    run_id, _ = execute(store, [bad])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert run.changes == []
        assert db.get(Document, 1).content[0]['content'] == 'old hero'


def test_paginated_reads_and_literal_search_report_coverage(store):
    from app.services.project_agent_service import get_run
    run_id, calls = execute(store, [action('read_document', document_id=1, offset=0, limit=1),
        action('search_project', query='hero', offset=0, limit=1), action('finish', answer='Found hero')])
    with store() as db:
        assert get_run(db, 1, 1, run_id).status == 'completed'
    observations = [json.loads(m['content']) for m in calls[-1] if m['role'] == 'user' and 'UNTRUSTED_OBSERVATION' in m['content']]
    by_tool = {o.get('tool'): o for o in observations if isinstance(o, dict)}
    # 后台预读会先插入 list_project / read_memory，按工具名断言
    assert by_tool['read_document']['data']['complete'] is False
    assert by_tool['search_project']['data']['coverage'] == 'all_project_documents_and_memory_literal'
    assert by_tool['search_project']['data']['complete'] is True


def test_cancel_fences_old_worker_resume_and_expired_claim(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run, transition, get_run
    from app.models.project_agent import AgentRun
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan freely', None).id
    old_claim = claim_run(store)
    with store() as db:
        transition(db, 1, 1, run_id, 'cancel')
    async def model(*args, **kwargs):
        return json.dumps(action('finish', answer='Stale answer'))
    asyncio.run(execute_run(store, old_claim, model))
    with store() as db:
        assert get_run(db, 1, 1, run_id).status == 'cancelled'
        transition(db, 1, 1, run_id, 'resume')
    claim = claim_run(store)
    with store() as db:
        db.get(AgentRun, run_id).lease_until = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    replacement = claim_run(store)
    assert replacement != claim
    asyncio.run(execute_run(store, claim, model))
    asyncio.run(execute_run(store, replacement, model))
    with store() as db:
        assert get_run(db, 1, 1, run_id).status == 'completed'


def test_owner_revocation_fences_worker(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run
    from app.models.project_agent import AgentRun
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan', None).id
    claim = claim_run(store)
    with store() as db:
        db.get(Project, 1).owner_id = 2
        db.commit()
    async def forbidden(*args, **kwargs):
        pytest.fail('Model called after owner revocation')
    asyncio.run(execute_run(store, claim, forbidden))
    with store() as db:
        assert db.get(AgentRun, run_id).status == 'failed'


@pytest.mark.parametrize('with_changes', [False, True])
def test_explicit_clarification_ends_turn_and_preserves_proposals(store, with_changes):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run
    with store() as db:
        run_id = create_run(db, 1, 1, 'Help me plan', None).id
    replies = ([json.dumps(action('propose_create_document', title='Plan', text='Draft', reason='Plan'))]
               if with_changes else []) + [json.dumps(action('finish', answer='Which character should we focus on?'))]
    calls = []
    async def model(messages, **kwargs):
        calls.append(messages)
        return replies[len(calls) - 1]
    asyncio.run(execute_run(store, claim_run(store), model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == ('applied' if with_changes else 'completed')
        assert run.answer == 'Which character should we focus on?'
        assert run.lease_owner is None
        assert len(calls) == len(replies)
        # 有提案时 create_document 会自动写入，文档数 +1
        assert db.query(Document).filter_by(project_id=1).count() == (2 if with_changes else 1)


def test_public_answer_sanitizes_action_json_but_keeps_bracket_prose(store):
    from app.services.project_agent_service import create_run, run_to_dict
    with store() as db:
        run = create_run(db, 1, 1, 'Plan', None)
        run.answer = 'I checked the project. ```json\\n{"tool":"read_memory","args":{}}```'
        run.messages = [
            {'role': 'assistant', 'content': '[小墨] 这是正常的上下文提示。', 'step': 1},
            {'role': 'assistant', 'content': '```json\\n{"tool":"read_memory"}\\n```', 'step': 2},
        ]
        run.events = [
            {'sequence': 1, 'type': 'finish', 'message': '```json\\n{"tool":"read_memory"}\\n```'},
            {'sequence': 2, 'type': 'info', 'message': '[小墨] 正常进度。'},
        ]
        result = run_to_dict(run)
        assert result['answer'] == 'I checked the project.'
        assert '[小墨] 这是正常的上下文提示。' in [m['content'] for m in result['messages']]
        assert all('read_memory' not in json.dumps(item, ensure_ascii=False) for item in result['messages'])
        assert all('read_memory' not in json.dumps(item, ensure_ascii=False) for item in result['events'])
        assert result['events'][1]['message'] == '[小墨] 正常进度。'


@pytest.mark.parametrize('envelope', [
    '{"tool":"read_memory","args":{}}', '{"to', '{',
    '[{"tool":"read_memory","args":{}}]', '[ { "tool":', '[',
])
def test_public_answer_and_messages_hide_action_envelopes(store, envelope):
    from app.services.project_agent_service import create_run, run_to_dict
    with store() as db:
        run = create_run(db, 1, 1, 'Plan', None)
        run.answer = envelope
        run.messages = [{'role': 'assistant', 'content': envelope, 'streaming': True}]
        result = run_to_dict(run)
        assert result['answer'] == ''
        assert result['messages'] == []


@pytest.mark.parametrize('reply', [
    '{"tool":',
    json.dumps(action('finish', answer='Done. ```json\n{"tool":"private_envelope"}\n```')),
])
def test_execution_public_payload_has_no_action_envelope(store, reply):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run, run_to_dict
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan', None).id
    async def model(messages, **kwargs):
        return reply
    asyncio.run(execute_run(store, claim_run(store), model))
    with store() as db:
        result = run_to_dict(get_run(db, 1, 1, run_id))
        public_text = json.dumps(result, ensure_ascii=False)
        assert 'private_envelope' not in public_text
        assert '\\"tool\\"' not in public_text
        assert all('```' not in event['message'] for event in result['events'])


def test_bracket_prose_survives_next_turn_history(store):
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import _load_conversation_messages
    now = datetime.utcnow()
    with store() as db:
        previous = AgentRun(user_id=1, project_id=1, conversation_id='bracket-prose',
            instruction='Continue', status='completed', answer='[小墨] 请先确认你的目标。',
            created_at=now - timedelta(seconds=1), messages=[
                {'role': 'assistant', 'content': '[小墨] 我已经读完了设定。', 'streaming': False},
            ])
        current = AgentRun(user_id=1, project_id=1, conversation_id='bracket-prose',
                           instruction='Next', created_at=now)
        db.add_all([previous, current])
        db.commit()
        history = _load_conversation_messages(db, current)
        contents = [message['content'] for message in history]
        assert '[小墨] 我已经读完了设定。' in contents
        assert '[小墨] 请先确认你的目标。' in contents


def test_serialization_sanitizes_partial_tool_streams(store):
    from app.services.project_agent_service import create_run, run_to_dict
    with store() as db:
        run = create_run(db, 1, 1, 'Plan', None)
        run.messages = [
            {'role': 'user', 'content': 'Plan', 'step': 0},
            {'role': 'assistant', 'content': 'Checking now. ```json\n{"tool": "read_', 'step': 1, 'streaming': True},
            {'role': 'assistant', 'content': '{"tool": "read_', 'step': 2, 'streaming': True},
            {'role': 'assistant', 'content': 'Working `', 'step': 3, 'streaming': True},
            {'role': 'tool', 'content': 'secret raw tool result'},
        ]
        messages = run_to_dict(run)['messages']
        assert messages == [
            {'role': 'user', 'content': 'Plan', 'step': 0, 'streaming': False},
            {'role': 'assistant', 'content': 'Checking now.', 'step': 1, 'streaming': True},
            {'role': 'assistant', 'content': 'Working', 'step': 3, 'streaming': True},
        ]


def test_stream_progress_never_persists_tool_json(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run, run_to_dict
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan', None).id
    calls = []
    async def model(messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            chunk = 'I will inspect the project. ```json\n{"tool":"list_project","args":{}}```'
            kwargs['on_delta'](chunk)
            with store() as db:
                run = get_run(db, 1, 1, run_id)
                assert 'list_project' not in json.dumps(run.messages)
                assert run_to_dict(run)['messages'][-1]['content'] == 'I will inspect the project.'
            return chunk
        return json.dumps(action('finish', answer='Done'))
    asyncio.run(execute_run(store, claim_run(store), model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'completed', run.error


def test_history_scoped_deduplicated_and_status_aware(store):
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import _load_conversation_messages
    now = datetime.utcnow()
    with store() as db:
        rows = []
        for index, (user, project, status) in enumerate([
            (1, 1, 'proposed'), (1, 1, 'failed'), (1, 1, 'applied'),
            (2, 1, 'completed'), (1, 2, 'completed'),
        ]):
            instruction = f'instruction-{index}'
            rows.append(AgentRun(user_id=user, project_id=project, conversation_id='shared',
                instruction=instruction, status=status, answer=f'claim-{index}',
                created_at=now - timedelta(seconds=10-index), messages=[
                    {'role': 'user', 'content': instruction},
                    {'role': 'assistant', 'content': f'claim-{index}', 'streaming': False},
                    {'role': 'assistant', 'content': 'unfinished secret', 'streaming': True},
                    {'role': 'assistant', 'content': '{"tool":"raw_secret"}'},
                ]))
        current = AgentRun(user_id=1, project_id=1, conversation_id='shared',
                           instruction='Continue', created_at=now)
        db.add_all(rows + [current])
        db.commit()
        history = _load_conversation_messages(db, current)
        text = json.dumps(history, ensure_ascii=False)
        assert text.count('instruction-0') == 1
        assert text.count('claim-0') == 1
        assert 'proposed' in text and '未应用' in text
        assert 'applied' in text and '已应用' in text
        assert 'failed' in text
        for secret in ['claim-1', 'instruction-3', 'instruction-4', 'unfinished secret', 'raw_secret']:
            assert secret not in text


def test_history_drops_prior_tool_json_and_long_prose(store):
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import _load_conversation_messages
    now = datetime.utcnow()
    long_story = "故事线阶段。" * 200
    with store() as db:
        previous = AgentRun(
            user_id=1, project_id=1, conversation_id='long-history',
            instruction='补写感情线', status='applied',
            answer='故事线已更新完成。' + long_story,
            created_at=now - timedelta(seconds=1),
            messages=[{
                'role': 'assistant',
                'content': '先改角色。\n{"tool":"propose_memory_patch","args":{"field":"characters","after":[{"name":"不应回放"}]}}',
                'streaming': False,
            }],
        )
        current = AgentRun(user_id=1, project_id=1, conversation_id='long-history',
                           instruction='继续', created_at=now)
        db.add_all([previous, current])
        db.commit()
        history = _load_conversation_messages(db, current)
        blob = json.dumps(history, ensure_ascii=False)
        assert '不应回放' not in blob
        assert 'propose_memory_patch' not in blob
        assert '故事线已更新完成' in blob
        assert len(blob) < 2500


def test_overlong_history_is_dropped_for_current_instruction(store):
    """历史总长超出上限时整段不带入，只留下当前指令给执行循环。"""
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import _load_conversation_messages, MAX_CONTEXT_CHARS
    now = datetime.utcnow()
    with store() as db:
        rows = []
        for index in range(12):
            rows.append(AgentRun(
                user_id=1, project_id=1, conversation_id='too-long',
                instruction=f'第{index}轮去改故事线', status='applied',
                answer='已写入。' + ('阶段说明。' * 80),
                created_at=now - timedelta(seconds=20 - index),
                messages=[{'role': 'assistant', 'content': '已写入。' + ('阶段说明。' * 80), 'streaming': False}],
            ))
        current = AgentRun(user_id=1, project_id=1, conversation_id='too-long',
                           instruction='只改 outline', created_at=now)
        db.add_all(rows + [current])
        db.commit()
        history = _load_conversation_messages(db, current, current.instruction)
        assert history == []
        assert MAX_CONTEXT_CHARS > 0


def test_history_trimming_retains_status_with_claims_and_equal_timestamps(store):
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import _load_conversation_messages
    now = datetime.utcnow()
    with store() as db:
        previous = AgentRun(user_id=1, project_id=1, conversation_id='same-time',
            instruction='Prepare edits', status='proposed', created_at=now,
            messages=[{'role': 'assistant', 'content': f'claim-{i}'} for i in range(30)])
        current = AgentRun(user_id=1, project_id=1, conversation_id='same-time',
            instruction='Continue', created_at=now)
        db.add_all([previous, current])
        db.commit()
        history = _load_conversation_messages(db, current)
        assert any('claim-' in m['content'] for m in history)
        for index, message in enumerate(history):
            if 'claim-' in message['content']:
                assert index > 0
                assert 'proposed' in history[index - 1]['content']
                assert '未应用' in history[index - 1]['content']


@pytest.mark.parametrize('ending', ['plain', 'finish'])
@pytest.mark.parametrize('interruption', ['cancel', 'owner', 'lease'])
def test_final_reply_fenced_against_mid_model_changes(store, ending, interruption):
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import create_run, claim_run, execute_run
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan', None).id
    claim = claim_run(store)
    async def model(messages, **kwargs):
        with store() as db:
            run = db.get(AgentRun, run_id)
            if interruption == 'cancel':
                run.status = 'cancelled'
                run.lease_owner = None
            elif interruption == 'owner':
                db.get(Project, 1).owner_id = 2
            else:
                run.lease_until = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        return 'Which hero?' if ending == 'plain' else json.dumps(action('finish', answer='Which hero?'))
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = db.get(AgentRun, run_id)
        assert run.status not in ('completed', 'proposed')
        assert not run.answer


def test_creation_and_lookup_require_current_project_ownership(store):
    from app.services.project_agent_service import create_run, get_run
    with store() as db:
        run = create_run(db, 1, 1, 'Plan', None)
        db.get(Project, 1).owner_id = 2
        db.commit()
        for operation in [lambda: get_run(db, 1, 1, run.id),
                          lambda: create_run(db, 1, 1, 'Again', None)]:
            with pytest.raises(HTTPException) as error:
                operation()
            assert error.value.status_code == 404


def test_conversation_and_idempotency_cannot_cross_scopes(store):
    from app.services.project_agent_service import create_run
    with store() as db:
        db.add(Project(id=3, owner_id=1, title='Other owned project'))
        db.commit()
        first = create_run(db, 1, 1, 'Plan', None, 'same-key')
        assert create_run(db, 1, 1, 'Plan', first.conversation_id, 'same-key').id == first.id
        for user, project in [(1, 3), (2, 2)]:
            with pytest.raises(HTTPException) as error:
                create_run(db, user, project, 'Continue', first.conversation_id)
            assert error.value.status_code == 404
            with pytest.raises(HTTPException) as error:
                create_run(db, user, project, 'Other', None, 'same-key')
            assert error.value.status_code == 409
        with pytest.raises(HTTPException) as error:
            create_run(db, 1, 1, 'Continue', 'unknown-conversation')
        assert error.value.status_code == 404
        assert create_run(db, 1, 1, 'Continue', first.conversation_id).conversation_id == first.conversation_id


def test_incomplete_action_fence_fails_without_leaking_answer(store):
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run, run_to_dict
    with store() as db:
        run_id = create_run(db, 1, 1, 'Plan', None).id
    async def model(messages, **kwargs):
        return 'Checking. ```json\n{"tool":"private_action","args":'
    asyncio.run(execute_run(store, claim_run(store), model))
    with store() as db:
        result = run_to_dict(get_run(db, 1, 1, run_id))
        assert result['status'] == 'failed'
        assert 'private_action' not in json.dumps(result)


@pytest.mark.parametrize('other_scope', [False, True])
def test_idempotency_race_recovers_or_rejects_scope(store, monkeypatch, other_scope):
    from app.services.project_agent_service import create_run
    with store() as db:
        original_commit = db.commit
        winner = []
        def competing_commit():
            with store() as competitor:
                winner.append(create_run(competitor, 2 if other_scope else 1,
                                         2 if other_scope else 1, 'First', None, 'racing-key').id)
            original_commit()
        monkeypatch.setattr(db, 'commit', competing_commit)
        if other_scope:
            with pytest.raises(HTTPException) as error:
                create_run(db, 1, 1, 'Retry', None, 'racing-key')
            assert error.value.status_code == 409
        else:
            assert create_run(db, 1, 1, 'Retry', None, 'racing-key').id == winner[0]


def test_api_contract_and_authorization_all_endpoints(store):
    from app.api import project_agent
    from app.api.auth import get_current_user
    app = FastAPI()
    app.include_router(project_agent.router)
    def session():
        with store() as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_user] = lambda: {'id': 1}
    async def requests():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            base = '/api/projects/1/agent/runs'
            response = await client.post(base, json={'instruction': 'Think about anything useful'})
            assert response.status_code == 200
            run = response.json()
            assert run['status'] == 'queued' and run['conversation_id']
            assert (await client.get(base)).json()[0]['id'] == run['id']
            app.dependency_overrides[get_current_user] = lambda: {'id': 2}
            for method, path in [('GET', base), ('POST', base), ('GET', base + '/' + run['id'])] + [
                ('POST', base + '/' + run['id'] + '/' + verb) for verb in ['apply', 'revert', 'resume', 'cancel']]:
                result = await client.request(method, path, json={'instruction': 'Unauthorized'})
                assert result.status_code in (403, 404)
    asyncio.run(requests())


def test_writing_tools_whitelist_and_arg_validation(store):
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool, ToolViolation, TOOLS
    for name in (
        "create_project",
        "list_hot_topics",
        "hot_topic_write",
        "copywriting_write",
        "list_brainstorm_ideas",
        "brainstorm_write",
        "story_generate",
        "propose_writing_draft",
        "propose_story_settings",
    ):
        assert name in TOOLS
    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        with pytest.raises(ToolViolation):
            execute_tool(ctx, db, "hot_topic_write", {})
        with pytest.raises(ToolViolation):
            execute_tool(ctx, db, "copywriting_write", {"word_count": "nine"})
        with pytest.raises(ToolViolation):
            execute_tool(ctx, db, "propose_writing_draft", {"draft_id": "missing", "reason": "x"})


def test_propose_memory_patch_reason_optional(store):
    """模型常漏填 reason / 传 null，不应整轮 ToolViolation。"""
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool, _validate_args

    resolved = _validate_args(
        "propose_memory_patch",
        {"field": "storyline", "before": "old", "after": "new with conflict"},
    )
    assert resolved["reason"] == "更新项目设定"

    resolved_null = _validate_args(
        "propose_memory_patch",
        {"field": "storyline", "before": "old", "after": "new", "reason": None},
    )
    assert resolved_null["reason"] == "更新项目设定"

    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        execute_tool(ctx, db, "read_memory", {})
        before = ctx.staged_memory.get("storyline")
        data = execute_tool(
            ctx,
            db,
            "propose_memory_patch",
            {"field": "storyline", "before": before, "after": "加入冲突与感情转折"},
        )
        assert data["complete"] is True
        assert ctx.changes
        assert ctx.changes[-1]["reason"] == "更新项目设定"


def test_propose_memory_patch_infers_missing_field(store):
    """模型漏传 field 时：按 after 形态或中文别名自动补全。"""
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool

    points = [
        {"title": "雨天相遇", "summary": "两人因伞初识"},
        {"title": "文化祭告白", "summary": "舞台后双向告白"},
    ]
    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        execute_tool(ctx, db, "read_memory", {})
        before = ctx.staged_memory.get("key_points")
        data = execute_tool(
            ctx,
            db,
            "propose_memory_patch",
            {"before": before, "after": points},  # 故意不传 field
        )
        assert data["field"] == "key_points"
        assert ctx.changes[-1]["field"] == "key_points"

        # 中文别名
        before2 = ctx.staged_memory.get("key_points")
        data2 = execute_tool(
            ctx,
            db,
            "propose_memory_patch",
            {
                "field": "关键情节点",
                "before": before2,
                "after": points + [{"title": "尾声", "summary": "留白"}],
            },
        )
        assert data2["field"] == "key_points"


def test_read_memory_overview_and_single_field(store):
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool

    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        overview = execute_tool(ctx, db, "read_memory", {})
        assert overview["coverage"] == "overview"
        assert "characters" in overview["fields"]
        assert overview["fields"]["characters"]["empty"] is True or "count" in overview["fields"]["characters"]

        single = execute_tool(ctx, db, "read_memory", {"field": "key_points"})
        assert single["coverage"] == "single_field"
        assert single["field"] == "key_points"
        assert "value" in single


def test_read_memory_accepts_field_and_ignores_benign_extras(store):
    """field 必须可用；模型瞎加的 mode/full 等多余参数不致失败。"""
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool, _validate_args

    resolved = _validate_args(
        "read_memory",
        {"field": "storyline", "mode": "full", "verbose": True},
    )
    assert resolved == {"field": "storyline"}

    resolved2 = _validate_args("read_memory", {"字段": "故事线"})
    assert resolved2.get("field") == "故事线"

    with store() as db:
        mem = db.query(AIMemory).filter_by(project_id=1).one()
        mem.storyline = {
            "summary": "很长" * 2000,
            "stages": [{"title": f"S{i}", "summary": "x" * 200} for i in range(30)],
        }
        db.commit()
        ctx = ProjectAgentContext(1, 1)
        data = execute_tool(ctx, db, "read_memory", {"field": "storyline", "full": True})
        assert data["field"] == "storyline"
        assert data["coverage"] == "single_field_digest"
        assert data["full_chars"] > 2200
        assert ctx.staged_memory["storyline"]["summary"].startswith("很长")


def test_action_top_level_field_merged_into_args(store):
    """模型把 field 写在顶层而非 args 内时也应成功。"""
    from app.services.project_agent_service import (
        _parse_action_and_message,
        create_run,
        claim_run,
        execute_run,
        get_run,
    )

    raw = '好的\n```json\n{"tool":"read_memory","field":"storyline"}\n```'
    action, said = _parse_action_and_message(raw)
    assert action["tool"] == "read_memory"
    assert action.get("field") == "storyline"

    with store() as db:
        run = create_run(db, 1, 1, "读 notes", None)
        run_id = run.id
    calls = {"n": 0}

    async def model(messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps({"tool": "read_memory", "field": "notes"}, ensure_ascii=False)
        return json.dumps({"tool": "finish", "args": {"answer": "已读"}}, ensure_ascii=False)

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status in ("completed", "applied", "proposed")
        assert run.status != "failed"
        assert not (run.error or "").startswith("工具")


def test_propose_memory_patch_merge_without_before(store):
    """merge 模式可不传 before；只传增量角色即可 upsert。"""
    from app.models.models import AIMemory
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool
    from app.services.project_agent_service import get_run, transition

    with store() as db:
        mem = db.query(AIMemory).filter_by(project_id=1).one()
        mem.characters = [
            {"name": "Irene", "description": "会长", "role": "主角", "personality": "", "background": "", "goals": "", "avatar": "", "color": ""},
        ]
        db.commit()

        ctx = ProjectAgentContext(1, 1)
        data = execute_tool(
            ctx,
            db,
            "propose_memory_patch",
            {
                "field": "characters",
                "mode": "merge",
                "after": [
                    {"name": "Irene", "description": "会长，反差萌"},
                    {"name": "Wendy", "description": "转学生", "role": "主角"},
                ],
            },
        )
        assert data["mode"] == "merge"
        names = [c["name"] for c in data["staged_value"]]
        assert names == ["Irene", "Wendy"]
        assert "反差萌" in data["staged_value"][0]["description"]


def test_propose_memory_merge_applies(store):
    from app.services.project_agent_service import get_run
    from app.models.models import AIMemory

    run_id, _ = execute(store, [
        action("propose_memory_patch", field="key_points", mode="merge",
               after=[{"title": "开端", "summary": "相遇"}, {"title": "高潮", "summary": "告白"}]),
        action("finish", answer="已补情节点"),
    ])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "applied"
        points = db.query(AIMemory).filter_by(project_id=1).one().key_points
        titles = [p.get("title") for p in (points or [])]
        assert "开端" in titles and "高潮" in titles


def test_copywriting_write_then_propose_draft_auto_apply(store, monkeypatch):
    """生成 → propose_writing_draft → finish：正文经提案写入，不在 adapter 落库。"""
    from unittest.mock import AsyncMock
    from app.services.project_agent_service import get_run
    from app.services import writing_adapters

    async def _fake(**kwargs):
        return {
            "kind": "copywriting",
            "title": "测试文案",
            "content": "完整营销文案正文，请写入文档。",
            "meta": {},
        }

    monkeypatch.setattr(
        writing_adapters,
        "copywriting_generate",
        AsyncMock(side_effect=_fake),
    )

    draft_holder = {"id": None}

    def scripted():
        # 假模型：写文案 → 用 observation 里的 draft_id 提案 → finish
        steps = []

        async def model(messages, **kwargs):
            steps.append(messages)
            n = len(steps)
            if n == 1:
                return json.dumps(
                    action(
                        "copywriting_write",
                        product="墨心",
                        target_audience="作者",
                        selling_points="智能写作",
                    ),
                    ensure_ascii=False,
                )
            if n == 2:
                blob = json.dumps(messages, ensure_ascii=False)
                assert "draft_id" in blob
                assert "完整营销文案正文" not in blob or "preview" in blob
                # 从最后一条 observation 取 draft_id
                last = messages[-1]["content"]
                data = json.loads(last) if last.strip().startswith("{") else None
                if data is None:
                    import re
                    m = re.search(r'"draft_id"\s*:\s*"([^"]+)"', last)
                    draft_holder["id"] = m.group(1) if m else None
                else:
                    draft_holder["id"] = data.get("draft_id") or (data.get("data") or {}).get("draft_id")
                if not draft_holder["id"]:
                    import re
                    m = re.search(r'draft_[a-f0-9]+', last)
                    draft_holder["id"] = m.group(0) if m else None
                assert draft_holder["id"]
                return json.dumps(
                    action(
                        "propose_writing_draft",
                        draft_id=draft_holder["id"],
                        reason="写入项目",
                    ),
                    ensure_ascii=False,
                )
            return json.dumps(action("finish", answer="文案已写入"), ensure_ascii=False)

        return model

    from app.services.project_agent_service import create_run, claim_run, execute_run

    with store() as db:
        run = create_run(db, 1, 1, "写一篇营销文案", None)
        run_id = run.id
    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, scripted()))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "applied"
        assert any(c["kind"] == "create_document" for c in run.changes)
        created = [d for d in db.query(Document).filter_by(project_id=1).all() if d.title == "测试文案"]
        assert created
        texts = json.dumps(created[0].content, ensure_ascii=False)
        assert "完整营销文案正文" in texts


def test_list_brainstorm_ideas_tool(store):
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool
    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        data = execute_tool(ctx, db, "list_brainstorm_ideas", {"limit": 5})
    assert data["kind"] == "brainstorm_ideas"
    assert data["ideas"]
    assert data.get("page_hint") == "/brainstorm-writing"


def test_story_generate_then_propose_settings(store, monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool
    from app.services import writing_adapters

    fake_story = {
        "title_options": ["新故事"],
        "characters": [{"name": "小墨", "role": "主角"}],
        "outline": [{"title": "第一幕", "description": "开场"}],
        "plot_points": ["冲突"],
        "world_building": {"city": "云城"},
        "core_theme": "友情",
        "input_theme": "猫咪与作家",
        "genre": "日常",
        "writing_style": {"tone": "温暖"},
    }

    monkeypatch.setattr(
        writing_adapters,
        "story_generate",
        AsyncMock(
            return_value={
                "kind": "story_settings",
                "title": "新故事",
                "story_data": fake_story,
                "meta": {},
            }
        ),
    )

    with store() as db:
        ctx = ProjectAgentContext(1, 1)
        obs = execute_tool(ctx, db, "story_generate", {"theme": "猫咪与作家"})
        assert obs["draft_id"]
        assert obs.get("has_story_data")
        assert "preview" in obs or obs.get("content_chars") == 0
        result = execute_tool(
            ctx,
            db,
            "propose_story_settings",
            {"draft_id": obs["draft_id"], "reason": "应用设定"},
        )
        assert "characters" in result["patched_fields"]
        assert any(c["kind"] == "memory_patch" for c in ctx.changes)


def test_create_project_tool_binds_context(store):
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool, ToolViolation
    with store() as db:
        ctx = ProjectAgentContext(None, 1)
        with pytest.raises(ToolViolation):
            execute_tool(ctx, db, "list_project", {})
        data = execute_tool(
            ctx, db, "create_project", {"title": "脑洞新作", "description": "测试", "reason": "建项"}
        )
        assert data["project_id"]
        assert ctx.project_id == data["project_id"]
        assert any(c["kind"] == "created_project" for c in ctx.changes)
        listed = execute_tool(ctx, db, "list_project", {})
        assert listed["project_id"] == data["project_id"]
        with pytest.raises(ToolViolation):
            execute_tool(ctx, db, "create_project", {"title": "第二个"})
        assert db.get(Project, data["project_id"]).title == "脑洞新作"


def test_system_run_create_project_then_document(store, monkeypatch):
    """无项目会话：create_project → copywriting → propose_writing_draft → finish。"""
    from unittest.mock import AsyncMock
    from app.services.project_agent_service import (
        create_system_run, claim_run, execute_run, get_system_run,
    )
    from app.services import writing_adapters

    monkeypatch.setattr(
        writing_adapters,
        "copywriting_generate",
        AsyncMock(
            return_value={
                "kind": "copywriting",
                "title": "开篇文案",
                "content": "这是写入新项目的文案正文。",
                "meta": {},
            }
        ),
    )

    draft_holder = {"id": None}

    async def model(messages, **kwargs):
        n = getattr(model, "n", 0) + 1
        model.n = n
        blob = json.dumps(messages, ensure_ascii=False)
        if n == 1:
            return json.dumps(action("create_project", title="营销项目", reason="用户要写文案"))
        if n == 2:
            assert "project_id" in blob or "营销项目" in blob
            return json.dumps(action("copywriting_write", product="墨心", selling_points="AI"))
        if n == 3:
            import re
            m = re.search(r'draft_[a-f0-9]+', blob)
            draft_holder["id"] = m.group(0) if m else None
            assert draft_holder["id"]
            return json.dumps(
                action("propose_writing_draft", draft_id=draft_holder["id"], reason="写入")
            )
        return json.dumps(action("finish", answer="项目与文案已就绪"))

    with store() as db:
        run = create_system_run(db, 1, "帮我建项目写篇文案", None)
        run_id = run.id
        assert run.scope == "system"
        assert run.project_id is None

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))

    with store() as db:
        run = get_system_run(db, 1, run_id)
        assert run.status == "applied"
        assert run.project_id is not None
        assert db.get(Project, run.project_id).title == "营销项目"
        docs = db.query(Document).filter_by(project_id=run.project_id).all()
        assert any("文案正文" in json.dumps(d.content, ensure_ascii=False) for d in docs)


def test_system_agent_api_contract(store):
    from app.api import project_agent
    from app.api.auth import get_current_user
    app = FastAPI()
    app.include_router(project_agent.router)

    def session():
        with store() as db:
            yield db

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_user] = lambda: {"id": 1}

    async def requests():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            base = "/api/agent/runs"
            response = await client.post(base, json={"instruction": "聊聊脑洞选题"})
            assert response.status_code == 200
            run = response.json()
            assert run["status"] == "queued"
            assert run.get("scope") == "system"
            assert run.get("project_id") in (None, 0) or run["project_id"] is None
            listed = (await client.get(base)).json()
            assert listed[0]["id"] == run["id"]
            got = (await client.get(f"{base}/{run['id']}")).json()
            assert got["id"] == run["id"]
            app.dependency_overrides[get_current_user] = lambda: {"id": 2}
            assert (await client.get(base)).status_code in (200,)
            # user 2 看不到 user 1 的 system runs
            assert (await client.get(base)).json() == []
            deny = await client.get(f"{base}/{run['id']}")
            assert deny.status_code == 404

    asyncio.run(requests())


def test_propose_delete_document_stays_proposed_until_confirm(store):
    """删除提案禁止自动 apply，须用户确认后才删；可撤销恢复。"""
    from app.services.project_agent_service import get_run, transition

    run_id, _ = execute(
        store,
        [
            action('list_project'),
            action('propose_delete_document', document_id=1, reason='用户要求删除'),
            action('finish', answer='已准备删除提案，请确认'),
        ],
        instruction='请删除文档 One',
    )
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'proposed'  # 不得自动删除
        assert len(run.changes) == 1
        assert run.changes[0]['kind'] == 'delete_document'
        assert db.get(Document, 1) is not None

        transition(db, 1, 1, run_id, 'apply')
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert db.get(Document, 1) is None

        transition(db, 1, 1, run_id, 'revert')
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'reverted'
        restored_id = run.changes[0].get('restored_document_id')
        assert restored_id == 1  # 原 id 恢复，侧栏/编辑器链接仍有效
        restored = db.get(Document, restored_id)
        assert restored is not None
        assert restored.title == 'One'
        assert restored.content[0]['content'] == 'old hero'


def test_document_map_and_digest_keep_body_out_of_observation(store):
    """长文：目录/摘要不把全文塞进工具返回；摘要不解锁 rewrite。"""
    from app.services.project_agent_tools import ProjectAgentContext, execute_tool, ToolViolation

    with store() as db:
        doc = db.get(Document, 1)
        doc.content = [
            {"id": "h1", "type": "heading", "content": "第一章 起风了", "props": {"level": 1}},
            {"id": "b1", "type": "paragraph", "content": "old hero walked into the storm." * 20, "props": {}},
            {"id": "b2", "type": "paragraph", "content": "second beat of the chapter", "props": {}},
        ]
        db.commit()

        ctx = ProjectAgentContext(1, 1)
        mapped = execute_tool(ctx, db, "document_map", {})
        assert mapped["coverage"] == "project"
        assert mapped["documents"][0]["headings"]
        assert "old hero" not in json.dumps(mapped, ensure_ascii=False)

        digest = execute_tool(ctx, db, "digest_document", {"document_id": 1})
        assert "digest" in digest
        assert digest["block_count"] == 3
        assert 1 in ctx.document_digests
        assert 1 not in ctx.read_documents  # 摘要不解锁改稿

        with pytest.raises(ToolViolation):
            execute_tool(
                ctx,
                db,
                "propose_block_rewrite",
                {"document_id": 1, "block_id": "b1", "new_content": "x", "reason": "t"},
            )


def test_auto_compact_triggers_on_budget():
    from app.services.project_agent_service import (
        _should_auto_compact,
        _compact_messages,
        LIVE_CONTEXT_BUDGET_CHARS,
        LIVE_COMPACT_TRIGGER_RATIO,
    )
    from app.services.project_agent_tools import ProjectAgentContext

    fat = "字" * int(LIVE_CONTEXT_BUDGET_CHARS * LIVE_COMPACT_TRIGGER_RATIO // 2)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": fat},
        {"role": "assistant", "content": fat},
        {
            "role": "user",
            "content": '{"marker":"UNTRUSTED_OBSERVATION","data":"' + fat + '"}',
        },
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "next"},
    ]
    assert _should_auto_compact(messages)
    ctx = ProjectAgentContext(1, 1)
    ctx.document_digests[1] = {
        "title": "One",
        "digest": "英雄入场",
        "headings": [{"text": "第一章"}],
    }
    compacted = _compact_messages(messages, reason="测试", ctx=ctx, tail=3)
    blob = json.dumps(compacted, ensure_ascii=False)
    assert "已压缩" in blob or "上下文已压缩" in blob
    assert "英雄入场" in blob
    assert len(blob) < len(json.dumps(messages, ensure_ascii=False))


def test_propose_delete_apply_conflicts_on_content_edit(store):
    """提案后正文被人工改动时，确认删除须 409，文档保留。"""
    from app.services.project_agent_service import get_run, transition

    run_id, _ = execute(
        store,
        [
            action('propose_delete_document', document_id=1, reason='删'),
            action('finish', answer='待确认'),
        ],
    )
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'proposed'
        doc = db.get(Document, 1)
        doc.content = [{'id': 'b1', 'type': 'paragraph', 'content': 'human edited', 'props': {}}]
        db.commit()
        with pytest.raises(HTTPException) as error:
            transition(db, 1, 1, run_id, 'apply')
        assert error.value.status_code == 409
        assert db.get(Document, 1) is not None
        assert db.get(Document, 1).content[0]['content'] == 'human edited'


def test_propose_delete_document_cancel_keeps_document(store):
    from app.services.project_agent_service import get_run, transition

    run_id, _ = execute(
        store,
        [
            action('propose_delete_document', document_id=1, reason='试删'),
            action('finish', answer='待确认'),
        ],
    )
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'proposed'
        transition(db, 1, 1, run_id, 'cancel')
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'cancelled'
        assert db.get(Document, 1) is not None


def test_propose_delete_rejects_when_has_children(store):
    from app.services.project_agent_service import get_run

    with store() as db:
        db.add(Document(id=3, project_id=1, title='Child', parent_id=1, content=[]))
        db.commit()

    run_id, _ = execute(
        store,
        [action('propose_delete_document', document_id=1, reason='有子文档也应失败')],
    )
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert db.get(Document, 1) is not None
