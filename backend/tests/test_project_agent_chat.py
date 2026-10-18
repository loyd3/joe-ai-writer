"""对话式智能体回归测试：自然语言 + fenced 动作、消息持久化、会话上下文继承。"""
import asyncio
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.models import User, Project, Document, AIMemory


@pytest.fixture
def store():
    engine = create_engine('sqlite://', poolclass=StaticPool,
                           connect_args={'check_same_thread': False})
    from app.models.project_agent import AgentRun
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([User(id=1, username='owner', is_active=True),
                    User(id=2, username='other', is_active=True)])
        db.add_all([Project(id=1, owner_id=1, title='Novel'),
                    Project(id=2, owner_id=2, title='Private')])
        db.add_all([Document(id=1, project_id=1, title='One', content=[
            {'id': 'b1', 'type': 'paragraph', 'content': 'old hero', 'props': {}}]),
            Document(id=2, project_id=2, title='Secret', content=[])])
        db.add(AIMemory(project_id=1, notes='old notes'))
        db.commit()
    yield factory
    engine.dispose()


def action(tool, **args):
    return {'tool': tool, 'args': args}


def fenced(action_obj, prose='好的，我来处理。'):
    return f"{prose}\n```json\n{json.dumps(action_obj, ensure_ascii=False)}\n```"


def execute(store, replies, instruction='帮我把主角名字改一下', conversation_id=None, user_id=1, project_id=1):
    """replies: list[str]，按轮次返回的模型输出。返回 (run_id, calls)。"""
    from app.services.project_agent_service import create_run, claim_run, execute_run
    with store() as db:
        run = create_run(db, user_id, project_id, instruction, conversation_id)
        run_id, conv = run.id, run.conversation_id
    calls = []

    async def model(messages, **kwargs):
        calls.append(messages)
        # 校验增量回调可调用（注入模型也收到 on_delta）
        if 'on_delta' in kwargs and kwargs['on_delta']:
            kwargs['on_delta']('流式')
        return replies[min(len(calls) - 1, len(replies) - 1)]

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    return run_id, conv, calls


def test_chat_style_turns_apply_and_messages_persisted(store):
    """对话形态：自然语言 + fenced 动作；消息落库；finish 后自动写入。"""
    from app.services.project_agent_service import get_run, transition
    replies = [
        fenced(action('read_document', document_id=1), '我先读一下第一章。'),
        fenced(action('propose_document_patch', document_id=1, block_id='b1',
                      old_text='old', new_text='new', reason='改名'), '找到一处，先暂存修改。'),
        fenced(action('finish', answer='改完了，等你确认'), '完成了，请查看变更。',
               ),
    ]
    # 第三个 finish 不带 fenced 包装，验证 fence 可选
    replies[2] = '完成了，请查看变更。\n```json\n{"tool": "finish", "args": {"answer": "改完了，等你确认"}}\n```'
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert db.get(Document, 1).content[0]['content'] == 'new hero'
        roles = [(m['role'], m['content'][:20]) for m in run.messages]
        assert roles[0][0] == 'user'
        assistant_texts = [m['content'] for m in run.messages if m['role'] == 'assistant']
        assert any('我先读一下第一章' in t for t in assistant_texts)
        assert any('完成了' in t for t in assistant_texts)
        transition(db, 1, 1, run_id, 'revert')
        assert db.get(Document, 1).content[0]['content'] == 'old hero'


def test_clarification_finishes_explicitly_with_message(store):
    """澄清需求须显式 finish，避免把进度说明误当成完成。"""
    from app.services.project_agent_service import get_run
    question = '我需要确认一下：只改正文，不动设定，对吗？'
    replies = [fenced(action('finish', answer=question), question)]
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'completed'
        assert run.changes == []
        assert '只改正文' in (run.answer or '')
        assistant_texts = [m['content'] for m in run.messages if m['role'] == 'assistant']
        assert any('只改正文' in t for t in assistant_texts)


def test_progress_only_reply_continues_reading_and_proposing(store):
    """读文前漏发动作不能使章节扩写任务提前完成。"""
    from app.services.project_agent_service import get_run
    replies = [
        '先读原文和第一章。',
        fenced(action('read_document', document_id=1), '现在读取正文。'),
        '读完了，接下来拆分并扩写章节。',
        fenced(action('propose_create_document', title='新增章节', text='扩写内容', reason='拆分扩写')),
        fenced(action('finish', answer='已生成扩写提案，请确认。')),
    ]
    run_id, _, calls = execute(store, replies, instruction='把现有章节拆细并扩写')
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert len(run.changes) == 1
        assert len(calls) == len(replies)
        assert any('先读原文' in m['content'] for m in run.messages)
        assert [e['type'] for e in run.events].count('finish') == 1
        assert db.query(Document).filter_by(project_id=1).count() == 2


def test_repeated_progress_without_actions_fails_instead_of_completing(store):
    from app.services.project_agent_service import get_run
    run_id, _, calls = execute(store, ['先读原文和第一章。'])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert '工具动作' in run.error
        assert len(calls) == 3
        assert not any(e['type'] == 'finish' for e in run.events)


def test_conversation_context_inherited_by_next_run(store):
    """同一会话的后续 run 能看到前轮 assistant 消息。"""
    run_id, conv, _ = execute(
        store,
        [json.dumps(action('finish', answer='前轮结论：主角应改名为林远'), ensure_ascii=False)],
        instruction='第一轮：总结设定', conversation_id=None)
    run2_id, _, calls = execute(
        store,
        [json.dumps(action('finish', answer='收到'), ensure_ascii=False)],
        instruction='第二轮：还记得你刚才的结论吗？', conversation_id=conv)
    with store() as db:
        from app.services.project_agent_service import get_run
        assert get_run(db, 1, 1, run2_id).status == 'completed'
    flattened = json.dumps(calls[0], ensure_ascii=False)
    assert '前轮结论：主角应改名为林远' in flattened


def test_invalid_fence_json_fails_run(store):
    """代码块修不出带 tool 的动作 → 重试耗尽后 failed，不产生提案。"""
    from app.services.project_agent_service import get_run
    # 可修复的脏 JSON（如 {"tool":"finish", broken}）会走 json_repair 成功；
    # 这里用修不出 tool 字段的内容，验证仍会失败。
    run_id, _, _ = execute(store, ['我来操作。\n```json\n{definitely not:::}\n```'])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert run.changes == []
        assert 'tool' in (run.error or '')


def test_uppercase_fence_marker_recognized(store):
    """```JSON 大写围栏也能解析为动作（模型常这样写）。"""
    from app.services.project_agent_service import get_run
    replies = [
        '我先读一下原文。\n```JSON\n{"tool": "read_document", "args": {"document_id": 1}}\n```',
        json.dumps(action('finish', answer='读完了'), ensure_ascii=False),
    ]
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'completed'


def test_midtask_narration_does_not_end_run(store):
    """任务中途的纯说明文字（漏发工具动作）不结束任务：纠正后继续，直到 finish。"""
    from app.services.project_agent_service import get_run
    replies = [
        fenced(action('read_document', document_id=1), '先读原文和第一章。'),
        '我注意到第一章结尾适合拆分，正在确认衔接点。',
        json.dumps(action('finish', answer='拆分点已确认'), ensure_ascii=False),
    ]
    run_id, _, calls = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'completed'
        assert len(calls) == 3  # 说明文字触发了一次纠正续跑


def test_memory_patch_before_mismatch_auto_corrected(store):
    """before 与 outline 当前值不一致（模型回显偏差）→ 自动以真实值纠正，任务不失败。"""
    from app.services.project_agent_service import get_run, transition
    # 给项目设置一个结构化 outline
    with store() as db:
        db.query(AIMemory).filter_by(project_id=1).one().outline = [
            {'title': '第一章', 'description': '开端'},
            {'title': '第二章', 'description': '发展'},
        ]
        db.commit()
    replies = [
        json.dumps(action('read_memory'), ensure_ascii=False),
        # 模型回显的 before 是“凭记忆写的简化版”，与真实值不完全一致
        json.dumps(action('propose_memory_patch', field='outline',
                          before=[{'title': '第一章'}],  # 偏差：缺 description、少一章
                          after=[{'title': '第一章', 'description': '开端'},
                                 {'title': '第二章', 'description': '发展'},
                                 {'title': '第三章', 'description': '高潮'}],
                          reason='扩展大纲'), ensure_ascii=False),
        json.dumps(action('finish', answer='大纲已扩展'), ensure_ascii=False),
    ]
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        change = run.changes[0]
        # 基线被纠正为真实当前值，而不是模型回显的偏差值
        assert change['before'] == [{'title': '第一章', 'description': '开端'},
                                    {'title': '第二章', 'description': '发展'}]
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        assert len(memory.outline) == 3
        transition(db, 1, 1, run_id, 'revert')
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        assert memory.outline == change['before']


def test_memory_patch_conflict_check_still_sound(store):
    """残留 proposed 时若设定已被人改，apply 仍 409 且不落库。"""
    import pytest as _pytest
    from fastapi import HTTPException
    from app.models.project_agent import AgentRun
    from app.services.project_agent_service import transition
    with store() as db:
        run = AgentRun(
            user_id=1,
            project_id=1,
            conversation_id='mem-conflict',
            instruction='done',
            status='proposed',
            changes=[{
                'id': 'c1',
                'kind': 'memory_patch',
                'field': 'notes',
                'before': 'old notes',
                'after': 'new notes',
                'reason': 'x',
            }],
        )
        db.add(run)
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        memory.notes = 'human edited'
        db.commit()
        run_id = run.id
        with _pytest.raises(HTTPException) as err:
            transition(db, 1, 1, run_id, 'apply')
        assert err.value.status_code == 409
        assert db.query(AIMemory).filter_by(project_id=1).one().notes == 'human edited'


def test_recoverable_violation_recovers(store):
    """未先读就补丁 → 错误反馈给模型，自行纠正（先读再补）后任务继续成功。"""
    from app.services.project_agent_service import get_run
    replies = [
        # 第 1 轮：直接补丁，违规（未 read_document）
        json.dumps(action('propose_document_patch', document_id=1, block_id='b1',
                          old_text='old', new_text='new', reason='改名'), ensure_ascii=False),
        # 第 2 轮：读到反馈后先读文档
        json.dumps(action('read_document', document_id=1), ensure_ascii=False),
        # 第 3 轮：重新提案成功
        json.dumps(action('propose_document_patch', document_id=1, block_id='b1',
                          old_text='old', new_text='new', reason='改名'), ensure_ascii=False),
        json.dumps(action('finish', answer='改名完成'), ensure_ascii=False),
    ]
    run_id, _, calls = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert len(run.changes) == 1
        assert len(calls) == 4
        assert db.get(Document, 1).content[0]['content'] == 'new hero'
    # 第 2 轮的模型输入里包含违规反馈（带 error 的观察）
    feedback = [json.loads(m['content']) for m in calls[1] if m['role'] == 'user'
                and 'UNTRUSTED_OBSERVATION' in m['content']]
    assert any(obs.get('error') and 'read_document' in str(obs.get('error')) for obs in feedback)


def test_persistent_violation_fails_run(store):
    """反复犯同一个可纠正违规（3 次）→ run failed 且不留提案（契约要求）。"""
    from app.services.project_agent_service import get_run
    replies = [json.dumps(action('propose_document_patch', document_id=1, block_id='b1',
                                 old_text='old', new_text='x', reason='y'), ensure_ascii=False)]
    run_id, _, calls = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert run.changes == []
        assert len(calls) == 3  # 两次反馈机会 + 第三次判失败


def test_finish_without_answer_uses_narration(store):
    """finish 缺 answer 参数（常见模型疏漏）→ 用当轮自然语言回复兜底，任务正常完成。"""
    from app.services.project_agent_service import get_run
    # fenced finish 带说明文字但 args 为空 / 缺 answer → answer 兜底为说明文字
    replies = [
        '关于导出：我没有文件导出功能，可以把内容整理成新文档提案。\n```json\n{"tool": "finish", "args": {}}\n```',
    ]
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'completed'
        assert '导出' in (run.answer or '')


def test_pure_json_still_supported(store):
    """契约形态：纯 JSON 动作（无自然语言）继续可用。"""
    from app.services.project_agent_service import get_run
    replies = [
        json.dumps(action('read_document', document_id=1), ensure_ascii=False),
        json.dumps(action('read_memory'), ensure_ascii=False),
        json.dumps(action('propose_memory_patch', field='notes', before='old notes',
                          after='new notes', reason='x'), ensure_ascii=False),
        json.dumps(action('finish', answer='done'), ensure_ascii=False),
    ]
    run_id, _, _ = execute(store, replies)
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert db.query(AIMemory).filter_by(project_id=1).one().notes == 'new notes'
        # 无自然语言时 finish 答案作为 assistant 消息呈现
        assistant_texts = [m['content'] for m in run.messages if m['role'] == 'assistant']
        assert 'done' in assistant_texts


def test_parse_action_repairs_unescaped_quotes_in_fenced_json():
    """大字段补丁里常见未转义引号：应用 json_repair 后仍能解析为合法动作。"""
    from app.services.project_agent_service import _parse_action_and_message

    broken = (
        '接下来丰富 characters。\n'
        '```json\n'
        '{"tool":"propose_memory_patch","args":{"field":"characters","before":[],'
        '"after":[{"name":"林梦","description":"他说"想做个好梦""}],"reason":"添加角色"}}\n'
        '```'
    )
    action_obj, message = _parse_action_and_message(broken)
    assert action_obj['tool'] == 'propose_memory_patch'
    assert action_obj['args']['field'] == 'characters'
    assert '想做个好梦' in action_obj['args']['after'][0]['description']
    assert message.startswith('接下来丰富')


def test_parse_action_accepts_unclosed_fence_when_json_complete():
    """缺结尾 ``` 但 JSON 完整时仍应接受（模型偶发漏写闭合围栏）。"""
    from app.services.project_agent_service import _parse_action_and_message

    raw = (
        '先更新人物。\n'
        '```json\n'
        '{"tool":"propose_memory_patch","args":{"field":"characters","before":[],'
        '"after":[{"name":"Joy"}],"reason":"加人"}}'
    )
    action_obj, message = _parse_action_and_message(raw)
    assert action_obj['tool'] == 'propose_memory_patch'
    assert action_obj['args']['field'] == 'characters'
    assert message.startswith('先更新人物')


def test_parse_action_rejects_truncated_unclosed_json():
    """JSON 半截被截断：给出可纠正的截断提示，而非含糊的「回复被中止」。"""
    from app.services.project_agent_tools import ToolViolation
    from app.services.project_agent_service import _parse_action_and_message
    import pytest

    raw = (
        '先更新故事线。\n'
        '```json\n'
        '{"tool":"propose_memory_patch","args":{"field":"storyline","after":"很长的冲突'
    )
    with pytest.raises(ToolViolation) as exc:
        _parse_action_and_message(raw)
    assert '截断' in str(exc.value) or '未闭合' in str(exc.value)
    assert '缩小' in str(exc.value)


def test_parse_action_repairs_trailing_comma_in_pure_json():
    from app.services.project_agent_service import _parse_action_and_message

    action_obj, message = _parse_action_and_message(
        '{"tool":"finish","args":{"answer":"完成了",}}'
    )
    assert action_obj == {'tool': 'finish', 'args': {'answer': '完成了'}}
    assert message is None


def test_parse_action_repairs_rewrite_with_unescaped_inner_quotes():
    """propose_block_rewrite 的 new_content 含未转义引号时仍应可解析。"""
    from app.services.project_agent_service import _parse_action_and_message

    broken = (
        '开始扩写。\n'
        '```json\n'
        '{"tool":"propose_block_rewrite","args":{"document_id":1,"block_id":"b1",'
        '"new_content":"他说"你好"然后离开","reason":"扩写"}}\n'
        '```'
    )
    action_obj, message = _parse_action_and_message(broken)
    assert action_obj['tool'] == 'propose_block_rewrite'
    assert '你好' in action_obj['args']['new_content']
    assert message.startswith('开始扩写')


def test_illegal_json_feedback_includes_raw_and_can_recover(store):
    """脏 JSON / 非法参数重试时回传原文；下一轮修好后仍可完成。"""
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run

    with store() as db:
        run = create_run(
            db, 1, 1, "扩写选中段", None,
            focus={"document_id": 1, "selection": "old hero", "block_ids": ["b1"]},
        )
        run_id = run.id
    calls = []

    async def model(messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            # 修不出 tool 的残缺围栏 → ToolViolation；须把原文回传给下一轮
            return '先改。\n```json\n{definitely not:::}\n```'
        blob = json.dumps(messages, ensure_ascii=False)
        assert 'definitely not:::' in blob
        assert '不是合法 JSON' in blob or '动作代码块' in blob or '缺少 tool' in blob
        if len(calls) == 2:
            return json.dumps({
                'tool': 'propose_block_rewrite',
                'args': {
                    'document_id': 1,
                    'block_id': 'b1',
                    'new_content': 'new hero expanded',
                    'reason': 'expand',
                },
            }, ensure_ascii=False)
        return json.dumps({'tool': 'finish', 'args': {'answer': '已扩写'}}, ensure_ascii=False)

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'applied'
        assert run.changes[0]['after'] == 'new hero expanded'
        assert db.get(Document, 1).content[0]['content'] == 'new hero expanded'


def test_default_model_falls_back_to_non_stream_on_empty(monkeypatch):
    """流式连续空响应时回退非流式，避免整次任务直接失败。"""
    from app.services import project_agent_service as svc
    import app.core.ai_client as ai_mod

    class _FakeClient:
        def __init__(self):
            self.stream_calls = 0
            self.chat_calls = 0

        async def stream_completion(self, *args, **kwargs):
            self.stream_calls += 1
            if False:  # keep async-generator type
                yield ""

        async def chat_completion(self, *args, **kwargs):
            self.chat_calls += 1
            return '{"tool":"finish","args":{"answer":"ok"}}'

    fake = _FakeClient()
    monkeypatch.setattr(ai_mod, "ai_client", fake)

    async def _sleep(_):
        return None

    monkeypatch.setattr(svc.asyncio, "sleep", _sleep)

    text = asyncio.run(svc.default_model([{"role": "user", "content": "hi"}]))
    assert '"tool"' in text
    assert fake.stream_calls == 3
    assert fake.chat_calls == 1


def test_empty_model_response_retries_then_can_finish(store):
    """execute_run 遇到空响应会反馈重试，后续正常动作仍可完成。"""
    from app.services.project_agent_service import create_run, claim_run, execute_run, get_run

    sequence = [
        RuntimeError("[错误] 模型未返回内容"),
        json.dumps(action("finish", answer="荒诞方向已记下"), ensure_ascii=False),
    ]
    with store() as db:
        run = create_run(db, 1, 1, "荒诞搞笑", None)
        run_id = run.id
    calls = {"n": 0}

    async def model(messages, **kwargs):
        idx = calls["n"]
        calls["n"] += 1
        item = sequence[min(idx, len(sequence) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "completed"
        assert "荒诞" in (run.answer or "")


def test_empty_model_exhausted_soft_finishes_not_failed(store):
    """空响应耗尽重试应软结束（completed），不要 failed +「模型调用失败」。"""
    from app.services.project_agent_service import (
        MAX_EMPTY_MODEL_RETRIES,
        create_run,
        claim_run,
        execute_run,
        get_run,
    )

    with store() as db:
        run = create_run(db, 1, 1, "核查设定落盘状态", None)
        run_id = run.id

    async def model(messages, **kwargs):
        raise RuntimeError("[错误] 模型未返回内容")

    claim = claim_run(store)
    asyncio.run(execute_run(store, claim, model))
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == "completed"
        assert not (run.error or "").startswith("模型调用失败")
        assert "拆小" in (run.answer or "") or "空响应" in (run.answer or "") or "可用内容" in (run.answer or "")
        # 预读后仍会多次空响应；次数应覆盖 MAX_EMPTY_MODEL_RETRIES+1
        assert MAX_EMPTY_MODEL_RETRIES >= 1


def test_message_content_falls_back_to_reasoning():
    from app.core.ai_client import AIClient
    from types import SimpleNamespace

    msg = SimpleNamespace(content="", reasoning_content='先看文档\n```json\n{"tool":"list_project","args":{}}\n```')
    text = AIClient._message_content(msg)
    assert "list_project" in text

    parts = SimpleNamespace(content=[{"type": "text", "text": "你好"}], reasoning_content="ignore")
    assert AIClient._message_content(parts) == "你好"
