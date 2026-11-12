import os
import tempfile

TEST_DIR = tempfile.TemporaryDirectory(prefix='candock-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + TEST_DIR.name + '/test.db'
os.environ['UPLOAD_DIR'] = TEST_DIR.name + '/resumes'
os.environ['APP_URL'] = 'http://testserver'
os.environ['APP_ENV'] = 'test'
os.environ['COOKIE_SECURE'] = 'false'

import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app
from app.security import _buckets


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _buckets.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app, headers={'Origin': 'http://testserver'}) as client:
        yield client


@pytest.fixture
def other_client():
    with TestClient(app, headers={'Origin': 'http://testserver'}) as client:
        yield client
