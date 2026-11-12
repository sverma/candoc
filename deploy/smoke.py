"""Real HTTPS workflow test using ephemeral synthetic accounts; cleans up on exit.

Usage: python deploy/smoke.py https://host [--ai]
--ai authorizes one small provider call using the server's configured credential.
"""
import http.cookiejar
import json
import secrets
import sys
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1].rstrip('/')
USE_AI = '--ai' in sys.argv[2:]
suffix = uuid.uuid4().hex[:12]
password = secrets.token_urlsafe(24)


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.registered = False

    def call(self, path, method='GET', data=None, raw=None, content_type=None):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        headers = {'Origin': BASE}
        if body is not None:
            headers['Content-Type'] = content_type or 'application/json'
        request = urllib.request.Request(BASE + '/api' + path, body, headers, method=method)
        with self.opener.open(request, timeout=100) as response:
            return json.load(response)


candidate, company, anonymous = Client(), Client(), Client()
candidate_email = 'candoc-smoke-' + suffix + '@example.invalid'
company_email = 'candoc-company-' + suffix + '@example.invalid'
resume = '''Synthetic Workflow Test
Summary
Software engineer documenting a synthetic test portfolio.
Skills
Python, SQL, PostgreSQL, Docker, React
Experience
Built Python API services for a customer platform and reduced response latency by 25% through measured database query optimization.
Designed PostgreSQL reporting pipelines for operations teams and improved report reliability with automated validation tests.
Delivered a React dashboard that enabled customers to review service requests and resolved accessibility issues through user feedback.
Led a team workflow migration using Docker, documented implementation choices, and reduced release failures through monitored testing.
Projects
Developed a Python inventory application with SQL transactions and validated rollback behavior through integration tests.
Implemented an API monitoring dashboard with tested failure alerts and improved incident response through reviewed documentation.
'''

try:
    assert anonymous.call('/health')['status'] == 'ok'
    assert anonymous.call('/candidates')['candidates'] == []
    before = anonymous.call('/stats')
    candidate.call('/auth/register', 'POST', {'email': candidate_email, 'password': password,
                                             'name': 'Synthetic Workflow Test', 'role': 'candidate'})
    candidate.registered = True
    company.call('/auth/register', 'POST', {'email': company_email, 'password': password,
                                           'name': 'Synthetic Recruiter', 'company_name': 'Synthetic Test Company', 'role': 'company'})
    company.registered = True
    candidate.call('/profile', 'PUT', {'headline': 'Synthetic software profile — will be deleted',
                                      'skills': ['Python', 'SQL', 'PostgreSQL', 'Docker', 'React'],
                                      'location': 'Remote', 'consent_external_ai': USE_AI})
    boundary = 'candoc-' + uuid.uuid4().hex
    upload = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="synthetic-resume.txt"\r\nContent-Type: text/plain\r\n\r\n' + resume + '\r\n--' + boundary + '--\r\n').encode()
    candidate.call('/profile/resume', 'POST', raw=upload, content_type='multipart/form-data; boundary=' + boundary)
    profile = candidate.call('/profile/analyze', 'POST')['profile']
    assessment = profile['assessment']
    assert 1 <= assessment['score'] <= 5
    assert len(assessment['dimensions']) == 5
    if USE_AI:
        assert assessment['semantic_review']['status'] == 'complete', assessment['semantic_review']['detail']
        assert assessment['semantic_review']['observations'], 'Live AI did not return supported observations'
    candidate.call('/profile', 'PUT', {'visible': True})
    public = company.call('/candidates/' + profile['id'])['candidate']
    assert 'resume_text' not in public and 'linkedin_text' not in public
    assert candidate_email not in json.dumps(public)
    found = company.call('/candidates?search=Synthetic%20Workflow')['candidates']
    assert any(item['id'] == profile['id'] for item in found)
    introduction = company.call('/introductions', 'POST', {'candidate_id': profile['id'],
                                                          'role_title': 'Synthetic test role',
                                                          'message': 'This is an automated end-to-end verification message, removed after testing.',
                                                          'salary_range': 'Test only', 'work_mode': 'Remote'})['introduction']
    assert 'contact_email' not in introduction
    candidate.call('/introductions/' + introduction['id'], 'PATCH', {'status': 'accepted'})
    accepted = company.call('/introductions')['introductions']
    assert any(item.get('contact_email') == candidate_email for item in accepted)
    assert candidate.call('/account/export')['profile']['resume_text']
    result = {'workflow': 'passed', 'score': assessment['score'],
              'ai_status': assessment['semantic_review']['status'],
              'ai_observations': len(assessment['semantic_review'].get('observations', [])),
              'token_usage': assessment['semantic_review'].get('usage', {})}
finally:
    failures = []
    for client in (candidate, company):
        if client.registered:
            try:
                client.call('/account', 'DELETE')
            except Exception as exc:
                failures.append(type(exc).__name__)
    if failures:
        raise RuntimeError('Synthetic account cleanup failed: ' + ', '.join(failures))

after = anonymous.call('/stats')
assert after == before, 'Synthetic records were not fully removed'
print(json.dumps({**result, 'synthetic_data_cleanup': 'passed'}, indent=2))
