"""Models for background job infrastructure."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class BackgroundJobState(Base):
    """Tracks watermark per registered sweep job."""

    __tablename__ = "background_job_state"

    job_name = Column(String(100), primary_key=True)
    last_processed_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class PendingJob(Base):
    """Durable queue: jobs written here survive server restarts."""

    __tablename__ = "pending_jobs"

    job_name = Column(String(100), primary_key=True)
    dedup_key = Column(String(255), primary_key=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
