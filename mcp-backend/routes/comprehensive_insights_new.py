"""
Comprehensive Insights Route - OAuth Only
Provides individual insights per data source plus combined insights
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import json
import asyncio
import logging

from credential_manager import credential_manager
from shared_integrator import data_integrator_instance

logger = logging.getLogger(__name__)

router = APIRouter()

class DataSelection(BaseModel):
    platform: str  # 'facebook' | 'google_ads' | 'google_analytics'
    account_id: Optional[str] = None
    property_id: Optional[str] = None
    campaign_ids: Optional[List[str]] = None
    date_range: Dict[str, str]

class AnalysisOptions(BaseModel):
    min_spend_threshold: float = 100
    budget_increase_limit: float = 50
    include_predictions: bool = True
    prediction_target: str = "conversions"

class ComprehensiveInsightsRequest(BaseModel):
    user_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_spend_threshold: float = 100
    budget_increase_limit: float = 50
    data_selections: List[DataSelection]  # Required - must specify data sources
    analysis_options: Optional[AnalysisOptions] = None

def _clean_for_json(obj):
    """Clean up data structures for JSON serialization"""
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    elif hasattr(obj, '__dict__'):
        return _clean_for_json(obj.__dict__)
    else:
        return obj

@router.post("/comprehensive-insights")
async def comprehensive_insights(request: ComprehensiveInsightsRequest):
    """
    OAuth-only comprehensive insights endpoint
    
    Provides individual insights per data source, plus combined insights when multiple sources available:
    - GA4 insights: user behavior, traffic sources, conversion funnels
    - Google Ads insights: campaign performance, keyword analysis, ad optimization
    - Meta Ads insights: audience performance, creative analysis, platform comparison
    - Combined insights: user journey, cross-platform attribution, funnel optimization
    """
    
    try:
        user_id = request.user_id
        start_date = request.start_date
        end_date = request.end_date
        min_spend_threshold = request.min_spend_threshold
        budget_increase_limit = request.budget_increase_limit
        data_selections = request.data_selections
        
        logger.info(f"Starting OAuth-only comprehensive analysis for user {user_id}")
        logger.info(f"Data selections: {len(data_selections)} platforms configured")
        
        # Set default date range if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")
            start_date = start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            logger.info(f"Using default date range: {start_date} to {end_date}")
        
        # Load user OAuth credentials
        credential_manager.load_user_connectors(user_id)
        
        # Extract platforms and map to data sources
        platform_map = {
            'facebook': 'meta_ads',
            'google_ads': 'google_ads', 
            'google_analytics': 'ga4'
        }
        
        # Fetch data per platform
        platform_data = {}
        for selection in data_selections:
            platform = selection.platform
            data_source = platform_map.get(platform, platform)
            
            try:
                logger.info(f"Fetching data for {platform} ({data_source})")
                
                if data_source == 'ga4':
                    platform_data[platform] = await _fetch_ga4_data(
                        user_id, start_date, end_date, selection.property_id
                    )
                elif data_source == 'google_ads':
                    platform_data[platform] = await _fetch_google_ads_data(
                        user_id, start_date, end_date, selection.account_id
                    )
                elif data_source == 'meta_ads':
                    platform_data[platform] = await _fetch_meta_ads_data(
                        user_id, start_date, end_date, selection.account_id
                    )
                    
                if platform_data[platform] is not None and not platform_data[platform].empty:
                    logger.info(f"✅ {platform} data: {len(platform_data[platform])} rows")
                else:
                    logger.warning(f"❌ {platform} data: empty or failed")
                    
            except Exception as e:
                logger.error(f"Failed to fetch {platform} data: {e}")
                platform_data[platform] = None
        
        # Generate individual insights per platform
        individual_insights = {}
        for platform, data in platform_data.items():
            if data is not None and not data.empty:
                logger.info(f"Generating insights for {platform}")
                individual_insights[platform] = await _generate_platform_insights(
                    platform, data, min_spend_threshold, budget_increase_limit
                )
        
        # Generate combined insights if multiple platforms available
        combined_insights = {}
        available_platforms = [p for p, data in platform_data.items() if data is not None and not data.empty]
        
        if len(available_platforms) > 1:
            logger.info(f"Generating combined insights for platforms: {available_platforms}")
            combined_insights = await _generate_combined_insights(
                platform_data, available_platforms, min_spend_threshold, budget_increase_limit
            )
        
        # Build response
        response = {
            "success": True,
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "configuration": {
                "platforms_analyzed": list(individual_insights.keys()),
                "has_combined_insights": len(combined_insights) > 0,
                "min_spend_threshold": min_spend_threshold,
                "budget_increase_limit": budget_increase_limit
            },
            "individual_insights": individual_insights,
            "combined_insights": combined_insights,
            "data_availability": {
                platform: data is not None and not data.empty 
                for platform, data in platform_data.items()
            }
        }
        
        return _clean_for_json(response)
        
    except Exception as e:
        logger.error(f"Comprehensive insights error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Individual platform data fetchers
async def _fetch_ga4_data(user_id: str, start_date: str, end_date: str, property_id: str = None):
    """Fetch GA4 data with comprehensive metrics"""
    try:
        connector = None
        for name, conn in data_integrator_instance.connectors.items():
            if name == 'ga4':
                connector = conn
                break
        
        if not connector:
            return None
        
        # Override property ID if specified
        if property_id:
            original_property_id = connector.property_id
            connector.property_id = property_id
            
        try:
            data = await connector.fetch_data(
                start_date=start_date,
                end_date=end_date,
                dimensions=[
                    'date', 'sessionDefaultChannelGrouping', 'sessionSourceMedium',
                    'sessionCampaignName', 'deviceCategory', 'city', 'country'
                ],
                metrics=[
                    'sessions', 'newUsers', 'screenPageViews', 'engagementRate',
                    'userEngagementDuration', 'keyEvents', 'totalRevenue'
                ]
            )
            return data
        finally:
            if property_id:
                connector.property_id = original_property_id
                
    except Exception as e:
        logger.error(f"GA4 data fetch error: {e}")
        return None

async def _fetch_google_ads_data(user_id: str, start_date: str, end_date: str, account_id: str = None):
    """Fetch Google Ads data with comprehensive metrics"""
    try:
        ad_sources = ['google_ads']
        data = await data_integrator_instance.fetch_specific_data(
            connector_names=ad_sources,
            start_date=start_date,
            end_date=end_date
        )
        return data
    except Exception as e:
        logger.error(f"Google Ads data fetch error: {e}")
        return None

async def _fetch_meta_ads_data(user_id: str, start_date: str, end_date: str, account_id: str = None):
    """Fetch Meta Ads data with comprehensive metrics"""
    try:
        ad_sources = ['meta_ads']
        data = await data_integrator_instance.fetch_specific_data(
            connector_names=ad_sources,
            start_date=start_date,
            end_date=end_date
        )
        return data
    except Exception as e:
        logger.error(f"Meta Ads data fetch error: {e}")
        return None

# Individual platform insight generators
async def _generate_platform_insights(platform: str, data, min_spend_threshold: float, budget_increase_limit: float):
    """Generate insights specific to each platform"""
    
    insights = {
        "platform": platform,
        "data_summary": {
            "total_rows": len(data),
            "date_range": {
                "start": str(data['date'].min()) if 'date' in data.columns else None,
                "end": str(data['date'].max()) if 'date' in data.columns else None
            },
            "columns": list(data.columns)
        }
    }
    
    try:
        if platform == 'google_analytics':
            insights.update(await _generate_ga4_insights(data))
        elif platform == 'google_ads':
            insights.update(await _generate_google_ads_insights(data, min_spend_threshold))
        elif platform == 'facebook':
            insights.update(await _generate_meta_ads_insights(data, min_spend_threshold))
            
    except Exception as e:
        logger.error(f"Error generating {platform} insights: {e}")
        insights["error"] = str(e)
    
    return insights

async def _generate_ga4_insights(data):
    """Generate GA4-specific insights"""
    insights = {}
    
    # Traffic overview
    if 'sessions' in data.columns:
        insights["traffic_overview"] = {
            "total_sessions": int(data['sessions'].sum()),
            "total_users": int(data.get('newUsers', data.get('users', [0])).sum()),
            "avg_session_duration": float(data.get('userEngagementDuration', [0]).mean()),
            "engagement_rate": float(data.get('engagementRate', [0]).mean())
        }
    
    # Top channels
    if 'sessionDefaultChannelGrouping' in data.columns:
        channel_performance = data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'keyEvents': 'sum' if 'keyEvents' in data.columns else lambda x: 0
        }).reset_index()
        
        insights["top_channels"] = channel_performance.head(5).to_dict('records')
    
    # Geographic insights
    if 'country' in data.columns:
        geo_performance = data.groupby('country')['sessions'].sum().head(10)
        insights["geographic_performance"] = geo_performance.to_dict()
    
    # Device insights
    if 'deviceCategory' in data.columns:
        device_performance = data.groupby('deviceCategory')['sessions'].sum()
        insights["device_breakdown"] = device_performance.to_dict()
    
    return insights

async def _generate_google_ads_insights(data, min_spend_threshold: float):
    """Generate Google Ads specific insights"""
    from analytics.ad_performance import AdPerformanceAnalyzer, CampaignComparator
    from analytics.recommendation_engine import RecommendationEngine
    
    insights = {}
    
    try:
        # Ad performance analysis
        analyzer = AdPerformanceAnalyzer(data)
        insights["ad_performance"] = analyzer.analyze_performance()
        
        # Campaign comparison
        comparator = CampaignComparator(data)
        insights["campaign_comparison"] = comparator.compare_campaigns()
        
        # Recommendations
        engine = RecommendationEngine(data, min_spend_threshold)
        insights["recommendations"] = engine.generate_recommendations()
        
    except Exception as e:
        logger.error(f"Google Ads insights error: {e}")
        insights["error"] = str(e)
    
    return insights

async def _generate_meta_ads_insights(data, min_spend_threshold: float):
    """Generate Meta Ads specific insights"""
    # Similar to Google Ads but with Meta-specific metrics
    insights = {
        "ad_performance": {},
        "audience_insights": {},
        "creative_performance": {}
    }
    
    # Add Meta-specific analysis here
    return insights

async def _generate_combined_insights(platform_data: dict, available_platforms: list, min_spend_threshold: float, budget_increase_limit: float):
    """Generate insights that require multiple data sources"""
    combined_insights = {}
    
    try:
        # User Journey Analysis (GA4 + Ads data)
        ga4_data = platform_data.get('google_analytics')
        ads_data = platform_data.get('google_ads') or platform_data.get('facebook')
        
        if ga4_data is not None and not ga4_data.empty and ads_data is not None and not ads_data.empty:
            logger.info("Generating user journey analysis...")
            
            from analytics.journey_analyzer import JourneyAnalyzer
            journey_analyzer = JourneyAnalyzer(ga4_data, ads_data)
            combined_insights["user_journey"] = journey_analyzer.analyze_funnel()
            
        # Funnel Optimization (GA4 + Ads data)
        if ga4_data is not None and not ga4_data.empty and ads_data is not None and not ads_data.empty:
            logger.info("Generating funnel optimization...")
            
            from analytics.funnel_optimizer import FunnelOptimizer
            optimizer = FunnelOptimizer(ga4_data, ads_data)
            combined_insights["funnel_optimization"] = optimizer.generate_optimization_plan(budget_increase_limit)
        
        # Cross-platform attribution
        if len(available_platforms) > 1:
            combined_insights["cross_platform_attribution"] = await _generate_attribution_analysis(platform_data, available_platforms)
        
    except Exception as e:
        logger.error(f"Combined insights error: {e}")
        combined_insights["error"] = str(e)
    
    return combined_insights

async def _generate_attribution_analysis(platform_data: dict, available_platforms: list):
    """Generate cross-platform attribution insights"""
    attribution = {
        "platforms_analyzed": available_platforms,
        "attribution_model": "data_driven",
        "insights": []
    }
    
    # Add attribution logic here
    return attribution