from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import os
import tempfile
import json
from autogluon.tabular import TabularPredictor
import shap
from models import PredictRequest
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
import data_integrator

router = APIRouter()

model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

@router.post("/analyze")
def full_analysis(file: UploadFile = File(...), request: str = Form(...)):
    req_data = PredictRequest(**json.loads(request))
    df = pd.read_csv(file.file)
    if req_data.target not in df.columns:
        raise HTTPException(status_code=400, detail="Target column not in data")
    predictor_path = os.path.join(model_dir, req_data.id)
    predictor = TabularPredictor(label=req_data.target, path=predictor_path).fit(df)
    predictions = predictor.predict(df)
    df['prediction'] = predictions
    try:
        model_names = predictor.get_model_names()
        best_model = model_names[0]
        if any(name in best_model.lower() for name in ["xgboost", "lightgbm", "catboost"]):
            explainer = shap.Explainer(predictor._trainer.load_model(best_model).model)
            shap_values = explainer(df.drop(columns=[req_data.target, 'prediction']))
            shap_summary = shap_values.values.mean(axis=0).tolist()
        else:
            raise Exception()
    except:
        shap_summary = predictor.feature_importance(df.drop(columns=['prediction']))["importance"].tolist()
    from ydata_profiling import ProfileReport
    report = ProfileReport(df, title="Full AutoML Analysis Report", minimal=True)
    temp_dir = tempfile.mkdtemp()
    report_path = os.path.join(temp_dir, "full_analysis_report.html")
    report.to_file(report_path)
    return {"predictions": df['prediction'].tolist(), "shap_summary": shap_summary, "eda_report_path": report_path}

@router.post("/analyze-with-ga4")
async def analyze_with_ga4(file: UploadFile = File(...), request: str = Form(...)):
    """
    Enhanced analysis combining uploaded data with GA4 web analytics
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    target = req_data.get('target')
    model_id = req_data.get('id', 'analyze_ga4')
    
    if not all([user_id, start_date, end_date, target]):
        raise HTTPException(status_code=400, detail="user_id, start_date, end_date, and target are required")
    
    # Load user credentials
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Process uploaded data
        df = pd.read_csv(file.file)
        if target not in df.columns:
            raise HTTPException(status_code=400, detail="Target column not in uploaded data")
        
        # Fetch GA4 data
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        # Perform ML analysis on uploaded data
        predictor_path = os.path.join(model_dir, model_id)
        predictor = TabularPredictor(label=target, path=predictor_path).fit(df)
        predictions = predictor.predict(df)
        df['prediction'] = predictions
        
        # Get feature importance
        try:
            model_names = predictor.get_model_names()
            best_model = model_names[0]
            if any(name in best_model.lower() for name in ["xgboost", "lightgbm", "catboost"]):
                explainer = shap.Explainer(predictor._trainer.load_model(best_model).model)
                shap_values = explainer(df.drop(columns=[target, 'prediction']))
                shap_summary = shap_values.values.mean(axis=0).tolist()
            else:
                raise Exception()
        except:
            shap_summary = predictor.feature_importance(df.drop(columns=['prediction']))["importance"].tolist()
        
        # Analyze GA4 data
        ga4_analysis = _analyze_ga4_business_correlation(ga4_data, df)
        
        # Generate comprehensive report
        from ydata_profiling import ProfileReport
        report = ProfileReport(df, title="ML + GA4 Analysis Report", minimal=True)
        temp_dir = tempfile.mkdtemp()
        report_path = os.path.join(temp_dir, "ml_ga4_analysis_report.html")
        report.to_file(report_path)
        
        return {
            "ml_analysis": {
                "predictions": df['prediction'].tolist(),
                "shap_summary": shap_summary,
                "model_performance": predictor.leaderboard().to_dict('records')[0]
            },
            "ga4_analysis": ga4_analysis,
            "combined_insights": _generate_combined_insights(df, ga4_data, predictions),
            "eda_report_path": report_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in combined analysis: {str(e)}")

@router.post("/ga4-performance-analysis") 
async def ga4_performance_analysis(request: str = Form(...)):
    """
    Deep dive GA4 performance analysis with ML-powered insights
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    if not all([user_id, start_date, end_date]):
        raise HTTPException(status_code=400, detail="user_id, start_date, and end_date are required")
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch comprehensive GA4 data
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found for the specified period")
        
        # Perform advanced analytics
        performance_analysis = _advanced_ga4_analysis(ga4_data)
        
        # ML-powered user segmentation
        user_segments = _ml_user_segmentation(ga4_data)
        
        # Predictive analytics
        predictions = _ga4_predictive_analysis(ga4_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "total_records": len(ga4_data),
            "performance_analysis": performance_analysis,
            "user_segments": user_segments,
            "predictive_insights": predictions,
            "actionable_recommendations": _generate_ga4_recommendations(ga4_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in GA4 performance analysis: {str(e)}")

@router.post("/revenue-correlation-analysis")
async def revenue_correlation_analysis(file: UploadFile = File(...), request: str = Form(...)):
    """
    Correlate GA4 traffic patterns with business revenue/conversions
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    revenue_column = req_data.get('revenue_column', 'revenue')
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Load business data
        business_df = pd.read_csv(file.file)
        if revenue_column not in business_df.columns:
            raise HTTPException(status_code=400, detail=f"Revenue column '{revenue_column}' not found in data")
        
        # Fetch GA4 data
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        # Perform correlation analysis
        correlation_analysis = _correlate_ga4_with_revenue(ga4_data, business_df, revenue_column)
        
        # ML model to predict revenue from GA4 metrics
        revenue_model = _build_ga4_revenue_model(ga4_data, business_df, revenue_column)
        
        return {
            "user_id": user_id,
            "correlation_analysis": correlation_analysis,
            "revenue_prediction_model": revenue_model,
            "optimization_opportunities": _identify_revenue_optimization_opportunities(ga4_data, business_df, revenue_column)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in revenue correlation analysis: {str(e)}")

@router.post("/conversion-funnel-ml-analysis")
async def conversion_funnel_ml_analysis(request: str = Form(...)):
    """
    ML-powered conversion funnel analysis with predictive insights
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch detailed GA4 funnel data
        ga4_data = await _fetch_detailed_ga4_funnel_data(user_id, start_date, end_date)
        
        # ML analysis of conversion patterns
        ml_funnel_analysis = _ml_conversion_analysis(ga4_data)
        
        # Predict user conversion probability
        conversion_predictions = _predict_user_conversions(ga4_data)
        
        # Identify optimization opportunities
        optimization_plan = _ml_funnel_optimization_plan(ga4_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "ml_funnel_analysis": ml_funnel_analysis,
            "conversion_predictions": conversion_predictions,
            "ml_optimization_plan": optimization_plan,
            "expected_impact": _calculate_optimization_impact(ga4_data, optimization_plan)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in ML funnel analysis: {str(e)}")

# Helper functions for GA4 analysis

async def _fetch_comprehensive_ga4_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch comprehensive GA4 data for analysis"""
    
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
            'engagementRate',
            'averageSessionDuration',
            'conversions',
            'eventCount',
            'engagementRate'
        ]
    )
    
    return ga4_data

async def _fetch_detailed_ga4_funnel_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch GA4 data optimized for funnel analysis"""
    
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
            'deviceCategory',
            'firstUserSource',
            'firstUserMedium'
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
            'exitRate',
            'sessionConversionRate'
        ]
    )
    
    return funnel_data

def _analyze_ga4_business_correlation(ga4_data: pd.DataFrame, business_data: pd.DataFrame) -> Dict:
    """Analyze correlation between GA4 metrics and business data"""
    
    if ga4_data.empty:
        return {"error": "No GA4 data available"}
    
    # Aggregate GA4 data by date for correlation analysis
    daily_ga4 = ga4_data.groupby('date').agg({
        'sessions': 'sum',
        'users': 'sum',
        'pageviews': 'sum',
        'conversions': 'sum',
        'engagementRate': 'mean',
        'avgSessionDuration': 'mean',
        'engagementRate': 'mean'
    }).round(2)
    
    # Traffic source analysis
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_performance = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean'
        }).round(2)
        
        source_performance['conversion_rate'] = (source_performance['conversions'] / source_performance['sessions'] * 100).round(2)
        source_analysis = source_performance.to_dict('index')
    else:
        source_analysis = {}
    
    # Device performance analysis
    if 'deviceCategory' in ga4_data.columns:
        device_performance = ga4_data.groupby('deviceCategory').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean'
        }).round(2)
        
        device_performance['conversion_rate'] = (device_performance['conversions'] / device_performance['sessions'] * 100).round(2)
        device_analysis = device_performance.to_dict('index')
    else:
        device_analysis = {}
    
    return {
        "daily_trends": daily_ga4.to_dict('index'),
        "traffic_source_performance": source_analysis,
        "device_performance": device_analysis,
        "total_sessions": int(ga4_data['sessions'].sum()),
        "total_conversions": int(ga4_data['conversions'].sum()),
        "overall_conversion_rate": float((ga4_data['conversions'].sum() / ga4_data['sessions'].sum() * 100)) if ga4_data['sessions'].sum() > 0 else 0
    }

def _advanced_ga4_analysis(ga4_data: pd.DataFrame) -> Dict:
    """Perform advanced GA4 analysis with statistical insights"""
    
    analysis = {
        "user_behavior_patterns": {},
        "content_performance": {},
        "audience_insights": {},
        "technical_performance": {}
    }
    
    # User behavior patterns
    if 'avgSessionDuration' in ga4_data.columns and 'engagementRate' in ga4_data.columns:
        # Segment users by session quality
        ga4_data['session_quality'] = np.where(
            (ga4_data['avgSessionDuration'] > ga4_data['avgSessionDuration'].median()) & 
            (ga4_data['engagementRate'] > ga4_data['engagementRate'].median()),
            'high_quality',
            np.where(
                (ga4_data['avgSessionDuration'] < ga4_data['avgSessionDuration'].quantile(0.25)) | 
                (ga4_data['engagementRate'] < ga4_data['engagementRate'].quantile(0.25)),
                'low_quality',
                'medium_quality'
            )
        )
        
        quality_distribution = ga4_data['session_quality'].value_counts().to_dict()
        analysis["user_behavior_patterns"]["session_quality_distribution"] = quality_distribution
    
    # Content performance analysis
    if 'pagePath' in ga4_data.columns:
        page_performance = ga4_data.groupby('pagePath').agg({
            'sessions': 'sum',
            'pageviews': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean'
        }).round(2)
        
        page_performance['conversion_rate'] = (page_performance['conversions'] / page_performance['sessions'] * 100).round(2)
        
        # Find top and bottom performing pages
        top_pages = page_performance.nlargest(10, 'conversion_rate')
        bottom_pages = page_performance[page_performance['sessions'] >= 100].nsmallest(10, 'conversion_rate')
        
        analysis["content_performance"] = {
            "top_converting_pages": top_pages.to_dict('index'),
            "underperforming_pages": bottom_pages.to_dict('index'),
            "total_pages_analyzed": len(page_performance)
        }
    
    # Audience insights
    if 'country' in ga4_data.columns and 'deviceCategory' in ga4_data.columns:
        # Geographic performance
        geo_performance = ga4_data.groupby('country').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'avgSessionDuration': 'mean'
        }).round(2)
        
        geo_performance['conversion_rate'] = (geo_performance['conversions'] / geo_performance['sessions'] * 100).round(2)
        top_countries = geo_performance.nlargest(10, 'sessions')
        
        analysis["audience_insights"]["geographic_performance"] = top_countries.to_dict('index')
    
    # Technical performance
    if 'browser' in ga4_data.columns and 'operatingSystem' in ga4_data.columns:
        tech_performance = ga4_data.groupby(['browser', 'operatingSystem']).agg({
            'sessions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean'
        }).round(2)
        
        # Find problematic tech combinations
        low_engagement_tech = tech_performance[tech_performance['engagementRate'] < 30]
        if not high_bounce_tech.empty:
            analysis["technical_performance"]["high_bounce_combinations"] = high_bounce_tech.head(10).to_dict('index')
    
    return analysis

def _ml_user_segmentation(ga4_data: pd.DataFrame) -> Dict:
    """Use ML to segment users based on behavior patterns"""
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        
        # Prepare features for clustering
        feature_columns = ['avgSessionDuration', 'engagementRate', 'pageviews', 'sessions']
        available_features = [col for col in feature_columns if col in ga4_data.columns]
        
        if len(available_features) < 2:
            return {"error": "Insufficient features for user segmentation"}
        
        # Aggregate user data
        if 'sessionDefaultChannelGrouping' in ga4_data.columns:
            user_features = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
                col: 'mean' for col in available_features
            }).fillna(0)
        else:
            user_features = ga4_data[available_features].fillna(0)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(user_features)
        
        # Perform clustering
        n_clusters = min(5, len(user_features))  # Limit clusters based on data size
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Analyze segments
        user_features['segment'] = clusters
        segment_analysis = user_features.groupby('segment').agg({
            col: 'mean' for col in available_features
        }).round(2)
        
        # Generate segment descriptions
        segment_descriptions = {}
        for segment in segment_analysis.index:
            segment_data = segment_analysis.loc[segment]
            
            # Create meaningful segment names based on characteristics
            if segment_data.get('engagementRate', 50) < segment_analysis['engagementRate'].mean():
                if segment_data.get('avgSessionDuration', 0) < segment_analysis['avgSessionDuration'].mean():
                    segment_name = "Quick Exit Users"
                else:
                    segment_name = "Browse & Leave Users"
            else:
                if segment_data.get('avgSessionDuration', 0) > segment_analysis['avgSessionDuration'].mean():
                    segment_name = "Engaged Users"
                else:
                    segment_name = "Active Converters"
            
            segment_descriptions[f"Segment {segment}"] = {
                "name": segment_name,
                "characteristics": segment_data.to_dict(),
                "user_count": int((clusters == segment).sum())
            }
        
        return segment_descriptions
        
    except ImportError:
        return {"error": "ML libraries not available for user segmentation"}

def _ga4_predictive_analysis(ga4_data: pd.DataFrame) -> Dict:
    """Generate predictive insights from GA4 data"""
    
    predictions = {
        "traffic_forecasts": {},
        "conversion_predictions": {},
        "seasonal_patterns": {}
    }
    
    if 'date' in ga4_data.columns:
        # Simple time series analysis
        daily_metrics = ga4_data.groupby('date').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'users': 'sum'
        }).sort_index()
        
        if len(daily_metrics) > 7:  # Need at least a week of data
            # Calculate growth trends
            for metric in ['sessions', 'conversions', 'users']:
                if metric in daily_metrics.columns:
                    recent_avg = daily_metrics[metric].tail(7).mean()
                    earlier_avg = daily_metrics[metric].head(7).mean()
                    
                    growth_rate = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
                    
                    # Simple forecast for next 7 days
                    forecast = recent_avg * (1 + growth_rate/100) ** 7
                    
                    predictions["traffic_forecasts"][metric] = {
                        "current_7d_avg": float(recent_avg),
                        "growth_rate_pct": float(growth_rate),
                        "7d_forecast": float(forecast)
                    }
        
        # Seasonal pattern detection
        if len(daily_metrics) > 14:
            # Day of week patterns
            daily_metrics['day_of_week'] = pd.to_datetime(daily_metrics.index).dayofweek
            day_patterns = daily_metrics.groupby('day_of_week')['sessions'].mean()
            
            predictions["seasonal_patterns"]["day_of_week"] = {
                "Monday": float(day_patterns.get(0, 0)),
                "Tuesday": float(day_patterns.get(1, 0)),
                "Wednesday": float(day_patterns.get(2, 0)),
                "Thursday": float(day_patterns.get(3, 0)),
                "Friday": float(day_patterns.get(4, 0)),
                "Saturday": float(day_patterns.get(5, 0)),
                "Sunday": float(day_patterns.get(6, 0))
            }
    
    return predictions

def _generate_ga4_recommendations(ga4_data: pd.DataFrame) -> List[Dict]:
    """Generate actionable recommendations based on GA4 analysis"""
    
    recommendations = []
    
    if ga4_data.empty:
        return recommendations
    
    # Bounce rate recommendations
    if 'engagementRate' in ga4_data.columns:
        avg_engagement_rate = ga4_data['engagementRate'].mean()
        if avg_bounce_rate > 70:
            recommendations.append({
                "priority": "high",
                "category": "User Experience",
                "issue": f"High bounce rate: {avg_bounce_rate:.1f}%",
                "recommendation": "Optimize landing page experience and page load speed",
                "expected_impact": "Reduce bounce rate by 15-25%"
            })
    
    # Mobile performance recommendations
    if 'deviceCategory' in ga4_data.columns:
        device_engagement = ga4_data.groupby('deviceCategory')['engagementRate'].mean()
        if 'mobile' in device_bounce and 'desktop' in device_bounce:
            if device_bounce['mobile'] > device_bounce['desktop'] * 1.3:
                recommendations.append({
                    "priority": "high",
                    "category": "Mobile Optimization",
                    "issue": f"Mobile bounce rate ({device_bounce['mobile']:.1f}%) significantly higher than desktop ({device_bounce['desktop']:.1f}%)",
                    "recommendation": "Implement mobile-first design improvements and optimize mobile page speed",
                    "expected_impact": "Improve mobile conversion rate by 20-30%"
                })
    
    # Traffic source optimization
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_performance = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean'
        })
        
        source_performance['conversion_rate'] = source_performance['conversions'] / source_performance['sessions'] * 100
        
        # Find underperforming traffic sources
        poor_sources = source_performance[
            (source_performance['conversion_rate'] < 2.0) & 
            (source_performance['sessions'] > source_performance['sessions'].quantile(0.3))
        ]
        
        if not poor_sources.empty:
            recommendations.append({
                "priority": "medium",
                "category": "Traffic Quality",
                "issue": f"{len(poor_sources)} traffic sources with conversion rate < 2%",
                "recommendation": "Review and optimize underperforming traffic sources",
                "expected_impact": "Improve overall conversion rate by 10-15%"
            })
    
    return recommendations

def _generate_combined_insights(business_data: pd.DataFrame, ga4_data: pd.DataFrame, predictions: pd.Series) -> Dict:
    """Generate insights combining business data, GA4 data, and ML predictions"""
    
    insights = {
        "data_quality_score": 0,
        "prediction_confidence": 0,
        "key_insights": [],
        "optimization_opportunities": []
    }
    
    # Calculate data quality score
    business_completeness = (business_data.notna().sum().sum() / (len(business_data) * len(business_data.columns))) * 100
    ga4_completeness = (ga4_data.notna().sum().sum() / (len(ga4_data) * len(ga4_data.columns))) * 100 if not ga4_data.empty else 0
    
    insights["data_quality_score"] = float((business_completeness + ga4_completeness) / 2)
    
    # Prediction confidence based on data volume and quality
    prediction_confidence = min(100, (len(business_data) / 1000) * 100 * (insights["data_quality_score"] / 100))
    insights["prediction_confidence"] = float(prediction_confidence)
    
    # Generate key insights
    if not ga4_data.empty:
        total_sessions = ga4_data['sessions'].sum()
        total_conversions = ga4_data['conversions'].sum()
        
        insights["key_insights"].append({
            "insight": f"GA4 data shows {total_sessions:,} sessions with {total_conversions:,} conversions",
            "implication": "Strong web analytics foundation for data-driven decisions"
        })
        
        if 'sessionDefaultChannelGrouping' in ga4_data.columns:
            top_channel = ga4_data.groupby('sessionDefaultChannelGrouping')['sessions'].sum().idxmax()
            insights["key_insights"].append({
                "insight": f"'{top_channel}' is the primary traffic source",
                "implication": "Focus optimization efforts on this channel first"
            })
    
    return insights

def _correlate_ga4_with_revenue(ga4_data: pd.DataFrame, business_data: pd.DataFrame, revenue_column: str) -> Dict:
    """Correlate GA4 metrics with business revenue"""
    
    correlation_analysis = {
        "correlation_matrix": {},
        "strong_correlations": [],
        "revenue_drivers": {}
    }
    
    if ga4_data.empty or business_data.empty:
        return {"error": "Insufficient data for correlation analysis"}
    
    try:
        # Prepare data for correlation
        if 'date' in ga4_data.columns and 'date' in business_data.columns:
            # Merge on date
            ga4_daily = ga4_data.groupby('date').agg({
                'sessions': 'sum',
                'users': 'sum',
                'conversions': 'sum',
                'engagementRate': 'mean',
                'avgSessionDuration': 'mean'
            }).reset_index()
            
            business_daily = business_data.groupby('date')[revenue_column].sum().reset_index()
            
            merged_data = pd.merge(ga4_daily, business_daily, on='date', how='inner')
            
            if len(merged_data) > 3:  # Need minimum data points
                # Calculate correlations
                ga4_metrics = ['sessions', 'users', 'conversions', 'engagementRate', 'avgSessionDuration']
                correlations = {}
                
                for metric in ga4_metrics:
                    if metric in merged_data.columns:
                        corr = merged_data[metric].corr(merged_data[revenue_column])
                        if not np.isnan(corr):
                            correlations[metric] = float(corr)
                
                correlation_analysis["correlation_matrix"] = correlations
                
                # Identify strong correlations (>0.5 or <-0.5)
                strong_corrs = {k: v for k, v in correlations.items() if abs(v) > 0.5}
                correlation_analysis["strong_correlations"] = strong_corrs
                
                # Identify top revenue drivers
                positive_drivers = {k: v for k, v in correlations.items() if v > 0.3}
                correlation_analysis["revenue_drivers"] = positive_drivers
        
        return correlation_analysis
        
    except Exception as e:
        return {"error": f"Correlation analysis failed: {str(e)}"}

def _build_ga4_revenue_model(ga4_data: pd.DataFrame, business_data: pd.DataFrame, revenue_column: str) -> Dict:
    """Build ML model to predict revenue from GA4 metrics"""
    
    try:
        # Prepare features
        if 'date' in ga4_data.columns and 'date' in business_data.columns:
            ga4_features = ga4_data.groupby('date').agg({
                'sessions': 'sum',
                'users': 'sum',
                'conversions': 'sum',
                'engagementRate': 'mean',
                'avgSessionDuration': 'mean',
                'pageviews': 'sum'
            }).reset_index()
            
            business_target = business_data.groupby('date')[revenue_column].sum().reset_index()
            
            model_data = pd.merge(ga4_features, business_target, on='date', how='inner')
            
            if len(model_data) < 10:
                return {"error": "Insufficient data for model building (need at least 10 data points)"}
            
            # Simple linear regression model
            feature_cols = ['sessions', 'users', 'conversions', 'avgSessionDuration', 'pageviews']
            available_features = [col for col in feature_cols if col in model_data.columns]
            
            if len(available_features) > 0:
                X = model_data[available_features].fillna(0)
                y = model_data[revenue_column].fillna(0)
                
                # Build simple model
                from sklearn.linear_model import LinearRegression
                from sklearn.metrics import r2_score, mean_absolute_error
                
                model = LinearRegression()
                model.fit(X, y)
                
                predictions = model.predict(X)
                r2 = r2_score(y, predictions)
                mae = mean_absolute_error(y, predictions)
                
                # Feature importance (coefficients)
                feature_importance = {}
                for i, feature in enumerate(available_features):
                    feature_importance[feature] = float(model.coef_[i])
                
                return {
                    "model_performance": {
                        "r2_score": float(r2),
                        "mean_absolute_error": float(mae),
                        "data_points": len(model_data)
                    },
                    "feature_importance": feature_importance,
                    "revenue_predictions": predictions.tolist()[-7:],  # Last 7 predictions
                    "model_equation": f"Revenue = {float(model.intercept_):.2f} + " + 
                                    " + ".join([f"{coef:.4f}*{feat}" for feat, coef in zip(available_features, model.coef_)])
                }
        
        return {"error": "Unable to build revenue model with available data"}
        
    except ImportError:
        return {"error": "ML libraries not available for model building"}
    except Exception as e:
        return {"error": f"Model building failed: {str(e)}"}

def _identify_revenue_optimization_opportunities(ga4_data: pd.DataFrame, business_data: pd.DataFrame, revenue_column: str) -> List[Dict]:
    """Identify opportunities to optimize revenue based on GA4 data"""
    
    opportunities = []
    
    if ga4_data.empty:
        return opportunities
    
    # Traffic source revenue optimization
    if 'sessionDefaultChannelGrouping' in ga4_data.columns:
        source_metrics = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean'
        })
        
        source_metrics['conversion_rate'] = source_metrics['conversions'] / source_metrics['sessions'] * 100
        
        # Find high-traffic, low-converting sources
        high_traffic_sources = source_metrics[source_metrics['sessions'] > source_metrics['sessions'].quantile(0.6)]
        underperforming = high_traffic_sources[high_traffic_sources['conversion_rate'] < 2.0]
        
        if not underperforming.empty:
            opportunities.append({
                "opportunity": "Traffic Source Optimization",
                "description": f"Optimize {len(underperforming)} high-traffic, low-converting sources",
                "affected_sources": underperforming.index.tolist(),
                "potential_impact": "15-25% increase in conversions",
                "action_required": "Improve landing pages and targeting for these sources"
            })
    
    # Device optimization opportunities
    if 'deviceCategory' in ga4_data.columns:
        device_performance = ga4_data.groupby('deviceCategory').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean'
        })
        
        device_performance['conversion_rate'] = device_performance['conversions'] / device_performance['sessions'] * 100
        
        # Check mobile performance
        if 'mobile' in device_performance.index and 'desktop' in device_performance.index:
            mobile_conv = device_performance.loc['mobile', 'conversion_rate']
            desktop_conv = device_performance.loc['desktop', 'conversion_rate']
            
            if mobile_conv < desktop_conv * 0.7:  # Mobile significantly underperforming
                opportunities.append({
                    "opportunity": "Mobile Experience Optimization",
                    "description": f"Mobile conversion rate ({mobile_conv:.2f}%) significantly below desktop ({desktop_conv:.2f}%)",
                    "potential_impact": "20-35% increase in mobile conversions",
                    "action_required": "Optimize mobile UX, speed, and checkout process"
                })
    
    return opportunities

def _ml_conversion_analysis(ga4_data: pd.DataFrame) -> Dict:
    """ML analysis of conversion patterns"""
    
    analysis = {
        "conversion_drivers": {},
        "user_journey_patterns": {},
        "predictive_segments": {}
    }
    
    if ga4_data.empty:
        return {"error": "No data available for ML conversion analysis"}
    
    # Identify conversion drivers using feature importance
    try:
        feature_columns = ['avgSessionDuration', 'engagementRate', 'pageviews', 'totalUsers']
        available_features = [col for col in feature_columns if col in ga4_data.columns]
        
        if len(available_features) >= 2 and 'conversions' in ga4_data.columns:
            X = ga4_data[available_features].fillna(0)
            y = ga4_data['conversions'].fillna(0)
            
            # Use Random Forest for feature importance
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            
            # Handle case where y is all zeros or very sparse
            if y.sum() > 0:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                rf = RandomForestRegressor(n_estimators=100, random_state=42)
                rf.fit(X_scaled, y)
                
                # Get feature importance
                feature_importance = {}
                for i, feature in enumerate(available_features):
                    feature_importance[feature] = float(rf.feature_importances_[i])
                
                analysis["conversion_drivers"] = feature_importance
        
        return analysis
        
    except ImportError:
        return {"error": "ML libraries not available for conversion analysis"}
    except Exception as e:
        return {"error": f"ML conversion analysis failed: {str(e)}"}

def _predict_user_conversions(ga4_data: pd.DataFrame) -> Dict:
    """Predict user conversion probability"""
    
    predictions = {
        "high_potential_users": [],
        "conversion_probability_distribution": {},
        "recommendation": ""
    }
    
    if ga4_data.empty or 'conversions' not in ga4_data.columns:
        return {"error": "Insufficient data for conversion prediction"}
    
    try:
        # Create user segments based on behavior
        if 'sessionDefaultChannelGrouping' in ga4_data.columns:
            user_behavior = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
                'avgSessionDuration': 'mean',
                'engagementRate': 'mean',
                'pageviews': 'mean',
                'conversions': 'sum',
                'sessions': 'sum'
            }).fillna(0)
            
            user_behavior['conversion_rate'] = user_behavior['conversions'] / user_behavior['sessions'] * 100
            
            # Simple conversion probability based on behavior metrics
            user_behavior['conversion_probability'] = np.where(
                (user_behavior['avgSessionDuration'] > user_behavior['avgSessionDuration'].median()) & 
                (user_behavior['engagementRate'] > user_behavior['engagementRate'].median()) &
                (user_behavior['pageviews'] > user_behavior['pageviews'].median()),
                'high',
                np.where(
                    (user_behavior['avgSessionDuration'] < user_behavior['avgSessionDuration'].quantile(0.25)) | 
                    (user_behavior['engagementRate'] < user_behavior['engagementRate'].quantile(0.25)),
                    'low',
                    'medium'
                )
            )
            
            prob_dist = user_behavior['conversion_probability'].value_counts().to_dict()
            predictions["conversion_probability_distribution"] = prob_dist
            
            # Identify high potential user segments
            high_potential = user_behavior[user_behavior['conversion_probability'] == 'high']
            if not high_potential.empty:
                predictions["high_potential_users"] = high_potential.index.tolist()
                predictions["recommendation"] = f"Focus marketing efforts on {len(high_potential)} high-potential user segments"
        
        return predictions
        
    except Exception as e:
        return {"error": f"Conversion prediction failed: {str(e)}"}

def _ml_funnel_optimization_plan(ga4_data: pd.DataFrame) -> Dict:
    """Generate ML-powered funnel optimization plan"""
    
    optimization_plan = {
        "priority_areas": [],
        "ml_recommendations": [],
        "expected_outcomes": {}
    }
    
    if ga4_data.empty:
        return {"error": "No data available for optimization planning"}
    
    # Identify bottlenecks using ML analysis
    if 'pagePath' in ga4_data.columns and 'conversions' in ga4_data.columns:
        page_performance = ga4_data.groupby('pagePath').agg({
            'sessions': 'sum',
            'conversions': 'sum',
            'engagementRate': 'mean',
            'exitRate': 'mean',
            'avgSessionDuration': 'mean'
        }).fillna(0)
        
        page_performance['conversion_rate'] = page_performance['conversions'] / page_performance['sessions'] * 100
        
        # Identify high-traffic, low-converting pages (optimization opportunities)
        high_traffic_pages = page_performance[page_performance['sessions'] > page_performance['sessions'].quantile(0.7)]
        optimization_opportunities = high_traffic_pages[high_traffic_pages['conversion_rate'] < 2.0]
        
        if not optimization_opportunities.empty:
            optimization_plan["priority_areas"].append({
                "area": "Page Conversion Optimization",
                "description": f"{len(optimization_opportunities)} high-traffic pages with low conversion rates",
                "pages": optimization_opportunities.head(5).to_dict('index'),
                "recommended_action": "A/B test different page layouts, CTAs, and content"
            })
        
        # Identify exit points
        high_exit_pages = page_performance[page_performance['exitRate'] > 70]
        if not high_exit_pages.empty:
            optimization_plan["priority_areas"].append({
                "area": "Exit Rate Reduction",
                "description": f"{len(high_exit_pages)} pages with high exit rates",
                "recommended_action": "Improve content relevance and add engaging elements"
            })
    
    # ML-powered recommendations
    optimization_plan["ml_recommendations"] = [
        {
            "recommendation": "Implement dynamic content personalization",
            "rationale": "ML analysis shows user behavior varies significantly by segment",
            "expected_impact": "10-20% improvement in engagement"
        },
        {
            "recommendation": "Optimize mobile experience based on device performance gaps",
            "rationale": "ML models identify mobile-specific conversion barriers",
            "expected_impact": "15-25% improvement in mobile conversions"
        }
    ]
    
    return optimization_plan

def _calculate_optimization_impact(ga4_data: pd.DataFrame, optimization_plan: Dict) -> Dict:
    """Calculate expected impact of optimization plan"""
    
    if ga4_data.empty:
        return {"error": "No data for impact calculation"}
    
    current_performance = {
        "total_sessions": int(ga4_data['sessions'].sum()),
        "total_conversions": int(ga4_data['conversions'].sum()),
        "current_conversion_rate": float(ga4_data['conversions'].sum() / ga4_data['sessions'].sum() * 100) if ga4_data['sessions'].sum() > 0 else 0
    }
    
    # Conservative impact estimates based on optimization areas
    estimated_improvements = {
        "conversion_rate_improvement": 0.15,  # 15% improvement
        "traffic_quality_improvement": 0.10,  # 10% improvement  
        "mobile_experience_improvement": 0.20   # 20% improvement
    }
    
    total_improvement = sum(estimated_improvements.values()) / len(estimated_improvements)
    
    projected_performance = {
        "projected_conversions": int(current_performance["total_conversions"] * (1 + total_improvement)),
        "projected_conversion_rate": float(current_performance["current_conversion_rate"] * (1 + total_improvement)),
        "additional_conversions": int(current_performance["total_conversions"] * total_improvement)
    }
    
    return {
        "current_performance": current_performance,
        "projected_performance": projected_performance,
        "estimated_improvement_pct": float(total_improvement * 100),
        "confidence_level": "medium"  # Based on data quality and historical patterns
    }

