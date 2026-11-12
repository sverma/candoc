import pytest
from sqlalchemy import func, select
from app.database import SessionLocal
from app.models import GitLabConnection
from test_api import register, publish

URL = 'https://gitlab.com/example.dev_user'


def test_gitlab_defaults_persist_export_privacy_and_delete(client, other_client):
    register(client)
    profile = publish(client)
    assert profile['gitlab_url'] == ''
    assert profile['consent_gitlab_analysis'] is False
    updated = client.put('/api/profile', json={'gitlab_url': 'https://gitlab.com/Example.Dev_User/', 'consent_gitlab_analysis': True})
    assert updated.status_code == 200, updated.text
    own = updated.json()['profile']
    assert own['gitlab_url'] == URL and own['consent_gitlab_analysis'] is True
    assert own['assessment'] is None
    assert client.get('/api/profile').json()['profile']['gitlab_url'] == URL
    exported = client.get('/api/account/export').json()['profile']
    assert exported['gitlab_url'] == URL and exported['consent_gitlab_analysis'] is True
    register(other_client, 'company@example.com', 'company')
    public = other_client.get('/api/candidates/' + profile['id']).json()['candidate']
    assert public['gitlab_url'] == URL
    assert 'consent_gitlab_analysis' not in public
    assert other_client.put('/api/profile', json={'gitlab_url': URL}).status_code == 403
    assert client.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(GitLabConnection)) == 0


def test_github_consent_does_not_grant_gitlab_permission(client, monkeypatch):
    register(client)
    publish(client)
    calls = []

    async def gitlab(url):
        calls.append(url)
        return {'status': 'unavailable', 'url': url, 'detail': 'Unavailable.'}

    monkeypatch.setattr('app.gitlab.fetch_gitlab_profile', gitlab)
    client.put('/api/profile', json={'gitlab_url': URL, 'consent_public_analysis': True})
    first = client.post('/api/profile/analyze')
    assert first.status_code == 200, first.text
    assert calls == []
    client.put('/api/profile', json={'consent_gitlab_analysis': True})
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls == [URL]
    client.put('/api/profile', json={'consent_gitlab_analysis': False})
    assert client.get('/api/profile').json()['profile']['assessment'] is None
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls == [URL]


def test_combined_sources_pass_separately_without_changing_rubric(client, monkeypatch):
    register(client)
    baseline = publish(client)['assessment']['score']
    calls = []

    async def github(url):
        calls.append('github')
        return {'status': 'available', 'url': url, 'detail': 'Public GitHub observations.', 'repositories': [], 'evidence': ['GitHub supplementary work description.']}

    async def gitlab(url):
        calls.append('gitlab')
        return {'status': 'available', 'url': url, 'detail': 'Public GitLab observations.', 'repositories': [], 'evidence': ['GitLab supplementary work description.']}

    monkeypatch.setattr('app.sources.fetch_github_profile', github)
    monkeypatch.setattr('app.gitlab.fetch_gitlab_profile', gitlab)
    client.put('/api/profile', json={'github_url': 'https://github.com/octocat', 'consent_public_analysis': True, 'gitlab_url': URL, 'consent_gitlab_analysis': True})
    result = client.post('/api/profile/analyze')
    assert result.status_code == 200, result.text
    assessment = result.json()['profile']['assessment']
    assert assessment['score'] == baseline
    assert {'github', 'gitlab'} <= {item['type'] for item in assessment['sources']}
    assert calls == ['github', 'gitlab']


def test_revoking_gitlab_during_github_wait_prevents_gitlab_and_ai(client, monkeypatch):
    register(client)
    profile = publish(client)
    client.put('/api/profile', json={'github_url': 'https://github.com/octocat', 'consent_public_analysis': True, 'gitlab_url': URL, 'consent_gitlab_analysis': True})
    gitlab_calls, ai_calls = [], []

    async def github(url):
        with SessionLocal() as db:
            db.get(GitLabConnection, profile['id']).consent = False
            db.commit()
        return {'status': 'unavailable'}

    async def gitlab(url):
        gitlab_calls.append(url)
        return {'status': 'unavailable'}

    async def ai(assessment, *args, **kwargs):
        ai_calls.append(True)
        return assessment

    monkeypatch.setattr('app.sources.fetch_github_profile', github)
    monkeypatch.setattr('app.gitlab.fetch_gitlab_profile', gitlab)
    monkeypatch.setattr('app.semantic.enhance_assessment', ai)
    assert client.post('/api/profile/analyze').status_code == 409
    assert gitlab_calls == [] and ai_calls == []


def test_revocation_during_gitlab_wait_prevents_ai(client, monkeypatch):
    register(client)
    profile = publish(client)
    client.put('/api/profile', json={'gitlab_url': URL, 'consent_gitlab_analysis': True})
    ai_calls = []

    async def gitlab(url):
        with SessionLocal() as db:
            db.get(GitLabConnection, profile['id']).consent = False
            db.commit()
        return {'status': 'available', 'url': url, 'repositories': [], 'evidence': []}

    async def ai(assessment, *args, **kwargs):
        ai_calls.append(True)
        return assessment

    monkeypatch.setattr('app.gitlab.fetch_gitlab_profile', gitlab)
    monkeypatch.setattr('app.semantic.enhance_assessment', ai)
    assert client.post('/api/profile/analyze').status_code == 409
    assert ai_calls == []


@pytest.mark.parametrize('unsafe', [
    'http://gitlab.com/person', 'https://gitlab.example.com/person',
    'https://gitlab.com.evil.example/person', 'https://127.0.0.1/person',
    'https://gitlab.com/person/project', 'https://gitlab.com/api',
    'https://gitlab.com/users', 'https://gitlab.com/-',
    'https://gitlab.com/person?token=secret', 'https://gitlab.com/person#fragment',
    'https://name:password@gitlab.com/person', 'https://gitlab.com:8443/person',
    'https://gitlab.com/%2fadmin', 'https://gitlab.com/../admin',
])
def test_gitlab_url_ssrf_and_reserved_paths_rejected(client, unsafe):
    register(client)
    assert client.put('/api/profile', json={'gitlab_url': unsafe}).status_code == 422
    assert client.get('/api/profile').json()['profile']['gitlab_url'] == ''


def test_clearing_gitlab_url_preserves_other_profile_fields(client):
    register(client)
    client.put('/api/profile', json={'gitlab_url': URL, 'consent_gitlab_analysis': True, 'headline': 'Engineer'})
    cleared = client.put('/api/profile', json={'gitlab_url': '', 'consent_gitlab_analysis': False})
    assert cleared.status_code == 200
    profile = cleared.json()['profile']
    assert profile['gitlab_url'] == '' and profile['consent_gitlab_analysis'] is False
    assert profile['headline'] == 'Engineer'
