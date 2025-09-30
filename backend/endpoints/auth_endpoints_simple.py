"""
Authentication Endpoints with Proper Database Session Management
Handles OAuth flow, account selection, and persistent sessions
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

router = APIRouter()

# Initialize session service
session_service = SessionService()


@router.get("/api/oauth/google/auth-url")
async def get_auth_url():
    """Get Google OAuth authentication URL from MCP server"""
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


@router.get("/api/oauth/google/status")
async def get_auth_status(request: Request, db: Session = Depends(get_db)):
    """Get authentication status with session management"""
    try:
        session_service.db = db
        session_id = request.headers.get('X-Session-ID', 'default')

        # Check for active session in database
        session = session_service.get_active_session(session_id)

        if session and not session.logged_out:
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
                            "google_ads_id": account_mapping.google_ads_id,
                            "ga4_property_id": account_mapping.ga4_property_id,
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
            async with http_session.get(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/user-info") as response:
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
                    "error": "Not authenticated"
                }

    except Exception as e:
        print(f"[AUTH-STATUS] Error: {e}")
        return {
            "authenticated": False,
            "success": False,
            "error": str(e)
        }


@router.post("/api/oauth/google/complete")
async def complete_oauth(request: Request, db: Session = Depends(get_db)):
    """Complete OAuth flow - create database session from MCP authentication"""
    try:
        session_service.db = db
        session_id = request.headers.get('X-Session-ID', 'default')

        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")

        # Get user info from MCP server
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/user-info") as response:
                if response.status != 200:
                    raise HTTPException(status_code=401, detail="Not authenticated with MCP")

                data = await response.json()
                if not data.get('authenticated') or not data.get('user_info'):
                    raise HTTPException(status_code=401, detail="Invalid authentication data")

                user_info = data['user_info']

        # Create or update user profile with Google platform identifier
        profile = await session_service.create_or_update_user_profile(user_info, platform='google')

        # Create auth session
        auth_session = session_service.create_auth_session(session_id, profile.google_user_id)

        return {
            "success": True,
            "message": "OAuth completed successfully",
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
        print(f"[OAUTH-COMPLETE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/accounts/available")
async def get_available_accounts(db: Session = Depends(get_db)):
    """Get list of available accounts for selection"""
    try:
        accounts = db.query(AccountMapping).filter(
            AccountMapping.is_active == True
        ).order_by(AccountMapping.sort_order).all()
        
        return {
            "success": True,
            "accounts": [
                {
                    "id": account.account_id,
                    "name": account.account_name,
                    "google_ads_id": account.google_ads_id,
                    "ga4_property_id": account.ga4_property_id,
                    "business_type": account.business_type,
                    "color": account.account_color,
                    "display_name": f"{account.account_name} • Google Ads: {account.google_ads_id} • GA4: {account.ga4_property_id}"
                }
                for account in accounts
            ]
        }
        
    except Exception as e:
        print(f"[ACCOUNTS-AVAILABLE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AccountSelectionRequest(BaseModel):
    account_id: str
    session_id: Optional[str] = "test_session"


@router.post("/api/accounts/select")
async def select_account(request: Request, selection: AccountSelectionRequest, db: Session = Depends(get_db)):
    """Select account for session - PROPERLY STORED IN DATABASE"""
    try:
        session_service.db = db
        session_id = request.headers.get('X-Session-ID', selection.session_id)

        # Verify account exists
        account = db.query(AccountMapping).filter(
            AccountMapping.account_id == selection.account_id,
            AccountMapping.is_active == True
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {selection.account_id}")

        # Store account selection in database session
        success = session_service.select_account_for_session(session_id, selection.account_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to store account selection - no active session found")

        print(f"[ACCOUNT-SELECT] Successfully stored {selection.account_id} for session {session_id}")

        # Build selected account response with both Google and Meta fields
        selected_account_data = {
            "id": account.account_id,
            "name": account.account_name,
            "business_type": account.business_type
        }

        # Add Google Ads fields if available
        if hasattr(account, 'google_ads_id') and account.google_ads_id:
            selected_account_data["google_ads_id"] = account.google_ads_id
        if hasattr(account, 'ga4_property_id') and account.ga4_property_id:
            selected_account_data["ga4_property_id"] = account.ga4_property_id

        # Add Meta Ads fields if available
        if hasattr(account, 'meta_ads_id') and account.meta_ads_id:
            selected_account_data["meta_ads_id"] = account.meta_ads_id

        return {
            "success": True,
            "message": f"Selected account: {account.account_name}",
            "selected_account": selected_account_data,
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ACCOUNT-SELECT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/oauth/google/logout")
async def logout():
    """Simple logout - clears MCP session"""
    try:
        # Try to logout from MCP server
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{os.getenv('MCP_BASE_URL', 'http://localhost:8000')}/google-oauth/logout") as response:
                print(f"[LOGOUT] MCP logout status: {response.status}")

        return {
            "success": True,
            "message": "Logged out successfully"
        }

    except Exception as e:
        print(f"[LOGOUT] Error: {e}")
        return {
            "success": True,  # Always return success for logout
            "message": f"Logout completed: {str(e)}"
        }


@router.post("/api/oauth/bypass-login")
async def bypass_login(request: Request, db: Session = Depends(get_db)):
    """
    Mobile-friendly login bypass that creates a working session
    Returns session_id that frontend should use for all subsequent requests
    """
    try:
        session_service.db = db
        frontend_session_id = request.headers.get('X-Session-ID', f'bypass_{int(time.time())}')

        print(f"[BYPASS-LOGIN] Creating bypass session: {frontend_session_id}")

        # Step 1: Ensure account mappings exist
        try:
            from models.user_profile import AccountMapping
            account_count = db.query(AccountMapping).filter(AccountMapping.is_active == True).count()

            if account_count == 0:
                print("[BYPASS-LOGIN] No accounts found, initializing...")
                # Initialize default accounts
                accounts = [
                    AccountMapping(
                        account_id="dfsa",
                        account_name="DFSA - Goodness to Go",
                        google_ads_id="7574136388",
                        ga4_property_id="458016659",
                        business_type="food",
                        is_active=True,
                        sort_order=1,
                        account_color="#4F46E5"
                    ),
                    AccountMapping(
                        account_id="cherry_time",
                        account_name="Cherry Time - Fresh Fruit",
                        google_ads_id="8705861821",
                        ga4_property_id="292652926",
                        business_type="food",
                        is_active=True,
                        sort_order=2,
                        account_color="#DC2626"
                    ),
                    AccountMapping(
                        account_id="onvlee",
                        account_name="Onvlee Engineering - Cable Trays",
                        google_ads_id="7482456286",
                        ga4_property_id="428236885",
                        business_type="engineering",
                        is_active=True,
                        sort_order=3,
                        account_color="#059669"
                    )
                ]

                for account in accounts:
                    db.add(account)
                db.commit()
                print(f"[BYPASS-LOGIN] Initialized {len(accounts)} accounts")
            else:
                print(f"[BYPASS-LOGIN] Found {account_count} existing accounts")
        except Exception as e:
            print(f"[BYPASS-LOGIN] Account initialization error: {e}")

        # Step 2: Create authenticated session with DFSA as default
        test_user_id = "106540664695114193744"  # Trystin's Google user ID

        # Create or update user profile for bypass
        from models.user_profile import UserProfile
        profile = db.query(UserProfile).filter(UserProfile.google_user_id == test_user_id).first()

        if not profile:
            profile = UserProfile(
                google_user_id=test_user_id,
                email="trystin@11and1.com",
                name="Trystin (Bypass)",
                picture_url="",
                is_active=True
            )
            db.add(profile)
            db.commit()

        # Get DFSA account details first
        dfsa_account = db.query(AccountMapping).filter(
            AccountMapping.account_id == "dfsa",
            AccountMapping.is_active == True
        ).first()

        if not dfsa_account:
            raise Exception("DFSA account mapping not found")

        # Check if session already exists and update it, or create new one
        existing_session = db.query(AuthSession).filter(
            AuthSession.session_id == frontend_session_id
        ).first()

        if existing_session:
            print(f"[BYPASS-LOGIN] Updating existing session: {frontend_session_id}")
            # Update existing session
            existing_session.google_user_id = test_user_id
            existing_session.authenticated = True
            existing_session.logged_out = False
            existing_session.selected_account_id = "dfsa"
            existing_session.google_ads_id = dfsa_account.google_ads_id
            existing_session.ga4_property_id = dfsa_account.ga4_property_id
            existing_session.expires_at = datetime.utcnow() + timedelta(hours=24)  # Extend expiry
            db.commit()
        else:
            print(f"[BYPASS-LOGIN] Creating new session: {frontend_session_id}")
            # Create new authenticated session directly
            new_session = AuthSession(
                session_id=frontend_session_id,
                google_user_id=test_user_id,
                authenticated=True,
                logged_out=False,
                selected_account_id="dfsa",
                google_ads_id=dfsa_account.google_ads_id,
                ga4_property_id=dfsa_account.ga4_property_id,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                session_page_visits={}
            )
            db.add(new_session)
            db.commit()

        success = True

        print(f"[BYPASS-LOGIN] Success! Session {frontend_session_id} -> DFSA account")

        return {
            "success": True,
            "message": "Bypass login successful",
            "session_id": frontend_session_id,
            "user": {
                "name": profile.name,
                "email": profile.email,
                "id": profile.google_user_id,
                "picture": profile.picture_url
            },
            "default_account": {
                "id": "dfsa",
                "name": "DFSA - Goodness to Go"
            }
        }

    except Exception as e:
        print(f"[BYPASS-LOGIN] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/test/dynamic/{account_id}")
async def test_dynamic_account(account_id: str, db: Session = Depends(get_db)):
    """Test endpoint that uses dynamic account selection"""
    try:
        # Get account mapping
        account = db.query(AccountMapping).filter(
            AccountMapping.account_id == account_id,
            AccountMapping.is_active == True
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
        
        # Simulate what would happen in a real endpoint
        context = {
            "account_name": account.account_name,
            "google_ads_id": account.google_ads_id,
            "ga4_property_id": account.ga4_property_id,
            "business_type": account.business_type,
            "focus_account": account.account_id,  # For MCP compatibility
            "start_date": "2025-08-03",
            "end_date": "2025-09-02"
        }
        
        return {
            "success": True,
            "message": f"Dynamic endpoint working with {account.account_name}",
            "context": context,
            "ready_for_mcp": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TEST-DYNAMIC] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))