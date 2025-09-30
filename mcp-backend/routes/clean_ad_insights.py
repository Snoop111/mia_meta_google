"""
Clean Ad Insights Routes
Simplified and focused ad performance endpoints
"""

from fastapi import APIRouter, HTTPException, Form
import json
from typing import Dict, Any, List
import logging

from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
from analytics.ad_performance import AdPerformanceAnalyzer, CampaignComparator
from analytics.recommendation_engine import RecommendationEngine, ActionPlanGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ad-performance")
async def ad_performance_analysis(request: str = Form(...)):
    """Comprehensive ad performance analysis"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    data_sources = req_data.get('data_sources', ['meta_ads', 'google_ads'])
    
    # Load credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    ad_data = await _fetch_ad_data(data_sources, start_date, end_date)
    
    if ad_data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No ad data found for {start_date} to {end_date}"
        )
    
    # Analyze performance
    analyzer = AdPerformanceAnalyzer(ad_data)
    analysis = analyzer.analyze_performance()
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "data_sources": data_sources,
        "total_records": len(ad_data),
        **analysis
    }

@router.post("/campaign-comparison")
async def campaign_comparison(request: str = Form(...)):
    """Compare performance across campaigns"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    campaigns = req_data.get('campaigns', [])  # Specific campaigns to compare
    
    # Load credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    ad_data = await _fetch_ad_data(['meta_ads', 'google_ads'], start_date, end_date)
    
    if ad_data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No campaign data found for {start_date} to {end_date}"
        )
    
    # Compare campaigns
    comparator = CampaignComparator(ad_data)
    comparison = comparator.compare_campaigns(campaigns)
    
    return {
        "user_id": user_id,
        "comparison_period": f"{start_date} to {end_date}",
        "campaigns_filter": campaigns if campaigns else "All campaigns",
        **comparison
    }

@router.post("/ad-recommendations")
async def ad_recommendations(request: str = Form(...)):
    """Generate actionable ad optimization recommendations"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    min_spend = req_data.get('min_spend', 100)
    
    # Load credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    ad_data = await _fetch_ad_data(['meta_ads', 'google_ads'], start_date, end_date)
    
    if ad_data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No ad data found for {start_date} to {end_date}"
        )
    
    # Generate recommendations
    engine = RecommendationEngine(ad_data, min_spend)
    recommendations = engine.generate_recommendations()
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "min_spend_threshold": min_spend,
        "recommendations": recommendations,
        "total_recommendations": len(recommendations)
    }

@router.post("/optimization-action-plan")
async def optimization_action_plan(request: str = Form(...)):
    """Generate detailed optimization action plan"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    budget_limit = req_data.get('budget_increase_limit', 50)
    
    # Load credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    ad_data = await _fetch_ad_data(['meta_ads', 'google_ads'], start_date, end_date)
    
    if ad_data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No ad data found for {start_date} to {end_date}"
        )
    
    # Generate action plan
    planner = ActionPlanGenerator(ad_data)
    action_plan = planner.generate_action_plan(budget_limit)
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "budget_increase_limit": f"{budget_limit}%",
        "action_plan": action_plan,
        "implementation_note": "Execute in order: Immediate → Weekly → Monthly"
    }

def _parse_request(request: str) -> Dict[str, Any]:
    """Parse JSON request with error handling"""
    try:
        return json.loads(request)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request")

def _extract_required_fields(req_data: Dict[str, Any]) -> tuple:
    """Extract and validate required fields"""
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    if not all([user_id, start_date, end_date]):
        raise HTTPException(
            status_code=400,
            detail="user_id, start_date, and end_date are required"
        )
    
    return user_id, start_date, end_date

async def _fetch_ad_data(data_sources: List[str], start_date: str, end_date: str):
    """Fetch ad data from specified sources"""
    try:
        return await data_integrator_instance.fetch_specific_data(
            connector_names=data_sources,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error fetching ad data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching ad data: {str(e)}")