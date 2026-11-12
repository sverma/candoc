import datetime as dt

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.countries import COUNTRY_CODES, CURRENCY_CODES, REGION_CODES, catalogs, validate_country, validate_currency, validate_region
from app.database import SessionLocal
from app.models import Profile, User
from app.preference_models import CandidatePreference
from app.preference_schemas import PreferencesInput
from app.preferences import export_preferences, filter_preferences, professional_preferences


def register(client, email='mobility@example.test', role='candidate'):
    body = {'email': email, 'password': 'sufficiently-strong-password', 'name': 'Avery Example', 'role': role}
    if role == 'company':
        body['company_name'] = 'Example Company'
    response = client.post('/api/auth/register', json=body)
    assert response.status_code == 201, response.text
    return response.json()['user']


def profile_id(client):
    return client.get('/api/profile').json()['profile']['id']


def declaration(**updates):
    value = {'scope_type': 'country', 'scope_code': 'DE', 'status': 'permit_held',
             'valid_until': '2000-01-01', 'notes': 'Private permit note never shared'}
    value.update(updates)
    return value


def test_complete_catalogs_and_country_region_currency_separation():
    value = catalogs()
    assert len(value['countries']) == 249
    assert len(value['currencies']) >= 170
    assert {'IN', 'US', 'GB', 'DE', 'JP', 'ZA', 'BR', 'AU'} <= COUNTRY_CODES
    assert {'INR', 'USD', 'EUR', 'GBP', 'JPY'} <= CURRENCY_CODES
    assert {'EU', 'EEA', 'EUROPE', 'NORTH_AMERICA', 'SOUTH_AMERICA', 'APAC', 'MIDDLE_EAST', 'AFRICA', 'GLOBAL'} == REGION_CODES
    assert validate_country(' in ') == 'IN'
    assert validate_currency('eur') == 'EUR'
    assert validate_region('eea') == 'EEA'
    assert len(value['engagement_types']) == 8
    assert 'never work authorization' in value['geography_notice']
    for validator, code in [(validate_country, 'EU'), (validate_region, 'IN'), (validate_currency, 'ZZZ')]:
        with pytest.raises(ValueError):
            validator(code)


def test_defaults_private_and_role_access(client, other_client):
    assert client.get('/api/hiring/preferences').status_code == 401
    register(client)
    own = client.get('/api/hiring/preferences')
    assert own.status_code == 200, own.text
    value = own.json()['preferences']
    assert value['nationalities'] == []
    assert value['work_authorizations'] == []
    assert value['share_nationality'] is False
    assert value['share_work_authorization'] is False
    register(other_client, 'employer@example.test', 'company')
    assert other_client.get('/api/hiring/preferences').status_code == 403
    assert other_client.put('/api/hiring/preferences', json={}).status_code == 403


def test_sensitive_declarations_private_unless_each_flag_and_never_inferred(client):
    register(client)
    identifier = profile_id(client)
    saved = client.put('/api/hiring/preferences', json={'nationalities': ['IN'], 'work_authorizations': [declaration()],
        'preferred_regions': ['EU'], 'preferred_countries': ['DE'], 'sponsorship_need': 'discuss'})
    assert saved.status_code == 200, saved.text
    assert saved.json()['authorization_status'][0]['expired'] is True
    with SessionLocal() as db:
        public = professional_preferences(identifier, db)
        assert 'nationalities' not in public
        assert 'work_authorizations' not in public
        assert 'Private permit note' not in str(public)
        assert public['preferred_regions'] == ['EU']
        assert public['preferred_countries'] == ['DE']
    # Sharing nationality must not implicitly share authorization, nor invent rights.
    data = saved.json()['preferences']
    data['share_nationality'] = True
    client.put('/api/hiring/preferences', json=data)
    with SessionLocal() as db:
        public = professional_preferences(identifier, db)
        assert public['nationalities'] == ['IN']
        assert 'work_authorizations' not in public
    data.update(share_nationality=False, share_work_authorization=True)
    client.put('/api/hiring/preferences', json=data)
    with SessionLocal() as db:
        public = professional_preferences(identifier, db)
        assert 'nationalities' not in public
        assert public['work_authorizations'][0]['scope_code'] == 'DE'
        assert public['work_authorizations'][0]['expired'] is True
        assert public['work_authorizations'][0]['self_declared'] is True
        assert 'notes' not in public['work_authorizations'][0]
        assert 'not proof' in public['work_authorization_notice']


def test_region_scope_declared_not_granted_and_no_nationality_inference(client):
    register(client)
    identifier = profile_id(client)
    response = client.put('/api/hiring/preferences', json={'nationalities': ['DE'], 'preferred_regions': ['EEA'],
        'share_work_authorization': True, 'work_authorizations': [declaration(scope_type='region', scope_code='EEA', status='unknown', valid_until=None)]})
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        public = professional_preferences(identifier, db)
        assert public['work_authorizations'] == [{'scope_type': 'region', 'scope_code': 'EEA', 'status': 'unknown', 'valid_until': None, 'expired': False, 'self_declared': True}]
        assert 'nationalities' not in public
        assert len(public['work_authorizations']) == 1


def test_full_replace_clears_private_data_and_revokes_sharing_on_next_read(client):
    register(client)
    identifier = profile_id(client)
    assert client.put('/api/hiring/preferences', json={'nationalities': ['IN'], 'share_nationality': True, 'share_work_authorization': True, 'work_authorizations': [declaration()]}).status_code == 200
    replaced = client.put('/api/hiring/preferences', json={'preferred_title': 'Product engineer'})
    assert replaced.status_code == 200
    value = replaced.json()['preferences']
    assert value['nationalities'] == [] and value['work_authorizations'] == []
    assert value['share_nationality'] is False and value['share_work_authorization'] is False
    with SessionLocal() as db:
        assert 'nationalities' not in professional_preferences(identifier, db)
        assert 'work_authorizations' not in professional_preferences(identifier, db)


def test_all_engagement_modes_and_professional_fields_round_trip(client):
    register(client)
    body = {'engagement_types': ['permanent', 'contract', 'freelance', 'consulting', 'temporary', 'internship', 'apprenticeship', 'volunteer'],
        'work_modes': ['remote', 'hybrid', 'onsite'], 'time_commitment': 'part_time',
        'preferred_countries': ['in', 'US', 'IN'], 'preferred_regions': ['APAC', 'GLOBAL'],
        'willing_to_relocate': True, 'relocation_countries': ['DE'], 'relocation_regions': ['EUROPE'],
        'timezone': 'Asia/Kolkata', 'languages': [{'name': 'Hindi', 'proficiency': 'native'}, {'name': 'English', 'proficiency': 'professional'}],
        'available_from': '2027-02-01', 'notice_days': 30, 'hours_per_week': 20, 'compensation_min': 100, 'compensation_max': 150,
        'currency': 'usd', 'pay_period': 'hour', 'portfolio_url': 'https://portfolio.example.test/work', 'preferred_title': 'Consulting engineer'}
    response = client.put('/api/hiring/preferences', json=body)
    assert response.status_code == 200, response.text
    value = client.get('/api/hiring/preferences').json()['preferences']
    assert value['preferred_countries'] == ['IN', 'US']
    assert value['currency'] == 'USD'
    assert value['notice_days'] == 30
    assert len(value['engagement_types']) == 8
    assert value['languages'] == body['languages']


@pytest.mark.parametrize('body', [
    {'nationalities': ['EU']}, {'preferred_regions': ['IN']}, {'relocation_countries': ['ZZ']},
    {'work_authorizations': [declaration(scope_type='country', scope_code='EEA')]},
    {'work_authorizations': [declaration(scope_type='region', scope_code='DE')]},
    {'work_authorizations': [declaration(status='eligible')]},
    {'work_authorizations': [declaration(), declaration()]}, {'notice_days': -1}, {'notice_days': 366},
    {'hours_per_week': 169}, {'compensation_min': -1}, {'compensation_min': 100, 'compensation_max': 50, 'currency': 'USD'},
    {'compensation_min': 100}, {'currency': 'ZZZ'}, {'timezone': '../../etc/passwd'},
    {'portfolio_url': 'javascript:alert(1)'}, {'portfolio_url': 'https://user:password@example.test'},
    {'share_nationality': 'true'}, {'share_work_authorization': 1}, {'engagement_types': ['gig']},
    {'languages': [{'name': 'English', 'proficiency': 'expert'}]},
    {'languages': [{'name': 'English'}, {'name': 'english'}]}, {'unknown_private_field': True},
])
def test_invalid_geography_permissions_ranges_and_inputs_rejected(client, body):
    register(client)
    response = client.put('/api/hiring/preferences', json=body)
    assert response.status_code == 422, response.text


def test_nan_and_infinite_compensation_not_stored():
    for value in [float('nan'), float('inf'), float('-inf')]:
        with pytest.raises(ValidationError):
            PreferencesInput(compensation_min=value, currency='USD')


def test_tenant_isolation_full_export_and_delete_cascade(client, other_client):
    first = register(client)
    identifier = profile_id(client)
    body = {'nationalities': ['IN'], 'work_authorizations': [declaration()], 'preferred_title': 'First candidate'}
    client.put('/api/hiring/preferences', json=body)
    second = register(other_client, 'second@example.test')
    other_client.put('/api/hiring/preferences', json={'nationalities': ['JP'], 'preferred_title': 'Second candidate'})
    assert other_client.get('/api/hiring/preferences').json()['preferences']['nationalities'] == ['JP']
    assert client.get('/api/hiring/preferences').json()['preferences']['nationalities'] == ['IN']
    with SessionLocal() as db:
        exported = export_preferences(db.get(User, first['id']), db)
        assert exported['nationalities'] == ['IN']
        assert exported['work_authorizations'][0]['notes'] == declaration()['notes']
        assert export_preferences(db.get(User, second['id']), db)['nationalities'] == ['JP']
    assert client.delete('/api/account').status_code == 200
    with SessionLocal() as db:
        assert db.get(CandidatePreference, identifier) is None
        assert db.scalar(select(CandidatePreference)) is not None


def test_preferences_do_not_mutate_assessment_or_source_data(client):
    register(client)
    identifier = profile_id(client)
    sentinel = {'score': 3.5, 'version': 'preserved', 'sources': []}
    with SessionLocal() as db:
        profile = db.get(Profile, identifier)
        profile.assessment = sentinel
        db.commit()
    response = client.put('/api/hiring/preferences', json={'nationalities': ['IN'], 'work_authorizations': [declaration()], 'preferred_regions': ['EU']})
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(Profile, identifier).assessment == sentinel


def test_directory_filters_require_shared_current_declaration_and_no_nationality_inference(client, other_client):
    register(client)
    first_id = profile_id(client)
    register(other_client, 'other-mobility@example.test')
    second_id = profile_id(other_client)
    client.put('/api/hiring/preferences', json={'nationalities': ['DE'], 'share_nationality': True,
        'share_work_authorization': True, 'work_authorizations': [declaration(scope_code='US', valid_until='2099-01-01')],
        'engagement_types': ['contract'], 'work_modes': ['remote'], 'willing_to_relocate': True,
        'sponsorship_need': 'discuss', 'preferred_countries': ['US'], 'preferred_regions': ['NORTH_AMERICA']})
    other_client.put('/api/hiring/preferences', json={'nationalities': ['US'], 'share_work_authorization': False,
        'work_authorizations': [declaration(scope_code='US', valid_until='2099-01-01')], 'engagement_types': ['permanent']})
    with SessionLocal() as db:
        profiles = [db.get(Profile, first_id), db.get(Profile, second_id)]
        assert [item.id for item in filter_preferences(profiles, db, authorization_country='US')] == [first_id]
        assert not filter_preferences(profiles, db, authorization_country='DE')
        assert not filter_preferences(profiles, db, authorization_region='NORTH_AMERICA')
        assert [item.id for item in filter_preferences(profiles, db, engagement_type='contract', work_mode='remote', relocation=True, sponsorship_need='discuss')] == [first_id]
        assert [item.id for item in filter_preferences(profiles, db, preferred_country='US', preferred_region='NORTH_AMERICA')] == [first_id]
    payload = client.get('/api/hiring/preferences').json()['preferences']
    payload['work_authorizations'][0]['valid_until'] = '2000-01-01'
    client.put('/api/hiring/preferences', json=payload)
    with SessionLocal() as db:
        assert not filter_preferences([db.get(Profile, first_id)], db, authorization_country='US')
    payload['work_authorizations'] = [declaration(scope_type='region', scope_code='EU', valid_until=None, status='unknown')]
    client.put('/api/hiring/preferences', json=payload)
    with SessionLocal() as db:
        assert not filter_preferences([db.get(Profile, first_id)], db, authorization_region='EU')


@pytest.mark.parametrize('kwargs', [{'authorization_country': 'EU'}, {'authorization_region': 'IN'}, {'preferred_country': 'ZZ'},
    {'engagement_type': 'unknown'}, {'work_mode': 'unknown'}, {'sponsorship_need': 'unknown'}, {'relocation': 'true'}])
def test_invalid_directory_filter_is_error_not_eligibility_decision(kwargs):
    from fastapi import HTTPException
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc:
            filter_preferences([], db, **kwargs)
        assert exc.value.status_code == 422


def test_company_directory_filters_shared_current_declarations_and_never_exposes_private_nationality(client, other_client):
    from fastapi.testclient import TestClient
    from app.main import app
    register(client)
    first_id = profile_id(client)
    client.put('/api/profile', json={'visible': True, 'headline': 'Product engineer'})
    client.put('/api/hiring/preferences', json={'nationalities': ['DE'], 'work_authorizations': [declaration(scope_code='US', valid_until='2099-01-01')],
        'engagement_types': ['contract'], 'work_modes': ['remote'], 'share_work_authorization': False})
    with SessionLocal() as db:
        db.get(Profile, first_id).assessment = {'score': 3.5, 'version': 'unchanged', 'sources': []}
        db.commit()
    with TestClient(app, headers={'Origin': 'http://testserver'}) as second_client:
        register(second_client, 'expired-mobility@example.test')
        second_id = profile_id(second_client)
        second_client.put('/api/profile', json={'visible': True, 'headline': 'Research engineer'})
        second_client.put('/api/hiring/preferences', json={'nationalities': ['US'], 'share_work_authorization': True,
            'work_authorizations': [declaration(scope_code='US', valid_until='2000-01-01')]})
        register(other_client, 'hiring-company@example.test', 'company')
        assert other_client.get('/api/candidates?authorization_country=US').json()['candidates'] == []
        saved = client.get('/api/hiring/preferences').json()['preferences']
        saved['share_work_authorization'] = True
        client.put('/api/hiring/preferences', json=saved)
        results = other_client.get('/api/candidates?authorization_country=US&engagement_type=contract&work_mode=remote').json()['candidates']
        assert [item['id'] for item in results] == [first_id]
        summary = results[0]['work_preferences']
        assert 'nationalities' not in summary
        assert 'notes' not in summary['work_authorizations'][0]
        assert summary['work_authorizations'][0]['expired'] is False
        assert results[0]['assessment']['score'] == 3.5
        assert other_client.get('/api/candidates?authorization_region=EU').json()['candidates'] == []
        # Unknown nationality query parameters do not produce a demographic filter.
        all_candidates = other_client.get('/api/candidates?nationality=US').json()['candidates']
        assert {item['id'] for item in all_candidates} == {first_id, second_id}
        assert all('nationalities' not in item['work_preferences'] for item in all_candidates)
        saved['share_work_authorization'] = False
        client.put('/api/hiring/preferences', json=saved)
        assert other_client.get('/api/candidates?authorization_country=US').json()['candidates'] == []
        assert client.get('/api/profile').json()['profile']['assessment']['score'] == 3.5
