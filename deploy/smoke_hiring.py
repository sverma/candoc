"""Production hiring smoke check with disposable records, public HTTPS and real SMTP.

Run inside Candoc's API container via stdin. Verification delivery alone uses an
in-process TestClient to capture its link; all hiring actions use public HTTPS.
SMTP is restricted to Resend's simulated-delivery recipient. No secrets printed.
Every created account and its linked hiring records are removed in finally.
"""
import datetime as dt
import json
import os
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient
from app import mailer
from app.main import app

BASE = os.environ['APP_URL'].rstrip('/')
assert BASE.startswith('https://')
assert os.environ.get('SMTP_HOST') == 'smtp.resend.com', 'Use only the documented simulated-delivery test sink.'
suffix = uuid.uuid4().hex[:12]
password = secrets.token_urlsafe(24)
clients = []
before = httpx.get(BASE + '/api/stats', timeout=30).json()


class Client:
    def __init__(self, role, tag):
        self.http = httpx.Client(base_url=BASE, headers={'Origin': BASE}, timeout=40)
        self.role, self.email = role, 'delivered+candoc-hiring-' + suffix + '-' + tag + '@resend.dev'
        self.registered = False
        clients.append(self)
        self.user = self.call('/auth/register', 'POST', {'email': self.email, 'password': password,
            'name': 'Disposable Hiring ' + tag, 'role': role,
            **({'company_name': 'Disposable Hiring Company ' + tag} if role == 'company' else {})}, expected=201)['user']
        self.registered = True

    def call(self, path, method='GET', data=None, expected=200):
        response = self.http.request(method, '/api' + path, json=data)
        assert response.status_code == expected, method + ' ' + path + ': ' + str(response.status_code) + ' ' + response.text[:200]
        return response.json()

    def verify(self):
        captured = []
        original = mailer._send_message
        def capture_and_deliver(recipient, subject, body):
            assert recipient == self.email and recipient.endswith('@resend.dev')
            original(recipient, subject, body)
            link = next(line for line in body.splitlines() if line.startswith(BASE + '/verify-email#token='))
            captured.append(parse_qs(urlsplit(link).fragment)['token'][0])
        mailer._send_message = capture_and_deliver
        try:
            with TestClient(app, base_url=BASE, headers={'Origin': BASE}) as browser:
                assert browser.post('/api/auth/login', json={'email': self.email, 'password': password}).status_code == 200
                response = browser.post('/api/auth/request-verification')
                assert response.status_code == 202
                assert len(captured) == 1, 'SMTP did not accept verification email'
                assert captured[0] not in response.text
            def consume(_):
                return self.http.post('/api/auth/verify-email', json={'token': captured[0]}).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                assert sorted(pool.map(consume, range(2))) == [200, 400], 'Verification must be consumed once under concurrency'
            assert self.call('/auth/me')['user']['email_verified'] is True
        finally:
            mailer._send_message = original


try:
    candidate, company, outsider = Client('candidate', 'candidate'), Client('company', 'company'), Client('company', 'outsider')
    catalogs = candidate.call('/hiring/catalogs')
    assert len(catalogs['countries']) == 249 and len(catalogs['currencies']) >= 170
    candidate.call('/hiring/preferences', 'PUT', {
        'engagement_types': ['permanent', 'contract', 'freelance', 'consulting'], 'work_modes': ['remote', 'hybrid'],
        'preferred_countries': ['DE', 'CA'], 'preferred_regions': ['EU'], 'nationalities': ['IN'],
        'work_authorizations': [{'scope_type': 'country', 'scope_code': 'IN', 'status': 'unrestricted',
                                 'notes': 'Private synthetic permit note'}],
        'sponsorship_need': 'required', 'willing_to_relocate': True, 'relocation_countries': ['DE', 'CA'],
        'timezone': 'Asia/Kolkata', 'languages': [{'name': 'English', 'proficiency': 'professional'}],
        'hours_per_week': 40, 'compensation_min': 80, 'compensation_max': 100, 'currency': 'USD', 'pay_period': 'hour'
    })
    profile = candidate.call('/profile', 'PUT', {'headline': 'Disposable hiring workflow test', 'skills': ['Python'], 'visible': True})['profile']
    professional = company.call('/candidates/' + profile['id'])['candidate']['work_preferences']
    assert 'nationalities' not in professional and 'work_authorizations' not in professional
    candidate.call('/profile', 'PUT', {'visible': False})
    company.call('/hiring/company', 'PUT', {'name': 'Disposable Hiring Studio', 'website': 'https://example.com',
        'industry': 'Software', 'size': '11–50', 'headquarters': 'Berlin', 'about': 'Synthetic deployment verification, deleted after testing.'})
    role = {'title': 'Disposable hiring verification role', 'description': 'Synthetic verification role, automatically removed after testing.',
        'engagement_type': 'permanent', 'work_mode': 'hybrid', 'country_codes': ['DE'], 'skills': ['Python'],
        'visa_sponsorship': 'available', 'visa_details': 'Synthetic employer support subject to independent legal review.',
        'relocation_support': 'case_by_case', 'relocation_details': 'Synthetic relocation allowance discussion.',
        'compensation_min': 90000, 'compensation_max': 120000, 'currency': 'EUR', 'pay_period': 'year'}
    job = company.call('/hiring/jobs', 'POST', role, expected=201)['job']
    company.call('/hiring/jobs/' + job['id'], 'PATCH', {'status': 'published'}, expected=403)
    outsider.call('/hiring/jobs/' + job['id'], expected=404)
    company.verify()
    company.call('/hiring/jobs/' + job['id'], 'PATCH', {'status': 'published'})
    outsider.call('/hiring/jobs/' + job['id'], 'PATCH', {'title': 'Cross-tenant mutation'}, expected=404)
    found = candidate.call('/hiring/jobs?country=DE&engagement_type=permanent&visa_sponsorship=available&relocation_support=case_by_case')['jobs']
    assert any(item['id'] == job['id'] for item in found)
    candidate.call('/hiring/jobs/' + job['id'] + '/save', 'PUT', {'saved': True})
    assert any(item['id'] == job['id'] for item in candidate.call('/hiring/jobs?saved=true')['jobs'])
    candidate.call('/hiring/jobs/' + job['id'] + '/apply', 'POST', {'share_contact': True}, expected=403)
    application = candidate.call('/hiring/jobs/' + job['id'] + '/apply', 'POST', {'message': 'Synthetic application with private profile.'}, expected=201)['application']
    application_id = application['id']
    path = '/hiring/applications/' + application_id
    candidate.call('/hiring/jobs/' + job['id'] + '/apply', 'POST', {}, expected=409)
    outsider.call(path, expected=404)
    application = company.call(path)['application']
    assert application['candidate']['id'] == profile['id'] and 'contact_email' not in application
    assert 'nationalities' not in json.dumps(application) and 'Private synthetic permit note' not in json.dumps(application)
    assert 'resume_text' not in application['candidate']
    candidate.verify()
    candidate.call(path, 'PATCH', {'share_contact': True})
    assert company.call(path)['application']['contact_email'] == candidate.email
    candidate.call(path, 'PATCH', {'share_contact': False})
    assert 'contact_email' not in company.call(path)['application']
    company.call(path + '/stage', 'PATCH', {'stage': 'reviewing'})
    candidate.call(path + '/messages', 'POST', {'body': 'Synthetic candidate question.'}, expected=201)
    company.call(path + '/messages', 'POST', {'body': 'Synthetic recruiter response.'}, expected=201)
    assert len(candidate.call(path)['messages']) == 2
    interview = company.call(path + '/interviews', 'POST', {
        'starts_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)).isoformat(),
        'duration_minutes': 45, 'location_or_url': 'https://example.com/synthetic-meeting', 'notes': 'Synthetic interview.'}, expected=201)['interview']
    candidate.call('/hiring/interviews/' + interview['id'], 'PATCH', {'rsvp': 'accepted'})
    updated = company.call('/hiring/interviews/' + interview['id'], 'PATCH', {'duration_minutes': 60})['interview']
    assert updated['rsvp'] == 'pending'
    candidate.call('/hiring/interviews/' + interview['id'], 'PATCH', {'rsvp': 'accepted'})
    company.call(path + '/stage', 'PATCH', {'stage': 'hired'}, expected=409)
    offer_terms = {'summary': 'Synthetic proposed engagement terms; not a signed employment contract.',
        'compensation_min': 100000, 'currency': 'EUR', 'pay_period': 'year',
        'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=14)).isoformat(),
        'visa_sponsorship': 'available', 'relocation_support': 'case_by_case'}
    def send_offer(_):
        return company.http.post('/api' + path + '/offers', json=offer_terms)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send_offer, range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409], 'Concurrent offer creation must permit only one active offer'
    offer = next(response.json()['offer'] for response in responses if response.status_code == 201)
    outsider.call('/hiring/offers/' + offer['id'], 'PATCH', {'status': 'accepted'}, expected=404)
    candidate.call('/hiring/offers/' + offer['id'], 'PATCH', {'status': 'accepted'})
    candidate.call('/hiring/offers/' + offer['id'], 'PATCH', {'status': 'declined'}, expected=409)
    assert company.call(path + '/stage', 'PATCH', {'stage': 'hired'})['application']['stage'] == 'hired'
    assert company.call('/hiring/dashboard')['counts']['upcoming_interviews'] == 0
    assert company.call(path)['interviews'][0]['status'] == 'cancelled'
    # Exercise the reverse flow on a separate freelance role.
    candidate.call('/profile', 'PUT', {'visible': True})
    invitation_job = company.call('/hiring/jobs', 'POST', {**role, 'title': 'Disposable freelance invitation', 'engagement_type': 'freelance',
        'work_mode': 'remote', 'country_codes': [], 'region_codes': ['GLOBAL'], 'pay_period': 'project', 'status': 'published'}, expected=201)['job']
    invitation = company.call('/hiring/jobs/' + invitation_job['id'] + '/invite', 'POST', {'candidate_id': profile['id'],
        'message': 'Synthetic company invitation for verification.'}, expected=201)['application']
    invitation_path = '/hiring/applications/' + invitation['id']
    candidate.call(invitation_path, 'PATCH', {'action': 'accept_invitation'})
    candidate.call(invitation_path, 'PATCH', {'action': 'withdraw'})
    company.call(invitation_path + '/messages', 'POST', {'body': 'Must not send after withdrawal.'}, expected=409)
    # All remaining engagement types must persist, even with no public fixture.
    for engagement in ['contract', 'consulting', 'temporary', 'internship', 'apprenticeship', 'volunteer']:
        created = company.call('/hiring/jobs', 'POST', {**role, 'engagement_type': engagement}, expected=201)['job']
        assert created['engagement_type'] == engagement and created['status'] == 'draft'
    assert candidate.call('/hiring/notifications')['unread_count'] > 0
    candidate.call('/hiring/notifications/read-all', 'POST')
    assert candidate.call('/hiring/notifications')['unread_count'] == 0
    assert company.call('/hiring/dashboard')['pipeline']['hired'] == 1
    exported = candidate.call('/account/export')
    assert exported['work_preferences']['nationalities'] == ['IN']
    assert len(exported['hiring']['applications']) == 2 and len(exported['hiring']['offers']) == 1
    assert 'Private synthetic permit note' not in json.dumps(company.call('/account/export'))
    candidate.call('/account', 'DELETE')
    candidate.registered = False
    assert company.call('/hiring/applications')['applications'] == []
    company.call('/hiring/jobs/' + job['id'], 'PATCH', {'status': 'closed'})
    candidate.call('/hiring/jobs/' + job['id'], expected=404)
    company.call('/hiring/jobs/' + job['id'], 'PATCH', {'status': 'published'}, expected=409)
    print(json.dumps({'public_https_hiring': 'passed', 'engagement_types': 8, 'private_profile_application': 'passed',
        'reverse_invitation': 'passed', 'visa_relocation_filters': 'passed', 'sensitive_preferences': 'private',
        'messages_interviews_offer_hire': 'passed', 'tenant_isolation': 'passed',
        'verification_real_smtp': 'accepted by provider test sink', 'contact_revocation': 'passed', 'export': 'passed'}))
finally:
    failures = []
    for client in clients:
        try:
            if client.registered:
                client.call('/account', 'DELETE')
        except Exception:
            failures.append(client.role)
        finally:
            client.http.close()
    assert not failures, 'Disposable account cleanup failed: ' + ','.join(failures)
    assert httpx.get(BASE + '/api/stats', timeout=30).json() == before, 'Live counts did not return to baseline'
    print(json.dumps({'synthetic_hiring_records_cleanup': 'passed'}))
