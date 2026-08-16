#!/usr/bin/env python3
"""CI helper: run alembic upgrade head against PostgreSQL."""
import os

os.environ['DJ_AI_OS_DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/dj_ai_os_test'
from alembic.config import Config
from alembic import command

cfg = Config('alembic.ini')
cfg.set_main_option('script_location', 'app/server/db/migrations')
cfg.set_main_option('sqlalchemy.url', os.environ['DJ_AI_OS_DATABASE_URL'])
cfg.set_main_option('prepend_sys_path', '.')
cfg.config_file_name = 'alembic.ini'

command.upgrade(cfg, 'head')
print('alembic upgrade head: SUCCESS')
