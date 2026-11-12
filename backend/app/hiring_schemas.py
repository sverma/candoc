import re
from datetime import date, datetime
from typing import Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator

Engagement = Literal['permanent', 'contract', 'freelance', 'consulting', 'temporary', 'internship', 'apprenticeship', 'volunteer']
WorkMode = Literal['remote', 'hybrid', 'onsite']
Commitment = Literal['full_time', 'part_time', 'flexible']
Support = Literal['not_specified', 'available', 'case_by_case', 'not_available']
PayPeriod = Literal['hour', 'day', 'week', 'month', 'year', 'project']
Level = Literal['any', 'entry', 'junior', 'mid', 'senior', 'lead', 'executive']
JobStatus = Literal['draft', 'published', 'paused', 'closed']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


def safe_url(value):
    if not value:
        return value
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or re.search(r'[\x00-\x20]', value):
        raise ValueError('Use a valid HTTPS URL without embedded credentials.')
    return value


class CompanyUpdate(Strict):
    name: str = Field(min_length=2, max_length=150)
    website: str = Field(default='', max_length=350)
    industry: str = Field(default='', max_length=100)
    size: str = Field(default='', max_length=80)
    headquarters: str = Field(default='', max_length=150)
    about: str = Field(default='', max_length=10000)
    _website = field_validator('website')(safe_url)


class JobCreate(Strict):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=20, max_length=30000)
    engagement_type: Engagement = 'permanent'
    time_commitment: Commitment = 'full_time'
    work_mode: WorkMode = 'remote'
    country_codes: list[str] = Field(default_factory=list, max_length=50)
    region_codes: list[str] = Field(default_factory=list, max_length=9)
    city: str = Field(default='', max_length=150)
    compensation_min: Optional[float] = Field(default=None, ge=0, le=1e12)
    compensation_max: Optional[float] = Field(default=None, ge=0, le=1e12)
    currency: str = Field(default='', max_length=3)
    pay_period: PayPeriod = 'year'
    duration_months: Optional[float] = Field(default=None, gt=0, le=1200)
    hours_per_week: Optional[float] = Field(default=None, ge=0, le=168)
    skills: list[str] = Field(default_factory=list, max_length=40)
    experience_level: Level = 'any'
    visa_sponsorship: Support = 'not_specified'
    visa_details: str = Field(default='', max_length=3000)
    relocation_support: Support = 'not_specified'
    relocation_details: str = Field(default='', max_length=3000)
    status: JobStatus = 'draft'

    @field_validator('country_codes', 'region_codes')
    @classmethod
    def normalize_codes(cls, value):
        return list(dict.fromkeys(item.upper().strip() for item in value))

    @field_validator('skills')
    @classmethod
    def skills_valid(cls, value):
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if any(len(item) > 60 for item in cleaned):
            raise ValueError('Each skill must be 60 characters or fewer.')
        return cleaned


class JobPatch(Strict):
    title: Optional[str] = None
    description: Optional[str] = None
    engagement_type: Optional[Engagement] = None
    time_commitment: Optional[Commitment] = None
    work_mode: Optional[WorkMode] = None
    country_codes: Optional[list[str]] = None
    region_codes: Optional[list[str]] = None
    city: Optional[str] = None
    compensation_min: Optional[float] = None
    compensation_max: Optional[float] = None
    currency: Optional[str] = None
    pay_period: Optional[PayPeriod] = None
    duration_months: Optional[float] = None
    hours_per_week: Optional[float] = None
    skills: Optional[list[str]] = None
    experience_level: Optional[Level] = None
    visa_sponsorship: Optional[Support] = None
    visa_details: Optional[str] = None
    relocation_support: Optional[Support] = None
    relocation_details: Optional[str] = None
    status: Optional[JobStatus] = None


class SaveJob(Strict):
    saved: bool


class Apply(Strict):
    message: str = Field(default='', max_length=5000)
    share_contact: bool = False


class Invite(Strict):
    candidate_id: str = Field(max_length=36)
    message: str = Field(min_length=10, max_length=5000)


class ApplicationAction(Strict):
    action: Optional[Literal['accept_invitation', 'decline_invitation', 'withdraw']] = None
    share_contact: Optional[bool] = None


class StageChange(Strict):
    stage: Literal['reviewing', 'interviewing', 'rejected', 'hired']


class MessageCreate(Strict):
    body: str = Field(min_length=1, max_length=5000)


class InterviewCreate(Strict):
    starts_at: datetime
    duration_minutes: int = Field(ge=15, le=240)
    location_or_url: str = Field(min_length=2, max_length=1000)
    notes: str = Field(default='', max_length=5000)

    @field_validator('starts_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Include an explicit timezone offset.')
        return value

    @field_validator('location_or_url')
    @classmethod
    def location_safe(cls, value):
        if value.startswith('//') or re.search(r'[\x00-\x1f]', value):
            raise ValueError('Use a safe HTTPS meeting link or plain text location.')
        if re.match(r'^[a-z][a-z0-9+.-]*:', value, re.I):
            safe_url(value)
        return value


class InterviewPatch(Strict):
    starts_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location_or_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[Literal['cancelled', 'completed']] = None
    rsvp: Optional[Literal['accepted', 'declined']] = None


class OfferCreate(Strict):
    summary: str = Field(min_length=10, max_length=10000)
    compensation_min: Optional[float] = Field(default=None, ge=0, le=1e12)
    compensation_max: Optional[float] = Field(default=None, ge=0, le=1e12)
    currency: str = Field(default='', max_length=3)
    pay_period: PayPeriod = 'year'
    start_date: Optional[date] = None
    expires_at: Optional[datetime] = None
    visa_sponsorship: Support = 'not_specified'
    visa_details: str = Field(default='', max_length=3000)
    relocation_support: Support = 'not_specified'
    relocation_details: str = Field(default='', max_length=3000)

    @field_validator('expires_at')
    @classmethod
    def timezone_required(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError('Include an explicit timezone offset.')
        return value


class OfferAction(Strict):
    status: Literal['accepted', 'declined', 'withdrawn']


class NotificationRead(Strict):
    read: Literal[True]
