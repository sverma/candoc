import pytest
from sqlalchemy import func, select
from app.database import SessionLocal
from app.models import LinkedInImport
from test_api import register, publish
from test_resumes import make_pdf

TEXT = '''Experience
Built Python services serving client teams and reduced request latency by 35 percent.
Designed PostgreSQL pipelines with Docker and validated data quality through automated tests.
Projects
Created reporting applications for analysts and improved report accessibility through stakeholder feedback.
Skills
Python, PostgreSQL, Docker, data analysis.
'''
REPLACEMENT = TEXT.replace('Python', 'TypeScript')


def upload(client, text=TEXT, filename='linkedin.txt'):
    return client.post('/api/profile/linkedin/import', files={'file': (filename, text.encode(), 'text/plain')})


def test_upload_replace_remove_and_reupload(client):
    register(client)
    publish(client)
    response = upload(client)
    assert response.status_code == 200, response.text
    result = response.json()['profile']['linkedin_import']
    assert result['type'] == 'candidate_export' and result['filename'] == 'linkedin.txt'
    assert 'Python' in result['text'] and result['imported_at']
    assert response.json()['profile']['assessment'] is None
    replaced = upload(client, REPLACEMENT, 'new-export.txt').json()['profile']['linkedin_import']
    assert replaced['filename'] == 'new-export.txt'
    assert 'TypeScript' in replaced['text'] and 'Python' not in replaced['text']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LinkedInImport)) == 1
    assert client.delete('/api/profile/linkedin/import').json()['profile']['linkedin_import'] is None
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LinkedInImport)) == 0
    assert upload(client).status_code == 200


def test_document_is_private_in_directory_and_included_in_own_export(client, other_client):
    register(client)
    profile = publish(client)
    assert upload(client).status_code == 200
    register(other_client, 'company@example.com', 'company')
    public = other_client.get('/api/candidates/' + profile['id']).json()['candidate']
    assert 'linkedin_import' not in public
    assert 'linkedin_text' not in public
    exported = client.get('/api/account/export').json()['linkedin_imports']
    assert len(exported) == 1 and 'Python' in exported[0]['result']['text']
    assert client.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LinkedInImport)) == 0


def test_candidate_role_upload_is_explicit_and_no_profile_url_required(client, other_client):
    assert upload(client).status_code == 401
    register(client)
    assert client.get('/api/profile').json()['profile']['linkedin_url'] == ''
    assert upload(client).status_code == 200
    register(other_client, 'company@example.com', 'company')
    assert upload(other_client).status_code == 403
    assert other_client.delete('/api/profile/linkedin/import').status_code == 403


def test_invalid_and_oversized_uploads_do_not_replace_existing(client):
    register(client)
    assert upload(client).status_code == 200
    assert upload(client, 'bad content', 'export.exe').status_code in {400, 422}
    assert upload(client, 'x' * (5 * 1024 * 1024 + 1)).status_code == 413
    assert 'Python' in client.get('/api/profile').json()['profile']['linkedin_import']['text']


def test_pdf_upload_is_parsed_without_original_file_storage(client):
    from app.main import UPLOAD_DIR
    register(client)
    original_files = set(UPLOAD_DIR.iterdir())
    result = client.post('/api/profile/linkedin/import', files={'file': ('linkedin.pdf', make_pdf(), 'application/pdf')})
    assert result.status_code == 200, result.text
    assert 'Python' in result.json()['profile']['linkedin_import']['text']
    assert set(UPLOAD_DIR.iterdir()) == original_files


def test_imported_export_reaches_optional_ai_only_with_existing_separate_consent(client, monkeypatch):
    register(client)
    publish(client)
    assert upload(client).status_code == 200
    calls = []

    async def semantic(assessment, *args, **kwargs):
        calls.append(kwargs)
        return assessment

    monkeypatch.setattr('app.semantic.enhance_assessment', semantic)
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls[-1]['consent'] is False
    assert calls[-1]['linkedin_data']['type'] == 'candidate_export'
    client.put('/api/profile', json={'consent_external_ai': True})
    assert client.post('/api/profile/analyze').status_code == 200
    assert calls[-1]['consent'] is True


@pytest.mark.parametrize('change', ['remove', 'replace'])
def test_export_changes_during_github_wait_stop_analysis_before_ai(client, monkeypatch, change):
    register(client)
    profile = publish(client)
    assert upload(client).status_code == 200
    client.put('/api/profile', json={'github_url': 'https://github.com/octocat', 'consent_public_analysis': True})
    provider_calls = []

    async def github(url):
        with SessionLocal() as db:
            item = db.get(LinkedInImport, profile['id'])
            if change == 'remove':
                db.delete(item)
            else:
                item.result = {**item.result, 'text': REPLACEMENT, 'filename': 'replacement.txt'}
            db.commit()
        return {'status': 'unavailable'}

    async def semantic(*args, **kwargs):
        provider_calls.append(True)
        return args[0]

    monkeypatch.setattr('app.sources.fetch_github_profile', github)
    monkeypatch.setattr('app.semantic.enhance_assessment', semantic)
    assert client.post('/api/profile/analyze').status_code == 409
    assert provider_calls == []


def test_export_removed_during_ai_wait_cannot_save_stale_assessment(client, monkeypatch):
    register(client)
    profile = publish(client)
    assert upload(client).status_code == 200
    client.put('/api/profile', json={'consent_external_ai': True})

    async def semantic(assessment, *args, **kwargs):
        with SessionLocal() as db:
            db.delete(db.get(LinkedInImport, profile['id']))
            db.commit()
        return assessment

    monkeypatch.setattr('app.semantic.enhance_assessment', semantic)
    assert client.post('/api/profile/analyze').status_code == 409
    own = client.get('/api/profile').json()['profile']
    assert own['assessment'] is None
    assert own['linkedin_import'] is None
