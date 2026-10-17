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
    """对话形态：自然语言 + fenced 动作；消息落库；apply 语义不变。"""
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
        assert run.status == 'proposed'
        assert db.get(Document, 1).content[0]['content'] == 'old hero'  # 未批准前不落库
        roles = [(m['role'], m['content'][:20]) for m in run.messages]
        assert roles[0][0] == 'user'
        assistant_texts = [m['content'] for m in run.messages if m['role'] == 'assistant']
        assert any('我先读一下第一章' in t for t in assistant_texts)
        assert any('完成了' in t for t in assistant_texts)
        transition(db, 1, 1, run_id, 'apply')
        assert db.get(Document, 1).content[0]['content'] == 'new hero'


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
        assert run.status == 'proposed'
        assert len(run.changes) == 1
        assert len(calls) == len(replies)
        assert any('先读原文' in m['content'] for m in run.messages)
        assert [e['type'] for e in run.events].count('finish') == 1
        assert db.query(Document).filter_by(project_id=1).count() == 1


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
    """代码块里的动作非法 JSON → run failed，不产生提案。"""
    from app.services.project_agent_service import get_run
    run_id, _, _ = execute(store, ['我来操作。\n```json\n{"tool": "finish", broken}\n```'])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'failed'
        assert run.changes == []


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
        assert run.status == 'proposed'
        # 无自然语言时 finish 答案作为 assistant 消息呈现
        assistant_texts = [m['content'] for m in run.messages if m['role'] == 'assistant']
        assert 'done' in assistant_texts
