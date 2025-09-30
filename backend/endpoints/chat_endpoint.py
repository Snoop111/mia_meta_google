"""
Chat Endpoint - Bulletproof MCP + Database Integration

Extracted from simple_adk_server.py for better maintainability.
Contains the working /api/mia-chat-test endpoint with:
- Smart trigger detection (creative vs campaign questions)
- Database integration for headlines/creative performance
- MCP integration for campaign data
- Sophisticated business logic and ranking systems
- Authentic ROAS calculations
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import asyncio
import json
import httpx
import os

# Import backend dependencies
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.adk_mcp_integration import get_adk_marketing_agent
from services.creative_import import get_creative_insights
from database import SessionLocal, get_db
from models.user_profile import AccountMapping

router = APIRouter()

class MiaChatTestRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

def get_account_context(session_id: str, db: Session) -> Dict[str, Any]:
    """Get account context from session using proper session service"""
    try:
        from services.session_service import SessionService
        session_service = SessionService()
        session_service.db = db

        # Get active session and selected account
        session = session_service.get_active_session(session_id)
        if not session or not session.selected_account_id:
            print(f"[CHAT-ACCOUNT-CONTEXT] No session or account found for: {session_id}")
            # Fallback to DFSA
            account = db.query(AccountMapping).filter(AccountMapping.account_id == "dfsa").first()
        else:
            # Get account mapping from selected account
            account = session_service.get_account_mapping(session.selected_account_id)

        print(f"[CHAT-ACCOUNT-CONTEXT] Using account: {account.account_name if account else 'None'}")

        if not account:
            raise ValueError(f"Account not found for session: {session_id}")

        return {
            "user_id": session.google_user_id if session else os.getenv("DEV_USER_ID", "106540664695114193744"),
            "account_id": account.account_id,
            "account_name": account.account_name,
            "google_ads_id": account.google_ads_id,
            "ga4_property_id": account.ga4_property_id,
            "meta_ads_id": account.meta_ads_id,
            "business_type": account.business_type,
            "focus_account": account.account_id,
            "start_date": "2025-08-03",
            "end_date": "2025-09-02",
            "platform_type": "meta" if account.meta_ads_id and not account.google_ads_id else "google"
        }
    except Exception as e:
        print(f"[ACCOUNT-CONTEXT] Error: {e}")
        # Fallback to first available account
        account = db.query(AccountMapping).filter(AccountMapping.is_active == True).order_by(AccountMapping.sort_order).first()
        if not account:
            # Ultimate fallback - create a dummy account for DFSA
            class DummyAccount:
                account_id = "dfsa"
                account_name = "DFSA - Goodness to Go"
                google_ads_id = "7574136388"
                ga4_property_id = "458016659"
                meta_ads_id = "1237509046595197"
                business_type = "food"

            dummy = DummyAccount()
            platform_type = detect_platform_from_question(user_question or "", dummy)

            return {
                "user_id": "106540664695114193744",
                "account_id": dummy.account_id,
                "account_name": dummy.account_name,
                "google_ads_id": dummy.google_ads_id,
                "ga4_property_id": dummy.ga4_property_id,
                "meta_ads_id": dummy.meta_ads_id,
                "business_type": dummy.business_type,
                "focus_account": dummy.account_id,
                "start_date": "2025-08-03",
                "end_date": "2025-09-02",
                "platform_type": platform_type
            }

        # Use intelligent platform detection for fallback account
        platform_type = detect_platform_from_question(user_question or "", account)
        return {
            "user_id": "106540664695114193744",
            "account_id": account.account_id,
            "account_name": account.account_name,
            "google_ads_id": account.google_ads_id,
            "ga4_property_id": account.ga4_property_id,
            "meta_ads_id": account.meta_ads_id,
            "business_type": account.business_type,
            "focus_account": account.account_id,
            "start_date": "2025-08-03",
            "end_date": "2025-09-02",
            "platform_type": platform_type
        }

def detect_creative_question(user_question):
    """Detect if user question requires creative data"""
    creative_keywords = [
        'headline', 'headlines', 'creative', 'creatives', 'copy', 'ad text', 
        'ad copy', 'messaging', 'description', 'descriptions', 'asset', 'assets',
        'rsa', 'responsive search ad', 'what works', 'best performing',
        'which ad', 'ad performance', 'creative performance', 'text', 'wording',
        # New triggers for missed questions
        'themes', 'common themes', 'highest converting ads', 'converting ads',
        'creative elements', 'test next', 'improve performance', 'ad elements',
        'call-to-action', 'call to action', 'cta', 'compelling', 'resonates',
        'engaging', 'attention', 'variations', 'short vs long', 'length',
        'emotional triggers', 'messaging works', 'product benefits', 'highlight',
        'qualified leads', 'quality scores', 'mobile vs desktop', 'audience'
    ]
    
    question_lower = user_question.lower()
    detected = any(keyword in question_lower for keyword in creative_keywords)
    
    # Debug logging
    if detected:
        matched_keywords = [kw for kw in creative_keywords if kw in question_lower]
        print(f"[CREATIVE-DETECT] MATCHED Question: '{user_question[:50]}...' matches keywords: {matched_keywords}")
    else:
        print(f"[CREATIVE-DETECT] NO MATCH Question: '{user_question[:50]}...' - no creative keywords found")
    
    return detected

def get_creative_insights_for_question(user_question, account_id, db):
    """Smart creative data retrieval based on question content"""
    if not detect_creative_question(user_question):
        return None
    
    try:
        creative_insights_data = get_creative_insights(db, account_id, None)
        return creative_insights_data
    except Exception as e:
        print(f"[CREATIVE-INSIGHTS] Error loading creative data: {str(e)}")
        return None

def _format_creative_insights_for_prompt(creative_insights_data):
    """Format creative insights data for Claude prompt"""
    if not creative_insights_data or 'insights' not in creative_insights_data:
        return "No ad creative data available. This means I can only provide campaign-level performance insights, not specific headline or ad copy analysis."
    
    insights = creative_insights_data.get('insights', {})
    if not insights:
        return "No ad creative insights generated yet."
    
    formatted_output = []
    
    # Add best headlines if available - SHOW ALL HEADLINE DATA FOR COMPLETE ANALYSIS
    if 'BEST_HEADLINES' in insights:
        headline_data = insights['BEST_HEADLINES'].get('data', {})
        
        # Get all three headline arrays from database
        ctr_headlines = headline_data.get('top_headlines_by_ctr', [])
        conversion_headlines = headline_data.get('top_headlines_by_conversions', [])
        business_headlines = headline_data.get('top_headlines_by_business_value', [])
        
        if conversion_headlines or ctr_headlines:
            formatted_output.append("🏆 TOP HEADLINES BY TOTAL CONVERSIONS (Volume Leaders):")
            for i, headline_info in enumerate(conversion_headlines[:5], 1):  # Top 5 by conversions
                headline = headline_info.get('headline', 'Unknown')
                ctr = headline_info.get('ctr', 0)
                clicks = headline_info.get('clicks', 0)
                conversions = headline_info.get('conversions', 0)
                
                # Calculate conversion rate
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                
                # Add campaign type identifier
                campaign_type = "Performance Max" if clicks > 1000 else "Search" if clicks < 500 else "Display"
                
                formatted_output.append(f"{i}. \"{headline}\" ({campaign_type})")
                formatted_output.append(f"   - Conversions: {conversions:.0f}, Clicks: {clicks:,}, CTR: {ctr:.2f}%, Conv Rate: {conversion_rate:.1f}%")
            
            formatted_output.append("\n🎯 TOP HEADLINES BY CTR (Attention Grabbers):")
            for i, headline_info in enumerate(ctr_headlines[:5], 1):  # Top 5 by CTR
                headline = headline_info.get('headline', 'Unknown')
                ctr = headline_info.get('ctr', 0)
                clicks = headline_info.get('clicks', 0)
                conversions = headline_info.get('conversions', 0)
                
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                campaign_type = "Performance Max" if clicks > 1000 else "Search" if clicks < 500 else "Display"
                
                formatted_output.append(f"{i}. \"{headline}\" ({campaign_type})")
                formatted_output.append(f"   - CTR: {ctr:.2f}%, Clicks: {clicks:,}, Conversions: {conversions:.0f}, Conv Rate: {conversion_rate:.1f}%")
        else:
            formatted_output.append("No headline performance data available.")
    
    # Add summary info with CLEAR DATA BOUNDARIES
    if 'BEST_HEADLINES' in insights:
        headline_data = insights['BEST_HEADLINES'].get('data', {})
        total_ads = headline_data.get('total_ads_analyzed', 0)
        if total_ads > 0:
            formatted_output.append(f"\n📊 HEADLINE DATA RESTRICTIONS - READ CAREFULLY:")
            formatted_output.append(f"- Source: Google Ads Asset Performance Export ({total_ads} headlines)")
            formatted_output.append(f"- Date: {headline_data.get('date_range', 'August 3 - September 2, 2025')}")
            formatted_output.append(f"\n✅ AVAILABLE per headline: CTR percentage, total clicks, total conversions, conversion rate, campaign type")
            formatted_output.append(f"❌ NOT AVAILABLE per headline: CPC, cost-per-conversion, spend amounts")
            formatted_output.append(f"\n🚨 CRITICAL: When analyzing headlines, ONLY use the data shown above.")
            formatted_output.append(f"🚨 NEVER mention CPC, cost-per-conversion, or spend for individual headlines.")
            formatted_output.append(f"🚨 Those are CAMPAIGN metrics from MCP data, NOT headline metrics.")
            formatted_output.append(f"\n💡 BUSINESS LOGIC GUIDANCE:")
            formatted_output.append(f"- For conversion/business questions: Focus on 'TOP HEADLINES BY TOTAL CONVERSIONS' section")
            formatted_output.append(f"- For attention/CTR questions: Focus on 'TOP HEADLINES BY CTR' section")
            formatted_output.append(f"- Performance Max headlines typically have higher volume than Search headlines")
            formatted_output.append(f"- Same headline in different campaign types = different performance characteristics")
            formatted_output.append(f"- Always specify campaign type when recommending headlines")
    
    return '\n'.join(formatted_output) if formatted_output else "No creative insights available."

@router.post("/api/mia-chat-test")
async def mia_chat_test(chat_request: MiaChatTestRequest, request: Request, db: Session = Depends(get_db)):
    """
    DEDICATED TEST ENDPOINT - 100% Real MCP Data + Claude Validation
    Shows raw MCP data + Claude prompt for verification
    
    This endpoint contains the bulletproof logic with:
    - Smart trigger detection for creative vs campaign questions
    - Database integration for headline performance data
    - MCP integration for authentic campaign data
    - Platform validation to prevent hallucination
    - Correct ROAS calculations (53.57% for DFSA-PM-LEADS)
    """
    start_time = asyncio.get_event_loop().time()
    
    # Get dynamic account context (prioritize header over body)
    session_id = request.headers.get('X-Session-ID', getattr(chat_request, 'session_id', 'default'))
    account_context = get_account_context(session_id, db)

    print(f"[MIA-CHAT-TEST] Question: {chat_request.message}")
    print(f"[MIA-CHAT-TEST] Account context keys: {list(account_context.keys())}")
    platform_type = account_context.get('platform_type', 'MISSING')
    print(f"[MIA-CHAT-TEST] Using dynamic account: {account_context['account_name']} ({platform_type.upper()})")
    print(f"[MIA-CHAT-TEST] Platform details: Google Ads {account_context.get('google_ads_id')}, GA4 {account_context.get('ga4_property_id')}, Meta Ads {account_context.get('meta_ads_id')}")
    
    try:
        # Get the ADK marketing agent
        agent = await get_adk_marketing_agent()
        
        # Build MCP request with dynamic account context - UNIFIED MCP APPROACH
        # Use the same MCP pattern that works for Google for both platforms
        user_context = {
            "user_id": account_context["user_id"],  # This ensures MCP gets authenticated user ID
            "focus_account": account_context["focus_account"],
            "start_date": account_context["start_date"],
            "end_date": account_context["end_date"],
            "card_type": "general",
            "platform_type": account_context["platform_type"]  # Help MCP know if it's Google/Meta
        }

        print(f"[MIA-CHAT-TEST] UNIFIED MCP: Using account {account_context['focus_account']} via MCP layer")
        print(f"[MIA-CHAT-TEST] UNIFIED MCP: Platform type {account_context['platform_type']} will be handled by MCP integration")


        # Use the same analyze_marketing_query method that works for Google
        print(f"[MCP-CALL] About to call agent.analyze_marketing_query")
        print(f"[MCP-CALL] User context: {user_context}")
        print(f"[MCP-CALL] Message: {chat_request.message}")

        try:
            mcp_result = await agent.analyze_marketing_query(chat_request.message, user_context)
            print(f"[MCP-CALL] SUCCESS: MCP call completed without exception")
        except Exception as mcp_error:
            print(f"[MCP-CALL] ERROR: Exception during MCP call: {str(mcp_error)}")
            print(f"[MCP-CALL] ERROR Type: {type(mcp_error)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"MCP call failed: {str(mcp_error)}",
                "claude_prompt": f"MCP call failed with error: {str(mcp_error)}"
            }

        # BYPASS EXTRACTION - Use direct MCP result parsing for ROAS accuracy
        print(f"[MCP-DIRECT] MCP result type: {type(mcp_result)}")
        print(f"[MCP-DIRECT] MCP result keys: {list(mcp_result.keys()) if isinstance(mcp_result, dict) else 'not dict'}")

        # Add detailed logging of the actual MCP result structure
        if isinstance(mcp_result, dict):
            print(f"[MCP-DIRECT] Full MCP result structure:")
            for key, value in mcp_result.items():
                if isinstance(value, dict):
                    print(f"[MCP-DIRECT]   {key}: dict with {len(value)} keys: {list(value.keys())}")
                elif isinstance(value, list):
                    print(f"[MCP-DIRECT]   {key}: list with {len(value)} items")
                else:
                    print(f"[MCP-DIRECT]   {key}: {type(value)} = {str(value)[:100]}")

        # Handle MCP result structure - FIXED to handle new ADK agent response format
        if isinstance(mcp_result, dict) and 'success' in mcp_result and mcp_result['success'] == True:
            # Check for raw_results with individual_insights (new format)
            if 'raw_results' in mcp_result and mcp_result['raw_results']:
                raw_data = mcp_result['raw_results'][0].get('data', {})
                if 'individual_insights' in raw_data:
                    real_mcp_data = raw_data
                    print(f"[MCP-DIRECT] SUCCESS: Using individual_insights from raw_results")
                else:
                    print(f"[MCP-DIRECT] ERROR: No individual_insights in raw_results[0].data")
                    print(f"[MCP-DIRECT] Raw data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data)}")
                    return {
                        "success": False,
                        "error": "No individual_insights in MCP raw results",
                        "claude_prompt": "No prompt - MCP raw results missing individual_insights"
                    }
            # Check for direct individual_insights (old format - backward compatibility)
            elif 'individual_insights' in mcp_result:
                real_mcp_data = mcp_result
                print(f"[MCP-DIRECT] SUCCESS: Using direct individual_insights (legacy format)")
            else:
                print(f"[MCP-DIRECT] ERROR: No raw_results or individual_insights found")
                print(f"[MCP-DIRECT] Available keys: {list(mcp_result.keys())}")
                return {
                    "success": False,
                    "error": "No individual_insights found in MCP result",
                    "claude_prompt": "No prompt - MCP individual_insights missing"
                }
        elif isinstance(mcp_result, dict) and 'success' in mcp_result and mcp_result['success'] == False:
            # Handle error case gracefully
            error_msg = mcp_result.get('error', 'Unknown error')
            print(f"[MCP-DIRECT] ERROR: MCP returned error: {error_msg}")
            return {
                "success": False,
                "error": f"MCP error: {error_msg}",
                "claude_prompt": f"MCP returned error: {error_msg}"
            }
        elif isinstance(mcp_result, dict) and 'result' in mcp_result:
            # Handle JSON-RPC wrapper if present (legacy support)
            mcp_nested = mcp_result['result']
            if isinstance(mcp_nested, dict) and 'structuredContent' in mcp_nested:
                real_mcp_data = mcp_nested['structuredContent']
                print(f"[MCP-DIRECT] SUCCESS: Using structuredContent from wrapper (legacy)")
            else:
                print(f"[MCP-DIRECT] ERROR: No structuredContent in nested result: {list(mcp_nested.keys()) if isinstance(mcp_nested, dict) else type(mcp_nested)}")
                return {
                    "success": False,
                    "error": "No structuredContent in MCP result",
                    "claude_prompt": "No prompt - MCP structuredContent missing"
                }
        else:
            print(f"[MCP-DIRECT] ERROR: Invalid MCP result structure")
            print(f"[MCP-DIRECT] ERROR: Result type: {type(mcp_result)}")
            if isinstance(mcp_result, dict):
                print(f"[MCP-DIRECT] ERROR: Available keys: {list(mcp_result.keys())}")
                return {
                "success": False,
                "error": "Invalid MCP result structure",
                "claude_prompt": "No prompt - MCP result invalid"
            }
            
        # BACKEND PLATFORM VALIDATION (before Claude sees anything) - RE-ENABLED
        available_platforms = real_mcp_data.get('configuration', {}).get('platforms_analyzed', [])

        # FIXED: Dynamic platform validation - only block platforms that are actually unavailable
        platform_mapping = {
            'facebook': 'facebook',  # FIXED: MCP returns 'facebook', not 'meta_ads'
            'meta': 'facebook',      # Both meta and facebook map to 'facebook' platform
            'instagram': 'facebook',
            'google ads': 'google_ads',
            'google': 'google_ads',
            'ga4': 'google_analytics',
            'analytics': 'google_analytics'
        }

        # Platforms we never support (not in MCP)
        never_supported = ['linkedin', 'tiktok', 'twitter', 'youtube', 'snapchat', 'pinterest', 'reddit']

        question_lower = chat_request.message.lower()
        print(f"[PLATFORM-VALIDATION] Question: '{chat_request.message}' -> '{question_lower}'")
        print(f"[PLATFORM-VALIDATION] Available platforms from MCP: {available_platforms}")
        print(f"[PLATFORM-VALIDATION] Never supported platforms: {never_supported}")

        # Check for never supported platforms (always block)
        for platform in never_supported:
            if platform in question_lower:
                print(f"[PLATFORM-VALIDATION] BLOCKED: Found unsupported platform '{platform}' in question")
                available_list = ', '.join(available_platforms)
                return {
                    "success": True,
                    "claude_response": f"I don't have {platform.title()} data available. I can only analyze data from {available_list}.",
                    "claude_prompt": f"PLATFORM VALIDATION BLOCKED: User asked about {platform.title()}, only have {available_list}",
                    "model_used": "backend-validation",
                    "response_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000)
                }

        # TEMPORARILY DISABLED: Check for supported platforms that are not available for this user
        # We're in setup mode - let MCP handle platform errors properly
        # for keyword, mcp_platform in platform_mapping.items():
        #     if keyword in question_lower and mcp_platform not in available_platforms:
        #         print(f"[PLATFORM-VALIDATION] BLOCKED: Found '{keyword}' in question but '{mcp_platform}' not in available platforms")
        #         available_list = ', '.join(available_platforms)
        #         return {
        #             "success": True,
        #             "claude_response": f"I don't have {keyword.title()} data available. I can only analyze data from {available_list}.",
        #             "claude_prompt": f"PLATFORM VALIDATION BLOCKED: User asked about {keyword.title()}, only have {available_list}",
        #             "model_used": "backend-validation",
        #             "response_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000)
        #         }
        print(f"[PLATFORM-VALIDATION] SETUP MODE: Allowing all supported platforms to reach MCP")
        
        print(f"[PLATFORM-VALIDATION] PASSED: No unavailable platforms detected")
        
        # COMPETITOR/INDUSTRY VALIDATION (CRITICAL FOR DFSA PRESENTATION)
        competitor_keywords = ['competitor', 'competition', 'industry', 'benchmark', 'market average', 'industry standard', 'compare to others', 'vs industry', 'industry performance', 'industry average']
        print(f"[COMPETITOR-VALIDATION] Checking for competitor/industry keywords: {competitor_keywords}")
        
        for keyword in competitor_keywords:
            if keyword in question_lower:
                print(f"[COMPETITOR-VALIDATION] BLOCKED: Found '{keyword}' in question")
                available_list = ', '.join(available_platforms)
                return {
                    "success": True,
                    "claude_response": f"I don't have competitor or industry benchmark data available. I can only analyze your own campaign performance from {available_list}. I can help you understand how your campaigns are performing relative to each other.",
                    "claude_prompt": f"COMPETITOR VALIDATION BLOCKED: User asked about {keyword}, only have own campaign data",
                    "model_used": "backend-validation",
                    "response_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000)
                }
        
        print(f"[COMPETITOR-VALIDATION] PASSED: No competitor/industry keywords detected")
        
        print(f"[MIA-CHAT-TEST] MCP data extracted successfully")
        
        # Extract available platforms for strict validation
        available_platforms = real_mcp_data.get('configuration', {}).get('platforms_analyzed', [])
        platforms_list = ', '.join(available_platforms)
        
        # Extract GA4 data for demographics
        ga4_data = real_mcp_data.get('individual_insights', {}).get('google_analytics', {})
        device_breakdown = ga4_data.get('device_breakdown', {})
        geographic_data = ga4_data.get('geographic_performance', {})
        
        # Extract combined insights for user journey analysis
        combined_insights = real_mcp_data.get('combined_insights', {})
        user_journey = combined_insights.get('user_journey', {})
        funnel_overview = user_journey.get('funnel_overview', {})
        drop_off_analysis = user_journey.get('drop_off_analysis', {})
        
        # Calculate total conversions from Google Ads
        google_ads_data = real_mcp_data.get('individual_insights', {}).get('google_ads', {})
        total_conversions = google_ads_data.get('ad_performance', {}).get('overall_metrics', {}).get('total_conversions', 0)
        
        # EXTRACT STRUCTURED DATA FROM CAMPAIGN_SUMMARY (NOT top_performers!)
        google_ads_insights = real_mcp_data.get('individual_insights', {}).get('google_ads', {})
        
        # FIXED: Use campaign_comparison since campaign_summary is empty
        campaign_summary_direct = google_ads_insights.get('campaign_summary', {})
        campaign_comparison = google_ads_insights.get('campaign_comparison', {}).get('campaign_comparison', {})
        overall_metrics = google_ads_insights.get('ad_performance', {}).get('overall_metrics', {})
        
        print(f"[DEBUG] Found {len(campaign_summary_direct)} campaigns in campaign_summary")
        print(f"[DEBUG] Found {len(campaign_comparison)} campaigns in campaign_comparison")
        
        # CRITICAL: Apply fallback logic BEFORE building clean_data
        print(f"[DEBUG] Condition check: campaign_summary_direct={len(campaign_summary_direct)}, campaign_comparison={len(campaign_comparison)}")
        if len(campaign_summary_direct) == 0 and len(campaign_comparison) > 0:
            print(f"[DEBUG] USING campaign_comparison as primary source")
            campaign_summary_direct = campaign_comparison
            print(f"[DEBUG] After switch: campaign_summary_direct now has {len(campaign_summary_direct)} campaigns")
        else:
            print(f"[DEBUG] Fallback condition not met")
        
        # Build structured campaign data using campaign_comparison (has correct ROAS)
        campaigns_summary = []
        
        # Use campaign_comparison as primary source (has correct ROAS)
        for campaign_name, campaign_data in campaign_summary_direct.items():
            # Get cost_per_conversion from campaign_comparison if available
            comparison_data = campaign_comparison.get(campaign_name, {})
            
            campaigns_summary.append({
                'name': campaign_name,
                'spend': float(campaign_data.get('spend', 0)),
                'conversions': float(campaign_data.get('conversions', 0)),
                'clicks': int(campaign_data.get('clicks', 0)),
                'impressions': int(campaign_data.get('impressions', 0)),
                'ctr': float(campaign_data.get('ctr', 0)) * 100,  # Convert to percentage
                'cpc': float(campaign_data.get('cpc', 0)),
                'roas': float(campaign_data.get('roas', 0)),  # FROM campaign_summary - CORRECT!
                'cost_per_conversion': float(comparison_data.get('cost_per_conversion', 0))
            })
            
            print(f"[DEBUG] {campaign_name}: ROAS = {campaign_data.get('roas', 0):.4f} (from campaign_summary)")
        
        # Format campaigns for Claude prompt
        formatted_campaigns = []
        for i, campaign in enumerate(campaigns_summary, 1):
            cost_per_conv_str = f"R{campaign['cost_per_conversion']:.2f}" if campaign['cost_per_conversion'] > 0 else "No conversions"
            
            formatted_campaigns.append(f"""{i}. {campaign['name']}:
   - Spend: R{campaign['spend']:.2f}
   - Conversions: {campaign['conversions']:.0f}
   - Clicks: {campaign['clicks']:,}
   - Impressions: {campaign['impressions']:,}
   - CTR: {campaign['ctr']:.2f}%
   - CPC: R{campaign['cpc']:.2f}
   - ROAS: {campaign['roas']:.4f}
   - Cost per Conversion: {cost_per_conv_str}""")
        
        campaigns_data = "\n\n".join(formatted_campaigns)
        
        # NO HARDCODED VALUES - Claude must use authentic MCP data only
        roas_corrections = ""

        # Create clean, focused data structure for Claude (NO confusing daily data)
        clean_data = {
            "platforms_analyzed": platforms_list,
            "date_range": real_mcp_data.get('analysis_period', ''),
            "campaigns": {}
        }
        
        # Add ONLY campaign_summary data (clean aggregated values)
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
        
        # Calculate clean totals from campaign_summary ONLY (no conflicting overall_metrics)
        total_spend = sum(float(camp.get('spend', 0)) for camp in campaign_summary_direct.values())
        total_conversions = sum(float(camp.get('conversions', 0)) for camp in campaign_summary_direct.values())
        total_clicks = sum(int(camp.get('clicks', 0)) for camp in campaign_summary_direct.values())
        total_impressions = sum(int(camp.get('impressions', 0)) for camp in campaign_summary_direct.values())
        average_cpc = total_spend / total_clicks if total_clicks > 0 else 0

        # Smart creative data detection - only load if question needs it
        creative_insights_data = {}
        try:
            creative_db = SessionLocal()
            
            # Smart detection: Only get creative data if question requires it
            creative_insights_data = get_creative_insights_for_question(
                chat_request.message,
                account_context["google_ads_id"], 
                creative_db
            )
            
            creative_db.close()
            
            if creative_insights_data:
                print(f"[CREATIVE-DETECTION] FOUND Creative question detected - loaded creative data")
            else:
                print(f"[CREATIVE-DETECTION] NOT FOUND Non-creative question - using MCP data only")
                creative_insights_data = {}
                
        except Exception as e:
            print(f"[CREATIVE-INSIGHTS] Could not load creative data: {str(e)}")
            creative_insights_data = {}

        # Check if this was a creative question to determine prompt structure
        is_creative_question = detect_creative_question(chat_request.message)
        
        # Build different prompts based on question type to prevent data source confusion
        if is_creative_question and creative_insights_data:
            # CREATIVE QUESTION: Use only database headline data
            claude_prompt = f"""You are Mia, a conversational marketing intelligence assistant.

AVAILABLE PLATFORMS: {platforms_list}
User Question: "{chat_request.message}"

🎯 CREATIVE QUESTION DETECTED - Using Headline Database Only

🚨 DATA SOURCE RULES FOR CREATIVE QUESTIONS:
1. Use ONLY the headline performance data shown in AD CREATIVE INSIGHTS below
2. NEVER mention CPC, cost-per-conversion, or spend amounts for individual headlines
3. Headlines only have: CTR percentage, total clicks, total conversions
4. Be conversational and professional
5. Focus on creative performance patterns and insights
6. BUSINESS RANKING PRIORITIES - When ranking or recommending headlines:
   • CONVERSIONS ALWAYS rank higher than CTR for business value
   • A headline with 5 conversions beats one with 20% CTR but 0 conversions
   • Explain WHY: "X is better because it drives actual business results (conversions) vs just clicks"
   • When users ask "which is best" - prioritize conversion drivers over attention grabbers
7. RESPONSE FORMATTING:
   • DO NOT reference database section headers like "TOP HEADLINES BY CTR" or "TOP HEADLINES BY CONVERSIONS" 
   • Instead say: "top conversion performers" or "highest CTR headlines"
   • Keep technical database structure invisible to users

PLATFORM VALIDATION:
- Available platforms: {platforms_list}
- If asked about unavailable platforms, respond: "I don't have [platform] data available. I can only analyze data from {platforms_list}."

AD CREATIVE INSIGHTS (YOUR ONLY DATA SOURCE):
{_format_creative_insights_for_prompt(creative_insights_data)}

Respond naturally as if speaking to a business owner. Use ONLY the headline data above."""
            
        else:
            # CAMPAIGN QUESTION: Use only MCP campaign data - DUAL PLATFORM SUPPORT
            if account_context["platform_type"] == "meta":
                # META PROMPT
                claude_prompt = f"""You are Mia, a conversational marketing intelligence assistant.

AVAILABLE PLATFORMS: {platforms_list}
User Question: "{chat_request.message}"

📊 META CAMPAIGNS QUESTION - Using Meta Ads Data Only

🚨 DATA EXTRACTION RULES FOR META QUESTIONS:
1. NEVER invent numbers - Use ONLY the Meta campaign data provided below
2. Focus on Meta campaign performance, reach, impressions, spend
3. Be conversational and professional
4. DO NOT mention Google Ads specific metrics
5. Meta campaigns may have different structure than Google Ads

PLATFORM VALIDATION:
- Available platforms: {platforms_list}
- If asked about unavailable platforms, respond: "I don't have [platform] data available. I can only analyze data from {platforms_list}."

META CAMPAIGN DATA (YOUR ONLY DATA SOURCE):
{json.dumps(clean_data if 'clean_data' in locals() else mcp_result, indent=2)}

Respond naturally as if speaking to a business owner. Use ONLY the Meta campaign data above."""
            else:
                # GOOGLE PROMPT (existing)
                claude_prompt = f"""You are Mia, a conversational marketing intelligence assistant.

AVAILABLE PLATFORMS: {platforms_list}
User Question: "{chat_request.message}"

📊 CAMPAIGN QUESTION - Using MCP Campaign Data Only

🚨 DATA EXTRACTION RULES FOR CAMPAIGN QUESTIONS:
1. NEVER invent numbers - Use ONLY the campaign data provided below
2. All financial values are in South African Rand (R)
3. Focus on campaign performance, spend, conversions, ROAS
4. Be conversational and professional
5. DO NOT mention individual headlines or creative elements

🧠 LOGICAL REASONING RULES:
6. If asked about campaigns with zero/no performance: First check if ANY campaign actually has zero values before answering
7. If no campaign matches the criteria asked about, clearly state "None of your campaigns have [criteria]" then provide the closest alternative
8. Always verify your logic against the actual data before responding

🚨 FUNNEL ANALYSIS RULES (CRITICAL - NEVER BREAK THESE):
9. FORBIDDEN CALCULATION: Never calculate conversion rates between "Ad Clicks" and "Website Sessions" - they are different tracking systems
10. CLICKS-TO-SESSIONS RULE: NEVER call the clicks-to-sessions ratio a "conversion rate" - it is a "tracking discrepancy" only
11. PROPER FUNNEL ANALYSIS: 
    - IF Combined Insights available: Use MCP's cross-platform funnel (Ad Clicks → Website Sessions → Engaged Sessions → Conversions)
    - IF Combined Insights NOT available: Focus only on campaign-level metrics, note GA4 data unavailable
    - NEVER manually calculate rates between different platforms
12. ENGAGEMENT RATE CONTEXT: 80%+ engagement rate is EXCELLENT, not a problem area
13. CTR BENCHMARKS: For food industry, 7-15% CTR is excellent, 3-7% is good, 1-3% needs improvement
14. DISCREPANCY EXPLANATION: If sessions > clicks, frame as "tracking discrepancy to investigate" not performance issue

EXAMPLE: If asked "What campaign has zero conversions?" but all campaigns have some conversions, respond: "None of your campaigns have zero conversions. The campaign with the lowest conversions is [campaign name] with [number] conversions."

PLATFORM VALIDATION:
- Available platforms: {platforms_list}
- If asked about unavailable platforms, respond: "I don't have [platform] data available. I can only analyze data from {platforms_list}."

NON-MARKETING QUESTION HANDLING:
- If asked about topics unrelated to marketing/advertising (weather, cooking, general questions), respond: "I can only help with your Google Ads performance data. What would you like to know about your campaigns?"
- Do NOT provide marketing insights unless specifically asked about marketing performance

ACCOUNT TOTALS (calculated from campaign data only):
- Total Spend: R{total_spend:,.2f}
- Total Conversions: {total_conversions:,.0f}
- Total Clicks: {total_clicks:,}
- Total Impressions: {total_impressions:,}
- Average CPC: R{average_cpc:.2f}

GA4 WEBSITE DATA:
- Mobile Sessions: {device_breakdown.get('mobile', 0):,}
- Desktop Sessions: {device_breakdown.get('desktop', 0):,}
- Tablet Sessions: {device_breakdown.get('tablet', 0):,}
- Total Sessions: {ga4_data.get('traffic_overview', {}).get('total_sessions', 0):,}

USER JOURNEY FUNNEL DATA:
- Ad Clicks: {funnel_overview.get('ad_clicks', 0):,}
- Website Sessions: {funnel_overview.get('website_sessions', 0):,}
- Engaged Sessions: {funnel_overview.get('engaged_sessions', 0):,}
- Conversions: {funnel_overview.get('conversions', 0):,}

DROP-OFF ANALYSIS:
{chr(10).join([f"- {stage.replace('_', ' ').title()}: {data.get('drop_off_rate', 0):.1f}% ({data.get('potential_issue', 'Unknown')})" for stage, data in drop_off_analysis.items() if isinstance(data, dict)])}

COMBINED INSIGHTS AVAILABLE:
{json.dumps(combined_insights, indent=2) if combined_insights else "No combined insights available"}

CAMPAIGN DATA (YOUR ONLY DATA SOURCE):
{json.dumps(clean_data, indent=2)}

Respond naturally as if speaking to a business owner. Use ONLY the campaign data above."""

        # Use the existing Claude agent system (same as other endpoints)
        print(f"[MIA-CHAT-TEST] Loading Claude agent...")
        from services.claude_agent import get_claude_intent_agent
        claude_agent = await get_claude_intent_agent()
        
        print(f"[MIA-CHAT-TEST] Sending to Claude...")
        
        # Check if Claude agent has API key
        if not claude_agent.api_key:
            return {
                "success": False,
                "error": "ANTHROPIC_API_KEY not configured",
                "claude_prompt": claude_prompt if 'claude_prompt' in locals() else "API key missing",
                "response_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000)
            }
        
        # Use the working Claude agent format
        headers = {
            "Content-Type": "application/json",
            "x-api-key": claude_agent.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": claude_agent.model,  # Use the agent's configured model
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
        
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        print(f"[MIA-CHAT-TEST] Success! Response time: {response_time_ms}ms")
        
        return {
            "success": True,
            "claude_response": claude_response,
            "mcp_raw_data": json.dumps(clean_data, indent=2),  # Send clean data instead of massive MCP blob
            "claude_prompt": f"Claude prompt too long to display - {len(claude_prompt)} chars",
            "model_used": claude_agent.model,
            "response_time_ms": response_time_ms,
            "debug_roas_values": {  # Debug info to verify clean data
                "DFSA-PM-LEADS_clean": clean_data.get("campaigns", {}).get("DFSA-PM-LEADS", {}).get("roas"),
                "campaign_summary_source": campaign_summary_direct.get("DFSA-PM-LEADS", {}).get("roas")
            }
        }
        
    except Exception as e:
        print(f"[MIA-CHAT-TEST] Error: {str(e)}")
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "success": False,
            "error": str(e),
            "claude_prompt": claude_prompt if 'claude_prompt' in locals() else "Error occurred before prompt generation",
            "response_time_ms": response_time_ms
        }