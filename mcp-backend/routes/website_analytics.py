from fastapi import APIRouter, HTTPException, Form
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
import data_integrator

router = APIRouter()

@router.post("/user-journey-analysis")
async def user_journey_analysis(request: str = Form(...)):
    """
    Analyze user journey from ads to conversions, identifying drop-off points
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    if not all([user_id, start_date, end_date]):
        raise HTTPException(status_code=400, detail="user_id, start_date, and end_date are required")
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch detailed GA4 funnel data
        ga4_funnel_data = await _fetch_ga4_funnel_data(user_id, start_date, end_date)
        
        # Fetch ad data for correlation
        ad_data = await data_integrator_instance.fetch_specific_data(
            connector_names=['meta_ads', 'google_ads'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Analyze the user journey
        journey_analysis = _analyze_user_journey(ga4_funnel_data, ad_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            **journey_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing user journey: {str(e)}")

@router.post("/drop-off-analysis")
async def drop_off_analysis(request: str = Form(...)):
    """
    Identify specific reasons why users are dropping off at each funnel step
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    funnel_steps = req_data.get('funnel_steps', ['landing_page', 'product_page', 'cart', 'checkout', 'purchase'])
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch detailed behavioral data
        behavioral_data = await _fetch_detailed_ga4_data(user_id, start_date, end_date)
        
        # Analyze drop-offs with reasons
        drop_off_insights = _analyze_drop_offs_with_reasons(behavioral_data, funnel_steps)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "funnel_steps": funnel_steps,
            **drop_off_insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing drop-offs: {str(e)}")

@router.post("/conversion-funnel-optimization")
async def conversion_funnel_optimization(request: str = Form(...)):
    """
    Generate specific recommendations to fix conversion funnel issues
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Get comprehensive funnel data
        ga4_data = await _fetch_detailed_ga4_data(user_id, start_date, end_date)
        ad_data = await data_integrator_instance.fetch_specific_data(
            connector_names=['meta_ads', 'google_ads'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Generate optimization recommendations
        optimization_plan = _generate_funnel_optimization_plan(ga4_data, ad_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            **optimization_plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating optimization plan: {str(e)}")

@router.post("/traffic-quality-analysis")
async def traffic_quality_analysis(request: str = Form(...)):
    """
    Analyze the quality of traffic from different ad sources and campaigns
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch GA4 data with traffic source details
        ga4_data = await _fetch_traffic_quality_data(user_id, start_date, end_date)
        
        # Fetch ad performance data
        ad_data = await data_integrator_instance.fetch_specific_data(
            connector_names=['meta_ads', 'google_ads'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Analyze traffic quality
        quality_analysis = _analyze_traffic_quality(ga4_data, ad_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            **quality_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing traffic quality: {str(e)}")

async def _fetch_ga4_funnel_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch detailed GA4 data for funnel analysis"""
    
    # Get the GA4 connector for this user
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch funnel-specific data
    funnel_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'date',
            'sessionDefaultChannelGrouping',
            'sessionSourceMedium', 
            'sessionCampaignName',
            'pagePath',
            'eventName',
            'deviceCategory'
        ],
        metrics=[
            'sessions',
            'users', 
            'pageviews',
            'engagementRate',
            'avgSessionDuration',
            'conversions',
            'eventCount',
            'engagementRate',
            'exitRate'
        ]
    )
    
    return funnel_data

async def _fetch_detailed_ga4_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch detailed behavioral GA4 data"""
    
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch detailed behavioral data
    behavioral_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'date',
            'sessionDefaultChannelGrouping',
            'sessionSourceMedium',
            'sessionCampaignName',
            'pagePath',
            'pageTitle',
            'eventName',
            'deviceCategory',
            'operatingSystem',
            'browser',
            'country',
            'city'
        ],
        metrics=[
            'sessions',
            'users',
            'newUsers',
            'pageviews',
            'screenPageViews', 
            'engagementRate',
            'avgSessionDuration',
            'conversions',
            'conversionRate',
            'eventCount',
            'engagementRate',
            'exitRate',
            'sessionConversionRate'
        ]
    )
    
    return behavioral_data

async def _fetch_traffic_quality_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch GA4 data focused on traffic quality metrics"""
    
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch traffic quality data
    quality_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'sessionDefaultChannelGrouping',
            'sessionSourceMedium',
            'sessionCampaignName',
            'deviceCategory'
        ],
        metrics=[
            'sessions',
            'users',
            'engagementRate',
            'avgSessionDuration',
            'conversions',
            'conversionRate',
            'engagementRate',
            'pageviewsPerSession',
            'eventCountPerSession'
        ]
    )
    
    return quality_data

def _analyze_user_journey(ga4_data: pd.DataFrame, ad_data: pd.DataFrame) -> Dict:
    """Analyze the complete user journey from ads to conversion"""
    
    if ga4_data.empty:
        return {"error": "No GA4 data available for analysis"}
    
    # Calculate funnel metrics
    funnel_steps = {
        'ad_clicks': int(ad_data['clicks'].sum()) if not ad_data.empty else 0,
        'website_sessions': int(ga4_data['sessions'].sum()),
        'engaged_sessions': int(ga4_data[ga4_data['engagementRate'] > 0]['sessions'].sum()) if 'engagementRate' in ga4_data.columns else 0,
        'conversions': int(ga4_data['conversions'].sum()) if 'conversions' in ga4_data.columns else 0
    }
    
    # Calculate conversion rates at each step
    conversion_rates = {}
    if funnel_steps['ad_clicks'] > 0:
        conversion_rates['click_to_session'] = (funnel_steps['website_sessions'] / funnel_steps['ad_clicks']) * 100
    
    if funnel_steps['website_sessions'] > 0:
        conversion_rates['session_to_engagement'] = (funnel_steps['engaged_sessions'] / funnel_steps['website_sessions']) * 100
        conversion_rates['session_to_conversion'] = (funnel_steps['conversions'] / funnel_steps['website_sessions']) * 100
    
    # Identify biggest drop-off points
    drop_offs = {}
    if funnel_steps['ad_clicks'] > 0 and funnel_steps['website_sessions'] > 0:
        drop_offs['ads_to_website'] = {
            'lost_users': funnel_steps['ad_clicks'] - funnel_steps['website_sessions'],
            'drop_off_rate': ((funnel_steps['ad_clicks'] - funnel_steps['website_sessions']) / funnel_steps['ad_clicks']) * 100,
            'potential_issue': 'Ad targeting mismatch, slow loading times, or technical issues'
        }
    
    if funnel_steps['website_sessions'] > 0 and funnel_steps['engaged_sessions'] > 0:
        drop_offs['website_to_engagement'] = {
            'lost_users': funnel_steps['website_sessions'] - funnel_steps['engaged_sessions'],
            'drop_off_rate': ((funnel_steps['website_sessions'] - funnel_steps['engaged_sessions']) / funnel_steps['website_sessions']) * 100,
            'potential_issue': 'Poor landing page experience, slow loading, or irrelevant content'
        }
    
    if funnel_steps['engaged_sessions'] > 0 and funnel_steps['conversions'] > 0:
        drop_offs['engagement_to_conversion'] = {
            'lost_users': funnel_steps['engaged_sessions'] - funnel_steps['conversions'],
            'drop_off_rate': ((funnel_steps['engaged_sessions'] - funnel_steps['conversions']) / funnel_steps['engaged_sessions']) * 100,
            'potential_issue': 'Checkout issues, pricing concerns, or trust/security concerns'
        }
    
    # Traffic source analysis
    if not ga4_data.empty and 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_performance = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        source_performance['conversion_rate'] = (source_performance['conversions'] / source_performance['sessions'] * 100).round(2)
        source_performance = source_performance.to_dict('index')
    else:
        source_performance = {}
    
    return {
        "funnel_overview": funnel_steps,
        "conversion_rates": conversion_rates,
        "drop_off_analysis": drop_offs,
        "traffic_source_performance": source_performance,
        "total_users_lost": sum([drop['lost_users'] for drop in drop_offs.values()]),
        "biggest_drop_off_stage": max(drop_offs.items(), key=lambda x: x[1]['drop_off_rate'])[0] if drop_offs else None
    }

def _analyze_drop_offs_with_reasons(ga4_data: pd.DataFrame, funnel_steps: List[str]) -> Dict:
    """Analyze drop-offs and provide specific reasons"""
    
    if ga4_data.empty:
        return {"error": "No behavioral data available"}
    
    drop_off_insights = {
        "funnel_performance": {},
        "drop_off_reasons": {},
        "technical_issues": {},
        "user_behavior_patterns": {}
    }
    
    # Analyze engagement rate by traffic source
    if 'sessionDefaultChannelGrouping' in ga4_data.columns and 'engagementRate' in ga4_data.columns:
        engagement_analysis = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean',
            'sessions': 'sum'
        }).round(2)
        
        # Identify low engagement rate sources
        low_engagement_sources = engagement_analysis[engagement_analysis['engagementRate'] < 30]
        if not low_engagement_sources.empty:
            drop_off_insights["drop_off_reasons"]["low_engagement_rate"] = {
                "issue": "Low engagement rate traffic sources",
                "affected_sources": low_engagement_sources.to_dict('index'),
                "likely_reasons": [
                    "Ad messaging doesn't match landing page content",
                    "Poor mobile experience for mobile traffic",
                    "Slow page loading times",
                    "Irrelevant traffic from broad targeting"
                ],
                "recommended_actions": [
                    "Review ad copy to ensure message match",
                    "Test mobile landing page experience",
                    "Optimize page loading speed",
                    "Tighten ad targeting parameters"
                ]
            }
    
    # Analyze device performance
    if 'deviceCategory' in ga4_data.columns:
        device_performance = ga4_data.groupby('deviceCategory').agg({
            'engagementRate': 'mean',
            'conversionRate': 'mean' if 'conversionRate' in ga4_data.columns else lambda x: 0,
            'avgSessionDuration': 'mean',
            'sessions': 'sum'
        }).round(2)
        
        # Identify poor performing devices
        mobile_performance = device_performance.get('mobile', {})
        desktop_performance = device_performance.get('desktop', {})
        
        if mobile_performance and desktop_performance:
            if mobile_performance.get('engagementRate', 50) < desktop_performance.get('engagementRate', 50) * 0.7:
                drop_off_insights["technical_issues"]["mobile_experience"] = {
                    "issue": "Poor mobile experience",
                    "mobile_engagement_rate": f"{mobile_performance.get('engagementRate', 0)}%",
                    "desktop_engagement_rate": f"{desktop_performance.get('engagementRate', 0)}%",
                    "likely_reasons": [
                        "Mobile site not optimized",
                        "Slow loading on mobile devices", 
                        "Poor mobile UX/UI",
                        "Mobile checkout issues"
                    ],
                    "recommended_actions": [
                        "Implement responsive design improvements",
                        "Optimize images and resources for mobile",
                        "Test mobile checkout flow",
                        "Consider AMP or mobile-first design"
                    ]
                }
    
    # Analyze session duration patterns
    if 'avgSessionDuration' in ga4_data.columns:
        avg_duration = ga4_data['avgSessionDuration'].mean()
        
        if avg_duration < 30:  # Less than 30 seconds average
            drop_off_insights["user_behavior_patterns"]["short_sessions"] = {
                "issue": "Very short session durations",
                "average_duration": f"{avg_duration:.1f} seconds",
                "likely_reasons": [
                    "Landing page doesn't match user intent",
                    "Confusing or overwhelming page design",
                    "Slow loading times causing immediate exits",
                    "No clear call-to-action or value proposition"
                ],
                "recommended_actions": [
                    "A/B test different landing page designs",
                    "Simplify the initial user experience",
                    "Add clear value propositions above the fold",
                    "Implement exit-intent surveys"
                ]
            }
    
    # Analyze conversion funnel
    if 'pagePath' in ga4_data.columns and 'conversions' in ga4_data.columns:
        page_performance = ga4_data.groupby('pagePath').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean',
            'exitRate': 'mean' if 'exitRate' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        page_performance['conversion_rate'] = (page_performance['conversions'] / page_performance['sessions'] * 100).round(2)
        
        # Find pages with high traffic but low conversions
        high_traffic_pages = page_performance[page_performance['sessions'] > page_performance['sessions'].quantile(0.7)]
        low_converting_pages = high_traffic_pages[high_traffic_pages['conversion_rate'] < 2.0]
        
        if not low_converting_pages.empty:
            drop_off_insights["funnel_performance"]["conversion_bottlenecks"] = {
                "issue": "High traffic pages with poor conversion rates",
                "problematic_pages": low_converting_pages.head(5).to_dict('index'),
                "likely_reasons": [
                    "Weak call-to-action buttons",
                    "Pricing or trust issues",
                    "Complicated conversion process",
                    "Missing social proof or testimonials"
                ],
                "recommended_actions": [
                    "A/B test different CTA button designs and copy",
                    "Add customer reviews and testimonials",
                    "Simplify the conversion/checkout process",
                    "Add trust signals (security badges, guarantees)"
                ]
            }
    
    return drop_off_insights

def _generate_funnel_optimization_plan(ga4_data: pd.DataFrame, ad_data: pd.DataFrame) -> Dict:
    """Generate specific optimization recommendations based on funnel analysis"""
    
    optimization_plan = {
        "immediate_fixes": [],
        "week_1_optimizations": [], 
        "month_1_improvements": [],
        "expected_impact": {}
    }
    
    if ga4_data.empty:
        return {"error": "No data available for optimization planning"}
    
    # Calculate current performance baseline
    current_engagement_rate = ga4_data['engagementRate'].mean() if 'engagementRate' in ga4_data.columns else 50
    current_conversion_rate = (ga4_data['conversions'].sum() / ga4_data['sessions'].sum() * 100) if 'conversions' in ga4_data.columns else 0
    current_avg_duration = ga4_data['avgSessionDuration'].mean() if 'avgSessionDuration' in ga4_data.columns else 0
    
    # IMMEDIATE FIXES (24-48 hours)
    
    # Fix 1: Low engagement rate
    if current_engagement_rate < 40:
        optimization_plan["immediate_fixes"].append({
            "priority": "CRITICAL",
            "issue": f"Low engagement rate: {current_engagement_rate:.1f}%",
            "action": "Optimize landing page message match",
            "specific_steps": [
                "1. Review your top 3 ad headlines vs landing page headlines",
                "2. Ensure the value proposition matches exactly",
                "3. Add the same keywords from ads to landing page copy",
                "4. Test page load speed with GTmetrix or PageSpeed Insights",
                "5. Fix any loading issues over 3 seconds"
            ],
            "expected_impact": "Increase engagement rate by 15-25%",
            "time_required": "2-4 hours",
            "tools_needed": ["GTmetrix", "Google PageSpeed Insights"]
        })
    
    # Fix 2: Mobile performance issues
    if 'deviceCategory' in ga4_data.columns:
        device_perf = ga4_data.groupby('deviceCategory').agg({
            'engagementRate': 'mean',
            'sessions': 'sum'
        }).round(2)
        
        mobile_engagement = device_perf.get('mobile', {}).get('engagementRate', 50)
        desktop_engagement = device_perf.get('desktop', {}).get('engagementRate', 50)
        
        if mobile_engagement < desktop_engagement * 0.7:
            optimization_plan["immediate_fixes"].append({
                "priority": "HIGH",
                "issue": f"Poor mobile experience - {mobile_engagement:.1f}% mobile engagement vs {desktop_engagement:.1f}% desktop",
                "action": "Fix mobile landing page experience",
                "specific_steps": [
                    "1. Test your landing page on mobile device",
                    "2. Ensure buttons are large enough to tap easily",
                    "3. Check that forms are mobile-friendly",
                    "4. Optimize images for mobile loading speed",
                    "5. Test the checkout process on mobile"
                ],
                "expected_impact": "Increase mobile engagement rate by 20-30%",
                "time_required": "3-6 hours",
                "tools_needed": ["Mobile device testing", "Browser developer tools"]
            })
    
    # WEEK 1 OPTIMIZATIONS
    
    # Optimization 1: Conversion rate optimization
    if current_conversion_rate < 2.0:
        optimization_plan["week_1_optimizations"].append({
            "priority": "HIGH",
            "issue": f"Low conversion rate: {current_conversion_rate:.2f}%",
            "action": "Implement conversion rate optimization tactics",
            "specific_steps": [
                "1. Add customer testimonials above the fold",
                "2. Include trust signals (security badges, guarantees)",
                "3. Create urgency with limited-time offers",
                "4. Simplify forms (reduce required fields)",
                "5. A/B test different call-to-action button colors/text",
                "6. Add live chat or FAQ section"
            ],
            "expected_impact": "Increase conversion rate by 0.5-1.5%",
            "time_required": "8-12 hours",
            "tools_needed": ["A/B testing tool", "Customer review platform"]
        })
    
    # Optimization 2: Traffic quality improvement
    if not ad_data.empty:
        # Identify campaigns with high spend but low quality traffic
        ad_summary = ad_data.groupby('campaign_name').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'conversions': 'sum'
        }).round(2)
        
        ad_summary['cost_per_click'] = ad_summary['spend'] / ad_summary['clicks']
        ad_summary['conversion_rate'] = (ad_summary['conversions'] / ad_summary['clicks'] * 100).round(2)
        
        low_quality_campaigns = ad_summary[ad_summary['conversion_rate'] < 1.0]
        
        if not low_quality_campaigns.empty:
            optimization_plan["week_1_optimizations"].append({
                "priority": "MEDIUM",
                "issue": f"{len(low_quality_campaigns)} campaigns driving low-quality traffic",
                "action": "Improve ad targeting and relevance",
                "specific_steps": [
                    "1. Review audience targeting for low-converting campaigns",
                    "2. Add negative keywords to exclude irrelevant searches", 
                    "3. Test ad copy variations focused on qualified leads",
                    "4. Adjust geographic targeting if needed",
                    "5. Implement audience exclusions for non-converters"
                ],
                "campaigns_to_optimize": low_quality_campaigns.head(3).to_dict('index'),
                "expected_impact": "Improve overall conversion rate by 10-20%",
                "time_required": "6-10 hours"
            })
    
    # MONTH 1 IMPROVEMENTS
    
    # Improvement 1: Advanced funnel optimization
    optimization_plan["month_1_improvements"].append({
        "priority": "MEDIUM",
        "issue": "Comprehensive funnel optimization",
        "action": "Implement advanced conversion optimization",
        "specific_steps": [
            "1. Set up heat mapping to understand user behavior",
            "2. Implement exit-intent popups with special offers",
            "3. Create retargeting campaigns for website visitors",
            "4. A/B test completely different landing page designs",
            "5. Implement progressive profiling for forms",
            "6. Add social proof notifications (recent purchases)",
            "7. Optimize page loading speed to under 2 seconds"
        ],
        "expected_impact": "Overall conversion improvement of 25-50%",
        "time_required": "20-30 hours",
        "tools_needed": ["Hotjar/Crazy Egg", "Exit-intent popup tool", "Retargeting pixels"]
    })
    
    # Calculate expected impact
    total_sessions = ga4_data['sessions'].sum()
    current_conversions = ga4_data['conversions'].sum() if 'conversions' in ga4_data.columns else 0
    
    # Conservative impact estimates
    immediate_impact = current_conversions * 0.20  # 20% improvement
    weekly_impact = current_conversions * 0.35     # 35% total improvement  
    monthly_impact = current_conversions * 0.60    # 60% total improvement
    
    optimization_plan["expected_impact"] = {
        "current_monthly_conversions": int(current_conversions),
        "current_conversion_rate": f"{current_conversion_rate:.2f}%",
        "after_immediate_fixes": {
            "conversions": int(current_conversions + immediate_impact),
            "conversion_rate": f"{((current_conversions + immediate_impact) / total_sessions * 100):.2f}%",
            "additional_conversions": int(immediate_impact)
        },
        "after_week_1": {
            "conversions": int(current_conversions + weekly_impact),
            "conversion_rate": f"{((current_conversions + weekly_impact) / total_sessions * 100):.2f}%",
            "additional_conversions": int(weekly_impact)
        },
        "after_month_1": {
            "conversions": int(current_conversions + monthly_impact),
            "conversion_rate": f"{((current_conversions + monthly_impact) / total_sessions * 100):.2f}%",
            "additional_conversions": int(monthly_impact)
        }
    }
    
    return optimization_plan

def _analyze_traffic_quality(ga4_data: pd.DataFrame, ad_data: pd.DataFrame) -> Dict:
    """Analyze traffic quality from different sources"""
    
    quality_analysis = {
        "traffic_source_quality": {},
        "campaign_quality": {},
        "recommendations": {}
    }
    
    if ga4_data.empty:
        return {"error": "No GA4 data available"}
    
    # Analyze quality by traffic source
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_quality = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
            'engagementRate': 'mean' if 'engagementRate' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        source_quality['conversion_rate'] = (source_quality['conversions'] / source_quality['sessions'] * 100).round(2)
        source_quality['quality_score'] = (
            (source_quality['conversion_rate'] * 0.4) +
            (source_quality['engagementRate'] * 0.3) +
            (source_quality['avgSessionDuration'] / 10 * 0.3)
        ).round(1)
        
        quality_analysis["traffic_source_quality"] = source_quality.to_dict('index')
    
    # Correlate with ad campaign performance
    if not ad_data.empty and 'sessionCampaignName' in ga4_data.columns:
        campaign_quality = ga4_data.groupby('sessionCampaignName').agg({
            'sessions': 'sum',
            'engagementRate': 'mean', 
            'avgSessionDuration': 'mean',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        campaign_quality['conversion_rate'] = (campaign_quality['conversions'] / campaign_quality['sessions'] * 100).round(2)
        
        # Merge with ad spend data
        ad_summary = ad_data.groupby('campaign_name').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'ctr': 'mean'
        }).round(2)
        
        # Create quality recommendations
        high_spend_low_quality = []
        for campaign in campaign_quality.index:
            if campaign in ad_summary.index:
                spend = ad_summary.loc[campaign, 'spend']
                engagement_rate = campaign_quality.loc[campaign, 'engagementRate']
                conv_rate = campaign_quality.loc[campaign, 'conversion_rate']
                
                if spend > 500 and (engagement_rate < 30 or conv_rate < 1.0):
                    high_spend_low_quality.append({
                        "campaign": campaign,
                        "spend": spend,
                        "engagement_rate": engagement_rate,
                        "conversion_rate": conv_rate,
                        "issue": "High spend with poor website performance"
                    })
        
        quality_analysis["campaign_quality"] = campaign_quality.to_dict('index')
        quality_analysis["recommendations"]["low_quality_campaigns"] = high_spend_low_quality
    
    return quality_analysis