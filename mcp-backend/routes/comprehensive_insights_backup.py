"""
Comprehensive Insights Route
All-in-one endpoint that executes all available analyses with flexible input options
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import json
import asyncio
import logging

from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
from clean_consolidator import CleanDataConsolidator
from data_loader import DataLoader

# Import all analytics modules
from analytics.journey_analyzer import JourneyAnalyzer
from analytics.funnel_optimizer import FunnelOptimizer
from analytics.ad_performance import AdPerformanceAnalyzer, CampaignComparator
from analytics.recommendation_engine import RecommendationEngine, ActionPlanGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

def _clean_for_json(obj):
    """Clean data structures to make them JSON serializable"""
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            # Convert tuple keys to strings
            if isinstance(k, tuple):
                key = str(k)
            else:
                key = k
            cleaned[key] = _clean_for_json(v)
        return cleaned
    elif isinstance(obj, (list, tuple)):
        return [_clean_for_json(item) for item in obj]
    elif hasattr(obj, 'to_dict'):  # pandas objects
        return _clean_for_json(obj.to_dict())
    elif hasattr(obj, '__dict__'):  # custom objects
        return _clean_for_json(obj.__dict__)
    else:
        return obj

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
        use_api_data = request.use_api_data
        min_spend_threshold = request.min_spend_threshold
        budget_increase_limit = request.budget_increase_limit
        data_selections = request.data_selections or []
        
        logger.info(f"Starting comprehensive analysis for user {user_id}")
        logger.info(f"Data selections: {len(data_selections)} platforms configured")
        
        # Set default date range if not provided (get maximum available data)
        if not start_date or not end_date:
            # Default to last 90 days or maximum available
            from datetime import datetime, timedelta
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")
            start_date = start_date or (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            logger.info(f"Using default date range: {start_date} to {end_date}")
        
        # Determine data sources from selections or use default
        if data_selections:
            # Extract unique platforms from data selections
            platforms = list(set(selection.platform for selection in data_selections))
            # Map platform names to data source names
            platform_map = {
                'facebook': 'meta_ads',
                'google_ads': 'google_ads', 
                'google_analytics': 'ga4'
            }
            data_source_list = [platform_map.get(platform, platform) for platform in platforms]
            logger.info(f"Data sources from selections: {data_source_list}")
        else:
            # Fallback to default
            data_source_list = [s.strip() for s in (request.data_sources or "google_ads").split(",") if s.strip()]
            logger.info(f"Using default data sources: {data_source_list}")
        
        # Load user credentials if using API data
        if use_api_data:
            credential_manager.load_user_connectors(user_id)
        
        # Step 1: Consolidate uploaded file data (not supported in JSON mode)
        file_consolidator = CleanDataConsolidator()
        uploaded_data_available = {
            "ga4_file": False,
            "meta_file": False, 
            "google_file": False
        }
        
        # Step 2: Fetch API data if requested
        api_ga4_data = None
        api_ad_data = None
        
        if use_api_data:
            api_ga4_data, api_ad_data = await _fetch_api_data_with_selections(
                user_id, start_date, end_date, data_source_list, data_selections
            )
        
        # Step 3: Determine what data we have and run appropriate analyses
        results = await _run_comprehensive_analysis(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            file_consolidator=file_consolidator,
            uploaded_data_available=uploaded_data_available,
            api_ga4_data=api_ga4_data,
            api_ad_data=api_ad_data,
            min_spend_threshold=min_spend_threshold,
            budget_increase_limit=budget_increase_limit
        )
        
        try:
            response = {
                "success": True,
                "user_id": user_id,
                "analysis_period": f"{start_date} to {end_date}",
                "configuration": {
                    "uploaded_files": uploaded_data_available,
                    "used_api_data": use_api_data,
                    "data_sources": data_source_list,
                    "min_spend_threshold": min_spend_threshold,
                    "budget_increase_limit": budget_increase_limit
                },
                "analyses_performed": list(results.keys()),
                **results
            }
            
            # Clean up data structures for JSON serialization
            cleaned_results = {}
            for key, value in results.items():
                cleaned_results[key] = _clean_for_json(value)
            
            response = {
                "success": True,
                "user_id": user_id,
                "analysis_period": f"{start_date} to {end_date}",
                "configuration": {
                    "uploaded_files": uploaded_data_available,
                    "used_api_data": use_api_data,
                    "data_sources": data_source_list,
                    "min_spend_threshold": min_spend_threshold,
                    "budget_increase_limit": budget_increase_limit
                },
                "analyses_performed": list(results.keys()),
                **cleaned_results
            }
            
            # Test JSON serialization
            import json
            json.dumps(response, default=str)
            
            return response
            
        except Exception as e:
            logger.error(f"JSON serialization error: {e}")
            # Return a safe response without problematic data
            return {
                "success": True,
                "user_id": user_id,
                "analysis_period": f"{start_date} to {end_date}",
                "configuration": {
                    "uploaded_files": uploaded_data_available,
                    "used_api_data": use_api_data,
                    "data_sources": data_source_list,
                    "min_spend_threshold": min_spend_threshold,
                    "budget_increase_limit": budget_increase_limit
                },
                "analyses_performed": list(results.keys()),
                "error": f"Some analysis results could not be serialized: {str(e)}",
                "results_available": len(results)
            }
        
    except Exception as e:
        logger.error(f"Comprehensive insights error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/comprehensive-insights-form")
async def comprehensive_insights_form(
    # Required fields
    user_id: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    
    # File upload options (optional)
    ga4_file: Optional[UploadFile] = File(None),
    meta_file: Optional[UploadFile] = File(None),
    google_file: Optional[UploadFile] = File(None),
    
    # API configuration (optional)
    use_api_data: bool = Form(False),
    
    # Analysis options
    min_spend_threshold: float = Form(100),
    budget_increase_limit: float = Form(50),
    
    # Data source preferences
    data_sources: str = Form("meta_ads,google_ads")  # Comma-separated
):
    """Legacy form-based endpoint for backward compatibility"""
    
    # Convert form data to request object
    request = ComprehensiveInsightsRequest(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        use_api_data=use_api_data,
        min_spend_threshold=min_spend_threshold,
        budget_increase_limit=budget_increase_limit,
        data_sources=data_sources
    )
    
    # Call the main function
    return await comprehensive_insights(request)

async def _process_uploaded_files(
    consolidator: CleanDataConsolidator,
    ga4_file: Optional[UploadFile],
    meta_file: Optional[UploadFile],
    google_file: Optional[UploadFile]
) -> Dict[str, bool]:
    """Process uploaded files and return what was successfully loaded"""
    
    files_processed = {
        "ga4_file": False,
        "meta_file": False,
        "google_file": False
    }
    
    if ga4_file:
        df = _read_uploaded_file(ga4_file)
        if df is not None:
            files_processed["ga4_file"] = consolidator.add_ga4_data(df)
    
    if meta_file:
        df = _read_uploaded_file(meta_file)
        if df is not None:
            files_processed["meta_file"] = consolidator.add_meta_data(df)
    
    if google_file:
        df = _read_uploaded_file(google_file)
        if df is not None:
            files_processed["google_file"] = consolidator.add_google_ads_data(df)
    
    return files_processed

async def _fetch_api_data_with_selections(
    user_id: str, 
    start_date: str, 
    end_date: str, 
    data_sources: list,
    data_selections: List[DataSelection] = None
) -> tuple:
    """Enhanced fetch data that uses specific account/property selections"""
    
    api_ga4_data = None
    api_ad_data = None
    
    # Create a map of selections by platform for easy lookup
    selection_map = {}
    if data_selections:
        for selection in data_selections:
            selection_map[selection.platform] = selection
    
    try:
        # Fetch GA4 data with specific property ID if selected
        if 'ga4' in data_sources or any(s.platform == 'google_analytics' for s in data_selections or []):
            ga4_selection = selection_map.get('google_analytics')
            if ga4_selection and ga4_selection.property_id:
                api_ga4_data = await _fetch_ga4_api_data_with_property(
                    user_id, start_date, end_date, ga4_selection.property_id
                )
            else:
                api_ga4_data = await _fetch_ga4_api_data(user_id, start_date, end_date)
    except Exception as e:
        logger.warning(f"GA4 API data fetch failed: {e}")
    
    try:
        # Fetch ad data with specific account IDs if selected
        ad_sources = [src for src in data_sources if src in ['google_ads', 'meta_ads']]
        if ad_sources:
            # TODO: Implement account-specific fetching for Google Ads and Meta Ads
            api_ad_data = await data_integrator_instance.fetch_specific_data(
                connector_names=ad_sources,
                start_date=start_date,
                end_date=end_date
            )
    except Exception as e:
        logger.warning(f"Ad API data fetch failed: {e}")
    
    return api_ga4_data, api_ad_data

async def _fetch_api_data(
    user_id: str, 
    start_date: str, 
    end_date: str, 
    data_sources: list
) -> tuple:
    """Fetch data from APIs if credentials are available"""
    
    api_ga4_data = None
    api_ad_data = None
    
    try:
        # Fetch GA4 data
        api_ga4_data = await _fetch_ga4_api_data(user_id, start_date, end_date)
    except Exception as e:
        logger.warning(f"GA4 API data fetch failed: {e}")
    
    try:
        # Fetch ad data
        api_ad_data = await data_integrator_instance.fetch_specific_data(
            connector_names=data_sources,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.warning(f"Ad API data fetch failed: {e}")
    
    return api_ga4_data, api_ad_data

async def _run_comprehensive_analysis(
    user_id: str,
    start_date: str,
    end_date: str,
    file_consolidator: CleanDataConsolidator,
    uploaded_data_available: Dict[str, bool],
    api_ga4_data,
    api_ad_data,
    min_spend_threshold: float,
    budget_increase_limit: float
) -> Dict[str, Any]:
    """Run all available analyses based on available data"""
    
    results = {}
    
    # Get consolidated uploaded data
    uploaded_data = file_consolidator.get_data()
    has_uploaded_data = not uploaded_data.empty
    
    # Determine what data we can work with
    has_api_ad_data = api_ad_data is not None and not api_ad_data.empty
    has_api_ga4_data = api_ga4_data is not None and not api_ga4_data.empty
    
    logger.info(f"Data availability - Uploaded: {has_uploaded_data}, API Ad: {has_api_ad_data}, API GA4: {has_api_ga4_data}")
    
    # Analysis 1: File Upload Consolidation (if we have uploaded files)
    if has_uploaded_data:
        try:
            results["file_consolidation"] = file_consolidator.generate_insights()
            logger.info("✅ File consolidation analysis completed")
        except Exception as e:
            logger.error(f"File consolidation failed: {e}")
            results["file_consolidation"] = {"error": str(e)}
    
    # Analysis 2: Ad Performance Analysis (prefer API data, fallback to uploaded)
    ad_data_for_analysis = api_ad_data if has_api_ad_data else uploaded_data
    if not ad_data_for_analysis.empty:
        try:
            analyzer = AdPerformanceAnalyzer(ad_data_for_analysis)
            results["ad_performance"] = analyzer.analyze_performance()
            logger.info("✅ Ad performance analysis completed")
        except Exception as e:
            logger.error(f"Ad performance analysis failed: {e}")
            results["ad_performance"] = {"error": str(e)}
    
    # Analysis 3: Campaign Comparison
    if not ad_data_for_analysis.empty:
        try:
            comparator = CampaignComparator(ad_data_for_analysis)
            results["campaign_comparison"] = comparator.compare_campaigns()
            logger.info("✅ Campaign comparison completed")
        except Exception as e:
            logger.error(f"Campaign comparison failed: {e}")
            results["campaign_comparison"] = {"error": str(e)}
    
    # Analysis 4: User Journey Analysis (needs both GA4 and ad data)
    ga4_data_for_analysis = api_ga4_data if has_api_ga4_data else uploaded_data
    logger.info(f"User journey check - GA4 empty: {ga4_data_for_analysis.empty if ga4_data_for_analysis is not None else 'None'}, Ad empty: {ad_data_for_analysis.empty if ad_data_for_analysis is not None else 'None'}")
    if not ga4_data_for_analysis.empty and not ad_data_for_analysis.empty:
        try:
            logger.info("Starting user journey analysis...")
            journey_analyzer = JourneyAnalyzer(ga4_data_for_analysis, ad_data_for_analysis)
            results["user_journey"] = journey_analyzer.analyze_funnel()
            logger.info("✅ User journey analysis completed")
        except Exception as e:
            logger.error(f"User journey analysis failed: {e}")
            results["user_journey"] = {"error": str(e)}
    
    # Analysis 5: Funnel Optimization (needs both GA4 and ad data)
    if not ga4_data_for_analysis.empty and not ad_data_for_analysis.empty:
        try:
            logger.info("Starting funnel optimization...")
            optimizer = FunnelOptimizer(ga4_data_for_analysis, ad_data_for_analysis)
            results["funnel_optimization"] = optimizer.generate_optimization_plan(budget_increase_limit)
            logger.info("✅ Funnel optimization completed")
        except Exception as e:
            logger.error(f"Funnel optimization failed: {e}")
            results["funnel_optimization"] = {"error": str(e)}
    
    # Analysis 6: Recommendations
    if not ad_data_for_analysis.empty:
        try:
            engine = RecommendationEngine(ad_data_for_analysis, min_spend_threshold)
            results["recommendations"] = engine.generate_recommendations()
            logger.info("✅ Recommendations generated")
        except Exception as e:
            logger.error(f"Recommendations failed: {e}")
            results["recommendations"] = {"error": str(e)}
    
    # Analysis 7: Action Plan
    if not ad_data_for_analysis.empty:
        try:
            planner = ActionPlanGenerator(ad_data_for_analysis)
            results["action_plan"] = planner.generate_action_plan(budget_increase_limit)
            logger.info("✅ Action plan generated")
        except Exception as e:
            logger.error(f"Action plan failed: {e}")
            results["action_plan"] = {"error": str(e)}
    
    # Add summary of what was analyzed
    results["analysis_summary"] = {
        "total_analyses_run": len([k for k, v in results.items() if not isinstance(v, dict) or "error" not in v]),
        "data_sources_used": {
            "uploaded_files": has_uploaded_data,
            "api_ga4_data": has_api_ga4_data,
            "api_ad_data": has_api_ad_data
        },
        "uploaded_files_processed": uploaded_data_available
    }
    
    return results

async def _fetch_ga4_api_data_with_property(user_id: str, start_date: str, end_date: str, property_id: str):
    """Fetch GA4 data from API with specific property ID"""
    try:
        # Get GA4 connector
        ga4_connector = None
        for name, connector in data_integrator_instance.connectors.items():
            if name == 'ga4':
                ga4_connector = connector
                break
        
        if not ga4_connector:
            return None
        
        # Override property ID for this request
        original_property_id = ga4_connector.property_id
        ga4_connector.property_id = property_id
        
        try:
            # Fetch GA4 data with comprehensive dimensions and metrics
            data = await ga4_connector.fetch_data(
                start_date=start_date,
                end_date=end_date,
                dimensions=[
                    'date', 'sessionDefaultChannelGrouping', 'sessionSourceMedium',
                    'sessionCampaignName', 'deviceCategory'
                ],
                metrics=[
                    'sessions', 'newUsers', 'screenPageViews', 'engagementRate',
                    'userEngagementDuration', 'keyEvents'
                ]
            )
            return data
        finally:
            # Restore original property ID
            ga4_connector.property_id = original_property_id
            
    except Exception as e:
        logger.error(f"GA4 API fetch error for property {property_id}: {e}")
        return None

async def _fetch_ga4_api_data(user_id: str, start_date: str, end_date: str):
    """Fetch GA4 data from API"""
    try:
        # Get GA4 connector
        ga4_connector = None
        for name, connector in data_integrator_instance.connectors.items():
            if name == 'ga4':
                ga4_connector = connector
                break
        
        if not ga4_connector:
            return None
        
        # Fetch GA4 data with comprehensive dimensions and metrics
        return await ga4_connector.fetch_data(
            start_date=start_date,
            end_date=end_date,
            dimensions=[
                'date', 'sessionDefaultChannelGrouping', 'sessionSourceMedium',
                'sessionCampaignName', 'deviceCategory'
            ],
            metrics=[
                'sessions', 'newUsers', 'screenPageViews', 'engagementRate',
                'userEngagementDuration', 'keyEvents'
            ]
        )
    except Exception as e:
        logger.error(f"GA4 API fetch error: {e}")
        return None

def _read_uploaded_file(file: UploadFile):
    """Read uploaded file using DataLoader"""
    try:
        content = file.file.read()
        return DataLoader.load_csv_from_bytes(content, file.filename)
    except Exception as e:
        logger.error(f"Error reading uploaded file {file.filename}: {e}")
        return None

@router.get("/comprehensive-insights/example")
async def comprehensive_insights_example():
    """Get usage examples for the comprehensive insights endpoint"""
    return {
        "description": "Comprehensive Marketing Insights - All analyses in one endpoint",
        "endpoint": "/comprehensive-insights",
        "method": "POST",
        
        "required_parameters": {
            "user_id": "Your user ID"
        },
        
        "optional_parameters": {
            "start_date": "Start date (YYYY-MM-DD) - defaults to 90 days ago",
            "end_date": "End date (YYYY-MM-DD) - defaults to today",
            "ga4_file": "GA4 CSV upload (optional)",
            "meta_file": "Meta Ads CSV upload (optional)", 
            "google_file": "Google Ads CSV upload (optional)",
            "use_api_data": "Set to true to use stored API credentials (default: false)",
            "min_spend_threshold": "Minimum spend for recommendations (default: 100)",
            "budget_increase_limit": "Max budget increase % (default: 50)",
            "data_sources": "Comma-separated API sources (default: 'meta_ads,google_ads')"
        },
        
        "usage_examples": {
            "files_only": """
curl -X POST "http://localhost:8000/comprehensive-insights" \\
  -F "user_id=123" \\
  -F "ga4_file=@analytics.csv" \\
  -F "meta_file=@meta_ads.csv"
            """.strip(),
            
            "api_only": """
curl -X POST "http://localhost:8000/comprehensive-insights" \\
  -F "user_id=123" \\
  -F "use_api_data=true"
            """.strip(),
            
            "with_custom_dates": """
curl -X POST "http://localhost:8000/comprehensive-insights" \\
  -F "user_id=123" \\
  -F "start_date=2024-01-01" \\
  -F "end_date=2024-01-31" \\
  -F "use_api_data=true"
            """.strip(),
            
            "mixed_sources": """
curl -X POST "http://localhost:8000/comprehensive-insights" \\
  -F "user_id=123" \\
  -F "meta_file=@meta_ads.csv" \\
  -F "use_api_data=true" \\
  -F "min_spend_threshold=200"
            """.strip()
        },
        
        "analyses_included": [
            "1. File consolidation (if files uploaded)",
            "2. Ad performance analysis",
            "3. Campaign comparison", 
            "4. User journey analysis (needs GA4 + ad data)",
            "5. Funnel optimization (needs GA4 + ad data)",
            "6. Recommendations engine",
            "7. Detailed action plan"
        ],
        
        "flexible_inputs": [
            "✅ Upload CSV files only",
            "✅ Use API credentials only", 
            "✅ Mix uploaded files + API data",
            "✅ Skip sources you don't have",
            "✅ Automatic fallbacks (API → uploaded files)"
        ]
    }