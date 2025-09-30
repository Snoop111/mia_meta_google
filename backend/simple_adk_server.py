#!/usr/bin/env python3
"""
MIA Marketing Intelligence Agent - Modular Server (Fixed)

Refactored from monolithic structure for better maintainability.
Now uses modular endpoints to prevent file corruption during edits.
FIXED: Removed duplicate OAuth endpoints to prevent session conflicts.
"""

from fastapi import FastAPI, Depends, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
import tempfile
import os

# Add backend to path
sys.path.append('')

# Import all models FIRST to register them with Base
from models.chat import ChatHistory, UserSession
from models.session import ChatSession
from models.creative import AdCreative, CreativeInsight

# Then import other modules
from services.adk_mcp_integration import get_adk_marketing_agent, reset_adk_marketing_agent
from database import get_db, init_db
from services.creative_import import CreativeDataImporter, get_creative_insights, get_ad_creative_summary

# Import modular endpoints
from endpoints import (
    auth_router,
    meta_auth_router,
    chat_router,
    creative_router,
    growth_router,
    optimize_router,
    protect_router,
    static_router
)

# Import refactored creative module
from services.creative import creative_router as creative_router_v2

def extract_account_info_from_request(request) -> Dict[str, Any]:
    """DEPRECATED: This function is no longer needed - use session service instead"""

    print(f"[ACCOUNT-EXTRACT] WARNING: This function is deprecated. Use session service for account management.")

    # Return empty result to indicate this function should not be used
    return {
        "user_id": None,
        "account_id": None,
        "property_id": None,
        "has_selection": False,
        "deprecated": True
    }

# Create FastAPI app
app = FastAPI(title="MIA Marketing Intelligence Agent - Modular Server")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular routers - AUTHENTICATION IS HANDLED BY auth_router AND meta_auth_router
app.include_router(auth_router, tags=["auth"])
app.include_router(meta_auth_router, tags=["meta-auth"])
app.include_router(chat_router, tags=["chat"])
app.include_router(creative_router, tags=["creative"])
app.include_router(creative_router_v2, tags=["creative-v2"])  # Refactored creative module
app.include_router(growth_router, tags=["growth"])
app.include_router(optimize_router, tags=["optimize"])
app.include_router(protect_router, tags=["protect"])
app.include_router(static_router, tags=["static"])

# Global agent instance for proper cleanup
_global_agent = None

# Test endpoint for account mappings
@app.get("/api/test/accounts")
async def test_account_mappings(db: Session = Depends(get_db)):
    """Test endpoint to verify account mappings work"""
    try:
        from models.user_profile import AccountMapping
        accounts = db.query(AccountMapping).filter(
            AccountMapping.is_active == True
        ).order_by(AccountMapping.sort_order).all()

        return {
            "success": True,
            "count": len(accounts),
            "accounts": [
                {
                    "id": acc.account_id,
                    "name": acc.account_name,
                    "google_ads_id": acc.google_ads_id,
                    "ga4_property_id": acc.ga4_property_id
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on server shutdown"""
    global _global_agent
    if _global_agent:
        try:
            await _global_agent.close()
            print("ADK agent closed successfully")
        except Exception as e:
            print(f"Error closing ADK agent: {e}")
    print("Server shutdown complete")

# Ensure models are imported before creating tables
print("Initializing database tables...")
try:
    init_db()
    print("Database tables created successfully!")
except Exception as e:
    print(f"Error creating database tables: {e}")

# ===== UTILITY ENDPOINTS =====

@app.post("/api/accounts/initialize-meta")
async def init_meta_accounts_endpoint(db: Session = Depends(get_db)):
    """Endpoint to initialize Meta accounts"""
    result = await initialize_meta_account_mappings(db)
    return result

@app.post("/api/accounts/initialize")
async def initialize_account_mappings(db: Session = Depends(get_db)):
    """Initialize account mappings with all three test accounts"""
    try:
        from models.user_profile import AccountMapping

        # Clear existing mappings first
        db.query(AccountMapping).delete()

        # Create all three test accounts using environment variables
        accounts = [
            AccountMapping(
                account_id="dfsa",
                account_name="DFSA - Goodness to Go",
                google_ads_id=os.getenv("DEV_DFSA_GOOGLE_ADS_ID", "7574136388"),
                ga4_property_id=os.getenv("DEV_DFSA_GA4_PROPERTY_ID", "458016659"),
                business_type="food",
                is_active=True,
                sort_order=1,
                account_color="#4F46E5"
            ),
            AccountMapping(
                account_id="cherry_time",
                account_name="Cherry Time - Fresh Fruit",
                google_ads_id=os.getenv("DEV_CHERRY_TIME_GOOGLE_ADS_ID", "8705861821"),
                ga4_property_id=os.getenv("DEV_CHERRY_TIME_GA4_PROPERTY_ID", "292652926"),
                business_type="food",
                is_active=True,
                sort_order=2,
                account_color="#DC2626"
            ),
            AccountMapping(
                account_id="onvlee",
                account_name="Onvlee Engineering - Cable Trays",
                google_ads_id=os.getenv("DEV_ONVLEE_GOOGLE_ADS_ID", "7482456286"),
                ga4_property_id=os.getenv("DEV_ONVLEE_GA4_PROPERTY_ID", "428236885"),
                business_type="engineering",
                is_active=True,
                sort_order=3,
                account_color="#059669"
            )
        ]

        for account in accounts:
            db.add(account)

        db.commit()

        return {
            "success": True,
            "message": "Account mappings initialized successfully",
            "accounts_created": len(accounts),
            "accounts": [
                {
                    "id": acc.account_id,
                    "name": acc.account_name,
                    "google_ads_id": acc.google_ads_id,
                    "ga4_property_id": acc.ga4_property_id,
                    "business_type": acc.business_type
                }
                for acc in accounts
            ]
        }

    except Exception as e:
        print(f"[ACCOUNT-INIT] Error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/accounts/initialize-meta")
async def init_meta_accounts_endpoint(db: Session = Depends(get_db)):
    """Endpoint to initialize Meta accounts"""
    return await initialize_meta_account_mappings(db)

async def initialize_meta_account_mappings(db: Session):
    """Initialize Meta account mappings based on discovered Meta ad accounts"""
    try:
        from models.user_profile import AccountMapping

        # Meta accounts discovered from API
        meta_accounts = [
            {
                "id": "onvlee_meta",
                "name": "Onvlee (Meta Ads)",
                "meta_ads_id": "401656817167702",
                "business_type": "engineering",
                "color": "#059669"
            },
            {
                "id": "dfsa_meta",
                "name": "DFSA (Meta Ads)",
                "meta_ads_id": "630183442304468",  # TESTING: 11&1 Agency account
                "business_type": "food",
                "color": "#4F46E5"
            },
            {
                "id": "dutoit_meta",
                "name": "Dutoit (Meta Ads)",
                "meta_ads_id": "149638046968103",
                "business_type": "food",
                "color": "#DC2626"
            },
            {
                "id": "yourbud_meta",
                "name": "YourBud (Meta Ads)",
                "meta_ads_id": "773316628325458",
                "business_type": "retail",
                "color": "#10B981"
            },
            {
                "id": "agency_meta",
                "name": "11&1 Agency (Meta Ads)",
                "meta_ads_id": "630183442304468",
                "business_type": "agency",
                "color": "#8B5CF6"
            }
        ]

        created_accounts = []
        for meta_account in meta_accounts:
            # Check if account already exists
            existing = db.query(AccountMapping).filter(
                AccountMapping.account_id == meta_account["id"]
            ).first()

            if not existing:
                account_mapping = AccountMapping(
                    account_id=meta_account["id"],
                    account_name=meta_account["name"],
                    meta_ads_id=meta_account["meta_ads_id"],
                    business_type=meta_account["business_type"],
                    is_active=True,
                    sort_order=len(created_accounts) + 100,  # Start after Google accounts
                    account_color=meta_account["color"]
                )
                db.add(account_mapping)
                created_accounts.append(meta_account)

        db.commit()

        return {
            "success": True,
            "message": f"Meta account mappings initialized: {len(created_accounts)} accounts",
            "accounts_created": created_accounts,
            "total_meta_accounts_available": 7
        }

    except Exception as e:
        print(f"[META-ACCOUNT-INIT] Error: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

@app.post("/api/mcp/reset-agent")
async def reset_mcp_agent():
    """Manually reset MCP agent to clear cached sessions (for debugging)"""
    try:
        await reset_adk_marketing_agent()
        return {"success": True, "message": "MCP agent reset successfully"}
    except Exception as e:
        print(f"[MCP-RESET] Error resetting agent: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/accounts/status")
async def get_account_status(db: Session = Depends(get_db)):
    """Get status of all account mappings"""
    try:
        from models.user_profile import AccountMapping
        accounts = db.query(AccountMapping).filter(AccountMapping.is_active == True).order_by(AccountMapping.sort_order).all()

        return {
            "success": True,
            "total_accounts": len(accounts),
            "accounts": [
                {
                    "id": acc.account_id,
                    "name": acc.account_name,
                    "google_ads_id": acc.google_ads_id,
                    "ga4_property_id": acc.ga4_property_id,
                    "business_type": acc.business_type,
                    "color": acc.account_color,
                    "sort_order": acc.sort_order
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test-sessions/create")
async def create_test_sessions(db: Session = Depends(get_db)):
    """Create test sessions for all accounts (for testing multi-account functionality)"""
    try:
        from services.test_session_helper import create_test_session

        # Create individual test sessions
        test_sessions = [
            ("test_dfsa", "dfsa"),
            ("test_cherry_time", "cherry_time"),
            ("test_onvlee", "onvlee")
        ]

        results = []
        for session_id, account_id in test_sessions:
            success = create_test_session(session_id, account_id, db)
            results.append({
                "session_id": session_id,
                "account_id": account_id,
                "success": success
            })

        successful_sessions = sum(1 for r in results if r["success"])

        return {
            "success": True,
            "message": f"Created {successful_sessions}/{len(results)} test sessions",
            "results": results
        }

    except Exception as e:
        print(f"[TEST-SESSIONS] Error: {e}")
        return {"success": False, "error": str(e)}

# ===== CREATIVE DATA ENDPOINTS (keeping in main for now) =====

class CreativeImportRequest(BaseModel):
    csv_data: str  # CSV content as string
    account_id: str  # Required account ID from session

@app.post("/api/creative/import-csv")
async def import_creative_csv(request: CreativeImportRequest, db: Session = Depends(get_db)):
    """Import creative data from CSV string"""
    try:
        importer = CreativeDataImporter(db, request.account_id)
        result = await importer.import_from_csv_string(request.csv_data)
        return result
    except Exception as e:
        print(f"[CREATIVE-CSV] Error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/creative/import-file")
async def import_creative_file(file: UploadFile = File(...), account_id: str = "dfsa", db: Session = Depends(get_db)):
    """Import creative data from uploaded file"""
    try:
        if not file.filename.endswith('.csv'):
            return {"success": False, "error": "Only CSV files are supported"}

        # Read file content
        content = await file.read()
        csv_data = content.decode('utf-8')

        importer = CreativeDataImporter(db, account_id)
        result = await importer.import_from_csv_string(csv_data)

        return result
    except Exception as e:
        print(f"[CREATIVE-FILE] Error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/creative/summary")
async def get_creative_summary(account_id: str = "dfsa", db: Session = Depends(get_db)):
    """Get summary of creative data for account"""
    try:
        summary = get_ad_creative_summary(db, account_id)
        return {"success": True, "summary": summary}
    except Exception as e:
        print(f"[CREATIVE-SUMMARY] Error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for DigitalOcean App Platform
    port = int(os.environ.get("PORT", 8002))
    # Listen on all interfaces for DigitalOcean deployment
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)