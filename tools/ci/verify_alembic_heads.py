#!/usr/bin/env python3
"""CI helper: verify alembic has exactly one head against PostgreSQL."""
import os

os.environ['DJ_AI_OS_DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/dj_ai_os_test'
from alembic.config import Config
from alembic.script import ScriptDirectory

cfg = Config('alembic.ini')
cfg.set_main_option('script_location', 'app/server/db/migrations')
cfg.set_main_option('sqlalchemy.url', os.environ['DJ_AI_OS_DATABASE_URL'])
cfg.set_main_option('prepend_sys_path', '.')
cfg.config_file_name = 'alembic.ini'

heads = ScriptDirectory.from_config(cfg).get_heads()
print('Alembic heads:', heads)
assert len(heads) == 1, f'Expected single head, got multiple: {heads}'
# Accept any single head revision (current is 0002_company_revoked_deactivated)
print(f'Single head verified: {heads[0]}')
