from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import tempfile
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
import data_integrator

router = APIRouter()

@router.post("/eda")
def run_eda(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    from ydata_profiling import ProfileReport
    report = ProfileReport(df, title="EDA Report", minimal=True)
    temp_dir = tempfile.mkdtemp()
    report_path = os.path.join(temp_dir, "eda_report.html")
    report.to_file(report_path)
    return {"eda_report_path": report_path}

@router.post("/ga4-data-availability")
async def ga4_data_availability(request: str = Form(...)):
    """
    Check what GA4 data is available and get recommended date ranges
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Try to fetch a small sample to understand data availability
        today = datetime.now().strftime('%Y-%m-%d')
        last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        last_90_days = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Test different date ranges to find available data
        data_ranges = []
        
        for period_name, start, end in [
            ("Last 7 days", (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), today),
            ("Last 30 days", last_month, today),
            ("Last 90 days", last_90_days, today)
        ]:
            try:
                test_data = await _fetch_comprehensive_ga4_data(user_id, start, end)
                if not test_data.empty:
                    data_ranges.append({
                        "period": period_name,
                        "start_date": start,
                        "end_date": end,
                        "total_records": len(test_data),
                        "date_range": f"{test_data['date'].min()} to {test_data['date'].max()}",
                        "total_sessions": int(test_data['sessions'].sum()) if 'sessions' in test_data.columns else 0,
                        "total_conversions": int(test_data['conversions'].sum()) if 'conversions' in test_data.columns else 0
                    })
            except:
                continue
        
        if not data_ranges:
            return {
                "user_id": user_id,
                "data_available": False,
                "message": "No GA4 data found in the last 90 days. Please check your GA4 connection.",
                "suggested_actions": [
                    "Verify GA4 property ID is correct",
                    "Check if GA4 connector is properly configured", 
                    "Ensure date range includes recent data"
                ]
            }
        
        # Find the best available range
        best_range = max(data_ranges, key=lambda x: x['total_records'])
        
        return {
            "user_id": user_id,
            "data_available": True,
            "available_periods": data_ranges,
            "recommended_period": best_range,
            "quick_start_curl": f'curl -X POST "http://localhost:8000/complete-website-insights" -H "Content-Type: application/x-www-form-urlencoded" -d "request={{\\"user_id\\":\\"{user_id}\\",\\"start_date\\":\\"{best_range["start_date"]}\\",\\"end_date\\":\\"{best_range["end_date"]}\\"}}"'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking data availability: {str(e)}")

@router.post("/complete-website-insights")
async def complete_website_insights(request: str = Form(...)):
    """
    COMPREHENSIVE GA4 insights: drop-offs, traffic sources, user behavior, and actionable recommendations
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
        # Fetch comprehensive GA4 data
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found for the specified period")
        
        # Preprocess data to handle type issues
        ga4_data = _preprocess_ga4_data(ga4_data)
        
        # Generate all insights
        insights = {
            "overview": _generate_overview_insights(ga4_data),
            "drop_off_analysis": _analyze_drop_offs(ga4_data),
            "traffic_source_analysis": _analyze_traffic_sources(ga4_data),
            "user_behavior_patterns": _analyze_user_behavior(ga4_data),
            "content_performance": _analyze_content_performance(ga4_data),
            "device_performance": _analyze_device_performance(ga4_data),
            "actionable_recommendations": _generate_actionable_recommendations(ga4_data),
            "optimization_opportunities": _identify_optimization_opportunities(ga4_data)
        }
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "data_summary": {
                "total_sessions": int(ga4_data['sessions'].sum()),
                "total_users": int(ga4_data['totalUsers'].sum()) if 'totalUsers' in ga4_data.columns else 0,
                "total_conversions": int(ga4_data['conversions'].sum()) if 'conversions' in ga4_data.columns else 0,
                "overall_engagement_rate": float(ga4_data['engagementRate'].mean()) if 'engagementRate' in ga4_data.columns else 0,
                "avg_session_duration": float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0,
                "date_range": f"{ga4_data['date'].min()} to {ga4_data['date'].max()}",
                "unique_pages": ga4_data['pagePath'].nunique() if 'pagePath' in ga4_data.columns else 0,
                "traffic_sources": ga4_data['sessionDefaultChannelGrouping'].nunique() if 'sessionDefaultChannelGrouping' in ga4_data.columns else 0
            },
            "comprehensive_insights": insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating comprehensive insights: {str(e)}")

# Helper functions for comprehensive GA4 insights

async def _fetch_comprehensive_ga4_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch comprehensive GA4 data for deep insights"""
    
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch comprehensive GA4 data
    ga4_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'date',
            'sessionDefaultChannelGrouping',
            'sessionSourceMedium',
            'pagePath',
            'deviceCategory',
            'country',
            'eventName'
        ],
        metrics=[
            'sessions',
            'totalUsers',
            'newUsers',
            'screenPageViews',
            'averageSessionDuration',
            'conversions',
            'eventCount',
            'engagementRate'
        ]
    )
    
    return ga4_data

def _preprocess_ga4_data(ga4_data: pd.DataFrame) -> pd.DataFrame:
    """Preprocess GA4 data to handle data type issues"""
    
    # Convert all numeric columns to proper numeric types
    numeric_columns = [
        'sessions', 'totalUsers', 'newUsers', 'screenPageViews', 
        'averageSessionDuration', 'conversions', 
        'eventCount', 'engagementRate'
    ]
    
    for col in numeric_columns:
        if col in ga4_data.columns:
            ga4_data[col] = pd.to_numeric(ga4_data[col], errors='coerce').fillna(0)
    
    return ga4_data

def _generate_overview_insights(ga4_data: pd.DataFrame) -> Dict:
    """Generate high-level overview insights"""
    
    total_sessions = int(ga4_data['sessions'].sum()) if 'sessions' in ga4_data.columns else 0
    total_users = int(ga4_data['totalUsers'].sum()) if 'totalUsers' in ga4_data.columns else 0
    total_conversions = int(ga4_data['conversions'].sum()) if 'conversions' in ga4_data.columns else 0
    avg_engagement_rate = float(ga4_data['engagementRate'].mean()) if 'engagementRate' in ga4_data.columns else 0
    avg_session_duration = float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0
    
    conversion_rate = (total_conversions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Performance assessment
    performance_status = "excellent" if conversion_rate > 3 else "good" if conversion_rate > 1.5 else "poor"
    engagement_status = "excellent" if avg_engagement_rate > 60 else "good" if avg_engagement_rate > 40 else "poor"
    
    return {
        "total_sessions": total_sessions,
        "total_users": total_users,
        "total_conversions": total_conversions,
        "conversion_rate": round(conversion_rate, 2),
        "avg_engagement_rate": round(avg_engagement_rate, 1),
        "avg_session_duration": round(avg_session_duration, 1),
        "performance_assessment": {
            "overall_performance": performance_status,
            "engagement_status": engagement_status,
            "key_concern": _identify_main_concern(avg_engagement_rate, conversion_rate, avg_session_duration)
        }
    }

def _analyze_drop_offs(ga4_data: pd.DataFrame) -> Dict:
    """Analyze where and why users are dropping off"""
    
    drop_off_analysis = {
        "page_level_drop_offs": {},
        "traffic_source_drop_offs": {},
        "device_drop_offs": {},
        "main_drop_off_reasons": []
    }
    
    # Page-level drop-offs (using engagement rate instead of bounce rate)
    if 'pagePath' in ga4_data.columns and 'engagementRate' in ga4_data.columns:
        page_engagement = ga4_data.groupby('pagePath').agg({
            'sessions': 'sum',
            'engagementRate': 'mean',
            'averageSessionDuration': 'mean' if 'averageSessionDuration' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        # Find pages with low engagement rates and significant traffic
        problem_pages = page_engagement[
            (page_engagement['engagementRate'] < 30) & 
            (page_engagement['sessions'] > page_engagement['sessions'].quantile(0.5))
        ].sort_values('engagementRate', ascending=True)
        
        if not problem_pages.empty:
            drop_off_analysis["page_level_drop_offs"] = {
                "worst_pages": problem_pages.head(5).to_dict('index'),
                "total_problem_pages": len(problem_pages),
                "sessions_lost": int(problem_pages['sessions'].sum())
            }
    
    # Traffic source drop-offs
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_engagement = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'engagementRate': 'mean' if 'engagementRate' in ga4_data.columns else lambda x: 0,
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        source_engagement['conversion_rate'] = (source_engagement['conversions'] / source_engagement['sessions'] * 100).round(2)
        
        # Identify problematic traffic sources (low engagement)
        poor_sources = source_engagement[source_engagement['engagementRate'] < 30].sort_values('sessions', ascending=False)
        
        drop_off_analysis["traffic_source_drop_offs"] = {
            "problematic_sources": poor_sources.to_dict('index'),
            "best_performing_source": source_engagement.loc[source_engagement['conversion_rate'].idxmax()].to_dict() if not source_engagement.empty else {},
            "worst_performing_source": source_engagement.loc[source_engagement['engagementRate'].idxmin()].to_dict() if not source_engagement.empty else {}
        }
    
    # Device drop-offs
    if 'deviceCategory' in ga4_data.columns:
        device_performance = ga4_data.groupby('deviceCategory').agg({
            'sessions': 'sum',
            'engagementRate': 'mean' if 'engagementRate' in ga4_data.columns else lambda x: 0,
            'averageSessionDuration': 'mean' if 'averageSessionDuration' in ga4_data.columns else lambda x: 0
        }).round(2)
        
        drop_off_analysis["device_drop_offs"] = device_performance.to_dict('index')
    
    # Identify main reasons for drop-offs
    main_reasons = []
    
    if 'engagementRate' in ga4_data.columns:
        avg_engagement = ga4_data['engagementRate'].mean()
        if avg_engagement < 40:
            main_reasons.append({
                "reason": "Low overall engagement rate",
                "severity": "critical",
                "description": f"Average engagement rate of {avg_engagement:.1f}% indicates serious user experience issues",
                "immediate_action": "Improve content relevance and page user experience"
            })
    
    if 'deviceCategory' in ga4_data.columns and 'engagementRate' in ga4_data.columns:
        device_engagement = ga4_data.groupby('deviceCategory')['engagementRate'].mean()
        if 'mobile' in device_engagement and device_engagement['mobile'] < 30:
            main_reasons.append({
                "reason": "Poor mobile engagement",
                "severity": "high",
                "description": f"Mobile engagement rate of {device_engagement['mobile']:.1f}% suggests mobile optimization issues",
                "immediate_action": "Optimize mobile page speed and user interface"
            })
    
    drop_off_analysis["main_drop_off_reasons"] = main_reasons
    
    return drop_off_analysis

def _analyze_traffic_sources(ga4_data: pd.DataFrame) -> Dict:
    """Analyze where users are coming from and their quality"""
    
    traffic_analysis = {
        "source_breakdown": {},
        "source_quality": {},
        "recommendations": []
    }
    
    if 'sessionDefaultChannelGrouping' not in ga4_data.columns:
        return {"error": "No traffic source data available"}
    
    # Traffic source breakdown
    source_summary = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
        'sessions': 'sum',
        'totalUsers': 'sum' if 'totalUsers' in ga4_data.columns else lambda x: 0,
        'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
        'engagementRate': 'mean' if 'engagementRate' in ga4_data.columns else lambda x: 0,
        'averageSessionDuration': 'mean' if 'averageSessionDuration' in ga4_data.columns else lambda x: 0
    }).round(2)
    
    source_summary['conversion_rate'] = (source_summary['conversions'] / source_summary['sessions'] * 100).round(2)
    source_summary['traffic_share'] = (source_summary['sessions'] / source_summary['sessions'].sum() * 100).round(1)
    
    traffic_analysis["source_breakdown"] = source_summary.to_dict('index')
    
    # Source quality assessment
    quality_scores = {}
    for source in source_summary.index:
        row = source_summary.loc[source]
        
        # Calculate quality score (0-100)  
        quality_score = (
            (row['conversion_rate'] * 2) +  # Conversion rate weight: 2
            (row['engagementRate'] * 0.5) +  # Engagement rate weight: 0.5  
            (min(row['averageSessionDuration'] / 60, 10) * 5)  # Session duration weight: 5 (capped at 10 min)
        )
        
        quality_scores[source] = {
            "quality_score": round(quality_score, 1),
            "quality_grade": "A" if quality_score > 80 else "B" if quality_score > 60 else "C" if quality_score > 40 else "D",
            "sessions": int(row['sessions']),
            "conversion_rate": row['conversion_rate'],
            "engagement_rate": row['engagementRate']
        }
    
    traffic_analysis["source_quality"] = quality_scores
    
    # Generate recommendations
    recommendations = []
    
    # Find underperforming high-traffic sources
    high_traffic_sources = source_summary[source_summary['traffic_share'] > 10]
    underperforming = high_traffic_sources[high_traffic_sources['conversion_rate'] < 1.5]
    
    if not underperforming.empty:
        recommendations.append({
            "type": "optimize_underperforming",
            "priority": "high",
            "description": f"Optimize {len(underperforming)} high-traffic, low-converting sources",
            "sources": underperforming.index.tolist(),
            "potential_impact": "15-30% increase in conversions"
        })
    
    # Find high-performing sources to scale
    high_performers = source_summary[source_summary['conversion_rate'] > 3]
    if not high_performers.empty:
        recommendations.append({
            "type": "scale_high_performers",
            "priority": "medium",
            "description": f"Increase investment in {len(high_performers)} high-performing sources",
            "sources": high_performers.index.tolist(),
            "potential_impact": "20-40% increase in total conversions"
        })
    
    traffic_analysis["recommendations"] = recommendations
    
    return traffic_analysis

def _analyze_user_behavior(ga4_data: pd.DataFrame) -> Dict:
    """Analyze user behavior patterns"""
    
    behavior_analysis = {
        "engagement_patterns": {},
        "user_journey_analysis": {},
        "behavioral_segments": {}
    }
    
    # Engagement patterns
    if 'averageSessionDuration' in ga4_data.columns and 'engagementRate' in ga4_data.columns:
        # Create engagement segments
        ga4_data['engagement_level'] = np.where(
            (ga4_data['averageSessionDuration'] > ga4_data['averageSessionDuration'].median()) & 
            (ga4_data['engagementRate'] > ga4_data['engagementRate'].median()),
            'high_engagement',
            np.where(
                (ga4_data['averageSessionDuration'] < ga4_data['averageSessionDuration'].quantile(0.25)) | 
                (ga4_data['engagementRate'] < ga4_data['engagementRate'].quantile(0.25)),
                'low_engagement',
                'medium_engagement'
            )
        )
        
        engagement_summary = ga4_data.groupby('engagement_level').agg({
            'sessions': 'sum',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0
        })
        
        engagement_summary['conversion_rate'] = (engagement_summary['conversions'] / engagement_summary['sessions'] * 100).round(2)
        engagement_summary['session_share'] = (engagement_summary['sessions'] / engagement_summary['sessions'].sum() * 100).round(1)
        
        behavior_analysis["engagement_patterns"] = engagement_summary.to_dict('index')
    
    # User journey analysis
    if 'eventName' in ga4_data.columns:
        event_summary = ga4_data.groupby('eventName').agg({
            'eventCount': 'sum' if 'eventCount' in ga4_data.columns else lambda x: len(ga4_data),
            'sessions': 'nunique'
        }).sort_values('eventCount', ascending=False)
        
        behavior_analysis["user_journey_analysis"] = {
            "top_events": event_summary.head(10).to_dict('index'),
            "total_unique_events": len(event_summary)
        }
    
    return behavior_analysis

def _analyze_content_performance(ga4_data: pd.DataFrame) -> Dict:
    """Analyze content performance"""
    
    content_analysis = {
        "page_performance": {},
        "content_insights": []
    }
    
    if 'pagePath' not in ga4_data.columns:
        return {"error": "No page path data available"}
    
    # Page performance analysis
    page_metrics = ga4_data.groupby('pagePath').agg({
        'sessions': 'sum',
        'screenPageViews': 'sum' if 'screenPageViews' in ga4_data.columns else lambda x: 0,
        'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
        'engagementRate': 'mean' if 'engagementRate' in ga4_data.columns else lambda x: 0,
        'averageSessionDuration': 'mean' if 'averageSessionDuration' in ga4_data.columns else lambda x: 0
    }).round(2)
    
    page_metrics['conversion_rate'] = (page_metrics['conversions'] / page_metrics['sessions'] * 100).round(2)
    page_metrics['pages_per_session'] = (page_metrics['screenPageViews'] / page_metrics['sessions']).round(2)
    
    # Top and bottom performers
    top_pages = page_metrics.nlargest(10, 'conversion_rate')
    bottom_pages = page_metrics[page_metrics['sessions'] >= 100].nsmallest(5, 'conversion_rate')
    
    content_analysis["page_performance"] = {
        "top_converting_pages": top_pages.to_dict('index'),
        "underperforming_pages": bottom_pages.to_dict('index'),
        "total_pages": len(page_metrics)
    }
    
    # Content insights
    insights = []
    
    # Find high-traffic, low-converting pages
    high_traffic_low_conversion = page_metrics[
        (page_metrics['sessions'] > page_metrics['sessions'].quantile(0.7)) &
        (page_metrics['conversion_rate'] < 2.0)
    ]
    
    if not high_traffic_low_conversion.empty:
        insights.append({
            "type": "optimization_opportunity",
            "description": f"{len(high_traffic_low_conversion)} high-traffic pages have conversion rates below 2%",
            "recommendation": "Focus optimization efforts on these pages for maximum impact",
            "pages": high_traffic_low_conversion.head(5).index.tolist()
        })
    
    content_analysis["content_insights"] = insights
    
    return content_analysis

def _analyze_device_performance(ga4_data: pd.DataFrame) -> Dict:
    """Analyze device performance"""
    
    device_analysis = {
        "device_breakdown": {},
        "performance_gaps": [],
        "optimization_priorities": []
    }
    
    if 'deviceCategory' not in ga4_data.columns:
        return {"error": "No device category data available"}
    
    # Device performance breakdown
    device_metrics = ga4_data.groupby('deviceCategory').agg({
        'sessions': 'sum',
        'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
        'engagementRate': 'mean',
        'averageSessionDuration': 'mean' if 'averageSessionDuration' in ga4_data.columns else lambda x: 0
    }).round(2)
    
    device_metrics['conversion_rate'] = (device_metrics['conversions'] / device_metrics['sessions'] * 100).round(2)
    device_metrics['session_share'] = (device_metrics['sessions'] / device_metrics['sessions'].sum() * 100).round(1)
    
    device_analysis["device_breakdown"] = device_metrics.to_dict('index')
    
    # Identify performance gaps
    if 'mobile' in device_metrics.index and 'desktop' in device_metrics.index:
        mobile_conv = device_metrics.loc['mobile', 'conversion_rate']
        desktop_conv = device_metrics.loc['desktop', 'conversion_rate']
        mobile_engagement = device_metrics.loc['mobile', 'engagementRate'] if 'mobile' in device_metrics.index else 50
        desktop_engagement = device_metrics.loc['desktop', 'engagementRate'] if 'desktop' in device_metrics.index else 50
        
        if mobile_conv < desktop_conv * 0.7:
            device_analysis["performance_gaps"].append({
                "issue": "Mobile conversion rate significantly lower than desktop",
                "mobile_rate": mobile_conv,
                "desktop_rate": desktop_conv,
                "impact": "High - mobile represents significant traffic",
                "priority": "critical"
            })
        
        if mobile_engagement < desktop_engagement * 0.7:
            device_analysis["performance_gaps"].append({
                "issue": "Mobile engagement rate significantly lower than desktop",
                "mobile_engagement": mobile_engagement,
                "desktop_engagement": desktop_engagement,
                "impact": "High - indicates poor mobile experience",
                "priority": "high"
            })
    
    return device_analysis

def _generate_actionable_recommendations(ga4_data: pd.DataFrame) -> List[Dict]:
    """Generate specific, actionable recommendations"""
    
    recommendations = []
    
    # Engagement rate recommendations
    if 'engagementRate' in ga4_data.columns:
        avg_engagement_rate = ga4_data['engagementRate'].mean()
        if avg_engagement_rate < 40:
            recommendations.append({
                "priority": "critical",
                "category": "User Experience",
                "issue": f"Low engagement rate: {avg_engagement_rate:.1f}%",
                "action": "Optimize landing page experience",
                "specific_steps": [
                    "1. Test page load speed using Google PageSpeed Insights",
                    "2. Ensure mobile responsiveness",
                    "3. Match ad messaging with landing page content", 
                    "4. Add clear call-to-action above the fold",
                    "5. Simplify page design and remove distractions"
                ],
                "expected_impact": "15-25% increase in engagement rate",
                "timeline": "1-2 weeks"
            })
    
    # Mobile optimization
    if 'deviceCategory' in ga4_data.columns:
        device_engagement = ga4_data.groupby('deviceCategory')['engagementRate'].mean()
        if 'mobile' in device_engagement and 'desktop' in device_engagement:
            if device_engagement['mobile'] < device_engagement['desktop'] * 0.7:
                recommendations.append({
                    "priority": "high",
                    "category": "Mobile Optimization",
                    "issue": f"Mobile engagement rate ({device_engagement['mobile']:.1f}%) much lower than desktop ({device_engagement['desktop']:.1f}%)",
                    "action": "Implement mobile-first optimizations",
                    "specific_steps": [
                        "1. Optimize images for mobile loading",
                        "2. Increase button sizes for touch interaction",
                        "3. Simplify forms for mobile users",
                        "4. Test mobile checkout process",
                        "5. Consider AMP implementation for key pages"
                    ],
                    "expected_impact": "20-30% improvement in mobile conversion rate",
                    "timeline": "2-3 weeks"
                })
    
    # Traffic source optimization
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_performance = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
            'engagementRate': 'mean'
        })
        
        source_performance['conversion_rate'] = source_performance['conversions'] / source_performance['sessions'] * 100
        
        # Find high-traffic, low-converting sources
        high_traffic_sources = source_performance[source_performance['sessions'] > source_performance['sessions'].quantile(0.6)]
        underperforming = high_traffic_sources[high_traffic_sources['conversion_rate'] < 2.0]
        
        if not underperforming.empty:
            worst_source = underperforming['conversion_rate'].idxmin()
            recommendations.append({
                "priority": "medium",
                "category": "Traffic Quality",
                "issue": f"'{worst_source}' traffic source has low conversion rate",
                "action": "Improve traffic source targeting and landing pages",
                "specific_steps": [
                    f"1. Review {worst_source} targeting settings",
                    "2. Create dedicated landing pages for this traffic",
                    "3. A/B test different messaging approaches",
                    "4. Add exit-intent popups for this traffic source",
                    "5. Consider adjusting bid strategies"
                ],
                "expected_impact": "10-20% improvement in overall conversion rate",
                "timeline": "2-4 weeks"
            })
    
    return recommendations

def _identify_optimization_opportunities(ga4_data: pd.DataFrame) -> List[Dict]:
    """Identify specific optimization opportunities with impact estimates"""
    
    opportunities = []
    
    # Page optimization opportunities
    if 'pagePath' in ga4_data.columns and 'conversions' in ga4_data.columns:
        page_performance = ga4_data.groupby('pagePath').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean'
        })
        
        page_performance['conversion_rate'] = page_performance['conversions'] / page_performance['sessions'] * 100
        
        # High-impact page optimization
        high_traffic_pages = page_performance[page_performance['sessions'] > page_performance['sessions'].quantile(0.8)]
        optimization_pages = high_traffic_pages[high_traffic_pages['conversion_rate'] < 3.0]
        
        if not optimization_pages.empty:
            potential_sessions = optimization_pages['sessions'].sum()
            current_conversions = optimization_pages['conversions'].sum()
            potential_conversions = potential_sessions * 0.05  # Assume 5% conversion rate after optimization
            additional_conversions = potential_conversions - current_conversions
            
            opportunities.append({
                "opportunity": "High-Traffic Page Optimization",
                "description": f"Optimize {len(optimization_pages)} high-traffic pages with low conversion rates",
                "current_performance": {
                    "pages": len(optimization_pages),
                    "monthly_sessions": int(potential_sessions),
                    "current_conversions": int(current_conversions)
                },
                "potential_impact": {
                    "additional_monthly_conversions": int(additional_conversions),
                    "revenue_increase_potential": "high"
                },
                "effort_required": "medium",
                "timeline": "4-6 weeks"
            })
    
    # Traffic source optimization
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_sessions = ga4_data.groupby('sessionDefaultChannelGrouping')['sessions'].sum()
        underutilized_sources = source_sessions[source_sessions < source_sessions.quantile(0.3)]
        
        if len(underutilized_sources) > 0:
            opportunities.append({
                "opportunity": "Traffic Source Diversification",
                "description": f"Expand {len(underutilized_sources)} underutilized traffic sources",
                "current_performance": {
                    "underutilized_sources": underutilized_sources.index.tolist(),
                    "current_monthly_sessions": int(underutilized_sources.sum())
                },
                "potential_impact": {
                    "additional_monthly_sessions": int(underutilized_sources.sum() * 2),
                    "revenue_increase_potential": "medium"
                },
                "effort_required": "high",
                "timeline": "6-8 weeks"
            })
    
    return opportunities

def _identify_main_concern(engagement_rate: float, conversion_rate: float, avg_duration: float) -> str:
    """Identify the main concern based on metrics"""
    
    if engagement_rate < 30:
        return "Low engagement rate - users not connecting with content"
    elif conversion_rate < 1:
        return "Very low conversion rate - users not taking action"
    elif avg_duration < 30:
        return "Short session duration - users not engaging with content"
    elif conversion_rate < 2:
        return "Low conversion rate - room for significant improvement"
    else:
        return "Performance looks good - focus on scaling successful elements"

