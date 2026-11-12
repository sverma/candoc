"""Additive hiring workspace tables; all participant data is cascade-deleted."""
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from .database import Base
from .models import now, uid


class CompanyProfile(Base):
    __tablename__ = 'hiring_companies'
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    name = Column(String(150), nullable=False)
    website = Column(String(350), default='', nullable=False)
    industry = Column(String(100), default='', nullable=False)
    size = Column(String(80), default='', nullable=False)
    headquarters = Column(String(150), default='', nullable=False)
    about = Column(Text, default='', nullable=False)


class Job(Base):
    __tablename__ = 'hiring_jobs'
    id = Column(String(36), primary_key=True, default=uid)
    company_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    engagement_type = Column(String(20), default='permanent', nullable=False)
    time_commitment = Column(String(20), default='full_time', nullable=False)
    work_mode = Column(String(20), default='remote', nullable=False)
    country_codes = Column(JSON, default=list, nullable=False)
    region_codes = Column(JSON, default=list, nullable=False)
    city = Column(String(150), default='', nullable=False)
    compensation_min = Column(Float, nullable=True)
    compensation_max = Column(Float, nullable=True)
    currency = Column(String(3), default='', nullable=False)
    pay_period = Column(String(20), default='year', nullable=False)
    duration_months = Column(Float, nullable=True)
    hours_per_week = Column(Float, nullable=True)
    skills = Column(JSON, default=list, nullable=False)
    experience_level = Column(String(20), default='any', nullable=False)
    visa_sponsorship = Column(String(20), default='not_specified', nullable=False)
    visa_details = Column(Text, default='', nullable=False)
    relocation_support = Column(String(20), default='not_specified', nullable=False)
    relocation_details = Column(Text, default='', nullable=False)
    status = Column(String(20), default='draft', nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class SavedJob(Base):
    __tablename__ = 'hiring_saved_jobs'
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    job_id = Column(String(36), ForeignKey('hiring_jobs.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Application(Base):
    __tablename__ = 'hiring_applications'
    __table_args__ = (UniqueConstraint('job_id', 'candidate_id', name='uq_hiring_job_candidate'),)
    id = Column(String(36), primary_key=True, default=uid)
    job_id = Column(String(36), ForeignKey('hiring_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    stage = Column(String(20), default='applied', nullable=False, index=True)
    origin = Column(String(20), default='application', nullable=False)
    initial_message = Column(Text, default='', nullable=False)
    share_contact = Column(Boolean, default=False, nullable=False)
    professional_access = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Message(Base):
    __tablename__ = 'hiring_messages'
    id = Column(String(36), primary_key=True, default=uid)
    application_id = Column(String(36), ForeignKey('hiring_applications.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Interview(Base):
    __tablename__ = 'hiring_interviews'
    id = Column(String(36), primary_key=True, default=uid)
    application_id = Column(String(36), ForeignKey('hiring_applications.id', ondelete='CASCADE'), nullable=False, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    location_or_url = Column(String(1000), nullable=False)
    notes = Column(Text, default='', nullable=False)
    status = Column(String(20), default='scheduled', nullable=False)
    rsvp = Column(String(20), default='pending', nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Offer(Base):
    __tablename__ = 'hiring_offers'
    id = Column(String(36), primary_key=True, default=uid)
    application_id = Column(String(36), ForeignKey('hiring_applications.id', ondelete='CASCADE'), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    compensation_min = Column(Float, nullable=True)
    compensation_max = Column(Float, nullable=True)
    currency = Column(String(3), default='', nullable=False)
    pay_period = Column(String(20), default='year', nullable=False)
    start_date = Column(Date, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    visa_sponsorship = Column(String(20), default='not_specified', nullable=False)
    visa_details = Column(Text, default='', nullable=False)
    relocation_support = Column(String(20), default='not_specified', nullable=False)
    relocation_details = Column(Text, default='', nullable=False)
    status = Column(String(20), default='sent', nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Notification(Base):
    __tablename__ = 'hiring_notifications'
    id = Column(String(36), primary_key=True, default=uid)
    recipient_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey('hiring_applications.id', ondelete='CASCADE'), nullable=True)
    job_id = Column(String(36), ForeignKey('hiring_jobs.id', ondelete='CASCADE'), nullable=True)
    kind = Column(String(40), nullable=False)
    body = Column(String(500), nullable=False)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
