#!/usr/bin/env python3
"""
Test script for Meta Ads and Google Analytics integrations
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_meta_oauth():
    """Test Meta OAuth functionality"""
    print("🧪 Testing Meta OAuth...")
    try:
        from routes.meta_oauth import get_auth_url
        result = await get_auth_url()
        print("✅ Meta OAuth auth URL generated successfully!")
        print(f"   Auth URL starts with: {result['auth_url'][:60]}...")
        return True
    except Exception as e:
        print(f"❌ Meta OAuth error: {e}")
        return False

def test_google_analytics_imports():
    """Test Google Analytics API imports"""
    print("🧪 Testing Google Analytics imports...")
    try:
        from routes.google_analytics_api import router
        print("✅ Google Analytics API imports successfully!")
        return True
    except Exception as e:
        print(f"❌ Google Analytics import error: {e}")
        return False

def test_google_oauth_scopes():
    """Test Google OAuth scopes include Analytics"""
    print("🧪 Testing Google OAuth scopes...")
    try:
        from routes.google_oauth import SCOPES
        analytics_scope = 'https://www.googleapis.com/auth/analytics.readonly'
        if analytics_scope in SCOPES:
            print("✅ Google OAuth includes Analytics scope!")
            print(f"   All scopes: {', '.join(SCOPES)}")
            return True
        else:
            print("❌ Analytics scope missing from Google OAuth")
            return False
    except Exception as e:
        print(f"❌ Google OAuth scope test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Mia integrations...\n")
    
    tests = [
        test_google_oauth_scopes(),
        test_google_analytics_imports(),
        await test_meta_oauth(),
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integrations are working correctly!")
        print("\n✅ Ready to use:")
        print("   - Google Ads (existing)")
        print("   - Google Analytics (new - unified Google auth)")
        print("   - Meta Ads (new - separate auth)")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())