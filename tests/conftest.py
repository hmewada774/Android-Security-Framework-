import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from database.connection import init_db
from backend.app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db(tmp_path_factory):
    # Create temporary isolated test database
    temp_dir = tmp_path_factory.mktemp("asf_test_data")
    test_db_path = temp_dir / "test_asf.db"
    os.environ["ASF_DB_PATH"] = str(test_db_path)
    init_db(test_db_path)
    yield test_db_path

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
