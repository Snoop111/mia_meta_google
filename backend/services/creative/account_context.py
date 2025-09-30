"""
Account Context Service for Creative Analysis

Handles account lookups and provides fallback logic for creative analysis.
"""

import os
from typing import Dict, Any
from sqlalchemy.orm import Session
from models.user_profile import AuthSession, AccountMapping

def get_account_context(session_id: str, db: Session) -> Dict[str, Any]:
    """
    Get account context from session with fallback to DFSA

    Args:
        session_id: Session identifier
        db: Database session

    Returns:
        Dictionary containing account context information
    """
    try:
        # Simple direct session lookup from AuthSession table
        session = db.query(AuthSession).filter(
            AuthSession.session_id == session_id,
            AuthSession.authenticated == True
        ).first()

        if session and session.selected_account_id:
            # Direct account mapping lookup
            account = db.query(AccountMapping).filter(
                AccountMapping.account_id == session.selected_account_id,
                AccountMapping.is_active == True
            ).first()

            if account:
                print(f"[CREATIVE-ACCOUNT-CONTEXT] Using account: {account.account_name}")
                return {
                    "user_id": session.google_user_id,
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "google_ads_id": account.google_ads_id,
                    "ga4_property_id": account.ga4_property_id,
                    "business_type": account.business_type,
                    "focus_account": account.account_id
                }

        # Simple fallback to DFSA (like working version)
        print(f"[CREATIVE-ACCOUNT-CONTEXT] No valid session/account, using DFSA fallback")
        return _get_dfsa_fallback()

    except Exception as e:
        print(f"[CREATIVE-ACCOUNT-CONTEXT] Error: {e}, using DFSA fallback")
        return _get_dfsa_fallback()

def _get_dfsa_fallback() -> Dict[str, Any]:
    """Return DFSA account as fallback with environment variable support"""
    return {
        "user_id": os.getenv("DEV_USER_ID", "106540664695114193744"),
        "account_id": "dfsa",
        "account_name": "DFSA - Goodness to Go",
        "google_ads_id": os.getenv("DEV_DFSA_GOOGLE_ADS_ID", "7574136388"),
        "ga4_property_id": os.getenv("DEV_DFSA_GA4_PROPERTY_ID", "458016659"),
        "business_type": "food",
        "focus_account": "dfsa",
    }