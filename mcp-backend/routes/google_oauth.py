from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
import json
import logging
from typing import Dict, Any, Optional
from database import credential_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-oauth", tags=["Google OAuth"])

# OAuth configuration - includes both Ads and Analytics scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/adwords',
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "https://marketing-analytics-mcp-5qj9f.ondigitalocean.app/google-oauth/callback")]
    }
}

# Persistent token storage using database
def get_user_tokens(user_id: str = None) -> Dict[str, Dict[str, Any]]:
    """Get user tokens from database storage"""
    try:
        if user_id:
            # Get specific user's tokens
            user_data = credential_storage.get_user_credentials(user_id)
            if user_data and 'google' in user_data:
                google_creds = user_data['google']
                if 'token' in google_creds:
                    return {user_id: google_creds}
            return {}
        else:
            # Get all users with Google tokens
            all_users = credential_storage.get_all_users()
            result = {}
            for uid in all_users:
                user_data = credential_storage.get_user_credentials(uid)
                if user_data and 'google' in user_data and 'token' in user_data['google']:
                    result[uid] = user_data['google']
            return result
    except Exception as e:
        logger.error(f"Error getting user tokens: {e}")
        return {}

def store_user_tokens(user_id: str, token_data: Dict[str, Any]):
    """Store user tokens in database"""
    try:
        # Get existing credentials
        existing_creds = credential_storage.get_user_credentials(user_id) or {}
        
        # Update Google credentials
        existing_creds['google'] = token_data
        
        # Store back to database
        credential_storage.store_credentials(user_id, existing_creds)
        logger.info(f"Stored Google OAuth tokens for user {user_id}")
    except Exception as e:
        logger.error(f"Error storing user tokens: {e}")
        raise

def remove_user_tokens(user_id: str):
    """Remove user tokens from database"""
    try:
        existing_creds = credential_storage.get_user_credentials(user_id) or {}
        if 'google' in existing_creds:
            del existing_creds['google']
            credential_storage.store_credentials(user_id, existing_creds)
        logger.info(f"Removed Google OAuth tokens for user {user_id}")
    except Exception as e:
        logger.error(f"Error removing user tokens: {e}")

class TokenExchangeRequest(BaseModel):
    code: str
    state: str = None
    meta_ads_credentials: Optional[Dict[str, str]] = None

@router.get("/auth-url")
async def get_auth_url():
    """Generate Google OAuth authorization URL"""
    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = CLIENT_CONFIG["web"]["redirect_uris"][0]
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return {
            "auth_url": authorization_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """Exchange authorization code for access token"""
    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = CLIENT_CONFIG["web"]["redirect_uris"][0]
        
        # Exchange code for token
        flow.fetch_token(code=request.code)
        
        credentials = flow.credentials
        
        # Get user info to use as user_id
        from googleapiclient.discovery import build
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        user_id = user_info.get('id')  # Use Google user ID - this will match the user_id sent in comprehensive_insights requests
        
        # Store credentials in database for both Google Ads and GA4
        
        # Store Google Ads credentials
        google_ads_creds = {
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "refresh_token": credentials.refresh_token,
            "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        }
        credential_storage.save_credentials(user_id, "google_ads", google_ads_creds)
        
        # Store GA4 OAuth credentials (property_id will be specified later)
        ga4_creds = {
            "oauth_credentials": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret
            },
            # Keep service account as fallback
            "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            # Note: property_id will need to be set separately or passed at request time
        }
        credential_storage.save_credentials(user_id, "ga4", ga4_creds)
        logger.info(f"Stored GA4 OAuth credentials for user {user_id} (property_id to be configured separately)")
        
        # Store Meta Ads credentials if provided
        if request.meta_ads_credentials:
            credential_storage.save_credentials(user_id, "meta_ads", request.meta_ads_credentials)
            logger.info(f"Stored Meta Ads credentials for user {user_id}")
        
        # Store in database for persistent access
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
        store_user_tokens(user_id, token_data)
        
        logger.info(f"Stored Google credentials for user {user_id} in database")
        
        return {
            "success": True,
            "user_info": user_info,
            "token_stored": True
        }
        
    except Exception as e:
        logger.error(f"Error exchanging token: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

@router.get("/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback"""
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    # Exchange code for token
    exchange_request = TokenExchangeRequest(code=code)
    result = await exchange_token(exchange_request)
    
    # Return success message instead of redirecting
    return {
        "success": True, 
        "message": "Authentication successful! You can close this window.",
        "user_info": result.get("user_info", {})
    }

@router.get("/user-info")
async def get_user_info(user_id: Optional[str] = None):
    """Get current user info"""
    try:
        # If no user_id provided, try to find an active session
        if not user_id:
            # Look for any active user session
            user_tokens = get_user_tokens()
            if user_tokens:
                # Get the most recent user session
                user_id = list(user_tokens.keys())[-1]
                logger.info(f"No user_id provided, using most recent session: {user_id}")
            else:
                raise HTTPException(status_code=401, detail="No active sessions found")
        
        user_tokens = get_user_tokens(user_id)
        if user_id not in user_tokens:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        token_data = user_tokens[user_id]
        credentials = Credentials(
            token=token_data["token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Refresh token if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            # Update stored token in database
            token_data["token"] = credentials.token
            token_data["expiry"] = credentials.expiry.isoformat() if credentials.expiry else None
            store_user_tokens(user_id, token_data)
        
        from googleapiclient.discovery import build
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        return {
            "authenticated": True,
            "user_info": user_info
        }
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_user_credentials(user_id: str = "current_user") -> Credentials:
    """Get valid credentials for a user"""
    user_tokens = get_user_tokens(user_id)
    if user_id not in user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    token_data = user_tokens[user_id]
    credentials = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"]
    )
    
    # Refresh token if needed
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        # Update stored token in database
        token_data["token"] = credentials.token
        token_data["expiry"] = credentials.expiry.isoformat() if credentials.expiry else None
        store_user_tokens(user_id, token_data)
    
    return credentials

@router.post("/logout")
async def logout(user_id: str):
    """Logout user and revoke tokens"""
    try:
        remove_user_tokens(user_id)
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")