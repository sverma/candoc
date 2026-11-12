import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import mailer, verification
from app.database import SessionLocal
from app.main import app
from app.models import now
from app.security import token_hash
from app.verification_models import EmailVerification
from test_api import register


@pytest.fixture
def deliveries(monkeypatch):
    monkeypatch.setattr(mailer, 'is_configured', lambda: True)
    sent = []
    monkeypatch.setattr(mailer, '_send_message', lambda recipient, subject, body: sent.append((recipient, subject, body)))
    return sent


def request_token(client, deliveries):
    response = client.post('/api/auth/request-verification')
    assert response.status_code == 202, response.text
    body = deliveries[-1][2]
    url = next(line for line in body.splitlines() if line.startswith('http://testserver/'))
    assert url.startswith('http://testserver/verify-email#token=')
    token = parse_qs(urlsplit(url).fragment)['token'][0]
    assert token not in response.text
    return token


def test_verification_hash_single_use_status_and_export(client, other_client, deliveries):
    user = register(client)
    assert user['email_verified'] is False
    assert other_client.post('/api/auth/request-verification').status_code == 401
    token = request_token(client, deliveries)
    assert deliveries[0][0] == user['email']
    with SessionLocal() as db:
        record = db.get(EmailVerification, user['id'])
        assert record.token_hash == token_hash(token)
        assert record.token_hash != token
    assert token not in client.get('/api/account/export').text
    # The link can be opened in another browser without signing that browser in.
    assert other_client.post('/api/auth/verify-email', json={'token': token}).status_code == 200
    assert other_client.get('/api/auth/me').json()['user'] is None
    assert client.get('/api/auth/me').json()['user']['email_verified'] is True
    assert client.get('/api/account/export').json()['user']['email_verified'] is True
    assert client.post('/api/auth/verify-email', json={'token': token}).status_code == 400
    assert client.post('/api/auth/request-verification').json()['email_verified'] is True
    assert len(deliveries) == 1


def test_only_latest_token_and_expiry(client, deliveries):
    user = register(client)
    first = request_token(client, deliveries)
    second = request_token(client, deliveries)
    assert first != second
    assert client.post('/api/auth/verify-email', json={'token': first}).status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EmailVerification)) == 1
        db.get(EmailVerification, user['id']).expires_at = now() - dt.timedelta(seconds=1)
        db.commit()
    assert client.post('/api/auth/verify-email', json={'token': second}).status_code == 400
    assert client.post('/api/auth/verify-email', json={'token': 'x' * 43}).status_code == 400
    assert client.post('/api/auth/verify-email', json={'token': '<script>'}).status_code == 422


def test_mail_failure_invalidates_only_its_token(client, deliveries, monkeypatch):
    user = register(client)
    token = request_token(client, deliveries)
    def fail(*args):
        raise OSError('provider secret must not escape')
    monkeypatch.setattr(mailer, '_send_message', fail)
    verification._deliver(user['id'], user['email'], token, 'stale-hash', 'http://testserver')
    with SessionLocal() as db:
        assert db.get(EmailVerification, user['id']).token_hash == token_hash(token)
    verification._deliver(user['id'], user['email'], token, token_hash(token), 'http://testserver')
    with SessionLocal() as db:
        assert db.get(EmailVerification, user['id']).token_hash is None
    assert client.post('/api/auth/verify-email', json={'token': token}).status_code == 400


def test_unavailable_and_request_rate_limits(client, deliveries, monkeypatch):
    register(client)
    monkeypatch.setattr(mailer, 'is_configured', lambda: False)
    assert client.post('/api/auth/request-verification').status_code == 503
    monkeypatch.setattr(mailer, 'is_configured', lambda: True)
    request_token(client, deliveries)
    request_token(client, deliveries)
    assert client.post('/api/auth/request-verification').status_code == 429


def test_delete_revokes_verification_and_concurrent_consume_once(client, deliveries):
    user = register(client)
    token = request_token(client, deliveries)
    def consume(_):
        with TestClient(app, headers={'Origin': 'http://testserver'}) as browser:
            return browser.post('/api/auth/verify-email', json={'token': token}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(consume, range(2))) == [200, 400]
    assert client.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.get(EmailVerification, user['id']) is None
    assert client.post('/api/auth/verify-email', json={'token': token}).status_code == 400
