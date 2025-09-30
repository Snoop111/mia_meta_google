"""
Multi-Platform Insights Route
Allows users to select specific data sources and get both immediate insights and AutoML predictions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta

from routes.google_oauth import get_user_credentials
from routes.google_ads_api import get_google_ads_client
from routes.google_analytics_api import get_analytics_client
from credential_manager import credential_manager
from analytics.ad_performance import AdPerformanceAnalyzer
from analytics.recommendation_engine import RecommendationEngine
from clean_consolidator import CleanDataConsolidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/multi-platform", tags=["Multi-Platform Insights"])

class DataSelection(BaseModel):
    platform: str  # 'facebook', 'google_ads', 'google_analytics'
    account_id: Optional[str] = None
    property_id: Optional[str] = None
    campaign_ids: Optional[List[str]] = None
    date_range: Dict[str, str]  # {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}

class MultiPlatformInsightRequest(BaseModel):
    user_id: str
    selections: List[DataSelection]
    insight_types: List[str] = ['immediate', 'automl']  # Types of insights to generate
    analysis_options: Optional[Dict[str, Any]] = {
        'min_spend_threshold': 100,
        'budget_increase_limit': 50,
        'include_predictions': True,
        'prediction_target': 'conversions'  # or 'roas', 'cpa', etc.
    }

class ImmediateInsight(BaseModel):
    title: str
    description: str
    value: Any
    trend: Optional[str] = None  # 'up', 'down', 'stable'
    recommendation: Optional[str] = None

class MultiPlatformInsightResponse(BaseModel):
    success: bool
    user_id: str
    analysis_summary: Dict[str, Any]
    immediate_insights: List[ImmediateInsight]
    automl_predictions: Optional[Dict[str, Any]] = None
    platform_data_summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]

@router.post("/analyze", response_model=MultiPlatformInsightResponse)
async def analyze_multi_platform_data(request: MultiPlatformInsightRequest):
    """
    Analyze selected data from multiple platforms and provide both immediate insights and AutoML predictions
    """
    try:
        logger.info(f"Starting multi-platform analysis for user {request.user_id}")
        
        # Load user credentials
        credential_manager.load_user_connectors(request.user_id)
        
        # Fetch data from selected platforms
        platform_data = await _fetch_selected_platform_data(request.selections)
        
        # Generate immediate insights
        immediate_insights = []
        if 'immediate' in request.insight_types:
            immediate_insights = await _generate_immediate_insights(
                platform_data, request.analysis_options
            )
        
        # Generate AutoML predictions
        automl_predictions = None
        if 'automl' in request.insight_types:
            automl_predictions = await _generate_automl_predictions(
                platform_data, request.analysis_options
            )
        
        # Generate recommendations
        recommendations = await _generate_cross_platform_recommendations(
            platform_data, immediate_insights, request.analysis_options
        )
        
        # Create summary
        analysis_summary = _create_analysis_summary(platform_data, request.selections)
        platform_data_summary = _create_platform_data_summary(platform_data)
        
        return MultiPlatformInsightResponse(
            success=True,
            user_id=request.user_id,
            analysis_summary=analysis_summary,
            immediate_insights=immediate_insights,
            automl_predictions=automl_predictions,
            platform_data_summary=platform_data_summary,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Multi-platform analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def _fetch_selected_platform_data(selections: List[DataSelection]) -> Dict[str, pd.DataFrame]:
    """Fetch data from selected platforms concurrently"""
    platform_data = {}
    
    # Create tasks for concurrent data fetching
    tasks = []
    
    for selection in selections:
        if selection.platform == 'facebook':
            tasks.append(_fetch_facebook_data(selection))
        elif selection.platform == 'google_ads':
            tasks.append(_fetch_google_ads_data(selection))
        elif selection.platform == 'google_analytics':
            tasks.append(_fetch_google_analytics_data(selection))
    
    # Execute all tasks concurrently
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            selection = selections[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {selection.platform}: {result}")
                platform_data[selection.platform] = pd.DataFrame()
            else:
                platform_data[selection.platform] = result
    
    return platform_data

async def _fetch_facebook_data(selection: DataSelection) -> pd.DataFrame:
    """Fetch Facebook Ads data"""
    try:
        # Implementation will depend on your Meta Ads client
        # This is a placeholder - you would implement actual Meta API calls here
        # For now, return empty DataFrame
        logger.info("Facebook data fetching not yet implemented")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Facebook data fetch error: {e}")
        return pd.DataFrame()

async def _fetch_google_ads_data(selection: DataSelection) -> pd.DataFrame:
    """Fetch Google Ads data"""
    try:
        client = get_google_ads_client()
        
        # Build query based on selection
        query_parts = [
            "SELECT",
            "  campaign.id,",
            "  campaign.name,",
            "  metrics.impressions,",
            "  metrics.clicks,",
            "  metrics.cost_micros,",
            "  metrics.conversions,",
            "  metrics.conversions_value,",
            "  segments.date",
            "FROM campaign",
            f"WHERE segments.date BETWEEN '{selection.date_range['start']}' AND '{selection.date_range['end']}'"
        ]
        
        if selection.campaign_ids:
            campaign_filter = "','".join(selection.campaign_ids)
            query_parts.append(f"AND campaign.id IN ('{campaign_filter}')")
        
        query = " ".join(query_parts)
        
        # Execute query and convert to DataFrame  
        ga_service = client.get_service("GoogleAdsService")
        search_request = client.get_type("SearchGoogleAdsRequest")
        search_request.customer_id = selection.account_id.replace('-', '')
        search_request.query = query
        response = ga_service.search(request=search_request)
        
        rows = []
        for row in response:
            rows.append({
                'date': row.segments.date,
                'campaign_id': row.campaign.id,
                'campaign_name': row.campaign.name,
                'impressions': row.metrics.impressions,
                'clicks': row.metrics.clicks,
                'cost': row.metrics.cost_micros / 1_000_000,
                'conversions': row.metrics.conversions,
                'conversion_value': row.metrics.conversions_value
            })
        
        return pd.DataFrame(rows)
        
    except Exception as e:
        logger.error(f"Google Ads data fetch error: {e}")
        return pd.DataFrame()

async def _fetch_google_analytics_data(selection: DataSelection) -> pd.DataFrame:
    """Fetch Google Analytics data"""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import RunReportRequest, Dimension, Metric, DateRange
        
        client = get_analytics_client()
        
        request = RunReportRequest(
            property=f"properties/{selection.property_id}",
            dimensions=[
                Dimension(name="date"),
                Dimension(name="sessionDefaultChannelGrouping"),
                Dimension(name="sessionSourceMedium")
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="conversions"),
                Metric(name="totalRevenue")
            ],
            date_ranges=[DateRange(
                start_date=selection.date_range['start'], 
                end_date=selection.date_range['end']
            )]
        )
        
        response = client.run_report(request=request)
        
        rows = []
        for row in response.rows:
            rows.append({
                'date': row.dimension_values[0].value,
                'channel': row.dimension_values[1].value,
                'source_medium': row.dimension_values[2].value,
                'sessions': int(row.metric_values[0].value) if row.metric_values[0].value else 0,
                'users': int(row.metric_values[1].value) if row.metric_values[1].value else 0,
                'pageviews': int(row.metric_values[2].value) if row.metric_values[2].value else 0,
                'conversions': int(row.metric_values[3].value) if row.metric_values[3].value else 0,
                'revenue': float(row.metric_values[4].value) if row.metric_values[4].value else 0.0
            })
        
        return pd.DataFrame(rows)
        
    except Exception as e:
        logger.error(f"Google Analytics data fetch error: {e}")
        return pd.DataFrame()

async def _generate_immediate_insights(
    platform_data: Dict[str, pd.DataFrame], 
    options: Dict[str, Any]
) -> List[ImmediateInsight]:
    """Generate immediate insights from the platform data"""
    insights = []
    
    # Cross-platform performance summary
    total_spend = 0
    total_conversions = 0
    total_revenue = 0
    
    for platform, df in platform_data.items():
        if df.empty:
            continue
            
        if platform in ['facebook', 'google_ads']:
            if 'cost' in df.columns:
                total_spend += df['cost'].sum()
            if 'conversions' in df.columns:
                total_conversions += df['conversions'].sum()
            if 'conversion_value' in df.columns:
                total_revenue += df['conversion_value'].sum()
        elif platform == 'google_analytics':
            if 'revenue' in df.columns:
                total_revenue += df['revenue'].sum()
            if 'conversions' in df.columns:
                total_conversions += df['conversions'].sum()
    
    # Generate insights
    if total_spend > 0:
        roas = total_revenue / total_spend if total_spend > 0 else 0
        cpa = total_spend / total_conversions if total_conversions > 0 else 0
        
        insights.extend([
            ImmediateInsight(
                title="Total Ad Spend",
                description="Combined spending across all selected platforms",
                value=f"${total_spend:,.2f}",
                recommendation="Compare with revenue to assess profitability"
            ),
            ImmediateInsight(
                title="Return on Ad Spend (ROAS)",
                description="Revenue generated per dollar spent on advertising",
                value=f"{roas:.2f}x",
                trend="up" if roas > 3 else "down" if roas < 2 else "stable",
                recommendation="Aim for ROAS > 3x for profitable campaigns"
            ),
            ImmediateInsight(
                title="Cost Per Acquisition (CPA)",
                description="Average cost to acquire one conversion",
                value=f"${cpa:.2f}",
                trend="down" if cpa < 50 else "up" if cpa > 100 else "stable",
                recommendation="Lower CPA indicates more efficient campaigns"
            )
        ])
    
    # Platform-specific insights
    for platform, df in platform_data.items():
        platform_insights = _generate_platform_specific_insights(platform, df)
        insights.extend(platform_insights)
    
    return insights

def _generate_platform_specific_insights(platform: str, df: pd.DataFrame) -> List[ImmediateInsight]:
    """Generate insights specific to each platform"""
    insights = []
    
    if df.empty:
        return insights
    
    if platform == 'google_ads':
        if 'clicks' in df.columns and 'impressions' in df.columns:
            total_clicks = df['clicks'].sum()
            total_impressions = df['impressions'].sum()
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            
            insights.append(ImmediateInsight(
                title="Google Ads Click-Through Rate",
                description="Percentage of impressions that resulted in clicks",
                value=f"{ctr:.2f}%",
                trend="up" if ctr > 3 else "down" if ctr < 1 else "stable",
                recommendation="CTR > 3% indicates engaging ad creative"
            ))
    
    elif platform == 'google_analytics':
        if 'sessions' in df.columns and 'users' in df.columns:
            total_sessions = df['sessions'].sum()
            total_users = df['users'].sum()
            sessions_per_user = total_sessions / total_users if total_users > 0 else 0
            
            insights.append(ImmediateInsight(
                title="Average Sessions per User",
                description="How often users return to your website",
                value=f"{sessions_per_user:.2f}",
                trend="up" if sessions_per_user > 1.5 else "down" if sessions_per_user < 1.2 else "stable",
                recommendation="Higher values indicate good user engagement"
            ))
    
    return insights

async def _generate_automl_predictions(
    platform_data: Dict[str, pd.DataFrame], 
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate AutoML predictions using the consolidated data"""
    try:
        # Combine all platform data
        consolidated_df = _consolidate_platform_data(platform_data)
        
        if consolidated_df.empty:
            return {"error": "No data available for AutoML predictions"}
        
        # Use existing AutoML functionality
        from autogluon.tabular import TabularPredictor
        
        # Prepare data for AutoML
        target_column = options.get('prediction_target', 'conversions')
        if target_column not in consolidated_df.columns:
            # Default to a suitable target
            if 'conversions' in consolidated_df.columns:
                target_column = 'conversions'
            elif 'revenue' in consolidated_df.columns:
                target_column = 'revenue'
            else:
                return {"error": f"Target column '{target_column}' not found in data"}
        
        # Split data for training
        train_data = consolidated_df.sample(frac=0.8, random_state=42)
        test_data = consolidated_df.drop(train_data.index)
        
        # Train AutoML model
        predictor = TabularPredictor(label=target_column, problem_type='regression')
        predictor.fit(train_data, time_limit=60)  # Quick training
        
        # Generate predictions
        predictions = predictor.predict(test_data)
        
        # Calculate performance metrics
        from sklearn.metrics import mean_absolute_error, r2_score
        mae = mean_absolute_error(test_data[target_column], predictions)
        r2 = r2_score(test_data[target_column], predictions)
        
        return {
            "model_performance": {
                "mean_absolute_error": mae,
                "r2_score": r2,
                "target_column": target_column
            },
            "sample_predictions": predictions[:10].tolist(),
            "feature_importance": predictor.feature_importance(test_data).to_dict(),
            "model_summary": predictor.model_best
        }
        
    except Exception as e:
        logger.error(f"AutoML prediction error: {e}")
        return {"error": f"AutoML prediction failed: {str(e)}"}

def _consolidate_platform_data(platform_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidate data from multiple platforms into a single DataFrame"""
    consolidated_dfs = []
    
    for platform, df in platform_data.items():
        if df.empty:
            continue
        
        # Add platform identifier
        df_copy = df.copy()
        df_copy['platform'] = platform
        
        # Standardize column names
        if platform in ['facebook', 'google_ads']:
            # Standardize ad platform columns
            column_mapping = {
                'cost': 'spend',
                'conversion_value': 'revenue'
            }
            df_copy = df_copy.rename(columns=column_mapping)
        
        consolidated_dfs.append(df_copy)
    
    if not consolidated_dfs:
        return pd.DataFrame()
    
    # Find common columns for concatenation
    common_cols = set(consolidated_dfs[0].columns)
    for df in consolidated_dfs[1:]:
        common_cols = common_cols.intersection(set(df.columns))
    
    # Concatenate DataFrames with common columns
    if common_cols:
        consolidated = pd.concat([df[list(common_cols)] for df in consolidated_dfs], 
                               ignore_index=True)
    else:
        # If no common columns, create a basic consolidated view
        consolidated = pd.concat(consolidated_dfs, ignore_index=True, sort=False)
    
    return consolidated

async def _generate_cross_platform_recommendations(
    platform_data: Dict[str, pd.DataFrame],
    immediate_insights: List[ImmediateInsight],
    options: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate recommendations based on cross-platform data analysis"""
    recommendations = []
    
    # Analyze performance across platforms
    platform_performance = {}
    
    for platform, df in platform_data.items():
        if df.empty:
            continue
        
        if platform in ['facebook', 'google_ads']:
            if 'cost' in df.columns and 'conversions' in df.columns:
                total_spend = df['cost'].sum()
                total_conversions = df['conversions'].sum()
                cpa = total_spend / total_conversions if total_conversions > 0 else float('inf')
                
                platform_performance[platform] = {
                    'spend': total_spend,
                    'conversions': total_conversions,
                    'cpa': cpa
                }
    
    # Generate recommendations based on performance comparison
    if len(platform_performance) > 1:
        best_platform = min(platform_performance.items(), key=lambda x: x[1]['cpa'])
        worst_platform = max(platform_performance.items(), key=lambda x: x[1]['cpa'])
        
        recommendations.append({
            "category": "Budget Optimization",
            "title": f"Shift Budget to {best_platform[0].title()}",
            "description": f"{best_platform[0].title()} has the lowest CPA (${best_platform[1]['cpa']:.2f}) compared to {worst_platform[0].title()} (${worst_platform[1]['cpa']:.2f})",
            "priority": "high",
            "potential_impact": "Could reduce overall CPA by 15-25%",
            "action_items": [
                f"Increase budget allocation for {best_platform[0].title()} campaigns",
                f"Review and optimize {worst_platform[0].title()} targeting and creative",
                "Monitor performance changes over 2-week periods"
            ]
        })
    
    # Add general recommendations based on insights
    for insight in immediate_insights:
        if insight.trend == "down" and "ROAS" in insight.title:
            recommendations.append({
                "category": "Performance Improvement",
                "title": "Improve Return on Ad Spend",
                "description": f"Current ROAS of {insight.value} is below optimal levels",
                "priority": "high",
                "potential_impact": "Could increase profitability by 20-30%",
                "action_items": [
                    "Review and optimize underperforming campaigns",
                    "Test new ad creative and messaging",
                    "Refine audience targeting"
                ]
            })
    
    return recommendations

def _create_analysis_summary(
    platform_data: Dict[str, pd.DataFrame], 
    selections: List[DataSelection]
) -> Dict[str, Any]:
    """Create a summary of the analysis performed"""
    return {
        "platforms_analyzed": list(platform_data.keys()),
        "date_ranges": [sel.date_range for sel in selections],
        "total_data_points": sum(len(df) for df in platform_data.values()),
        "analysis_timestamp": datetime.now().isoformat(),
        "data_availability": {
            platform: not df.empty for platform, df in platform_data.items()
        }
    }

def _create_platform_data_summary(platform_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Create a summary of the data from each platform"""
    summary = {}
    
    for platform, df in platform_data.items():
        if df.empty:
            summary[platform] = {"status": "no_data", "records": 0}
        else:
            summary[platform] = {
                "status": "data_available",
                "records": len(df),
                "columns": list(df.columns),
                "date_range": {
                    "start": df['date'].min() if 'date' in df.columns else "unknown",
                    "end": df['date'].max() if 'date' in df.columns else "unknown"
                }
            }
    
    return summary

# Utility endpoints
@router.get("/available-platforms")
async def get_available_platforms():
    """Get list of supported platforms and their requirements"""
    return {
        "platforms": [
            {
                "id": "facebook",
                "name": "Facebook Ads",
                "required_fields": ["account_id", "date_range"],
                "optional_fields": ["campaign_ids"]
            },
            {
                "id": "google_ads", 
                "name": "Google Ads",
                "required_fields": ["account_id", "date_range"],
                "optional_fields": ["campaign_ids"]
            },
            {
                "id": "google_analytics",
                "name": "Google Analytics",
                "required_fields": ["property_id", "date_range"],
                "optional_fields": []
            }
        ],
        "insight_types": ["immediate", "automl"],
        "analysis_options": {
            "min_spend_threshold": "Minimum spend for campaign recommendations (default: 100)",
            "budget_increase_limit": "Maximum budget increase percentage (default: 50)",
            "prediction_target": "Target variable for AutoML predictions (conversions, revenue, etc.)"
        }
    }

@router.get("/example-request")
async def get_example_request():
    """Get an example request for the multi-platform analysis"""
    return {
        "example_request": {
            "user_id": "user123",
            "selections": [
                {
                    "platform": "google_ads",
                    "account_id": "123-456-7890",
                    "campaign_ids": ["campaign1", "campaign2"],
                    "date_range": {
                        "start": "2024-01-01",
                        "end": "2024-01-31"
                    }
                },
                {
                    "platform": "google_analytics",
                    "property_id": "12345678",
                    "date_range": {
                        "start": "2024-01-01", 
                        "end": "2024-01-31"
                    }
                }
            ],
            "insight_types": ["immediate", "automl"],
            "analysis_options": {
                "min_spend_threshold": 150,
                "budget_increase_limit": 30,
                "prediction_target": "conversions"
            }
        }
    }