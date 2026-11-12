"""Public HTTPS introduction/Updates regression with disposable accounts.

Run inside the configured API container via stdin. No email or AI is called.
All synthetic records are removed in finally; no credentials are printed.
"""
import json
import os
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE = os.environ['APP_URL'].rstrip('/')
assert BASE.startswith('https://')
suffix = uuid.uuid4().hex[:12]
password = secrets.token_urlsafe(24)
clients = []


class Client:
    def __init__(self, role, tag):
        self.http = httpx.Client(base_url=BASE, headers={'Origin': BASE}, timeout=30)
        self.registered = False
        clients.append(self)
        self.user = self.call('/auth/register', 'POST', {'email': 'intro-updates-' + suffix + '-' + tag + '@example.invalid',
            'password': password, 'name': 'Disposable Updates ' + tag, 'role': role,
            **({'company_name': 'Disposable Updates Studio ' + tag} if role == 'company' else {})}, expected=201)['user']
        self.registered = True

    def call(self, path, method='GET', data=None, expected=200):
        response = self.http.request(method, '/api' + path, json=data)
        assert response.status_code == expected, method + ' ' + path + ': ' + str(response.status_code)
        return response.json()


try:
    candidate, company, outsider = Client('candidate', 'candidate'), Client('company', 'company'), Client('company', 'outsider')
    profile = candidate.call('/profile', 'PUT', {'visible': True, 'headline': 'Disposable introduction updates regression'})['profile']
    introduction = company.call('/introductions', 'POST', {'candidate_id': profile['id'], 'role_title': 'Disposable update regression',
        'message': 'A synthetic introduction used only to verify the Updates feed. Removed after testing.'}, expected=201)['introduction']
    iid = introduction['id']
    received = candidate.call('/hiring/notifications')
    sent = company.call('/hiring/notifications')
    assert received['unread_count'] == sent['unread_count'] == 1
    notice = received['notifications'][0]
    assert notice['kind'] == 'introduction_received' and notice['introduction_id'] == iid
    assert sent['notifications'][0]['kind'] == 'introduction_sent'
    assert candidate.call('/hiring/dashboard')['counts']['unread_notifications'] == 1
    assert outsider.call('/hiring/notifications') == {'notifications': [], 'unread_count': 0}
    outsider.call('/hiring/notifications/' + notice['id'], 'PATCH', {'read': True}, expected=404)
    candidate.call('/hiring/notifications/' + notice['id'], 'PATCH', {'read': True})
    assert candidate.call('/hiring/notifications')['unread_count'] == 0
    # A repeated repair must preserve the existing event and its read state.
    from app.database import SessionLocal
    from app.models import Introduction
    from app.introduction_updates import record_introduction_sent
    with SessionLocal() as db:
        assert record_introduction_sent(db, db.get(Introduction, iid)) == 0
        db.commit()
    assert candidate.call('/hiring/notifications')['unread_count'] == 0
    def respond(_):
        return candidate.http.patch('/api/introductions/' + iid, json={'status': 'accepted'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(respond, range(2))) == [200, 409]
    candidate.call('/introductions/' + iid, 'PATCH', {'status': 'declined'}, expected=409)
    updates = company.call('/hiring/notifications')
    assert updates['unread_count'] == 2 and len(updates['notifications']) == 2
    assert updates['notifications'][0]['kind'] == 'introduction_accepted'
    assert len(candidate.call('/account/export')['hiring']['notifications']) == 2
    company.call('/hiring/notifications/read-all', 'POST')
    assert company.call('/hiring/dashboard')['counts']['unread_notifications'] == 0
    candidate.call('/account', 'DELETE')
    candidate.registered = False
    assert company.call('/hiring/notifications') == {'notifications': [], 'unread_count': 0}
    print(json.dumps({'introduction_sent_received_updates': 'passed', 'response_and_postgresql_concurrency': 'passed',
        'read_controls_and_dashboard': 'passed', 'recipient_isolation': 'passed', 'idempotent_repair': 'passed',
        'export_and_cascade_deletion': 'passed'}))
finally:
    failures = []
    for client in clients:
        try:
            if client.registered:
                client.call('/account', 'DELETE')
        except Exception:
            failures.append(client.user.get('role', 'unknown') if hasattr(client, 'user') else 'registration')
        finally:
            client.http.close()
    assert not failures, 'Disposable account cleanup failed: ' + ','.join(failures)
    print(json.dumps({'synthetic_account_cleanup': 'passed'}))
