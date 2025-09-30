#!/usr/bin/env python3
"""
OAuth Setup Verification Script

This script helps verify that your OAuth setup is working correctly
before using the MCP server.
"""

import asyncio
import json
import logging
import requests
import sys
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_fastapi_server(base_url="http://localhost:8000"):
    """Check if FastAPI server is running"""
    try:
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            logger.info("✅ FastAPI server is running")
            return True
    except requests.exceptions.ConnectionError:
        logger.error("❌ FastAPI server not running")
        logger.error("Please start it with: uvicorn main:app --reload --port 8000")
    return False

def get_auth_url(base_url="http://localhost:8000"):
    """Get OAuth authorization URL"""
    try:
        response = requests.get(f"{base_url}/google-oauth/auth-url")
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ OAuth URL generated successfully")
            return data["auth_url"], data["state"]
    except Exception as e:
        logger.error(f"❌ Failed to get auth URL: {e}")
    return None, None

def check_user_credentials(base_url="http://localhost:8000"):
    """Check if user is authenticated"""
    try:
        response = requests.get(f"{base_url}/google-oauth/user-info")
        if response.status_code == 200:
            user_info = response.json()
            logger.info("✅ User authenticated successfully")
            logger.info(f"User: {user_info.get('user_info', {}).get('email', 'Unknown')}")
            return True
    except Exception as e:
        logger.error(f"❌ User not authenticated: {e}")
    return False

def test_comprehensive_insights(base_url="http://localhost:8000"):
    """Test the comprehensive insights endpoint"""
    
    # Create test request
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    payload = {
        "user_id": "current_user",
        "start_date": start_date,
        "end_date": end_date,
        "min_spend_threshold": 100,
        "budget_increase_limit": 50,
        "data_selections": [
            {
                "platform": "google_ads",
                "date_range": {"start": start_date, "end": end_date}
            },
            {
                "platform": "google_analytics",
                "date_range": {"start": start_date, "end": end_date}
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{base_url}/comprehensive-insights",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Comprehensive insights working")
            
            # Check data availability
            data_availability = result.get("data_availability", {})
            for platform, available in data_availability.items():
                status = "✅" if available else "❌"
                logger.info(f"  {status} {platform}: {'Data available' if available else 'No data'}")
            
            return True
        else:
            logger.error(f"❌ Comprehensive insights failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Comprehensive insights error: {e}")
    
    return False

def print_oauth_instructions(auth_url):
    """Print OAuth setup instructions"""
    instructions = f"""
╔══════════════════════════════════════════════════════════════╗
║                    OAUTH SETUP REQUIRED                     ║
╚══════════════════════════════════════════════════════════════╝

To complete your OAuth setup:

1. 🔗 Open this URL in your browser:
   {auth_url}

2. 🔐 Sign in with your Google account that has access to:
   - Google Ads account
   - Google Analytics 4 property

3. ✅ Grant permissions for:
   - Google Ads API access
   - Google Analytics API access

4. 🔄 You'll be redirected to: http://localhost:8000/google-oauth/callback

5. 🧪 Run this script again to verify: python verify_oauth_setup.py

After OAuth is complete, you can use the MCP server with Claude Desktop!
"""
    print(instructions)

def print_success_message():
    """Print success message with next steps"""
    success = """
╔══════════════════════════════════════════════════════════════╗
║                 🎉 OAUTH SETUP COMPLETE! 🎉                 ║
╚══════════════════════════════════════════════════════════════╝

Your OAuth setup is working correctly! 

Next Steps:
1. 🔧 Configure Claude Desktop MCP settings
2. 🚀 Use marketing analytics with Claude

To configure Claude Desktop:
1. Copy claude_desktop_venv_config.json content to your Claude Desktop config
2. Update with your actual API credentials  
3. Restart Claude Desktop
4. Try: "Analyze my marketing performance for the last 30 days"

MCP Server Commands:
• Test MCP server: python test_mcp_server.py
• Start MCP server: python start_mcp_server.py
• Check environment: python start_mcp_server.py --check-env
"""
    print(success)

def main():
    """Main verification flow"""
    
    logger.info("🔍 Verifying OAuth setup for Marketing Analytics MCP...")
    
    base_url = "http://localhost:8000"
    
    # Step 1: Check FastAPI server
    if not check_fastapi_server(base_url):
        return False
    
    # Step 2: Check if user is already authenticated
    if check_user_credentials(base_url):
        logger.info("✅ User already authenticated!")
        
        # Step 3: Test comprehensive insights
        if test_comprehensive_insights(base_url):
            print_success_message()
            return True
        else:
            logger.warning("⚠️ Data access issues - check API credentials")
            return False
    
    # Step 3: User needs to authenticate
    logger.info("🔐 User authentication required")
    auth_url, state = get_auth_url(base_url)
    
    if auth_url:
        print_oauth_instructions(auth_url)
        return False
    else:
        logger.error("❌ Failed to generate OAuth URL")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)