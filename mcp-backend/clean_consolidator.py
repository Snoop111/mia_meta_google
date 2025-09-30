"""
Clean Data Consolidator - API Only
Main consolidation class for uploaded data
"""

import pandas as pd
from typing import Dict, Any
import logging

from data_standardizer import DataStandardizer
from insights_generator import InsightsGenerator

logger = logging.getLogger(__name__)

class CleanDataConsolidator:
    """Clean, modular data consolidator for API uploads"""
    
    def __init__(self):
        self.data = pd.DataFrame()
        self.standardizer = DataStandardizer()
    
    def add_ga4_data(self, df: pd.DataFrame) -> bool:
        """Add GA4 data from DataFrame"""
        if df is None or df.empty:
            return False
        
        standardized = self.standardizer.standardize_ga4_data(df)
        self._append_data(standardized)
        logger.info(f"Added {len(standardized)} GA4 records")
        return True
    
    def add_meta_data(self, df: pd.DataFrame) -> bool:
        """Add Meta Ads data from DataFrame"""
        if df is None or df.empty:
            return False
        
        standardized = self.standardizer.standardize_meta_data(df)
        self._append_data(standardized)
        logger.info(f"Added {len(standardized)} Meta records")
        return True
    
    def add_google_ads_data(self, df: pd.DataFrame) -> bool:
        """Add Google Ads data from DataFrame"""
        if df is None or df.empty:
            return False
        
        standardized = self.standardizer.standardize_google_ads_data(df)
        self._append_data(standardized)
        logger.info(f"Added {len(standardized)} Google Ads records")
        return True
    
    def generate_insights(self) -> Dict[str, Any]:
        """Generate all insights from consolidated data"""
        if self.data.empty:
            return {"error": "No data available"}
        
        insights_gen = InsightsGenerator(self.data)
        
        return {
            "summary": insights_gen.generate_summary(),
            "platform_performance": insights_gen.analyze_platform_performance(),
            "top_campaigns": insights_gen.get_top_campaigns(),
            "recommendations": insights_gen.generate_recommendations()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get quick summary"""
        if self.data.empty:
            return {"error": "No data available"}
        
        return InsightsGenerator(self.data).generate_summary()
    
    def get_data(self) -> pd.DataFrame:
        """Get copy of consolidated data"""
        return self.data.copy()
    
    def _append_data(self, df: pd.DataFrame) -> None:
        """Append standardized data to main dataset"""
        standardized = self.standardizer.ensure_required_columns(df)
        self.data = pd.concat([self.data, standardized], ignore_index=True)