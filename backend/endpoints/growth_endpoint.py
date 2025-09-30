"""
Growth Endpoint - Revenue/conversion opportunities, scaling winners

Rebuilt using the proven chat endpoint pattern with Growth-specific focus.
Uses same bulletproof MCP + database integration with UI formatting for Growth page.
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

class GrowthDataRequest(BaseModel):
    question: str
    user: str = "trystin@11and1.com"
    context: str = "growth"
    session_id: Optional[str] = "default"
    selected_account: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    property_id: Optional[str] = None

def get_account_context(session_id: str, db: Session) -> Dict[str, Any]:
    """Get account context from session using proper session service"""
    try:
        from services.session_service import SessionService
        session_service = SessionService()
        session_service.db = db

        # Get active session and selected account
        session = session_service.get_active_session(session_id)
        if not session or not session.selected_account_id:
            print(f"[GROWTH-ACCOUNT-CONTEXT] No session or account found for: {session_id}")
            # Fallback to first available account
            account = db.query(AccountMapping).filter(AccountMapping.is_active == True).order_by(AccountMapping.sort_order).first()
        else:
            # Get account mapping from selected account
            account = session_service.get_account_mapping(session.selected_account_id)

        print(f"[GROWTH-ACCOUNT-CONTEXT] Using account: {account.account_name if account else 'None'}")

        if not account:
            raise ValueError(f"Account not found for session: {session_id}")

        return {
            "user_id": session.google_user_id if session else "106540664695114193744",
            "account_id": account.account_id,
            "account_name": account.account_name,
            "google_ads_id": account.google_ads_id,
            "ga4_property_id": account.ga4_property_id,
            "business_type": account.business_type,
            "focus_account": account.account_id,
            "start_date": "2025-08-03",
            "end_date": "2025-09-02"
        }
    except Exception as e:
        print(f"[GROWTH-ACCOUNT-CONTEXT] Error: {e}")
        # Fallback to first available account
        account = db.query(AccountMapping).filter(AccountMapping.is_active == True).order_by(AccountMapping.sort_order).first()
        if not account:
            # Ultimate fallback to DFSA
            return {
                "user_id": "106540664695114193744",
                "account_id": "dfsa",
                "account_name": "DFSA - Goodness to Go",
                "google_ads_id": "7574136388",
                "ga4_property_id": "458016659",
                "business_type": "food",
                "focus_account": "dfsa",
                "start_date": "2025-08-03",
                "end_date": "2025-09-02"
            }

        return {
            "user_id": "106540664695114193744",
            "account_id": account.account_id,
            "account_name": account.account_name,
            "google_ads_id": account.google_ads_id,
            "ga4_property_id": account.ga4_property_id,
            "business_type": account.business_type,
            "focus_account": account.account_id,
            "start_date": "2025-08-03",
            "end_date": "2025-09-02"
        }

# Import the proven logic functions from chat_endpoint
from .chat_endpoint import (
    detect_creative_question,
    get_creative_insights_for_question,
    _format_creative_insights_for_prompt
)

def extract_growth_metrics_from_mcp_data(mcp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and format Growth-specific metrics from MCP data"""
    
    campaigns = mcp_data.get("campaigns", {})
    if not campaigns:
        return None
        
    # Find the best performing campaign (highest ROAS)
    best_campaign = None
    best_roas = 0
    total_spend = 0
    total_conversions = 0
    worst_campaign = None
    worst_cost_per_conversion = 0
    
    for campaign_name, campaign_data in campaigns.items():
        roas = float(campaign_data.get("roas", 0))
        spend = float(campaign_data.get("spend", 0))
        conversions = float(campaign_data.get("conversions", 0))
        cost_per_conversion = float(campaign_data.get("cost_per_conversion", 0))
        
        total_spend += spend
        total_conversions += conversions
        
        # Track best performer
        if roas > best_roas:
            best_roas = roas
            best_campaign = {
                "name": campaign_name,
                "roas": roas,
                "spend": spend,
                "conversions": conversions
            }
            
        # Track worst performer (highest cost per conversion with reasonable spend)
        if spend > 100 and cost_per_conversion > worst_cost_per_conversion:
            worst_cost_per_conversion = cost_per_conversion
            worst_campaign = {
                "name": campaign_name,
                "cost_per_conversion": cost_per_conversion,
                "spend": spend
            }
    
    if not best_campaign:
        return None
        
    # Calculate growth opportunity metrics
    overall_roas = (total_conversions / total_spend) if total_spend > 0 else 0
    growth_percentage = int(best_roas * 100)  # Convert to percentage (e.g., 0.5357 -> 54%)
    
    # Calculate potential reallocation from worst to best performer
    reallocation_amount = worst_campaign["spend"] if worst_campaign else 0
    
    return {
        "best_campaign": best_campaign,
        "worst_campaign": worst_campaign,
        "growth_percentage": growth_percentage,
        "overall_roas": overall_roas,
        "total_spend": total_spend,
        "total_conversions": total_conversions,
        "reallocation_amount": reallocation_amount
    }

def format_growth_response(claude_response: str, mcp_data: Dict[str, Any], growth_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Format the Growth page UI response using authentic MCP data"""
    
    if not growth_metrics:
        # Fallback data structure
        return {
            "success": True,
            "header": {
                "percentage": 0,
                "description": "Growth analysis unavailable",
                "icon": "📈"
            },
            "insights": ["Unable to analyze growth opportunities"],
            "roas": {
                "percentage": 0,
                "trend": "stable",
                "label": "Current ROAS"
            },
            "boxes": [
                {"value": "R0", "label": "Growth Potential"},
                {"value": "0%", "label": "Best Campaign"}
            ],
            "prediction": {
                "amount": "R0",
                "confidence": "low",
                "description": "Insufficient data for growth analysis"
            }
        }
    
    # Extract growth insights from Claude response - clean format without prefixes
    insights = []
    lines = claude_response.split('\n')
    for line in lines:
        line = line.strip()
        # Remove bullet and number prefixes like Optimize endpoint
        if line.startswith('- '):
            line = line[2:].strip()
        if line.startswith('• '):
            line = line[2:].strip()
        # Remove all numbered bullets more comprehensively
        if line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):  # Remove numbered bullets
            line = line[3:].strip()
        # Also handle cases without space after number
        if len(line) > 2 and line[0].isdigit() and line[1] == '.' and (line[2] == ' ' or line[2].isalpha()):
            line = line[2:].strip() if line[2] == ' ' else line[2:].strip()
        
        if line and len(line) > 20 and not line.startswith('Looking at') and not line.startswith('Based on'):
            # Clean up the line and add as insight (max 3 for UI)
            if len(insights) < 3:
                insights.append(line[:120] + '...' if len(line) > 120 else line)
    
    if not insights:
        insights = [
            "Analyzing growth opportunities for your campaigns...",
            "Processing scaling recommendations from campaign data...", 
            "Generating budget reallocation strategies..."
        ]
    
    # Determine trend based on ROAS
    trend = "up" if growth_metrics['growth_percentage'] > 40 else "down" if growth_metrics['growth_percentage'] < 20 else "stable"
    
    return {
        "success": True,
        "header": {
            "percentage": growth_metrics['growth_percentage'],
            "description": f"Revenue growth potential by scaling {growth_metrics['best_campaign']['name']}",
            "icon": "📈"
        },
        "insights": insights,
        "roas": {
            "percentage": growth_metrics['growth_percentage'],
            "trend": trend,
            "label": "Best Campaign ROAS"
        },
        "boxes": [
            {
                "value": f"R{growth_metrics['reallocation_amount']:,.0f}",
                "label": "Budget to Reallocate"
            },
            {
                "value": f"{growth_metrics['best_campaign']['conversions']:.0f}",
                "label": "Conversions from Winner"
            }
        ],
        "prediction": {
            "amount": f"R{growth_metrics['reallocation_amount']:,.0f}",
            "confidence": "high" if growth_metrics['growth_percentage'] > 40 else "medium",
            "description": f"Reallocate to {growth_metrics['best_campaign']['name']} for maximum growth"
        }
    }

@router.post("/api/growth-data")
async def get_growth_data(request: GrowthDataRequest):
    """
    Growth page endpoint - Revenue/conversion opportunities, scaling winners
    
    Uses the proven bulletproof chat logic with Growth-specific UI formatting.
    Focus: Identify best performers and scaling opportunities.
    """
    start_time = asyncio.get_event_loop().time()
    
    print(f"[GROWTH-DATA] Processing Growth request: {request.question}")
    print(f"[GROWTH-DATA] Using hardcoded Cherry Time context for reliability")
    
    # Extract account info but use hardcoded Onvlee values for consistency
    user_id = request.user_id or "106540664695114193744" 
    google_ads_id = request.account_id or "7482456286"
    ga4_property_id = request.property_id or "428236885"
    
    print(f"[GROWTH-DATA] Account IDs: User {user_id}, Google Ads {google_ads_id}, GA4 {ga4_property_id}")
    
    try:
        # Get the ADK marketing agent (same as chat endpoint)
        agent = await get_adk_marketing_agent()
        
        # Build MCP request with hardcoded DFSA account (identical to chat)
        user_context = {
            "user_id": user_id,
            "focus_account": "dfsa",  # Use DFSA configuration 
            "start_date": "2025-08-03",
            "end_date": "2025-09-02"
        }
        
        print(f"[GROWTH-DATA] Calling MCP with context: {user_context}")
        
        # Get comprehensive insights from MCP (same as chat endpoint)
        mcp_result = await agent._execute_tool(
            {"name": "get_comprehensive_insights"}, 
            user_context
        )
        
        # Use same MCP result parsing as chat endpoint
        if isinstance(mcp_result, dict) and 'success' in mcp_result and 'individual_insights' in mcp_result:
            real_mcp_data = mcp_result
            print(f"[GROWTH-DATA] SUCCESS: Using direct MCP data structure")
        elif isinstance(mcp_result, dict) and 'result' in mcp_result:
            mcp_nested = mcp_result['result']
            if isinstance(mcp_nested, dict) and 'structuredContent' in mcp_nested:
                real_mcp_data = mcp_nested['structuredContent']
                print(f"[GROWTH-DATA] SUCCESS: Using structuredContent from wrapper")
            else:
                return {"success": False, "error": "No structuredContent in MCP result"}
        else:
            return {"success": False, "error": "Invalid MCP result structure"}
            
        # SAME platform validation as chat endpoint
        available_platforms = real_mcp_data.get('configuration', {}).get('platforms_analyzed', [])
        unavailable_platforms = ['facebook', 'linkedin', 'tiktok', 'twitter', 'instagram', 'youtube', 'snapchat', 'pinterest', 'reddit']
        
        # Build same clean data structure as chat endpoint
        google_ads_insights = real_mcp_data.get('individual_insights', {}).get('google_ads', {})
        campaign_summary_direct = google_ads_insights.get('campaign_summary', {})
        campaign_comparison = google_ads_insights.get('campaign_comparison', {}).get('campaign_comparison', {})
        
        # Apply same fallback logic as chat endpoint
        if len(campaign_summary_direct) == 0 and len(campaign_comparison) > 0:
            campaign_summary_direct = campaign_comparison
        
        # Create same clean data structure as chat endpoint
        clean_data = {
            "platforms_analyzed": ', '.join(available_platforms),
            "date_range": real_mcp_data.get('analysis_period', ''),
            "campaigns": {}
        }
        
        # Add ONLY campaign_summary data (same as chat endpoint)
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
        
        # Growth-specific question for Claude
        growth_question = "Where can we grow? What are our best scaling opportunities and which campaigns should we increase budget for?"
        
        # Growth-focused Claude prompt
        platforms_list = ', '.join(available_platforms)
        claude_prompt = f"""You are Mia, a conversational marketing intelligence assistant.

AVAILABLE PLATFORMS: {platforms_list}
GROWTH QUESTION: "{growth_question}"

📈 GROWTH ANALYSIS - Focus on Revenue & Scaling Opportunities

🚨 GROWTH ANALYSIS RULES:
1. IDENTIFY the highest ROAS campaign as the primary scaling opportunity
2. RECOMMEND specific budget reallocation from worst to best performers  
3. QUANTIFY the growth potential in specific rand amounts
4. FOCUS on revenue opportunities and conversion scaling
5. Be specific about which campaigns to scale UP and which to scale DOWN
6. Provide actionable growth recommendations with concrete numbers

🎯 GROWTH PRIORITIES:
- Scale campaigns with highest ROAS (53%+ is excellent)
- Reallocate budget from campaigns with high cost-per-conversion  
- Focus on campaigns driving actual conversions, not just clicks
- Identify specific rand amounts for budget reallocation

CAMPAIGN DATA (YOUR ONLY DATA SOURCE):
{json.dumps(clean_data, indent=2)}

Provide specific growth recommendations focusing on scaling winners and budget reallocation opportunities."""

        # Use same Claude agent system as chat endpoint
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
        
        # Extract growth metrics from MCP data
        growth_metrics = extract_growth_metrics_from_mcp_data(clean_data)
        
        # Format for Growth page UI
        growth_ui_response = format_growth_response(claude_response, clean_data, growth_metrics)
        
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        print(f"[GROWTH-DATA] Success! Growth percentage: {growth_metrics['growth_percentage'] if growth_metrics else 0}%, Response time: {response_time_ms}ms")
        
        # Add debug info
        growth_ui_response.update({
            "debug_info": {
                "best_campaign_roas": growth_metrics["best_campaign"]["roas"] if growth_metrics and growth_metrics["best_campaign"] else None,
                "claude_response_preview": claude_response[:100] + "..." if len(claude_response) > 100 else claude_response,
                "response_time_ms": response_time_ms,
                "model_used": claude_agent.model
            }
        })
        
        # Wrap response in data property for frontend compatibility
        return {
            "success": True,
            "data": growth_ui_response
        }
        
    except Exception as e:
        print(f"[GROWTH-DATA] Error: {str(e)}")
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "success": False,
            "error": str(e),
            "response_time_ms": response_time_ms
        }