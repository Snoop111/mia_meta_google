"""
Clean Slate Authentication Endpoints
Bulletproof auth system with persistent user profiles and session management
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
import os
from datetime import datetime, timedelta

from services.session_service import SessionService
from services.account_setup import get_account_selection_data
from models.user_profile import UserProfile, AuthSession
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter()


class SessionResponse(BaseModel):
    authenticated: bool
    user_info: Optional[Dict[str, Any]] = None
    selected_account: Optional[Dict[str, Any]] = None
    analytics: Optional[Dict[str, Any]] = None
    success: bool
    error: Optional[str] = None


class AccountSelectionRequest(BaseModel):
    account_id: str


@router.get("/api/oauth/google/status")
async def get_auth_status(request: Request) -> SessionResponse:
    """
    Get comprehensive authentication and session status
    Returns user profile, selected account, and analytics
    """
    try:
        # Get session ID from header
        session_id = request.headers.get('X-Session-ID', 'default')
        
        # Check for active session
        session = session_service.get_active_session(session_id)
        
        if not session or session.logged_out:
            return SessionResponse(
                authenticated=False,
                success=False,
                error="No active session found"
            )
        
        # Get user profile
        profile = session_service.db.query(UserProfile).filter(
            UserProfile.google_user_id == session.google_user_id
        ).first()
        
        if not profile:
            return SessionResponse(
                authenticated=False,
                success=False,
                error="User profile not found"
            )
        
        # Build user info
        user_info = {
            "id": profile.google_user_id,
            "email": profile.email,
            "name": profile.name,
            "picture": profile.picture_url,
            "verified_email": True
        }
        
        # Build selected account info
        selected_account = None
        if session.selected_account_id:
            account_mapping = session_service.get_account_mapping(session.selected_account_id)
            if account_mapping:
                selected_account = {
                    "id": account_mapping.account_id,
                    "name": account_mapping.account_name,
                    "google_ads_id": account_mapping.google_ads_id,
                    "ga4_property_id": account_mapping.ga4_property_id,
                    "business_type": account_mapping.business_type
                }
        
        # Get analytics if requested
        analytics = session_service.get_user_analytics(profile.google_user_id)
        
        # Track activity
        session_service.track_activity(
            profile.google_user_id,
            session_id,
            "auth_status_check",
            {"has_selected_account": selected_account is not None}
        )
        
        return SessionResponse(
            authenticated=True,
            user_info=user_info,
            selected_account=selected_account,
            analytics=analytics,
            success=True
        )
        
    except Exception as e:
        print(f"[AUTH-STATUS] Error: {e}")
        return SessionResponse(
            authenticated=False,
            success=False,
            error=str(e)
        )


@router.get("/api/oauth/google/auth-url")
async def get_auth_url(request: Request):
    """
    Get Google OAuth authentication URL from MCP server
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/auth-url") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"MCP auth URL failed: {error_text}")
    except Exception as e:
        print(f"[AUTH-URL] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/oauth/google/complete")
async def complete_oauth(request: Request):
    """
    Complete OAuth flow - create user profile and auth session
    Called after successful OAuth redirect
    """
    try:
        # Get session ID
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Get user info from MCP server
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/user-info") as response:
                if response.status != 200:
                    raise HTTPException(status_code=401, detail="Not authenticated with Google")
                
                data = await response.json()
                if not data.get('authenticated') or not data.get('user_info'):
                    raise HTTPException(status_code=401, detail="Invalid authentication data")
                
                user_info = data['user_info']
        
        # Create or update user profile with Google platform identifier
        profile = await session_service.create_or_update_user_profile(user_info, platform='google')
        
        # Create auth session
        auth_session = session_service.create_auth_session(session_id, profile.google_user_id)
        
        # Track login activity
        session_service.track_activity(
            profile.google_user_id,
            session_id,
            "login",
            {"login_method": "google_oauth", "session_created": True}
        )
        
        # Update session count
        profile.total_sessions += 1
        session_service.db.commit()
        
        return {
            "success": True,
            "message": "Authentication completed successfully",
            "user": {
                "name": profile.name,
                "email": profile.email,
                "id": profile.google_user_id
            },
            "session_id": session_id,
            "requires_account_selection": auth_session.selected_account_id is None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OAUTH-COMPLETE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/accounts/available")
async def get_available_accounts(request: Request):
    """
    Get list of available accounts for selection
    """
    try:
        # Verify session
        session_id = request.headers.get('X-Session-ID', 'default')
        session = session_service.get_active_session(session_id)
        
        if not session:
            raise HTTPException(status_code=401, detail="No active session")
        
        # Get account data
        accounts = get_account_selection_data()
        
        # Get user preferences for ordering
        profile = session_service.db.query(UserProfile).filter(
            UserProfile.google_user_id == session.google_user_id
        ).first()
        
        # Reorder based on favorites
        if profile and profile.favorite_accounts:
            favorites = profile.favorite_accounts
            favorite_accounts = [acc for acc in accounts if acc['id'] in favorites]
            other_accounts = [acc for acc in accounts if acc['id'] not in favorites]
            
            # Sort favorites by preference order
            favorite_accounts.sort(key=lambda x: favorites.index(x['id']) if x['id'] in favorites else 999)
            accounts = favorite_accounts + other_accounts
        
        return {
            "success": True,
            "accounts": accounts,
            "user_preferences": {
                "last_selected": profile.last_selected_account if profile else None,
                "favorites": profile.favorite_accounts if profile else []
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ACCOUNTS-AVAILABLE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/accounts/select")
async def select_account(request: Request, selection: AccountSelectionRequest):
    """
    Select account for current session
    """
    try:
        # Get session ID
        session_id = request.headers.get('X-Session-ID', 'default')
        
        # Select account
        success = session_service.select_account_for_session(session_id, selection.account_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to select account")
        
        # Get updated session info
        session = session_service.get_active_session(session_id)
        account_mapping = session_service.get_account_mapping(selection.account_id)
        
        # Build selected account response with both Google and Meta fields
        selected_account_data = {
            "id": account_mapping.account_id,
            "name": account_mapping.account_name,
            "business_type": account_mapping.business_type
        }

        # Add Google Ads fields if available
        if hasattr(account_mapping, 'google_ads_id') and account_mapping.google_ads_id:
            selected_account_data["google_ads_id"] = account_mapping.google_ads_id
        if hasattr(account_mapping, 'ga4_property_id') and account_mapping.ga4_property_id:
            selected_account_data["ga4_property_id"] = account_mapping.ga4_property_id

        # Add Meta Ads fields if available
        if hasattr(account_mapping, 'meta_ads_id') and account_mapping.meta_ads_id:
            selected_account_data["meta_ads_id"] = account_mapping.meta_ads_id

        return {
            "success": True,
            "message": f"Selected account: {account_mapping.account_name}",
            "selected_account": selected_account_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ACCOUNT-SELECT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/oauth/google/logout")
async def logout(request: Request):
    """
    Smart logout - clears session but preserves user profile
    """
    try:
        session_id = request.headers.get('X-Session-ID', 'default')
        
        # Logout session
        success = session_service.logout_session(session_id)
        
        # Try to logout from MCP server too (best effort)
        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/logout") as response:
                    print(f"[LOGOUT] MCP logout status: {response.status}")
        except Exception as mcp_error:
            print(f"[LOGOUT] MCP logout failed: {mcp_error}")
        
        return {
            "success": True,
            "message": "Logged out successfully - your analytics are preserved"
        }
        
    except Exception as e:
        print(f"[LOGOUT] Error: {e}")
        return {
            "success": True,  # Always return success for logout
            "message": f"Logout completed with errors: {str(e)}"
        }


@router.post("/api/oauth/google/force-logout")  
async def force_logout(request: Request):
    """
    Nuclear logout - clears everything, requires fresh authentication
    """
    try:
        session_id = request.headers.get('X-Session-ID', 'default')
        
        # Get user ID before clearing session
        session = session_service.get_active_session(session_id)
        google_user_id = session.google_user_id if session else None
        
        # Force logout all sessions for this user
        if google_user_id:
            count = session_service.force_logout_all_user_sessions(google_user_id)
            print(f"[FORCE-LOGOUT] Cleared {count} sessions")
        else:
            # Just logout this session
            session_service.logout_session(session_id)
        
        # Try multiple MCP logout approaches
        try:
            async with aiohttp.ClientSession() as http_session:
                # Global logout
                async with http_session.post(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/logout") as response:
                    print(f"[FORCE-LOGOUT] MCP global logout: {response.status}")
                
                # User-specific logout if we have user ID
                if google_user_id:
                    logout_url = f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/logout?user_id={google_user_id}"
                    async with http_session.post(logout_url) as response:
                        print(f"[FORCE-LOGOUT] MCP user logout: {response.status}")
        
        except Exception as mcp_error:
            print(f"[FORCE-LOGOUT] MCP cleanup failed: {mcp_error}")
        
        return {
            "success": True,
            "message": "Complete logout successful - fresh authentication required"
        }
        
    except Exception as e:
        print(f"[FORCE-LOGOUT] Error: {e}")
        return {
            "success": True,  # Always return success for logout
            "message": f"Force logout completed with errors: {str(e)}"
        }


@router.get("/api/analytics/user")
async def get_user_analytics(request: Request):
    """
    Get comprehensive user analytics across all sessions
    """
    try:
        session_id = request.headers.get('X-Session-ID', 'default')
        session = session_service.get_active_session(session_id)
        
        if not session:
            raise HTTPException(status_code=401, detail="No active session")
        
        analytics = session_service.get_user_analytics(session.google_user_id)
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[USER-ANALYTICS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/analytics/track")
async def track_activity(request: Request):
    """
    Track user activity for analytics
    """
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'default')
        session = session_service.get_active_session(session_id)
        
        if not session:
            raise HTTPException(status_code=401, detail="No active session")
        
        activity = session_service.track_activity(
            session.google_user_id,
            session_id,
            data.get('activity_type'),
            data.get('activity_data', {}),
            data.get('page'),
            data.get('duration_seconds')
        )
        
        return {
            "success": True,
            "activity_id": activity.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRACK-ACTIVITY] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Initialize session service
session_service = SessionService()