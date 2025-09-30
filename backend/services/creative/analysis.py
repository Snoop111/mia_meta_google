"""
Creative Analysis Service

Handles the core business logic for analyzing creative assets and generating insights.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from services.adk_mcp_integration import get_adk_marketing_agent

async def analyze_creative_question(
    question: str,
    category: str,
    account_context: Dict[str, Any],
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Analyze a creative question using MCP integration

    Args:
        question: The creative question to analyze
        category: Question category (grow/optimise/protect)
        account_context: Account information
        start_date: Analysis start date
        end_date: Analysis end date

    Returns:
        Analysis results with success status and insights
    """
    try:
        # Get the marketing agent for MCP queries
        adk_agent = get_adk_marketing_agent()

        # Build MCP query based on question type
        mcp_query = _build_mcp_query(question, category, account_context, start_date, end_date)

        # Execute MCP query
        print(f"[CREATIVE-ANALYSIS] Executing MCP query for: {question}")
        mcp_result = await adk_agent.query_comprehensive_insights(mcp_query)

        if not mcp_result or not mcp_result.get('success', False):
            return {
                "success": False,
                "error": "MCP query failed or returned no data",
                "analysis": "Unable to analyze creative assets. Please try again."
            }

        # Process MCP results
        processed_data = _process_mcp_results(mcp_result, question, category)

        # Generate Claude analysis
        claude_analysis = await _generate_claude_analysis(
            question, category, processed_data, account_context
        )

        return {
            "success": True,
            "analysis": claude_analysis,
            "source": "creative-analysis",
            "raw_data_count": len(processed_data.get('assets', []))
        }

    except Exception as e:
        print(f"[CREATIVE-ANALYSIS] Error analyzing question '{question}': {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": f"Error analyzing creative question: {str(e)}"
        }

def _build_mcp_query(
    question: str,
    category: str,
    account_context: Dict[str, Any],
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """Build MCP query based on question and context"""

    base_query = {
        "user_id": account_context["user_id"],
        "google_ads_id": account_context["google_ads_id"],
        "ga4_property_id": account_context["ga4_property_id"],
        "focus_account": account_context["focus_account"],
        "start_date": start_date,
        "end_date": end_date,
        "query_type": "creative_assets",  # Asset-only analysis
        "question": question,
        "category": category
    }

    # Customize query based on question type
    if "format" in question.lower():
        base_query["asset_types"] = ["ALL"]
    elif "headline" in question.lower() or "cta" in question.lower():
        base_query["asset_types"] = ["HEADLINE", "DESCRIPTION", "SITELINK"]
    elif "visual" in question.lower() or "image" in question.lower():
        base_query["asset_types"] = ["IMAGE", "MARKETING_IMAGE"]
    else:
        base_query["asset_types"] = ["ALL"]

    return base_query

def _process_mcp_results(mcp_result: Dict[str, Any], question: str, category: str) -> Dict[str, Any]:
    """Process raw MCP results into structured data"""

    # Extract assets from MCP response
    raw_data = mcp_result.get('data', {})
    assets = raw_data.get('assets', [])

    if not assets:
        return {"assets": [], "summary": "No assets found"}

    # Basic processing - extract key metrics
    processed_assets = []
    for asset in assets:
        processed_asset = {
            "content": asset.get('content', ''),
            "type": asset.get('type', ''),
            "clicks": asset.get('clicks', 0),
            "impressions": asset.get('impressions', 0),
            "conversions": asset.get('conversions', 0),
            "ctr": asset.get('ctr', 0),
            "cost": asset.get('cost', 0)
        }
        processed_assets.append(processed_asset)

    return {
        "assets": processed_assets,
        "total_assets": len(processed_assets),
        "question": question,
        "category": category
    }

async def _generate_claude_analysis(
    question: str,
    category: str,
    processed_data: Dict[str, Any],
    account_context: Dict[str, Any]
) -> str:
    """Generate Claude analysis of the processed data"""

    assets = processed_data.get('assets', [])
    business_type = account_context.get('business_type', 'general')

    if not assets:
        return f"No creative assets found for analysis. This could be due to the date range or account configuration. Please try a different time period or check your account setup."

    # Create analysis prompt for Claude
    prompt = f"""
    Analyze the following creative assets for a {business_type} business to answer: "{question}"

    Assets found: {len(assets)} creative elements

    Asset Performance Summary:
    """

    # Add top performing assets to prompt
    sorted_assets = sorted(assets, key=lambda x: x.get('clicks', 0), reverse=True)[:5]

    for i, asset in enumerate(sorted_assets[:3], 1):
        prompt += f"""
        {i}. {asset.get('type', 'Unknown')}: "{asset.get('content', '')[:50]}..."
           Performance: {asset.get('clicks', 0)} clicks, {asset.get('impressions', 0)} impressions
           CTR: {asset.get('ctr', 0):.2f}%, Conversions: {asset.get('conversions', 0)}
        """

    prompt += f"""

    Please provide specific, actionable insights for this {category} question, focusing on:
    1. Which creative elements are performing best
    2. Specific recommendations for improvement
    3. Business context for a {business_type} company

    Keep the response concise and practical.
    """

    # For now, return a structured response based on the data
    # In a full implementation, this would call Claude API
    top_asset = sorted_assets[0] if sorted_assets else {}

    return f"""Based on analysis of {len(assets)} creative assets:

**Top Performer:** {top_asset.get('type', 'N/A')} - "{top_asset.get('content', 'N/A')[:50]}..."
- Performance: {top_asset.get('clicks', 0)} clicks, {top_asset.get('ctr', 0):.2f}% CTR

**Key Insights:**
• Your {business_type} business shows strongest performance with {top_asset.get('type', 'text-based')} creative formats
• Top performing assets generate {top_asset.get('clicks', 0)} clicks with {top_asset.get('conversions', 0)} conversions
• Consider focusing budget on similar creative styles for improved {category} performance

**Recommendation:** Scale successful creative patterns while testing variations for continuous optimization."""