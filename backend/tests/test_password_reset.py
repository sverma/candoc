import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app import mailer
from app.database import SessionLocal
from app.main import app
from app.models import AuthSession, PasswordReset, User, now
from app.security import hash_password, token_hash

EMAIL = 'reset@example.com'
OLD = 'old-password-secure-enough'
NEW = ' new-password-keeps-spaces '


def register(client):
    result = client.post('/api/auth/register', json={'email': EMAIL, 'password': OLD, 'name': 'Reset Tester', 'role': 'candidate'})
    assert result.status_code == 201, result.text
    return result.json()['user']


@pytest.fixture
def deliveries(monkeypatch):
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_FROM', 'security@example.com')
    monkeypatch.delenv('SMTP_USERNAME', raising=False)
    monkeypatch.delenv('SMTP_PASSWORD', raising=False)
    messages = []
    monkeypatch.setattr(mailer, 'send_password_reset', lambda address, url: messages.append((address, url)))
    monkeypatch.setattr(mailer, 'send_password_changed', lambda address: None)
    return messages


def request_token(client, deliveries):
    result = client.post('/api/auth/forgot-password', json={'email': EMAIL})
    assert result.status_code == 202, result.text
    url = deliveries[-1][1]
    assert url.startswith('http://testserver/reset-password#token=')
    token = parse_qs(urlsplit(url).fragment)['token'][0]
    assert token not in result.text
    return token


def test_reset_revokes_every_session_and_does_not_auto_login(client, other_client, deliveries):
    user = register(client)
    assert other_client.post('/api/auth/login', json={'email': EMAIL, 'password': OLD}).status_code == 200
    token = request_token(client, deliveries)
    with SessionLocal() as db:
        stored = db.scalar(select(PasswordReset).where(PasswordReset.user_id == user['id']))
        assert stored.token_hash == token_hash(token)
        assert token != stored.token_hash
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 2
    assert 'password_resets' not in client.get('/api/account/export').text
    result = client.post('/api/auth/reset-password', json={'token': token, 'password': NEW})
    assert result.status_code == 200, result.text
    assert 'Max-Age=0' in result.headers['set-cookie']
    assert client.get('/api/auth/me').json()['user'] is None
    assert other_client.get('/api/auth/me').json()['user'] is None
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 400
    assert client.post('/api/auth/login', json={'email': EMAIL, 'password': OLD}).status_code == 401
    assert client.post('/api/auth/login', json={'email': EMAIL, 'password': NEW.strip()}).status_code == 401
    assert client.post('/api/auth/login', json={'email': EMAIL, 'password': NEW}).status_code == 200


def test_new_request_invalidates_previous_token(client, deliveries):
    register(client)
    old = request_token(client, deliveries)
    new = request_token(client, deliveries)
    assert old != new
    assert client.post('/api/auth/reset-password', json={'token': old, 'password': NEW}).status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PasswordReset)) == 1
    assert client.post('/api/auth/reset-password', json={'token': new, 'password': NEW}).status_code == 200


def test_expired_wrong_and_password_changed_tokens_rejected(client, deliveries):
    user = register(client)
    token = request_token(client, deliveries)
    assert client.post('/api/auth/reset-password', json={'token': 'x' * 43, 'password': NEW}).status_code == 400
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': 'short'}).status_code == 422
    with SessionLocal() as db:
        db.get(PasswordReset, token_hash(token)).expires_at = now() - dt.timedelta(seconds=1)
        db.commit()
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 400
    current = request_token(client, deliveries)
    with SessionLocal() as db:
        db.get(User, user['id']).password_hash = hash_password('a-changed-password-after-issuance')
        db.commit()
    assert client.post('/api/auth/reset-password', json={'token': current, 'password': NEW}).status_code == 400


def test_missing_smtp_uniformly_unavailable(client, monkeypatch):
    register(client)
    monkeypatch.delenv('SMTP_HOST', raising=False)
    known = client.post('/api/auth/forgot-password', json={'email': EMAIL})
    unknown = client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PasswordReset)) == 0


def test_unknown_email_generic_response_without_mail(client, deliveries):
    register(client)
    known = client.post('/api/auth/forgot-password', json={'email': EMAIL})
    unknown = client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(deliveries) == 1


def test_delivery_failure_generic_ack_and_token_cleanup(client, deliveries, monkeypatch, caplog):
    register(client)

    def failure(address, url):
        raise mailer.MailUnavailable('provider secret containing ' + address + url)

    monkeypatch.setattr(mailer, 'send_password_reset', failure)
    known = client.post('/api/auth/forgot-password', json={'email': EMAIL})
    unknown = client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert EMAIL not in caplog.text
    assert 'token=' not in caplog.text
    assert 'provider secret' not in caplog.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PasswordReset)) == 0


def test_recovery_is_throttled_by_email_and_ip(client, deliveries):
    for _ in range(3):
        assert client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'}).status_code == 202
    assert client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'}).status_code == 429
    for number in range(6):
        assert client.post('/api/auth/forgot-password', json={'email': f'unknown{number}@example.com'}).status_code == 202
    assert client.post('/api/auth/forgot-password', json={'email': 'different@example.com'}).status_code == 429


def test_account_deletion_cascades_recovery_tokens(client, deliveries):
    register(client)
    token = request_token(client, deliveries)
    assert client.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PasswordReset)) == 0
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 400


def test_two_concurrent_submissions_have_one_winner(client, deliveries):
    register(client)
    token = request_token(client, deliveries)

    def submit(number):
        with TestClient(app, headers={'Origin': 'http://testserver'}) as contender:
            return contender.post('/api/auth/reset-password', json={'token': token, 'password': NEW + str(number)}).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(submit, [1, 2]))
    assert sorted(statuses) == [200, 400]


@pytest.mark.parametrize('address', ['victim@example.com\r\nBcc: attack@example.com', 'a@example.com,b@example.com', 'Name <a@example.com>'])
def test_header_injection_rejected_before_mail(client, deliveries, address):
    assert client.post('/api/auth/forgot-password', json={'email': address}).status_code == 422
    assert deliveries == []


def test_mailer_config_requires_encrypted_transport_and_safe_sender(monkeypatch):
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_FROM', 'security@example.com')
    monkeypatch.setenv('SMTP_SECURITY', 'plaintext')
    assert mailer.is_configured() is False
    monkeypatch.setenv('SMTP_SECURITY', 'starttls')
    monkeypatch.setenv('SMTP_FROM', 'security@example.com\r\nBcc: x@example.com')
    assert mailer.is_configured() is False


@pytest.mark.parametrize('security,port', [('starttls', 587), ('ssl', 465)])
def test_mailer_uses_verified_tls_and_fixed_headers(monkeypatch, security, port):
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_FROM', 'security@example.com')
    monkeypatch.setenv('SMTP_SECURITY', security)
    monkeypatch.delenv('SMTP_PORT', raising=False)
    monkeypatch.setenv('SMTP_USERNAME', 'smtp-user')
    monkeypatch.setenv('SMTP_PASSWORD', 'smtp-password')
    events = []

    class FakeSMTP:
        def __init__(self, host, actual_port, timeout, context=None):
            assert host == 'smtp.example.com' and actual_port == port and timeout == 12
            if security == 'ssl':
                assert context.check_hostname is True
            events.append('connect')

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            events.append('ehlo')

        def starttls(self, context):
            assert context.check_hostname is True
            events.append('tls')

        def login(self, username, password):
            assert (username, password) == ('smtp-user', 'smtp-password')
            events.append('login')

        def send_message(self, message):
            assert message['To'] == EMAIL
            assert message['From'] == 'Candoc <security@example.com>'
            assert message['Bcc'] is None
            assert 'https://candoc.org/reset-password#token=test-token' in message.get_content()
            events.append('send')
            return {}

    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL' if security == 'ssl' else 'SMTP', FakeSMTP)
    mailer.send_password_reset(EMAIL, 'https://candoc.org/reset-password#token=test-token')
    assert events == (['connect', 'ehlo', 'tls', 'ehlo', 'login', 'send'] if security == 'starttls' else ['connect', 'login', 'send'])


def test_successful_reset_sends_changed_notification(client, deliveries, monkeypatch):
    register(client)
    token = request_token(client, deliveries)
    changed = []
    monkeypatch.setattr(mailer, 'send_password_changed', lambda address: changed.append(address))
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 200
    assert changed == [EMAIL]


def test_failed_change_notification_does_not_undo_reset(client, deliveries, monkeypatch, caplog):
    register(client)
    token = request_token(client, deliveries)

    def fail(address):
        raise mailer.MailUnavailable('Sensitive provider text ' + address)

    monkeypatch.setattr(mailer, 'send_password_changed', fail)
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 200
    assert EMAIL not in caplog.text
    assert 'Sensitive provider text' not in caplog.text
    assert client.post('/api/auth/login', json={'email': EMAIL, 'password': NEW}).status_code == 200
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW}).status_code == 400
