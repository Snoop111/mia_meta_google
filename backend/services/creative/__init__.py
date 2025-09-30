"""
Creative Analysis Module

Refactored creative analysis system with improved modularity and maintainability.

This module provides:
- Creative asset analysis using MCP integration
- Account context management
- Modular query building and data processing
- Clean API endpoints

Usage:
    from backend.services.creative import creative_router
    app.include_router(creative_router, prefix="/creative")
"""

from .routes import router as creative_router
from .models import (
    CreativeAnalysisRequest,
    CreativeAnalysisResponse,
    PRESET_QUESTIONS,
    GOOGLE_ADS_ASSET_TYPES
)
from .analysis import analyze_creative_question
from .account_context import get_account_context

__all__ = [
    "creative_router",
    "CreativeAnalysisRequest",
    "CreativeAnalysisResponse",
    "PRESET_QUESTIONS",
    "GOOGLE_ADS_ASSET_TYPES",
    "analyze_creative_question",
    "get_account_context"
]