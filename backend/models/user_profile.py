"""
User Profile Models - Persistent user data that survives re-authentication
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from database import Base


class UserProfile(Base):
    """
    Persistent user profile - survives logout/re-auth cycles
    Stores Google user information and accumulated analytics
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)

    # Google OAuth identity (primary key for user)
    google_user_id = Column(String, unique=True, index=True)  # e.g., "106540664695114193744"
    email = Column(String, index=True)
    name = Column(String)
    picture_url = Column(String)

    # Profile metadata
    first_login = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    total_sessions = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Account preferences (most recent selections)
    last_selected_account = Column(String)  # Account ID from account mappings
    favorite_accounts = Column(JSON)  # Array of frequently used account IDs

    # Accumulated analytics (survives re-auth)
    total_questions_asked = Column(Integer, default=0)
    total_time_spent_seconds = Column(Integer, default=0)  # Total time across all sessions
    page_visit_counts = Column(JSON)  # {"growth": 45, "optimize": 23, "creative": 12}
    feature_usage_counts = Column(JSON)  # {"chat": 89, "preset_questions": 34}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuthSession(Base):
    """
    Temporary authentication session - expires after ~1 hour due to Google token limits
    Links to persistent UserProfile via google_user_id
    """
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    session_id = Column(String, unique=True, index=True)  # Frontend-generated session ID
    google_user_id = Column(String, index=True)  # Links to UserProfile

    # Authentication state
    authenticated = Column(Boolean, default=False)
    logged_out = Column(Boolean, default=False)  # Local logout flag
    meta_authenticated = Column(Boolean, default=False)  # Meta OAuth authenticated flag

    # Account selection for this session
    selected_account_id = Column(String)  # "dfsa", "cherry_time", "onvlee"
    google_ads_id = Column(String)  # Resolved Google Ads account ID
    ga4_property_id = Column(String)  # Resolved GA4 property ID
    meta_ads_id = Column(String)  # Resolved Meta Ads account ID

    # Session timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))  # Auto-expire sessions after 2 hours

    # Session analytics (for this session only)
    session_page_visits = Column(JSON, default=lambda: {})
    session_questions_asked = Column(Integer, default=0)
    session_start_time = Column(DateTime(timezone=True), server_default=func.now())


class UserActivity(Base):
    """
    Detailed activity tracking - for analytics and insights
    High-frequency table for tracking every user interaction
    """
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)

    # User and session linking
    google_user_id = Column(String, index=True)
    session_id = Column(String, index=True)

    # Activity details
    activity_type = Column(String, index=True)  # "page_visit", "question_asked", "account_selected", "logout"
    page = Column(String)  # "growth", "optimize", "protect", "creative", "chat"
    activity_data = Column(JSON)  # Flexible data storage for activity specifics

    # Context
    selected_account_id = Column(String)  # Which account was active during this activity
    duration_seconds = Column(Integer)  # Time spent on page/activity

    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class AccountMapping(Base):
    """
    Dynamic account mappings - easily add new accounts without code changes
    Replaces hardcoded mappings throughout the system
    """
    __tablename__ = "account_mappings"

    id = Column(Integer, primary_key=True, index=True)

    # Account identification
    account_id = Column(String, unique=True, index=True)  # "dfsa", "cherry_time", "onvlee"
    account_name = Column(String)  # Display name

    # Platform IDs
    google_ads_id = Column(String)  # "7574136388", "8705861821", "7482456286"
    ga4_property_id = Column(String)  # "458016659", "292652926", "428236885"
    meta_ads_id = Column(String)  # Meta/Facebook ads account ID

    # Account metadata
    business_type = Column(String)  # "food", "engineering", "retail"
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)  # For UI ordering

    # Configuration
    default_date_range_days = Column(Integer, default=30)  # Default reporting period
    account_color = Column(String)  # UI color theme

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())