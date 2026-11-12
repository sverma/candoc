import datetime as dt
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


def uid():
    return str(uuid.uuid4())


def now():
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id = Column(String(36), primary_key=True, default=uid)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(String(300), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    company_name = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    profile = relationship('Profile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    sessions = relationship('AuthSession', cascade='all, delete-orphan')


class AuthSession(Base):
    __tablename__ = 'sessions'
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class PasswordReset(Base):
    __tablename__ = 'password_resets'
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    password_fingerprint = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    headline = Column(String(160), default='', nullable=False)
    location = Column(String(100), default='', nullable=False)
    bio = Column(Text, default='', nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    years_experience = Column(Float, default=0, nullable=False)
    availability = Column(String(100), default='Open to opportunities', nullable=False)
    github_url = Column(String(250), default='', nullable=False)
    linkedin_url = Column(String(350), default='', nullable=False)
    linkedin_text = Column(Text, default='', nullable=False)
    consent_public_analysis = Column(Boolean, default=False, nullable=False)
    consent_external_ai = Column(Boolean, default=False, nullable=False)
    visible = Column(Boolean, default=False, nullable=False)
    resume_filename = Column(String(255), nullable=True)
    resume_path = Column(String(100), nullable=True)
    resume_text = Column(Text, default='', nullable=False)
    assessment = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)
    user = relationship('User', back_populates='profile')


class Introduction(Base):
    __tablename__ = 'introductions'
    id = Column(String(36), primary_key=True, default=uid)
    candidate_id = Column(String(36), ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    company_user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role_title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    salary_range = Column(String(100), default='', nullable=False)
    work_mode = Column(String(100), default='', nullable=False)
    status = Column(String(20), default='pending', nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    candidate = relationship('Profile')
    company = relationship('User')
