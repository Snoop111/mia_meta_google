"""
Creative Analysis Endpoint - Asset-Only Analysis System

NEW for Creative-Only Pivot:
- Completely separate from existing Growth/Optimise/Protect system
- Focuses ONLY on 9 Google Ads asset types (no campaign performance)
- Real-time MCP queries only (zero hardcoded data)
- Handles 12 preset questions across Grow/Optimise/Protect categories
- NO mixing with campaign data or ROAS calculations
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
from database import get_db
from models.user_profile import AccountMapping

router = APIRouter()

class CreativeAnalysisRequest(BaseModel):
    question: str  # One of the 12 preset questions
    category: str  # "grow", "optimise", or "protect"
    session_id: Optional[str] = "default"
    start_date: str = "2025-08-03"  # Default: Aug 3 - Sep 2 for grow/optimize, Aug 3-9 for protect
    end_date: str = "2025-09-02"    # Default: Calculated based on category

def get_account_context(session_id: str, db: Session) -> Dict[str, Any]:
    """Get account context from session - SIMPLIFIED like temp_github_working"""
    try:
        # Simple direct session lookup from AuthSession table
        from models.user_profile import AuthSession
        session = db.query(AuthSession).filter(
            AuthSession.session_id == session_id,
            AuthSession.authenticated == True
        ).first()

        if session and session.selected_account_id:
            # Direct account mapping lookup
            account = db.query(AccountMapping).filter(
                AccountMapping.account_id == session.selected_account_id,
                AccountMapping.is_active == True
            ).first()

            if account:
                print(f"[CREATIVE-ACCOUNT-CONTEXT] Using account: {account.account_name}")
                return {
                    "user_id": session.google_user_id,
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "google_ads_id": account.google_ads_id,
                    "ga4_property_id": account.ga4_property_id,
                    "business_type": account.business_type,
                    "focus_account": account.account_id
                }

        # Simple fallback to DFSA (like working version)
        print(f"[CREATIVE-ACCOUNT-CONTEXT] No valid session/account, using DFSA fallback")
        return {
            "user_id": os.getenv("DEV_USER_ID", "106540664695114193744"),
            "account_id": "dfsa",
            "account_name": "DFSA - Goodness to Go",
            "google_ads_id": os.getenv("DEV_DFSA_GOOGLE_ADS_ID", "7574136388"),
            "ga4_property_id": os.getenv("DEV_DFSA_GA4_PROPERTY_ID", "458016659"),
            "business_type": "food",
            "focus_account": "dfsa",
        }
    except Exception as e:
        print(f"[CREATIVE-ACCOUNT-CONTEXT] Error: {e}, using DFSA fallback")
        return {
            "user_id": os.getenv("DEV_USER_ID", "106540664695114193744"),
            "account_id": "dfsa",
            "account_name": "DFSA - Goodness to Go",
            "google_ads_id": os.getenv("DEV_DFSA_GOOGLE_ADS_ID", "7574136388"),
            "ga4_property_id": os.getenv("DEV_DFSA_GA4_PROPERTY_ID", "458016659"),
            "business_type": "food",
            "focus_account": "dfsa",
        }

# 12 Preset Creative Questions (from docs/Mia creative pivot.txt)
PRESET_QUESTIONS = {
    "grow": [
        "Which creative format is driving the most engagement?",
        "Which captions or headlines resonate best with my audience?", 
        "Which visual styles or themes perform best?",
        "Which messaging angle appeals most to our audience?"
    ],
    "optimise": [
        "Which creative gives me the most clicks for the lowest spend?",
        "How should I optimise creative to increase engagement?",
        "Which headlines or CTAs perform best?", 
        "Which advert delivered the highest click-through rate (CTR)?"
    ],
    "protect": [
        "Is creative fatigue affecting my ads?",
        "Which creative assets are showing declining performance trends?",
        "Which ads are starting to lose engagement over time?",
        "Are my audiences seeing the same creative too often?"
    ]
}

@router.post("/api/creative-analysis")
async def creative_analysis(request: CreativeAnalysisRequest, db: Session = Depends(get_db)):
    """
    CREATIVE-ONLY ANALYSIS ENDPOINT
    
    Completely separate from campaign analytics - focuses only on:
    - 9 Google Ads asset types (Headlines, Descriptions, Images, etc.)
    - Creative performance metrics (clicks, interaction rates, costs)
    - Asset-specific optimization recommendations
    - NO campaign ROAS, budget, or performance data mixing
    """
    start_time = asyncio.get_event_loop().time()
    
    # Get dynamic account context
    account_context = get_account_context(request.session_id, db)
    
    print(f"[CREATIVE-ANALYSIS] Question: {request.question}")
    print(f"[CREATIVE-ANALYSIS] Category: {request.category}")
    print(f"[CREATIVE-ANALYSIS] Using dynamic account: {account_context['account_name']} (Google Ads {account_context['google_ads_id']}, GA4 {account_context['ga4_property_id']})")
    
    # Validate question is in preset list
    valid_questions = PRESET_QUESTIONS.get(request.category, [])
    if request.question not in valid_questions:
        return {
            "success": False,
            "error": f"Invalid question for {request.category} category",
            "valid_questions": valid_questions
        }
    
    try:
        # Get the ADK marketing agent (REUSE pattern from chat_endpoint.py)
        agent = await get_adk_marketing_agent()
        
        # Build MCP request with dynamic account context
        user_context = {
            "user_id": account_context["user_id"],
            "focus_account": account_context["focus_account"],
            "start_date": request.start_date,
            "end_date": request.end_date
        }
        
        print(f"[CREATIVE-ANALYSIS] Calling MCP with context: {user_context}")
        
        # CONDITIONAL QUERY STRUCTURE: Time-series for PROTECT, aggregated for GROW/OPTIMIZE
        needs_time_series = request.category == 'protect'
        date_select = "segments.date," if needs_time_series else ""
        date_order = "segments.date, " if needs_time_series else ""
        
        # PROTECT questions use time-series analysis - respect frontend date selection
        # Frontend should send proper 7-day range for PROTECT category
        # No backend override needed - frontend calculates correct ranges
        
        # Check if this is a problematic question that needs no daily segmentation (API limit fix)
        problematic_questions = [
            # Only specific questions that have confirmed API limit issues
        ]
        use_aggregated_query = request.question in problematic_questions
        
        # Override time-series for problematic questions (API limit fix)
        if use_aggregated_query:
            needs_time_series = False
            date_select = ""
            date_order = ""
            print(f"[API-LIMIT-FIX] Using 30-day aggregated queries (no daily segments) for: {request.question}")
        
        print(f"[QUERY-TYPE] Category: {request.category}, Time-series needed: {needs_time_series}")
        
        # QUERY 1: ad_group_ad_asset_view for headlines/descriptions (GAQL-compatible)
        # All queries use the same structure - the difference is only time-series vs aggregated
        if use_aggregated_query:
            responsive_assets_query = f"""
            SELECT 
                ad_group_ad_asset_view.field_type,
                asset.type,
                asset.text_asset.text,
                ad_group_ad_asset_view.performance_label,
                SUM(metrics.impressions) AS total_impressions,
                SUM(metrics.clicks) AS total_clicks,
                SUM(metrics.conversions) AS total_conversions,
                SUM(metrics.cost_micros) AS total_cost_micros,
                AVG(metrics.ctr) AS avg_ctr,
                AVG(metrics.average_cpc) AS avg_cpc
            FROM ad_group_ad_asset_view 
            WHERE ad_group_ad_asset_view.field_type IN ('HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE')
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            GROUP BY
                ad_group_ad_asset_view.field_type,
                asset.type,
                asset.text_asset.text,
                ad_group_ad_asset_view.performance_label
            ORDER BY total_impressions DESC
            """
        else:
            responsive_assets_query = f"""
            SELECT 
                {date_select}
                ad_group_ad_asset_view.field_type,
                asset.type,
                asset.text_asset.text,
                ad_group_ad_asset_view.performance_label,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group_ad_asset_view 
            WHERE ad_group_ad_asset_view.field_type IN ('HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE')
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            ORDER BY {date_order}ad_group_ad_asset_view.field_type
            """
        
        # QUERY 2: campaign_asset for callouts/sitelinks (conditional aggregation)
        if use_aggregated_query:
            extension_assets_query = f"""
            SELECT 
                asset.type,
                asset.callout_asset.callout_text,
                asset.sitelink_asset.link_text,
                asset.sitelink_asset.description1,
                SUM(metrics.impressions) AS total_impressions,
                SUM(metrics.clicks) AS total_clicks,
                SUM(metrics.conversions) AS total_conversions,
                SUM(metrics.cost_micros) AS total_cost_micros,
                AVG(metrics.ctr) AS avg_ctr,
                AVG(metrics.average_cpc) AS avg_cpc
            FROM campaign_asset 
            WHERE asset.type IN ('CALLOUT', 'SITELINK') 
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            GROUP BY
                asset.type,
                asset.callout_asset.callout_text,
                asset.sitelink_asset.link_text,
                asset.sitelink_asset.description1
            ORDER BY total_impressions DESC
            """
        else:
            extension_assets_query = f"""
            SELECT 
                {date_select}
                asset.type,
                asset.callout_asset.callout_text,
                asset.sitelink_asset.link_text,
                asset.sitelink_asset.description1,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign_asset 
            WHERE asset.type IN ('CALLOUT', 'SITELINK') 
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            ORDER BY {date_order}asset.type
            """
        
        # QUERY 3: asset_group_asset for Performance Max campaigns (conditional aggregation)
        if use_aggregated_query:
            performance_max_query = f"""
            SELECT 
                asset_group_asset.field_type,
                asset.type,
                asset.text_asset.text,
                SUM(metrics.impressions) AS total_impressions,
                SUM(metrics.clicks) AS total_clicks,
                SUM(metrics.conversions) AS total_conversions,
                SUM(metrics.cost_micros) AS total_cost_micros,
                AVG(metrics.ctr) AS avg_ctr,
                AVG(metrics.average_cpc) AS avg_cpc
            FROM asset_group_asset 
            WHERE asset_group_asset.field_type IN ('HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE')
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            GROUP BY
                asset_group_asset.field_type,
                asset.type,
                asset.text_asset.text
            ORDER BY total_impressions DESC
            """
        else:
            performance_max_query = f"""
            SELECT 
                {date_select}
                asset_group_asset.field_type,
                asset.type,
                asset.text_asset.text,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.ctr,
                metrics.average_cpc
            FROM asset_group_asset 
            WHERE asset_group_asset.field_type IN ('HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE')
            AND segments.date BETWEEN '{request.start_date}' AND '{request.end_date}'
            ORDER BY {date_order}asset_group_asset.field_type
            """
        
        # All questions now use the same TRIPLE-query approach above
        # Question-specific filtering happens in Claude prompt, not in GAQL query
        
        # PARALLEL MCP CALLS - Execute all three queries simultaneously for complete asset coverage
        print(f"[TRIPLE-TABLE-MCP] Starting parallel queries for complete asset coverage")
        print(f"[TRIPLE-TABLE-MCP] Query 1: ad_group_ad_asset_view (Traditional Responsive Ads)")
        print(f"[TRIPLE-TABLE-MCP] Query 2: campaign_asset (Extensions: CALLOUT, SITELINK, IMAGE)")
        print(f"[TRIPLE-TABLE-MCP] Query 3: asset_group_asset (Performance Max Assets)")
        
        # Prepare all three MCP call arguments
        responsive_mcp_args = {
            "user_id": account_context["user_id"],
            "customer_id": account_context["google_ads_id"],
            "query_type": "",
            "start_date": request.start_date,
            "end_date": request.end_date,
            "dimensions": None,
            "metrics": None,
            "custom_query": responsive_assets_query
        }

        extension_mcp_args = {
            "user_id": account_context["user_id"],
            "customer_id": account_context["google_ads_id"],
            "query_type": "",
            "start_date": request.start_date,
            "end_date": request.end_date,
            "dimensions": None,
            "metrics": None,
            "custom_query": extension_assets_query
        }

        performance_max_mcp_args = {
            "user_id": account_context["user_id"],
            "customer_id": account_context["google_ads_id"],
            "query_type": "",
            "start_date": request.start_date,
            "end_date": request.end_date,
            "dimensions": None,
            "metrics": None,
            "custom_query": performance_max_query
        }
        
        # Execute all three queries in parallel for complete asset coverage
        responsive_result, extension_result, performance_max_result = await asyncio.gather(
            agent.mcp_client.call_tool("query_google_ads_data", responsive_mcp_args),
            agent.mcp_client.call_tool("query_google_ads_data", extension_mcp_args),
            agent.mcp_client.call_tool("query_google_ads_data", performance_max_mcp_args),
            return_exceptions=True
        )
        
        print(f"[TRIPLE-TABLE-MCP] All parallel queries completed")
        
        # PROCESS TRIPLE MCP RESULTS
        def extract_asset_data(mcp_result, query_name):
            if isinstance(mcp_result, Exception):
                print(f"[TRIPLE-MCP] {query_name} failed: {str(mcp_result)}")
                return []
            
            if isinstance(mcp_result, dict):
                if 'data' in mcp_result:
                    data = mcp_result['data']
                elif 'result' in mcp_result and isinstance(mcp_result['result'], dict) and 'data' in mcp_result['result']:
                    data = mcp_result['result']['data']
                else:
                    print(f"[TRIPLE-MCP] {query_name}: No data found in result")
                    return []
                
                asset_count = len(data) if isinstance(data, list) else 0
                print(f"[TRIPLE-MCP] {query_name}: Got {asset_count} assets")
                return data if isinstance(data, list) else []
            else:
                print(f"[TRIPLE-MCP] {query_name}: Invalid result structure")
                return []
        
        # Extract data from all three queries
        responsive_assets = extract_asset_data(responsive_result, "Responsive Assets (Headlines/Descriptions)")
        extension_assets = extract_asset_data(extension_result, "Extension Assets (Callouts/Sitelinks)")
        performance_max_assets = extract_asset_data(performance_max_result, "Performance Max Assets (Asset Groups)")
        
        # Combine all assets from all three sources
        asset_data = responsive_assets + extension_assets + performance_max_assets
        total_assets = len(asset_data)
        
        print(f"[TRIPLE-MCP] COMBINED: {len(responsive_assets)} responsive + {len(extension_assets)} extension + {len(performance_max_assets)} performance_max = {total_assets} total")
        
        if total_assets == 0:
            return {
                "success": False,
                "error": "No asset data returned from any query",
                "creative_prompt": "No prompt - All three MCP queries returned empty",
                "debug_responsive": str(responsive_result)[:200],
                "debug_extension": str(extension_result)[:200],
                "debug_performance_max": str(performance_max_result)[:200]
            }
            
        # NEW: Process asset-specific data for creative analysis
        creative_data = {
            "question_category": request.category,
            "preset_question": request.question,
            "asset_count": len(asset_data) if isinstance(asset_data, list) else 0,
            "raw_asset_data": asset_data if isinstance(asset_data, list) and len(asset_data) < 50 else "Too many assets to display"
        }
        
        # Extract asset insights for Claude - IMPROVED MULTI-FORMAT PARSING
        if isinstance(asset_data, list) and len(asset_data) > 0:
            # Categorize assets by ALL 9 types (including separate image categories)
            asset_formats = {
                'HEADLINE': [],
                'DESCRIPTION': [],
                'LONG_HEADLINE': [],
                'TEXT': [],
                'CALLOUT': [],
                'SITELINK': [], 
                'PRICE': [],
                'PROMOTION': [],
                'IMAGE_RESPONSIVE': [],     # Images from responsive ads
                'IMAGE_EXTENSION': [],      # Images from extensions  
                'IMAGE_PERFORMANCE_MAX': [] # Images from Performance Max campaigns
            }
            
            for asset in asset_data:
                # Time-series data for PROTECT questions
                date = asset.get('segments_date', '')
                # Handle both aggregated and non-aggregated field names
                clicks = asset.get('total_clicks', asset.get('metrics_clicks', 0))
                impressions = asset.get('total_impressions', asset.get('metrics_impressions', 0))
                interaction_rate = asset.get('metrics_interaction_rate', 0)  # Not aggregated
                cost_micros = asset.get('total_cost_micros', asset.get('metrics_cost_micros', 0))
                conversions = asset.get('total_conversions', asset.get('metrics_conversions', 0))
                
                # DYNAMIC ASSET TYPE DETECTION - Detect type from content fields (no hardcoding)
                asset_type = "UNKNOWN"
                content = ""
                
                # Google Ads Asset Type Mapping (numeric to text)
                ASSET_TYPE_MAP = {
                    1: 'TEXT',           # TEXT asset
                    2: 'IMAGE',          # IMAGE asset
                    3: 'VIDEO',          # VIDEO asset  
                    4: 'MEDIA_BUNDLE',   # HTML5 asset
                    5: 'TEXT',           # TEXT asset (alternative code)
                    9: 'CALLOUT',        # CALLOUT asset
                    10: 'LEAD_FORM',     # LEAD_FORM asset
                    11: 'SITELINK',      # SITELINK asset (corrected from BOOK_ON_GOOGLE)
                    12: 'PROMOTION',     # PROMOTION asset
                    13: 'CALLOUT',       # CALLOUT asset (alternative code)
                    14: 'STRUCTURED_SNIPPET', # STRUCTURED_SNIPPET asset
                    15: 'SITELINK',      # SITELINK asset (alternative code)
                    17: 'MOBILE_APP',    # MOBILE_APP asset
                    18: 'HOTEL_CALLOUT', # HOTEL_CALLOUT asset
                    19: 'CALL',          # CALL asset
                    20: 'PRICE'          # PRICE asset
                }
                
                # Google Ads Field Type Mapping (numeric to text) for asset_group_asset_field_type
                FIELD_TYPE_MAP = {
                    1: 'HEADLINE',           # HEADLINE field
                    2: 'DESCRIPTION',        # DESCRIPTION field
                    3: 'LONG_HEADLINE',      # LONG_HEADLINE field
                    4: 'MARKETING_IMAGE',    # MARKETING_IMAGE field
                    5: 'YOUTUBE_VIDEO',      # YOUTUBE_VIDEO field
                    6: 'VIDEO',              # VIDEO field
                    7: 'BUSINESS_NAME',      # BUSINESS_NAME field
                    8: 'LOGO',               # LOGO field
                    9: 'SQUARE_MARKETING_IMAGE', # SQUARE_MARKETING_IMAGE field
                    10: 'PORTRAIT_MARKETING_IMAGE', # PORTRAIT_MARKETING_IMAGE field
                    11: 'CALL_TO_ACTION_SELECTION', # CALL_TO_ACTION_SELECTION field
                    12: 'AD_IMAGE',          # AD_IMAGE field
                    13: 'LANDSCAPE_LOGO',    # LANDSCAPE_LOGO field
                    17: 'HEADLINE',          # HEADLINE field (alternative code)
                    18: 'DESCRIPTION',       # DESCRIPTION field (alternative code)
                }
                
                # CORRECTED ASSET TYPE DETECTION - Using field_type for responsive assets, asset.type for extensions
                
                # Check for responsive assets (from ad_group_ad_asset_view)
                # Try multiple possible field names for field_type
                field_type = (asset.get('ad_group_ad_asset_view_field_type', '') or 
                             asset.get('field_type', '') or 
                             asset.get('ad_group_ad_asset_view.field_type', ''))
                if field_type:
                    # Use field_type to determine asset category
                    if field_type == 'HEADLINE':
                        asset_type = 'HEADLINE'
                    elif field_type == 'DESCRIPTION':
                        asset_type = 'DESCRIPTION'
                    elif field_type == 'LONG_HEADLINE':
                        asset_type = 'LONG_HEADLINE'
                    elif field_type == 'MARKETING_IMAGE':
                        asset_type = 'IMAGE_RESPONSIVE'
                    else:
                        asset_type = field_type  # Use field_type directly
                    
                    # Get content based on type
                    if field_type in ['HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE']:
                        content = asset.get('asset_text_asset_text', '')
                    elif field_type == 'MARKETING_IMAGE':
                        image_url = asset.get('asset_image_asset_full_size_url', '')
                        width = asset.get('asset_image_asset_full_size_width_pixels', 0)
                        height = asset.get('asset_image_asset_full_size_height_pixels', 0)
                        content = f"{width}×{height}" if width and height else image_url
                    else:
                        content = asset.get('asset_text_asset_text', '') or str(asset.get('asset_type', ''))
                
                # Check for Performance Max assets (from asset_group_asset)
                elif asset.get('asset_group_asset_field_type'):
                    # Performance Max uses numeric field_type from asset_group_asset table
                    performance_field_type_num = asset.get('asset_group_asset_field_type', 0)
                    performance_field_type = FIELD_TYPE_MAP.get(performance_field_type_num, f'UNKNOWN_FIELD_{performance_field_type_num}')
                    
                    if performance_field_type == 'HEADLINE':
                        asset_type = 'HEADLINE'
                        content = asset.get('asset_text_asset_text', '')
                    elif performance_field_type == 'DESCRIPTION':
                        asset_type = 'DESCRIPTION'  
                        content = asset.get('asset_text_asset_text', '')
                    elif performance_field_type == 'LONG_HEADLINE':
                        asset_type = 'LONG_HEADLINE'
                        content = asset.get('asset_text_asset_text', '')
                    elif performance_field_type == 'MARKETING_IMAGE':
                        asset_type = 'IMAGE_PERFORMANCE_MAX'
                        image_url = asset.get('asset_image_asset_full_size_url', '')
                        width = asset.get('asset_image_asset_full_size_width_pixels', 0)
                        height = asset.get('asset_image_asset_full_size_height_pixels', 0)
                        content = f"{width}×{height}" if width and height else image_url
                    else:
                        asset_type = performance_field_type
                        content = asset.get('asset_text_asset_text', '') or str(asset.get('asset_type', ''))
                
                # Check for extension assets (from campaign_asset)
                elif asset.get('asset_callout_asset_callout_text'):
                    asset_type = 'CALLOUT'
                    content = asset.get('asset_callout_asset_callout_text', '')
                elif asset.get('asset_sitelink_asset_link_text'):
                    asset_type = 'SITELINK'
                    link_text = asset.get('asset_sitelink_asset_link_text', '')
                    # Use only the main link text, not concatenated with description
                    content = link_text
                elif asset.get('asset_image_asset_full_size_url') and not field_type:
                    asset_type = 'IMAGE_EXTENSION'
                    image_url = asset.get('asset_image_asset_full_size_url', '')
                    width = asset.get('asset_image_asset_full_size_width_pixels', 0)
                    height = asset.get('asset_image_asset_full_size_height_pixels', 0)
                    content = f"{width}×{height}" if width and height else image_url
                
                # Fallback: Handle numeric asset types (Performance Max without field_type)
                elif asset.get('asset_type'):
                    asset_type_num = asset.get('asset_type', 0)
                    asset_type_text = ASSET_TYPE_MAP.get(asset_type_num, f'UNKNOWN_{asset_type_num}')
                    
                    # Map to our categories based on numeric type and content
                    if asset_type_num == 5:  # TEXT asset - check if it's headline/description
                        text_content = asset.get('asset_text_asset_text', '')
                        if text_content:
                            # For Performance Max TEXT assets, assume they're headlines if we have text
                            asset_type = 'HEADLINE'  # Default Performance Max text to headline
                            content = text_content
                        else:
                            asset_type = 'TEXT'
                            content = text_content
                    elif asset_type_num == 2:  # IMAGE asset
                        asset_type = 'IMAGE_PERFORMANCE_MAX'
                        image_url = asset.get('asset_image_asset_full_size_url', '')
                        width = asset.get('asset_image_asset_full_size_width_pixels', 0)
                        height = asset.get('asset_image_asset_full_size_height_pixels', 0)
                        content = f"{width}×{height}" if width and height else image_url
                    else:
                        asset_type = asset_type_text
                        content = asset.get('asset_text_asset_text', '') or str(asset_type_num)
                
                # Get the API type number for debugging only (not for logic)
                asset_type_num = asset.get('asset_type', 0)
                
                # Get performance label and source info
                performance_label = asset.get('ad_group_ad_asset_view_performance_label', '') 
                if field_type:
                    source_table = 'responsive'
                elif asset.get('asset_group_asset_field_type'):
                    source_table = 'performance_max'
                else:
                    source_table = 'extension'
                
                print(f"[TRIPLE-MCP-PARSING] {asset_type} ({source_table}): '{content[:30]}...', clicks={clicks}, impressions={impressions}, conversions={conversions}, label={performance_label}")
                print(f"[DEBUG-FIELDS] Available keys: {list(asset.keys())[:10]}")  # Show first 10 field names
                
                # Add to appropriate format category (only if we detected a valid type)
                if asset_type in asset_formats:
                    asset_info = {
                        'date': date,  # Time-series data for PROTECT questions
                        'type': asset_type,
                        'content': content,
                        'clicks': clicks,
                        'impressions': impressions,
                        'conversions': conversions,
                        'interaction_rate': interaction_rate * 100,
                        'avg_cost': cost_micros / 1000000 if cost_micros > 0 else 0,
                        'ctr': round((clicks / impressions * 100), 2) if impressions > 0 else 0,
                        'conversion_rate': round((conversions / clicks), 4) if clicks > 0 else 0,
                        'performance_label': performance_label,  # Backward compatibility
                        'source_table': source_table,
                        'field_type': field_type if field_type else None
                    }
                    
                    # Add image-specific metadata for both image types
                    if asset_type in ['IMAGE_RESPONSIVE', 'IMAGE_EXTENSION', 'IMAGE_PERFORMANCE_MAX']:
                        asset_info.update({
                            'image_url': asset.get('asset_image_asset_full_size_url', ''),
                            'width': asset.get('asset_image_asset_full_size_width_pixels', 0),
                            'height': asset.get('asset_image_asset_full_size_height_pixels', 0),
                            'aspect_ratio': round(asset.get('asset_image_asset_full_size_width_pixels', 0) / asset.get('asset_image_asset_full_size_height_pixels', 1), 2) if asset.get('asset_image_asset_full_size_height_pixels', 0) > 0 else 0,
                            'format_type': 'Square' if abs(asset.get('asset_image_asset_full_size_width_pixels', 0) - asset.get('asset_image_asset_full_size_height_pixels', 0)) <= 50 else ('Horizontal' if asset.get('asset_image_asset_full_size_width_pixels', 0) > asset.get('asset_image_asset_full_size_height_pixels', 0) else 'Vertical'),
                            'image_category': 'Responsive Ad Image' if asset_type == 'IMAGE_RESPONSIVE' else ('Performance Max Image' if asset_type == 'IMAGE_PERFORMANCE_MAX' else 'Extension Image')
                        })
                    
                    asset_formats[asset_type].append(asset_info)
                else:
                    print(f"[TRIPLE-TABLE-PARSING] UNKNOWN asset type detected: {asset_type}, skipping")
            
            # Store by format type for proper analysis
            creative_data['asset_formats'] = asset_formats
            creative_data['format_summary'] = {
                format_type: {
                    'count': len(assets),
                    'total_clicks': sum(asset['clicks'] for asset in assets),
                    'total_impressions': sum(asset['impressions'] for asset in assets),
                    'total_conversions': sum(asset['conversions'] for asset in assets),
                    'avg_ctr': sum(asset['ctr'] for asset in assets) / len(assets) if assets else 0,
                    'avg_conversion_rate': sum(asset['conversions'] for asset in assets) / sum(asset['clicks'] for asset in assets) if sum(asset['clicks'] for asset in assets) > 0 else 0,
                    'total_cost': sum(asset['avg_cost'] for asset in assets),
                    'avg_cost_per_click': sum(asset['avg_cost'] for asset in assets) / sum(asset['clicks'] for asset in assets) if sum(asset['clicks'] for asset in assets) > 0 else 0,
                    'clicks_per_dollar': sum(asset['clicks'] for asset in assets) / sum(asset['avg_cost'] for asset in assets) if sum(asset['avg_cost'] for asset in assets) > 0 else 0,
                    'cost_efficiency_score': (sum(asset['clicks'] for asset in assets) / sum(asset['avg_cost'] for asset in assets)) * 100 if sum(asset['avg_cost'] for asset in assets) > 0 else 0
                }
                for format_type, assets in asset_formats.items() if assets
            }
            
            # Legacy format for backwards compatibility - group by broad categories
            creative_data['text_assets'] = []
            creative_data['image_assets'] = []
            for format_type, assets in asset_formats.items():
                if format_type in ['HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE', 'TEXT', 'CALLOUT', 'SITELINK', 'PRICE', 'PROMOTION']:
                    creative_data['text_assets'].extend(assets)
                elif format_type in ['IMAGE_RESPONSIVE', 'IMAGE_EXTENSION']:
                    creative_data['image_assets'].extend(assets)
            
            creative_data['total_text_assets'] = len(creative_data['text_assets'])
            creative_data['total_image_assets'] = len(creative_data['image_assets'])
            creative_data['total_responsive_assets'] = len(responsive_assets)
            creative_data['total_extension_assets'] = len(extension_assets)
        else:
            creative_data['text_assets'] = []
            creative_data['image_assets'] = []
            creative_data['data_note'] = "No asset data returned - may be empty response issue"
        
        print(f"[TRIPLE-MCP] Asset data extracted successfully - {total_assets} total assets from all three tables")
        
        # QUESTION-SPECIFIC Claude prompts for optimized analysis
        if request.question == "Which creative format is driving the most engagement?":
            # GROW Q1: Focus on FORMAT comparison, not individual assets
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎨 CREATIVE FORMAT ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- Say "Image Extensions" NOT "IMAGE_EXTENSION" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 FORMAT ANALYSIS RULES:
1. Compare PERFORMANCE by specific ASSET FORMAT TYPES: Headlines, Descriptions, Long Headlines, Callouts, Sitelinks, Images (Responsive/Extension/Performance Max)
2. Focus on FORMAT-level metrics: total engagement, conversion rates, interaction patterns
3. NEVER mention campaign spend, ROAS, or budget data
4. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars
5. Provide FORMAT-specific optimization recommendations based on the actual business and industry context
6. Identify which creative ASSET FORMATS drive the most engagement for growth

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific top-performing individual assets by exact name from the data
- Include both format analysis AND specific asset examples with performance numbers
- Focus on assets with significant performance (>50 clicks or >2% CTR)
- Provide 2-3 specific actionable recommendations

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE CREATIVE ASSET DATA:

INDIVIDUAL ASSETS BY FORMAT:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

FORMAT SUMMARY:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about engagement drivers
2. **Specific Top Assets**: Show 3-4 highest-performing individual assets with exact names and performance
3. **Format Analysis**: Explain which formats (descriptions, callouts, etc.) work best overall
4. **Recommendations**: 2-3 specific actionable tactics

🚨 ABSOLUTE REQUIREMENT: SHOW SPECIFIC ASSET NAMES
- MANDATORY: Quote the exact "content" field values from the highest-performing assets
- INCLUDE PERFORMANCE: Show clicks, CTR, conversions for each specific asset mentioned
- FORBIDDEN: Only showing generic format summaries without specific asset examples
- REQUIRED: Every asset name must exist exactly in the provided JSON data
- SHOW REAL ASSETS: Use the actual top-performing asset content from the data provided

Focus on actionable insights using EXACT asset text. Keep concise while using authentic performance data.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points with exact quoted asset text."""
        elif request.question == "Which captions or headlines resonate best with my audience?":
            # GROW Q2: Focus on actual HEADLINE and DESCRIPTION text from responsive search ads
            # Check if we have headline/description data
            headline_data = creative_data.get('asset_formats', {}).get('HEADLINE', [])
            description_data = creative_data.get('asset_formats', {}).get('DESCRIPTION', [])
            long_headline_data = creative_data.get('asset_formats', {}).get('LONG_HEADLINE', [])
            
            if not headline_data and not description_data and not long_headline_data:
                # No headline/description data found - provide fallback analysis
                creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎯 HEADLINE & CAPTION ANALYSIS - DATA LIMITATION NOTICE

**Data Limitation:** Your Google Ads account for the selected date range (2025-08-26 to 2025-09-02) does not contain responsive search ad headlines or descriptions with performance data. This could be because:
- Your campaigns primarily use other ad formats (Performance Max, Display, etc.)
- Responsive search ads exist but had no performance in this date range  
- Headlines/descriptions are tracked in different campaign types

**Available Alternative Analysis:** I can analyze your extension messaging (callouts and sitelinks) to understand messaging themes that resonate with your audience, which can inform headline creation.

**Start your response with a bold summary paragraph** explaining the data limitation and offering alternative insights based on available messaging data.

**Extension Messaging Data:**
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}"""
            else:
                creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎯 HEADLINE & CAPTION TEXT ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 HEADLINE & CAPTION ANALYSIS RULES:
1. Analyze actual HEADLINE text and DESCRIPTION text from responsive search ads
2. Focus on the main ad copy that users see - headlines and descriptions are the primary messaging
3. NEVER mention campaign spend, ROAS, or budget data
4. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific top-performing headlines and captions by exact text from the data
- Include both format analysis AND specific headline/caption examples with performance
- Focus on assets with significant performance (>50 clicks or >2% CTR)
- Provide 2-3 specific actionable recommendations

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE HEADLINE & CAPTION DATA:

INDIVIDUAL HEADLINES & CAPTIONS:
{json.dumps({
    'HEADLINE': creative_data.get('asset_formats', {}).get('HEADLINE', []),
    'DESCRIPTION': creative_data.get('asset_formats', {}).get('DESCRIPTION', []),
    'LONG_HEADLINE': creative_data.get('asset_formats', {}).get('LONG_HEADLINE', [])
}, indent=2)}

TEXT PERFORMANCE SUMMARY:
{json.dumps({
    format_type: summary for format_type, summary in creative_data.get('format_summary', {}).items()
    if format_type in ['HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE']
}, indent=2)}

🎯 ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about headline/caption resonance
2. **Specific Top Headlines**: Show 3-4 highest-performing headline/caption texts with exact performance
3. **Resonance Analysis**: Explain which types of headlines/captions resonate best
4. **Recommendations**: 2-3 specific tactics for headline/caption optimization

🚨 ABSOLUTE REQUIREMENT: SHOW SPECIFIC HEADLINE TEXT
- MANDATORY: Quote the exact headline and description text from highest-performing assets
- INCLUDE PERFORMANCE: Show clicks, CTR, conversions for each specific headline/caption mentioned
- FORBIDDEN: Only showing generic format summaries without specific headline examples
- REQUIRED: Every headline/caption quoted must exist exactly in the provided JSON data
- SHOW REAL TEXT: Use the actual top-performing headline/caption content from the data

Focus on actionable insights for mobile scanning. Keep concise while using authentic performance data.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which visual styles or themes perform best?":
            # GROW Q3: Focus on IMAGE visual style and theme analysis
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎨 VISUAL STYLE & THEME PERFORMANCE ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- Say "Image Extensions" NOT "IMAGE_EXTENSION" (use normal text, not bold)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 DATA-DRIVEN CREATIVE ANALYSIS RULES:
1. DISCOVER creative themes from actual asset content and performance
2. Focus on messaging themes that appear in the actual data
3. NEVER mention campaign spend, ROAS, or budget data
4. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST discover and show specific themes from actual asset content in the data
- Include theme analysis WITH specific asset examples that represent each theme
- Focus on themes with significant performance (assets >50 clicks or >2% CTR)
- Provide 2-3 specific actionable recommendations for theme optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE CREATIVE ASSET DATA FOR THEME DISCOVERY:

ALL ASSET CONTENT BY FORMAT:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

FORMAT SUMMARY:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 THEME ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important theme insight discovered from actual asset content
2. **Theme Discovery**: Identify 2-3 creative themes from analyzing all asset content patterns
3. **Theme Examples**: Show specific assets that represent each high-performing theme
4. **Performance Analysis**: Explain which creative themes drive the best engagement
5. **Recommendations**: 2-3 specific tactics for leveraging winning themes

🚨 ABSOLUTE REQUIREMENT: SHOW THEME-SPECIFIC ASSETS
- MANDATORY: Discover themes by analyzing actual asset content across all formats
- SHOW EXAMPLES: Quote specific assets that represent each theme (headlines, descriptions, callouts, etc.)
- INCLUDE PERFORMANCE: Show performance data for theme-representative assets
- FORBIDDEN: Generic theme descriptions without specific asset examples from the data
- THEME DISCOVERY: Let the actual asset content reveal the themes, don't assume categories

Discover themes from actual content patterns and performance data. Keep concise and mobile-scannable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which messaging angle appeals most to our audience?":
            # GROW Q4: DATA-DRIVEN messaging analysis - discover themes from actual content
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎯 MESSAGING ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 DATA-DRIVEN ANALYSIS RULES:
1. DISCOVER messaging themes from actual asset content and performance
2. Focus on messaging approaches that perform best based on actual metrics
3. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars
4. NEVER mention campaign spend, ROAS, or budget data

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific messaging angles from actual callout and sitelink text in the data
- Include angle analysis WITH specific messaging examples that represent each angle
- Focus on messaging with significant performance (>50 clicks or >3% CTR)
- Provide 2-3 specific actionable recommendations for messaging optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE MESSAGING DATA FOR ANGLE DISCOVERY:

INDIVIDUAL CALLOUTS & SITELINKS:
{json.dumps({
    'CALLOUT': creative_data.get('asset_formats', {}).get('CALLOUT', []),
    'SITELINK': creative_data.get('asset_formats', {}).get('SITELINK', [])
}, indent=2)}

MESSAGING FORMAT SUMMARY:
{json.dumps({
    format_type: summary for format_type, summary in creative_data.get('format_summary', {}).items()
    if format_type in ['CALLOUT', 'SITELINK']
}, indent=2)}

🎯 MESSAGING ANGLE ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about which messaging angles appeal most
2. **Angle Discovery**: Identify 2-3 messaging angles from analyzing callout and sitelink content
3. **Angle Examples**: Show specific callouts/sitelinks that represent each high-performing angle
4. **Performance Analysis**: Explain which messaging approaches drive the best engagement
5. **Recommendations**: 2-3 specific tactics for leveraging winning messaging angles

🚨 ABSOLUTE REQUIREMENT: SHOW ANGLE-SPECIFIC MESSAGING
- MANDATORY: Discover messaging angles by analyzing actual callout and sitelink content
- SHOW EXAMPLES: Quote specific callouts and sitelinks that represent each messaging angle
- INCLUDE PERFORMANCE: Show performance data for angle-representative messaging
- FORBIDDEN: Generic angle descriptions without specific messaging examples from the data
- ANGLE DISCOVERY: Let the actual messaging content reveal the angles that work best

Discover messaging patterns from actual performance data. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which creative gives me the most clicks for the lowest spend?":
            # OPTIMIZE Q1: Focus on COST EFFICIENCY - clicks per spend optimization
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

💰 COST EFFICIENCY OPTIMIZATION REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- Say "Image Extensions" NOT "IMAGE_EXTENSION" (use normal text, not bold)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 COST EFFICIENCY ANALYSIS RULES:
1. Focus on CLICKS-TO-SPEND RATIO across all creative asset types
2. Identify which specific ASSETS generate most clicks for lowest spend
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific most cost-efficient assets by name from the data
- Include cost efficiency analysis WITH specific asset examples and cost metrics
- Focus on assets with best clicks-to-cost ratio (>50 clicks or strong efficiency)
- Provide 2-3 specific actionable recommendations for cost optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE COST EFFICIENCY DATA:

INDIVIDUAL ASSETS WITH COST METRICS:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

COST EFFICIENCY SUMMARY BY FORMAT:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 COST EFFICIENCY ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about cost-efficient assets
2. **Cost-Efficient Assets**: Show 3-4 specific assets with best clicks-to-cost ratios
3. **Cost Analysis**: Compare cost per click (avg_cost) vs clicks generated for top performers
4. **Efficiency Insights**: Explain which assets deliver maximum clicks for minimum spend
5. **Recommendations**: 2-3 specific tactics for improving cost efficiency

🚨 ABSOLUTE REQUIREMENT: SHOW COST-EFFICIENT ASSET NAMES
- MANDATORY: Quote exact asset names with the lowest cost per click from the data
- INCLUDE METRICS: Show clicks generated and cost per click in Rands for each asset
- COST FOCUS: Prioritize assets with high clicks and low avg_cost values
- FORBIDDEN: Only showing generic cost summaries without specific efficient asset examples
- EFFICIENCY CALCULATION: Use actual clicks and avg_cost data to identify best performers

Focus on cost efficiency in South African Rands. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "How should I optimise creative to increase engagement?":
            # OPTIMIZE Q2: Focus on ENGAGEMENT OPTIMIZATION - interaction rate and CTR improvement tactics
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

📈 ENGAGEMENT OPTIMIZATION REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- Say "Image Extensions" NOT "IMAGE_EXTENSION" (use normal text, not bold)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 ENGAGEMENT OPTIMIZATION RULES:
1. Focus on INTERACTION RATES and CTR optimization across all creative asset types
2. Identify engagement patterns and optimization opportunities by asset format
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. Provide SPECIFIC tactics to increase interaction rates and engagement

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific highest-engagement assets by name from the data
- Include engagement analysis WITH specific asset examples and engagement metrics
- Focus on assets with strong engagement (>3% CTR or high interaction rates)
- Provide 2-3 specific actionable recommendations for engagement optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE ENGAGEMENT DATA:

INDIVIDUAL ASSETS WITH ENGAGEMENT METRICS:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

ENGAGEMENT SUMMARY BY FORMAT:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 ENGAGEMENT OPTIMIZATION REQUIREMENTS:
1. **Key Finding**: Single most important insight about engagement drivers
2. **High-Engagement Assets**: Show 3-4 specific assets with highest CTR and interaction rates
3. **Engagement Analysis**: Compare CTR and conversion rates for top-performing assets
4. **Optimization Insights**: Explain what makes certain assets more engaging
5. **Recommendations**: 2-3 specific tactics to increase audience engagement

🚨 ABSOLUTE REQUIREMENT: SHOW HIGH-ENGAGEMENT ASSET NAMES
- MANDATORY: Quote exact asset names with the highest CTR and engagement from the data
- INCLUDE METRICS: Show CTR, clicks, conversions, and interaction rates for each asset
- ENGAGEMENT FOCUS: Prioritize assets with high CTR (>3%) and strong interaction rates
- FORBIDDEN: Only showing generic engagement summaries without specific asset examples
- PERFORMANCE COMPARISON: Use actual CTR and interaction_rate data to identify top performers

Focus on maximizing audience engagement. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which headlines or CTAs perform best?":
            # OPTIMIZE Q3: Focus on HEADLINE & CTA EFFECTIVENESS - text content analysis for best performing copy
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

📝 HEADLINE & CTA EFFECTIVENESS ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 HEADLINE & CTA ANALYSIS RULES:
1. Focus on TEXT CONTENT effectiveness across callouts, sitelinks, text assets, and descriptions
2. Analyze which specific HEADLINE COPY and CTA LANGUAGE drives best performance
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. Compare text effectiveness by CTR, conversion rates, and interaction performance

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific best-performing headlines and CTAs by exact text from the data
- Include text effectiveness analysis WITH specific headline/CTA examples and performance
- Focus on text with significant performance (>50 clicks or >3% CTR)
- Provide 2-3 specific actionable recommendations for copy optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE TEXT ASSET DATA:

INDIVIDUAL TEXT ASSETS (Headlines, Descriptions, CTAs):
{json.dumps({
    'HEADLINE': creative_data.get('asset_formats', {}).get('HEADLINE', []),
    'DESCRIPTION': creative_data.get('asset_formats', {}).get('DESCRIPTION', []),
    'LONG_HEADLINE': creative_data.get('asset_formats', {}).get('LONG_HEADLINE', []),
    'CALLOUT': creative_data.get('asset_formats', {}).get('CALLOUT', []),
    'SITELINK': creative_data.get('asset_formats', {}).get('SITELINK', []),
    'TEXT': creative_data.get('asset_formats', {}).get('TEXT', [])
}, indent=2)}

TEXT PERFORMANCE SUMMARY:
{json.dumps({
    format_type: summary for format_type, summary in creative_data.get('format_summary', {}).items()
    if format_type in ['HEADLINE', 'DESCRIPTION', 'LONG_HEADLINE', 'CALLOUT', 'SITELINK', 'TEXT']
}, indent=2)}

🎯 HEADLINE & CTA EFFECTIVENESS REQUIREMENTS:
1. **Key Finding**: Single most important insight about headline/CTA effectiveness
2. **Top Text Assets**: Show 3-4 specific best-performing headlines and CTAs with exact text
3. **Text Analysis**: Compare performance of different headline and CTA approaches
4. **Copy Insights**: Explain what makes certain headlines and CTAs more effective
5. **Recommendations**: 2-3 specific tactics for copy optimization

🚨 ABSOLUTE REQUIREMENT: SHOW SPECIFIC HEADLINE/CTA TEXT
- MANDATORY: Quote exact headline and CTA text from the highest-performing text assets
- INCLUDE METRICS: Show clicks, CTR, conversions for each specific headline/CTA mentioned
- TEXT FOCUS: Prioritize text assets with strong performance (>50 clicks or >3% CTR)
- FORBIDDEN: Only showing generic text summaries without specific headline/CTA examples
- COPY ANALYSIS: Use actual text content and performance data to identify winning copy

Focus on text content effectiveness. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each.

CONTEXT: This is an OPTIMIZATION question focused on text copy effectiveness. Analyze which specific headlines and call-to-action language perform best, and provide copy optimization recommendations based on authentic performance data.

Please analyze which headlines or CTAs perform best and provide specific copy optimization recommendations."""
        elif request.question == "Which advert delivered the highest click-through rate (CTR)?":
            # OPTIMIZE Q4: Focus on CTR RANKING & OPTIMIZATION - highest performing assets by click-through rate
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

📈 CTR OPTIMIZATION ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- Say "Image Extensions" NOT "IMAGE_EXTENSION" (use normal text, not bold)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 CTR OPTIMIZATION RULES:
1. Focus on CLICK-THROUGH RATE rankings across all creative asset types
2. Identify the HIGHEST CTR performers and analyze what makes them effective
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. Rank assets by CTR performance and provide specific improvement tactics
5. Explain WHY certain assets achieve higher click-through rates
6. Provide actionable strategies to improve underperforming asset CTRs
7. USE USER-FRIENDLY TERMINOLOGY: Refer to "Performance Max Images" not "IMAGE_PERFORMANCE_MAX", "Image Extensions" not "IMAGE_EXTENSION", "Ad Headlines" not "HEADLINE", "Ad Descriptions" not "DESCRIPTION", "Callout Extensions" not "CALLOUT", "Sitelink Extensions" not "SITELINK"

📊 ASSET CTR PERFORMANCE DATA:

MULTI-FORMAT CTR BREAKDOWN:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

CTR SUMMARY BY FORMAT:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific highest-CTR assets by name from the data
- Include CTR analysis WITH specific asset examples and click-through rates
- Focus on assets with strong CTR performance (>3% or exceptional click performance)
- Provide 2-3 specific actionable recommendations for CTR optimization

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

🎯 CTR OPTIMIZATION REQUIREMENTS:
1. **Key Finding**: Single most important insight about CTR performance
2. **Highest-CTR Assets**: Show 3-4 specific assets with the highest click-through rates
3. **CTR Analysis**: Compare click-through rates across different asset types and content
4. **CTR Drivers**: Explain what makes certain assets achieve higher click-through rates
5. **Recommendations**: 2-3 specific tactics for improving CTR performance

🚨 ABSOLUTE REQUIREMENT: SHOW SPECIFIC HIGH-CTR ASSET NAMES
- MANDATORY: Quote exact asset names with the highest CTR from the data
- INCLUDE METRICS: Show exact CTR percentages, clicks, and impressions for each asset
- CTR FOCUS: Prioritize assets with exceptional click-through rates (>3% or top performers)
- FORBIDDEN: Only showing generic CTR summaries without specific asset examples
- PERFORMANCE RANKING: Use actual CTR data to rank and identify top-performing assets

Focus on maximizing click-through rates. Keep concise and actionable.

CONTEXT: This is an OPTIMIZATION question focused on maximizing click-through rates. Analyze which creative assets deliver the highest CTR and provide specific recommendations for improving click-through rate performance.

Please analyze which advert delivered the highest CTR and provide specific CTR optimization recommendations.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Is creative fatigue affecting my ads?":
            # PROTECT Q1: Focus on FATIGUE DETECTION - time-series trend analysis for performance degradation
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🛡️ CREATIVE FATIGUE DETECTION REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 ANALYSIS RULES:
1. Focus on PERFORMANCE DECLINE TRENDS (early vs recent period)
2. Identify assets with >20% decline in CTR indicating fatigue
3. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars
4. Compare days 1-3 vs days 5-7 performance for decline analysis

📱 MOBILE-FIRST REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific fatigued assets by exact name with decline patterns
- Focus on assets with >10 impressions and >20% CTR decline
- Provide 2-3 actionable recommendations for creative refresh

🏢 ACCOUNT CONTEXT:
Business: {account_context['account_name']} | Period: {request.start_date} to {request.end_date}

📊 TIME-SERIES FATIGUE DATA:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

🎯 ANALYSIS REQUIREMENTS:
1. **Key Finding**: Main insight about fatigue patterns
2. **Fatigued Assets**: 3-4 specific assets with decline trends (early CTR → recent CTR)
3. **Recommendations**: 2-3 specific refresh tactics

🚨 ABSOLUTE REQUIREMENT: SHOW SPECIFIC DECLINE PATTERNS
- MANDATORY: Quote exact asset names showing fatigue with before/after performance data
- INCLUDE TRENDS: Show early period CTR vs recent period CTR for declining assets
- DECLINE FOCUS: Prioritize assets with significant performance drops (>20% decline preferred)
- FORBIDDEN: Only showing generic fatigue summaries without specific asset examples
- TREND ANALYSIS: Use actual time-series data to identify clear decline patterns

Focus on time-series decline detection. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which creative assets are showing declining performance trends?":
            # PROTECT Q2: Focus on DECLINING ASSET IDENTIFICATION - specific asset trend analysis and ranking by severity
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🛡️ DECLINING ASSET IDENTIFICATION REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 DECLINING ASSET RANKING RULES:
1. Focus on RANKING SPECIFIC ASSETS by severity of decline (worst first)
2. Identify assets with >15% decline in performance metrics regardless of initial volume
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. ALL COSTS ARE IN SOUTH AFRICAN RANDS (R) - never mention dollars
5. Compare days 1-3 vs days 5-7 for each asset and calculate decline percentages

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific declining assets ranked by severity with exact decline percentages
- Include decline ranking WITH specific asset examples and percentage drops
- Focus on assets with measurable decline (any decline >15% should be flagged)
- Provide 2-3 specific actionable recommendations for asset intervention

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE ASSET DECLINE DATA:

INDIVIDUAL ASSETS WITH TIME-SERIES DATA:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

DECLINE SUMMARY BY FORMAT:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 DECLINE RANKING REQUIREMENTS:
1. **Key Finding**: Single most important insight about which assets are declining worst
2. **Worst Decliners**: Rank 3-4 specific assets by decline severity (worst first)
3. **Decline Severity**: Show exact percentage drops for each declining asset
4. **Decline Patterns**: Compare early performance vs recent performance for each asset
5. **Recommendations**: 2-3 specific intervention tactics for the worst performing assets

🚨 ABSOLUTE REQUIREMENT: SHOW RANKED DECLINE SEVERITY
- MANDATORY: Quote exact asset names ranked by decline severity with % drops
- INCLUDE RANKING: Show "Asset A: 60% decline, Asset B: 45% decline" format
- SEVERITY FOCUS: Prioritize assets with largest percentage drops in performance
- FORBIDDEN: Only showing generic declining trends without specific asset ranking
- INTERVENTION PRIORITY: Use decline severity to recommend which assets need immediate attention

Focus on decline severity ranking. Keep concise and actionable.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Which ads are starting to lose engagement over time?":
            # PROTECT Q3: Focus on EARLY WARNING ENGAGEMENT DECLINE - proactive engagement monitoring with early intervention
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🛡️ EARLY WARNING ENGAGEMENT DECLINE REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 EARLY WARNING ENGAGEMENT RULES:
1. Focus on ENGAGEMENT DECLINE DETECTION (CTR, interaction rates) before they become severe
2. Identify assets with 10-30% engagement decline as early warning signals
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. Detect SUBTLE declining patterns that indicate trouble ahead (proactive monitoring)
5. Provide PREVENTIVE recommendations before engagement collapses completely

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific assets with early warning engagement decline by exact name
- Include early warning analysis WITH specific asset examples and engagement decline %
- Focus on assets showing moderate decline (10-30% drops as early warning signs)
- Provide 2-3 specific proactive recommendations for engagement preservation

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE ENGAGEMENT TREND DATA:

INDIVIDUAL ASSETS WITH ENGAGEMENT METRICS:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

ENGAGEMENT TREND SUMMARY:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 EARLY WARNING ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about early engagement decline patterns
2. **Early Warning Assets**: Show 3-4 specific assets with moderate engagement decline (10-30%)
3. **Engagement Trends**: Compare early vs recent engagement levels for flagged assets
4. **Proactive Alerts**: Identify assets needing attention before engagement becomes critical
5. **Recommendations**: 2-3 specific preventive tactics to preserve declining engagement

🚨 ABSOLUTE REQUIREMENT: SHOW EARLY WARNING PATTERNS
- MANDATORY: Quote exact asset names showing early engagement decline (10-30% drops preferred)
- INCLUDE TRENDS: Show engagement decline patterns before they become severe
- WARNING FOCUS: Flag assets with moderate decline as prevention targets
- FORBIDDEN: Only showing severe declines (those should be in Q2, not early warning Q3)
- PROACTIVE MONITORING: Use 10-30% decline range to identify assets needing preventive action

Focus on early warning engagement preservation. Keep concise and preventive.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        elif request.question == "Are my audiences seeing the same creative too often?":
            # PROTECT Q4: Focus on FREQUENCY ANALYSIS & AUDIENCE FATIGUE - creative rotation optimization with frequency insights
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🛡️ FREQUENCY ANALYSIS & AUDIENCE FATIGUE REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 IMPORTANT: USE USER-FRIENDLY TERMINOLOGY (NORMAL TEXT ONLY)
- Say "Ad Headlines" NOT "HEADLINE" (use normal text, not bold)
- Say "Ad Descriptions" NOT "DESCRIPTION" (use normal text, not bold)
- Say "Long Headlines" NOT "LONG_HEADLINE" (use normal text, not bold)
- Say "Callout Extensions" NOT "CALLOUT" (use normal text, not bold)
- Say "Sitelink Extensions" NOT "SITELINK" (use normal text, not bold)
- Say "Performance Max Images" NOT "IMAGE_PERFORMANCE_MAX" (use normal text, not bold)
- ONLY use bold formatting for section headers like "## Key Findings:" or "## Recommendations:"

🚨 FREQUENCY ANALYSIS RULES:
1. Focus on HIGH IMPRESSION VOLUME assets that may be causing audience oversaturation
2. Identify assets with >50 impressions AND declining performance (frequency fatigue indicators)
3. NEVER mention campaign ROAS, budget allocation, or campaign-level financial data
4. Analyze impression-to-performance correlation to detect oversaturation
5. Provide STRATEGIC ROTATION recommendations based on impression frequency patterns

📱 MOBILE-FIRST RESPONSE REQUIREMENTS:
- Keep total response under 150 words
- MUST show specific high-frequency assets by exact name with impression volumes
- Include frequency analysis WITH impression counts and performance decline correlation
- Focus on assets with high impressions (>50) that also show performance decline
- Provide 2-3 specific rotation recommendations for oversaturated assets

🏢 ACCOUNT CONTEXT:
Business Name: {account_context['account_name']}
Business Type: {account_context['business_type']}
Analysis Period: {request.start_date} to {request.end_date}

📊 COMPLETE FREQUENCY DATA:

INDIVIDUAL ASSETS WITH IMPRESSION VOLUMES:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

FREQUENCY SUMMARY BY FORMAT:
{json.dumps(creative_data.get('format_summary', {}), indent=2)}

🎯 FREQUENCY ANALYSIS REQUIREMENTS:
1. **Key Finding**: Single most important insight about frequency oversaturation patterns
2. **High-Frequency Assets**: Show 3-4 specific assets with highest impression volumes
3. **Oversaturation Indicators**: Identify assets with high impressions AND declining performance
4. **Rotation Priority**: Which high-frequency assets need immediate rotation based on performance
5. **Recommendations**: 2-3 specific strategic rotation tactics to prevent audience fatigue

🚨 ABSOLUTE REQUIREMENT: SHOW FREQUENCY-PERFORMANCE CORRELATION
- MANDATORY: Quote exact asset names with highest impression volumes from the data
- INCLUDE CORRELATION: Show impression counts AND performance decline for high-frequency assets
- FREQUENCY FOCUS: Prioritize assets with >50 impressions that also show declining performance
- FORBIDDEN: Only showing impression volumes without performance correlation analysis
- ROTATION STRATEGY: Use high impressions + declining performance to identify rotation candidates

Focus on impression frequency and rotation strategy. Keep concise and strategic.

FORMATTING: Use "## Key Findings:" and "## Recommendations:" headers only. Short bullet points under each."""
        else:
            # FALLBACK: Default prompt for other questions
            creative_prompt = f"""You are Mia, a conversational marketing intelligence assistant specializing in creative asset analysis.

🎨 CREATIVE ASSET ANALYSIS REQUEST
Category: {request.category.upper()}
Question: "{request.question}"

🚨 CREATIVE-ONLY ANALYSIS RULES:
1. Focus ONLY on creative assets: headlines, descriptions, images, sitelinks, callouts
2. NEVER mention campaign spend, ROAS, cost-per-conversion, or budget data
3. Analyze creative performance: clicks, interaction rates, engagement metrics
4. Provide asset-specific optimization recommendations
5. No campaign-level financial performance mixing

📊 COMPREHENSIVE ASSET PERFORMANCE DATA:
Total Assets Found: {creative_data.get('asset_count', 0)}
Responsive Assets (HEADLINE/DESCRIPTION/TEXT/IMAGE): {creative_data.get('total_responsive_assets', 0)}
Extension Assets (CALLOUT/SITELINK/PRICE/PROMOTION): {creative_data.get('total_extension_assets', 0)}
Text Assets: {creative_data.get('total_text_assets', 0)}
Image Assets: {creative_data.get('total_image_assets', 0)}

📝 ALL ASSET FORMATS:
{json.dumps(creative_data.get('asset_formats', {}), indent=2)}

Please analyze the creative asset performance data above and provide specific recommendations for "{request.question}" focusing on {request.category} optimization. Be specific about which assets perform best and why.

**Start your response with a bold summary paragraph** using **bold text** to highlight the key findings.

FORMATTING: Use clear section headers followed by bullet points. Avoid numbering immediately after headers (e.g. use "Key Findings:" then bullets, not "Key Findings: 1.")"""

        # REUSE: Claude API integration (from chat_endpoint.py)
        from services.claude_agent import get_claude_intent_agent
        claude_agent = await get_claude_intent_agent()
        
        print(f"[CREATIVE-ANALYSIS] Sending to Claude...")
        
        # Use the working Claude agent format (REUSE pattern)
        headers = {
            "Content-Type": "application/json",
            "x-api-key": claude_agent.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": claude_agent.model,  # Use the agent's configured model
            "max_tokens": 1500,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": creative_prompt}]
        }
        
        # REUSE: Same timeout and error handling (120s timeout) with 429 rate limit support
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )

            # Handle 429 rate limit specifically
            if response.status_code == 429:
                print(f"[CREATIVE-ANALYSIS] Rate limit hit (429) - advising user to wait")
                end_time = asyncio.get_event_loop().time()
                response_time_ms = int((end_time - start_time) * 1000)

                return {
                    "success": False,
                    "error": "Rate limit reached. Please wait 30 seconds and try again.",
                    "retry_after": 30,
                    "error_type": "rate_limit",
                    "response_time_ms": response_time_ms,
                    "question_info": {
                        "category": request.category,
                        "question": request.question
                    }
                }

            response.raise_for_status()  # Handle other HTTP errors

            claude_result = response.json()

            if 'content' in claude_result and len(claude_result['content']) > 0:
                claude_response = claude_result['content'][0]['text'].strip()
            else:
                raise Exception("No content in Claude response")
        
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        print(f"[TRIPLE-MCP] SUCCESS! Complete asset analysis with {total_assets} assets from all three tables. Response time: {response_time_ms}ms")
        
        # NEW: Creative-specific response format
        return {
            "success": True,
            "creative_response": claude_response,
            "asset_data": json.dumps(creative_data, indent=2),
            "creative_prompt": f"Creative prompt too long to display - {len(creative_prompt)} chars",
            "model_used": claude_agent.model,
            "response_time_ms": response_time_ms,
            "question_info": {
                "category": request.category,
                "question": request.question,
                "question_index": valid_questions.index(request.question) + 1,
                "total_questions": len(valid_questions)
            }
        }
        
    except Exception as e:
        print(f"[TRIPLE-MCP] ERROR: {str(e)}")
        end_time = asyncio.get_event_loop().time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "success": False,
            "error": str(e),
            "creative_prompt": creative_prompt if 'creative_prompt' in locals() else "Error occurred before prompt generation",
            "response_time_ms": response_time_ms
        }