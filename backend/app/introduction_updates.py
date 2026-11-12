"""Introduction events in the shared Updates feed, with source-aware deletion."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .database import Base
from .models import Introduction, now, uid


class IntroductionNotification(Base):
    # Additive table: no alteration of existing live notification/profile tables.
    __tablename__ = 'introduction_notifications'
    __table_args__ = (UniqueConstraint('introduction_id', 'recipient_id', 'kind', name='uq_introduction_update_event'),)
    id = Column(String(36), primary_key=True, default=uid)
    introduction_id = Column(String(36), ForeignKey('introductions.id', ondelete='CASCADE'), nullable=False, index=True)
    recipient_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    kind = Column(String(40), nullable=False)
    body = Column(String(500), nullable=False)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


def _record(db, introduction, recipient_id, kind, body, timestamp):
    insert = pg_insert if db.get_bind().dialect.name == 'postgresql' else sqlite_insert
    result = db.execute(insert(IntroductionNotification).values(
        id=uid(), introduction_id=introduction.id, recipient_id=recipient_id,
        kind=kind, body=body[:500], read=False, created_at=timestamp,
    ).on_conflict_do_nothing(index_elements=['introduction_id', 'recipient_id', 'kind'])
        .returning(IntroductionNotification.id))
    return int(result.scalar_one_or_none() is not None)


def record_introduction_sent(db, introduction):
    company = introduction.company.company_name or introduction.company.name
    candidate = introduction.candidate.user
    timestamp = introduction.created_at
    return (
        _record(db, introduction, candidate.id, 'introduction_received',
                company + ' sent you an introduction for ' + introduction.role_title + '.', timestamp)
        + _record(db, introduction, introduction.company_user_id, 'introduction_sent',
                  'Your introduction to ' + candidate.name + ' for ' + introduction.role_title + ' was sent.', timestamp)
    )


def record_introduction_response(db, introduction):
    candidate = introduction.candidate.user
    company = introduction.company.company_name or introduction.company.name
    timestamp = now()
    kind = 'introduction_' + introduction.status
    return (
        _record(db, introduction, introduction.company_user_id, kind,
                candidate.name + ' ' + introduction.status + ' your introduction for ' + introduction.role_title + '.', timestamp)
        + _record(db, introduction, candidate.id, kind,
                  'You ' + introduction.status + ' the introduction from ' + company + ' for ' + introduction.role_title + '.', timestamp)
    )


def backfill_introduction_updates(db):
    """Restore sent/received events at their actual timestamps; preserve read state.

    Historical decisions have no recorded response timestamp. Do not fabricate a
    decision event or resend a request; the introduction view shows current status.
    The unique event key makes repeat/concurrent repairs safe.
    """
    return sum(record_introduction_sent(db, item)
               for item in db.scalars(select(Introduction).order_by(Introduction.created_at)).all())
