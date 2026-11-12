"""Candidate-supplied work preferences, with separate opt-ins for sensitive declarations."""
import copy
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .countries import ENGAGEMENT_TYPES, WORK_MODES, catalogs, validate_country, validate_region
from .preference_models import CandidatePreference
from .preference_schemas import PreferencesInput


def _authorization_view(declaration):
    value = copy.deepcopy(declaration)
    until = value.get('valid_until')
    expired = bool(until and dt.date.fromisoformat(until) < dt.datetime.now(dt.timezone.utc).date())
    value['expired'] = expired
    value['self_declared'] = True
    return value


def _stored(profile_id, db):
    record = db.scalar(select(CandidatePreference).where(CandidatePreference.profile_id == profile_id)
                       .execution_options(populate_existing=True))
    return copy.deepcopy(record.data) if record else None


def professional_preferences(profile_id, db):
    """Caller must already authorize profile access; this helper adds no visibility grant.

    Work preferences may accompany an intentionally published/application-shared profile.
    Nationalities and authorizations each require a separate explicit sharing flag.
    Permit notes are always private and are never returned by this function.
    """
    data = _stored(profile_id, db)
    if data is None:
        return {}
    safe = {key: value for key, value in data.items() if key not in {
        'nationalities', 'work_authorizations', 'share_nationality', 'share_work_authorization'}}
    if data.get('share_nationality') is True:
        safe['nationalities'] = data.get('nationalities', [])
    if data.get('share_work_authorization') is True:
        safe['work_authorizations'] = [{key: value for key, value in _authorization_view(item).items() if key != 'notes'}
                                       for item in data.get('work_authorizations', [])]
        safe['work_authorization_notice'] = 'Self-declared and unverified. Region scope is not proof of legal work rights; expired declarations do not establish current authorization.'
    return safe


def export_preferences(user, db):
    if user.role != 'candidate' or not user.profile:
        return None
    return _stored(user.profile.id, db)


def filter_preferences(profiles, db, *, engagement_type='', work_mode='', relocation=None,
                       sponsorship_need='', authorization_country='', authorization_region='',
                       preferred_country='', preferred_region=''):
    """Filter declarations, never determine legal eligibility or infer from nationality.

    Authorization filters require explicit sharing, exact scope, a positive self-declared
    status, and a non-expired declaration. Region and country scopes never imply each other.
    The caller must first enforce directory visibility and authorization to view profiles.
    """
    try:
        if engagement_type and engagement_type not in ENGAGEMENT_TYPES:
            raise ValueError('Choose a supported engagement type.')
        if work_mode and work_mode not in WORK_MODES:
            raise ValueError('Choose a supported work arrangement.')
        if sponsorship_need and sponsorship_need not in {'not_required', 'required', 'discuss', 'not_specified'}:
            raise ValueError('Choose a supported sponsorship preference.')
        authorization_country = validate_country(authorization_country) if authorization_country else ''
        authorization_region = validate_region(authorization_region) if authorization_region else ''
        preferred_country = validate_country(preferred_country) if preferred_country else ''
        preferred_region = validate_region(preferred_region) if preferred_region else ''
        if relocation is not None and not isinstance(relocation, bool):
            raise ValueError('Relocation must be true or false.')
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    values = list(profiles)
    if not any([engagement_type, work_mode, sponsorship_need, authorization_country, authorization_region,
                preferred_country, preferred_region, relocation is not None]):
        return values
    records = {item.profile_id: item.data for item in db.scalars(select(CandidatePreference)
               .where(CandidatePreference.profile_id.in_([profile.id for profile in values]))
               .execution_options(populate_existing=True)).all()} if values else {}
    result = []
    for profile in values:
        data = records.get(profile.id, {})
        if engagement_type and engagement_type not in data.get('engagement_types', []):
            continue
        if work_mode and work_mode not in data.get('work_modes', []):
            continue
        if relocation is not None and data.get('willing_to_relocate') is not relocation:
            continue
        if sponsorship_need and data.get('sponsorship_need') != sponsorship_need:
            continue
        if preferred_country and preferred_country not in data.get('preferred_countries', []):
            continue
        if preferred_region and preferred_region not in data.get('preferred_regions', []):
            continue
        if authorization_country or authorization_region:
            if data.get('share_work_authorization') is not True:
                continue
            declarations = [item for item in data.get('work_authorizations', [])
                            if item.get('status') in {'unrestricted', 'permit_held'} and not _authorization_view(item)['expired']]
            if authorization_country and not any(item.get('scope_type') == 'country' and item.get('scope_code') == authorization_country for item in declarations):
                continue
            if authorization_region and not any(item.get('scope_type') == 'region' and item.get('scope_code') == authorization_region for item in declarations):
                continue
        result.append(profile)
    return result


def build_router():
    # Imported here after main's dependencies are defined; avoids module import cycles.
    from .main import candidate_user, get_db, rate_limit
    router = APIRouter(prefix='/api/hiring', tags=['Work preferences'])

    @router.get('/catalogs')
    def get_catalogs():
        return catalogs()

    @router.get('/preferences')
    def get_preferences(user=Depends(candidate_user), db: Session = Depends(get_db)):
        if not user.profile:
            raise HTTPException(404, 'Candidate profile was not found.')
        data = _stored(user.profile.id, db) or PreferencesInput().model_dump(mode='json')
        return {'preferences': data,
                'authorization_status': [_authorization_view(item) for item in data.get('work_authorizations', [])],
                'privacy_notice': 'Professional work preferences accompany your shared profile. Nationality and authorization declarations are private unless you opt in separately. Permit notes remain private. These fields never enter the evidence score or AI review.'}

    @router.put('/preferences')
    def put_preferences(payload: PreferencesInput, request: Request, user=Depends(candidate_user), db: Session = Depends(get_db)):
        rate_limit(request, 'candidate-preferences', 60, 3600, user.id)
        if not user.profile:
            raise HTTPException(404, 'Candidate profile was not found.')
        record = db.get(CandidatePreference, user.profile.id)
        if record is None:
            record = CandidatePreference(profile_id=user.profile.id)
            db.add(record)
        record.data = payload.model_dump(mode='json')
        db.commit()
        return {'preferences': copy.deepcopy(record.data),
                'authorization_status': [_authorization_view(item) for item in record.data.get('work_authorizations', [])]}

    return router
