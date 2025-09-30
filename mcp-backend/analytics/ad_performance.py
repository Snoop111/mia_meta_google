"""
Ad Performance Analysis Module
Analyzes advertising performance across platforms
"""

import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class AdPerformanceAnalyzer:
    """Analyzes advertising performance and generates insights"""
    
    def __init__(self, ad_data: pd.DataFrame):
        self.ad_data = ad_data.copy()
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with calculated metrics"""
        if self.ad_data.empty:
            return
        
        # Calculate performance metrics
        self.ad_data['roas'] = self.ad_data['conversions'] / (self.ad_data['spend'] + 0.001)
        self.ad_data['cost_per_conversion'] = self.ad_data['spend'] / (self.ad_data['conversions'] + 0.001)
        self.ad_data['conversion_rate'] = self.ad_data['conversions'] / (self.ad_data['clicks'] + 0.001)
        
        # Clean infinite and NaN values
        numeric_cols = ['roas', 'cost_per_conversion', 'conversion_rate']
        for col in numeric_cols:
            self.ad_data[col] = self.ad_data[col].replace([float('inf'), float('-inf')], 0).fillna(0)
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Comprehensive performance analysis"""
        if self.ad_data.empty:
            return {"error": "No ad data available"}
        
        return {
            "overall_metrics": self._calculate_overall_metrics(),
            "platform_comparison": self._compare_platforms(),
            "top_performers": self._find_top_performers(),
            "bottom_performers": self._find_bottom_performers(),
            "campaign_summary": self._summarize_campaigns()
        }
    
    def _calculate_overall_metrics(self) -> Dict[str, float]:
        """Calculate overall advertising metrics"""
        return {
            "total_spend": float(self.ad_data['spend'].sum()),
            "total_conversions": float(self.ad_data['conversions'].sum()),
            "total_clicks": float(self.ad_data['clicks'].sum()),
            "total_impressions": float(self.ad_data['impressions'].sum()),
            "average_ctr": float(self.ad_data['ctr'].mean()),
            "average_cpc": float(self.ad_data['cpc'].mean()),
            "overall_roas": float(self.ad_data['conversions'].sum() / (self.ad_data['spend'].sum() + 0.001))
        }
    
    def _compare_platforms(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across advertising platforms"""
        if 'source' not in self.ad_data.columns:
            return {}
        
        platform_stats = self.ad_data.groupby('source').agg({
            'spend': 'sum',
            'conversions': 'sum',
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'cpc': 'mean'
        }).round(4)
        
        # Calculate platform ROAS
        platform_stats['roas'] = (platform_stats['conversions'] / (platform_stats['spend'] + 0.001)).round(4)
        
        return platform_stats.to_dict('index')
    
    def _find_top_performers(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """Find top performing ads by various metrics"""
        top_performers = {}
        metrics = ['ctr', 'cpc', 'roas', 'conversion_rate']
        
        for metric in metrics:
            if metric in self.ad_data.columns:
                # Get top performers for this metric
                top_threshold = self.ad_data[metric].quantile(0.9)
                top_ads = self.ad_data[self.ad_data[metric] >= top_threshold]
                
                # Select relevant columns and convert to records
                base_columns = ['campaign_name', metric, 'spend', 'conversions']
                optional_columns = ['adset_name', 'ad_name', 'campaign_id', 'campaign_status']
                columns = base_columns + [col for col in optional_columns if col in top_ads.columns]
                available_columns = [col for col in columns if col in top_ads.columns]
                
                top_performers[metric] = top_ads[available_columns].head(limit).to_dict('records')
        
        return top_performers
    
    def _find_bottom_performers(self, limit: int = 10, min_spend: float = 50) -> Dict[str, List[Dict]]:
        """Find bottom performing ads (with minimum spend requirement)"""
        bottom_performers = {}
        metrics = ['ctr', 'roas', 'conversion_rate']
        
        # Filter to ads with significant spend
        significant_spend = self.ad_data[self.ad_data['spend'] >= min_spend]
        
        if significant_spend.empty:
            return bottom_performers
        
        for metric in metrics:
            if metric in significant_spend.columns:
                # Get bottom performers for this metric
                bottom_threshold = significant_spend[metric].quantile(0.1)
                bottom_ads = significant_spend[significant_spend[metric] <= bottom_threshold]
                
                # Select relevant columns and convert to records
                base_columns = ['campaign_name', metric, 'spend', 'conversions']
                optional_columns = ['adset_name', 'ad_name', 'campaign_id', 'campaign_status']
                columns = base_columns + [col for col in optional_columns if col in bottom_ads.columns]
                available_columns = [col for col in columns if col in bottom_ads.columns]
                
                bottom_performers[metric] = bottom_ads[available_columns].head(limit).to_dict('records')
        
        return bottom_performers
    
    def _summarize_campaigns(self) -> Dict[str, Dict[str, float]]:
        """Summarize performance by campaign"""
        if 'campaign_name' not in self.ad_data.columns:
            return {}
        
        campaign_summary = self.ad_data.groupby('campaign_name').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'spend': 'sum',
            'conversions': 'sum',
            'ctr': 'mean',
            'cpc': 'mean',
            'cpm': 'mean'
        }).round(4)
        
        # Calculate campaign-level ROAS and conversion rate
        campaign_summary['roas'] = (campaign_summary['conversions'] / (campaign_summary['spend'] + 0.001)).round(4)
        campaign_summary['conversion_rate'] = (campaign_summary['conversions'] / (campaign_summary['clicks'] + 0.001)).round(4)
        
        return campaign_summary.to_dict('index')

class CampaignComparator:
    """Compares campaign performance side by side"""
    
    def __init__(self, ad_data: pd.DataFrame):
        self.ad_data = ad_data
    
    def compare_campaigns(self, campaign_list: List[str] = None) -> Dict[str, Any]:
        """Compare specific campaigns or all campaigns"""
        if self.ad_data.empty or 'campaign_name' not in self.ad_data.columns:
            return {"error": "No campaign data available"}
        
        # Filter to specific campaigns if provided
        data = self.ad_data
        if campaign_list:
            data = data[data['campaign_name'].isin(campaign_list)]
        
        if data.empty:
            return {"error": "No matching campaigns found"}
        
        campaign_metrics = self._calculate_campaign_metrics(data)
        rankings = self._rank_campaigns(campaign_metrics)
        
        return {
            "campaign_comparison": campaign_metrics,
            "campaign_rankings": rankings,
            "total_campaigns": len(campaign_metrics)
        }
    
    def _calculate_campaign_metrics(self, data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate metrics for each campaign"""
        metrics = data.groupby('campaign_name').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'spend': 'sum',
            'conversions': 'sum',
            'ctr': 'mean',
            'cpc': 'mean',
            'cpm': 'mean'
        }).round(4)
        
        # Calculate additional metrics
        metrics['roas'] = (metrics['conversions'] / (metrics['spend'] + 0.001)).round(4)
        metrics['conversion_rate'] = (metrics['conversions'] / (metrics['clicks'] + 0.001)).round(4)
        metrics['cost_per_conversion'] = (metrics['spend'] / (metrics['conversions'] + 0.001)).round(4)
        
        return metrics.to_dict('index')
    
    def _rank_campaigns(self, campaign_metrics: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """Rank campaigns by different metrics"""
        if not campaign_metrics:
            return {}
        
        # Convert to DataFrame for easier ranking
        df = pd.DataFrame.from_dict(campaign_metrics, orient='index')
        
        rankings = {}
        metrics_to_rank = ['roas', 'ctr', 'conversion_rate', 'conversions']
        
        for metric in metrics_to_rank:
            if metric in df.columns:
                ranked = df.sort_values(metric, ascending=False)
                rankings[f"best_{metric}"] = ranked.index.tolist()[:5]  # Top 5
        
        return rankings