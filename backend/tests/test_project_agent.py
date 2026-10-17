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


def test_arbitrary_multistep_staged_patch_memory_apply_revert(store):
    from app.services.project_agent_service import get_run, transition
    run_id, calls = execute(store, [
        action('list_project'), action('read_document', document_id=1),
        patch(), patch('new', 'brave'), action('read_memory'),
        action('propose_memory_patch', field='notes', before='old notes', after='new notes', reason='Consistency'),
        action('finish', answer='Reviewed and prepared coordinated edits')])
    with store() as db:
        run = get_run(db, 1, 1, run_id)
        assert run.status == 'proposed'
        assert len(run.changes) == 2
        assert db.get(Document, 1).content[0]['content'] == 'old hero'
        assert 'brave hero' in json.dumps(calls[-1])
        transition(db, 1, 1, run_id, 'apply')
        assert db.get(Document, 1).content[0] == {
            'id': 'b1', 'type': 'paragraph', 'content': 'brave hero', 'props': {'align': 'left'}}
        transition(db, 1, 1, run_id, 'apply')  # idempotent
        assert db.query(AIMemory).filter_by(project_id=1).one().notes == 'new notes'
        transition(db, 1, 1, run_id, 'revert')
        assert db.get(Document, 1).content[0]['content'] == 'old hero'
        transition(db, 1, 1, run_id, 'revert')


def test_create_and_revert_rejects_edited_created_document(store):
    from app.services.project_agent_service import transition, get_run
    run_id, _ = execute(store, [action('propose_create_document', title='Plan', text='A new plan', reason='Planning'),
                                action('finish', answer='Plan drafted')])
    with store() as db:
        transition(db, 1, 1, run_id, 'apply')
        change = get_run(db, 1, 1, run_id).changes[0]
        doc = db.get(Document, change['target_id'])
        doc.title = 'Human edited'
        db.commit()
        with pytest.raises(HTTPException) as error:
            transition(db, 1, 1, run_id, 'revert')
        assert error.value.status_code == 409
        assert db.get(Document, doc.id).title == 'Human edited'


def test_apply_conflict_is_atomic_including_read_dependencies(store):
    from app.services.project_agent_service import transition
    run_id, _ = execute(store, [action('read_document', document_id=1), patch(),
        action('read_memory'), action('propose_memory_patch', field='notes', before='old notes', after='new', reason='Improve'),
        action('finish', answer='Ready')])
    with store() as db:
        memory = db.query(AIMemory).filter_by(project_id=1).one()
        memory.notes = 'human'
        db.commit()
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
    assert observations[0]['data']['complete'] is False
    assert observations[1]['data']['coverage'] == 'all_project_documents_and_memory_literal'
    assert observations[1]['data']['complete'] is True


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
        assert run.status == ('proposed' if with_changes else 'completed')
        assert run.answer == 'Which character should we focus on?'
        assert run.lease_owner is None
        assert len(calls) == len(replies)
        assert db.query(Document).filter_by(project_id=1).count() == 1


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
