#!/usr/bin/env python3
"""
Direct Meta MCP Integration Test
Verifies that Meta campaign data can be retrieved through MCP
"""

import asyncio
import sys
import os
sys.path.append('backend')

from services.mcp_client_fixed import get_mcp_client_fixed

async def test_meta_comprehensive_insights():
    """Test Meta data retrieval via comprehensive insights"""
    print("[META-TEST] Starting direct Meta MCP test...")

    try:
        # Get MCP client
        mcp_client = await get_mcp_client_fixed()
        print("[META-TEST] [OK] MCP client initialized")

        # Test parameters for DFSA Meta account
        user_id = "106540664695114193744"  # Trystin's user ID
        data_selections = [
            {
                "platform": "facebook",  # Meta uses 'facebook' platform in MCP
                "account_id": "1237509046595197",  # DFSA Meta account ID
                "date_range": {
                    "start": "2025-08-03",
                    "end": "2025-09-02"
                }
            }
        ]

        arguments = {
            "user_id": user_id,
            "data_selections": data_selections,
            "start_date": "2025-08-03",
            "end_date": "2025-09-02",
            "min_spend_threshold": 50,
            "budget_increase_limit": 25
        }

        print(f"[META-TEST] Calling comprehensive_insights for Meta account 1237509046595197...")
        print(f"[META-TEST] Arguments: {arguments}")

        # Call MCP tool
        result = await mcp_client.call_tool("get_comprehensive_insights", arguments)

        print(f"[META-TEST] [OK] MCP call completed")
        print(f"[META-TEST] Result type: {type(result)}")
        print(f"[META-TEST] Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        if isinstance(result, dict):
            if result.get('success', False):
                print(f"[META-TEST] [SUCCESS] Meta data retrieved!")

                # Check for platforms analyzed
                if 'individual_insights' in result:
                    insights = result['individual_insights']
                    platforms = list(insights.keys())
                    print(f"[META-TEST] Platforms found: {platforms}")

                    if 'facebook' in insights:
                        fb_data = insights['facebook']
                        print(f"[META-TEST] 📊 Facebook data structure: {list(fb_data.keys()) if isinstance(fb_data, dict) else type(fb_data)}")

                        # Check for campaign data
                        if isinstance(fb_data, dict) and 'campaign_summary' in fb_data:
                            campaigns = fb_data['campaign_summary']
                            print(f"[META-TEST] [FOUND] Found {len(campaigns)} Meta campaigns!")
                            for i, (campaign_name, campaign_data) in enumerate(campaigns.items()):
                                if i < 3:  # Show first 3 campaigns
                                    spend = campaign_data.get('spend', 0)
                                    impressions = campaign_data.get('impressions', 0)
                                    clicks = campaign_data.get('clicks', 0)
                                    print(f"[META-TEST]   - {campaign_name}: ${spend:.2f} spend, {impressions:,} impressions, {clicks:,} clicks")
                        else:
                            print(f"[META-TEST] [ERROR] No campaign_summary in Facebook data")
                            print(f"[META-TEST] Available keys: {list(fb_data.keys()) if isinstance(fb_data, dict) else 'Not a dict'}")
                    else:
                        print(f"[META-TEST] [ERROR] No facebook platform in insights")
                else:
                    print(f"[META-TEST] [ERROR] No individual_insights in result")

                # Check configuration
                if 'configuration' in result:
                    config = result['configuration']
                    platforms_analyzed = config.get('platforms_analyzed', [])
                    print(f"[META-TEST] Platforms analyzed: {platforms_analyzed}")

            else:
                error = result.get('error', 'Unknown error')
                print(f"[META-TEST] [ERROR] MCP returned error: {error}")
        else:
            print(f"[META-TEST] [ERROR] Unexpected result format: {result}")

    except Exception as e:
        print(f"[META-TEST] [ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'mcp_client' in locals() and mcp_client:
            await mcp_client.close()
        print("[META-TEST] Test completed")

if __name__ == "__main__":
    asyncio.run(test_meta_comprehensive_insights())