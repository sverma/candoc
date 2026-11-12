"""Live GitLab.com consent/source integration check with a disposable account.

Uses the public sytses API profile as a source fixture, never publishes the test
candidate and never calls external AI. Run: python deploy/smoke_gitlab.py https://host
"""
import http.cookiejar
import json
import secrets
import sys
import urllib.request
import uuid

base = sys.argv[1].rstrip('/')
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, method='GET', data=None, raw=None, content_type='application/json'):
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(base + '/api' + path, data=body,
                                     headers={'Origin': base, 'Content-Type': content_type}, method=method)
    with opener.open(request, timeout=70) as response:
        return json.load(response)


registered = False
try:
    call('/auth/register', 'POST', {'email': 'gitlab-smoke-' + uuid.uuid4().hex[:12] + '@example.invalid',
                                   'password': secrets.token_urlsafe(24), 'name': 'Disposable GitLab Source Test',
                                   'role': 'candidate'})
    registered = True
    assert call('/profile')['profile']['consent_gitlab_analysis'] is False
    profile = call('/profile', 'PUT', {'gitlab_url': 'https://gitlab.com/sytses'})['profile']
    assert profile['gitlab_url'] == 'https://gitlab.com/sytses'
    boundary = 'candoc-' + uuid.uuid4().hex
    body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="synthetic-resume.txt"\r\nContent-Type: text/plain\r\n\r\nSynthetic GitLab Test\nSummary\nBuilt Python API services for customer teams and improved service reliability through automated tests.\nExperience\nDesigned SQL reporting workflows and validated operational reports through reviewed documentation.\n\r\n--' + boundary + '--\r\n').encode()
    call('/profile/resume', 'POST', raw=body, content_type='multipart/form-data; boundary=' + boundary)
    baseline = call('/profile/analyze', 'POST')['profile']['assessment']
    first_source = next(item for item in baseline['sources'] if item['type'] == 'gitlab')
    assert first_source['status'] == 'not_connected'
    call('/profile', 'PUT', {'consent_gitlab_analysis': True})
    assessment = call('/profile/analyze', 'POST')['profile']['assessment']
    source = next(item for item in assessment['sources'] if item['type'] == 'gitlab')
    assert source['status'] == 'available', source['detail']
    assert assessment['score'] == baseline['score']
    assert assessment['semantic_review']['status'] == 'consent_required'
    export = call('/account/export')['profile']
    assert export['gitlab_url'] == 'https://gitlab.com/sytses' and export['consent_gitlab_analysis'] is True
    revoked = call('/profile', 'PUT', {'consent_gitlab_analysis': False})['profile']
    assert revoked['assessment'] is None
    final = call('/profile/analyze', 'POST')['profile']['assessment']
    assert next(item for item in final['sources'] if item['type'] == 'gitlab')['status'] == 'not_connected'
    print(json.dumps({'gitlab_source': 'available', 'projects_observed': len(source.get('repositories', [])),
                      'consent_and_revocation': 'passed', 'profile_export': 'passed',
                      'score_unchanged_by_public_source': True, 'external_ai_called': False}))
finally:
    if registered:
        assert call('/account', 'DELETE')['ok'], 'Disposable test account cleanup failed'
        print(json.dumps({'synthetic_account_cleanup': 'passed'}))
