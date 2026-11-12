import datetime as dt
from typing import List, Literal, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .countries import validate_country, validate_currency, validate_region


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, str_strip_whitespace=True)


class WorkAuthorization(StrictModel):
    scope_type: Literal['country', 'region']
    scope_code: str = Field(min_length=2, max_length=20)
    status: Literal['unrestricted', 'permit_held', 'needs_sponsorship', 'unknown']
    valid_until: Optional[dt.date] = None
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def valid_scope(self):
        self.scope_code = validate_country(self.scope_code) if self.scope_type == 'country' else validate_region(self.scope_code)
        return self


class Language(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    proficiency: Literal['basic', 'conversational', 'professional', 'native'] = 'professional'


class PreferencesInput(StrictModel):
    engagement_types: List[Literal['permanent', 'contract', 'freelance', 'consulting', 'temporary', 'internship', 'apprenticeship', 'volunteer']] = Field(default_factory=list, max_length=8)
    work_modes: List[Literal['remote', 'hybrid', 'onsite']] = Field(default_factory=list, max_length=3)
    time_commitment: Literal['full_time', 'part_time', 'flexible'] = 'flexible'
    preferred_countries: List[str] = Field(default_factory=list, max_length=249)
    preferred_regions: List[str] = Field(default_factory=list, max_length=9)
    nationalities: List[str] = Field(default_factory=list, max_length=20)
    work_authorizations: List[WorkAuthorization] = Field(default_factory=list, max_length=50)
    share_work_authorization: bool = Field(default=False, strict=True)
    share_nationality: bool = Field(default=False, strict=True)
    sponsorship_need: Literal['not_required', 'required', 'discuss', 'not_specified'] = 'not_specified'
    willing_to_relocate: bool = Field(default=False, strict=True)
    relocation_countries: List[str] = Field(default_factory=list, max_length=249)
    relocation_regions: List[str] = Field(default_factory=list, max_length=9)
    timezone: str = Field(default='', max_length=100)
    languages: List[Language] = Field(default_factory=list, max_length=30)
    available_from: Optional[dt.date] = None
    notice_days: Optional[int] = Field(default=None, ge=0, le=365, strict=True)
    hours_per_week: Optional[float] = Field(default=None, ge=0, le=168)
    compensation_min: Optional[float] = Field(default=None, ge=0, le=1_000_000_000_000)
    compensation_max: Optional[float] = Field(default=None, ge=0, le=1_000_000_000_000)
    currency: str = Field(default='', max_length=3)
    pay_period: Literal['hour', 'day', 'week', 'month', 'year', 'project'] = 'year'
    portfolio_url: str = Field(default='', max_length=500)
    preferred_title: str = Field(default='', max_length=160)

    @field_validator('preferred_countries', 'nationalities', 'relocation_countries')
    @classmethod
    def country_codes(cls, values):
        return list(dict.fromkeys(validate_country(code) for code in values))

    @field_validator('preferred_regions', 'relocation_regions')
    @classmethod
    def region_codes(cls, values):
        return list(dict.fromkeys(validate_region(code) for code in values))

    @field_validator('engagement_types', 'work_modes')
    @classmethod
    def unique_values(cls, values):
        return list(dict.fromkeys(values))

    @field_validator('currency')
    @classmethod
    def currency_code(cls, value):
        return validate_currency(value) if value else ''

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        if value:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError('Use an IANA timezone such as Asia/Kolkata or Europe/London.')
        return value

    @field_validator('portfolio_url')
    @classmethod
    def safe_portfolio(cls, value):
        if value:
            try:
                parsed = urlparse(value)
                if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password or any(ord(char) < 33 for char in value):
                    raise ValueError()
            except ValueError:
                raise ValueError('Use a complete HTTP or HTTPS portfolio URL without credentials.')
        return value

    @model_validator(mode='after')
    def coherent_values(self):
        if self.compensation_min is not None and self.compensation_max is not None and self.compensation_max < self.compensation_min:
            raise ValueError('Maximum compensation must be at least the minimum.')
        if (self.compensation_min is not None or self.compensation_max is not None) and not self.currency:
            raise ValueError('Choose a currency for the compensation range.')
        scopes = [(item.scope_type, item.scope_code) for item in self.work_authorizations]
        if len(scopes) != len(set(scopes)):
            raise ValueError('Declare each country or region authorization once.')
        languages = [item.name.casefold() for item in self.languages]
        if len(languages) != len(set(languages)):
            raise ValueError('List each language once.')
        return self
