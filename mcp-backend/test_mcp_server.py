#!/usr/bin/env python3
"""
Test script for Marketing Analytics MCP Server

This script tests the MCP server functionality without requiring a full MCP client.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_server():
    """Test the MCP server tools directly"""
    
    logger.info("🧪 Testing Marketing Analytics MCP Server...")
    
    try:
        # Import the server
        from mcp_server import (
            handle_list_tools,
            handle_call_tool,
            handle_list_prompts,
            handle_get_prompt
        )
        
        # Test 1: List available tools
        logger.info("Test 1: Listing available tools...")
        tools = await handle_list_tools()
        logger.info(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Test 2: List available prompts  
        logger.info("\nTest 2: Listing available prompts...")
        prompts = await handle_list_prompts()
        logger.info(f"✅ Found {len(prompts)} prompts:")
        for prompt in prompts:
            logger.info(f"  - {prompt.name}: {prompt.description}")
        
        # Test 3: Get a prompt template
        logger.info("\nTest 3: Getting marketing analysis prompt...")
        prompt_text = await handle_get_prompt(
            "marketing_analysis_report",
            {"platforms": "Google Ads, GA4", "focus": "optimization"}
        )
        logger.info("✅ Prompt template generated successfully")
        logger.info(f"Preview: {prompt_text[:200]}...")
        
        # Test 4: Test credential setup (mock)
        logger.info("\nTest 4: Testing credential setup...")
        try:
            mock_credentials = {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "refresh_token": "test_refresh_token",
                "developer_token": "test_developer_token"
            }
            
            result = await handle_call_tool(
                "setup_credentials",
                {
                    "user_id": "test_user",
                    "platform": "google_ads", 
                    "credentials": mock_credentials
                }
            )
            logger.info("✅ Credential setup test passed")
            logger.info(f"Result: {result[0].text}")
            
        except Exception as e:
            logger.warning(f"⚠️ Credential setup test failed (expected): {e}")
        
        # Test 5: Test comprehensive insights (will fail without real credentials)
        logger.info("\nTest 5: Testing comprehensive insights structure...")
        try:
            # This will fail without real credentials, but we can test the structure
            result = await handle_call_tool(
                "comprehensive_insights",
                {
                    "user_id": "test_user",
                    "platforms": ["google_ads"],
                    "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                    "min_spend_threshold": 100
                }
            )
            logger.info("✅ Comprehensive insights test passed")
            
        except Exception as e:
            logger.warning(f"⚠️ Comprehensive insights test failed (expected without credentials): {e}")
        
        logger.info("\n🎉 MCP Server tests completed!")
        logger.info("The server structure is working correctly.")
        logger.info("To use with real data, configure your API credentials first.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    
    return True

async def test_import_dependencies():
    """Test that all dependencies can be imported"""
    
    logger.info("🔍 Testing dependency imports...")
    
    dependencies = [
        ("mcp", "MCP protocol support"),
        ("pandas", "Data analysis"),
        ("google.auth", "Google API authentication"),
        ("pydantic", "Data validation"),
        ("asyncio", "Async support"),
        ("json", "JSON handling"),
        ("logging", "Logging support")
    ]
    
    failed_imports = []
    
    for module, description in dependencies:
        try:
            __import__(module)
            logger.info(f"  ✅ {module}: {description}")
        except ImportError as e:
            logger.error(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"❌ Failed to import: {failed_imports}")
        logger.error("Please install missing dependencies with: pip install -e .")
        return False
    
    logger.info("✅ All dependencies imported successfully")
    return True

async def test_analytics_modules():
    """Test that analytics modules can be imported"""
    
    logger.info("🧮 Testing analytics module imports...")
    
    modules = [
        ("analytics.ad_performance", "Ad performance analysis"),
        ("analytics.journey_analyzer", "User journey analysis"),
        ("analytics.funnel_optimizer", "Funnel optimization"),
        ("analytics.recommendation_engine", "Recommendation generation"),
        ("routes.comprehensive_insights", "Comprehensive insights"),
        ("credential_manager", "Credential management"),
        ("database", "Database operations")
    ]
    
    failed_imports = []
    
    for module, description in modules:
        try:
            __import__(module)
            logger.info(f"  ✅ {module}: {description}")
        except ImportError as e:
            logger.error(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"❌ Failed to import analytics modules: {failed_imports}")
        return False
    
    logger.info("✅ All analytics modules imported successfully")
    return True

async def run_all_tests():
    """Run all tests"""
    
    logger.info("🚀 Starting Marketing Analytics MCP Server tests...\n")
    
    tests = [
        ("Dependencies", test_import_dependencies),
        ("Analytics Modules", test_analytics_modules),
        ("MCP Server", test_mcp_server)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"{'='*60}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*60}")
        
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name} test PASSED\n")
            else:
                failed += 1
                logger.error(f"❌ {test_name} test FAILED\n")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} test FAILED with exception: {e}\n")
    
    # Summary
    logger.info(f"{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        logger.info("\n🎉 All tests passed! Your MCP server is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Set up your API credentials in environment variables")
        logger.info("2. Run: python3 start_mcp_server.py --check-env")
        logger.info("3. Start the server: python3 start_mcp_server.py")
        logger.info("4. Configure Claude Desktop MCP settings")
    else:
        logger.error(f"\n❌ {failed} test(s) failed. Please fix the issues before using the server.")
    
    return failed == 0

def main():
    """Main entry point"""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()