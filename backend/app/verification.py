"""Email control verification, separate from organization/identity verification."""
import datetime as dt
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import select, update

from .database import SessionLocal, get_db
from .models import User, now
from .security import rate_limit, token_hash
from .verification_models import EmailVerification


def is_email_verified(user_id, db):
    record = db.get(EmailVerification, user_id, populate_existing=True)
    return bool(record and record.verified_at)


def require_verified_email(user, db):
    if not is_email_verified(user.id, db):
        raise HTTPException(403, 'Verify your email in Account & privacy before publishing a role or sharing your contact email.')


def _deliver(user_id, recipient, raw_token, hashed, app_url):
    from . import mailer
    with SessionLocal() as db:
        record = db.get(EmailVerification, user_id)
        if not record or record.token_hash != hashed or record.verified_at:
            return
    try:
        mailer._send_message(recipient, 'Verify your Candoc email',
                            'Confirm this email address for your Candoc account:\n\n'
                            + app_url + '/verify-email#token=' + raw_token + '\n\n'
                            'This single-use link expires after 24 hours. Only the latest link works.\n'
                            'If you did not request this email, you can ignore it.\n'
                            'Email verification confirms email control, not company identity or qualifications.\n')
    except Exception:
        logging.getLogger(__name__).warning('Email verification delivery failed.')
        with SessionLocal() as db:
            record = db.get(EmailVerification, user_id)
            if record and record.token_hash == hashed:
                record.token_hash = None
                record.expires_at = None
                db.commit()


def build_router():
    from .main import APP_URL, StrictModel, require_user
    router = APIRouter(prefix='/api/auth', tags=['Email verification'])

    class VerifyRequest(StrictModel):
        token: str = Field(min_length=20, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')

    @router.post('/request-verification', status_code=202)
    def request_verification(request: Request, background_tasks: BackgroundTasks,
                             user=Depends(require_user), db=Depends(get_db)):
        from . import mailer
        rate_limit(request, 'verify-email-ip', 20, 3600)
        rate_limit(request, 'verify-email-user', 3, 3600, user.id)
        # User-first lock order matches password recovery and deletion.
        locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
        if not locked_user:
            raise HTTPException(401, 'Please sign in to continue.')
        record = db.get(EmailVerification, user.id, populate_existing=True)
        if record and record.verified_at:
            return {'detail': 'Your email address is already verified.', 'email_verified': True}
        if not mailer.is_configured():
            raise HTTPException(503, 'Verification email is temporarily unavailable. Please try again later.')
        raw = secrets.token_urlsafe(32)
        hashed = token_hash(raw)
        if not record:
            record = EmailVerification(user_id=user.id)
            db.add(record)
        record.token_hash = hashed
        record.expires_at = now() + dt.timedelta(hours=24)
        db.commit()
        background_tasks.add_task(_deliver, user.id, user.email, raw, hashed, APP_URL)
        return {'detail': 'Verification requested. Check your inbox and spam folder for the latest link.', 'email_verified': False}

    @router.post('/verify-email')
    def verify_email(payload: VerifyRequest, request: Request, db=Depends(get_db)):
        rate_limit(request, 'verify-email-token', 20, 900)
        hashed = token_hash(payload.token)
        record = db.scalar(select(EmailVerification).where(EmailVerification.token_hash == hashed))
        invalid = 'This verification link is invalid or expired. Request a new link from Account & privacy.'
        if not record:
            raise HTTPException(400, invalid)
        user = db.scalar(select(User).where(User.id == record.user_id).with_for_update())
        # Refresh after obtaining user lock: only one concurrent request wins.
        if not user:
            db.rollback()
            raise HTTPException(400, invalid)
        db.refresh(record)
        expiry = record.expires_at
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=dt.timezone.utc)
        if record.token_hash != hashed or record.verified_at or not expiry or expiry <= now():
            db.rollback()
            raise HTTPException(400, invalid)
        consumed = db.execute(update(EmailVerification).where(
            EmailVerification.user_id == user.id,
            EmailVerification.token_hash == hashed,
            EmailVerification.verified_at.is_(None),
            EmailVerification.expires_at > now(),
        ).values(verified_at=now(), token_hash=None, expires_at=None)
            .execution_options(synchronize_session=False)
            .returning(EmailVerification.user_id)).scalar_one_or_none()
        if not consumed:
            db.rollback()
            raise HTTPException(400, invalid)
        db.commit()
        return {'detail': 'Email verified. You can continue in your Candoc account.', 'email_verified': True}

    return router
