from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import os
import json
import numpy as np
from autogluon.tabular import TabularPredictor
import shap
from sklearn.cluster import KMeans

from models import PredictWithDataRequest, PredictWithUserDataRequest
from shared_integrator import data_integrator_instance
from credential_manager import credential_manager

router = APIRouter()

model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

@router.post("/predict-with-external-data")
async def predict_with_external_data(
    file: UploadFile = File(None),
    request: str = Form(...)
):
    req_data = PredictWithDataRequest(**json.loads(request))
    df = pd.read_csv(file.file) if file is not None else None
    if df is not None and req_data.target and req_data.target not in df.columns:
        raise HTTPException(status_code=400, detail="Target column not in data")
    external_df = None
    if req_data.use_external_data and req_data.start_date and req_data.end_date:
        try:
            if req_data.data_sources:
                external_df = await data_integrator_instance.fetch_specific_data(
                    connector_names=req_data.data_sources,
                    start_date=req_data.start_date,
                    end_date=req_data.end_date
                )
            else:
                external_df = await data_integrator_instance.fetch_all_data(
                    start_date=req_data.start_date,
                    end_date=req_data.end_date
                )
        except Exception as e:
            print(f"Warning: Failed to fetch external data: {e}")
            external_df = None
    merge_col = req_data.merge_on if req_data.merge_on else 'date'
    if df is not None and external_df is not None and not external_df.empty:
        if merge_col in external_df.columns and merge_col in df.columns:
            numeric_cols = external_df.select_dtypes(include=['number']).columns
            external_agg = external_df.groupby(merge_col)[numeric_cols].sum().reset_index()
            if merge_col == 'date':
                df[merge_col] = pd.to_datetime(df[merge_col])
                external_agg[merge_col] = pd.to_datetime(external_agg[merge_col])
            df = df.merge(external_agg, on=merge_col, how='left', suffixes=('', '_external'))
            external_cols = [col for col in df.columns if col.endswith('_external') or col in numeric_cols]
            df[external_cols] = df[external_cols].fillna(0)
    elif df is None and external_df is not None and not external_df.empty:
        df = external_df.copy()
    elif df is None:
        raise HTTPException(status_code=400, detail="No data provided (CSV or external data required)")
    cluster_df = df.drop(columns=[req_data.target], errors='ignore').select_dtypes(include=[np.number]).fillna(0)
    n_clusters = min(5, len(cluster_df)) if len(cluster_df) > 1 else 1
    clusters = KMeans(n_clusters=n_clusters, random_state=42).fit_predict(cluster_df) if n_clusters > 1 else np.zeros(len(cluster_df), dtype=int)
    predictions = None
    shap_summary = None
    if req_data.target and req_data.target in df.columns:
        predictor_path = os.path.join(model_dir, req_data.id)
        predictor = TabularPredictor(label=req_data.target, path=predictor_path).fit(df)
        predictions = predictor.predict(df)
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
    return {
        "predictions": predictions.tolist() if predictions is not None else None,
        "shap_summary": shap_summary,
        "data_shape": df.shape,
        "external_data_used": req_data.use_external_data and external_df is not None and not external_df.empty if req_data.use_external_data else False,
        "feature_columns": df.drop(columns=[req_data.target], errors='ignore').columns.tolist(),
        "clusters": clusters.tolist(),
        "n_clusters": int(n_clusters)
    }

@router.post("/fetch-external-data")
async def fetch_external_data(
    start_date: str = Form(...),
    end_date: str = Form(...),
    data_sources: str = Form(None)
):
    try:
        sources_list = json.loads(data_sources) if data_sources else None
        if sources_list:
            df = await data_integrator_instance.fetch_specific_data(
                connector_names=sources_list,
                start_date=start_date,
                end_date=end_date
            )
        else:
            df = await data_integrator_instance.fetch_all_data(
                start_date=start_date,
                end_date=end_date
            )
        if df.empty:
            return {"message": "No data found", "data": []}
        return {
            "message": "Data fetched successfully",
            "data_shape": df.shape,
            "columns": df.columns.tolist(),
            "data": df.to_dict('records')[:100],
            "total_rows": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching external data: {str(e)}")

@router.post("/predict-with-user-data")
async def predict_with_user_data(
    file: UploadFile = File(None),
    request: str = Form(...)
):
    """Predict using a user's stored credentials for external data"""
    req_data = PredictWithUserDataRequest(**json.loads(request))
    
    # Load user's credentials if not already loaded
    credential_manager.load_user_connectors(req_data.user_id)
    
    df = pd.read_csv(file.file) if file is not None else None
    if df is not None and req_data.target and req_data.target not in df.columns:
        raise HTTPException(status_code=400, detail="Target column not in data")
    
    external_df = None
    if req_data.use_external_data and req_data.start_date and req_data.end_date:
        try:
            if req_data.data_sources:
                external_df = await data_integrator_instance.fetch_specific_data(
                    connector_names=req_data.data_sources,
                    start_date=req_data.start_date,
                    end_date=req_data.end_date
                )
            else:
                external_df = await data_integrator_instance.fetch_all_data(
                    start_date=req_data.start_date,
                    end_date=req_data.end_date
                )
        except Exception as e:
            print(f"Warning: Failed to fetch external data: {e}")
            external_df = None
    
    merge_col = req_data.merge_on if req_data.merge_on else 'date'
    if df is not None and external_df is not None and not external_df.empty:
        if merge_col in external_df.columns and merge_col in df.columns:
            numeric_cols = external_df.select_dtypes(include=['number']).columns
            external_agg = external_df.groupby(merge_col)[numeric_cols].sum().reset_index()
            if merge_col == 'date':
                df[merge_col] = pd.to_datetime(df[merge_col])
                external_agg[merge_col] = pd.to_datetime(external_agg[merge_col])
            df = df.merge(external_agg, on=merge_col, how='left', suffixes=('', '_external'))
            external_cols = [col for col in df.columns if col.endswith('_external') or col in numeric_cols]
            df[external_cols] = df[external_cols].fillna(0)
    elif df is None and external_df is not None and not external_df.empty:
        df = external_df.copy()
    elif df is None:
        raise HTTPException(status_code=400, detail="No data provided (CSV or external data required)")
    
    cluster_df = df.drop(columns=[req_data.target], errors='ignore').select_dtypes(include=[np.number]).fillna(0)
    n_clusters = min(5, len(cluster_df)) if len(cluster_df) > 1 else 1
    clusters = KMeans(n_clusters=n_clusters, random_state=42).fit_predict(cluster_df) if n_clusters > 1 else np.zeros(len(cluster_df), dtype=int)
    
    predictions = None
    shap_summary = None
    if req_data.target and req_data.target in df.columns:
        predictor_path = os.path.join(model_dir, req_data.id)
        predictor = TabularPredictor(label=req_data.target, path=predictor_path).fit(df)
        predictions = predictor.predict(df)
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
    
    return {
        "user_id": req_data.user_id,
        "predictions": predictions.tolist() if predictions is not None else None,
        "shap_summary": shap_summary,
        "data_shape": df.shape,
        "external_data_used": req_data.use_external_data and external_df is not None and not external_df.empty if req_data.use_external_data else False,
        "feature_columns": df.drop(columns=[req_data.target], errors='ignore').columns.tolist(),
        "clusters": clusters.tolist(),
        "n_clusters": int(n_clusters),
        "available_connectors": data_integrator_instance.get_available_connectors()
    }
