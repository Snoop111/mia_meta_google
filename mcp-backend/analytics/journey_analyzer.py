"""
User Journey Analysis Module
Analyzes user journey from ads to conversions
"""

import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class JourneyAnalyzer:
    """Analyzes user journey and conversion funnel"""
    
    def __init__(self, ga4_data: pd.DataFrame, ad_data: pd.DataFrame):
        self.ga4_data = ga4_data
        self.ad_data = ad_data
    
    def analyze_funnel(self) -> Dict[str, Any]:
        """Analyze the complete conversion funnel"""
        if (hasattr(self.ga4_data, 'empty') and self.ga4_data.empty) and (hasattr(self.ad_data, 'empty') and self.ad_data.empty):
            return {"error": "No data available"}
        
        funnel_metrics = self._calculate_funnel_metrics()
        conversion_rates = self._calculate_conversion_rates(funnel_metrics)
        drop_offs = self._identify_drop_offs(funnel_metrics)
        source_performance = self._analyze_traffic_sources()
        
        return {
            "funnel_overview": funnel_metrics,
            "conversion_rates": conversion_rates,
            "drop_off_analysis": drop_offs,
            "traffic_source_performance": source_performance,
            "biggest_drop_off_stage": self._find_biggest_drop_off(drop_offs)
        }
    
    def _calculate_funnel_metrics(self) -> Dict[str, int]:
        """Calculate key funnel metrics"""
        return {
            'ad_clicks': int(self.ad_data['clicks'].sum()) if hasattr(self.ad_data, 'empty') and not self.ad_data.empty else 0,
            'website_sessions': int(self.ga4_data['sessions'].sum()) if hasattr(self.ga4_data, 'empty') and not self.ga4_data.empty else 0,
            'engaged_sessions': self._calculate_engaged_sessions(),
            'conversions': self._calculate_total_conversions()
        }
    
    def _calculate_engaged_sessions(self) -> int:
        """Calculate engaged sessions from GA4 data"""
        if (hasattr(self.ga4_data, 'empty') and self.ga4_data.empty) or 'engagementRate' not in self.ga4_data.columns:
            return 0
        
        engaged = self.ga4_data[self.ga4_data['engagementRate'] > 0]['sessions'].sum()
        return int(engaged)
    
    def _calculate_total_conversions(self) -> int:
        """Calculate total conversions from all sources"""
        total = 0
        
        if hasattr(self.ga4_data, 'empty') and not self.ga4_data.empty and 'conversions' in self.ga4_data.columns:
            total += self.ga4_data['conversions'].sum()
        
        if hasattr(self.ad_data, 'empty') and not self.ad_data.empty and 'conversions' in self.ad_data.columns:
            total += self.ad_data['conversions'].sum()
        
        return int(total)
    
    def _calculate_conversion_rates(self, funnel_metrics: Dict[str, int]) -> Dict[str, float]:
        """Calculate conversion rates between funnel stages"""
        rates = {}
        
        if funnel_metrics['ad_clicks'] > 0:
            rates['click_to_session'] = round(
                (funnel_metrics['website_sessions'] / funnel_metrics['ad_clicks']) * 100, 2
            )
        
        if funnel_metrics['website_sessions'] > 0:
            rates['session_to_engagement'] = round(
                (funnel_metrics['engaged_sessions'] / funnel_metrics['website_sessions']) * 100, 2
            )
            rates['session_to_conversion'] = round(
                (funnel_metrics['conversions'] / funnel_metrics['website_sessions']) * 100, 2
            )
        
        return rates
    
    def _identify_drop_offs(self, funnel_metrics: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """Identify drop-off points in the funnel"""
        drop_offs = {}
        
        # Ads to website drop-off
        if funnel_metrics['ad_clicks'] > 0 and funnel_metrics['website_sessions'] > 0:
            lost_users = funnel_metrics['ad_clicks'] - funnel_metrics['website_sessions']
            drop_offs['ads_to_website'] = {
                'lost_users': lost_users,
                'drop_off_rate': round((lost_users / funnel_metrics['ad_clicks']) * 100, 2),
                'potential_issue': 'Ad targeting mismatch or slow loading times'
            }
        
        # Website to engagement drop-off
        if funnel_metrics['website_sessions'] > 0 and funnel_metrics['engaged_sessions'] > 0:
            lost_users = funnel_metrics['website_sessions'] - funnel_metrics['engaged_sessions']
            drop_offs['website_to_engagement'] = {
                'lost_users': lost_users,
                'drop_off_rate': round((lost_users / funnel_metrics['website_sessions']) * 100, 2),
                'potential_issue': 'Poor landing page experience or irrelevant content'
            }
        
        return drop_offs
    
    def _analyze_traffic_sources(self) -> Dict[str, Any]:
        """Analyze performance by traffic source"""
        if (hasattr(self.ga4_data, 'empty') and self.ga4_data.empty) or 'sessionDefaultChannelGrouping' not in self.ga4_data.columns:
            return {}
        
        source_performance = self.ga4_data.groupby('sessionDefaultChannelGrouping').agg({
            'sessions': 'sum',
            'engagementRate': 'mean',
            'avgSessionDuration': 'mean',
            'conversions': 'sum' if 'conversions' in self.ga4_data.columns else lambda x: 0
        }).round(2)
        
        if hasattr(source_performance, 'empty') and not source_performance.empty:
            source_performance['conversion_rate'] = round(
                (source_performance['conversions'] / source_performance['sessions'] * 100), 2
            )
        
        return source_performance.to_dict('index')
    
    def _find_biggest_drop_off(self, drop_offs: Dict[str, Dict]) -> str:
        """Find the stage with the biggest drop-off rate"""
        if not drop_offs:
            return None
        
        biggest = max(drop_offs.items(), key=lambda x: x[1]['drop_off_rate'])
        return biggest[0]