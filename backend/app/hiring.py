"""Participant-controlled hiring workspace. No automatic hiring/eligibility decisions."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import String, and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from .models import Profile, User, now
from .hiring_models import Application, CompanyProfile, Interview, Job, Message, Notification, Offer, SavedJob
from .introduction_updates import IntroductionNotification
from . import hiring_schemas as S

TERMINAL = {'hired', 'rejected', 'withdrawn', 'declined'}
ACTIVE = {'applied', 'reviewing', 'interviewing', 'offer'}
JOB_FIELDS = list(S.JobCreate.model_fields)
OFFER_FIELDS = list(S.OfferCreate.model_fields)


def utc(value):
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value.astimezone(dt.timezone.utc)


def iso(value):
    return utc(value).isoformat() if value else None


def company_json(user, db):
    profile = db.get(CompanyProfile, user.id)
    result = {'id': user.id, 'name': user.company_name or user.name, 'website': '', 'industry': '', 'size': '', 'headquarters': '', 'about': ''}
    if profile:
        result.update({key: getattr(profile, key) for key in S.CompanyUpdate.model_fields})
    try:
        from .verification import is_email_verified
        result['email_verified'] = is_email_verified(user.id, db)
    except ImportError:
        result['email_verified'] = False
    return result


def job_json(job, db, viewer=None):
    company = db.get(User, job.company_id)
    company_data = company_json(company, db)
    result = {key: getattr(job, key) for key in JOB_FIELDS}
    result.update(id=job.id, company_id=job.company_id, company_name=company_data['name'],
                  company=company_data, created_at=iso(job.created_at), updated_at=iso(job.updated_at), saved=False)
    if viewer and viewer.role == 'candidate':
        result['saved'] = db.get(SavedJob, (viewer.id, job.id)) is not None
    if viewer and viewer.id == job.company_id:
        result['application_count'] = db.scalar(select(func.count()).select_from(Application).where(Application.job_id == job.id))
    return result


def _profile_json(profile, share_contact=False):
    from .main import profile_json, redact_contact
    result = profile_json(profile)
    if not share_contact:
        for key in ['name', 'headline', 'bio', 'skills']:
            result[key] = redact_contact(result[key])
    return result


def application_json(item, db, viewer):
    job = db.get(Job, item.job_id)
    profile = db.get(Profile, item.candidate_id)
    candidate = db.get(User, profile.user_id)
    professional = viewer.id == profile.user_id or item.professional_access or profile.visible
    result = {'id': item.id, 'job_id': job.id, 'job_title': job.title, 'title': job.title,
              'company_id': job.company_id, 'company_name': company_json(db.get(User, job.company_id), db)['name'],
              'candidate_id': profile.id, 'candidate_name': candidate.name, 'stage': item.stage, 'origin': item.origin,
              'message': item.initial_message, 'share_contact': item.share_contact,
              'candidate': _profile_json(profile, item.share_contact) if professional else None,
              'job': job_json(job, db, viewer), 'created_at': iso(item.created_at), 'updated_at': iso(item.updated_at)}
    if item.share_contact:
        result['contact_email'] = candidate.email
    return result


def message_json(item, db):
    sender = db.get(User, item.sender_id)
    return {'id': item.id, 'application_id': item.application_id, 'sender_id': item.sender_id,
            'sender_name': sender.name, 'sender_role': sender.role, 'body': item.body, 'created_at': iso(item.created_at)}


def interview_json(item):
    return {**{key: getattr(item, key) for key in ['id', 'application_id', 'duration_minutes', 'location_or_url', 'notes', 'status', 'rsvp']},
            'starts_at': iso(item.starts_at), 'ends_at': iso(utc(item.starts_at) + dt.timedelta(minutes=item.duration_minutes)),
            'created_at': iso(item.created_at), 'updated_at': iso(item.updated_at)}


def offer_json(item):
    result = {key: getattr(item, key) for key in OFFER_FIELDS if key not in {'start_date', 'expires_at'}}
    # Expiry is effective on every read, without a background worker or mutation on GET.
    status = 'expired' if item.status == 'sent' and item.expires_at and utc(item.expires_at) <= now() else item.status
    result.update(id=item.id, application_id=item.application_id, status=status,
                  start_date=item.start_date.isoformat() if item.start_date else None, expires_at=iso(item.expires_at),
                  created_at=iso(item.created_at), updated_at=iso(item.updated_at))
    return result


def notification_json(item):
    return {**{key: getattr(item, key) for key in ['id', 'kind', 'body', 'read']},
            'application_id': getattr(item, 'application_id', None), 'job_id': getattr(item, 'job_id', None),
            'introduction_id': getattr(item, 'introduction_id', None), 'created_at': iso(item.created_at)}


def notification_items(user_id, db, limit=None):
    rows = []
    for model in [Notification, IntroductionNotification]:
        query = select(model).where(model.recipient_id == user_id).order_by(model.created_at.desc(), model.id.desc())
        rows.extend(db.scalars(query.limit(limit) if limit is not None else query).all())
    rows.sort(key=lambda item: (utc(item.created_at), item.id), reverse=True)
    return rows[:limit] if limit is not None else rows


def unread_notifications(user_id, db):
    return sum(db.scalar(select(func.count()).select_from(model).where(
        model.recipient_id == user_id, model.read.is_(False)))
        for model in [Notification, IntroductionNotification])


def notify(db, recipient, kind, body, application=None, job=None):
    db.add(Notification(recipient_id=recipient, kind=kind, body=body[:500], application_id=application.id if application else None,
                        job_id=job.id if job else application.job_id if application else None))


def validate_compensation(values):
    from .countries import validate_currency
    minimum, maximum = values.get('compensation_min'), values.get('compensation_max')
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(422, 'Minimum compensation cannot exceed maximum compensation.')
    currency = values.get('currency', '')
    try:
        values['currency'] = validate_currency(currency) if currency else ''
    except ValueError:
        raise HTTPException(422, 'Choose a supported ISO currency.')
    if (minimum is not None or maximum is not None) and not values['currency']:
        raise HTTPException(422, 'Choose a currency when compensation is specified.')
    return values


def validate_job(values):
    from .countries import validate_country, validate_region
    try:
        values = S.JobCreate(**values).model_dump()
        values['country_codes'] = [validate_country(code) for code in values['country_codes']]
        values['region_codes'] = [validate_region(code) for code in values['region_codes']]
    except (ValidationError, ValueError):
        raise HTTPException(422, 'Check the role fields, country/region codes and numeric limits.')
    validate_compensation(values)
    if values['status'] == 'published' and values['work_mode'] in {'onsite', 'hybrid'} and not values['country_codes']:
        raise HTTPException(422, 'Published onsite or hybrid roles must name at least one country.')
    return values


def verified(user, db):
    from .verification import require_verified_email
    require_verified_email(user, db)


def application_query(user):
    query = select(Application).join(Job, Job.id == Application.job_id).join(Profile, Profile.id == Application.candidate_id)
    return query.where(Job.company_id == user.id) if user.role == 'company' else query.where(Profile.user_id == user.id)


def export_hiring(user, db):
    applications = db.scalars(application_query(user)).all()
    ids = [item.id for item in applications]
    result = {'applications': [application_json(item, db, user) for item in applications],
              'messages': [message_json(item, db) for item in db.scalars(select(Message).where(Message.application_id.in_(ids))).all()],
              'interviews': [interview_json(item) for item in db.scalars(select(Interview).where(Interview.application_id.in_(ids))).all()],
              'offers': [offer_json(item) for item in db.scalars(select(Offer).where(Offer.application_id.in_(ids))).all()],
              'notifications': [notification_json(item) for item in notification_items(user.id, db)],
              'saved_jobs': [item.job_id for item in db.scalars(select(SavedJob).where(SavedJob.user_id == user.id)).all()]}
    if user.role == 'company':
        result['company'] = company_json(user, db)
        result['jobs'] = [job_json(item, db, user) for item in db.scalars(select(Job).where(Job.company_id == user.id)).all()]
    return result


def build_router():
    from .main import candidate_user, company_user, current_user, get_db, require_user, rate_limit
    router = APIRouter(prefix='/api/hiring', tags=['hiring'])

    def owned_job(job_id, user, db, lock=False):
        query = select(Job).where(Job.id == job_id, Job.company_id == user.id)
        job = db.scalar(query.with_for_update() if lock else query)
        if not job:
            raise HTTPException(404, 'Role was not found.')
        return job

    def participant(application_id, user, db, lock=False):
        query = application_query(user).where(Application.id == application_id)
        if lock:
            # PostgreSQL locks only the application, preserving a consistent order
            # for messages, stage changes, interview and offer actions.
            query = query.with_for_update(of=Application)
        item = db.scalar(query)
        if not item:
            raise HTTPException(404, 'Application was not found.')
        return item

    def other_party(item, user, db):
        job = db.get(Job, item.job_id)
        profile = db.get(Profile, item.candidate_id)
        return profile.user_id if user.role == 'company' else job.company_id

    def active(item, allow_invited=False):
        if item.stage not in ACTIVE and not (allow_invited and item.stage == 'invited'):
            raise HTTPException(409, 'This application is not active for that action.')

    @router.get('/company')
    def get_company(user=Depends(company_user), db=Depends(get_db)):
        return {'company': company_json(user, db)}

    @router.put('/company')
    def put_company(payload: S.CompanyUpdate, user=Depends(company_user), db=Depends(get_db)):
        # Lock the existing user so concurrent first-time saves cannot race insert.
        db.scalar(select(User).where(User.id == user.id).with_for_update())
        item = db.get(CompanyProfile, user.id)
        if not item:
            item = CompanyProfile(user_id=user.id, **payload.model_dump())
            db.add(item)
        else:
            for key, value in payload.model_dump().items():
                setattr(item, key, value)
        user.company_name = payload.name
        db.commit()
        return {'company': company_json(user, db)}

    @router.get('/jobs')
    def list_jobs(search: str = Query('', max_length=150), engagement_type: S.Engagement = None,
                  work_mode: S.WorkMode = None, country: str = Query('', max_length=3), region: str = Query('', max_length=30),
                  visa_sponsorship: S.Support = None, relocation_support: S.Support = None, saved: bool = False,
                  mine: bool = False, status: S.JobStatus = None, limit: int = Query(30, ge=1, le=100),
                  offset: int = Query(0, ge=0, le=100000), user=Depends(current_user), db=Depends(get_db)):
        from .countries import validate_country, validate_region
        query = select(Job).join(User, User.id == Job.company_id).outerjoin(CompanyProfile, CompanyProfile.user_id == User.id)
        if mine:
            if not user or user.role != 'company':
                raise HTTPException(403, 'Company sign-in is required for your roles.')
            query = query.where(Job.company_id == user.id)
        else:
            query = query.where(Job.status == 'published')
        if status:
            query = query.where(Job.status == status)
        if saved:
            if not user or user.role != 'candidate':
                raise HTTPException(403, 'Candidate sign-in is required for saved roles.')
            query = query.join(SavedJob, and_(SavedJob.job_id == Job.id, SavedJob.user_id == user.id))
        if search:
            query = query.where(or_(*(func.lower(column).contains(search.lower(), autoescape=True)
                                     for column in [Job.title, Job.description, func.coalesce(CompanyProfile.name, User.company_name)])))
        for value, column in [(engagement_type, Job.engagement_type), (work_mode, Job.work_mode),
                              (visa_sponsorship, Job.visa_sponsorship), (relocation_support, Job.relocation_support)]:
            if value:
                query = query.where(column == value)
        try:
            if country:
                query = query.where(Job.country_codes.cast(String).contains('"' + validate_country(country) + '"', autoescape=True))
            if region:
                query = query.where(Job.region_codes.cast(String).contains('"' + validate_region(region) + '"', autoescape=True))
        except ValueError:
            raise HTTPException(422, 'Choose a supported country or region.')
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.scalars(query.order_by(Job.created_at.desc()).offset(offset).limit(limit)).all()
        return {'jobs': [job_json(item, db, user) for item in rows], 'total': total}

    @router.post('/jobs', status_code=201)
    def create_job(payload: S.JobCreate, request: Request, user=Depends(company_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-job-create', 40, 3600, user.id)
        values = validate_job(payload.model_dump())
        if values['status'] == 'published':
            verified(user, db)
        job = Job(company_id=user.id, **values)
        db.add(job)
        db.commit()
        return {'job': job_json(job, db, user)}

    @router.get('/jobs/{job_id}')
    def get_job(job_id: str, user=Depends(current_user), db=Depends(get_db)):
        job = db.get(Job, job_id)
        owner = user and job and user.id == job.company_id
        applicant = user and job and user.role == 'candidate' and db.scalar(application_query(user).where(Application.job_id == job.id))
        if not job or (job.status != 'published' and not owner and not applicant):
            raise HTTPException(404, 'Role was not found.')
        return {'job': job_json(job, db, user)}

    @router.patch('/jobs/{job_id}')
    def patch_job(job_id: str, payload: S.JobPatch, user=Depends(company_user), db=Depends(get_db)):
        job = owned_job(job_id, user, db, True)
        values = validate_job({**{key: getattr(job, key) for key in JOB_FIELDS}, **payload.model_dump(exclude_unset=True)})
        if values['status'] == 'published' and job.status != 'published':
            verified(user, db)
        if job.status == 'closed' and values['status'] != 'closed':
            raise HTTPException(409, 'Closed roles cannot be reopened. Create a new role instead.')
        for key, value in values.items():
            setattr(job, key, value)
        db.commit()
        return {'job': job_json(job, db, user)}

    @router.put('/jobs/{job_id}/save')
    def save_job(job_id: str, payload: S.SaveJob, user=Depends(candidate_user), db=Depends(get_db)):
        job = db.get(Job, job_id)
        db.scalar(select(User).where(User.id == user.id).with_for_update())
        existing = db.get(SavedJob, (user.id, job_id))
        if not job or (job.status != 'published' and (payload.saved or not existing)):
            raise HTTPException(404, 'Published or previously saved role was not found.')
        if payload.saved and not existing:
            db.add(SavedJob(user_id=user.id, job_id=job.id))
        elif not payload.saved and existing:
            db.delete(existing)
        db.commit()
        return {'saved': payload.saved}

    @router.post('/jobs/{job_id}/apply', status_code=201)
    def apply_job(job_id: str, payload: S.Apply, request: Request, user=Depends(candidate_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-apply', 30, 3600, user.id)
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if not job or job.status != 'published':
            raise HTTPException(404, 'This role is not accepting applications.')
        if payload.share_contact:
            verified(user, db)
        item = Application(job_id=job.id, candidate_id=user.profile.id, stage='applied', origin='application',
                           initial_message=payload.message, share_contact=payload.share_contact, professional_access=True)
        db.add(item)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'An application or invitation already exists for this role.')
        notify(db, job.company_id, 'application', user.name + ' applied to ' + job.title + '.', item)
        db.commit()
        return {'application': application_json(item, db, user)}

    @router.post('/jobs/{job_id}/invite', status_code=201)
    def invite_candidate(job_id: str, payload: S.Invite, request: Request, user=Depends(company_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-invite', 30, 3600, user.id)
        job = owned_job(job_id, user, db, True)
        if job.status != 'published':
            raise HTTPException(409, 'Only published roles can send invitations.')
        profile = db.get(Profile, payload.candidate_id)
        if not profile or not profile.visible:
            raise HTTPException(404, 'A discoverable candidate was not found.')
        item = Application(job_id=job.id, candidate_id=profile.id, stage='invited', origin='invitation', initial_message=payload.message)
        db.add(item)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'An application or invitation already exists for this role.')
        notify(db, profile.user_id, 'invitation', company_json(user, db)['name'] + ' invited you to ' + job.title + '.', item)
        db.commit()
        return {'application': application_json(item, db, user)}

    @router.get('/applications')
    def list_applications(job_id: str = Query('', max_length=36), stage: str = Query('', max_length=20), user=Depends(require_user), db=Depends(get_db)):
        if stage and stage not in ACTIVE | TERMINAL | {'invited'}:
            raise HTTPException(422, 'Choose a valid application stage.')
        query = application_query(user)
        if job_id:
            query = query.where(Application.job_id == job_id)
        if stage:
            query = query.where(Application.stage == stage)
        return {'applications': [application_json(item, db, user) for item in db.scalars(query.order_by(Application.created_at.desc()).limit(500)).all()]}

    @router.get('/applications/{application_id}')
    def get_application(application_id: str, user=Depends(require_user), db=Depends(get_db)):
        item = participant(application_id, user, db)
        return {'application': application_json(item, db, user),
                'messages': [message_json(message, db) for message in db.scalars(select(Message).where(Message.application_id == item.id).order_by(Message.created_at)).all()],
                'interviews': [interview_json(interview) for interview in db.scalars(select(Interview).where(Interview.application_id == item.id).order_by(Interview.starts_at)).all()],
                'offers': [offer_json(offer) for offer in db.scalars(select(Offer).where(Offer.application_id == item.id).order_by(Offer.created_at.desc())).all()]}

    @router.patch('/applications/{application_id}')
    def act_application(application_id: str, payload: S.ApplicationAction, user=Depends(candidate_user), db=Depends(get_db)):
        item = participant(application_id, user, db, True)
        if not payload.model_fields_set:
            raise HTTPException(422, 'Choose an action or contact sharing preference.')
        if payload.share_contact is not None:
            if payload.share_contact:
                verified(user, db)
            item.share_contact = payload.share_contact
        if payload.action:
            if payload.action in {'accept_invitation', 'decline_invitation'}:
                if item.stage != 'invited':
                    raise HTTPException(409, 'This invitation has already been answered.')
                item.stage = 'applied' if payload.action == 'accept_invitation' else 'declined'
                item.professional_access = payload.action == 'accept_invitation'
            else:
                if item.stage in TERMINAL:
                    raise HTTPException(409, 'This application is already closed.')
                item.stage = 'withdrawn'
            # Withdrawing/declining stops pending offers/interviews; history remains.
            if item.stage in TERMINAL:
                for offer in db.scalars(select(Offer).where(Offer.application_id == item.id, Offer.status == 'sent')).all():
                    offer.status = 'withdrawn'
                for interview in db.scalars(select(Interview).where(Interview.application_id == item.id, Interview.status == 'scheduled')).all():
                    interview.status = 'cancelled'
            notify(db, other_party(item, user, db), 'stage', 'Application moved to ' + item.stage + '.', item)
        db.commit()
        return {'application': application_json(item, db, user)}

    @router.patch('/applications/{application_id}/stage')
    def stage_application(application_id: str, payload: S.StageChange, user=Depends(company_user), db=Depends(get_db)):
        item = participant(application_id, user, db, True)
        if item.stage == payload.stage:
            return {'application': application_json(item, db, user)}
        active(item)
        allowed = {'applied': {'reviewing', 'interviewing', 'rejected'}, 'reviewing': {'interviewing', 'rejected'},
                   'interviewing': {'reviewing', 'rejected'}, 'offer': {'rejected', 'hired'}}
        if payload.stage not in allowed.get(item.stage, set()):
            raise HTTPException(409, 'This stage transition is not available.')
        if payload.stage == 'hired' and not db.scalar(select(Offer.id).where(Offer.application_id == item.id, Offer.status == 'accepted')):
            raise HTTPException(409, 'An accepted offer is required before marking someone hired.')
        item.stage = payload.stage
        if payload.stage == 'rejected':
            for offer in db.scalars(select(Offer).where(Offer.application_id == item.id, Offer.status == 'sent')).all():
                offer.status = 'withdrawn'
        if payload.stage in {'rejected', 'hired'}:
            for interview in db.scalars(select(Interview).where(Interview.application_id == item.id, Interview.status == 'scheduled')).all():
                interview.status = 'cancelled'
        notify(db, other_party(item, user, db), 'stage', 'Application moved to ' + item.stage + '.', item)
        db.commit()
        return {'application': application_json(item, db, user)}

    @router.post('/applications/{application_id}/messages', status_code=201)
    def send_message(application_id: str, payload: S.MessageCreate, request: Request, user=Depends(require_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-message', 60, 3600, user.id)
        item = participant(application_id, user, db, True)
        if item.stage in {'declined', 'rejected', 'withdrawn'}:
            raise HTTPException(409, 'This conversation is closed. Its existing messages remain available.')
        message = Message(application_id=item.id, sender_id=user.id, body=payload.body)
        db.add(message)
        notify(db, other_party(item, user, db), 'message', 'A new message was added to your hiring conversation.', item)
        db.commit()
        return {'message': message_json(message, db)}

    @router.post('/applications/{application_id}/interviews', status_code=201)
    def create_interview(application_id: str, payload: S.InterviewCreate, request: Request, user=Depends(company_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-interview', 30, 3600, user.id)
        item = participant(application_id, user, db, True)
        active(item)
        if utc(payload.starts_at) <= now():
            raise HTTPException(422, 'Schedule interviews in the future.')
        interview = Interview(application_id=item.id, **payload.model_dump())
        interview.starts_at = utc(interview.starts_at)
        db.add(interview)
        if item.stage in {'applied', 'reviewing'}:
            item.stage = 'interviewing'
        notify(db, other_party(item, user, db), 'interview', 'An interview was scheduled. Please review its time and RSVP.', item)
        db.commit()
        return {'interview': interview_json(interview)}

    @router.patch('/interviews/{interview_id}')
    def patch_interview(interview_id: str, payload: S.InterviewPatch, user=Depends(require_user), db=Depends(get_db)):
        interview = db.get(Interview, interview_id)
        if not interview:
            raise HTTPException(404, 'Interview was not found.')
        item = participant(interview.application_id, user, db, True)
        db.refresh(interview)
        changes = payload.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(422, 'Provide valid interview changes.')
        active(item)
        if interview.status != 'scheduled':
            raise HTTPException(409, 'This interview is no longer scheduled.')
        if user.role == 'candidate':
            if set(changes) != {'rsvp'}:
                raise HTTPException(403, 'Candidates can only update their interview RSVP.')
            interview.rsvp = payload.rsvp
        else:
            if 'rsvp' in changes:
                raise HTTPException(403, 'Only the candidate can set an RSVP.')
            field_values = {key: getattr(interview, key) for key in S.InterviewCreate.model_fields}
            field_values.update({key: value for key, value in changes.items() if key != 'status'})
            # Normalize SQLite timestamps before validating an unchanged date.
            if 'starts_at' not in changes:
                field_values['starts_at'] = utc(interview.starts_at)
            try:
                checked = S.InterviewCreate(**field_values)
            except ValidationError:
                raise HTTPException(422, 'Check the interview timezone, duration and safe meeting link.')
            if 'starts_at' in changes and utc(checked.starts_at) <= now():
                raise HTTPException(422, 'Reschedule interviews to a future time.')
            rescheduled = any(key in changes and getattr(interview, key) != value for key, value in checked.model_dump().items() if key in {'starts_at', 'duration_minutes', 'location_or_url'})
            for key, value in checked.model_dump().items():
                setattr(interview, key, utc(value) if key == 'starts_at' else value)
            if rescheduled:
                interview.rsvp = 'pending'
            if payload.status:
                if payload.status == 'completed' and utc(interview.starts_at) > now():
                    raise HTTPException(409, 'A future interview cannot be marked complete.')
                interview.status = payload.status
        notify(db, other_party(item, user, db), 'interview', 'Interview details or RSVP were updated.', item)
        db.commit()
        return {'interview': interview_json(interview)}

    @router.post('/applications/{application_id}/offers', status_code=201)
    def create_offer(application_id: str, payload: S.OfferCreate, request: Request, user=Depends(company_user), db=Depends(get_db)):
        rate_limit(request, 'hiring-offer', 20, 3600, user.id)
        item = participant(application_id, user, db, True)
        active(item)
        values = validate_compensation(payload.model_dump())
        if payload.expires_at and utc(payload.expires_at) <= now():
            raise HTTPException(422, 'Offer expiry must be in the future.')
        for previous in db.scalars(select(Offer).where(Offer.application_id == item.id, Offer.status.in_(['sent', 'accepted']))).all():
            effective = offer_json(previous)['status']
            if effective in {'sent', 'accepted'}:
                raise HTTPException(409, 'An active or accepted offer already exists for this application.')
            previous.status = 'expired'
        offer = Offer(application_id=item.id, **values)
        db.add(offer)
        item.stage = 'offer'
        notify(db, other_party(item, user, db), 'offer', 'A new offer is ready for your review.', item)
        db.commit()
        return {'offer': offer_json(offer)}

    @router.patch('/offers/{offer_id}')
    def act_offer(offer_id: str, payload: S.OfferAction, user=Depends(require_user), db=Depends(get_db)):
        offer = db.get(Offer, offer_id)
        if not offer:
            raise HTTPException(404, 'Offer was not found.')
        item = participant(offer.application_id, user, db, True)
        db.refresh(offer)
        if (user.role == 'candidate' and payload.status == 'withdrawn') or (user.role == 'company' and payload.status != 'withdrawn'):
            raise HTTPException(403, 'This offer action is not available to your role.')
        if offer.status == payload.status:
            return {'offer': offer_json(offer)}
        active(item)
        if offer_json(offer)['status'] != 'sent':
            raise HTTPException(409, 'This offer has expired or has already been answered.')
        offer.status = payload.status
        notify(db, other_party(item, user, db), 'offer', 'Offer response: ' + payload.status + '.', item)
        db.commit()
        return {'offer': offer_json(offer)}

    @router.get('/notifications')
    def get_notifications(user=Depends(require_user), db=Depends(get_db)):
        return {'notifications': [notification_json(item) for item in notification_items(user.id, db, 200)],
                'unread_count': unread_notifications(user.id, db)}

    @router.patch('/notifications/{notification_id}')
    def read_notification(notification_id: str, payload: S.NotificationRead, user=Depends(require_user), db=Depends(get_db)):
        item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user.id))
        if not item:
            item = db.scalar(select(IntroductionNotification).where(IntroductionNotification.id == notification_id,
                                                                  IntroductionNotification.recipient_id == user.id))
        if not item:
            raise HTTPException(404, 'Notification was not found.')
        item.read = True
        db.commit()
        return {'notification': notification_json(item)}

    @router.post('/notifications/read-all')
    def read_all_notifications(user=Depends(require_user), db=Depends(get_db)):
        for model in [Notification, IntroductionNotification]:
            db.query(model).filter(model.recipient_id == user.id, model.read.is_(False)).update({'read': True}, synchronize_session=False)
        db.commit()
        return {'ok': True}

    @router.get('/dashboard')
    def dashboard(user=Depends(require_user), db=Depends(get_db)):
        applications = db.scalars(application_query(user).order_by(Application.created_at.desc())).all()
        ids = [item.id for item in applications]
        pipeline = {stage: sum(item.stage == stage for item in applications) for stage in ['invited', 'applied', 'reviewing', 'interviewing', 'offer', 'hired', 'rejected', 'withdrawn', 'declined']}
        upcoming_query = select(Interview).where(Interview.application_id.in_(ids), Interview.status == 'scheduled', Interview.starts_at >= now())
        upcoming_count = db.scalar(select(func.count()).select_from(upcoming_query.subquery()))
        interviews = db.scalars(upcoming_query.order_by(Interview.starts_at).limit(20)).all()
        job_count = db.scalar(select(func.count()).select_from(Job).where(Job.company_id == user.id)) if user.role == 'company' else 0
        published = db.scalar(select(func.count()).select_from(Job).where(Job.company_id == user.id, Job.status == 'published')) if user.role == 'company' else 0
        unread = unread_notifications(user.id, db)
        saved = db.scalar(select(func.count()).select_from(SavedJob).where(SavedJob.user_id == user.id))
        return {'role': user.role, 'counts': {'jobs': job_count, 'published_jobs': published, 'applications': len(applications),
                 'unread_notifications': unread, 'saved_jobs': saved, 'upcoming_interviews': upcoming_count},
                'pipeline': pipeline, 'upcoming_interviews': [interview_json(item) for item in interviews],
                'recent_applications': [application_json(item, db, user) for item in applications[:10]]}

    return router
