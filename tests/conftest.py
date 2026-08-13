import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def setup_e2e_data():
    if os.getenv("RUN_EXTERNAL_E2E") != "1":
        pytest.skip("External Supabase E2E is opt-in; set RUN_EXTERNAL_E2E=1.")
    pytest.fail("Use scripts/seed_integration_test.sql in a dedicated test project before external E2E.")
