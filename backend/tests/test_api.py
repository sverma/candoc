import io
import zipfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app, UPLOAD_DIR
from app.models import User
from app.security import COOKIE_NAME

PASSWORD = 'sufficiently-strong-password'
RESUME = '''Experience\nSenior software engineer, Acme, 2020-2025.
Built Python and PostgreSQL APIs serving 20000 requests each day.
Reduced API latency by 35 percent through query profiling and caching.
Led a team of 4 engineers shipping payments and observability projects.
Projects\nDesigned an open source queue with retry logic and 90 percent test coverage.
Skills\nPython, PostgreSQL, Docker, TypeScript, Redis.
Education\nEngineering degree.'''


def register(client, email='candidate@example.com', role='candidate'):
    data = {'email': email, 'password': PASSWORD, 'name': 'Avery Engineer', 'role': role}
    if role == 'company':
        data['company_name'] = 'Example Company'
    response = client.post('/api/auth/register', json=data)
    assert response.status_code == 201, response.text
    return response.json()['user']


def publish(client):
    response = client.put('/api/profile', json={'headline': 'Platform engineer', 'skills': ['Python', 'PostgreSQL'], 'location': 'Bengaluru', 'visible': True})
    assert response.status_code == 200, response.text
    uploaded = client.post('/api/profile/resume', files={'file': ('resume.txt', RESUME.encode(), 'text/plain')})
    assert uploaded.status_code == 200, uploaded.text
    analyzed = client.post('/api/profile/analyze')
    assert analyzed.status_code == 200, analyzed.text
    return analyzed.json()['profile']


def test_cookie_auth_validation_and_logout(client):
    assert client.get('/api/auth/me').json() == {'user': None}
    assert client.post('/api/auth/register', json={'email': 'bad', 'password': 'tiny', 'name': 'A', 'role': 'candidate'}).status_code == 422
    user = register(client)
    assert user['email'] == 'candidate@example.com'
    assert client.cookies.get(COOKIE_NAME)
    assert client.get('/api/auth/me').json()['user']['id'] == user['id']
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/auth/me').json()['user'] is None
    assert client.post('/api/auth/login', json={'email': user['email'], 'password': 'wrong'}).status_code == 401
    response = client.post('/api/auth/login', json={'email': user['email'].upper(), 'password': PASSWORD})
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']


def test_private_profile_and_contact_consent(client, other_client):
    register(client)
    private_profile = client.get('/api/profile').json()['profile']
    register(other_client, 'company@example.com', 'company')
    assert other_client.get('/api/candidates').json()['candidates'] == []
    assert other_client.get('/api/candidates/' + private_profile['id']).status_code == 404
    profile = publish(client)
    assert 1 <= profile['assessment']['score'] <= 5
    listed = other_client.get('/api/candidates?search=platform&skill=python&location=bengaluru').json()['candidates']
    assert len(listed) == 1
    public = listed[0]
    for key in ['email', 'resume_text', 'resume_filename', 'linkedin_text', 'consent_public_analysis', 'resume_path']:
        assert key not in public
    response = other_client.post('/api/introductions', json={'candidate_id': profile['id'], 'role_title': 'Staff engineer', 'message': 'We would love to discuss our platform engineering opportunity.', 'salary_range': 'INR 30–40 lakh', 'work_mode': 'Remote'})
    assert response.status_code == 201, response.text
    intro = response.json()['introduction']
    assert 'contact_email' not in intro
    assert 'contact_email' not in client.get('/api/introductions').json()['introductions'][0]
    assert other_client.patch('/api/introductions/' + intro['id'], json={'status': 'accepted'}).status_code == 403
    accepted = client.patch('/api/introductions/' + intro['id'], json={'status': 'accepted'})
    assert accepted.status_code == 200
    assert accepted.json()['introduction']['contact_email'] == 'company@example.com'
    assert other_client.get('/api/introductions').json()['introductions'][0]['contact_email'] == 'candidate@example.com'
    assert client.patch('/api/introductions/' + intro['id'], json={'status': 'declined'}).status_code == 409


def test_cross_account_access_and_delete_cascade(client, other_client):
    candidate = register(client)
    profile = publish(client)
    register(other_client, 'company@example.com', 'company')
    intro = other_client.post('/api/introductions', json={'candidate_id': profile['id'], 'role_title': 'Engineer', 'message': 'A meaningful opportunity for your next career step.'}).json()['introduction']
    export = client.get('/api/account/export').json()
    assert export['profile']['resume_text'] == RESUME
    with SessionLocal() as db:
        path = db.get(User, candidate['id']).profile.resume_path
    assert (UPLOAD_DIR / path).exists()
    assert client.delete('/api/account').status_code == 200
    assert not (UPLOAD_DIR / path).exists()
    assert client.get('/api/auth/me').json()['user'] is None
    assert other_client.get('/api/candidates/' + profile['id']).status_code == 404
    assert other_client.get('/api/introductions').json()['introductions'] == []


def test_origin_protection_and_role_isolation(client):
    register(client)
    assert client.put('/api/profile', json={'bio': 'changed'}, headers={'Origin': 'https://evil.example'}).status_code == 403
    client.headers.pop('Origin')
    assert client.put('/api/profile', json={'bio': 'changed'}).status_code == 403
    client.headers['Origin'] = 'http://testserver'
    assert client.post('/api/introductions', json={'candidate_id': 'unknown', 'role_title': 'Role', 'message': 'This message is long enough to pass.'}).status_code == 403
    assert client.get('/api/candidates').json()['candidates'] == []


def test_resume_rejection_and_assessment_invalidation(client):
    register(client)
    assert client.post('/api/profile/analyze').status_code == 400
    assert client.post('/api/profile/resume', files={'file': ('resume.exe', b'MZbad', 'application/octet-stream')}).status_code == 400
    assert client.post('/api/profile/resume', files={'file': ('resume.pdf', b'pretend PDF file that is not really a PDF document', 'application/pdf')}).status_code == 400
    assert client.post('/api/profile/resume', files={'file': ('resume.txt', b'x' * (5 * 1024 * 1024 + 1), 'text/plain')}).status_code == 413
    profile = publish(client)
    assert profile['assessment']
    changed = client.put('/api/profile', json={'skills': ['Go']}).json()['profile']
    assert changed['assessment'] is None
    assert client.put('/api/profile', json={'github_url': 'https://169.254.169.254/latest/meta-data'}).status_code == 422
    assert client.put('/api/profile', json={'github_url': 'https://github.com/a/repo'}).status_code == 422
    assert client.put('/api/profile', json={'linkedin_url': 'https://linkedin.com.evil.example/in/person'}).status_code == 422


def test_public_network_enrichment_requires_consent(client, monkeypatch):
    register(client)
    publish(client)
    client.put('/api/profile', json={'github_url': 'https://github.com/octocat', 'consent_public_analysis': False})
    calls = []

    async def github(url):
        calls.append(url)
        return {'status': 'unavailable', 'url': url, 'detail': 'Test unavailable'}

    monkeypatch.setattr('app.sources.fetch_github_profile', github)
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls == []
    client.put('/api/profile', json={'consent_public_analysis': True})
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls == ['https://github.com/octocat']


def test_unrelated_candidate_cannot_read_or_answer_requests(client, other_client):
    register(client)
    profile = publish(client)
    register(other_client, 'second@example.com')
    assert other_client.get('/api/candidates/' + profile['id']).status_code == 404
    assert other_client.patch('/api/introductions/not-theirs', json={'status': 'accepted'}).status_code == 404


def test_login_rate_limit(client):
    for _ in range(20):
        assert client.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': PASSWORD}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': PASSWORD}).status_code == 429


def test_password_whitespace_is_preserved(client):
    password = ' password-with-spaces '
    assert client.post('/api/auth/register', json={'email': 'spaces@example.com', 'password': password, 'name': 'Whitespace Tester', 'role': 'candidate'}).status_code == 201
    client.post('/api/auth/logout')
    assert client.post('/api/auth/login', json={'email': 'spaces@example.com', 'password': password.strip()}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'spaces@example.com', 'password': password}).status_code == 200


def test_no_public_discovery_without_company_auth(client):
    register(client)
    publish(client)
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/candidates').json()['candidates'] == []
        assert anonymous.get('/api/stats').json()['candidates'] == 1
        assert anonymous.get('/api/health').json()['status'] == 'ok'


def test_public_assessment_redacts_contact_details(client, other_client):
    candidate = register(client)
    profile = publish(client)
    with SessionLocal() as db:
        account = db.get(User, candidate['id'])
        assessment = dict(account.profile.assessment)
        assessment['summary'] = 'Built Python APIs. Contact candidate@example.com or +91 98765 43210.'
        account.profile.assessment = assessment
        db.commit()
    assert 'candidate@example.com' in client.get('/api/profile').json()['profile']['assessment']['summary']
    register(other_client, 'company@example.com', 'company')
    summary = other_client.get('/api/candidates/' + profile['id']).json()['candidate']['assessment']['summary']
    assert 'candidate@example.com' not in summary
    assert '98765' not in summary


def test_external_ai_consent_is_private_and_invalidates_assessment(client, other_client):
    register(client)
    profile = publish(client)
    changed = client.put('/api/profile', json={'consent_external_ai': True}).json()['profile']
    assert changed['consent_external_ai'] is True
    assert changed['assessment'] is None
    register(other_client, 'company@example.com', 'company')
    public = other_client.get('/api/candidates/' + profile['id']).json()['candidate']
    assert 'consent_external_ai' not in public


def test_revoke_ai_consent_during_github_fetch_prevents_provider_call(client, monkeypatch):
    candidate = register(client)
    publish(client)
    client.put('/api/profile', json={'github_url': 'https://github.com/octocat', 'consent_public_analysis': True, 'consent_external_ai': True})
    calls = []

    async def github(url):
        with SessionLocal() as db:
            account = db.get(User, candidate['id'])
            account.profile.consent_external_ai = False
            account.profile.assessment = None
            db.commit()
        return {'status': 'unavailable', 'url': url, 'detail': 'Test unavailable'}

    async def semantic(*args, **kwargs):
        calls.append(True)
        return args[0]

    monkeypatch.setattr('app.sources.fetch_github_profile', github)
    monkeypatch.setattr('app.semantic.enhance_assessment', semantic)
    assert client.post('/api/profile/analyze').status_code == 409
    assert calls == []
    assert client.get('/api/profile').json()['profile']['assessment'] is None


def test_nested_semantic_review_contacts_are_hidden(client, other_client):
    candidate = register(client)
    profile = publish(client)
    with SessionLocal() as db:
        account = db.get(User, candidate['id'])
        assessment = dict(account.profile.assessment)
        assessment['semantic_review'] = {'observations': [{'quote': 'Contact candidate@example.com at +919876543210.', 'interpretation': 'Shared contact candidate@example.com.'}]}
        account.profile.assessment = assessment
        db.commit()
    register(other_client, 'company@example.com', 'company')
    public = other_client.get('/api/candidates/' + profile['id']).json()['candidate']
    serialized = json.dumps(public)
    assert 'candidate@example.com' not in serialized
    assert '9876543210' not in serialized
