"""
Data Standardization Module
Handles column mapping and data cleaning for different sources
"""

import pandas as pd
from typing import Dict, List
import logging
import re

logger = logging.getLogger(__name__)

class DataStandardizer:
    """Standardizes data from different marketing platforms"""
    
    @staticmethod
    def standardize_ga4_data(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Google Analytics 4 data"""
        logger.info(f"GA4 CSV columns: {list(df.columns)}")
        
        mappings = {
            'sessions': 'sessions',
            'users': 'users',
            'newUsers': 'new_users',
            'pageviews': 'pageviews',
            'conversions': 'conversions',
            'sessionDefaultChannelGrouping': 'channel',
            'date': 'date',
            # Additional common GA4 column variations
            'Sessions': 'sessions',
            'Users': 'users',
            'Active users': 'users',  # Your GA4 export uses this
            'New users': 'new_users',
            'Pageviews': 'pageviews',
            'Page views': 'pageviews',
            'Conversions': 'conversions',
            'Date': 'date',
            'Nth day': 'date',  # Your GA4 export uses this
            'Channel': 'channel',
            'Source': 'source_medium',
            'Medium': 'medium'
        }
        
        standardized = DataStandardizer._apply_column_mappings(df, mappings)
        standardized['source'] = 'ga4'
        
        logger.info(f"GA4 after mapping: found {len(standardized.columns)} columns")
        
        return DataStandardizer._ensure_numeric_columns(
            standardized, 
            ['sessions', 'users', 'pageviews', 'conversions']
        )
    
    @staticmethod
    def standardize_meta_data(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Meta Ads data"""
        logger.info(f"Meta CSV columns: {list(df.columns)}")
        logger.info(f"Meta sample data: {df.head(2).to_dict()}")
        
        mappings = {
            'Campaign name': 'campaign_name',
            'Campaign': 'campaign_name',
            'Ad Set Name': 'adset_name',
            'Ad group': 'adset_name',  # Your Meta export uses this
            'Adset name': 'adset_name', 
            'Ad set name': 'adset_name',
            'Ad name': 'ad_name',
            'Day': 'date',
            'Date': 'date',
            'Reporting starts': 'date',
            'Impressions': 'impressions',
            'Impr.': 'impressions',  # Your Meta export uses this
            'Amount spent': 'spend',
            'Amount spent (ZAR)': 'spend',
            'Amount spent (USD)': 'spend',
            'Spend': 'spend',
            'Cost': 'spend',  # Your Meta export uses this
            'Results': 'conversions',
            'Conversions': 'conversions',  # Your Meta export uses this
            'Link clicks': 'clicks',
            'Clicks': 'clicks',
            'Interactions': 'clicks',  # Your Meta export uses this
            'Reach': 'reach'
        }
        
        standardized = DataStandardizer._apply_column_mappings(df, mappings)
        standardized['source'] = 'meta'
        
        logger.info(f"Meta after mapping: {list(standardized.columns)}")
        logger.info(f"Meta spend column exists: {'spend' in standardized.columns}")
        if 'spend' in standardized.columns:
            logger.info(f"Meta spend values: {standardized['spend'].head()}")
        if 'Cost' in standardized.columns:
            logger.info(f"Meta Cost values: {standardized['Cost'].head()}")
            
        result = DataStandardizer._ensure_numeric_columns(
            standardized,
            ['impressions', 'spend', 'conversions', 'clicks']
        )
        
        logger.info(f"Meta final totals - spend: {result['spend'].sum()}, conversions: {result['conversions'].sum()}, clicks: {result['clicks'].sum()}")
        return result
    
    @staticmethod
    def standardize_google_ads_data(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Google Ads data"""
        mappings = {
            'Campaign': 'campaign_name',
            'Ad group': 'adset_name', 
            'Impr.': 'impressions',
            'Clicks': 'clicks',
            'Cost': 'spend',
            'Conversions': 'conversions',
            # Handle variations in Google Ads exports
            'Impressions': 'impressions',
            'Ad name': 'ad_name'
        }
        
        standardized = DataStandardizer._apply_column_mappings(df, mappings)
        standardized['source'] = 'google_ads'
        
        return DataStandardizer._ensure_numeric_columns(
            standardized,
            ['impressions', 'clicks', 'spend', 'conversions']
        )
    
    @staticmethod
    def _apply_column_mappings(df: pd.DataFrame, mappings: Dict[str, str]) -> pd.DataFrame:
        """Apply column name mappings"""
        existing_mappings = {k: v for k, v in mappings.items() if k in df.columns}
        return df.rename(columns=existing_mappings)
    
    @staticmethod
    def _ensure_numeric_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Ensure specified columns are numeric, filling missing with 0"""
        result = df.copy()
        
        for col in columns:
            if col not in result.columns:
                result[col] = 0
            else:
                # Clean up common formatting issues
                if result[col].dtype == 'object':
                    # Remove commas, currency symbols, percentage signs, quotes, and extra spaces
                    result[col] = result[col].astype(str)
                    result[col] = result[col].str.replace(',', '', regex=False)
                    result[col] = result[col].str.replace('ZAR', '', regex=False)
                    result[col] = result[col].str.replace('$', '', regex=False)
                    result[col] = result[col].str.replace('%', '', regex=False)
                    result[col] = result[col].str.replace('"', '', regex=False)
                    result[col] = result[col].str.strip()
                    result[col] = result[col].str.replace('--', '0', regex=False)
                    result[col] = result[col].str.replace('< 0.01', '0', regex=False)
                    
                result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0)
        
        return result
    
    @staticmethod
    def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all required columns exist with proper types"""
        result = df.copy()
        
        # Required string columns
        string_columns = ['campaign_name', 'adset_name', 'ad_name', 'source']
        for col in string_columns:
            if col not in result.columns:
                result[col] = 'Unknown'
            else:
                result[col] = result[col].fillna('Unknown').astype(str)
        
        # Required numeric columns
        numeric_columns = ['impressions', 'clicks', 'spend', 'conversions', 'sessions', 'users', 'pageviews', 'ctr', 'cpc', 'cpm']
        for col in numeric_columns:
            if col not in result.columns:
                result[col] = 0.0
            else:
                result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0.0)
        
        return result