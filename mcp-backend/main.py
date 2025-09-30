from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
from fastmcp import FastMCP
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()
from routes.data_sources import router as data_sources_router
from routes.eda import router as eda_router
# from routes.analyze import router as analyze_router  # Removed - requires AutoGluon
from routes.ad_insights import router as ad_insights_router
from routes.website_analytics import router as website_analytics_router
from routes.clean_insights import router as clean_insights_router
from routes.clean_website_analytics import router as clean_website_router
from routes.clean_ad_insights import router as clean_ad_router
from routes.comprehensive_insights import router as comprehensive_router
from routes.google_oauth import router as google_oauth_router
from routes.google_ads_api import router as google_ads_router
from routes.meta_oauth import router as meta_oauth_router
from routes.meta_ads_api import router as meta_ads_router
from routes.google_analytics_api import router as google_analytics_router
# from routes.multi_platform_insights import router as multi_platform_router  # Removed - requires AutoGluon
from database import credential_storage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Will be redefined later with MCP lifespan
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000","*"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database and restore any existing connectors"""
    logger.info("Starting up application...")
    
    # Initialize database (tables will be created if they don't exist)
    credential_storage._init_database()
    logger.info("Database initialized")
    
    # Note: Connectors will be loaded on-demand when users make requests
    # This prevents issues with invalid credentials on startup
    logger.info("Application startup complete")

# Register routers
app.include_router(data_sources_router)
app.include_router(eda_router)
# app.include_router(analyze_router)  # Removed - requires AutoGluon
app.include_router(ad_insights_router)
app.include_router(website_analytics_router)
app.include_router(clean_insights_router)
app.include_router(clean_website_router)
app.include_router(clean_ad_router)
app.include_router(comprehensive_router)
app.include_router(google_oauth_router)
app.include_router(google_ads_router)
app.include_router(meta_oauth_router)
app.include_router(meta_ads_router)
app.include_router(google_analytics_router)
# app.include_router(multi_platform_router)  # Removed - requires AutoGluon

# 1. Create MCP server with selective tools (not from FastAPI)
mcp = FastMCP("Marketing Analytics MCP")

# 2. Create the MCP's ASGI app
mcp_app = mcp.http_app(path='/mcp')

# 3. Recreate FastAPI app with MCP lifespan and mount
app = FastAPI(title="Marketing Analytics API", lifespan=mcp_app.lifespan)

# Re-add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000","*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Re-register all routers
app.include_router(data_sources_router)
app.include_router(eda_router)
# app.include_router(analyze_router)  # Removed - requires AutoGluon
app.include_router(ad_insights_router)
app.include_router(website_analytics_router)
app.include_router(clean_insights_router)
app.include_router(clean_website_router)
app.include_router(clean_ad_router)
app.include_router(comprehensive_router)
app.include_router(google_oauth_router)
app.include_router(google_ads_router)
app.include_router(meta_oauth_router)
app.include_router(meta_ads_router)
app.include_router(google_analytics_router)
# app.include_router(multi_platform_router)  # Removed - requires AutoGluon

# Mount MCP
app.mount("/llm", mcp_app)

# Health check endpoint for Docker deployments
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and container orchestration"""
    try:
        # Check database connection
        from database import credential_storage
        credential_storage._init_database()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {
                "database": "operational",
                "api": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# MCP Tools
@mcp.tool()
async def get_comprehensive_insights(
    user_id: str,
    data_selections: List[Dict[str, Any]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_spend_threshold: float = 100,
    budget_increase_limit: float = 50
) -> Dict[str, Any]:
    """
    Get comprehensive marketing insights from multiple data sources.
    
    Args:
        user_id: User identifier for credential lookup
        data_selections: List of data source selections with platform, account_id, property_id, etc.
        start_date: Analysis start date (YYYY-MM-DD format). Defaults to 30 days ago.
        end_date: Analysis end date (YYYY-MM-DD format). Defaults to today.
        min_spend_threshold: Minimum spend threshold for analysis (default: 100)
        budget_increase_limit: Maximum budget increase percentage (default: 50)
    
    Returns:
        Comprehensive insights including individual platform insights and combined analysis
    
    Example data_selections:
    [
        {
            "platform": "google_analytics",
            "property_id": "123456789",
            "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
        },
        {
            "platform": "google_ads", 
            "account_id": "987-654-3210",
            "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
        }
    ]
    """
    try:
        logger.info(f"MCP: Getting comprehensive insights for user {user_id}")
        
        from routes.comprehensive_insights import ComprehensiveInsightsRequest, comprehensive_insights, DataSelection
        
        # Convert data_selections to proper format
        selections = []
        for selection in data_selections:
            selections.append(DataSelection(**selection))
        
        # Create request object
        request = ComprehensiveInsightsRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            min_spend_threshold=min_spend_threshold,
            budget_increase_limit=budget_increase_limit,
            data_selections=selections
        )
        
        # Call the existing endpoint
        result = await comprehensive_insights(request)
        
        logger.info(f"MCP: Successfully generated insights for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"MCP: Error getting comprehensive insights: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

def _extract_all_row_data(row) -> dict:
    """
    Dynamically extract all available data from a Google Ads API row.
    This handles custom queries where we don't know the structure ahead of time.
    """
    def extract_value(obj, path=""):
        """Recursively extract values from Google Ads API objects"""
        if obj is None:
            return None
            
        # Handle primitive types
        if isinstance(obj, (str, int, float, bool)):
            return obj
            
        # Handle enums
        if hasattr(obj, 'name'):
            return obj.name
            
        # Handle repeated fields (lists)
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                items = list(obj)
                if not items:
                    return []
                # For lists of primitives
                if isinstance(items[0], (str, int, float, bool)):
                    return items
                # For lists of objects, extract recursively
                return [extract_value(item, path) for item in items]
            except:
                pass
        
        # Handle objects with attributes
        result = {}
        try:
            # Get all non-private attributes
            attrs = [attr for attr in dir(obj) if not attr.startswith('_') and not callable(getattr(obj, attr, None))]
            for attr in attrs:
                try:
                    value = getattr(obj, attr)
                    if value is not None:
                        extracted = extract_value(value, f"{path}.{attr}" if path else attr)
                        if extracted is not None:
                            result[attr] = extracted
                except:
                    continue
        except:
            pass
            
        return result if result else str(obj)
    
    row_data = {}
    
    # Extract from all major sections of a Google Ads row
    sections = [
        'campaign', 'ad_group', 'ad_group_ad', 'ad_group_criterion', 
        'keyword_view', 'geographic_view', 'asset', 'metrics', 'segments'
    ]
    
    for section in sections:
        if hasattr(row, section):
            section_obj = getattr(row, section)
            extracted = extract_value(section_obj, section)
            if extracted:
                if isinstance(extracted, dict):
                    # Flatten the structure for easier access
                    for key, value in extracted.items():
                        row_data[f"{section}_{key}"] = value
                else:
                    row_data[section] = extracted
    
    # Also try to extract any other attributes
    try:
        attrs = [attr for attr in dir(row) if not attr.startswith('_') and not callable(getattr(row, attr, None))]
        for attr in attrs:
            if attr not in sections:  # Don't duplicate
                try:
                    value = getattr(row, attr)
                    extracted = extract_value(value, attr)
                    if extracted:
                        row_data[attr] = extracted
                except:
                    continue
    except:
        pass
    
    return row_data

def _extract_selected_fields(row, query: str) -> dict:
    """
    Extract only the fields that were selected in the custom query.
    This parses the SELECT statement to identify requested fields.
    """
    import re
    
    row_data = {}
    
    try:
        # Parse SELECT fields from query
        # Match SELECT ... FROM pattern
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            # Fallback to extracting all data if parsing fails
            return _extract_all_row_data(row)
        
        fields_str = select_match.group(1).strip()
        
        # Split by comma and clean up field names
        fields = []
        for field in fields_str.split(','):
            field = field.strip()
            # Remove any alias (AS alias_name)
            field = re.sub(r'\s+AS\s+\w+', '', field, flags=re.IGNORECASE)
            fields.append(field.strip())
        
        # Extract each field from the row
        for field in fields:
            try:
                value = _get_field_value(row, field)
                if value is not None:
                    # Use a clean field name for the output
                    clean_name = field.replace('.', '_')
                    row_data[clean_name] = value
            except Exception as e:
                logger.debug(f"Could not extract field {field}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error parsing custom query fields: {e}")
        # Fallback to extracting all data if parsing fails
        return _extract_all_row_data(row)
    
    return row_data

def _get_field_value(row, field_path: str):
    """
    Get a specific field value from a Google Ads API row using dot notation.
    e.g., 'metrics.impressions' or 'asset.callout_asset.callout_text'
    """
    try:
        # Split the field path by dots
        path_parts = field_path.split('.')
        
        # Start with the row object
        current_obj = row
        
        # Navigate through the path
        for part in path_parts:
            if hasattr(current_obj, part):
                current_obj = getattr(current_obj, part)
            else:
                return None
        
        # Handle different types of values
        if current_obj is None:
            return None
        elif isinstance(current_obj, (str, int, float, bool)):
            return current_obj
        elif hasattr(current_obj, 'name'):  # Enum values
            return current_obj.name
        elif hasattr(current_obj, 'value'):  # Some API objects have .value
            return current_obj.value
        else:
            return str(current_obj)
            
    except Exception as e:
        logger.debug(f"Error getting field value for {field_path}: {e}")
        return None

@mcp.tool()
async def query_google_ads_data(
    user_id: str,
    customer_id: Optional[str] = None,
    query_type: str = "campaigns",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    custom_query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query Google Ads data directly for specific insights like demographics, campaign performance, etc.
    
    Use this tool when someone asks about:
    - Campaign performance by demographics (gender, age)
    - Ad performance metrics
    - Keyword performance
    - Geographic performance
    - Device performance
    - Time-based performance
    
    Args:
        user_id: User identifier for credential lookup
        customer_id: Google Ads customer ID (optional, will use first available if not provided)
        query_type: Type of query - "campaigns", "demographics", "keywords", "locations", "devices", "custom"
        start_date: Start date (YYYY-MM-DD format). Defaults to 30 days ago.
        end_date: End date (YYYY-MM-DD format). Defaults to today.
        dimensions: List of dimensions to include (e.g., ["gender", "age_range"])
        metrics: List of metrics to include (e.g., ["impressions", "clicks", "cost_micros"])
        custom_query: Custom Google Ads query string for advanced queries
    
    Returns:
        Google Ads data formatted for easy analysis
    
    Example usage for "Which gender viewed the campaign the most":
    - query_type: "demographics"
    - dimensions: ["gender"]
    - metrics: ["impressions", "clicks"]
    """
    try:
        logger.info(f"MCP: Querying Google Ads data for user {user_id}")
        
        from routes.google_ads_api import get_google_ads_client
        from google.ads.googleads.errors import GoogleAdsException
        from datetime import datetime, timedelta
        
        # Get client
        client = get_google_ads_client(user_id)
        ga_service = client.get_service("GoogleAdsService")
        
        # Get customer ID if not provided
        if not customer_id:
            customer_service = client.get_service("CustomerService")
            request = client.get_type("ListAccessibleCustomersRequest")
            response = customer_service.list_accessible_customers(request=request)
            if response.resource_names:
                customer_id = response.resource_names[0].split("/")[-1]
            else:
                return {"success": False, "error": "No accessible Google Ads accounts found"}
        
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Build query based on query_type
        if custom_query:
            query = custom_query
        elif query_type == "demographics":
            # Perfect for gender/age questions
            dim_list = dimensions or ["gender", "age_range"]
            met_list = metrics or ["impressions", "clicks", "cost_micros", "conversions"]
            
            query = f"""
                SELECT 
                    {', '.join([f"ad_group_criterion.{dim}" for dim in dim_list])},
                    {', '.join([f"metrics.{met}" for met in met_list])},
                    segments.date
                FROM gender_view 
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                AND ad_group_criterion.gender.type != 'UNSPECIFIED'
                ORDER BY metrics.impressions DESC
            """
            
        elif query_type == "campaigns":
            dim_list = dimensions or []
            met_list = metrics or ["impressions", "clicks", "cost_micros", "conversions", "ctr"]
            
            fields = ["campaign.id", "campaign.name", "campaign.status"]
            fields.extend([f"metrics.{met}" for met in met_list])
            if dim_list:
                fields.extend([f"segments.{dim}" for dim in dim_list])
            
            query = f"""
                SELECT {', '.join(fields)}
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                AND campaign.status != 'REMOVED'
                ORDER BY metrics.impressions DESC
            """
            
        elif query_type == "keywords":
            met_list = metrics or ["impressions", "clicks", "cost_micros", "conversions", "ctr"]
            
            query = f"""
                SELECT 
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    campaign.name,
                    ad_group.name,
                    {', '.join([f"metrics.{met}" for met in met_list])}
                FROM keyword_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                AND ad_group_criterion.status != 'REMOVED'
                ORDER BY metrics.impressions DESC
                LIMIT 100
            """
            
        elif query_type == "locations":
            met_list = metrics or ["impressions", "clicks", "cost_micros"]
            
            query = f"""
                SELECT 
                    geographic_view.country_criterion_id,
                    geographic_view.location_type,
                    {', '.join([f"metrics.{met}" for met in met_list])}
                FROM geographic_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
                LIMIT 50
            """
            
        elif query_type == "devices":
            met_list = metrics or ["impressions", "clicks", "cost_micros", "conversions"]
            
            query = f"""
                SELECT 
                    segments.device,
                    {', '.join([f"metrics.{met}" for met in met_list])}
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
            """
            
        else:
            return {"success": False, "error": f"Unknown query_type: {query_type}"}
        
        # Execute query
        logger.info(f"Executing Google Ads query: {query}")
        response = ga_service.search(customer_id=customer_id, query=query)
        
        # Process results
        results = []
        for row in response:
            row_data = {}
            
            # For custom queries, extract only selected fields
            if custom_query:
                row_data = _extract_selected_fields(row, custom_query)
            else:
                # Extract based on query type for predefined queries
                if query_type == "demographics":
                    if hasattr(row, 'ad_group_criterion') and hasattr(row.ad_group_criterion, 'gender'):
                        row_data['gender'] = row.ad_group_criterion.gender.type.name if row.ad_group_criterion.gender.type else 'UNKNOWN'
                    if hasattr(row, 'ad_group_criterion') and hasattr(row.ad_group_criterion, 'age_range'):
                        row_data['age_range'] = row.ad_group_criterion.age_range.type.name if row.ad_group_criterion.age_range.type else 'UNKNOWN'
                elif query_type == "campaigns":
                    if hasattr(row, 'campaign'):
                        row_data['campaign_id'] = str(row.campaign.id)
                        row_data['campaign_name'] = row.campaign.name
                        row_data['campaign_status'] = row.campaign.status.name
                elif query_type == "keywords":
                    if hasattr(row, 'ad_group_criterion') and hasattr(row.ad_group_criterion, 'keyword'):
                        row_data['keyword'] = row.ad_group_criterion.keyword.text
                        row_data['match_type'] = row.ad_group_criterion.keyword.match_type.name
                    if hasattr(row, 'campaign'):
                        row_data['campaign_name'] = row.campaign.name
                    if hasattr(row, 'ad_group'):
                        row_data['ad_group_name'] = row.ad_group.name
                elif query_type == "devices":
                    if hasattr(row, 'segments'):
                        row_data['device'] = row.segments.device.name if row.segments.device else 'UNKNOWN'
                
                # Extract standard metrics for predefined queries
                if hasattr(row, 'metrics'):
                    m = row.metrics
                    row_data['impressions'] = int(m.impressions or 0)
                    row_data['clicks'] = int(m.clicks or 0)
                    row_data['cost'] = float(m.cost_micros or 0) / 1_000_000
                    row_data['conversions'] = float(m.conversions or 0)
                    row_data['ctr'] = float(m.ctr or 0)
                    if hasattr(m, 'average_cpc'):
                        row_data['average_cpc'] = float(m.average_cpc or 0) / 1_000_000
                    if hasattr(m, 'cost_per_conversion'):
                        row_data['cost_per_conversion'] = float(m.cost_per_conversion or 0) / 1_000_000
                
                # Extract date if available
                if hasattr(row, 'segments') and hasattr(row.segments, 'date'):
                    row_data['date'] = row.segments.date
            
            results.append(row_data)
        
        return {
            "success": True,
            "query_type": query_type,
            "customer_id": customer_id,
            "date_range": {"start": start_date, "end": end_date},
            "total_rows": len(results),
            "data": results,
            "query_executed": query
        }
        
    except GoogleAdsException as ex:
        logger.error(f"MCP: Google Ads API error: {ex}")
        return {"success": False, "error": f"Google Ads API error: {str(ex)}"}
    except Exception as e:
        logger.error(f"MCP: Error querying Google Ads data: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def query_ga4_data(
    user_id: str,
    property_id: Optional[str] = None,
    query_type: str = "overview",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    filters: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Query Google Analytics 4 data directly for specific insights about website/app performance.
    
    Use this tool when someone asks about:
    - Website traffic and user behavior
    - Content performance (pages, events)
    - Traffic sources and acquisition
    - User demographics and interests
    - Conversion tracking
    - Real-time data
    
    Args:
        user_id: User identifier for credential lookup
        property_id: GA4 property ID (optional, will use first available if not provided)
        query_type: Type of query - "overview", "demographics", "pages", "sources", "events", "conversions", "realtime"
        start_date: Start date (YYYY-MM-DD format). Defaults to 30 days ago.
        end_date: End date (YYYY-MM-DD format). Defaults to today.
        dimensions: List of GA4 dimensions (e.g., ["userGender", "userAgeBracket"])
        metrics: List of GA4 metrics (e.g., ["sessions", "screenPageViews"])
        filters: Optional filters to apply to the data
    
    Returns:
        GA4 data formatted for easy analysis
    
    Example usage for website demographics:
    - query_type: "demographics" 
    - dimensions: ["userGender", "userAgeBracket"]
    - metrics: ["sessions", "newUsers"]
    """
    try:
        logger.info(f"MCP: Querying GA4 data for user {user_id}")
        
        from routes.google_analytics_api import get_analytics_client
        from routes.google_oauth import get_user_credentials
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange, FilterExpression, Filter
        )
        from google.analytics.admin import AnalyticsAdminServiceClient
        from datetime import datetime, timedelta
        
        # Get GA4 property if not provided
        if not property_id:
            credentials = get_user_credentials(user_id)
            admin_client = AnalyticsAdminServiceClient(credentials=credentials)
            accounts_response = admin_client.list_accounts()
            
            for account in accounts_response:
                from google.analytics.admin_v1alpha.types import ListPropertiesRequest
                request = ListPropertiesRequest(filter=f"parent:{account.name}")
                properties_response = admin_client.list_properties(request=request)
                
                for prop in properties_response:
                    property_id = prop.name.split('/')[-1]
                    break
                if property_id:
                    break
            
            if not property_id:
                return {"success": False, "error": "No accessible GA4 properties found"}
        
        # Set default date range
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get client
        client = get_analytics_client(user_id)
        
        # Build request based on query_type
        if query_type == "demographics":
            dim_list = dimensions or ["userGender", "userAgeBracket"]
            met_list = metrics or ["sessions", "newUsers", "screenPageViews"]
        elif query_type == "overview":
            dim_list = dimensions or []
            met_list = metrics or ["sessions", "newUsers", "screenPageViews", "bounceRate", "userEngagementDuration"]
        elif query_type == "pages":
            dim_list = dimensions or ["pagePath", "pageTitle"]
            met_list = metrics or ["screenPageViews", "newUsers", "userEngagementDuration"]
        elif query_type == "sources":
            dim_list = dimensions or ["sessionSource", "sessionMedium", "sessionCampaignName"]
            met_list = metrics or ["sessions", "newUsers", "conversions"]
        elif query_type == "events":
            dim_list = dimensions or ["eventName"]
            met_list = metrics or ["eventCount", "newUsers"]
        elif query_type == "conversions":
            dim_list = dimensions or ["eventName"]
            met_list = metrics or ["keyEvents", "totalRevenue"]
        elif query_type == "realtime":
            # For real-time, use different date range
            start_date = "today"
            end_date = "today"
            dim_list = dimensions or []
            met_list = metrics or ["activeUsers"]
        else:
            dim_list = dimensions or []
            met_list = metrics or ["sessions", "newUsers"]
        
        # Create dimension and metric objects
        dimensions_objs = [Dimension(name=dim) for dim in dim_list] if dim_list else []
        metrics_objs = [Metric(name=met) for met in met_list] if met_list else []
        
        # Build request
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=dimensions_objs,
            metrics=metrics_objs,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        # Add filters if provided
        if filters:
            # This is a simplified filter implementation
            # In practice, you might want more sophisticated filter building
            pass
        
        # Execute request
        response = client.run_report(request=request)
        
        # Process results
        results = []
        for row in response.rows:
            row_data = {}
            
            # Extract dimensions
            for i, dim_value in enumerate(row.dimension_values):
                if i < len(dim_list):
                    row_data[dim_list[i]] = dim_value.value
            
            # Extract metrics
            for i, met_value in enumerate(row.metric_values):
                if i < len(met_list):
                    metric_name = met_list[i]
                    # Convert to appropriate type
                    if metric_name in ["sessions", "newUsers", "screenPageViews", "eventCount", "keyEvents", "activeUsers"]:
                        row_data[metric_name] = int(met_value.value) if met_value.value else 0
                    else:
                        row_data[metric_name] = float(met_value.value) if met_value.value else 0.0
            
            results.append(row_data)
        
        # Calculate totals for summary
        totals = {}
        if results:
            for metric in met_list:
                if metric in ["sessions", "newUsers", "screenPageViews", "eventCount", "keyEvents", "activeUsers"]:
                    totals[metric] = sum(row.get(metric, 0) for row in results)
                elif metric in ["bounceRate", "userEngagementDuration", "totalRevenue"]:
                    values = [row.get(metric, 0) for row in results if row.get(metric, 0) > 0]
                    totals[metric] = sum(values) / len(values) if values else 0.0
        
        return {
            "success": True,
            "query_type": query_type,
            "property_id": property_id,
            "date_range": {"start": start_date, "end": end_date},
            "total_rows": len(results),
            "totals": totals,
            "data": results,
            "dimensions": dim_list,
            "metrics": met_list
        }
        
    except Exception as e:
        logger.error(f"MCP: Error querying GA4 data: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_ga4_properties(user_id: str) -> Dict[str, Any]:
    """
    Get all accessible Google Analytics 4 properties for the authenticated user.
    
    Args:
        user_id: User identifier for credential lookup
    
    Returns:
        List of GA4 properties with their IDs, names, and metadata
    """
    try:
        logger.info(f"MCP: Getting GA4 properties for user {user_id}")
        
        from routes.google_analytics_api import get_properties
        
        # Call the existing endpoint
        result = await get_properties(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "properties": result,
            "total_properties": len(result)
        }
        
    except Exception as e:
        logger.error(f"MCP: Error getting GA4 properties: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@mcp.tool()
async def get_google_ads_accounts(user_id: str) -> Dict[str, Any]:
    """
    Get all accessible Google Ads accounts for the authenticated user.
    
    Args:
        user_id: User identifier for credential lookup
    
    Returns:
        List of Google Ads accounts with their IDs, names, and metadata
    """
    try:
        logger.info(f"MCP: Getting Google Ads accounts for user {user_id}")
        
        from routes.google_ads_api import get_google_ads_client
        
        # Get client and accounts
        client = get_google_ads_client(user_id)
        customer_service = client.get_service("CustomerService")
        
        # Get accessible customers
        request = client.get_type("ListAccessibleCustomersRequest")
        response = customer_service.list_accessible_customers(request=request)
        
        accounts = []
        for resource_name in response.resource_names:
            customer_id = resource_name.split("/")[-1]
            
            # Get customer details
            try:
                customer_request = client.get_type("GetCustomerRequest")
                customer_request.resource_name = resource_name
                customer = customer_service.get_customer(request=customer_request)
                
                accounts.append({
                    "customer_id": customer_id,
                    "resource_name": resource_name,
                    "descriptive_name": customer.descriptive_name,
                    "currency_code": customer.currency_code,
                    "time_zone": customer.time_zone,
                    "auto_tagging_enabled": customer.auto_tagging_enabled,
                    "manager": customer.manager,
                    "test_account": customer.test_account
                })
            except Exception as account_error:
                logger.warning(f"Could not get details for customer {customer_id}: {account_error}")
                accounts.append({
                    "customer_id": customer_id,
                    "resource_name": resource_name,
                    "descriptive_name": f"Account {customer_id}",
                    "error": str(account_error)
                })
        
        return {
            "success": True,
            "user_id": user_id,
            "accounts": accounts,
            "total_accounts": len(accounts)
        }
        
    except Exception as e:
        logger.error(f"MCP: Error getting Google Ads accounts: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@mcp.tool()
async def get_meta_ads_accounts(user_id: str) -> Dict[str, Any]:
    """
    Get all accessible Meta (Facebook) Ads accounts for the authenticated user.
    
    Args:
        user_id: User identifier for credential lookup
    
    Returns:
        List of Meta Ads accounts with their IDs, names, and metadata
    """
    try:
        logger.info(f"MCP: Getting Meta Ads accounts for user {user_id}")
        
        from credential_manager import credential_manager
        import requests
        
        # Get Meta Ads credentials for user
        credentials = credential_manager.storage.get_user_credentials(user_id)
        meta_creds = credentials.get("meta_ads")
        
        if not meta_creds:
            return {
                "success": False,
                "error": "No Meta Ads credentials found for user",
                "user_id": user_id
            }
        
        access_token = meta_creds.get("access_token")
        if not access_token:
            return {
                "success": False,
                "error": "No access token found in Meta Ads credentials",
                "user_id": user_id
            }
        
        # Get ad accounts
        url = f"https://graph.facebook.com/v18.0/me/adaccounts"
        params = {
            "access_token": access_token,
            "fields": "id,name,account_id,currency,account_status,business,timezone_name,spend_cap,funding_source"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        accounts = data.get("data", [])
        
        return {
            "success": True,
            "user_id": user_id,
            "accounts": accounts,
            "total_accounts": len(accounts)
        }
        
    except Exception as e:
        logger.error(f"MCP: Error getting Meta Ads accounts: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@mcp.tool()
async def query_meta_ads_data(
    user_id: str,
    account_id: Optional[str] = None,
    query_type: str = "campaigns",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    custom_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Query Meta (Facebook) Ads data for various insights including campaigns, demographics, and performance metrics.

    Args:
        user_id: User identifier for credential lookup
        account_id: Meta Ads account ID (if not provided, uses first available account)
        query_type: Type of query - "campaigns", "demographics", "performance", "interests", "devices", "locations"
        start_date: Start date for data query (YYYY-MM-DD format)
        end_date: End date for data query (YYYY-MM-DD format)
        custom_fields: Custom fields to query (overrides default fields for query_type)

    Returns:
        Meta Ads data based on query type with metrics and insights
    """
    try:
        logger.info(f"MCP: Querying Meta Ads data for user {user_id}")

        from credential_manager import credential_manager
        import requests
        from datetime import datetime, timedelta

        # Get Meta Ads credentials for user
        credentials = credential_manager.storage.get_user_credentials(user_id)
        meta_creds = credentials.get("meta_ads")

        if not meta_creds:
            return {
                "success": False,
                "error": "No Meta Ads credentials found for user",
                "user_id": user_id
            }

        access_token = meta_creds.get("access_token")
        if not access_token:
            return {
                "success": False,
                "error": "No access token found in Meta Ads credentials",
                "user_id": user_id
            }

        # If no account_id provided, get the first available account
        if not account_id:
            accounts_url = f"https://graph.facebook.com/v18.0/me/adaccounts"
            accounts_params = {
                "access_token": access_token,
                "fields": "id,account_id"
            }

            accounts_response = requests.get(accounts_url, params=accounts_params)
            accounts_response.raise_for_status()
            accounts_data = accounts_response.json()
            accounts = accounts_data.get("data", [])

            if not accounts:
                return {
                    "success": False,
                    "error": "No Meta Ads accounts found for user",
                    "user_id": user_id
                }

            account_id = accounts[0]["id"]

        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Define fields based on query type
        if custom_fields:
            fields = custom_fields
        else:
            base_metrics = [
                "impressions", "clicks", "spend", "reach", "frequency",
                "ctr", "cpc", "cpm", "cpp", "actions"
            ]

            if query_type == "campaigns":
                fields = ["campaign_id", "campaign_name"] + base_metrics
            elif query_type == "demographics":
                fields = ["age", "gender"] + base_metrics
            elif query_type == "interests":
                fields = ["actions", "action_type"] + base_metrics
            elif query_type == "devices":
                fields = ["platform_position", "impression_device"] + base_metrics
            elif query_type == "locations":
                fields = ["country", "region", "dma"] + base_metrics
            elif query_type == "performance":
                fields = ["date_start", "date_stop"] + base_metrics
            else:
                fields = base_metrics

        # Build API URL based on query type
        if query_type == "campaigns":
            url = f"https://graph.facebook.com/v18.0/{account_id}/campaigns"
            params = {
                "access_token": access_token,
                "fields": f"id,name,status,insights{{{',' .join(fields)}}}"
            }
        elif query_type in ["demographics", "interests", "devices", "locations", "performance"]:
            url = f"https://graph.facebook.com/v18.0/{account_id}/insights"
            params = {
                "access_token": access_token,
                "fields": ",".join(fields),
                "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
                "time_increment": 1
            }

            # Add breakdowns for specific query types
            if query_type == "demographics":
                params["breakdowns"] = "age,gender"
            elif query_type == "interests":
                params["breakdowns"] = "actions"
            elif query_type == "devices":
                params["breakdowns"] = "platform_position,impression_device"
            elif query_type == "locations":
                params["breakdowns"] = "country,region,dma"
        else:
            # Default to insights
            url = f"https://graph.facebook.com/v18.0/{account_id}/insights"
            params = {
                "access_token": access_token,
                "fields": ",".join(fields),
                "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}'
            }

        # Make API request
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("data", [])

        # Process results based on query type
        processed_results = []
        for item in results:
            if query_type == "campaigns" and "insights" in item:
                # Extract campaign info and insights
                insights_data = item["insights"].get("data", [])
                for insight in insights_data:
                    processed_item = {
                        "campaign_id": item.get("id"),
                        "campaign_name": item.get("name"),
                        "campaign_status": item.get("status"),
                        **insight
                    }
                    processed_results.append(processed_item)
            else:
                processed_results.append(item)

        return {
            "success": True,
            "query_type": query_type,
            "account_id": account_id,
            "date_range": {"start": start_date, "end": end_date},
            "total_rows": len(processed_results),
            "data": processed_results,
            "fields_requested": fields
        }

    except Exception as e:
        logger.error(f"MCP: Error querying Meta Ads data: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_platform_examples() -> Dict[str, Any]:
    """
    Get examples of how to structure data_selections for different platforms.

    Returns:
        Examples for Google Analytics, Google Ads, and Meta Ads platforms
    """
    return {
        "examples": {
            "google_analytics": {
                "platform": "google_analytics",
                "property_id": "123456789",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            },
            "google_ads": {
                "platform": "google_ads",
                "account_id": "987-654-3210",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            },
            "meta_ads": {
                "platform": "meta_ads",
                "account_id": "act_1234567890",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            }
        },
        "meta_ads_query_examples": {
            "campaigns": {
                "description": "Get campaign performance data",
                "query_type": "campaigns",
                "example_call": "query_meta_ads_data(user_id='user123', account_id='act_1234567890', query_type='campaigns')"
            },
            "demographics": {
                "description": "Get audience demographics (age, gender)",
                "query_type": "demographics",
                "example_call": "query_meta_ads_data(user_id='user123', query_type='demographics', start_date='2024-01-01', end_date='2024-01-31')"
            },
            "devices": {
                "description": "Get device and platform performance",
                "query_type": "devices",
                "example_call": "query_meta_ads_data(user_id='user123', query_type='devices')"
            },
            "locations": {
                "description": "Get geographic performance data",
                "query_type": "locations",
                "example_call": "query_meta_ads_data(user_id='user123', query_type='locations')"
            },
            "performance": {
                "description": "Get time-series performance data",
                "query_type": "performance",
                "example_call": "query_meta_ads_data(user_id='user123', query_type='performance', start_date='2024-01-01', end_date='2024-01-31')"
            }
        },
        "multi_platform_example": [
            {
                "platform": "google_analytics",
                "property_id": "123456789",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            },
            {
                "platform": "google_ads",
                "account_id": "987-654-3210",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            },
            {
                "platform": "meta_ads",
                "account_id": "act_1234567890",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
            }
        ],
        "note": "When using multiple platforms, you'll get combined insights including user journey analysis and cross-platform attribution.",
        "mcp_tools": {
            "get_comprehensive_insights": "Get full marketing analysis combining multiple data sources with AI insights",
            "query_google_ads_data": "Query specific Google Ads data - demographics, campaigns, keywords, locations, devices",
            "query_ga4_data": "Query specific GA4 data - website traffic, user behavior, content performance, traffic sources",
            "query_meta_ads_data": "Query specific Meta Ads data - campaigns, demographics, performance, interests, devices, locations",
            "get_ga4_properties": "List all accessible Google Analytics 4 properties for a user",
            "get_google_ads_accounts": "List all accessible Google Ads accounts for a user",
            "get_meta_ads_accounts": "List all accessible Meta (Facebook) Ads accounts for a user"
        }
    }
