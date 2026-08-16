#!/usr/bin/env python3
"""CI helper: server smoke test against PostgreSQL using TestClient."""
import os

os.environ['DJ_AI_OS_DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/dj_ai_os_test'
os.environ['DJ_AI_OS_INIT_DB'] = 'true'
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'

from fastapi.testclient import TestClient
from app.server.run import app

with TestClient(app) as client:
    r = client.get('/health')
    assert r.status_code == 200, f'Health check failed: {r.status_code} {r.text}'
    assert r.json().get('ok') is True
    print('Server health: OK')
    r2 = client.get('/api/update/manifest')
    print(f'Manifest endpoint: {r2.status_code} (expected 200 or 500)')
    from app.license.license_manager import LicenseManager
    from app.license.entitlements import EntitlementManager
    print('License/Entitlement imports: OK')