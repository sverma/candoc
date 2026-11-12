from sqlalchemy import Column, DateTime, ForeignKey, String

from .database import Base


class EmailVerification(Base):
    __tablename__ = 'email_verifications'
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    token_hash = Column(String(64), unique=True, nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
