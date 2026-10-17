"""Existing agent_runs tables must be upgraded without deleting runs."""
from sqlalchemy import create_engine, inspect, text


def test_upgrade_existing_agent_messages_is_idempotent():
    from app.services.agent_schema import ensure_agent_messages
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE agent_runs (id VARCHAR(36) PRIMARY KEY, instruction TEXT)'))
        conn.execute(text("INSERT INTO agent_runs VALUES ('old', 'keep me')"))
    ensure_agent_messages(engine)
    ensure_agent_messages(engine)
    assert 'messages' in {c['name'] for c in inspect(engine).get_columns('agent_runs')}
    with engine.begin() as conn:
        assert conn.execute(text('SELECT instruction, messages FROM agent_runs')).one() == ('keep me', None)
        conn.execute(text("UPDATE agent_runs SET messages = '[]' WHERE id = 'old'"))
    engine.dispose()


def test_upgrade_absent_table_is_noop():
    from app.services.agent_schema import ensure_agent_messages
    engine = create_engine('sqlite://')
    ensure_agent_messages(engine)
    assert not inspect(engine).has_table('agent_runs')
    engine.dispose()
