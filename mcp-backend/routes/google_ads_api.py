from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
# Removed old OAuth import - now using database credentials directly
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advertising", tags=["Google Ads API"])

class GoogleAdsConfig:
    def __init__(self):
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        if not self.developer_token:
            logger.warning("GOOGLE_ADS_DEVELOPER_TOKEN not set")

config = GoogleAdsConfig()

class CustomerAccount(BaseModel):
    id: str
    name: str
    currency_code: str
    time_zone: str
    resource_name: str

class CampaignMetrics(BaseModel):
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    average_cpc: float = 0.0
    cost_per_conversion: float = 0.0

class Campaign(BaseModel):
    id: str
    name: str
    status: str
    resource_name: str
    metrics: Optional[CampaignMetrics] = None

def get_google_ads_client(user_id: str) -> GoogleAdsClient:
    """Create Google Ads client with stored credentials from database"""
    try:
        from database import credential_storage
        
        # Get stored Google Ads credentials from database
        user_credentials = credential_storage.get_user_credentials(user_id)
        
        if "google_ads" not in user_credentials:
            raise HTTPException(status_code=401, detail="Google Ads credentials not found. Please authenticate first.")
        
        google_ads_creds = user_credentials["google_ads"]
        
        # Create client configuration in the format expected by Google Ads API
        client_config = {
            "developer_token": google_ads_creds.get("developer_token"),
            "client_id": google_ads_creds.get("client_id"),
            "client_secret": google_ads_creds.get("client_secret"),
            "refresh_token": google_ads_creds.get("refresh_token"),
            "use_proto_plus": True,
        }
        
        # Validate required fields
        required_fields = ["developer_token", "client_id", "client_secret", "refresh_token"]
        missing_fields = [field for field in required_fields if not client_config.get(field)]
        
        if missing_fields:
            raise HTTPException(
                status_code=401, 
                detail=f"Missing required Google Ads credentials: {', '.join(missing_fields)}"
            )
        
        # Create client
        client = GoogleAdsClient.load_from_dict(client_config, version="v21")
        
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Google Ads client: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Google Ads client")

@router.get("/accounts", response_model=List[CustomerAccount])
async def get_accounts(user_id: str):
    """Get all accessible Google Ads accounts"""
    try:
        client = get_google_ads_client(user_id)
        
        # Get accessible customers using the proper Google Ads API v21 method
        customer_service = client.get_service("CustomerService", version="v21")
        request = client.get_type("ListAccessibleCustomersRequest", version="v21")
        accessible_customers_response = customer_service.list_accessible_customers(request=request)
        
        accounts = []
        
        # Get details for each accessible customer
        for customer_resource_name in accessible_customers_response.resource_names:
            customer_id = customer_resource_name.split("/")[-1]
            
            try:
                # Get customer details using GoogleAdsService
                ga_service = client.get_service("GoogleAdsService", version="v21")
                
                query = """
                    SELECT 
                        customer.id,
                        customer.descriptive_name,
                        customer.currency_code,
                        customer.time_zone,
                        customer.resource_name
                    FROM customer
                    LIMIT 1
                """
                
                search_request = client.get_type("SearchGoogleAdsRequest", version="v21")
                search_request.customer_id = customer_id
                search_request.query = query
                
                response = ga_service.search(request=search_request)
                
                for row in response:
                    customer = row.customer
                    accounts.append(CustomerAccount(
                        id=str(customer.id),
                        name=customer.descriptive_name or f"Account {customer.id}",
                        currency_code=customer.currency_code or "USD",
                        time_zone=customer.time_zone or "UTC",
                        resource_name=customer.resource_name
                    ))
                    break
                    
            except GoogleAdsException as ex:
                logger.warning(f"Could not access customer {customer_id}: {ex}")
                # Still add the account but with limited info
                accounts.append(CustomerAccount(
                    id=customer_id,
                    name=f"Account {customer_id} (Limited Access)",
                    currency_code="USD",
                    time_zone="UTC", 
                    resource_name=customer_resource_name
                ))
                continue
            except Exception as ex:
                logger.warning(f"Error processing customer {customer_id}: {ex}")
                continue
        
        return accounts
        
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")

@router.get("/accounts/{customer_id}/campaigns", response_model=List[Campaign])
async def get_campaigns(
    customer_id: str,
    user_id: str,
    include_metrics: bool = Query(True, description="Include campaign metrics")
):
    """Get campaigns for a specific customer account"""
    try:
        client = get_google_ads_client(user_id)
        ga_service = client.get_service("GoogleAdsService")
        
        # Build query
        fields = [
            "campaign.id",
            "campaign.name",
            "campaign.status",
            "campaign.resource_name"
        ]
        
        if include_metrics:
            fields.extend([
                "metrics.impressions",
                "metrics.clicks", 
                "metrics.cost_micros",
                "metrics.conversions",
                "metrics.ctr",
                "metrics.average_cpc",
                "metrics.cost_per_conversion"
            ])
        
        query = f"""
            SELECT {', '.join(fields)}
            FROM campaign
            WHERE campaign.status != 'REMOVED'
        """

        response = ga_service.search(customer_id=customer_id, query=query)

        campaigns = []
        for row in response:
            campaign = row.campaign
            
            metrics = None
            if include_metrics and hasattr(row, 'metrics'):
                m = row.metrics
                metrics = CampaignMetrics(
                    impressions=int(m.impressions or 0),
                    clicks=int(m.clicks or 0),
                    cost=float(m.cost_micros or 0) / 1_000_000,  # Convert from micros
                    conversions=float(m.conversions or 0),
                    ctr=float(m.ctr or 0),
                    average_cpc=float(m.average_cpc or 0) / 1_000_000,  # Convert from micros
                    cost_per_conversion=float(m.cost_per_conversion or 0) / 1_000_000  # Convert from micros
                )
            
            campaigns.append(Campaign(
                id=str(campaign.id),
                name=campaign.name,
                status=campaign.status.name,
                resource_name=campaign.resource_name,
                metrics=metrics
            ))
        
        return campaigns
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=f"Google Ads API error: {str(ex)}")
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {str(e)}")

@router.get("/accounts/{customer_id}/performance")
async def get_account_performance(
    customer_id: str,
    user_id: str,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """Get account performance metrics for a date range"""
    try:
        client = get_google_ads_client(user_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT 
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_per_conversion,
                segments.date
            FROM customer
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        # Aggregate metrics
        total_impressions = 0
        total_clicks = 0
        total_cost = 0.0
        total_conversions = 0.0
        daily_metrics = []
        
        for row in response:
            m = row.metrics
            date = row.segments.date
            
            impressions = int(m.impressions or 0)
            clicks = int(m.clicks or 0)
            cost = float(m.cost_micros or 0) / 1_000_000
            conversions = float(m.conversions or 0)
            
            total_impressions += impressions
            total_clicks += clicks
            total_cost += cost
            total_conversions += conversions
            
            daily_metrics.append({
                "date": date,
                "impressions": impressions,
                "clicks": clicks,
                "cost": cost,
                "conversions": conversions,
                "ctr": float(m.ctr or 0),
                "average_cpc": float(m.average_cpc or 0) / 1_000_000
            })
        
        # Calculate totals
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        average_cpc = (total_cost / total_clicks) if total_clicks > 0 else 0
        cost_per_conversion = (total_cost / total_conversions) if total_conversions > 0 else 0
        
        return {
            "customer_id": customer_id,
            "date_range": {"start": start_date, "end": end_date},
            "totals": {
                "impressions": total_impressions,
                "clicks": total_clicks,
                "cost": total_cost,
                "conversions": total_conversions,
                "ctr": ctr,
                "average_cpc": average_cpc,
                "cost_per_conversion": cost_per_conversion
            },
            "daily_breakdown": daily_metrics
        }
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=f"Google Ads API error: {str(ex)}")
    except Exception as e:
        logger.error(f"Error fetching performance data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance data: {str(e)}")

@router.get("/health")
async def health_check():
    """Check if Google Ads API integration is properly configured"""
    issues = []
    
    if not config.developer_token:
        issues.append("GOOGLE_ADS_DEVELOPER_TOKEN not configured")
    
    if not os.getenv("GOOGLE_CLIENT_ID"):
        issues.append("GOOGLE_CLIENT_ID not configured")
        
    if not os.getenv("GOOGLE_CLIENT_SECRET"):
        issues.append("GOOGLE_CLIENT_SECRET not configured")
    
    return {
        "status": "healthy" if not issues else "configuration_issues",
        "issues": issues,
        "google_ads_api": "configured" if config.developer_token else "not_configured"
    }