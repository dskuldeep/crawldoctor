"""User model for authentication and authorization."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for dashboard authentication."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # API Key for programmatic access
    api_key = Column(String(64), unique=True, index=True)
    api_key_created_at = Column(DateTime(timezone=True))
    
    # User preferences
    timezone = Column(String(50), default="UTC")
    notification_preferences = Column(Text)  # JSON field for notification settings
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
