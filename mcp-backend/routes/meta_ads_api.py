from fastapi import APIRouter, HTTPException, Query
import logging
from typing import List, Optional
import requests
from routes.meta_oauth import get_meta_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta-ads", tags=["Meta Ads API"])

@router.get("/accounts")
async def get_ad_accounts():
    """Get all accessible Meta ad accounts for the authenticated user"""
    try:
        access_token = get_meta_access_token()
        
        # Get ad accounts
        url = f"https://graph.facebook.com/v18.0/me/adaccounts"
        params = {
            'access_token': access_token,
            'fields': 'id,name,account_id,currency,timezone_name,account_status'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Meta Ad Accounts API error: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch ad accounts")
        
        data = response.json()
        accounts = data.get('data', [])
        
        # Format the response
        formatted_accounts = []
        for account in accounts:
            formatted_accounts.append({
                'id': account.get('id'),
                'name': account.get('name'),
                'account_id': account.get('account_id'),
                'currency': account.get('currency'),
                'timezone_name': account.get('timezone_name'),
                'account_status': account.get('account_status')
            })
        
        return formatted_accounts
        
    except Exception as e:
        logger.error(f"Error fetching Meta ad accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ad accounts: {str(e)}")

@router.get("/accounts/{account_id}/campaigns")
async def get_campaigns(
    account_id: str,
    include_metrics: bool = Query(True, description="Include campaign metrics")
):
    """Get campaigns for a specific Meta ad account"""
    try:
        access_token = get_meta_access_token()
        
        # Base fields for campaigns
        fields = ['id', 'name', 'status', 'objective', 'daily_budget', 'lifetime_budget']
        
        # Add metrics if requested
        if include_metrics:
            fields.extend([
                'insights{impressions,clicks,spend,reach,frequency,ctr,cpc,cpm,cpp,actions}'
            ])
        
        url = f"https://graph.facebook.com/v18.0/{account_id}/campaigns"
        params = {
            'access_token': access_token,
            'fields': ','.join(fields)
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Meta Campaigns API error: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch campaigns")
        
        data = response.json()
        campaigns = data.get('data', [])
        
        # Format the response
        formatted_campaigns = []
        for campaign in campaigns:
            campaign_data = {
                'id': campaign.get('id'),
                'name': campaign.get('name'),
                'status': campaign.get('status'),
                'objective': campaign.get('objective'),
                'daily_budget': campaign.get('daily_budget'),
                'lifetime_budget': campaign.get('lifetime_budget')
            }
            
            # Add metrics if available
            if include_metrics and 'insights' in campaign:
                insights = campaign['insights'].get('data', [])
                if insights:
                    insight = insights[0]  # Take the first insight record
                    campaign_data['metrics'] = {
                        'impressions': int(insight.get('impressions', 0)),
                        'clicks': int(insight.get('clicks', 0)),
                        'spend': float(insight.get('spend', 0)),
                        'reach': int(insight.get('reach', 0)),
                        'frequency': float(insight.get('frequency', 0)),
                        'ctr': float(insight.get('ctr', 0)),
                        'cpc': float(insight.get('cpc', 0)),
                        'cpm': float(insight.get('cpm', 0)),
                        'cpp': float(insight.get('cpp', 0)),
                        'actions': insight.get('actions', [])
                    }
            
            formatted_campaigns.append(campaign_data)
        
        return formatted_campaigns
        
    except Exception as e:
        logger.error(f"Error fetching Meta campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {str(e)}")

@router.get("/accounts/{account_id}/performance")
async def get_account_performance(
    account_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get performance metrics for a Meta ad account"""
    try:
        access_token = get_meta_access_token()
        
        url = f"https://graph.facebook.com/v18.0/{account_id}/insights"
        params = {
            'access_token': access_token,
            'fields': 'impressions,clicks,spend,reach,frequency,ctr,cpc,cpm,cpp,actions',
            'time_range': f'{{"since":"{start_date}","until":"{end_date}"}}',
            'time_increment': 1
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Meta Account Performance API error: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch account performance")
        
        data = response.json()
        insights = data.get('data', [])
        
        # Aggregate metrics
        total_metrics = {
            'impressions': 0,
            'clicks': 0,
            'spend': 0.0,
            'reach': 0,
            'frequency': 0.0,
            'ctr': 0.0,
            'cpc': 0.0,
            'cpm': 0.0,
            'cpp': 0.0
        }
        
        for insight in insights:
            total_metrics['impressions'] += int(insight.get('impressions', 0))
            total_metrics['clicks'] += int(insight.get('clicks', 0))
            total_metrics['spend'] += float(insight.get('spend', 0))
            total_metrics['reach'] += int(insight.get('reach', 0))
        
        # Calculate averages for rate metrics
        if insights:
            total_metrics['frequency'] = sum(float(i.get('frequency', 0)) for i in insights) / len(insights)
            total_metrics['ctr'] = sum(float(i.get('ctr', 0)) for i in insights) / len(insights)
            total_metrics['cpc'] = sum(float(i.get('cpc', 0)) for i in insights) / len(insights)
            total_metrics['cpm'] = sum(float(i.get('cpm', 0)) for i in insights) / len(insights)
            total_metrics['cpp'] = sum(float(i.get('cpp', 0)) for i in insights) / len(insights)
        
        return total_metrics
        
    except Exception as e:
        logger.error(f"Error fetching Meta account performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch account performance: {str(e)}")

@router.get("/accounts/{account_id}/adsets")
async def get_adsets(
    account_id: str,
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID")
):
    """Get ad sets for a Meta ad account"""
    try:
        access_token = get_meta_access_token()
        
        url = f"https://graph.facebook.com/v18.0/{account_id}/adsets"
        params = {
            'access_token': access_token,
            'fields': 'id,name,status,campaign_id,daily_budget,lifetime_budget'
        }
        
        if campaign_id:
            params['filtering'] = f'[{{"field":"campaign.id","operator":"EQUAL","value":"{campaign_id}"}}]'
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Meta Ad Sets API error: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch ad sets")
        
        data = response.json()
        return data.get('data', [])
        
    except Exception as e:
        logger.error(f"Error fetching Meta ad sets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ad sets: {str(e)}")

@router.get("/accounts/{account_id}/ads")
async def get_ads(
    account_id: str,
    adset_id: Optional[str] = Query(None, description="Filter by ad set ID")
):
    """Get ads for a Meta ad account"""
    try:
        access_token = get_meta_access_token()
        
        url = f"https://graph.facebook.com/v18.0/{account_id}/ads"
        params = {
            'access_token': access_token,
            'fields': 'id,name,status,adset_id,campaign_id'
        }
        
        if adset_id:
            params['filtering'] = f'[{{"field":"adset.id","operator":"EQUAL","value":"{adset_id}"}}]'
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Meta Ads API error: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to fetch ads")
        
        data = response.json()
        return data.get('data', [])
        
    except Exception as e:
        logger.error(f"Error fetching Meta ads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ads: {str(e)}")