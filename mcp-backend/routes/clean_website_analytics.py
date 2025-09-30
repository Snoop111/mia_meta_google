"""
Clean Website Analytics Routes
Simplified and focused analytics endpoints
"""

from fastapi import APIRouter, HTTPException, Form
import pandas as pd
import json
from typing import Dict, Any
import logging

from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
from analytics.journey_analyzer import JourneyAnalyzer
from analytics.funnel_optimizer import FunnelOptimizer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/journey-analysis")
async def journey_analysis(request: str = Form(...)):
    """Analyze user journey from ads to conversions"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        ga4_data = await _fetch_ga4_data(user_id, start_date, end_date)
        ad_data = await _fetch_ad_data(start_date, end_date)
        
        analyzer = JourneyAnalyzer(ga4_data, ad_data)
        analysis = analyzer.analyze_funnel()
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            **analysis
        }
        
    except Exception as e:
        logger.error(f"Journey analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/funnel-optimization")
async def funnel_optimization(request: str = Form(...)):
    """Generate funnel optimization recommendations"""
    
    req_data = _parse_request(request)
    user_id, start_date, end_date = _extract_required_fields(req_data)
    budget_limit = req_data.get('budget_increase_limit', 50)
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        ga4_data = await _fetch_ga4_data(user_id, start_date, end_date)
        ad_data = await _fetch_ad_data(start_date, end_date)
        
        optimizer = FunnelOptimizer(ga4_data, ad_data)
        optimization_plan = optimizer.generate_optimization_plan(budget_limit)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "optimization_plan": optimization_plan
        }
        
    except Exception as e:
        logger.error(f"Funnel optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

async def _fetch_ga4_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch GA4 data for the specified user and date range"""
    try:
        # Get GA4 connector
        ga4_connector = None
        for name, connector in data_integrator_instance.connectors.items():
            if name == 'ga4':
                ga4_connector = connector
                break
        
        if not ga4_connector:
            logger.warning("GA4 connector not found")
            return pd.DataFrame()
        
        # Fetch GA4 data with required dimensions and metrics
        data = await ga4_connector.fetch_data(
            start_date=start_date,
            end_date=end_date,
            dimensions=[
                'date', 'sessionDefaultChannelGrouping', 'sessionSourceMedium',
                'sessionCampaignName', 'deviceCategory'
            ],
            metrics=[
                'sessions', 'users', 'pageviews', 'engagementRate',
                'avgSessionDuration', 'conversions'
            ]
        )
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching GA4 data: {e}")
        return pd.DataFrame()

async def _fetch_ad_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch ad data from Meta and Google"""
    try:
        ad_data = await data_integrator_instance.fetch_specific_data(
            connector_names=['meta_ads', 'google_ads'],
            start_date=start_date,
            end_date=end_date
        )
        return ad_data
        
    except Exception as e:
        logger.error(f"Error fetching ad data: {e}")
        return pd.DataFrame()