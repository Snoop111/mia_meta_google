from fastapi import APIRouter, HTTPException, Query
import logging
from typing import List, Optional
from routes.google_oauth import get_user_credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Google Analytics API"])

def get_analytics_client(user_id: str):
    """Get authenticated Google Analytics client"""
    credentials = get_user_credentials(user_id)
    return BetaAnalyticsDataClient(credentials=credentials)

@router.get("/properties")
async def get_properties(user_id: str):
    """Get all accessible GA4 properties for the authenticated user"""
    try:
        from google.analytics.admin import AnalyticsAdminServiceClient
        from google.analytics.admin_v1alpha.types import ListPropertiesRequest
        credentials = get_user_credentials(user_id)
        
        # Use the Google Analytics Admin API client
        client = AnalyticsAdminServiceClient(credentials=credentials)
        
        # First, list all accounts
        accounts_response = client.list_accounts()
        properties = []
        
        # For each account, list its properties
        for account in accounts_response:
            # Create the proper request object with filter
            request = ListPropertiesRequest(
                filter=f"parent:{account.name}"
            )
            properties_response = client.list_properties(request=request)
            
            for prop in properties_response:
                # Extract property ID from the resource name
                property_id = prop.name.split('/')[-1]
                account_id = account.name.split('/')[-1]
                
                properties.append({
                    'property_id': property_id,
                    'display_name': prop.display_name,
                    'name': prop.name,
                    'currency_code': prop.currency_code,
                    'time_zone': prop.time_zone,
                    'parent': prop.parent,
                    'account_id': account_id,
                    'account_display_name': account.display_name
                })
        
        return properties
        
    except Exception as e:
        logger.error(f"Error fetching GA4 properties: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch GA4 properties: {str(e)}")

@router.get("/properties/{property_id}/metrics")
async def get_property_metrics(
    property_id: str,
    user_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions")
):
    """Get metrics for a GA4 property"""
    try:
        client = get_analytics_client(user_id)
        
        # Define metrics to fetch
        metrics_list = [
            Metric(name="sessions"),
            Metric(name="newUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="userEngagementDuration"),
            Metric(name="keyEvents"),
            Metric(name="totalRevenue")
        ]
        
        # Define dimensions if provided
        dimensions_list = []
        if dimensions:
            for dim in dimensions.split(','):
                dimensions_list.append(Dimension(name=dim.strip()))
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=dimensions_list,
            metrics=metrics_list,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        response = client.run_report(request=request)
        
        # Process the response
        if not response.rows:
            return {
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "metrics": {
                    "sessions": 0,
                    "new_users": 0,
                    "page_views": 0,
                    "bounce_rate": 0.0,
                    "engagement_duration": 0.0,
                    "key_events": 0,
                    "key_event_rate": 0.0,
                    "revenue": 0.0
                },
                "dimensions": []
            }
        
        # Aggregate metrics
        total_sessions = 0
        total_new_users = 0
        total_page_views = 0
        total_bounce_rate = 0.0
        total_engagement_duration = 0.0
        total_key_events = 0
        total_revenue = 0.0
        
        dimension_data = []
        
        for row in response.rows:
            # Extract metric values (updated for new GA4 metrics)
            sessions = int(row.metric_values[0].value) if row.metric_values[0].value else 0
            new_users = int(row.metric_values[1].value) if row.metric_values[1].value else 0
            page_views = int(row.metric_values[2].value) if row.metric_values[2].value else 0
            bounce_rate = float(row.metric_values[3].value) if row.metric_values[3].value else 0.0
            engagement_duration = float(row.metric_values[4].value) if row.metric_values[4].value else 0.0
            key_events = int(row.metric_values[5].value) if row.metric_values[5].value else 0
            revenue = float(row.metric_values[6].value) if row.metric_values[6].value else 0.0
            
            total_sessions += sessions
            total_new_users += new_users
            total_page_views += page_views
            total_bounce_rate += bounce_rate
            total_engagement_duration += engagement_duration
            total_key_events += key_events
            total_revenue += revenue
            
            # Extract dimension values if present
            if dimensions_list and row.dimension_values:
                dimension_row = {}
                for i, dim_value in enumerate(row.dimension_values):
                    if i < len(dimensions_list):
                        dimension_row[dimensions_list[i].name] = dim_value.value
                dimension_row.update({
                    "sessions": sessions,
                    "new_users": new_users,
                    "page_views": page_views,
                    "bounce_rate": bounce_rate,
                    "engagement_duration": engagement_duration,
                    "key_events": key_events,
                    "revenue": revenue
                })
                dimension_data.append(dimension_row)
        
        # Calculate averages for rate metrics
        num_rows = len(response.rows)
        avg_bounce_rate = total_bounce_rate / num_rows if num_rows > 0 else 0.0
        avg_engagement_duration = total_engagement_duration / num_rows if num_rows > 0 else 0.0
        key_event_rate = (total_key_events / total_sessions * 100) if total_sessions > 0 else 0.0
        
        return {
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "metrics": {
                "sessions": total_sessions,
                "new_users": total_new_users,
                "page_views": total_page_views,
                "bounce_rate": avg_bounce_rate,
                "engagement_duration": avg_engagement_duration,
                "key_events": total_key_events,
                "key_event_rate": key_event_rate,
                "revenue": total_revenue
            },
            "dimensions": dimension_data
        }
        
    except Exception as e:
        logger.error(f"Error fetching GA4 metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch GA4 metrics: {str(e)}")

@router.get("/properties/{property_id}/top-pages")
async def get_top_pages(
    property_id: str,
    user_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, description="Number of top pages to return")
):
    """Get top pages for a GA4 property"""
    try:
        client = get_analytics_client(user_id)
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="newUsers")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit
        )
        
        response = client.run_report(request=request)
        
        top_pages = []
        for row in response.rows:
            page_path = row.dimension_values[0].value
            page_views = int(row.metric_values[0].value) if row.metric_values[0].value else 0
            unique_users = int(row.metric_values[1].value) if row.metric_values[1].value else 0
            
            top_pages.append({
                "page_path": page_path,
                "page_views": page_views,
                "unique_users": unique_users
            })
        
        return top_pages
        
    except Exception as e:
        logger.error(f"Error fetching top pages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top pages: {str(e)}")

@router.get("/properties/{property_id}/traffic-sources")
async def get_traffic_sources(
    property_id: str,
    user_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get traffic sources for a GA4 property"""
    try:
        client = get_analytics_client(user_id)
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium")
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="newUsers")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        response = client.run_report(request=request)
        
        traffic_sources = []
        for row in response.rows:
            source = row.dimension_values[0].value
            medium = row.dimension_values[1].value
            sessions = int(row.metric_values[0].value) if row.metric_values[0].value else 0
            users = int(row.metric_values[1].value) if row.metric_values[1].value else 0
            
            traffic_sources.append({
                "source": source,
                "medium": medium,
                "sessions": sessions,
                "users": users
            })
        
        return traffic_sources
        
    except Exception as e:
        logger.error(f"Error fetching traffic sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch traffic sources: {str(e)}")

@router.get("/properties/{property_id}/conversions")
async def get_conversions(
    property_id: str,
    user_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get conversion events for a GA4 property"""
    try:
        client = get_analytics_client(user_id)
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="eventName")],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="totalRevenue")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        response = client.run_report(request=request)
        
        conversions = []
        for row in response.rows:
            event_name = row.dimension_values[0].value
            event_count = int(row.metric_values[0].value) if row.metric_values[0].value else 0
            total_revenue = float(row.metric_values[1].value) if row.metric_values[1].value else 0.0
            
            # Only include events that might be conversions
            if any(keyword in event_name.lower() for keyword in ['purchase', 'conversion', 'complete', 'submit']):
                conversions.append({
                    "event_name": event_name,
                    "event_count": event_count,
                    "total_revenue": total_revenue
                })
        
        return conversions
        
    except Exception as e:
        logger.error(f"Error fetching conversions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversions: {str(e)}")

@router.get("/properties/{property_id}/realtime")
async def get_realtime_metrics(property_id: str, user_id: str):
    """Get real-time metrics for a GA4 property"""
    try:
        client = get_analytics_client(user_id)
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[],
            metrics=[
                Metric(name="activeUsers")
            ],
            date_ranges=[DateRange(start_date="today", end_date="today")]
        )
        
        response = client.run_report(request=request)
        
        active_users = 0
        if response.rows:
            active_users = int(response.rows[0].metric_values[0].value) if response.rows[0].metric_values[0].value else 0
        
        return {
            "active_users": active_users,
            "sessions_last_30_minutes": active_users  # Simplified for now
        }
        
    except Exception as e:
        logger.error(f"Error fetching real-time metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch real-time metrics: {str(e)}")