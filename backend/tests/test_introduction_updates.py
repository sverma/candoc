import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.hiring_models import Notification
from app.introduction_updates import IntroductionNotification, backfill_introduction_updates
from app.main import app
from app.models import Introduction, User, now
from app.security import COOKIE_NAME
from test_api import register


@pytest.fixture
def parties():
    with ExitStack() as stack:
        clients = [stack.enter_context(TestClient(app, headers={'Origin': 'http://testserver'})) for _ in range(3)]
        candidate, company, outsider = clients
        users = [register(candidate, 'candidate@example.com'), register(company, 'company@example.com', 'company'),
                 register(outsider, 'outsider@example.com', 'company')]
        profile = candidate.put('/api/profile', json={'visible': True, 'headline': 'Platform engineer'}).json()['profile']
        yield candidate, company, outsider, users, profile


def send(company, profile):
    response = company.post('/api/introductions', json={'candidate_id': profile['id'], 'role_title': 'Platform engineer',
        'message': 'We would like to discuss a platform engineering opportunity with you.'})
    assert response.status_code == 201, response.text
    return response.json()['introduction']


def feed(client):
    response = client.get('/api/hiring/notifications')
    assert response.status_code == 200
    return response.json()


def test_request_is_in_both_participants_updates_dashboard_and_export(parties):
    candidate, company, outsider, users, profile = parties
    introduction = send(company, profile)
    for client, kind in [(candidate, 'introduction_received'), (company, 'introduction_sent')]:
        result = feed(client)
        assert result['unread_count'] == 1
        item = result['notifications'][0]
        assert item['introduction_id'] == introduction['id'] and item['kind'] == kind
        assert item['application_id'] is None and item['job_id'] is None
        assert 'contact_email' not in item and '@example.com' not in item['body']
        assert client.get('/api/hiring/dashboard').json()['counts']['unread_notifications'] == 1
        assert client.get('/api/account/export').json()['hiring']['notifications'][0]['id'] == item['id']
    assert feed(outsider) == {'notifications': [], 'unread_count': 0}
    assert candidate.get('/api/introductions', params={'introduction_id': introduction['id']}).json()['introductions'][0]['id'] == introduction['id']
    assert outsider.get('/api/introductions', params={'introduction_id': introduction['id']}).json()['introductions'] == []
    assert company.post('/api/introductions', json={'candidate_id': profile['id'], 'role_title': 'Engineer',
        'message': 'Another request must not create duplicate pending updates.'}).status_code == 409
    assert feed(candidate)['unread_count'] == 1


@pytest.mark.parametrize('status', ['accepted', 'declined'])
def test_response_creates_one_update_for_each_participant_and_replay_is_rejected(parties, status):
    candidate, company, outsider, users, profile = parties
    introduction = send(company, profile)
    url = '/api/introductions/' + introduction['id']
    assert outsider.patch(url, json={'status': status}).status_code == 403
    assert candidate.patch(url, json={'status': status}).status_code == 200
    for client in [candidate, company]:
        result = feed(client)
        assert result['unread_count'] == 2
        assert result['notifications'][0]['kind'] == 'introduction_' + status
        assert result['notifications'][0]['introduction_id'] == introduction['id']
    assert candidate.patch(url, json={'status': status}).status_code == 409
    assert feed(company)['unread_count'] == 2


def test_combined_feed_read_controls_are_recipient_scoped(parties):
    candidate, company, outsider, users, profile = parties
    send(company, profile)
    with SessionLocal() as db:
        db.add(Notification(recipient_id=users[1]['id'], kind='message', body='An existing hiring update.'))
        db.commit()
    assert feed(company)['unread_count'] == 2
    assert feed(company)['notifications'][0]['kind'] == 'message'
    notification = feed(candidate)['notifications'][0]
    path = '/api/hiring/notifications/' + notification['id']
    assert company.patch(path, json={'read': True}).status_code == 404
    assert outsider.patch(path, json={'read': True}).status_code == 404
    assert candidate.patch(path, json={'read': True}).status_code == 200
    assert feed(candidate)['unread_count'] == 0 and feed(company)['unread_count'] == 2
    assert company.post('/api/hiring/notifications/read-all').status_code == 200
    assert feed(company)['unread_count'] == 0
    assert all(item['read'] for item in feed(company)['notifications'])
    assert company.get('/api/hiring/dashboard').json()['counts']['unread_notifications'] == 0


def test_backfill_preserves_original_time_status_and_read_state_without_duplicate_delivery(parties):
    candidate, company, outsider, users, profile = parties
    created = now() - dt.timedelta(days=2)
    with SessionLocal() as db:
        item = Introduction(candidate_id=profile['id'], company_user_id=users[1]['id'], role_title='Existing role',
                            message='An existing introduction before Updates integration.', created_at=created, status='accepted')
        db.add(item)
        db.commit()
        introduction_id = item.id
        assert backfill_introduction_updates(db) == 2
        db.commit()
    first = feed(candidate)['notifications'][0]
    assert first['introduction_id'] == introduction_id and first['kind'] == 'introduction_received'
    assert dt.datetime.fromisoformat(first['created_at']) == created
    assert candidate.patch('/api/hiring/notifications/' + first['id'], json={'read': True}).status_code == 200
    with SessionLocal() as db:
        assert backfill_introduction_updates(db) == 0
        db.commit()
        assert db.get(Introduction, introduction_id).status == 'accepted'
        assert db.scalar(select(func.count()).select_from(IntroductionNotification)) == 2
    after = feed(candidate)
    assert after['notifications'][0]['id'] == first['id'] and after['unread_count'] == 0
    assert candidate.get('/api/introductions').json()['introductions'][0]['status'] == 'accepted'


@pytest.mark.parametrize('deleted_party', ['candidate', 'company'])
def test_deleting_either_participant_removes_updates_for_both(parties, deleted_party):
    candidate, company, outsider, users, profile = parties
    introduction = send(company, profile)
    candidate.patch('/api/introductions/' + introduction['id'], json={'status': 'accepted'})
    removed, remaining = (candidate, company) if deleted_party == 'candidate' else (company, candidate)
    assert removed.delete('/api/account').status_code == 200
    assert feed(remaining) == {'notifications': [], 'unread_count': 0}
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(IntroductionNotification)) == 0


def test_concurrent_response_records_one_decision_only(parties):
    candidate, company, outsider, users, profile = parties
    introduction = send(company, profile)
    cookie = candidate.cookies.get(COOKIE_NAME)
    def respond(status):
        with TestClient(app, headers={'Origin': 'http://testserver', 'Cookie': COOKIE_NAME + '=' + cookie}) as browser:
            return browser.patch('/api/introductions/' + introduction['id'], json={'status': status}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(respond, ['accepted', 'declined'])) == [200, 409]
    updates = feed(company)['notifications']
    assert len(updates) == 2
    assert len([item for item in updates if item['kind'] in {'introduction_accepted', 'introduction_declined'}]) == 1


def test_feed_cap_does_not_cap_unread_count_or_export(parties):
    candidate, company, outsider, users, profile = parties
    with SessionLocal() as db:
        for number in range(205):
            db.add(Introduction(candidate_id=profile['id'], company_user_id=users[1]['id'],
                role_title='Historical role ' + str(number), message='Existing introduction history.',
                created_at=now() - dt.timedelta(days=205 - number)))
        db.commit()
        assert backfill_introduction_updates(db) == 410
        db.add(Notification(recipient_id=users[0]['id'], kind='interview', body='A newer hiring update.'))
        db.commit()
    result = feed(candidate)
    assert len(result['notifications']) == 200 and result['unread_count'] == 206
    assert result['notifications'][0]['kind'] == 'interview'
    assert len(candidate.get('/api/account/export').json()['hiring']['notifications']) == 206
    assert candidate.post('/api/hiring/notifications/read-all').status_code == 200
    assert feed(candidate)['unread_count'] == 0
