from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
from typing import Dict, Any
import requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta-oauth", tags=["Meta OAuth"])

# OAuth configuration
CLIENT_ID = os.getenv("META_CLIENT_ID")
CLIENT_SECRET = os.getenv("META_CLIENT_SECRET")
REDIRECT_URI = os.getenv("META_REDIRECT_URI", "http://localhost:8000/meta-oauth/callback")

# Scopes for Meta Business API
SCOPES = [
    'ads_management',
    'business_management',
    'pages_read_engagement',
    'read_insights'
]

# In-memory token storage (in production, use a proper database)
meta_user_tokens: Dict[str, Dict[str, Any]] = {}

class TokenExchangeRequest(BaseModel):
    code: str
    state: str = None

@router.get("/auth-url")
async def get_auth_url():
    """Generate Meta OAuth authorization URL"""
    try:
        if not CLIENT_ID:
            raise HTTPException(status_code=500, detail="Meta OAuth not configured - missing CLIENT_ID")
        
        base_url = "https://www.facebook.com/v18.0/dialog/oauth"
        scope_string = ",".join(SCOPES)
        
        authorization_url = (
            f"{base_url}?"
            f"client_id={CLIENT_ID}&"
            f"redirect_uri={REDIRECT_URI}&"
            f"scope={scope_string}&"
            f"response_type=code&"
            f"state=meta_oauth_state"
        )
        
        return {
            "auth_url": authorization_url,
            "state": "meta_oauth_state"
        }
    except Exception as e:
        logger.error(f"Error generating Meta auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """Exchange authorization code for access token"""
    try:
        if not CLIENT_ID or not CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Meta OAuth not configured")
        
        # Exchange code for access token
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'code': request.code
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            logger.error(f"Meta token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Token exchange failed")
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user info
        user_info_url = f"https://graph.facebook.com/v18.0/me?access_token={access_token}&fields=id,name,email"
        user_response = requests.get(user_info_url)
        
        if user_response.status_code != 200:
            logger.error(f"Meta user info fetch failed: {user_response.text}")
            user_info = {"id": "unknown", "name": "Meta User"}
        else:
            user_info = user_response.json()
        
        # Store credentials (use user ID as key in production)
        user_id = "default_user"  # In production, get from JWT or session
        meta_user_tokens[user_id] = {
            "access_token": access_token,
            "token_type": token_data.get("token_type", "bearer"),
            "expires_in": token_data.get("expires_in"),
            "user_info": user_info
        }
        
        return {
            "success": True,
            "user_info": user_info,
            "token_stored": True
        }
        
    except Exception as e:
        logger.error(f"Error exchanging Meta token: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

@router.get("/user-info")
async def get_user_info():
    """Get current Meta user info"""
    try:
        user_id = "default_user"  # Get from JWT in production
        if user_id not in meta_user_tokens:
            raise HTTPException(status_code=401, detail="User not authenticated with Meta")
        
        token_data = meta_user_tokens[user_id]
        
        # Verify token is still valid by making a test API call
        access_token = token_data["access_token"]
        test_url = f"https://graph.facebook.com/v18.0/me?access_token={access_token}"
        test_response = requests.get(test_url)
        
        if test_response.status_code != 200:
            # Token is invalid, remove it
            del meta_user_tokens[user_id]
            raise HTTPException(status_code=401, detail="Meta token expired or invalid")
        
        return {
            "authenticated": True,
            "user_info": token_data["user_info"]
        }
        
    except Exception as e:
        logger.error(f"Error getting Meta user info: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_meta_access_token(user_id: str = "default_user") -> str:
    """Get valid Meta access token for a user"""
    if user_id not in meta_user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated with Meta")
    
    token_data = meta_user_tokens[user_id]
    access_token = token_data["access_token"]
    
    # Test token validity
    test_url = f"https://graph.facebook.com/v18.0/me?access_token={access_token}"
    test_response = requests.get(test_url)
    
    if test_response.status_code != 200:
        # Token is invalid, remove it
        del meta_user_tokens[user_id]
        raise HTTPException(status_code=401, detail="Meta token expired or invalid")
    
    return access_token

@router.get("/callback")
async def oauth_callback(code: str, state: str = None):
    """Handle OAuth callback from Meta"""
    try:
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")

        # Exchange code for token using existing endpoint
        token_request = TokenExchangeRequest(code=code, state=state)
        result = await exchange_token(token_request)

        return result

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")

@router.post("/logout")
async def logout():
    """Logout user and revoke Meta tokens"""
    try:
        user_id = "default_user"  # Get from JWT in production
        if user_id in meta_user_tokens:
            # Optional: Revoke the token with Facebook
            # This requires additional API calls to Facebook's token revocation endpoint
            del meta_user_tokens[user_id]

        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during Meta logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")