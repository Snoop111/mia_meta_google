#!/usr/bin/env python3
"""
Simple MCP connectivity test
"""

import asyncio
import sys
sys.path.append('backend')

from services.mcp_client_fixed import get_mcp_client_fixed

async def test_mcp_basic():
    """Test basic MCP connectivity"""
    print("[MCP-TEST] Testing basic MCP connectivity...")

    try:
        # Get MCP client
        mcp_client = await get_mcp_client_fixed()
        print("[MCP-TEST] ✅ MCP client initialized")

        # Test simple call
        result = await mcp_client.call_tool("get_platform_examples", {})

        print(f"[MCP-TEST] Result type: {type(result)}")
        if result:
            print(f"[MCP-TEST] ✅ Basic MCP call succeeded")
        else:
            print(f"[MCP-TEST] ❌ Basic MCP call returned None")

    except Exception as e:
        print(f"[MCP-TEST] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'mcp_client' in locals() and mcp_client:
            await mcp_client.close()
        print("[MCP-TEST] Test completed")

if __name__ == "__main__":
    asyncio.run(test_mcp_basic())