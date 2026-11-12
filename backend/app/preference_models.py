from sqlalchemy import Column, DateTime, ForeignKey, JSON, String

from .database import Base
from .models import now


class CandidatePreference(Base):
    __tablename__ = 'candidate_preferences'
    profile_id = Column(String(36), ForeignKey('profiles.id', ondelete='CASCADE'), primary_key=True)
    data = Column(JSON, default=dict, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)
