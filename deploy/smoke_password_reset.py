"""Disposable recovery integration test with real SMTP to Resend's test sink.

Run inside the configured API container via stdin. No human recipient, password,
reset link, or provider credential is printed. Synthetic records are deleted.
The HTTP transport is TestClient; SMTP uses the real configured service.
"""
import json
import os
import secrets
import uuid
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from app import mailer
from app.main import app

assert os.environ.get('SMTP_HOST') == 'smtp.resend.com', 'This test requires Resend test recipients.'
url = os.environ['APP_URL']
headers = {'Origin': url}
email = 'delivered+candoc-reset-' + uuid.uuid4().hex[:12] + '@resend.dev'
old_password, new_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
captured = []
notifications = []
original = mailer.send_password_reset
original_changed = mailer.send_password_changed


def capture_and_deliver(recipient, link):
    assert recipient == email
    assert link.startswith(url + '/reset-password#token=')
    original(recipient, link)
    captured.append(parse_qs(urlsplit(link).fragment)['token'][0])


mailer.send_password_reset = capture_and_deliver


def capture_notification(recipient):
    assert recipient == email
    original_changed(recipient)
    notifications.append(True)


mailer.send_password_changed = capture_notification
registered = False
with TestClient(app, base_url=url, headers=headers) as first, TestClient(app, base_url=url, headers=headers) as second:
    try:
        response = first.post('/api/auth/register', json={'email': email, 'password': old_password,
                                                        'name': 'Disposable Recovery Test', 'role': 'candidate'})
        assert response.status_code == 201
        registered = True
        assert second.post('/api/auth/login', json={'email': email, 'password': old_password}).status_code == 200
        response = first.post('/api/auth/forgot-password', json={'email': email})
        assert response.status_code == 202
        assert len(captured) == 1, 'SMTP did not accept the reset email'
        assert captured[0] not in response.text
        response = first.post('/api/auth/reset-password', json={'token': captured[0], 'password': new_password})
        assert response.status_code == 200
        assert notifications == [True], 'SMTP did not accept the password-change notification'
        assert first.get('/api/auth/me').json()['user'] is None
        assert second.get('/api/auth/me').json()['user'] is None
        assert first.post('/api/auth/reset-password', json={'token': captured[0], 'password': new_password}).status_code == 400
        assert first.post('/api/auth/login', json={'email': email, 'password': old_password}).status_code == 401
        assert first.post('/api/auth/login', json={'email': email, 'password': new_password}).status_code == 200
        print(json.dumps({'recovery_workflow': 'passed', 'real_smtp_reset_email': 'accepted',
                          'real_smtp_changed_notification': 'accepted',
                          'recipient': 'Resend simulated-delivery test sink', 'old_password': 'rejected',
                          'new_password': 'accepted', 'previous_sessions': 'revoked', 'token_replay': 'rejected'}))
    finally:
        mailer.send_password_reset = original
        mailer.send_password_changed = original_changed
        if registered:
            first.post('/api/auth/login', json={'email': email, 'password': new_password if captured else old_password})
            # On a test failure before reset, try the original password for cleanup.
            if first.get('/api/auth/me').json()['user'] is None:
                first.post('/api/auth/login', json={'email': email, 'password': old_password})
            assert first.delete('/api/account').status_code == 200, 'Synthetic account cleanup failed'
            print(json.dumps({'synthetic_account_cleanup': 'passed'}))
