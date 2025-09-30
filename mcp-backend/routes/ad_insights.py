from fastapi import APIRouter, HTTPException, Form, UploadFile, File
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
from models import LoadUserCredentialsRequest
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
import chardet  # Add chardet for encoding detection

def _detect_encoding_and_read_csv(file_obj, filename: str, **kwargs):
    """
    Detect file encoding and read CSV with proper encoding handling
    """
    # Reset file position
    file_obj.seek(0)

    # Read a sample of the file to detect encoding
    sample = file_obj.read(10000)  # Read first 10KB
    file_obj.seek(0)  # Reset position

    # Detect encoding
    detected = chardet.detect(sample)
    encoding = detected.get('encoding', 'utf-8')
    confidence = detected.get('confidence', 0)

    print(f"🔍 Detected encoding for '{filename}': {encoding} (confidence: {confidence:.2f})")

    # List of encodings to try in order of preference
    encodings_to_try = [
        encoding,  # Start with detected encoding
        'utf-8',
        'utf-16',
        'utf-8-sig',  # UTF-8 with BOM
        'windows-1252',  # Common Windows encoding
        'iso-8859-1',   # Latin-1
        'cp1252'        # Another Windows encoding
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique_encodings = []
    for enc in encodings_to_try:
        if enc and enc.lower() not in seen:
            seen.add(enc.lower())
            unique_encodings.append(enc)

    last_error = None

    for encoding_attempt in unique_encodings:
        try:
            file_obj.seek(0)
            print(f"🔄 Trying to read '{filename}' with encoding: {encoding_attempt}")

            # Create a text wrapper with the specific encoding
            text_file = io.TextIOWrapper(file_obj, encoding=encoding_attempt)
            df = pd.read_csv(text_file, **kwargs)

            print(f"✅ Successfully read '{filename}' with encoding: {encoding_attempt}")
            print(f"   Loaded {len(df)} rows with columns: {list(df.columns)[:5]}...")

            return df

        except UnicodeDecodeError as e:
            last_error = e
            print(f"❌ Encoding {encoding_attempt} failed: {str(e)}")
            continue
        except Exception as e:
            last_error = e
            print(f"❌ Reading with {encoding_attempt} failed: {str(e)}")
            continue

    # If all encodings failed, raise a helpful error
    raise Exception(
        f"Could not read '{filename}' with any supported encoding. "
        f"Tried: {', '.join(unique_encodings)}. "
        f"Last error: {str(last_error)}. "
        f"Please save the file as UTF-8 CSV or check if it's corrupted."
    )

async def _get_automatic_date_range(user_id: str) -> Dict[str, str]:
    """
    Automatically determine optimal date range based on available data
    Returns last 30 days, or adjusts based on data availability
    """
    try:
        # Load user credentials to check data availability
        credential_manager.load_user_connectors(user_id)
        
        # Default to last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Try to fetch a small sample to see if data exists
        try:
            sample_df = await data_integrator_instance.fetch_specific_data(
                connector_names=['meta_ads', 'google_ads'],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if not sample_df.empty:
                # Data exists for last 30 days
                return {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d')
                }
        except:
            pass
        
        # If no data in last 30 days, try last 90 days
        start_date = end_date - timedelta(days=90)
        try:
            sample_df = await data_integrator_instance.fetch_specific_data(
                connector_names=['meta_ads', 'google_ads'],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if not sample_df.empty:
                # Find the actual date range with data
                if 'date' in sample_df.columns:
                    actual_start = sample_df['date'].min()
                    actual_end = sample_df['date'].max()
                    return {
                        "start_date": str(actual_start),
                        "end_date": str(actual_end)
                    }
        except:
            pass
        
        # Fallback to last 30 days even if no data
        return {
            "start_date": (end_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        # Ultimate fallback
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        return {
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }

router = APIRouter()

@router.post("/debug-ad-data-availability")
async def debug_ad_data_availability(request: str = Form(...)):
    """
    Debug endpoint to check what ad data is available for a user
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    debug_info = {
        "user_id": user_id,
        "connector_status": data_integrator_instance.get_connector_status(),
        "date_ranges_tested": []
    }
    
    # Test different date ranges
    end_date = datetime.now()
    test_ranges = [
        ("last_7_days", 7),
        ("last_30_days", 30),
        ("last_90_days", 90),
        ("last_365_days", 365)
    ]
    
    for range_name, days in test_ranges:
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        try:
            df = await data_integrator_instance.fetch_specific_data(
                connector_names=['meta_ads', 'google_ads'],
                start_date=start_str,
                end_date=end_str
            )
            
            debug_info["date_ranges_tested"].append({
                "range": range_name,
                "start_date": start_str,
                "end_date": end_str,
                "records_found": len(df) if not df.empty else 0,
                "has_data": not df.empty,
                "columns": list(df.columns) if not df.empty else [],
                "date_range_in_data": {
                    "min_date": str(df['date'].min()) if not df.empty and 'date' in df.columns else None,
                    "max_date": str(df['date'].max()) if not df.empty and 'date' in df.columns else None
                } if not df.empty else None
            })
            
            if not df.empty:
                # Found data, can stop here
                break
                
        except Exception as e:
            debug_info["date_ranges_tested"].append({
                "range": range_name,
                "start_date": start_str,
                "end_date": end_str,
                "error": str(e),
                "has_data": False
            })
    
    return debug_info

@router.post("/ad-performance-analysis")
async def ad_performance_analysis(request: str = Form(...)):
    """
    Comprehensive ad performance analysis for agencies
    
    Returns insights on what works and what doesn't work
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    data_sources = req_data.get('data_sources', ['meta_ads', 'google_ads'])
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    # Fetch data from specified sources
    try:
        df = await data_integrator_instance.fetch_specific_data(
            connector_names=data_sources,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No ad data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
            )
        
        # Calculate key performance metrics
        analysis = _analyze_ad_performance(df)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
            "data_sources": data_sources,
            "total_records": len(df),
            **analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing ad performance: {str(e)}")

@router.post("/campaign-comparison")
async def campaign_comparison(request: str = Form(...)):
    """
    Compare performance across different campaigns
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    campaigns = req_data.get('campaigns', [])  # List of campaign names to compare
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    
    df = await data_integrator_instance.fetch_specific_data(
        connector_names=['meta_ads', 'google_ads'],
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No campaign data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
        )
    
    # Filter campaigns if specified
    if campaigns:
        df = df[df['campaign_name'].isin(campaigns)]
    
    # Compare campaigns
    comparison = _compare_campaigns(df)
    
    return {
        "user_id": user_id,
        "comparison_period": f"{start_date} to {end_date}",
        "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
        "campaigns_analyzed": campaigns if campaigns else "All campaigns",
        **comparison
    }

@router.post("/ad-recommendations")
async def ad_recommendations(request: str = Form(...)):
    """
    Generate actionable recommendations for ad optimization
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    min_spend = req_data.get('min_spend', 100)  # Minimum spend to consider for recommendations
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    
    df = await data_integrator_instance.fetch_specific_data(
        connector_names=['meta_ads', 'google_ads'],
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No ad data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
        )
    
    # Generate recommendations
    recommendations = _generate_recommendations(df, min_spend)
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
        "recommendations": recommendations
    }

@router.post("/performance-trends")
async def performance_trends(request: str = Form(...)):
    """
    Analyze performance trends over time
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    metric = req_data.get('metric', 'ctr')  # ctr, cpc, cpm, conversions, etc.
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    
    df = await data_integrator_instance.fetch_specific_data(
        connector_names=['meta_ads', 'google_ads'],
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No ad data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
        )
    
    # Analyze trends
    trends = _analyze_trends(df, metric)
    
    return {
        "user_id": user_id,
        "metric": metric,
        "analysis_period": f"{start_date} to {end_date}",
        "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
        **trends
    }

@router.post("/optimization-action-plan")
async def optimization_action_plan(request: str = Form(...)):
    """
    Generate detailed action plan with specific steps to optimize ad performance
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    budget_increase_limit = req_data.get('budget_increase_limit', 50)  # Max % increase
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    
    df = await data_integrator_instance.fetch_specific_data(
        connector_names=['meta_ads', 'google_ads'],
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No ad data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
        )
    
    # Generate comprehensive action plan
    action_plan = _generate_action_plan(df, budget_increase_limit)
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
        "action_plan": action_plan,
        "implementation_priority": "Execute in order: Immediate → This Week → This Month"
    }

@router.post("/budget-reallocation-plan") 
async def budget_reallocation_plan(request: str = Form(...)):
    """
    Calculate specific budget reallocation recommendations
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    total_monthly_budget = req_data.get('total_monthly_budget', 10000)
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Auto-detect date range if not provided
    if not start_date or not end_date:
        date_range = await _get_automatic_date_range(user_id)
        start_date = start_date or date_range['start_date']
        end_date = end_date or date_range['end_date']
    
    # Load user credentials and fetch data
    credential_manager.load_user_connectors(user_id)
    
    df = await data_integrator_instance.fetch_specific_data(
        connector_names=['meta_ads', 'google_ads'],
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No ad data found for period {start_date} to {end_date}. Check if: 1) Ad accounts have active campaigns, 2) Credentials point to correct accounts, 3) Try endpoint /debug-ad-data-availability to troubleshoot"
        )
    
    # Calculate optimal budget allocation
    reallocation = _calculate_budget_reallocation(df, total_monthly_budget)
    
    return {
        "user_id": user_id,
        "analysis_period": f"{start_date} to {end_date}",
        "auto_detected_dates": not req_data.get('start_date') or not req_data.get('end_date'),
        "current_monthly_budget": total_monthly_budget,
        "reallocation_plan": reallocation
    }

def _analyze_ad_performance(df: pd.DataFrame) -> Dict:
    """Analyze what works and what doesn't work in ads"""
    
    # Calculate performance metrics with NaN handling
    df['roas'] = df['conversions'] / (df['spend'] + 0.001)  # Avoid division by zero
    df['cost_per_conversion'] = df['spend'] / (df['conversions'] + 0.001)
    df['conversion_rate'] = df['conversions'] / (df['clicks'] + 0.001)
    
    # Replace infinite and NaN values with 0
    df['roas'] = df['roas'].replace([float('inf'), float('-inf')], 0).fillna(0)
    df['cost_per_conversion'] = df['cost_per_conversion'].replace([float('inf'), float('-inf')], 0).fillna(0)
    df['conversion_rate'] = df['conversion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)
    
    # Identify top and bottom performers
    performance_metrics = ['ctr', 'cpc', 'cpm', 'roas', 'conversion_rate']
    
    top_performers = {}
    bottom_performers = {}
    
    for metric in performance_metrics:
        if metric in df.columns:
            # Top 10% performers
            top_threshold = df[metric].quantile(0.9)
            top_ads = df[df[metric] >= top_threshold][['campaign_name', 'adset_name', 'ad_name', metric, 'spend', 'conversions']].to_dict('records')
            
            # Bottom 10% performers (with minimum spend requirement)
            min_spend_df = df[df['spend'] >= 50]  # Only consider ads with at least $50 spend
            if not min_spend_df.empty:
                bottom_threshold = min_spend_df[metric].quantile(0.1)
                bottom_ads = min_spend_df[min_spend_df[metric] <= bottom_threshold][['campaign_name', 'adset_name', 'ad_name', metric, 'spend', 'conversions']].to_dict('records')
            else:
                bottom_ads = []
            
            top_performers[metric] = top_ads[:10]  # Limit to top 10
            bottom_performers[metric] = bottom_ads[:10]  # Limit to bottom 10
    
    # Campaign-level insights
    campaign_summary = df.groupby('campaign_name').agg({
        'impressions': 'sum',
        'clicks': 'sum', 
        'spend': 'sum',
        'conversions': 'sum',
        'ctr': 'mean',
        'cpc': 'mean',
        'cpm': 'mean'
    }).round(4)
    
    # Calculate campaign-level metrics
    campaign_summary['roas'] = campaign_summary['conversions'] / (campaign_summary['spend'] + 0.001)
    campaign_summary['conversion_rate'] = campaign_summary['conversions'] / (campaign_summary['clicks'] + 0.001)
    campaign_summary = campaign_summary.round(4)
    
    # Find patterns in high-performing ads
    if not df.empty:
        # Group by source to see which platform performs better
        source_performance = df.groupby('source').agg({
            'ctr': 'mean',
            'cpc': 'mean',
            'conversions': 'sum',
            'spend': 'sum'
        }).round(4)
        source_performance['roas'] = (source_performance['conversions'] / (source_performance['spend'] + 0.001)).round(4)
    else:
        source_performance = pd.DataFrame()
    
    return {
        "top_performers": top_performers,
        "bottom_performers": bottom_performers,
        "campaign_summary": campaign_summary.to_dict('index'),
        "platform_comparison": source_performance.to_dict('index'),
        "overall_metrics": {
            "total_spend": float(df['spend'].sum()),
            "total_conversions": float(df['conversions'].sum()),
            "average_ctr": float(df['ctr'].mean()),
            "average_cpc": float(df['cpc'].mean()),
            "overall_roas": float(df['conversions'].sum() / (df['spend'].sum() + 0.001))
        }
    }

def _compare_campaigns(df: pd.DataFrame) -> Dict:
    """Compare campaign performance side by side"""
    
    campaign_metrics = df.groupby('campaign_name').agg({
        'impressions': 'sum',
        'clicks': 'sum',
        'spend': 'sum',
        'conversions': 'sum',
        'ctr': 'mean',
        'cpc': 'mean',
        'cpm': 'mean'
    }).round(4)
    
    # Calculate additional metrics
    campaign_metrics['roas'] = (campaign_metrics['conversions'] / (campaign_metrics['spend'] + 0.001)).round(4)
    campaign_metrics['conversion_rate'] = (campaign_metrics['conversions'] / (campaign_metrics['clicks'] + 0.001)).round(4)
    campaign_metrics['cost_per_conversion'] = (campaign_metrics['spend'] / (campaign_metrics['conversions'] + 0.001)).round(4)
    
    # Rank campaigns by different metrics
    rankings = {}
    metrics_to_rank = ['roas', 'ctr', 'conversion_rate', 'conversions']
    
    for metric in metrics_to_rank:
        if metric in campaign_metrics.columns:
            ranked = campaign_metrics.sort_values(metric, ascending=False)
            rankings[f"best_{metric}"] = ranked.index.tolist()[:5]  # Top 5 campaigns
    
    return {
        "campaign_comparison": campaign_metrics.to_dict('index'),
        "campaign_rankings": rankings,
        "total_campaigns": len(campaign_metrics)
    }

def _generate_recommendations(df: pd.DataFrame, min_spend: float) -> List[Dict]:
    """Generate actionable recommendations for ad optimization"""
    
    recommendations = []
    
    # Filter ads with sufficient spend for meaningful analysis
    significant_ads = df[df['spend'] >= min_spend].copy()
    
    if significant_ads.empty:
        return [{"type": "warning", "message": f"No ads found with minimum spend of ${min_spend}"}]
    
    # Calculate performance metrics
    significant_ads['roas'] = significant_ads['conversions'] / (significant_ads['spend'] + 0.001)
    significant_ads['conversion_rate'] = significant_ads['conversions'] / (significant_ads['clicks'] + 0.001)
    
    # Recommendation 1: Stop poor performers
    poor_performers = significant_ads[
        (significant_ads['ctr'] < significant_ads['ctr'].quantile(0.2)) &
        (significant_ads['roas'] < 1.0)
    ]
    
    if not poor_performers.empty:
        total_waste = poor_performers['spend'].sum()
        recommendations.append({
            "type": "stop_ads",
            "priority": "high",
            "message": f"Consider pausing {len(poor_performers)} underperforming ads",
            "details": f"These ads have low CTR and ROAS < 1.0, wasting ${total_waste:.2f}",
            "affected_ads": poor_performers[['campaign_name', 'ad_name', 'spend', 'ctr', 'roas']].to_dict('records')[:5]
        })
    
    # Recommendation 2: Scale top performers
    top_performers = significant_ads[
        (significant_ads['roas'] > significant_ads['roas'].quantile(0.8)) &
        (significant_ads['ctr'] > significant_ads['ctr'].mean())
    ]
    
    if not top_performers.empty:
        recommendations.append({
            "type": "scale_ads",
            "priority": "high", 
            "message": f"Consider increasing budget for {len(top_performers)} high-performing ads",
            "details": f"These ads have high ROAS and above-average CTR",
            "affected_ads": top_performers[['campaign_name', 'ad_name', 'spend', 'ctr', 'roas']].to_dict('records')[:5]
        })
    
    # Recommendation 3: Platform optimization
    platform_performance = significant_ads.groupby('source').agg({
        'roas': 'mean',
        'ctr': 'mean',
        'spend': 'sum'
    }).round(4)
    
    if len(platform_performance) > 1:
        best_platform = platform_performance['roas'].idxmax()
        worst_platform = platform_performance['roas'].idxmin()
        
        if platform_performance.loc[best_platform, 'roas'] > platform_performance.loc[worst_platform, 'roas'] * 1.5:
            recommendations.append({
                "type": "platform_shift",
                "priority": "medium",
                "message": f"Consider shifting more budget to {best_platform}",
                "details": f"{best_platform} shows {platform_performance.loc[best_platform, 'roas']:.2f} ROAS vs {worst_platform} at {platform_performance.loc[worst_platform, 'roas']:.2f} ROAS"
            })
    
    # Recommendation 4: Campaign optimization
    campaign_performance = significant_ads.groupby('campaign_name').agg({
        'roas': 'mean',
        'spend': 'sum',
        'conversions': 'sum'
    }).round(4)
    
    underperforming_campaigns = campaign_performance[campaign_performance['roas'] < 0.5]
    if not underperforming_campaigns.empty:
        total_wasted = underperforming_campaigns['spend'].sum()
        recommendations.append({
            "type": "campaign_review",
            "priority": "medium",
            "message": f"Review {len(underperforming_campaigns)} campaigns with ROAS < 0.5",
            "details": f"These campaigns spent ${total_wasted:.2f} with poor returns",
            "affected_campaigns": underperforming_campaigns.to_dict('index')
        })
    
    return recommendations

def _analyze_trends(df: pd.DataFrame, metric: str) -> Dict:
    """Analyze performance trends over time"""
    
    if metric not in df.columns:
        return {"error": f"Metric '{metric}' not found in data"}
    
    # Find the date column - be flexible about naming
    date_col = None
    for potential_date_col in ['date', 'Day', 'day']:
        if potential_date_col in df.columns:
            date_col = potential_date_col
            break
    
    if not date_col:
        return {"error": "No date column found for trend analysis"}
    
    # Group by date and calculate daily metrics
    try:
        daily_trends = df.groupby(date_col).agg({
            metric: 'mean',
            'spend': 'sum',
            'impressions': 'sum',
            'clicks': 'sum',
            'conversions': 'sum'
        }).round(4)
    except Exception as e:
        return {"error": f"Error calculating trends: {str(e)}"}
        
    if daily_trends.empty:
        return {"error": "No data available for trend analysis"}
    
    # Calculate trend direction
    if len(daily_trends) > 1:
        recent_avg = daily_trends[metric].tail(7).mean()  # Last 7 days
        earlier_avg = daily_trends[metric].head(7).mean()  # First 7 days
        
        if recent_avg > earlier_avg * 1.1:
            trend_direction = "improving"
        elif recent_avg < earlier_avg * 0.9:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"
    
    # Find best and worst days
    try:
        best_day = daily_trends[metric].idxmax()
        worst_day = daily_trends[metric].idxmin()
        
        return {
            "trend_direction": trend_direction,
            "daily_data": daily_trends.to_dict('index'),
            "best_day": {
                "date": str(best_day),
                "value": float(daily_trends.loc[best_day, metric])
            },
            "worst_day": {
                "date": str(worst_day), 
                "value": float(daily_trends.loc[worst_day, metric])
            },
            "average_value": float(daily_trends[metric].mean()),
            "data_points": len(daily_trends),
            "date_column_used": date_col
        }
    except Exception as e:
        return {"error": f"Error analyzing trend data: {str(e)}"}
    

def _generate_action_plan(df: pd.DataFrame, budget_increase_limit: float) -> Dict:
    """Generate detailed action plan with specific steps"""
    
    # Calculate performance metrics
    df['roas'] = df['conversions'] / (df['spend'] + 0.001)
    df['conversion_rate'] = df['conversions'] / (df['clicks'] + 0.001)
    df['cost_per_conversion'] = df['spend'] / (df['conversions'] + 0.001)
    
    action_plan = {
        "immediate_actions": [],  # Do today
        "weekly_actions": [],     # Do this week
        "monthly_actions": []     # Do this month
    }
    
    # IMMEDIATE ACTIONS (Do Today)
    
    # 1. Pause worst performers
    worst_performers = df[
        (df['spend'] >= 50) & 
        (df['roas'] < 0.5) & 
        (df['ctr'] < df['ctr'].quantile(0.2))
    ]
    
    if not worst_performers.empty:
        total_savings = worst_performers['spend'].sum()
        action_plan["immediate_actions"].append({
            "action": "PAUSE_ADS",
            "priority": "CRITICAL",
            "title": f"Pause {len(worst_performers)} underperforming ads",
            "description": f"These ads have ROAS < 0.5 and low CTR, wasting ${total_savings:.2f}",
            "specific_steps": [
                "1. Log into Meta Ads Manager / Google Ads",
                "2. Navigate to Ads tab",
                "3. Filter by the ad names listed below",
                "4. Select all and click 'Pause'",
                "5. Add note: 'Paused due to poor ROAS and CTR performance'"
            ],
            "ads_to_pause": worst_performers[['campaign_name', 'ad_name', 'spend', 'roas', 'ctr']].to_dict('records'),
            "expected_impact": f"Save ${total_savings:.2f}/month, no meaningful conversion loss",
            "time_required": "15 minutes"
        })
    
    # 2. Increase budget for top performers
    top_performers = df[
        (df['roas'] > df['roas'].quantile(0.8)) & 
        (df['ctr'] > df['ctr'].mean()) &
        (df['spend'] >= 100)
    ]
    
    if not top_performers.empty:
        action_plan["immediate_actions"].append({
            "action": "INCREASE_BUDGET",
            "priority": "HIGH",
            "title": f"Increase budget for {len(top_performers)} top-performing ads",
            "description": f"These ads have high ROAS and above-average CTR",
            "specific_steps": [
                "1. In Ads Manager, go to Campaign or Ad Set level",
                "2. Find the campaigns/ad sets listed below",
                "3. Increase daily budget by 25-50% (don't exceed platform recommendations)",
                "4. Monitor for 3-5 days to ensure performance maintains",
                "5. Repeat increase if performance stays strong"
            ],
            "ads_to_scale": top_performers[['campaign_name', 'ad_name', 'spend', 'roas', 'ctr']].head(10).to_dict('records'),
            "budget_increase_suggestion": f"Increase by {min(budget_increase_limit, 50)}%",
            "expected_impact": f"Potentially increase conversions by 20-40%",
            "time_required": "20 minutes"
        })
    
    # WEEKLY ACTIONS (Do This Week)
    
    # 3. Platform optimization
    platform_performance = df.groupby('source').agg({
        'roas': 'mean',
        'ctr': 'mean',
        'spend': 'sum',
        'conversions': 'sum'
    }).round(4)
    
    if len(platform_performance) > 1:
        best_platform = platform_performance['roas'].idxmax()
        worst_platform = platform_performance['roas'].idxmin()
        
        if platform_performance.loc[best_platform, 'roas'] > platform_performance.loc[worst_platform, 'roas'] * 1.3:
            spend_to_shift = platform_performance.loc[worst_platform, 'spend'] * 0.3  # Shift 30%
            
            action_plan["weekly_actions"].append({
                "action": "SHIFT_PLATFORM_BUDGET",
                "priority": "MEDIUM",
                "title": f"Shift ${spend_to_shift:.2f} from {worst_platform} to {best_platform}",
                "description": f"{best_platform} shows {platform_performance.loc[best_platform, 'roas']:.2f} ROAS vs {worst_platform} at {platform_performance.loc[worst_platform, 'roas']:.2f}",
                "specific_steps": [
                    f"1. In {worst_platform}, reduce campaign budgets by 30%",
                    f"2. In {best_platform}, create new campaigns or increase existing ones",
                    "3. Use same targeting as best-performing campaigns",
                    "4. Start with 50% of shifted budget, then scale up",
                    "5. Monitor daily for first week"
                ],
                "budget_shift_amount": f"${spend_to_shift:.2f}",
                "expected_impact": f"Improve overall ROAS by {((platform_performance.loc[best_platform, 'roas'] - platform_performance.loc[worst_platform, 'roas']) * 0.3):.2f}",
                "time_required": "2-3 hours over the week"
            })
    
    # 4. Campaign restructuring
    campaign_performance = df.groupby('campaign_name').agg({
        'roas': 'mean',
        'spend': 'sum',
        'conversions': 'sum',
        'ctr': 'mean'
    }).round(4)
    
    low_performing_campaigns = campaign_performance[
        (campaign_performance['roas'] < 1.0) & 
        (campaign_performance['spend'] > 500)
    ]
    
    if not low_performing_campaigns.empty:
        action_plan["weekly_actions"].append({
            "action": "RESTRUCTURE_CAMPAIGNS",
            "priority": "MEDIUM",
            "title": f"Restructure {len(low_performing_campaigns)} underperforming campaigns",
            "description": "These campaigns have ROAS < 1.0 despite significant spend",
            "specific_steps": [
                "1. Analyze audience overlap between campaigns",
                "2. Consolidate similar audiences into single campaigns",
                "3. Test new ad creatives in best-performing ad sets",
                "4. Adjust bidding strategy (if using auto, try manual)",
                "5. Review and tighten targeting parameters"
            ],
            "campaigns_to_restructure": low_performing_campaigns.head(5).to_dict('index'),
            "expected_impact": "Improve campaign ROAS by 0.3-0.8 points",
            "time_required": "4-6 hours"
        })
    
    # MONTHLY ACTIONS (Do This Month)
    
    # 5. Creative testing
    ad_groups = df.groupby(['campaign_name', 'ad_name']).agg({
        'ctr': 'mean',
        'roas': 'mean',
        'spend': 'sum'
    }).round(4)
    
    action_plan["monthly_actions"].append({
        "action": "CREATIVE_TESTING",
        "priority": "LOW",
        "title": "Launch creative testing for top campaigns",
        "description": "Test new ad creatives to prevent ad fatigue and improve performance",
        "specific_steps": [
            "1. Identify top 5 campaigns by spend and ROAS",
            "2. Create 3-4 new ad variations per campaign",
            "3. Use different headlines, images, or video hooks",
            "4. Run A/B tests with 70/30 budget split (existing/new)",
            "5. Let run for 2 weeks minimum before deciding",
            "6. Scale winning creatives, pause losing ones"
        ],
        "recommended_campaigns": campaign_performance.nlargest(5, 'roas').index.tolist(),
        "expected_impact": "Prevent ad fatigue, potentially improve CTR by 15-25%",
        "time_required": "6-8 hours over the month"
    })
    
    # 6. Audience expansion
    action_plan["monthly_actions"].append({
        "action": "AUDIENCE_EXPANSION",
        "priority": "LOW", 
        "title": "Expand audiences for successful campaigns",
        "description": "Scale reach while maintaining performance",
        "specific_steps": [
            "1. Identify campaigns with ROAS > 2.0 and stable performance",
            "2. Create lookalike audiences from existing converters",
            "3. Test interest expansion (add related interests)",
            "4. Try automatic placements if not already enabled",
            "5. Create campaigns for new geographic markets",
            "6. Start with 20% of original campaign budget"
        ],
        "recommended_for_expansion": campaign_performance[campaign_performance['roas'] > 2.0].index.tolist(),
        "expected_impact": "Increase total conversions by 25-50%",
        "time_required": "4-5 hours"
    })
    
    # Calculate overall impact
    total_current_spend = df['spend'].sum()
    total_current_conversions = df['conversions'].sum()
    current_roas = total_current_conversions / (total_current_spend + 0.001)
    
    # Estimate impact of all actions
    potential_savings = worst_performers['spend'].sum() if not worst_performers.empty else 0
    potential_conversion_increase = top_performers['conversions'].sum() * 0.3 if not top_performers.empty else 0
    
    action_plan["expected_overall_impact"] = {
        "current_monthly_spend": f"${total_current_spend:.2f}",
        "current_monthly_conversions": int(total_current_conversions),
        "current_roas": f"{current_roas:.2f}",
        "estimated_monthly_savings": f"${potential_savings:.2f}",
        "estimated_additional_conversions": int(potential_conversion_increase),
        "projected_new_roas": f"{((total_current_conversions + potential_conversion_increase) / (total_current_spend - potential_savings + 0.001)):.2f}"
    }
    
    return action_plan

def _calculate_budget_reallocation(df: pd.DataFrame, total_budget: float) -> Dict:
    """Calculate optimal budget allocation based on performance"""
    
    # Calculate performance metrics
    df['roas'] = df['conversions'] / (df['spend'] + 0.001)
    df['efficiency_score'] = (df['roas'] * df['ctr'] * 100)  # Combined performance score
    
    # Group by campaign for budget allocation
    campaign_performance = df.groupby('campaign_name').agg({
        'spend': 'sum',
        'conversions': 'sum',
        'roas': 'mean',
        'ctr': 'mean',
        'efficiency_score': 'mean'
    }).round(4)
    
    # Calculate current budget allocation
    current_total_spend = campaign_performance['spend'].sum()
    campaign_performance['current_budget_pct'] = (campaign_performance['spend'] / current_total_spend * 100).round(2)
    
    # Calculate optimal allocation based on efficiency score
    total_efficiency = campaign_performance['efficiency_score'].sum()
    campaign_performance['optimal_budget_pct'] = (campaign_performance['efficiency_score'] / total_efficiency * 100).round(2)
    campaign_performance['optimal_budget_amount'] = (campaign_performance['optimal_budget_pct'] / 100 * total_budget).round(2)
    
    # Calculate the difference (reallocation needed)
    campaign_performance['budget_change_pct'] = (campaign_performance['optimal_budget_pct'] - campaign_performance['current_budget_pct']).round(2)
    campaign_performance['budget_change_amount'] = (campaign_performance['optimal_budget_amount'] - campaign_performance['spend']).round(2)
    
    # Separate campaigns that should get more vs less budget
    increase_budget = campaign_performance[campaign_performance['budget_change_amount'] > 50].sort_values('budget_change_amount', ascending=False)
    decrease_budget = campaign_performance[campaign_performance['budget_change_amount'] < -50].sort_values('budget_change_amount', ascending=True)
    maintain_budget = campaign_performance[abs(campaign_performance['budget_change_amount']) <= 50]
    
    # Create detailed reallocation steps
    reallocation_steps = []
    
    # Step 1: Decrease underperforming campaigns
    if not decrease_budget.empty:
        total_to_decrease = abs(decrease_budget['budget_change_amount'].sum())
        reallocation_steps.append({
            "step": 1,
            "action": "DECREASE_BUDGETS",
            "title": f"Reduce budget for {len(decrease_budget)} underperforming campaigns",
            "total_amount_to_reduce": f"${total_to_decrease:.2f}",
            "campaigns": [
                {
                    "campaign_name": campaign,
                    "current_spend": f"${row['spend']:.2f}",
                    "recommended_budget": f"${row['optimal_budget_amount']:.2f}", 
                    "budget_decrease": f"${abs(row['budget_change_amount']):.2f}",
                    "reason": f"Low efficiency score: {row['efficiency_score']:.1f}"
                }
                for campaign, row in decrease_budget.head(10).iterrows()
            ]
        })
    
    # Step 2: Increase high-performing campaigns
    if not increase_budget.empty:
        total_to_increase = increase_budget['budget_change_amount'].sum()
        reallocation_steps.append({
            "step": 2,
            "action": "INCREASE_BUDGETS",
            "title": f"Increase budget for {len(increase_budget)} high-performing campaigns",
            "total_amount_to_increase": f"${total_to_increase:.2f}",
            "campaigns": [
                {
                    "campaign_name": campaign,
                    "current_spend": f"${row['spend']:.2f}",
                    "recommended_budget": f"${row['optimal_budget_amount']:.2f}",
                    "budget_increase": f"${row['budget_change_amount']:.2f}",
                    "reason": f"High efficiency score: {row['efficiency_score']:.1f}, ROAS: {row['roas']:.2f}"
                }
                for campaign, row in increase_budget.head(10).iterrows()
            ]
        })
    
    # Calculate impact
    current_total_conversions = campaign_performance['conversions'].sum()
    current_avg_roas = (campaign_performance['conversions'].sum() / campaign_performance['spend'].sum())
    
    # Estimate new performance (simplified model)
    weighted_roas = (campaign_performance['roas'] * campaign_performance['optimal_budget_amount']).sum() / total_budget
    estimated_new_conversions = total_budget * weighted_roas
    
    return {
        "current_allocation": campaign_performance[['spend', 'current_budget_pct', 'roas', 'efficiency_score']].to_dict('index'),
        "optimal_allocation": campaign_performance[['optimal_budget_amount', 'optimal_budget_pct', 'budget_change_amount']].to_dict('index'),
        "reallocation_steps": reallocation_steps,
        "summary": {
            "total_budget": f"${total_budget:.2f}",
            "campaigns_to_decrease": len(decrease_budget),
            "campaigns_to_increase": len(increase_budget), 
            "campaigns_to_maintain": len(maintain_budget),
            "current_monthly_conversions": int(current_total_conversions),
            "current_avg_roas": f"{current_avg_roas:.2f}",
            "projected_monthly_conversions": int(estimated_new_conversions),
            "projected_avg_roas": f"{weighted_roas:.2f}",
            "estimated_improvement": f"{((estimated_new_conversions - current_total_conversions) / current_total_conversions * 100):.1f}% more conversions"
        }
    }

@router.post("/file-insights")
async def file_insights(meta_csv: UploadFile = File(...), google_csv: UploadFile = File(...)):
    """
    Upload Meta and Google Ads CSVs and get unified ad insights.
    """
    try:
        # --- Meta CSV ---
        meta_rename = {
            # Updated Meta/Facebook Ads column mappings based on your new headers
            'Ad group status': 'ad_group_status',
            'Ad group': 'adset_name',
            'Campaign': 'campaign_name',
            'Status': 'ad_status',
            'Status reasons': 'status_reasons',
            'Currency code': 'currency',
            'Target CPA': 'target_cpa',
            'Ad group type': 'ad_group_type',
            'Impr.': 'impressions',
            'Interactions': 'clicks',  # Facebook uses 'Interactions' instead of 'Clicks'
            'Interaction rate': 'ctr',  # Facebook uses 'Interaction rate' instead of 'CTR'
            'Avg. cost': 'cpc',
            'Cost': 'spend',
            'Brand Inclusions': 'brand_inclusions',
            'Locations of interest': 'locations_of_interest',
            'Conv. rate': 'conversion_rate',
            'Conversions': 'conversions',
            'Cost / conv.': 'cost_per_conversion',

            # Legacy Meta columns (keep for backwards compatibility)
            'Campaign name': 'campaign_name',
            'Ad Set Name': 'adset_name',
            'Ad name': 'ad_name',
            'Day': 'date',
            'Impressions': 'impressions',
            'Amount spent (ZAR)': 'spend',
            'Amount spent': 'spend',
            'Spent': 'spend',
            'Amount Spent': 'spend',
            'Reach': 'reach',
            'Results': 'conversions',
            'Cost per results': 'cost_per_result',
            'Ad delivery': 'ad_delivery',
            'Bid': 'bid_amount',
            'Bid type': 'bid_type',
            'Ad set budget': 'adset_budget',
            'Ad set budget type': 'adset_budget_type',
            'Last significant edit': 'last_edit',
            'Attribution setting': 'attribution_setting',
            'Result indicator': 'result_indicator',
            'Quality ranking': 'quality_ranking',
            'Engagement rate ranking': 'engagement_ranking',
            'Conversion rate ranking': 'conversion_ranking',
            'Result type': 'result_type',
            'Objective': 'objective',
            'Reporting starts': 'reporting_starts',
            'Reporting ends': 'reporting_ends',
            'Ends': 'campaign_ends',
        }

        # Use encoding detection for Meta CSV with better separator detection
        meta_df = _detect_encoding_and_read_csv(
            meta_csv.file,
            meta_csv.filename,
            sep=None,  # Let pandas auto-detect separator
            engine='python'
        )

        # If auto-detection failed and we have concatenated columns, try semicolon separator
        if len(meta_df.columns) <= 3 and any(';' in str(col) for col in meta_df.columns):
            print("🔄 Meta CSV appears to use semicolon separator, re-reading...")
            meta_csv.file.seek(0)
            meta_df = _detect_encoding_and_read_csv(
                meta_csv.file,
                meta_csv.filename,
                sep=';',  # Force semicolon separator
                engine='python'
            )

        print(f"✅ Meta CSV loaded successfully: {len(meta_df)} rows, columns: {[str(col) for col in meta_df.columns]}")

        # Debug: Check for spend-related columns
        spend_related = [col for col in meta_df.columns if 'spent' in col.lower() or 'spend' in col.lower() or 'cost' in col.lower()]
        print(f"🔍 Meta spend-related columns found: {spend_related}")

        # Only rename columns that exist in the CSV
        existing_meta_columns = {k: v for k, v in meta_rename.items() if k in meta_df.columns}
        print(f"🔍 Meta columns to rename: {len(existing_meta_columns)} out of {len(meta_rename)} possible")

        meta_df = meta_df.rename(columns=existing_meta_columns)
        meta_df['source'] = 'meta_ads'

        # --- Google CSV ---
        try:
            google_rename = {
                # Updated Google Ads column mappings based on your new headers
                'Most specific location target (User location)': 'location_target',
                'Campaign': 'campaign_name',
                'Impr.': 'impressions',
                'CTR': 'ctr',
                'Clicks': 'clicks',
                'Currency code': 'currency',
                'Cost': 'spend',
                'Conversions': 'conversions',
                'Cost / conv.': 'cost_per_conversion',
                'Conv. rate': 'conversion_rate',

                # Legacy Google Ads columns (keep for backwards compatibility)
                'Ad group': 'adset_name',
                'Ad name': 'ad_name',
                'Campaign type': 'campaign_type',
                'Campaign subtype': 'campaign_subtype',
                'Avg. CPC': 'cpc',
                'View-through conv.': 'view_through_conversions',
                'Ad state': 'ad_state',
                'Ad type': 'ad_type',
                'Final URL': 'final_url',
                'Beacon URLs': 'beacon_urls',
                'Business name': 'business_name',
                'Display URL': 'display_url',
                'ad.device_preference': 'device_preference',

                # All Headlines (1-15)
                'Headline 1': 'headline_1',
                'Headline 1 position': 'headline_1_position',
                'Headline 2': 'headline_2',
                'Headline 2 position': 'headline_2_position',
                'Headline 3': 'headline_3',
                'Headline 3 position': 'headline_3_position',
                'Headline 4': 'headline_4',
                'Headline 4 position': 'headline_4_position',
                'Headline 5': 'headline_5',
                'Headline 5 position': 'headline_5_position',
                'Headline 6': 'headline_6',
                'Headline 6 position': 'headline_6_position',
                'Headline 7': 'headline_7',
                'Headline 7 position': 'headline_7_position',
                'Headline 8': 'headline_8',
                'Headline 8 position': 'headline_8_position',
                'Headline 9': 'headline_9',
                'Headline 9 position': 'headline_9_position',
                'Headline 10': 'headline_10',
                'Headline 10 position': 'headline_10_position',
                'Headline 11': 'headline_11',
                'Headline 11 position': 'headline_11_position',
                'Headline 12': 'headline_12',
                'Headline 12 position': 'headline_12_position',
                'Headline 13': 'headline_13',
                'Headline 13 position': 'headline_13_position',
                'Headline 14': 'headline_14',
                'Headline 14 position': 'headline_14_position',
                'Headline 15': 'headline_15',
                'Headline 15 position': 'headline_15_position',

                # All Descriptions (1-4)
                'Description 1': 'description_1',
                'Description 1 position': 'description_1_position',
                'Description 2': 'description_2',
                'Description 2 position': 'description_2_position',
                'Description 3': 'description_3',
                'Description 3 position': 'description_3_position',
                'Description 4': 'description_4',
                'Description 4 position': 'description_4_position',

                # URLs and tracking
                'Ad final URL': 'ad_final_url',
                'Ad mobile final URL': 'ad_mobile_final_url',
                'Mobile final URL': 'mobile_final_url',
                'Tracking template': 'tracking_template',
                'Final URL suffix': 'final_url_suffix',
                'Custom parameter': 'custom_parameter',
                'Path 1': 'path_1',
                'Path 2': 'path_2',

                # Contact and verification
                'Country': 'country',
                'Phone number': 'phone_number',
                'Verification URL': 'verification_url',
                'Call reporting': 'call_reporting',
                'Call conversion': 'call_conversion'
            }

            # Try to read Google CSV with auto-detection first
            google_df = _detect_encoding_and_read_csv(
                google_csv.file,
                google_csv.filename,
                sep=None,  # Let pandas auto-detect separator
                engine='python'
            )

            # Check if we have the concatenated column issue (semicolon-separated data in one column)
            if len(google_df.columns) == 1 and ';' in str(google_df.columns[0]):
                print("🔄 Google CSV appears to use semicolon separator, re-reading...")
                google_csv.file.seek(0)
                google_df = _detect_encoding_and_read_csv(
                    google_csv.file,
                    google_csv.filename,
                    sep=';',  # Force semicolon separator
                    engine='python'
                )

            # Alternative check: if we have very few columns but expect more
            elif len(google_df.columns) <= 3:
                print("🔄 Google CSV has too few columns, trying semicolon separator...")
                google_csv.file.seek(0)
                try:
                    google_df = _detect_encoding_and_read_csv(
                        google_csv.file,
                        google_csv.filename,
                        sep=';',  # Force semicolon separator
                        engine='python'
                    )
                except Exception as semicolon_error:
                    print(f"⚠️ Semicolon separator also failed: {str(semicolon_error)}")
                    # Continue with the original dataframe
                    pass

            print(f"✅ Google CSV loaded successfully: {len(google_df)} rows, columns: {[str(col) for col in google_df.columns[:10]]}...")

            # Debug: Check for important columns
            important_cols = ['Campaign', 'Impr.', 'Clicks', 'Cost', 'Conversions']
            missing_important = [col for col in important_cols if col not in google_df.columns]
            if missing_important:
                print(f"⚠️ Missing important Google columns: {missing_important}")
                print(f"🔍 Available columns: {[str(col) for col in google_df.columns[:10]]}")

            # Only rename columns that exist in the dataframe
            existing_columns = {k: v for k, v in google_rename.items() if k in google_df.columns}
            print(f"🔍 Google columns to rename: {len(existing_columns)} out of {len(google_rename)} possible")

            if existing_columns:
                google_df = google_df.rename(columns=existing_columns)
                print(f"✅ Successfully renamed {len(existing_columns)} Google columns")

            google_df['source'] = 'google_ads'
        except Exception as e:
            error_msg = str(e)
            if "Expected" in error_msg and "fields" in error_msg and "line" in error_msg:
                # Extract line number from error if possible
                import re
                line_match = re.search(r'line (\d+)', error_msg)
                line_num = line_match.group(1) if line_match else "unknown"

                raise HTTPException(
                    status_code=400,
                    detail=f"❌ CSV PARSING ERROR in Google file '{google_csv.filename}': Field count mismatch at line {line_num}. This usually means:\n" +
                           f"1. Extra comma in a text field (like 'Company, LLC' should be '\"Company, LLC\"')\n" +
                           f"2. Unescaped quotes in ad text\n" +
                           f"3. Line breaks within a cell\n" +
                           f"💡 SOLUTION: Open the CSV in Excel, check line {line_num}, and re-save as CSV with proper quoting."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ ERROR in Google CSV file '{google_csv.filename}': {error_msg}. Try re-exporting the CSV from Google Ads or check for data formatting issues."
                )

        # Combine dataframes
        df = pd.concat([meta_df, google_df], ignore_index=True, sort=False)
        print(f"Combined: {len(df)} rows")

        # Parse date columns
        for col in ['date', 'reporting_starts', 'reporting_ends']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Ensure all required numeric columns exist and are properly typed
        required_numeric_cols = ['impressions', 'clicks', 'spend', 'conversions', 'reach']
        for col in required_numeric_cols:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Calculate CTR first (needed for clicks calculation)
        if 'ctr' not in df.columns:
            # For Meta ads, we need to calculate CTR differently since they don't provide clicks
            # We'll set CTR to 0 initially and calculate it after we have clicks
            df['ctr'] = 0.0
        else:
            df['ctr'] = pd.to_numeric(df['ctr'], errors='coerce').fillna(0.0)

        # Calculate clicks for Meta ads (they don't provide clicks directly)
        # For Meta rows where clicks is 0 but we have impressions and CTR > 0
        meta_mask = df['source'] == 'meta_ads'
        if meta_mask.any():
            # For Meta, if we have CTR data, calculate clicks from CTR and impressions
            meta_with_ctr = meta_mask & (df['ctr'] > 0)
            if meta_with_ctr.any():
                df.loc[meta_with_ctr, 'clicks'] = (df.loc[meta_with_ctr, 'impressions'] * df.loc[meta_with_ctr, 'ctr'] / 100).round()

            # For Meta rows without CTR, estimate a reasonable CTR based on industry average (1-2%)
            meta_no_ctr = meta_mask & (df['ctr'] == 0) & (df['impressions'] > 0)
            if meta_no_ctr.any():
                estimated_ctr = 1.5  # 1.5% industry average
                df.loc[meta_no_ctr, 'clicks'] = (df.loc[meta_no_ctr, 'impressions'] * estimated_ctr / 100).round()
                df.loc[meta_no_ctr, 'ctr'] = estimated_ctr

        # Now recalculate CTR for any remaining rows without it
        missing_ctr = (df['ctr'] == 0) & (df['clicks'] > 0) & (df['impressions'] > 0)
        if missing_ctr.any():
            df.loc[missing_ctr, 'ctr'] = (df.loc[missing_ctr, 'clicks'] / df.loc[missing_ctr, 'impressions'] * 100).round(2)

        # Calculate CPC
        if 'cpc' not in df.columns:
            df['cpc'] = 0.0
        else:
            df['cpc'] = pd.to_numeric(df['cpc'], errors='coerce').fillna(0.0)

        missing_cpc = (df['cpc'] == 0) & (df['clicks'] > 0)
        if missing_cpc.any():
            df.loc[missing_cpc, 'cpc'] = (df.loc[missing_cpc, 'spend'] / df.loc[missing_cpc, 'clicks']).round(2)

        # Calculate CPM
        if 'cpm' not in df.columns:
            df['cpm'] = 0.0
        else:
            df['cpm'] = pd.to_numeric(df['cpm'], errors='coerce').fillna(0.0)

        missing_cpm = (df['cpm'] == 0) & (df['impressions'] > 0)
        if missing_cpm.any():
            df.loc[missing_cpm, 'cpm'] = (df.loc[missing_cpm, 'spend'] / df.loc[missing_cpm, 'impressions'] * 1000).round(2)

        # Ensure required string columns exist
        required_string_cols = ['campaign_name', 'ad_name', 'adset_name']
        for col in required_string_cols:
            if col not in df.columns:
                df[col] = 'Unknown'
            else:
                df[col] = df[col].fillna('Unknown').astype(str)

        # Process optional string columns from all data sources
        optional_string_cols = [
            # Google Ads creative columns
            'ad_state', 'ad_type', 'final_url', 'beacon_urls', 'device_preference',
            'business_name', 'display_url', 'country', 'phone_number', 'verification_url',
            'call_reporting', 'call_conversion', 'path_1', 'path_2', 'mobile_final_url',
            'tracking_template', 'final_url_suffix', 'custom_parameter', 'currency',
            'campaign_type', 'campaign_subtype', 'ad_final_url', 'ad_mobile_final_url',
            
            # All Google Ads headlines (1-15)
            'headline_1', 'headline_2', 'headline_3', 'headline_4', 'headline_5',
            'headline_6', 'headline_7', 'headline_8', 'headline_9', 'headline_10',
            'headline_11', 'headline_12', 'headline_13', 'headline_14', 'headline_15',
            'headline_1_position', 'headline_2_position', 'headline_3_position', 'headline_4_position', 'headline_5_position',
            'headline_6_position', 'headline_7_position', 'headline_8_position', 'headline_9_position', 'headline_10_position',
            'headline_11_position', 'headline_12_position', 'headline_13_position', 'headline_14_position', 'headline_15_position',
            
            # All Google Ads descriptions (1-4)  
            'description_1', 'description_2', 'description_3', 'description_4',
            'description_1_position', 'description_2_position', 'description_3_position', 'description_4_position',
            
            # Meta Ads specific columns
            'ad_delivery', 'bid_type', 'adset_budget_type', 'last_edit', 'attribution_setting',
            'result_indicator', 'quality_ranking', 'engagement_ranking', 'conversion_ranking',
            'result_type', 'objective',
            
            # HubSpot specific columns
            'entity', 'network', 'status', 'tracking_status', 'account_name'
        ]
        for col in optional_string_cols:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # Remove rows with no campaign name - FIXED: Don't remove 'Unknown'
        df = df[df['campaign_name'].notna() & (df['campaign_name'] != '') & (df['campaign_name'] != 'nan')]

        if df.empty:
            return {
                "total_records": 0,
                "error": "No valid data found after processing.",
                "debug_info": {
                    "meta_records_loaded": len(meta_df),
                    "google_records_loaded": len(google_df),
                    "ga_records_loaded": len(ga_df) if not ga_df.empty else 0,
                    "hubspot_records_loaded": len(hubspot_df) if not hubspot_df.empty else 0,
                    "suggestion": "Check that your CSV files contain valid campaign data with proper column headers."
                }
            }

        # Get data date range - be flexible about date column names
        date_col = None
        for potential_date_col in ['date', 'Day', 'day']:
            if potential_date_col in df.columns:
                date_col = potential_date_col
                break
        
        print(f"🗓️ Using '{date_col}' column for date range calculation")
        
        if date_col and not df[date_col].isna().all():
            try:
                data_date_range = {
                    "earliest": str(df[date_col].min()),
                    "latest": str(df[date_col].max())
                }
                print(f"✅ Date range calculated: {data_date_range}")
            except Exception as date_range_error:
                print(f"⚠️ Error calculating date range: {str(date_range_error)}")
                data_date_range = {
                    "earliest": None,
                    "latest": None
                }
        else:
            print("ℹ️ No valid date column found or all dates are null")
            data_date_range = {
                "earliest": None,
                "latest": None
            }

        # Run ALL analysis functions with error handling
        try:
            performance_analysis = _analyze_ad_performance(df)
        except Exception as e:
            print(f"⚠️ Error in performance analysis: {str(e)}")
            performance_analysis = {"error": "Performance analysis failed", "details": str(e)}
        
        try:
            campaign_comparison = _compare_campaigns(df)
        except Exception as e:
            print(f"⚠️ Error in campaign comparison: {str(e)}")
            campaign_comparison = {"error": "Campaign comparison failed", "details": str(e)}
        
        try:
            recommendations = _generate_recommendations(df, min_spend=100)  # Default $100 minimum spend
        except Exception as e:
            print(f"⚠️ Error generating recommendations: {str(e)}")
            recommendations = [{"type": "error", "message": f"Recommendations failed: {str(e)}"}]
        
        try:
            action_plan = _generate_action_plan(df, budget_increase_limit=50)  # Default 50% max increase
        except Exception as e:
            print(f"⚠️ Error generating action plan: {str(e)}")
            action_plan = {"error": "Action plan generation failed", "details": str(e)}
        
        try:
            budget_reallocation = _calculate_budget_reallocation(df, total_budget=10000)  # Default $10k budget
        except Exception as e:
            print(f"⚠️ Error calculating budget reallocation: {str(e)}")
            budget_reallocation = {"error": "Budget reallocation failed", "details": str(e)}

        # Analyze trends for key metrics
        trend_metrics = ['ctr', 'cpc', 'cpm', 'conversions']
        trends_analysis = {}
        for metric in trend_metrics:
            if metric in df.columns:
                try:
                    trends_analysis[metric] = _analyze_trends(df, metric)
                except Exception as e:
                    print(f"⚠️ Error analyzing trends for {metric}: {str(e)}")
                    trends_analysis[metric] = {"error": f"Trend analysis failed for {metric}", "details": str(e)}

        # Clean up any NaN/infinite values before JSON serialization
        def clean_for_json(obj):
            """Recursively clean NaN and infinite values from nested data structures"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, float):
                if pd.isna(obj) or obj == float('inf') or obj == float('-inf'):
                    return 0.0
                return obj
            elif hasattr(obj, 'item'):  # numpy scalars
                try:
                    val = obj.item()
                    if isinstance(val, float) and (pd.isna(val) or val == float('inf') or val == float('-inf')):
                        return 0.0
                    return val
                except (ValueError, TypeError):
                    return 0.0
            else:
                return obj
        
        # Clean all analysis results
        performance_analysis = clean_for_json(performance_analysis)
        campaign_comparison = clean_for_json(campaign_comparison)
        recommendations = clean_for_json(recommendations)
        action_plan = clean_for_json(action_plan)
        budget_reallocation = clean_for_json(budget_reallocation)
        trends_analysis = clean_for_json(trends_analysis)

        # Return comprehensive structured response
        return {
            "summary": {
                "total_records": len(df),
                "data_sources": {
                    "meta_ads_records": len(df[df['source'] == 'meta_ads']),
                    "google_ads_records": len(df[df['source'] == 'google_ads']),
                    "google_analytics_records": len(df[df['source'] == 'google_analytics']) if 'google_analytics' in df['source'].values else 0,
                    "hubspot_records": len(df[df['source'] == 'hubspot']) if 'hubspot' in df['source'].values else 0,
                    "total_sources": len(df['source'].unique())
                },
                "data_date_range": data_date_range,
                "total_campaigns": len(df['campaign_name'].unique()),
                "total_spend": clean_for_json(df['spend'].sum()),
                "total_conversions": clean_for_json(df['conversions'].sum()),
                "overall_roas": clean_for_json(df['conversions'].sum() / (df['spend'].sum() + 0.001))
            },

            "performance_analysis": {
                "description": "What works and what doesn't work - top and bottom performers by metrics",
                **performance_analysis
            },

            "campaign_comparison": {
                "description": "Side-by-side comparison of all campaigns with rankings",
                **campaign_comparison
            },

            "recommendations": {
                "description": "Actionable recommendations for immediate optimization",
                "total_recommendations": len(recommendations),
                "recommendations": recommendations
            },

            "action_plan": {
                "description": "Detailed step-by-step action plan organized by priority and timeline",
                **action_plan
            },

            "budget_reallocation": {
                "description": "Optimal budget allocation based on performance efficiency",
                **budget_reallocation
            },

            "trends_analysis": {
                "description": "Performance trends over time for key metrics",
                "metrics_analyzed": list(trends_analysis.keys()),
                "trends": trends_analysis
            },

            "insights_summary": {
                "key_findings": [
                    f"Analyzed {len(df)} records from {len(df['source'].unique())} data sources across {len(df['campaign_name'].unique())} campaigns",
                    f"Data sources: {', '.join([str(source) for source in df['source'].unique()])}",
                    f"Total spend: ${df['spend'].sum():,.2f} with {df['conversions'].sum():.0f} conversions",
                    f"Overall ROAS: {df['conversions'].sum() / (df['spend'].sum() + 0.001):.2f}",
                    f"Average CTR: {df['ctr'].mean():.2f}%",
                    f"Average CPC: ${df['cpc'].mean():.2f}",
                    f"Generated {len(recommendations)} actionable recommendations"
                ],
                "next_steps": [
                    "Review immediate actions in the action plan",
                    "Implement high-priority recommendations first",
                    "Monitor performance changes for 3-5 days",
                    "Execute weekly and monthly action items",
                    "Consider budget reallocation suggestions"
                ]
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions (these have specific error messages)
        raise
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = str(e)
        
        # Add detailed debugging for the error
        print(f"🚨 UNEXPECTED ERROR CAUGHT: {error_msg}")
        print(f"🚨 Error type: {type(e).__name__}")
        print(f"🚨 Full error details: {repr(e)}")
        
        # Import traceback to get full stack trace
        import traceback
        print(f"🚨 Stack trace:")
        traceback.print_exc()
        
        if "Expected" in error_msg and "fields" in error_msg and "saw" in error_msg:
            raise HTTPException(
                status_code=400, 
                detail=f"❌ CSV FORMAT ERROR: {error_msg}. This usually indicates a malformed CSV file. Please check for: 1) Extra commas in text fields, 2) Unescaped quotes, 3) Inconsistent number of columns. Try opening the file in Excel and re-saving as CSV."
            )
        elif error_msg.strip() == 'date':
            raise HTTPException(
                status_code=400,
                detail=f"❌ DATE COLUMN ERROR: There's an issue with the 'date' column in your CSV files. Common causes:\n" +
                       f"1. The 'date' column contains invalid date formats\n" +
                       f"2. The 'date' column name appears multiple times\n" +
                       f"3. There's a conflict between Meta 'Day' and Google 'date' columns\n" +
                       f"4. Missing or empty date values\n" +
                       f"💡 SOLUTION: Check your CSV files and ensure date columns have consistent formatting (YYYY-MM-DD or similar)."
            )
        elif len(error_msg.strip()) < 50 and not any(char in error_msg for char in [' ', '\n', '\t']):
            # Single word/column name error
            raise HTTPException(
                status_code=400,
                detail=f"❌ COLUMN PROCESSING ERROR: Issue with '{error_msg.strip()}' in your CSV files. This could be:\n" +
                       f"1. Missing or malformed data in the '{error_msg.strip()}' column\n" +
                       f"2. Duplicate column names causing conflicts\n" +
                       f"3. Incompatible data types\n" +
                       f"💡 SOLUTION: Check your CSV files for issues with the '{error_msg.strip()}' column or re-export from the original source."
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"❌ UNEXPECTED ERROR: {error_msg}. Error type: {type(e).__name__}. Please check your CSV files and try again."
            )
