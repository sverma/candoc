import datetime as dt
from contextlib import ExitStack
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.database import SessionLocal
from app.main import app
from app.models import User, now
from app.hiring import export_hiring
from app.hiring_models import Application, CompanyProfile, Interview, Job, Message, Notification, Offer, SavedJob
from app.verification_models import EmailVerification
from test_api import register

def verify(user_id):
    with SessionLocal() as db:
        existing = db.get(EmailVerification, user_id)
        if not existing:
            db.add(EmailVerification(user_id=user_id, verified_at=now()))
        else:
            existing.verified_at = now()
        db.commit()


@pytest.fixture
def parties():
    with ExitStack() as stack:
        clients = [stack.enter_context(TestClient(app, headers={'Origin': 'http://testserver'})) for _ in range(4)]
        candidate, company, stranger, rival = clients
        users = [register(candidate, 'candidate@example.com'), register(company, 'company@example.com', 'company'),
                 register(stranger, 'stranger@example.com'), register(rival, 'rival@example.com', 'company')]
        verify(users[1]['id'])
        verify(users[3]['id'])
        yield candidate, company, stranger, rival, users


def job(company, **changes):
    payload = {'title': 'Platform engineer', 'description': 'Build reliable APIs and collaborate with our product engineering team.',
               'engagement_type': 'permanent', 'work_mode': 'remote', 'country_codes': ['IN'], 'region_codes': ['APAC'],
               'compensation_min': 2000000, 'compensation_max': 3500000, 'currency': 'INR', 'pay_period': 'year',
               'visa_sponsorship': 'case_by_case', 'relocation_support': 'available', 'status': 'published', **changes}
    response = company.post('/api/hiring/jobs', json=payload)
    assert response.status_code == 201, response.text
    return response.json()['job']


def apply(candidate, created, share=False):
    response = candidate.post('/api/hiring/jobs/' + created['id'] + '/apply', json={'message': 'I would like to discuss this work.', 'share_contact': share})
    assert response.status_code == 201, response.text
    return response.json()['application']


def offer(company, application, **changes):
    response = company.post('/api/hiring/applications/' + application['id'] + '/offers', json={
        'summary': 'A role offer for platform engineering, subject to the agreed formal contract.',
        'compensation_min': 2500000, 'compensation_max': 3000000, 'currency': 'INR', 'pay_period': 'year',
        'expires_at': (now() + dt.timedelta(days=7)).isoformat(), 'visa_sponsorship': 'case_by_case',
        'relocation_support': 'available', **changes})
    assert response.status_code == 201, response.text
    return response.json()['offer']


def test_full_candidate_apply_message_interview_offer_human_hire_flow(parties):
    candidate, company, stranger, rival, users = parties
    created = job(company)
    application = apply(candidate, created)
    application_url = '/api/hiring/applications/' + application['id']
    company_row = company.get(application_url).json()['application']
    assert company_row['candidate']['name'] == 'Avery Engineer'
    assert 'contact_email' not in company_row and 'resume_text' not in company_row['candidate']
    assert candidate.post('/api/hiring/jobs/' + created['id'] + '/apply', json={}).status_code == 409
    assert rival.get(application_url).status_code == stranger.get(application_url).status_code == 404
    assert company.patch(application_url + '/stage', json={'stage': 'reviewing'}).status_code == 200
    assert candidate.post(application_url + '/messages', json={'body': 'Could you share more about the team?'}).status_code == 201
    assert company.post(application_url + '/messages', json={'body': 'Our team owns the platform APIs.'}).status_code == 201
    assert stranger.post(application_url + '/messages', json={'body': 'I must not read this thread.'}).status_code == 404
    starts = (now() + dt.timedelta(days=2)).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    interview_response = company.post(application_url + '/interviews', json={'starts_at': starts.isoformat(), 'duration_minutes': 45, 'location_or_url': 'https://meet.example.com/engineering', 'notes': 'Discuss a recent project.'})
    assert interview_response.status_code == 201, interview_response.text
    interview = interview_response.json()['interview']
    assert dt.datetime.fromisoformat(interview['starts_at']) == starts
    interview_url = '/api/hiring/interviews/' + interview['id']
    assert candidate.patch(interview_url, json={'rsvp': 'accepted'}).json()['interview']['rsvp'] == 'accepted'
    assert rival.patch(interview_url, json={'status': 'cancelled'}).status_code == 404
    assert company.patch(interview_url, json={'starts_at': (now() + dt.timedelta(days=3)).isoformat()}).json()['interview']['rsvp'] == 'pending'
    assert candidate.patch(interview_url, json={'rsvp': 'accepted'}).status_code == 200
    sent = offer(company, application)
    assert company.patch(application_url + '/stage', json={'stage': 'hired'}).status_code == 409
    offer_url = '/api/hiring/offers/' + sent['id']
    assert company.patch(offer_url, json={'status': 'accepted'}).status_code == 403
    assert stranger.patch(offer_url, json={'status': 'accepted'}).status_code == 404
    assert candidate.patch(offer_url, json={'status': 'accepted'}).status_code == 200
    assert candidate.patch(offer_url, json={'status': 'accepted'}).status_code == 200
    assert candidate.patch(offer_url, json={'status': 'declined'}).status_code == 409
    assert company.get(application_url).json()['application']['stage'] == 'offer'
    assert company.patch(application_url + '/stage', json={'stage': 'hired'}).json()['application']['stage'] == 'hired'
    assert company.get('/api/hiring/dashboard').json()['counts']['upcoming_interviews'] == 0
    assert company.patch(application_url + '/stage', json={'stage': 'reviewing'}).status_code == 409
    assert candidate.post(application_url + '/messages', json={'body': 'Thank you, I will review onboarding details.'}).status_code == 201
    detail = candidate.get(application_url).json()
    assert len(detail['messages']) == 3 and len(detail['interviews']) == 1 and len(detail['offers']) == 1
    assert detail['interviews'][0]['status'] == 'cancelled'
    assert candidate.get('/api/hiring/dashboard').json()['pipeline']['hired'] == 1


def test_reverse_invitation_acceptance_preserves_directory_privacy_and_contact_choice(parties):
    candidate, company, stranger, rival, users = parties
    profile = candidate.put('/api/profile', json={'visible': True, 'headline': 'Backend engineer'}).json()['profile']
    created = job(company)
    response = company.post('/api/hiring/jobs/' + created['id'] + '/invite', json={'candidate_id': profile['id'], 'message': 'We would love to discuss our platform role with you.'})
    assert response.status_code == 201, response.text
    application = response.json()['application']
    assert application['stage'] == 'invited'
    candidate.put('/api/profile', json={'visible': False})
    url = '/api/hiring/applications/' + application['id']
    assert company.get(url).json()['application']['candidate'] is None
    assert company.patch(url + '/stage', json={'stage': 'reviewing'}).status_code == 409
    accepted = candidate.patch(url, json={'action': 'accept_invitation', 'share_contact': False})
    assert accepted.status_code == 200
    assert company.get(url).json()['application']['candidate']['headline'] == 'Backend engineer'
    assert company.get('/api/candidates/' + profile['id']).status_code == 404
    assert candidate.patch(url, json={'share_contact': True}).status_code == 403
    verify(users[0]['id'])
    assert candidate.patch(url, json={'share_contact': True}).status_code == 200
    assert company.get(url).json()['application']['contact_email'] == 'candidate@example.com'
    assert candidate.patch(url, json={'share_contact': False}).status_code == 200
    assert 'contact_email' not in company.get(url).json()['application']
    assert candidate.patch(url, json={'action': 'withdraw'}).json()['application']['stage'] == 'withdrawn'
    assert company.patch(url + '/stage', json={'stage': 'reviewing'}).status_code == 409


def test_drafts_closed_roles_and_tenant_isolation(parties):
    candidate, company, stranger, rival, users = parties
    draft = job(company, status='draft')
    assert company.get('/api/hiring/jobs?mine=true').json()['total'] == 1
    assert candidate.get('/api/hiring/jobs').json()['total'] == 0
    assert candidate.get('/api/hiring/jobs/' + draft['id']).status_code == 404
    assert rival.get('/api/hiring/jobs/' + draft['id']).status_code == 404
    assert rival.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'published'}).status_code == 404
    assert candidate.post('/api/hiring/jobs/' + draft['id'] + '/apply', json={}).status_code == 404
    assert company.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'published'}).status_code == 200
    application = apply(candidate, draft)
    assert company.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'closed'}).status_code == 200
    assert stranger.post('/api/hiring/jobs/' + draft['id'] + '/apply', json={}).status_code == 404
    assert candidate.get('/api/hiring/jobs/' + draft['id']).status_code == 200
    assert stranger.get('/api/hiring/jobs/' + draft['id']).status_code == 404
    assert candidate.get('/api/hiring/applications/' + application['id']).status_code == 200
    assert company.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'published'}).status_code == 409


@pytest.mark.parametrize('initial_status', ['draft', 'paused'])
def test_invitation_requires_explicit_publication_then_explicit_send(parties, initial_status):
    candidate, company, stranger, rival, users = parties
    profile = candidate.put('/api/profile', json={'visible': True, 'headline': 'Platform engineer'}).json()['profile']
    role = job(company, status=initial_status)
    invitation = {'candidate_id': profile['id'], 'message': 'Please consider our platform engineering opportunity.'}
    endpoint = '/api/hiring/jobs/' + role['id']
    assert company.post(endpoint + '/invite', json=invitation).status_code == 409
    assert candidate.get('/api/hiring/applications').json()['applications'] == []
    assert company.patch(endpoint, json={'status': 'published'}).status_code == 200
    # Publishing alone never contacts a candidate or creates an invitation.
    assert candidate.get('/api/hiring/applications').json()['applications'] == []
    assert candidate.get('/api/hiring/notifications').json()['unread_count'] == 0
    response = company.post(endpoint + '/invite', json=invitation)
    assert response.status_code == 201, response.text
    assert response.json()['application']['stage'] == 'invited'
    assert candidate.get('/api/hiring/notifications').json()['unread_count'] == 1
    assert company.post(endpoint + '/invite', json=invitation).status_code == 409


@pytest.mark.parametrize('engagement', ['permanent', 'contract', 'freelance', 'consulting', 'temporary', 'internship', 'apprenticeship', 'volunteer'])
def test_all_engagement_types_and_structured_filters(parties, engagement):
    candidate, company, stranger, rival, users = parties
    created = job(company, engagement_type=engagement, work_mode='hybrid', country_codes=['in'], region_codes=['apac'])
    result = candidate.get('/api/hiring/jobs', params={'engagement_type': engagement, 'work_mode': 'hybrid', 'country': 'IN', 'region': 'APAC', 'visa_sponsorship': 'case_by_case', 'relocation_support': 'available'})
    assert result.status_code == 200, result.text
    assert result.json()['total'] == 1
    assert result.json()['jobs'][0]['id'] == created['id']
    assert candidate.get('/api/hiring/jobs?country=US').json()['total'] == 0
    assert candidate.get('/api/hiring/jobs?engagement_type=madeup').status_code == 422
    assert candidate.get('/api/hiring/jobs?country=ZZ').status_code == 422
    assert candidate.get('/api/hiring/jobs?nationality=IN').json()['total'] == 1


def test_verification_gates_publish_and_shared_contact_but_not_drafts_or_apply(client, other_client):
    company_user = register(client, 'unverified-company@example.com', 'company')
    register(other_client)
    payload = {'title': 'Software engineer', 'description': 'Build product APIs with our engineering team.', 'status': 'published'}
    assert client.post('/api/hiring/jobs', json=payload).status_code == 403
    draft = job(client, status='draft')
    assert client.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'published'}).status_code == 403
    verify(company_user['id'])
    assert client.patch('/api/hiring/jobs/' + draft['id'], json={'status': 'published'}).status_code == 200
    assert other_client.post('/api/hiring/jobs/' + draft['id'] + '/apply', json={'share_contact': True}).status_code == 403
    assert other_client.post('/api/hiring/jobs/' + draft['id'] + '/apply', json={'share_contact': False}).status_code == 201


def test_compensation_location_and_meeting_validation(parties):
    candidate, company, stranger, rival, users = parties
    base = {'title': 'A platform engineer', 'description': 'A real role with useful engineering work and a professional team.'}
    for extra in [{'compensation_min': 200, 'compensation_max': 100, 'currency': 'USD'}, {'compensation_min': 100},
                  {'status': 'published', 'work_mode': 'onsite'}, {'country_codes': ['GLOBAL']}, {'region_codes': ['US']},
                  {'currency': 'ZZZ'}, {'hours_per_week': 169}, {'engagement_type': 'gig'}]:
        assert company.post('/api/hiring/jobs', json={**base, **extra}).status_code == 422
    application = apply(candidate, job(company))
    url = '/api/hiring/applications/' + application['id'] + '/interviews'
    assert company.post(url, json={'starts_at': '2030-01-01T10:00:00', 'duration_minutes': 30, 'location_or_url': 'Office'}).status_code == 422
    assert company.post(url, json={'starts_at': (now() + dt.timedelta(days=1)).isoformat(), 'duration_minutes': 30, 'location_or_url': 'javascript:alert(1)'}).status_code == 422
    assert company.post(url, json={'starts_at': (now() - dt.timedelta(days=1)).isoformat(), 'duration_minutes': 30, 'location_or_url': 'Office'}).status_code == 422


def test_offer_expiry_replacement_withdrawal_and_no_automatic_hire(parties):
    candidate, company, stranger, rival, users = parties
    application = apply(candidate, job(company))
    first = offer(company, application)
    with SessionLocal() as db:
        db.get(Offer, first['id']).expires_at = now() - dt.timedelta(seconds=1)
        db.commit()
    assert candidate.patch('/api/hiring/offers/' + first['id'], json={'status': 'accepted'}).status_code == 409
    second = offer(company, application)
    assert company.patch('/api/hiring/offers/' + second['id'], json={'status': 'withdrawn'}).status_code == 200
    assert company.patch('/api/hiring/offers/' + second['id'], json={'status': 'withdrawn'}).status_code == 200
    assert candidate.patch('/api/hiring/offers/' + second['id'], json={'status': 'accepted'}).status_code == 409
    third = offer(company, application)
    assert candidate.patch('/api/hiring/offers/' + third['id'], json={'status': 'declined'}).status_code == 200
    assert company.get('/api/hiring/applications/' + application['id']).json()['application']['stage'] == 'offer'


def test_saved_jobs_company_profile_notifications_export_and_cascade(parties):
    candidate, company, stranger, rival, users = parties
    company_response = company.put('/api/hiring/company', json={'name': 'Example Engineering', 'website': 'https://example.com', 'industry': 'Software', 'size': '11–50', 'headquarters': 'Bengaluru', 'about': 'We build useful engineering tools.'})
    assert company_response.status_code == 200
    assert company_response.json()['company']['email_verified'] is True
    created = job(company)
    assert 'email' not in created['company']
    assert created['company_name'] == 'Example Engineering'
    saved_url = '/api/hiring/jobs/' + created['id'] + '/save'
    assert candidate.put(saved_url, json={'saved': True}).status_code == 200
    assert candidate.put(saved_url, json={'saved': True}).status_code == 200
    assert candidate.get('/api/hiring/jobs?saved=true').json()['total'] == 1
    application = apply(candidate, created)
    company_notifications = company.get('/api/hiring/notifications').json()
    assert company_notifications['unread_count'] == 1
    nid = company_notifications['notifications'][0]['id']
    assert rival.patch('/api/hiring/notifications/' + nid, json={'read': True}).status_code == 404
    assert company.patch('/api/hiring/notifications/' + nid, json={'read': True}).status_code == 200
    assert company.get('/api/hiring/notifications').json()['unread_count'] == 0
    candidate.post('/api/hiring/applications/' + application['id'] + '/messages', json={'body': 'A private hiring message.'})
    with SessionLocal() as db:
        exported = export_hiring(db.get(User, users[0]['id']), db)
        assert len(exported['applications']) == len(exported['messages']) == 1
        assert exported['saved_jobs'] == [created['id']]
    assert candidate.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        for model in [Application, Message, Interview, Offer, Notification, SavedJob]:
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert db.scalar(select(func.count()).select_from(Job)) == 1
    assert company.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(CompanyProfile)) == 0


def test_message_rate_limit_is_per_sender_and_real_inapp_only(parties):
    candidate, company, stranger, rival, users = parties
    application = apply(candidate, job(company))
    url = '/api/hiring/applications/' + application['id'] + '/messages'
    for number in range(60):
        assert candidate.post(url, json={'body': f'Message number {number}'}).status_code == 201
    assert candidate.post(url, json={'body': 'The rate limit should stop this.'}).status_code == 429
    assert company.post(url, json={'body': 'The other participant has an independent limit.'}).status_code == 201


@pytest.mark.parametrize('terminal', ['withdrawn', 'rejected', 'declined'])
def test_closed_conversations_retain_history_but_stop_new_messages(parties, terminal):
    candidate, company, stranger, rival, users = parties
    created = job(company)
    if terminal == 'declined':
        profile = candidate.put('/api/profile', json={'visible': True}).json()['profile']
        application = company.post('/api/hiring/jobs/' + created['id'] + '/invite', json={'candidate_id': profile['id'], 'message': 'Please consider our platform role.'}).json()['application']
    else:
        application = apply(candidate, created)
    url = '/api/hiring/applications/' + application['id']
    assert company.post(url + '/messages', json={'body': 'A message before the conversation closes.'}).status_code == 201
    if terminal == 'rejected':
        assert company.patch(url + '/stage', json={'stage': 'rejected'}).status_code == 200
    else:
        action = 'decline_invitation' if terminal == 'declined' else 'withdraw'
        assert candidate.patch(url, json={'action': action}).status_code == 200
    assert company.post(url + '/messages', json={'body': 'This must not reach the candidate.'}).status_code == 409
    assert candidate.post(url + '/messages', json={'body': 'This thread is now closed.'}).status_code == 409
    assert len(candidate.get(url).json()['messages']) == 1


def test_application_and_company_export_respect_nationality_permit_and_contact_privacy(parties):
    candidate, company, stranger, rival, users = parties
    preferences = candidate.put('/api/hiring/preferences', json={
        'nationalities': ['IN'], 'work_authorizations': [{'scope_type': 'country', 'scope_code': 'US', 'status': 'needs_sponsorship', 'notes': 'A private permit note.'}],
        'share_nationality': False, 'share_work_authorization': False, 'sponsorship_need': 'required'})
    assert preferences.status_code == 200, preferences.text
    candidate.put('/api/profile', json={'bio': 'For contact use candidate@example.com or +919876543210.'})
    # Nationality and sponsorship declarations are not eligibility decisions.
    application = apply(candidate, job(company, country_codes=['US'], region_codes=[], work_mode='onsite', visa_sponsorship='not_available'))
    detail = company.get('/api/hiring/applications/' + application['id'])
    row = detail.json()['application']
    assert 'candidate@example.com' not in detail.text and '9876543210' not in detail.text
    work = row['candidate']['work_preferences']
    assert 'nationalities' not in work and 'work_authorizations' not in work
    assert 'A private permit note.' not in detail.text
    with SessionLocal() as db:
        exported = export_hiring(db.get(User, users[1]['id']), db)
        safe = exported['applications'][0]['candidate']['work_preferences']
        assert 'nationalities' not in safe and 'work_authorizations' not in safe
    stranger_export = stranger.get('/api/account/export')
    assert application['id'] not in stranger_export.text


def test_company_deletion_cascades_complete_workspace_but_retains_candidate(parties):
    candidate, company, stranger, rival, users = parties
    created = job(company)
    candidate.put('/api/hiring/jobs/' + created['id'] + '/save', json={'saved': True})
    application = apply(candidate, created)
    url = '/api/hiring/applications/' + application['id']
    company.post(url + '/messages', json={'body': 'Discuss the role and next steps.'})
    response = company.post(url + '/interviews', json={'starts_at': (now() + dt.timedelta(days=2)).isoformat(), 'duration_minutes': 30, 'location_or_url': 'https://meet.example.com/session'})
    assert response.status_code == 201
    offer(company, application)
    assert company.delete('/api/account').status_code == 200
    assert candidate.get(url).status_code == 404
    assert candidate.get('/api/auth/me').json()['user']['id'] == users[0]['id']
    with SessionLocal() as db:
        for model in [Job, Application, Message, Interview, Offer, Notification, SavedJob]:
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_previously_saved_closed_role_can_be_removed(parties):
    candidate, company, stranger, rival, users = parties
    created = job(company)
    url = '/api/hiring/jobs/' + created['id']
    assert candidate.put(url + '/save', json={'saved': True}).status_code == 200
    company.patch(url, json={'status': 'closed'})
    assert candidate.put(url + '/save', json={'saved': False}).json()['saved'] is False
    assert candidate.get('/api/hiring/dashboard').json()['counts']['saved_jobs'] == 0


def test_hiring_cancels_pending_interviews_and_preserves_completed_history(parties):
    candidate, company, stranger, rival, users = parties
    application = apply(candidate, job(company))
    url = '/api/hiring/applications/' + application['id']
    pending = company.post(url + '/interviews', json={'starts_at': (now() + dt.timedelta(days=2)).isoformat(), 'duration_minutes': 30, 'location_or_url': 'Office meeting room'}).json()['interview']
    with SessionLocal() as db:
        completed = Interview(application_id=application['id'], starts_at=now() - dt.timedelta(days=2), duration_minutes=30, location_or_url='Office meeting room', status='completed', rsvp='accepted')
        db.add(completed)
        db.commit()
        completed_id = completed.id
    sent = offer(company, application)
    assert candidate.patch('/api/hiring/offers/' + sent['id'], json={'status': 'accepted'}).status_code == 200
    assert company.patch(url + '/stage', json={'stage': 'hired'}).status_code == 200
    statuses = {item['id']: item['status'] for item in candidate.get(url).json()['interviews']}
    assert statuses[pending['id']] == 'cancelled'
    assert statuses[completed_id] == 'completed'
    assert candidate.get('/api/hiring/dashboard').json()['counts']['upcoming_interviews'] == 0
    assert company.get('/api/hiring/dashboard').json()['counts']['upcoming_interviews'] == 0
