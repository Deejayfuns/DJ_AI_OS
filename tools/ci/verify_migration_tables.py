#!/usr/bin/env python3
"""CI helper: verify all 7 expected tables exist after migration."""
import os

os.environ['DJ_AI_OS_DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/dj_ai_os_test'
from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ['DJ_AI_OS_DATABASE_URL'].replace('+asyncpg', ''), future=True)
tables = set(inspect(engine).get_table_names())
expected = {'users', 'licenses', 'machine_activations', 'subscriptions', 'webhook_events', 'audit_log', 'alembic_version'}
missing = expected - tables
assert not missing, f'Missing tables: {missing}'
print('All 7 tables present:', sorted(tables))
engine.dispose()
