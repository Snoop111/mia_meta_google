"""
Meta OAuth Authentication Endpoints
Follows same pattern as Google OAuth with MCP integration
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import aiohttp
import time
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db
from models.user_profile import AccountMapping, UserProfile, AuthSession
from services.session_service import SessionService

# Get MCP base URL from environment
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "https://mia-analytics.ngrok.app")

router = APIRouter()

# Initialize session service
session_service = SessionService()


@router.get("/api/oauth/meta/auth-url")
async def get_meta_auth_url():
    """Get Meta OAuth authentication URL from MCP server"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MCP_BASE_URL}/meta-oauth/auth-url") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"MCP Meta auth URL failed: {error_text}")
    except Exception as e:
        print(f"[META-AUTH-URL] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MetaTokenExchangeRequest(BaseModel):
    code: str
    state: Optional[str] = "meta_oauth_state"


@router.post("/api/oauth/meta/exchange-token")
async def exchange_meta_token(request: MetaTokenExchangeRequest):
    """Exchange Meta authorization code for access token via MCP server"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "code": request.code,
                "state": request.state
            }
            async with session.post(
                f"{MCP_BASE_URL}/meta-oauth/exchange-token",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"MCP Meta token exchange failed: {error_text}")
    except Exception as e:
        print(f"[META-TOKEN-EXCHANGE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/oauth/meta/status")
async def get_meta_auth_status(request: Request, db: Session = Depends(get_db)):
    """Get Meta authentication status with session management"""
    try:
        session_service.db = db
        session_id = request.headers.get('X-Session-ID', 'default')

        # Check for active session in database
        try:
            session = session_service.get_active_session(session_id)
            has_meta_auth = getattr(session, 'meta_authenticated', False) if session else False
        except Exception as e:
            # Handle case where meta_authenticated column doesn't exist yet
            print(f"[META-AUTH-STATUS] Database schema issue (likely missing meta_authenticated column): {e}")
            session = None
            has_meta_auth = False

        if session and not session.logged_out and has_meta_auth:
            # Get user profile
            profile = db.query(UserProfile).filter(
                UserProfile.google_user_id == session.google_user_id
            ).first()

            if profile:
                # Build selected account info
                selected_account = None
                if session.selected_account_id:
                    account_mapping = session_service.get_account_mapping(session.selected_account_id)
                    if account_mapping:
                        selected_account = {
                            "id": account_mapping.account_id,
                            "name": account_mapping.account_name,
                            "meta_ads_id": getattr(account_mapping, 'meta_ads_id', None),
                            "business_type": account_mapping.business_type
                        }

                return {
                    "authenticated": True,
                    "user_info": {
                        "id": profile.google_user_id,
                        "email": profile.email,
                        "name": profile.name,
                        "picture": profile.picture_url,
                        "verified_email": True
                    },
                    "selected_account": selected_account,
                    "success": True
                }

        # No active session - check MCP server
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{MCP_BASE_URL}/meta-oauth/user-info") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('authenticated') and data.get('user_info'):
                        return {
                            "authenticated": True,
                            "user_info": data['user_info'],
                            "success": True,
                            "needs_session_creation": True
                        }

                return {
                    "authenticated": False,
                    "success": False,
                    "error": "Not authenticated with Meta"
                }

    except Exception as e:
        print(f"[META-AUTH-STATUS] Error: {e}")
        return {
            "authenticated": False,
            "success": False,
            "error": str(e)
        }


@router.get("/api/oauth/meta/user-info")
async def get_meta_user_info():
    """Get Meta user info from MCP server"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MCP_BASE_URL}/meta-oauth/user-info") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"MCP Meta user info failed: {error_text}")
    except Exception as e:
        print(f"[META-USER-INFO] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/oauth/meta/complete")
async def complete_meta_oauth(request: Request, db: Session = Depends(get_db)):
    """Complete Meta OAuth flow - create database session from MCP authentication"""
    try:
        session_service.db = db
        session_id = request.headers.get('X-Session-ID', 'default')

        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")

        # Get user info from MCP server
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{MCP_BASE_URL}/meta-oauth/user-info") as response:
                if response.status != 200:
                    raise HTTPException(status_code=401, detail="Not authenticated with MCP Meta")

                data = await response.json()
                if not data.get('authenticated') or not data.get('user_info'):
                    raise HTTPException(status_code=401, detail="Invalid Meta authentication data")

                user_info = data['user_info']

        # Create or update user profile with Meta platform identifier
        profile = await session_service.create_or_update_user_profile(user_info, platform='meta')

        # Create/update auth session with Meta flag
        existing_session = db.query(AuthSession).filter(
            AuthSession.session_id == session_id
        ).first()

        try:
            if existing_session:
                existing_session.google_user_id = profile.google_user_id
                existing_session.authenticated = True
                existing_session.logged_out = False
                # Add meta authentication flag (if column exists)
                if hasattr(existing_session, 'meta_authenticated'):
                    existing_session.meta_authenticated = True
                existing_session.expires_at = datetime.utcnow() + timedelta(hours=24)
                db.commit()
            else:
                # Try to create with meta_authenticated, fallback without it
                try:
                    auth_session = AuthSession(
                        session_id=session_id,
                        google_user_id=profile.google_user_id,
                        authenticated=True,
                        logged_out=False,
                        meta_authenticated=True,
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                        session_page_visits={}
                    )
                    db.add(auth_session)
                    db.commit()
                except Exception as schema_error:
                    print(f"[META-OAUTH-COMPLETE] Schema issue, creating session without meta_authenticated: {schema_error}")
                    db.rollback()
                    auth_session = AuthSession(
                        session_id=session_id,
                        google_user_id=profile.google_user_id,
                        authenticated=True,
                        logged_out=False,
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                        session_page_visits={}
                    )
                    db.add(auth_session)
                    db.commit()
        except Exception as e:
            print(f"[META-OAUTH-COMPLETE] Database error: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        return {
            "success": True,
            "message": "Meta OAuth completed successfully",
            "user": {
                "name": profile.name,
                "email": profile.email,
                "id": profile.google_user_id
            },
            "session_id": session_id,
            "requires_account_selection": True
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[META-OAUTH-COMPLETE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/oauth/meta/logout")
async def logout_meta(request: Request, db: Session = Depends(get_db)):
    """Logout from Meta - clears MCP session and local database sessions"""
    try:
        session_id = request.headers.get('X-Session-ID')

        # Clear local database sessions first
        if session_id:
            session = db.query(AuthSession).filter(
                AuthSession.session_id == session_id,
                AuthSession.logged_out == False
            ).first()

            if session:
                # Clear Meta authentication from this session
                session.meta_authenticated = False
                session.meta_ads_id = None
                db.commit()
                print(f"[META-LOGOUT] Cleared local session: {session_id}")

        # Also clear ALL Meta sessions (in case session_id is missing)
        try:
            result = db.query(AuthSession).filter(
                AuthSession.meta_authenticated == True
            ).update({
                'meta_authenticated': False,
                'meta_ads_id': None
            })
            db.commit()
            print(f"[META-LOGOUT] Cleared {result} Meta authenticated sessions")
        except Exception as db_error:
            print(f"[META-LOGOUT] Database clear error (non-critical): {db_error}")

        # Try to logout from MCP server
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{MCP_BASE_URL}/meta-oauth/logout") as response:
                print(f"[META-LOGOUT] MCP logout status: {response.status}")

        return {
            "success": True,
            "message": "Logged out from Meta successfully",
            "cleared_local_sessions": True
        }

    except Exception as e:
        print(f"[META-LOGOUT] Error: {e}")
        return {
            "success": True,  # Always return success for logout
            "message": f"Meta logout completed: {str(e)}",
            "cleared_local_sessions": True
        }


@router.post("/api/oauth/meta/bypass-login")
async def bypass_meta_login(request: Request, db: Session = Depends(get_db)):
    """
    Meta-friendly login bypass for testing - similar to Google bypass
    """
    try:
        session_service.db = db
        frontend_session_id = request.headers.get('X-Session-ID', f'meta_bypass_{int(time.time())}')

        print(f"[META-BYPASS-LOGIN] Creating Meta bypass session: {frontend_session_id}")

        # Use same user profile as Google (unified user management)
        test_user_id = os.getenv("DEV_USER_ID", "106540664695114193744")  # Test user ID from env

        # Create or update user profile for bypass
        from models.user_profile import UserProfile
        profile = db.query(UserProfile).filter(UserProfile.google_user_id == test_user_id).first()

        if not profile:
            profile = UserProfile(
                google_user_id=test_user_id,
                email="trystin@11and1.com",
                name="Trystin (Meta Bypass)",
                picture_url="",
                is_active=True
            )
            db.add(profile)
            db.commit()

        # Check if session already exists and update it, or create new one
        existing_session = db.query(AuthSession).filter(
            AuthSession.session_id == frontend_session_id
        ).first()

        try:
            if existing_session:
                print(f"[META-BYPASS-LOGIN] Updating existing session: {frontend_session_id}")
                existing_session.google_user_id = test_user_id
                existing_session.authenticated = True
                existing_session.logged_out = False
                # Add meta authentication flag (if column exists)
                if hasattr(existing_session, 'meta_authenticated'):
                    existing_session.meta_authenticated = True
                existing_session.expires_at = datetime.utcnow() + timedelta(hours=24)
                db.commit()
            else:
                print(f"[META-BYPASS-LOGIN] Creating new Meta session: {frontend_session_id}")
                # Try to create with meta_authenticated, fallback without it
                try:
                    new_session = AuthSession(
                        session_id=frontend_session_id,
                        google_user_id=test_user_id,
                        authenticated=True,
                        logged_out=False,
                        meta_authenticated=True,
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                        session_page_visits={}
                    )
                    db.add(new_session)
                    db.commit()
                except Exception as schema_error:
                    print(f"[META-BYPASS-LOGIN] Schema issue, creating session without meta_authenticated: {schema_error}")
                    db.rollback()
                    new_session = AuthSession(
                        session_id=frontend_session_id,
                        google_user_id=test_user_id,
                        authenticated=True,
                        logged_out=False,
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                        session_page_visits={}
                    )
                    db.add(new_session)
                    db.commit()
        except Exception as e:
            print(f"[META-BYPASS-LOGIN] Database error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        print(f"[META-BYPASS-LOGIN] Success! Meta session {frontend_session_id} created")

        return {
            "success": True,
            "message": "Meta bypass login successful",
            "session_id": frontend_session_id,
            "user": {
                "name": profile.name,
                "email": profile.email,
                "id": profile.google_user_id,
                "picture": profile.picture_url
            },
            "platform": "meta"
        }

    except Exception as e:
        print(f"[META-BYPASS-LOGIN] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))