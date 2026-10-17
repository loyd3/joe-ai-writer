"""Additive upgrade for deployments created before conversational messages.

Only adds a nullable column; existing records remain untouched. Rollback of
application code does not require dropping the column.
"""
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError


def ensure_agent_messages(engine):
    """Run before API/standalone workers access the AgentRun ORM model."""
    inspector = inspect(engine)
    if not inspector.has_table('agent_runs'):
        return
    if 'messages' in {column['name'] for column in inspector.get_columns('agent_runs')}:
        return
    try:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE agent_runs ADD COLUMN messages JSON NULL'))
    except DBAPIError:
        # Concurrent application startups may both observe the missing column.
        # Suppress only the expected duplicate-column race, never permissions or
        # other DDL failures: callers must not start the worker on a bad schema.
        if 'messages' not in {column['name'] for column in inspect(engine).get_columns('agent_runs')}:
            raise
