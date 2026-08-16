#!/usr/bin/env python3
"""CI helper: verify migrated schema matches SQLAlchemy models column-for-column."""
import os

os.environ['DJ_AI_OS_DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/dj_ai_os_test'
from sqlalchemy import create_engine, inspect
from app.server.db.models import Base

engine = create_engine(os.environ['DJ_AI_OS_DATABASE_URL'].replace('+asyncpg', ''), future=True)
with engine.connect() as conn:
    inspector = inspect(engine)
    model_tables = {t.name for t in Base.metadata.sorted_tables}
    for table in Base.metadata.sorted_tables:
        migrated_cols = {c['name'] for c in inspector.get_columns(table.name)}
        model_cols = {c.name for c in table.columns}
        assert migrated_cols == model_cols, f'Column mismatch in {table.name}: migrated={migrated_cols} model={model_cols}'
print('Schema matches models: PASS')
engine.dispose()
