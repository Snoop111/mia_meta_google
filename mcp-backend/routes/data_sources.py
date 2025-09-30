from fastapi import APIRouter, HTTPException

from models import ConfigureDataSourceRequest, LoadUserCredentialsRequest
from shared_integrator import data_integrator_instance
from credential_manager import credential_manager
import data_integrator

router = APIRouter()

@router.post("/configure-data-sources")
async def configure_data_sources(request: ConfigureDataSourceRequest):
    configured_sources = []
    failed_sources = []
    
    if request.credentials.meta_ads:
        success = credential_manager.save_and_configure_credentials(
            request.user_id, "meta_ads", request.credentials.meta_ads
        )
        if success:
            configured_sources.append("meta_ads")
        else:
            failed_sources.append("meta_ads")
    
    if request.credentials.google_ads:
        success = credential_manager.save_and_configure_credentials(
            request.user_id, "google_ads", request.credentials.google_ads
        )
        if success:
            configured_sources.append("google_ads")
        else:
            failed_sources.append("google_ads")
    
    if request.credentials.ga4:
        success = credential_manager.save_and_configure_credentials(
            request.user_id, "ga4", request.credentials.ga4
        )
        if success:
            configured_sources.append("ga4")
        else:
            failed_sources.append("ga4")
    
    return {
        "message": "Data sources processed",
        "user_id": request.user_id,
        "configured_sources": configured_sources,
        "failed_sources": failed_sources,
        "connector_status": data_integrator_instance.get_connector_status()
    }

@router.post("/load-user-credentials")
async def load_user_credentials(request: LoadUserCredentialsRequest):
    """Load all stored credentials for a user"""
    results = credential_manager.load_user_connectors(request.user_id)
    return {
        "message": "User credentials loaded",
        "user_id": request.user_id,
        "loaded_connectors": results,
        "connector_status": data_integrator_instance.get_connector_status()
    }

@router.get("/data-sources/status")
async def get_data_sources_status():
    return {
        "available_connectors": data_integrator_instance.get_available_connectors(),
        "connector_status": data_integrator_instance.get_connector_status()
    }

@router.get("/users/{user_id}/data-sources")
async def get_user_data_sources(user_id: str):
    """Get information about a user's configured data sources"""
    return credential_manager.get_user_data_sources(user_id)

@router.delete("/users/{user_id}/data-sources/{source_name}")
async def remove_user_data_source(user_id: str, source_name: str):
    """Remove a data source for a specific user"""
    try:
        success = credential_manager.remove_user_connector(user_id, source_name)
        if success:
            return {
                "message": f"Data source {source_name} removed successfully for user {user_id}",
                "remaining_connectors": data_integrator_instance.get_available_connectors()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Data source {source_name} not found for user {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing data source: {str(e)}")

@router.delete("/data-sources/{source_name}")
async def remove_data_source(source_name: str):
    try:
        data_integrator_instance.remove_connector(source_name)
        return {
            "message": f"Data source {source_name} removed successfully",
            "remaining_connectors": data_integrator_instance.get_available_connectors()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing data source: {str(e)}")
