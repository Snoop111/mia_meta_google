"""
Protect Endpoint - Risk mitigation, safeguarding winning campaigns

Rebuilt using the proven Growth/Optimize endpoint pattern with Protect-specific focus.
Uses same bulletproof MCP + database integration with UI formatting for Protect page.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import json
import httpx
from sqlalchemy.orm import Session

# Import backend dependencies
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.adk_mcp_integration import get_adk_marketing_agent
from services.creative_import import get_creative_insights
from database import SessionLocal, get_db
from models.user_profile import AccountMapping

router = APIRouter()

class ProtectDataRequest(BaseModel):
    question: str = "What needs protecting?"
    user: str = "trystin@11and1.com"
    context: str = "protect"
    session_id: Optional[str] = "default"
    selected_account: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    property_id: Optional[str] = None

# Import the account context function from growth_endpoint
from .growth_endpoint import get_account_context

def extract_protection_metrics_from_mcp_data(clean_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract protection-specific metrics - focus on safeguarding winners, risk analysis"""
    try:
        campaigns = clean_data.get("campaigns", {})
        if not campaigns:
            return None
        
        # Find campaigns that need protection (winners at risk)
        campaign_list = []
        for campaign_name, campaign_data in campaigns.items():
            roas = campaign_data.get('roas', 0)
            spend = campaign_data.get('spend', 0)
            conversions = campaign_data.get('conversions', 0)
            cpc = campaign_data.get('cpc', 0)
            
            campaign_list.append({
                "name": campaign_name,
                "roas": roas,
                "spend": spend,
                "conversions": conversions,
                "cpc": cpc
            })
        
        # Sort by ROAS (best first - these need protection)
        campaign_list.sort(key=lambda x: x["roas"], reverse=True)
        
        if not campaign_list:
            return None
            
        best_campaign = campaign_list[0]  # Highest ROAS - needs protection
        at_risk_campaigns = [c for c in campaign_list if c["roas"] > 0.4 and c["spend"] > 1000]  # Winners spending significant budget
        
        # Calculate protection metrics - DIFFERENT FROM GROWTH PAGE
        total_winner_spend = sum(c["spend"] for c in at_risk_campaigns)
        # Protection percentage = amount of budget in high-performing campaigns vs total
        total_spend = sum(c["spend"] for c in campaign_list)
        protection_percentage = int((total_winner_spend / total_spend * 100)) if total_spend > 0 else 0
        protection_percentage = min(max(protection_percentage, 15), 95)  # Keep between 15-95%
        
        # Risk analysis - campaigns with high spend but declining potential
        risk_budget = sum(c["spend"] for c in campaign_list if c["roas"] < 0.3)
        
        return {
            "protection_percentage": protection_percentage,
            "best_campaign": best_campaign,
            "at_risk_campaigns": len(at_risk_campaigns),
            "total_winner_spend": int(total_winner_spend),
            "risk_budget": int(risk_budget),
            "campaigns_to_protect": len([c for c in campaign_list if c["roas"] > 0.4])
        }
        
    except Exception as e:
        print(f"[PROTECT-METRICS] Error extracting metrics: {str(e)}")
        return None

def format_protection_response(claude_response: str, clean_data: Dict[str, Any], protection_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Format protection response for UI display - SAME structure as Growth/Optimize pages"""
    
    if not protection_metrics:
        # Fallback response
        return {
            "success": True,
            "header": {
                "percentage": 0,
                "description": "Unable to analyze\nprotection opportunities", 
                "icon": "🛡️"
            },
            "insights": [
                "Protection analysis unavailable",
                "Please check your campaign data",
                "Contact support if issues persist"
            ],
            "roas": {
                "percentage": 0,
                "trend": "neutral",
                "label": "Winner Campaign ROAS"
            },
            "boxes": [
                {"value": "R0", "label": "Budget at Risk", "trend": "neutral"},
                {"value": "0", "label": "Campaigns to Protect", "trend": "neutral"}
            ],
            "prediction": {
                "amount": "R0",
                "confidence": "low",
                "description": "Unable to generate protection recommendations"
            }
        }
    
    # Extract insights EXACTLY like Growth page 
    insights = []
    lines = claude_response.split('\n')
    for line in lines:
        line = line.strip()
        # Remove bullet and number prefixes like Growth endpoint
        if line.startswith('- '):
            line = line[2:].strip()
        if line.startswith('• '):
            line = line[2:].strip()
        # Remove all numbered bullets more comprehensively
        if line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
            line = line[3:].strip()
        # Also handle cases without space after number
        if len(line) > 2 and line[0].isdigit() and line[1] == '.' and (line[2] == ' ' or line[2].isalpha()):
            line = line[2:].strip() if line[2] == ' ' else line[2:].strip()
        
        if (line and len(line) > 20 and 
            not line.startswith('Looking at') and not line.startswith('Based on') and
            not line.startswith('🛡️') and not line.startswith('🚨') and 
            not line.startswith('AVAILABLE PLATFORMS') and not line.startswith('PROTECTION QUESTION') and
            not line.startswith('IDENTIFY') and not line.startswith('QUANTIFY') and
            'PROTECTION ANALYSIS' not in line and 'RULES:' not in line):
            # Clean up the line and add as insight (max 3 for UI) - SAME AS GROWTH
            if len(insights) < 3:
                insights.append(line[:120] + '...' if len(line) > 120 else line)
    
    # Only use loading fallback if NO insights found - NO FAKE DATA
    if not insights:
        insights = [
            "Analyzing protection opportunities for your campaigns...",
            "Processing risk assessment from campaign data...", 
            "Generating safeguarding recommendations..."
        ]
    
    best_campaign = protection_metrics.get("best_campaign", {})
    best_roas_pct = int((best_campaign.get("roas", 0)) * 100) if best_campaign else 0
    
    return {
        "success": True,
        "header": {
            "percentage": protection_metrics["protection_percentage"],
            "description": f"Protection priority for\n{best_campaign.get('name', 'top performers')[:20] if best_campaign else 'campaigns'}",
            "icon": "🛡️"
        },
        "insights": insights,
        "roas": {
            "percentage": best_roas_pct,
            "trend": "up",
            "label": "Winner Campaign ROAS"
        },
        "boxes": [
            {
                "value": f"{best_roas_pct}%",
                "label": "Top Winner ROAS",
                "trend": "up"  # High ROAS is good to protect
            },
            {
                "value": f"R{best_campaign.get('cpc', 0):.2f}",
                "label": "Winner Cost Per Click", 
                "trend": "down"  # Low CPC is good for protection
            }
        ],
        "prediction": {
            "amount": f"R{protection_metrics.get('risk_budget', 0):,}",
            "confidence": "high" if protection_metrics.get('protection_percentage', 0) > 40 else "medium",
            "description": f"Risk budget identified - redirect away from {best_campaign.get('name', 'winners')} threats"
        }
    }

@router.post("/api/fix-data")
async def get_protect_data(request: ProtectDataRequest):
    """
    Protect page endpoint - Risk mitigation, safeguarding winners using proven Growth pattern
    Focus: Protect high-performing campaigns, risk analysis, winner safeguarding
    """
    start_time = asyncio.get_event_loop().time()
    
    print(f"[PROTECT-DATA] Processing Protect request: {request.question}")
    print(f"[PROTECT-DATA] Using hardcoded Cherry Time context for reliability")
    
    # Extract account info but use hardcoded Onvlee values for consistency
    user_id = request.user_id or "106540664695114193744" 
    google_ads_id = request.account_id or "7482456286"
    ga4_property_id = request.property_id or "428236885"
    
    print(f"[PROTECT-DATA] Account IDs: User {user_id}, Google Ads {google_ads_id}, GA4 {ga4_property_id}")
    
    try:
        # Get the ADK marketing agent (same as Growth/Optimize endpoint)
        agent = await get_adk_marketing_agent()
        
        # Build MCP request with hardcoded DFSA account (identical to Growth/Optimize)
        user_context = {
            "user_id": user_id,
            "focus_account": "dfsa",  # Use DFSA configuration
            "start_date": "2025-08-03",
            "end_date": "2025-09-02"
        }
        
        print(f"[PROTECT-DATA] Calling MCP with context: {user_context}")
        
        # Get comprehensive insights from MCP (same as Growth/Optimize endpoint)
        mcp_result = await agent._execute_tool(
            {"name": "get_comprehensive_insights"}, 
            user_context
        )
        
        # Use same MCP result parsing as Growth/Optimize endpoint
        if isinstance(mcp_result, dict) and 'success' in mcp_result and 'individual_insights' in mcp_result:
            real_mcp_data = mcp_result
            print(f"[PROTECT-DATA] SUCCESS: Using direct MCP data structure")
        elif isinstance(mcp_result, dict) and 'result' in mcp_result:
            mcp_nested = mcp_result['result']
            if isinstance(mcp_nested, dict) and 'structuredContent' in mcp_nested:
                real_mcp_data = mcp_nested['structuredContent']
                print(f"[PROTECT-DATA] SUCCESS: Using structuredContent from wrapper")
            else:
                return {"success": False, "error": "No structuredContent in MCP result"}
        else:
            return {"success": False, "error": "Invalid MCP result structure"}
        
        print(f"[PROTECT-DATA] MCP returned {len(str(real_mcp_data))} characters of data")
        
        # SAME platform validation as Growth/Optimize endpoint
        available_platforms = real_mcp_data.get('configuration', {}).get('platforms_analyzed', [])
        campaign_summary_direct = real_mcp_data.get('individual_insights', {}).get('google_ads', {}).get('ad_performance', {}).get('campaign_summary', {})
        campaign_comparison = real_mcp_data.get('individual_insights', {}).get('google_ads', {}).get('campaign_comparison', {}).get('campaign_comparison', {})
        
        # Apply same fallback logic as Growth/Optimize endpoint
        if len(campaign_summary_direct) == 0 and len(campaign_comparison) > 0:
            campaign_summary_direct = campaign_comparison
        
        # Create same clean data structure as Growth/Optimize endpoint
        clean_data = {
            "platforms_analyzed": ', '.join(available_platforms),
            "date_range": real_mcp_data.get('analysis_period', ''),
            "campaigns": {}
        }
        
        # Add ONLY campaign_summary data (same as Growth/Optimize endpoint)
        for campaign_name, campaign_data in campaign_summary_direct.items():
            comparison_data = campaign_comparison.get(campaign_name, {})
            clean_data["campaigns"][campaign_name] = {
                "impressions": campaign_data.get('impressions', 0),
                "clicks": campaign_data.get('clicks', 0),
                "spend": campaign_data.get('spend', 0),
                "conversions": campaign_data.get('conversions', 0),
                "ctr": campaign_data.get('ctr', 0),
                "cpc": campaign_data.get('cpc', 0),
                "roas": campaign_data.get('roas', 0),  # CLEAN ROAS from campaign_summary
                "cost_per_conversion": comparison_data.get('cost_per_conversion', 0)
            }
        
        # Protect-specific question for Claude
        protect_question = "What needs protecting? Which winning campaigns are at risk and how can we safeguard our top performers?"
        
        # Calculate dynamic thresholds from actual data
        campaigns = clean_data.get("campaigns", {})
        if campaigns:
            roas_values = [float(camp.get('roas', 0)) for camp in campaigns.values()]
            highest_roas = max(roas_values) if roas_values else 0.5
            high_roas_threshold = int(highest_roas * 100)  # Convert to percentage
        else:
            high_roas_threshold = 40  # Fallback
        
        # Protect-focused Claude prompt - DYNAMIC DATA DRIVEN
        platforms_list = ', '.join(available_platforms)
        claude_prompt = f"""Analyze this campaign data and provide protection recommendations.

CAMPAIGN DATA:
{json.dumps(clean_data, indent=2)}

Question: {protect_question}

Provide 3-4 concise insights about protecting your best campaigns. Use South African Rand (R) for all currency amounts. Be direct and specific - no introductions."""

        # Use same Claude agent system as Growth/Optimize endpoint
        from services.claude_agent import get_claude_intent_agent
        claude_agent = await get_claude_intent_agent()
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": claude_agent.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": claude_agent.model,
            "max_tokens": 1500,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": claude_prompt}]
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages", 
                headers=headers, 
                json=payload
            )
            response.raise_for_status()
            
            claude_result = response.json()
            
            if 'content' in claude_result and len(claude_result['content']) > 0:
                claude_response = claude_result['content'][0]['text'].strip()
            else:
                raise Exception("No content in Claude response")
        
        # Extract protection metrics from MCP data
        protection_metrics = extract_protection_metrics_from_mcp_data(clean_data)
        
        # Format for Protect page UI
        protect_ui_response = format_protection_response(claude_response, clean_data, protection_metrics)
        
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        print(f"[PROTECT-DATA] Success! Protection percentage: {protection_metrics['protection_percentage'] if protection_metrics else 0}%, Response time: {response_time_ms}ms")
        
        # Add debug info
        protect_ui_response.update({
            "debug_info": {
                "best_campaign_roas": protection_metrics["best_campaign"]["roas"] if protection_metrics and protection_metrics["best_campaign"] else None,
                "claude_response_preview": claude_response[:100] + "..." if len(claude_response) > 100 else claude_response,
                "response_time_ms": response_time_ms,
                "model_used": claude_agent.model
            }
        })
        
        # Wrap response in data property for frontend compatibility (same as Growth/Optimize)
        return {
            "success": True,
            "data": protect_ui_response
        }
        
    except Exception as e:
        print(f"[PROTECT-DATA] Error: {str(e)}")
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "success": False,
            "error": str(e),
            "response_time_ms": response_time_ms
        }