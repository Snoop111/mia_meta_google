from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import pandas as pd
import os
import json
from autogluon.tabular import TabularPredictor
import shap
from models import PredictRequest, PredictWithDataRequest
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from credential_manager import credential_manager
from shared_integrator import data_integrator_instance
import data_integrator

router = APIRouter()

model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

@router.post("/predict")
def train_predict(file: UploadFile = File(...), request: str = Form(...)):
    req_data = PredictRequest(**json.loads(request))
    df = pd.read_csv(file.file)
    if req_data.target not in df.columns:
        raise HTTPException(status_code=400, detail="Target column not in data")
    predictor_path = os.path.join(model_dir, req_data.id)
    predictor = TabularPredictor(label=req_data.target, path=predictor_path).fit(df)
    pred = predictor.predict(df)
    try:
        model_names = predictor.get_model_names()
        best_model = model_names[0]
        if any(name in best_model.lower() for name in ["xgboost", "lightgbm", "catboost"]):
            explainer = shap.Explainer(predictor._trainer.load_model(best_model).model)
            shap_values = explainer(df.drop(columns=[req_data.target]))
            shap_summary = shap_values.values.mean(axis=0).tolist()
        else:
            raise Exception()
    except:
        shap_summary = predictor.feature_importance(df)["importance"].tolist()
    return {"predictions": pred.tolist(), "shap_summary": shap_summary}

@router.post("/predict-traffic")
async def predict_traffic(request: str = Form(...)):
    """
    Predict future traffic patterns based on GA4 historical data
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    forecast_days = req_data.get('forecast_days', 30)
    
    if not all([user_id, start_date, end_date]):
        raise HTTPException(status_code=400, detail="user_id, start_date, and end_date are required")
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Fetch GA4 data
        ga4_data = await _fetch_ga4_time_series_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found")
        
        # Preprocess data to handle type issues
        ga4_data = _preprocess_ga4_data(ga4_data)
        
        # Build traffic prediction model
        traffic_predictions = _build_traffic_prediction_model(ga4_data, forecast_days)
        
        return {
            "user_id": user_id,
            "training_period": f"{start_date} to {end_date}",
            "forecast_period": f"{forecast_days} days",
            "traffic_predictions": traffic_predictions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting traffic: {str(e)}")

@router.post("/predict-conversions")
async def predict_conversions(request: str = Form(...)):
    """
    Predict future conversions based on GA4 data and trends
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    forecast_days = req_data.get('forecast_days', 30)
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        ga4_data = await _fetch_ga4_time_series_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found")
        
        # Preprocess data to handle type issues
        ga4_data = _preprocess_ga4_data(ga4_data)
        
        # Build conversion prediction model
        conversion_predictions = _build_conversion_prediction_model(ga4_data, forecast_days)
        
        return {
            "user_id": user_id,
            "training_period": f"{start_date} to {end_date}",
            "forecast_period": f"{forecast_days} days",
            "conversion_predictions": conversion_predictions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting conversions: {str(e)}")

@router.post("/predict-user-segments")
async def predict_user_segments(request: str = Form(...)):
    """
    Predict user behavior segments and their future performance
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found")
        
        # Preprocess data to handle type issues
        ga4_data = _preprocess_ga4_data(ga4_data)
        
        # Predict user segments and behavior
        segment_predictions = _predict_user_segments(ga4_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "segment_predictions": segment_predictions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting user segments: {str(e)}")

@router.post("/predict-revenue-impact")
async def predict_revenue_impact(file: UploadFile = File(...), request: str = Form(...)):
    """
    Predict revenue impact of GA4 optimization scenarios
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    optimization_scenarios = req_data.get('optimization_scenarios', [])
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        # Load revenue data
        revenue_df = pd.read_csv(file.file)
        
        # Fetch GA4 data
        ga4_data = await _fetch_comprehensive_ga4_data(user_id, start_date, end_date)
        
        # Build revenue impact prediction model
        revenue_impact = _predict_revenue_impact(ga4_data, revenue_df, optimization_scenarios)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "revenue_impact_predictions": revenue_impact
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting revenue impact: {str(e)}")

@router.post("/predict-seasonal-trends")
async def predict_seasonal_trends(request: str = Form(...)):
    """
    Predict seasonal trends and patterns in GA4 data
    """
    req_data = json.loads(request)
    user_id = req_data.get('user_id')
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    credential_manager.load_user_connectors(user_id)
    
    try:
        ga4_data = await _fetch_ga4_time_series_data(user_id, start_date, end_date)
        
        if ga4_data.empty:
            raise HTTPException(status_code=404, detail="No GA4 data found")
        
        # Preprocess data to handle type issues
        ga4_data = _preprocess_ga4_data(ga4_data)
        
        # Analyze seasonal patterns and predict trends
        seasonal_predictions = _predict_seasonal_trends(ga4_data)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{start_date} to {end_date}",
            "seasonal_predictions": seasonal_predictions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting seasonal trends: {str(e)}")

# Helper functions for GA4 predictive analytics

async def _fetch_ga4_time_series_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch GA4 data optimized for time series analysis"""
    
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch time series data
    ga4_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'date',
            'sessionDefaultChannelGrouping',
            'deviceCategory'
        ],
        metrics=[
            'sessions',
            'totalUsers',
            'newUsers',
            'screenPageViews',
            'conversions',
            'eventCount',
            'engagementRate',
            'averageSessionDuration'
        ]
    )
    
    return ga4_data

async def _fetch_comprehensive_ga4_data(user_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch comprehensive GA4 data for predictive analysis"""
    
    ga4_connector = None
    for name, connector in data_integrator_instance.connectors.items():
        if name == 'ga4' and isinstance(connector, data_integrator.GA4Connector):
            ga4_connector = connector
            break
    
    if not ga4_connector:
        raise Exception("GA4 connector not found for user")
    
    # Fetch comprehensive data
    ga4_data = await ga4_connector.fetch_data(
        start_date=start_date,
        end_date=end_date,
        dimensions=[
            'date',
            'sessionDefaultChannelGrouping',
            'sessionSourceMedium',
            'pagePath',
            'deviceCategory',
            'country'
        ],
        metrics=[
            'sessions',
            'totalUsers',
            'newUsers',
            'screenPageViews',
            'conversions',
            'eventCount',
            'engagementRate',
            'averageSessionDuration'
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

def _build_traffic_prediction_model(ga4_data: pd.DataFrame, forecast_days: int) -> Dict:
    """Build traffic prediction model using GA4 data"""
    
    try:
        # Prepare time series data
        daily_traffic = ga4_data.groupby('date').agg({
            'sessions': 'sum',
            'totalUsers': 'sum',
            'screenPageViews': 'sum'
        }).sort_index()
        
        if len(daily_traffic) < 14:
            return {"error": "Need at least 14 days of data for reliable predictions"}
        
        # Simple trend analysis
        predictions = {}
        
        for metric in ['sessions', 'totalUsers', 'screenPageViews']:
            if metric in daily_traffic.columns:
                # Calculate trend
                values = daily_traffic[metric].values
                days = np.arange(len(values))
                
                # Simple linear trend
                z = np.polyfit(days, values, 1)
                trend_slope = z[0]
                
                # Calculate moving averages for seasonality
                recent_avg = daily_traffic[metric].tail(7).mean()
                overall_avg = daily_traffic[metric].mean()
                
                # Simple forecast
                forecast_values = []
                for i in range(forecast_days):
                    forecast_day = len(values) + i
                    base_prediction = z[1] + z[0] * forecast_day
                    
                    # Add weekly seasonality (simplified)
                    day_of_week = forecast_day % 7
                    weekly_pattern = daily_traffic[metric].groupby(daily_traffic.index.to_series().dt.dayofweek).mean()
                    if day_of_week in weekly_pattern.index:
                        seasonal_factor = weekly_pattern[day_of_week] / overall_avg
                        base_prediction *= seasonal_factor
                    
                    forecast_values.append(max(0, base_prediction))
                
                predictions[metric] = {
                    "historical_avg": float(overall_avg),
                    "recent_avg": float(recent_avg),
                    "trend": "growing" if trend_slope > 0 else "declining" if trend_slope < 0 else "stable",
                    "trend_rate": float(trend_slope),
                    "forecast": [float(x) for x in forecast_values],
                    "forecast_total": float(sum(forecast_values)),
                    "confidence": "medium" if len(daily_traffic) > 30 else "low"
                }
        
        return predictions
        
    except Exception as e:
        return {"error": f"Traffic prediction failed: {str(e)}"}

def _build_conversion_prediction_model(ga4_data: pd.DataFrame, forecast_days: int) -> Dict:
    """Build conversion prediction model"""
    
    try:
        if 'conversions' not in ga4_data.columns:
            return {"error": "No conversion data available"}
        
        # Prepare conversion time series
        daily_conversions = ga4_data.groupby('date').agg({
            'conversions': 'sum',
            'sessions': 'sum'
        }).sort_index()
        
        daily_conversions['calculated_conversion_rate'] = (daily_conversions['conversions'] / daily_conversions['sessions'] * 100).fillna(0)
        
        if len(daily_conversions) < 14:
            return {"error": "Need at least 14 days of data for reliable conversion predictions"}
        
        # Analyze conversion patterns
        conversion_predictions = {}
        
        # Conversion volume prediction
        conversion_values = daily_conversions['conversions'].values
        conversion_days = np.arange(len(conversion_values))
        
        # Fit trend
        z_conv = np.polyfit(conversion_days, conversion_values, 1)
        
        # Recent performance
        recent_conv_avg = daily_conversions['conversions'].tail(7).mean()
        recent_conv_rate = daily_conversions['calculated_conversion_rate'].tail(7).mean()
        overall_conv_rate = daily_conversions['calculated_conversion_rate'].mean()
        
        # Forecast conversions
        forecast_conversions = []
        for i in range(forecast_days):
            forecast_day = len(conversion_values) + i
            predicted_conversions = max(0, z_conv[1] + z_conv[0] * forecast_day)
            forecast_conversions.append(predicted_conversions)
        
        conversion_predictions = {
            "historical_daily_avg": float(daily_conversions['conversions'].mean()),
            "recent_daily_avg": float(recent_conv_avg),
            "historical_conversion_rate": float(overall_conv_rate),
            "recent_conversion_rate": float(recent_conv_rate),
            "trend": "improving" if z_conv[0] > 0 else "declining" if z_conv[0] < 0 else "stable",
            "forecast_daily_conversions": [float(x) for x in forecast_conversions],
            "forecast_total_conversions": float(sum(forecast_conversions)),
            "performance_outlook": _assess_conversion_outlook(recent_conv_rate, overall_conv_rate, z_conv[0])
        }
        
        return conversion_predictions
        
    except Exception as e:
        return {"error": f"Conversion prediction failed: {str(e)}"}

def _predict_user_segments(ga4_data: pd.DataFrame) -> Dict:
    """Predict user behavior segments using ML"""
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        # Prepare features for segmentation
        feature_data = ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'avgSessionDuration': 'mean',
            'engagementRate': 'mean',
            'screenPageViews': 'mean',
            'sessions': 'sum',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0
        }).fillna(0)
        
        feature_data['conversion_rate'] = (feature_data['conversions'] / feature_data['sessions'] * 100).fillna(0)
        
        if len(feature_data) < 3:
            return {"error": "Need at least 3 traffic sources for user segmentation"}
        
        # Features for clustering
        features = ['avgSessionDuration', 'engagementRate', 'screenPageViews', 'conversion_rate']
        X = feature_data[features].fillna(0)
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Perform clustering
        n_clusters = min(4, len(feature_data))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Analyze segments
        feature_data['segment'] = clusters
        segment_analysis = {}
        
        for segment in range(n_clusters):
            segment_data = feature_data[feature_data['segment'] == segment]
            
            # Characterize segment
            avg_conv_rate = segment_data['conversion_rate'].mean()
            avg_engagement = segment_data['engagementRate'].mean()
            avg_duration = segment_data['avgSessionDuration'].mean()
            total_sessions = segment_data['sessions'].sum()
            
            # Assign segment name
            if avg_conv_rate > 3 and avg_engagement > 50:
                segment_name = "High-Value Users"
                outlook = "excellent"
            elif avg_conv_rate > 1.5:
                segment_name = "Converting Users"
                outlook = "good"
            elif avg_engagement > 60:
                segment_name = "Engaged Browsers"
                outlook = "promising"
            else:
                segment_name = "Opportunity Users"
                outlook = "needs_improvement"
            
            segment_analysis[f"Segment {segment + 1}"] = {
                "name": segment_name,
                "outlook": outlook,
                "characteristics": {
                    "avg_conversion_rate": float(avg_conv_rate),
                    "avg_engagement_rate": float(avg_engagement),
                    "avg_session_duration": float(avg_duration),
                    "total_sessions": int(total_sessions)
                },
                "traffic_sources": segment_data.index.tolist(),
                "predicted_performance": _predict_segment_performance(avg_conv_rate, avg_engagement, total_sessions)
            }
        
        return {
            "total_segments": n_clusters,
            "segment_analysis": segment_analysis,
            "recommendations": _generate_segment_recommendations(segment_analysis)
        }
        
    except ImportError:
        return {"error": "ML libraries not available for user segmentation"}
    except Exception as e:
        return {"error": f"User segmentation prediction failed: {str(e)}"}

def _predict_revenue_impact(ga4_data: pd.DataFrame, revenue_data: pd.DataFrame, scenarios: List[Dict]) -> Dict:
    """Predict revenue impact of optimization scenarios"""
    
    try:
        # Current performance baseline
        current_sessions = ga4_data['sessions'].sum()
        current_conversions = ga4_data['conversions'].sum() if 'conversions' in ga4_data.columns else 0
        current_conv_rate = (current_conversions / current_sessions * 100) if current_sessions > 0 else 0
        
        # Estimate current revenue (simplified)
        avg_revenue_per_conversion = revenue_data.iloc[:, -1].mean() if not revenue_data.empty else 100
        current_revenue = current_conversions * avg_revenue_per_conversion
        
        scenario_predictions = {}
        
        # Default scenarios if none provided
        if not scenarios:
            scenarios = [
                {"name": "Bounce Rate Optimization", "bounce_reduction": 15, "expected_conversion_lift": 20},
                {"name": "Mobile Experience Improvement", "mobile_sessions_boost": 10, "mobile_conversion_boost": 25},
                {"name": "Traffic Source Optimization", "traffic_increase": 15, "quality_improvement": 10}
            ]
        
        for scenario in scenarios:
            scenario_name = scenario.get('name', 'Unnamed Scenario')
            
            # Calculate scenario impact
            new_sessions = current_sessions
            new_conv_rate = current_conv_rate
            
            # Apply scenario parameters
            if 'bounce_reduction' in scenario:
                bounce_impact = scenario['bounce_reduction'] / 100
                new_conv_rate *= (1 + bounce_impact * 0.5)  # Bounce reduction improves conversions
            
            if 'traffic_increase' in scenario:
                traffic_impact = scenario['traffic_increase'] / 100
                new_sessions *= (1 + traffic_impact)
            
            if 'expected_conversion_lift' in scenario:
                conv_lift = scenario['expected_conversion_lift'] / 100
                new_conv_rate *= (1 + conv_lift)
            
            # Calculate projected metrics
            projected_conversions = (new_sessions * new_conv_rate / 100)
            projected_revenue = projected_conversions * avg_revenue_per_conversion
            
            scenario_predictions[scenario_name] = {
                "projected_sessions": int(new_sessions),
                "projected_conversions": int(projected_conversions),
                "projected_conversion_rate": round(new_conv_rate, 2),
                "projected_monthly_revenue": round(projected_revenue, 2),
                "revenue_increase": round(projected_revenue - current_revenue, 2),
                "revenue_lift_percentage": round(((projected_revenue - current_revenue) / current_revenue * 100), 1) if current_revenue > 0 else 0,
                "roi_outlook": "high" if projected_revenue > current_revenue * 1.2 else "medium" if projected_revenue > current_revenue * 1.1 else "low"
            }
        
        return {
            "current_baseline": {
                "monthly_sessions": int(current_sessions),
                "monthly_conversions": int(current_conversions),
                "conversion_rate": round(current_conv_rate, 2),
                "estimated_monthly_revenue": round(current_revenue, 2)
            },
            "scenario_predictions": scenario_predictions,
            "best_scenario": max(scenario_predictions.items(), key=lambda x: x[1]['revenue_increase'])[0] if scenario_predictions else None
        }
        
    except Exception as e:
        return {"error": f"Revenue impact prediction failed: {str(e)}"}

def _predict_seasonal_trends(ga4_data: pd.DataFrame) -> Dict:
    """Predict seasonal trends and patterns"""
    
    try:
        # Prepare data for seasonal analysis
        daily_data = ga4_data.groupby('date').agg({
            'sessions': 'sum',
            'conversions': 'sum' if 'conversions' in ga4_data.columns else lambda x: 0,
            'totalUsers': 'sum'
        }).sort_index()
        
        if len(daily_data) < 28:
            return {"error": "Need at least 28 days of data for seasonal analysis"}
        
        # Convert index to datetime
        daily_data.index = pd.to_datetime(daily_data.index)
        
        # Day of week patterns
        daily_data['day_of_week'] = daily_data.index.dayofweek
        dow_patterns = daily_data.groupby('day_of_week').agg({
            'sessions': 'mean',
            'conversions': 'mean',
            'totalUsers': 'mean'
        })
        
        # Week over week trends
        weekly_data = daily_data.resample('W').sum()
        
        seasonal_insights = {
            "day_of_week_patterns": {
                "Monday": {"sessions": float(dow_patterns.loc[0, 'sessions']), "conversions": float(dow_patterns.loc[0, 'conversions'])},
                "Tuesday": {"sessions": float(dow_patterns.loc[1, 'sessions']), "conversions": float(dow_patterns.loc[1, 'conversions'])},
                "Wednesday": {"sessions": float(dow_patterns.loc[2, 'sessions']), "conversions": float(dow_patterns.loc[2, 'conversions'])},
                "Thursday": {"sessions": float(dow_patterns.loc[3, 'sessions']), "conversions": float(dow_patterns.loc[3, 'conversions'])},
                "Friday": {"sessions": float(dow_patterns.loc[4, 'sessions']), "conversions": float(dow_patterns.loc[4, 'conversions'])},
                "Saturday": {"sessions": float(dow_patterns.loc[5, 'sessions']), "conversions": float(dow_patterns.loc[5, 'conversions'])},
                "Sunday": {"sessions": float(dow_patterns.loc[6, 'sessions']), "conversions": float(dow_patterns.loc[6, 'conversions'])}
            },
            "best_performing_days": dow_patterns['sessions'].nlargest(3).index.tolist(),
            "worst_performing_days": dow_patterns['sessions'].nsmallest(2).index.tolist(),
            "weekly_trend": "growing" if len(weekly_data) > 1 and weekly_data['sessions'].iloc[-1] > weekly_data['sessions'].iloc[0] else "stable",
            "seasonal_recommendations": _generate_seasonal_recommendations(dow_patterns)
        }
        
        return seasonal_insights
        
    except Exception as e:
        return {"error": f"Seasonal trend prediction failed: {str(e)}"}

def _assess_conversion_outlook(recent_rate: float, historical_rate: float, trend_slope: float) -> str:
    """Assess conversion performance outlook"""
    
    if recent_rate > historical_rate * 1.1 and trend_slope > 0:
        return "improving - strong upward trend"
    elif recent_rate > historical_rate and trend_slope > 0:
        return "improving - positive momentum"
    elif trend_slope > 0:
        return "stable with growth potential"
    elif recent_rate < historical_rate * 0.9:
        return "declining - needs attention"
    else:
        return "stable - monitor for changes"

def _predict_segment_performance(conv_rate: float, engagement_rate: float, sessions: int) -> str:
    """Predict future performance of user segment"""
    
    if conv_rate > 3 and engagement_rate > 60:
        return "excellent - focus on scaling this segment"
    elif conv_rate > 1.5 and sessions > 1000:
        return "good - optimize for better conversion rates"
    elif engagement_rate > 50:
        return "promising - improve conversion funnel"
    else:
        return "needs improvement - review user experience"

def _generate_segment_recommendations(segment_analysis: Dict) -> List[Dict]:
    """Generate recommendations for user segments"""
    
    recommendations = []
    
    for segment_name, segment_data in segment_analysis.items():
        if segment_data['outlook'] == 'excellent':
            recommendations.append({
                "segment": segment_name,
                "priority": "high",
                "action": "Scale successful elements",
                "description": f"Increase investment in {', '.join(segment_data['traffic_sources'])} to grow this high-performing segment"
            })
        elif segment_data['outlook'] == 'needs_improvement':
            recommendations.append({
                "segment": segment_name,
                "priority": "medium",
                "action": "Optimize user experience",
                "description": f"Focus on reducing bounce rate and improving conversion funnel for {', '.join(segment_data['traffic_sources'])}"
            })
    
    return recommendations

def _generate_seasonal_recommendations(dow_patterns: pd.DataFrame) -> List[Dict]:
    """Generate seasonal optimization recommendations"""
    
    recommendations = []
    
    # Find best and worst days
    best_day = dow_patterns['sessions'].idxmax()
    worst_day = dow_patterns['sessions'].idxmin()
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    recommendations.append({
        "type": "peak_day_optimization",
        "description": f"{day_names[best_day]} is your best performing day",
        "action": f"Increase ad spend and content promotion on {day_names[best_day]}s"
    })
    
    recommendations.append({
        "type": "low_day_improvement",
        "description": f"{day_names[worst_day]} has the lowest traffic",
        "action": f"Test special promotions or content strategies for {day_names[worst_day]}s"
    })
    
    return recommendations

# Additional endpoints (predict-with-external-data, etc.) can be added here following the same pattern.

