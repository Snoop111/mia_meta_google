"""
Creative Analysis Models and Schemas

Contains all data models, request/response schemas, and constants
for the creative analysis system.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class CreativeAnalysisRequest(BaseModel):
    """Request model for creative analysis endpoint"""
    question: str  # One of the 12 preset questions
    category: str  # "grow", "optimise", or "protect"
    session_id: Optional[str] = "default"
    start_date: str = "2025-08-03"  # Default: Aug 3 - Sep 2 for grow/optimize, Aug 3-9 for protect
    end_date: str = "2025-09-02"    # Default: Calculated based on category

class CreativeAnalysisResponse(BaseModel):
    """Response model for creative analysis"""
    success: bool
    analysis: str
    source: str = "creative-analysis"
    error: Optional[str] = None

class AccountContext(BaseModel):
    """Account context information"""
    user_id: str
    account_id: str
    account_name: str
    google_ads_id: str
    ga4_property_id: str
    business_type: str
    focus_account: str

# 12 Preset Creative Questions (from docs/Mia creative pivot.txt)
PRESET_QUESTIONS = {
    "grow": [
        "Which creative format is driving the most engagement?",
        "Which captions or headlines resonate best with my audience?",
        "Which visual styles or themes perform best?",
        "Which messaging angle appeals most to our audience?"
    ],
    "optimise": [
        "Which creative gives me the most clicks for the lowest spend?",
        "How should I optimise creative to increase engagement?",
        "Which headlines or CTAs perform best?",
        "Which advert delivered the highest click-through rate (CTR)?"
    ],
    "protect": [
        "Is creative fatigue affecting my ads?",
        "Which creative assets are showing declining performance trends?",
        "Which ads are starting to lose engagement over time?",
        "Are my audiences seeing the same creative too often?"
    ]
}

# Google Ads Asset Type Mappings
GOOGLE_ADS_ASSET_TYPES = {
    "HEADLINE": "Headlines",
    "DESCRIPTION": "Descriptions",
    "LONG_HEADLINE": "Long Headlines",
    "CALLOUT": "Callouts",
    "SITELINK": "Sitelinks",
    "IMAGE": "Images",
    "LOGO": "Logo Images",
    "SQUARE_MARKETING_IMAGE": "Square Images",
    "MARKETING_IMAGE": "Marketing Images"
}

# Question category mappings for date range calculation
CATEGORY_DATE_RANGES = {
    "grow": {"default_days": 30, "description": "Growth analysis"},
    "optimise": {"default_days": 30, "description": "Optimization analysis"},
    "protect": {"default_days": 7, "description": "Protection analysis"}
}