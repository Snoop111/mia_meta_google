"""
Unified Session Management Service
Handles authentication sessions, user profiles, and account selection
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.user_profile import UserProfile, AuthSession, UserActivity, AccountMapping


class SessionService:
    """
    Bulletproof session management that handles:
    - Persistent user profiles across re-authentication
    - Temporary auth sessions with account selection
    - Activity tracking and analytics
    - Dynamic account management
    """
    
    def __init__(self):
        self.db: Optional[Session] = None
    
    def get_db(self) -> Session:
        """Get database session (lazy initialization)"""
        if self.db is None:
            self.db = next(get_db())
        return self.db
    
    async def create_or_update_user_profile(self, user_info: Dict[str, Any], platform: str = 'google') -> UserProfile:
        """
        Create new user profile or update existing one from OAuth data (Google/Meta)
        This survives logout/re-auth cycles
        """
        user_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        picture_url = user_info.get('picture')

        # Use google_user_id as primary key for both platforms for compatibility
        # (We maintain the existing field name but store both Google and Meta IDs)

        # Check if profile already exists
        db = self.get_db()
        profile = db.query(UserProfile).filter(
            UserProfile.google_user_id == user_id
        ).first()

        if profile:
            # Update existing profile
            profile.email = email
            profile.name = name
            profile.picture_url = picture_url
            profile.last_active = datetime.utcnow()
            print(f"[SESSION] Updated existing profile for {name} ({email}) via {platform.title()}")
        else:
            # Create new profile
            profile = UserProfile(
                google_user_id=user_id,  # Store ID regardless of platform
                email=email,
                name=name,
                picture_url=picture_url,
                page_visit_counts={},
                feature_usage_counts={},
                favorite_accounts=[]
            )
            self.db.add(profile)
            print(f"[SESSION] Created new profile for {name} ({email}) via {platform.title()}")

        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def create_auth_session(self, session_id: str, google_user_id: str) -> AuthSession:
        """
        Create new authentication session (temporary, expires)
        """
        # Expire any existing sessions for this session_id
        existing_sessions = self.db.query(AuthSession).filter(
            AuthSession.session_id == session_id
        ).all()
        
        for session in existing_sessions:
            session.logged_out = True
            session.expires_at = datetime.utcnow()
        
        # Create new session
        new_session = AuthSession(
            session_id=session_id,
            google_user_id=google_user_id,
            authenticated=True,
            logged_out=False,
            expires_at=datetime.utcnow() + timedelta(hours=2),  # 2 hour expiry
            session_page_visits={}
        )
        
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        
        print(f"[SESSION] Created auth session {session_id} for user {google_user_id}")
        return new_session
    
    def get_active_session(self, session_id: str) -> Optional[AuthSession]:
        """
        Get active authentication session if valid
        """
        session = self.db.query(AuthSession).filter(
            AuthSession.session_id == session_id,
            AuthSession.logged_out == False,
            AuthSession.expires_at > datetime.utcnow()
        ).first()
        
        if session:
            # Update last activity
            session.last_activity = datetime.utcnow()
            self.db.commit()
            
        return session
    
    def logout_session(self, session_id: str) -> bool:
        """
        Logout specific session (mark as logged out)
        """
        session = self.db.query(AuthSession).filter(
            AuthSession.session_id == session_id
        ).first()
        
        if session:
            session.logged_out = True
            session.expires_at = datetime.utcnow()
            self.db.commit()
            
            # Track logout activity
            self.track_activity(
                session.google_user_id,
                session_id,
                "logout",
                {"type": "regular_logout"}
            )
            
            print(f"[SESSION] Logged out session {session_id}")
            return True
        
        return False
    
    def force_logout_all_user_sessions(self, google_user_id: str) -> int:
        """
        Force logout all sessions for a user (nuclear option)
        """
        sessions = self.db.query(AuthSession).filter(
            AuthSession.google_user_id == google_user_id,
            AuthSession.logged_out == False
        ).all()
        
        count = 0
        for session in sessions:
            session.logged_out = True
            session.expires_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        
        # Track force logout activity
        if sessions:
            self.track_activity(
                google_user_id,
                sessions[0].session_id,
                "force_logout",
                {"sessions_cleared": count}
            )
        
        print(f"[SESSION] Force logged out {count} sessions for user {google_user_id}")
        return count
    
    def select_account_for_session(self, session_id: str, account_id: str) -> bool:
        """
        Set selected account for this session
        Updates both session and user profile preferences
        """
        session = self.get_active_session(session_id)
        if not session:
            return False
        
        # Get account mapping
        account_mapping = self.get_account_mapping(account_id)
        if not account_mapping:
            print(f"[SESSION] Account mapping not found: {account_id}")
            return False
        
        # Update session with account selection
        session.selected_account_id = account_id
        session.google_ads_id = account_mapping.google_ads_id
        session.ga4_property_id = account_mapping.ga4_property_id
        session.meta_ads_id = account_mapping.meta_ads_id
        
        # Update user profile preferences
        profile = self.db.query(UserProfile).filter(
            UserProfile.google_user_id == session.google_user_id
        ).first()
        
        if profile:
            profile.last_selected_account = account_id
            
            # Update favorite accounts (simple frequency tracking)
            favorites = profile.favorite_accounts or []
            if account_id in favorites:
                favorites.remove(account_id)
            favorites.insert(0, account_id)  # Move to front
            profile.favorite_accounts = favorites[:5]  # Keep top 5
        
        self.db.commit()
        
        # Track account selection activity
        self.track_activity(
            session.google_user_id,
            session_id,
            "account_selected",
            {
                "account_id": account_id,
                "account_name": account_mapping.account_name,
                "google_ads_id": account_mapping.google_ads_id
            }
        )
        
        print(f"[SESSION] Selected account {account_id} for session {session_id}")
        return True
    
    def get_account_mapping(self, account_id: str) -> Optional[AccountMapping]:
        """
        Get account mapping by account ID
        """
        return self.db.query(AccountMapping).filter(
            AccountMapping.account_id == account_id,
            AccountMapping.is_active == True
        ).first()
    
    def get_all_account_mappings(self) -> List[AccountMapping]:
        """
        Get all available account mappings for selection
        """
        return self.db.query(AccountMapping).filter(
            AccountMapping.is_active == True
        ).order_by(AccountMapping.sort_order, AccountMapping.account_name).all()
    
    def track_activity(self, google_user_id: str, session_id: str, 
                      activity_type: str, activity_data: Dict[str, Any] = None,
                      page: str = None, duration_seconds: int = None) -> UserActivity:
        """
        Track user activity for analytics
        """
        # Get current session for context
        session = self.get_active_session(session_id)
        selected_account_id = session.selected_account_id if session else None
        
        activity = UserActivity(
            google_user_id=google_user_id,
            session_id=session_id,
            activity_type=activity_type,
            page=page,
            activity_data=activity_data or {},
            selected_account_id=selected_account_id,
            duration_seconds=duration_seconds
        )
        
        self.db.add(activity)
        
        # Update counters in user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.google_user_id == google_user_id
        ).first()
        
        if profile:
            if activity_type == "question_asked":
                profile.total_questions_asked += 1
                if session:
                    session.session_questions_asked += 1
            
            elif activity_type == "page_visit" and page:
                # Update page visit counts
                page_counts = profile.page_visit_counts or {}
                page_counts[page] = page_counts.get(page, 0) + 1
                profile.page_visit_counts = page_counts
                
                # Update session page visits
                if session:
                    session_visits = session.session_page_visits or {}
                    session_visits[page] = session_visits.get(page, 0) + 1
                    session.session_page_visits = session_visits
            
            elif activity_type in ["chat", "preset_questions", "account_selected"]:
                # Update feature usage counts
                feature_counts = profile.feature_usage_counts or {}
                feature_counts[activity_type] = feature_counts.get(activity_type, 0) + 1
                profile.feature_usage_counts = feature_counts
            
            # Update total time spent
            if duration_seconds:
                profile.total_time_spent_seconds += duration_seconds
        
        self.db.commit()
        return activity
    
    def get_user_analytics(self, google_user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a user across all sessions
        """
        profile = self.db.query(UserProfile).filter(
            UserProfile.google_user_id == google_user_id
        ).first()
        
        if not profile:
            return {}
        
        # Get recent activity
        recent_activities = self.db.query(UserActivity).filter(
            UserActivity.google_user_id == google_user_id
        ).order_by(desc(UserActivity.timestamp)).limit(50).all()
        
        # Get session count
        total_sessions = self.db.query(AuthSession).filter(
            AuthSession.google_user_id == google_user_id
        ).count()
        
        return {
            "profile": {
                "name": profile.name,
                "email": profile.email,
                "first_login": profile.first_login.isoformat() if profile.first_login else None,
                "last_active": profile.last_active.isoformat() if profile.last_active else None,
                "total_sessions": total_sessions,
                "total_questions_asked": profile.total_questions_asked,
                "total_time_spent_seconds": profile.total_time_spent_seconds,
                "favorite_accounts": profile.favorite_accounts or [],
                "last_selected_account": profile.last_selected_account
            },
            "page_visits": profile.page_visit_counts or {},
            "feature_usage": profile.feature_usage_counts or {},
            "recent_activities": [
                {
                    "type": activity.activity_type,
                    "page": activity.page,
                    "timestamp": activity.timestamp.isoformat(),
                    "account": activity.selected_account_id,
                    "data": activity.activity_data
                }
                for activity in recent_activities
            ]
        }
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (can be run as a background task)
        """
        expired_sessions = self.db.query(AuthSession).filter(
            AuthSession.expires_at < datetime.utcnow(),
            AuthSession.logged_out == False
        ).all()
        
        count = 0
        for session in expired_sessions:
            session.logged_out = True
            count += 1
        
        self.db.commit()
        
        if count > 0:
            print(f"[SESSION] Cleaned up {count} expired sessions")
        
        return count


# Singleton instance
session_service = SessionService()