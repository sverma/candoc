"""Live HTTPS LinkedIn export test using disposable synthetic accounts.

No LinkedIn website access or external AI call is needed. All test accounts and
documents are removed. Run: python deploy/smoke_linkedin_export.py https://host
"""
import http.cookiejar
import io
import json
import secrets
import sys
import urllib.request
import uuid
import zipfile

base = sys.argv[1].rstrip('/')
suffix = uuid.uuid4().hex[:12]
password = secrets.token_urlsafe(24)


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.registered = False

    def call(self, path, method='GET', data=None, raw=None, content_type='application/json'):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(base + '/api' + path, data=body,
                                         headers={'Origin': base, 'Content-Type': content_type}, method=method)
        with self.opener.open(request, timeout=45) as response:
            return json.load(response)

    def upload(self, path, filename, content):
        boundary = 'candoc-' + uuid.uuid4().hex
        body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename + '"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + content + ('\r\n--' + boundary + '--\r\n').encode()
        return self.call(path, 'POST', raw=body, content_type='multipart/form-data; boundary=' + boundary)


candidate, company = Client(), Client()
canary = 'PRIVATE_IGNORE_CANARY'
archive = io.BytesIO()
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
    package.writestr('Profile.csv', 'First Name,Last Name,Headline,Summary,Birth Date,Address\nSynthetic,Export,Software engineer,Built Python tools for operations teams.,1984-01-01,PRIVATE_IGNORE_CANARY\n')
    package.writestr('Positions.csv', 'Company Name,Title,Description,Location,Started On,Finished On\nSynthetic Company,Engineer,Developed Python API services and improved reliability through automated tests.,Remote,2021-01,2025-01\n')
    package.writestr('Skills.csv', 'Name\nPython\nSQL\n')
    package.writestr('Messages.csv', 'Message\nPRIVATE_IGNORE_CANARY\n')
    package.writestr('Connections.csv', 'Email Address\nPRIVATE_IGNORE_CANARY@example.invalid\n')

try:
    for client, role in ((candidate, 'candidate'), (company, 'company')):
        client.call('/auth/register', 'POST', {'email': 'linkedin-export-' + role + '-' + suffix + '@example.invalid',
                                             'password': password, 'name': 'Disposable LinkedIn Export Test',
                                             'role': role, **({'company_name': 'Disposable Export Review'} if role == 'company' else {})})
        client.registered = True
    profile = candidate.upload('/profile/linkedin/import', 'linkedin-export.zip', archive.getvalue())['profile']
    imported = profile['linkedin_import']
    assert imported['type'] == 'candidate_export' and imported['status'] == 'available'
    assert 'Python' in imported['text']
    assert canary not in json.dumps(imported) and '1984-01-01' not in imported['text']
    assert candidate.call('/account/export')['profile']['linkedin_import']['filename'] == 'linkedin-export.zip'
    candidate.upload('/profile/resume', 'synthetic-resume.txt', b'Synthetic Export Test\nSummary\nBuilt software services for customers using Python and SQL, with validation tests and reviewed documentation.\nExperience\nDesigned API workflows and improved service reliability through monitored tests.\n')
    assessed = candidate.call('/profile/analyze', 'POST')['profile']
    assert 1 <= assessed['assessment']['score'] <= 5
    assert assessed['assessment']['semantic_review']['status'] == 'consent_required'
    candidate.call('/profile', 'PUT', {'visible': True})
    published = company.call('/candidates/' + profile['id'])['candidate']
    assert 'linkedin_import' not in published
    assert canary not in json.dumps(published)
    replacement = candidate.upload('/profile/linkedin/import', 'Skills.csv', b'Name\nDocker\nPostgreSQL\n')['profile']
    assert replacement['assessment'] is None
    assert replacement['linkedin_import']['filename'] == 'Skills.csv'
    cleared = candidate.call('/profile/linkedin/import', 'DELETE')['profile']
    assert cleared['linkedin_import'] is None and cleared['assessment'] is None
    print(json.dumps({'export_upload': 'passed', 'private_archive_fields': 'excluded',
                      'assessment_integration': 'passed', 'full_text_directory_privacy': 'passed',
                      'replace_and_remove': 'passed', 'external_ai_called': False}))
finally:
    for client in (candidate, company):
        if client.registered:
            assert client.call('/account', 'DELETE')['ok'], 'Synthetic account cleanup failed'
    print(json.dumps({'synthetic_accounts_cleanup': 'passed'}))
