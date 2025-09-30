"""
Test Session Helper - Creates sessions for different accounts during testing
"""
from sqlalchemy.orm import Session
from models.user_profile import AuthSession, AccountMapping
from database import get_db
import uuid
import os
from datetime import datetime, timedelta

def create_test_session(session_id: str, account_id: str, db: Session) -> bool:
    """
    Create a test session for a specific account

    Args:
        session_id: Test session ID (e.g., "test_cherry_time")
        account_id: Account ID to associate (e.g., "cherry_time", "dfsa", "onvlee")
        db: Database session

    Returns:
        True if session created successfully
    """
    try:
        # Get account mapping
        account = db.query(AccountMapping).filter(
            AccountMapping.account_id == account_id,
            AccountMapping.is_active == True
        ).first()

        if not account:
            print(f"[TEST-SESSION] Account not found: {account_id}")
            return False

        # Check if session already exists
        existing_session = db.query(AuthSession).filter(
            AuthSession.session_id == session_id
        ).first()

        if existing_session:
            # Update existing session
            existing_session.selected_account_id = account_id
            existing_session.google_ads_id = account.google_ads_id
            existing_session.ga4_property_id = account.ga4_property_id
            existing_session.last_activity = datetime.utcnow()
            existing_session.expires_at = datetime.utcnow() + timedelta(hours=24)
            existing_session.authenticated = True
            print(f"[TEST-SESSION] Updated session {session_id} -> {account.account_name}")
        else:
            # Create new session
            new_session = AuthSession(
                session_id=session_id,
                google_user_id=os.getenv("DEV_USER_ID", "106540664695114193744"),  # Test user ID from env
                authenticated=True,
                selected_account_id=account_id,
                google_ads_id=account.google_ads_id,
                ga4_property_id=account.ga4_property_id,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.add(new_session)
            print(f"[TEST-SESSION] Created session {session_id} -> {account.account_name}")

        db.commit()
        return True

    except Exception as e:
        print(f"[TEST-SESSION] Error creating session: {e}")
        db.rollback()
        return False

def create_all_test_sessions():
    """Create test sessions for all accounts"""
    db = next(get_db())

    test_sessions = [
        ("test_dfsa", "dfsa"),
        ("test_cherry_time", "cherry_time"),
        ("test_onvlee", "onvlee")
    ]

    success_count = 0
    for session_id, account_id in test_sessions:
        if create_test_session(session_id, account_id, db):
            success_count += 1

    print(f"[TEST-SESSION] Created {success_count}/{len(test_sessions)} test sessions")
    return success_count == len(test_sessions)

if __name__ == "__main__":
    create_all_test_sessions()