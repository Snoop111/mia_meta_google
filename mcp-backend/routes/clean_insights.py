"""
Clean Insights API Routes
Simplified API endpoints for data consolidation
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import logging

from clean_consolidator import CleanDataConsolidator
from data_loader import DataLoader

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/clean-insights")
async def clean_insights(
    ga4_file: Optional[UploadFile] = File(None),
    meta_file: Optional[UploadFile] = File(None),
    google_file: Optional[UploadFile] = File(None)
):
    """Upload CSV files and get consolidated insights"""
    
    if not any([ga4_file, meta_file, google_file]):
        raise HTTPException(
            status_code=400,
            detail="Upload at least one CSV file (GA4, Meta, or Google Ads)"
        )
    
    try:
        consolidator = CleanDataConsolidator()
        files_processed = _process_uploaded_files(consolidator, ga4_file, meta_file, google_file)
        
        if not files_processed or not any(files_processed.values()):
            raise HTTPException(
                status_code=400,
                detail="No files could be processed successfully"
            )
        
        insights = consolidator.generate_insights()
        
        return {
            "success": True,
            "files_processed": files_processed,
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"Error processing insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clean-insights/example")
async def insights_example():
    """Get usage examples for the clean insights endpoint"""
    return {
        "description": "Clean Data Consolidation API",
        "endpoint": "/clean-insights",
        "method": "POST",
        "parameters": {
            "ga4_file": "GA4 CSV export (optional)",
            "meta_file": "Meta Ads CSV export (optional)",
            "google_file": "Google Ads CSV export (optional)"
        },
        "example_curl": """
curl -X POST "http://localhost:8000/clean-insights" \\
  -F "ga4_file=@analytics.csv" \\
  -F "meta_file=@meta_ads.csv" \\
  -F "google_file=@google_ads.csv"
        """.strip(),
        "response_includes": [
            "Summary statistics (spend, conversions, ROAS)",
            "Platform performance comparison",
            "Top performing campaigns",
            "Actionable recommendations"
        ]
    }

def _process_uploaded_files(
    consolidator: CleanDataConsolidator,
    ga4_file: Optional[UploadFile],
    meta_file: Optional[UploadFile],
    google_file: Optional[UploadFile]
) -> dict:
    """Process uploaded files and return which ones were successful"""
    
    files_processed = {}
    
    if ga4_file:
        df = _read_uploaded_file(ga4_file)
        if df is not None and consolidator.add_ga4_data(df):
            files_processed['ga4'] = True
        else:
            files_processed['ga4'] = False
    
    if meta_file:
        df = _read_uploaded_file(meta_file)
        if df is not None and consolidator.add_meta_data(df):
            files_processed['meta'] = True
        else:
            files_processed['meta'] = False
    
    if google_file:
        df = _read_uploaded_file(google_file)
        if df is not None and consolidator.add_google_ads_data(df):
            files_processed['google'] = True
        else:
            files_processed['google'] = False
    
    return files_processed

def _read_uploaded_file(file: UploadFile):
    """Read uploaded file using DataLoader"""
    try:
        content = file.file.read()
        return DataLoader.load_csv_from_bytes(content, file.filename)
    except Exception as e:
        logger.error(f"Error reading uploaded file {file.filename}: {e}")
        return None