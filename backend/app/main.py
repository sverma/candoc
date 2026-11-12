import datetime as dt
import hmac
import json
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import String, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import Session, object_session, selectinload

from .database import Base, SessionLocal, engine, get_db
from .models import AuthSession, Introduction, LinkedInImport, PasswordReset, Profile, User, now
from .resumes import MAX_UPLOAD, extract_resume
from .security import COOKIE_NAME, COOKIE_SECURE, SESSION_DAYS, check_password, hash_password, rate_limit, token_hash

APP_URL = os.getenv('APP_URL', 'http://localhost:5173').rstrip('/')
ALLOWED_ORIGINS = {APP_URL, *(value.strip().rstrip('/') for value in os.getenv('ALLOWED_ORIGINS', '').split(',') if value.strip())}
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', './data/resumes')).resolve()


@asynccontextmanager
async def lifespan(app):
    if os.getenv('APP_ENV') == 'production' and (not COOKIE_SECURE or not APP_URL.startswith('https://')):
        raise RuntimeError('Production requires APP_URL=https://... and COOKIE_SECURE=true.')
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='Candoc API', version='1.0.0', lifespan=lifespan, docs_url='/api/docs' if os.getenv('APP_ENV') != 'production' else None, openapi_url='/api/openapi.json' if os.getenv('APP_ENV') != 'production' else None, redoc_url=None)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        # Origin is required for authenticated browser writes. Non-browser clients
        # can use the same explicit origin, preventing cross-site form attacks.
        if (origin and origin.rstrip('/') not in ALLOWED_ORIGINS) or (request.cookies.get(COOKIE_NAME) and not origin):
            return JSONResponse({'detail': 'This request origin is not permitted.'}, status_code=403)
        try:
            if int(request.headers.get('content-length', '0')) > MAX_UPLOAD + 65536:
                return JSONResponse({'detail': 'Request is too large. Resume limit is 5 MB.'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': 'Invalid request length.'}, status_code=400)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    first = error.errors()[0]
    field = '.'.join(str(part) for part in first['loc'] if part != 'body')
    return JSONResponse({'detail': f"{field}: {first['msg']}"}, status_code=422)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='before')
    @classmethod
    def trim_text_fields(cls, value):
        if isinstance(value, dict):
            return {key: item.strip() if isinstance(item, str) and key != 'password' else item for key, item in value.items()}
        return value


class Register(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    role: Literal['candidate', 'company']
    company_name: Optional[str] = Field(default=None, max_length=150)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        if not re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+', value):
            raise ValueError('Enter a valid email address.')
        return value.casefold()


class Login(StrictModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ForgotPassword(StrictModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        if not re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+', value):
            raise ValueError('Enter a valid email address.')
        return value.casefold()


class ResetPassword(StrictModel):
    token: str = Field(min_length=20, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')
    password: str = Field(min_length=12, max_length=128)


class ProfileUpdate(StrictModel):
    headline: Optional[str] = Field(default=None, max_length=160)
    location: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=5000)
    skills: Optional[list[str]] = Field(default=None, max_length=40)
    years_experience: Optional[float] = Field(default=None, ge=0, le=80)
    availability: Optional[str] = Field(default=None, max_length=100)
    github_url: Optional[str] = Field(default=None, max_length=250)
    linkedin_url: Optional[str] = Field(default=None, max_length=350)
    linkedin_text: Optional[str] = Field(default=None, max_length=50000)
    visible: Optional[bool] = None
    consent_public_analysis: Optional[bool] = None
    consent_external_ai: Optional[bool] = None

    @field_validator('skills')
    @classmethod
    def valid_skills(cls, value):
        if value is None:
            return value
        clean = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if any(len(item) > 60 for item in clean):
            raise ValueError('Each skill must contain 60 characters or fewer.')
        return clean

    @field_validator('github_url')
    @classmethod
    def valid_github(cls, value):
        if not value:
            return value
        parsed = urlparse(value)
        username = parsed.path.strip('/')
        if parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com' or parsed.query or parsed.fragment or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
            raise ValueError('Use an HTTPS GitHub profile URL, such as https://github.com/username.')
        return f'https://github.com/{username}'

    @field_validator('linkedin_url')
    @classmethod
    def valid_linkedin(cls, value):
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme != 'https' or parsed.netloc.lower() not in {'linkedin.com', 'www.linkedin.com'} or not re.fullmatch(r'/in/[A-Za-z0-9%_-]+/?', parsed.path) or parsed.query or parsed.fragment:
            raise ValueError('Use an HTTPS LinkedIn /in/ profile URL without tracking parameters.')
        return value


class IntroductionCreate(StrictModel):
    candidate_id: str = Field(max_length=36)
    role_title: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=20, max_length=5000)
    salary_range: str = Field(default='', max_length=100)
    work_mode: str = Field(default='', max_length=100)


class IntroductionUpdate(StrictModel):
    status: Literal['accepted', 'declined']


def user_json(user):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role, 'company_name': user.company_name}


def redact_contact(value):
    """Remove contact information from extracted evidence shown to companies."""
    if isinstance(value, str):
        value = re.sub(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', '[contact hidden]', value)
        return re.sub(r'(?<!\w)(?:\+?\d[\d ().-]{8,}\d)(?!\w)', '[phone hidden]', value)
    if isinstance(value, list):
        return [redact_contact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_contact(item) for key, item in value.items()}
    return value


def profile_json(profile, private=False):
    data = {key: getattr(profile, key) for key in ['id', 'user_id', 'headline', 'location', 'bio', 'skills', 'years_experience', 'availability', 'github_url', 'linkedin_url', 'visible', 'assessment']}
    data.update(name=profile.user.name, created_at=profile.created_at.isoformat())
    if not private and data['assessment']:
        data['assessment'] = redact_contact(data['assessment'])
    if private:
        data.update(linkedin_text=profile.linkedin_text, consent_public_analysis=profile.consent_public_analysis,
                    consent_external_ai=profile.consent_external_ai,
                    resume_filename=profile.resume_filename, has_resume=bool(profile.resume_text), resume_text=profile.resume_text,
                    updated_at=profile.updated_at.isoformat())
        data['linkedin_import'] = linkedin_import_result(profile)
    return data


def linkedin_import_result(profile):
    db = object_session(profile)
    if not db:
        return None
    item = db.scalar(select(LinkedInImport).where(LinkedInImport.profile_id == profile.id)
                     .execution_options(populate_existing=True))
    return item.result if item else None


def source_revision(profile):
    imported = linkedin_import_result(profile)
    return (profile.resume_text, tuple(profile.skills or []), profile.linkedin_text,
            profile.github_url, profile.linkedin_url,
            profile.consent_public_analysis, profile.consent_external_ai,
            # Uploaded source changes have no Profile column migration. Include
            # a freshly read document fingerprint in the analysis revision.
            token_hash(json.dumps(imported, sort_keys=True)) if imported else None)


def check_analysis_revision(db, profile, revision):
    try:
        db.refresh(profile)
    except InvalidRequestError:
        raise HTTPException(409, 'Your profile was removed during analysis.')
    if revision != source_revision(profile):
        raise HTTPException(409, 'Your profile changed during analysis. Run the assessment again with the updated information.')


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        return None
    session = db.get(AuthSession, token_hash(token))
    if not session:
        return None
    expires = session.expires_at.replace(tzinfo=dt.timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if expires < now():
        db.delete(session)
        db.commit()
        return None
    return db.get(User, session.user_id)


def require_user(user: Optional[User] = Depends(current_user)):
    if not user:
        raise HTTPException(401, 'Please sign in to continue.')
    return user


def candidate_user(user: User = Depends(require_user)):
    if user.role != 'candidate':
        raise HTTPException(403, 'This action is available to candidates.')
    return user


def company_user(user: User = Depends(require_user)):
    if user.role != 'company':
        raise HTTPException(403, 'This action is available to companies.')
    return user


def create_session(user, request, response, db):
    previous = request.cookies.get(COOKIE_NAME)
    if previous:
        existing = db.get(AuthSession, token_hash(previous))
        if existing:
            db.delete(existing)
    # Keep expired sessions from accumulating indefinitely.
    db.query(AuthSession).filter(AuthSession.expires_at < now()).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id, expires_at=now() + dt.timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_DAYS * 86400, httponly=True, secure=COOKIE_SECURE, samesite='lax', path='/')


@app.post('/api/auth/register', status_code=201)
def register(payload: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, 'register', 10, 3600)
    if payload.role == 'company' and not payload.company_name:
        raise HTTPException(422, 'Enter your company name.')
    user = User(email=payload.email, password_hash=hash_password(payload.password), name=payload.name, role=payload.role, company_name=payload.company_name if payload.role == 'company' else None)
    if user.role == 'candidate':
        user.profile = Profile()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account with this email already exists.')
    create_session(user, request, response, db)
    return {'user': user_json(user)}


@app.post('/api/auth/login')
def login(payload: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, 'login', 20, 900)
    # Serialize password verification/session creation with password reset, which
    # locks the same user before changing credentials and revoking sessions.
    user = db.scalar(select(User).where(User.email == payload.email.casefold()).with_for_update())
    if not user or not check_password(payload.password, user.password_hash):
        # Match password-hash work for nonexistent users to reduce enumeration.
        if not user:
            hash_password(payload.password)
        raise HTTPException(401, 'Email or password is incorrect.')
    create_session(user, request, response, db)
    return {'user': user_json(user)}


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.get(AuthSession, token_hash(token))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path='/', secure=COOKIE_SECURE, httponly=True, samesite='lax')
    return {'ok': True}


def deliver_password_reset(user_id, recipient, hashed, raw_token):
    from . import mailer
    if not user_id:
        return
    with SessionLocal() as delivery_db:
        # A newer request or account deletion may invalidate a queued message.
        active = delivery_db.scalar(select(PasswordReset.token_hash).where(PasswordReset.token_hash == hashed,
                                                                         PasswordReset.expires_at > now()))
    if not active:
        return
    try:
        mailer.send_password_reset(recipient, APP_URL + '/reset-password#token=' + raw_token)
    except Exception:
        # Neither addresses, reset tokens, provider error text nor credentials
        # belong in logs. The response is generic regardless of delivery outcome.
        logging.getLogger(__name__).warning('Password reset email delivery failed.')
        with SessionLocal() as cleanup_db:
            cleanup_db.execute(delete(PasswordReset).where(PasswordReset.token_hash == hashed))
            cleanup_db.commit()


@app.post('/api/auth/forgot-password', status_code=202)
def forgot_password(payload: ForgotPassword, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from . import mailer
    rate_limit(request, 'password-reset-ip', 10, 3600)
    rate_limit(request, 'password-reset-email', 3, 3600, token_hash(payload.email))
    if not mailer.is_configured():
        raise HTTPException(503, 'Password recovery email is not configured. Please contact the site operator.')
    raw_token = secrets.token_urlsafe(32)
    hashed = token_hash(raw_token)
    # Lock order is user first, then reset rows, matching reset_password().
    user = db.scalar(select(User).where(User.email == payload.email).with_for_update())
    if user:
        db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
        db.add(PasswordReset(token_hash=hashed, user_id=user.id,
                             password_fingerprint=token_hash(user.password_hash),
                             expires_at=now() + dt.timedelta(minutes=20)))
    db.execute(delete(PasswordReset).where(PasswordReset.expires_at < now()))
    # SMTP runs after commit: network latency never holds database row locks.
    db.commit()
    background_tasks.add_task(deliver_password_reset, user.id if user else None, payload.email, hashed, raw_token)
    return {'detail': "If an account matches this email, we'll attempt to send a password reset link."}


@app.post('/api/auth/reset-password')
def reset_password(payload: ResetPassword, request: Request, response: Response, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rate_limit(request, 'password-reset-submit', 10, 900)
    hashed = token_hash(payload.token)
    reset = db.get(PasswordReset, hashed)
    invalid = 'This password reset link is invalid or expired. Request a new link.'
    if not reset:
        raise HTTPException(400, invalid)
    user = db.scalar(select(User).where(User.id == reset.user_id).with_for_update())
    if not user or not hmac.compare_digest(reset.password_fingerprint, token_hash(user.password_hash)):
        db.rollback()
        raise HTTPException(400, invalid)
    # Conditional DELETE is the single-use gate. Under concurrent submissions,
    # only one transaction can consume the row, including on SQLite.
    consumed = db.execute(delete(PasswordReset).where(PasswordReset.token_hash == hashed,
                                                    PasswordReset.expires_at > now())
                          .execution_options(synchronize_session=False)
                          .returning(PasswordReset.user_id)).scalar_one_or_none()
    if not consumed:
        db.rollback()
        raise HTTPException(400, invalid)
    user.password_hash = hash_password(payload.password)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.commit()
    response.delete_cookie(COOKIE_NAME, path='/', secure=COOKIE_SECURE, httponly=True, samesite='lax')
    background_tasks.add_task(deliver_password_changed, user.email)
    return {'detail': 'Password updated. Sign in with your new password.'}


def deliver_password_changed(recipient):
    from . import mailer
    try:
        mailer.send_password_changed(recipient)
    except Exception:
        logging.getLogger(__name__).warning('Password change notification delivery failed.')


@app.get('/api/auth/me')
def me(user: Optional[User] = Depends(current_user)):
    return {'user': user_json(user) if user else None}


@app.get('/api/stats')
def stats(db: Session = Depends(get_db)):
    return {'candidates': db.scalar(select(func.count()).select_from(Profile).where(Profile.visible.is_(True))),
            'companies': db.scalar(select(func.count()).select_from(User).where(User.role == 'company')),
            'introductions': db.scalar(select(func.count()).select_from(Introduction))}


@app.get('/api/profile')
def get_profile(user: User = Depends(candidate_user)):
    return {'profile': profile_json(user.profile, True)}


@app.put('/api/profile')
def update_profile(payload: ProfileUpdate, user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    profile = user.profile
    changes = payload.model_dump(exclude_unset=True)
    # Null is intentionally rejected for concrete profile fields.
    if any(value is None for value in changes.values()):
        raise HTTPException(422, 'Profile fields cannot be null. Use an empty value to clear a field.')
    invalidates = {'skills', 'linkedin_text', 'github_url', 'linkedin_url', 'consent_public_analysis', 'consent_external_ai'}
    changed_sources = any(key in invalidates and getattr(profile, key) != value for key, value in changes.items())
    for key, value in changes.items():
        setattr(profile, key, value)
    if changed_sources:
        profile.assessment = None
    db.commit()
    return {'profile': profile_json(profile, True)}


@app.post('/api/profile/resume')
async def upload_resume(request: Request, file: UploadFile = File(...), user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    rate_limit(request, 'resume', 20, 3600, user.id)
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    filename = Path((file.filename or 'resume').replace('\\', '/')).name[:255]
    content, suffix = extract_resume(filename, data)
    profile = user.profile
    previous = profile.resume_path
    storage_name = secrets.token_hex(24) + suffix
    target = UPLOAD_DIR / storage_name
    target.write_bytes(data)
    target.chmod(0o600)
    profile.resume_filename = filename
    profile.resume_path = storage_name
    profile.resume_text = content
    profile.assessment = None
    try:
        db.commit()
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if previous:
        (UPLOAD_DIR / previous).unlink(missing_ok=True)
    return {'profile': profile_json(profile, True)}


@app.post('/api/profile/analyze')
async def analyze(request: Request, user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    from .evaluation import evaluate_profile
    from .sources import fetch_github_profile
    from .semantic import enhance_assessment
    rate_limit(request, 'analyze', 10, 3600, user.id)
    profile = user.profile
    if not profile.resume_text:
        raise HTTPException(400, 'Upload a readable resume before running an assessment.')
    revision = source_revision(profile)
    github = None
    if profile.github_url and profile.consent_public_analysis:
        github = await fetch_github_profile(profile.github_url)
    # A source request may yield long enough for another tab to revoke consent or
    # delete/edit the profile. Recheck before sending excerpts to an AI provider.
    check_analysis_revision(db, profile, revision)
    imported = linkedin_import_result(profile)
    assessment = evaluate_profile(profile.resume_text, profile.skills or [], linkedin_text=profile.linkedin_text or '', github_data=github, linkedin_data=imported)
    assessment = await enhance_assessment(assessment, profile.resume_text, linkedin_text=profile.linkedin_text or '', github_data=github, consent=profile.consent_external_ai, linkedin_data=imported)
    check_analysis_revision(db, profile, revision)
    profile.assessment = assessment
    db.commit()
    return {'profile': profile_json(profile, True)}


@app.post('/api/profile/linkedin/import')
async def import_linkedin(request: Request, file: UploadFile = File(...), user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    from .linkedin import parse_linkedin_export
    rate_limit(request, 'linkedin-import-user', 20, 3600, user.id)
    rate_limit(request, 'linkedin-import-ip', 40, 3600)
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    filename = Path((file.filename or 'linkedin-export').replace('\\', '/')).name[:255]
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, 'LinkedIn export files must be no larger than 5 MB.')
    # Parsing is local. Keep only professional text/metadata, never the original
    # PDF, TXT, CSV or ZIP bytes and never make an outbound LinkedIn request.
    result = parse_linkedin_export(filename, data)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id).with_for_update()
                        .execution_options(populate_existing=True))
    if not profile:
        raise HTTPException(409, 'Your profile was removed during upload.')
    item = db.get(LinkedInImport, profile.id)
    if item:
        item.result = result
    else:
        db.add(LinkedInImport(profile_id=profile.id, result=result))
    profile.assessment = None
    db.commit()
    return {'profile': profile_json(profile, True)}


@app.delete('/api/profile/linkedin/import')
def remove_linkedin_import(user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id).with_for_update()
                        .execution_options(populate_existing=True))
    if not profile:
        raise HTTPException(409, 'Your profile was removed during removal.')
    db.execute(delete(LinkedInImport).where(LinkedInImport.profile_id == profile.id))
    profile.assessment = None
    db.commit()
    return {'profile': profile_json(profile, True)}


@app.get('/api/rubric')
def rubric():
    from .evaluation import get_rubric
    return get_rubric()


@app.get('/api/candidates')
def candidates(search: str = Query('', max_length=150), skill: str = Query('', max_length=60), location: str = Query('', max_length=100), min_score: Optional[float] = Query(None, ge=1, le=5), sort: Literal['recent', 'score'] = 'recent', user: Optional[User] = Depends(current_user), db: Session = Depends(get_db)):
    if not user or user.role != 'company':
        return {'candidates': []}
    query = select(Profile).join(User).options(selectinload(Profile.user)).where(Profile.visible.is_(True))
    if search:
        query = query.where(or_(*(func.lower(column).contains(search.casefold(), autoescape=True)
                                 for column in [User.name, Profile.headline, Profile.bio, Profile.skills.cast(String)])))
    if skill:
        query = query.where(func.lower(Profile.skills.cast(String)).contains(skill.casefold(), autoescape=True))
    if location:
        query = query.where(func.lower(Profile.location).contains(location.casefold(), autoescape=True))
    if min_score is not None:
        query = query.where(Profile.assessment['score'].as_float() >= min_score)
    if sort == 'score':
        query = query.order_by(Profile.assessment['score'].as_float().desc().nullslast(), Profile.created_at.desc())
    else:
        query = query.order_by(Profile.created_at.desc())
    return {'candidates': [profile_json(profile) for profile in db.scalars(query.limit(200)).all()]}


@app.get('/api/candidates/{candidate_id}')
def candidate_detail(candidate_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, candidate_id)
    if not profile or (profile.user_id != user.id and (user.role != 'company' or not profile.visible)):
        raise HTTPException(404, 'Candidate profile was not found.')
    return {'candidate': profile_json(profile, profile.user_id == user.id)}


def introduction_json(item, viewer):
    data = {key: getattr(item, key) for key in ['id', 'candidate_id', 'role_title', 'message', 'salary_range', 'work_mode', 'status']}
    data.update(candidate_name=item.candidate.user.name, company_name=item.company.company_name, created_at=item.created_at.isoformat())
    if item.status == 'accepted':
        data['contact_email'] = item.candidate.user.email if viewer.role == 'company' else item.company.email
    return data


@app.post('/api/introductions', status_code=201)
def request_introduction(payload: IntroductionCreate, request: Request, user: User = Depends(company_user), db: Session = Depends(get_db)):
    rate_limit(request, 'introduction', 30, 3600, user.id)
    profile = db.get(Profile, payload.candidate_id)
    if not profile or not profile.visible:
        raise HTTPException(404, 'Candidate profile was not found.')
    existing = db.scalar(select(Introduction).where(Introduction.candidate_id == profile.id, Introduction.company_user_id == user.id, Introduction.status == 'pending'))
    if existing:
        raise HTTPException(409, 'You already have a pending introduction request to this candidate.')
    item = Introduction(company_user_id=user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    return {'introduction': introduction_json(item, user)}


def introduction_query(user):
    query = select(Introduction).order_by(Introduction.created_at.desc())
    if user.role == 'company':
        query = query.where(Introduction.company_user_id == user.id)
    else:
        query = query.where(Introduction.candidate_id == user.profile.id)
    return query


@app.get('/api/introductions')
def introductions(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return {'introductions': [introduction_json(item, user) for item in db.scalars(introduction_query(user).limit(500)).all()]}


@app.patch('/api/introductions/{introduction_id}')
def decide_introduction(introduction_id: str, payload: IntroductionUpdate, user: User = Depends(candidate_user), db: Session = Depends(get_db)):
    item = db.get(Introduction, introduction_id)
    if not item or item.candidate_id != user.profile.id:
        raise HTTPException(404, 'Introduction was not found.')
    if item.status != 'pending':
        raise HTTPException(409, 'This introduction has already been answered.')
    item.status = payload.status
    db.commit()
    return {'introduction': introduction_json(item, user)}


@app.get('/api/account/export')
def export_account(user: User = Depends(require_user), db: Session = Depends(get_db)):
    data = {'user': user_json(user), 'exported_at': now().isoformat(),
            'introductions': [introduction_json(item, user) for item in db.scalars(introduction_query(user)).all()]}
    if user.role == 'candidate':
        data['profile'] = profile_json(user.profile, True)
        data['linkedin_imports'] = [{'created_at': item.created_at.isoformat(), 'result': item.result}
                                    for item in db.scalars(select(LinkedInImport).where(LinkedInImport.profile_id == user.profile.id)).all()]
    return data


@app.delete('/api/account')
def delete_account(response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)):
    resume_path = user.profile.resume_path if user.profile else None
    db.delete(user)
    db.commit()
    if resume_path:
        (UPLOAD_DIR / resume_path).unlink(missing_ok=True)
    response.delete_cookie(COOKIE_NAME, path='/', secure=COOKIE_SECURE, httponly=True, samesite='lax')
    return {'ok': True}


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'service': 'candoc', 'version': '1.0.0'}
