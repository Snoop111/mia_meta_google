"""
Insights Generation Module
Generates actionable insights from consolidated marketing data
"""

import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class InsightsGenerator:
    """Generates insights from consolidated marketing data"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate high-level summary statistics"""
        if self.data.empty:
            return {"error": "No data available"}
        
        return {
            "total_records": len(self.data),
            "data_sources": self.data['source'].value_counts().to_dict(),
            "total_spend": float(self.data['spend'].sum()),
            "total_conversions": float(self.data['conversions'].sum()),
            "total_clicks": float(self.data['clicks'].sum()),
            "overall_roas": self._calculate_roas(
                self.data['conversions'].sum(), 
                self.data['spend'].sum()
            )
        }
    
    def analyze_platform_performance(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across different platforms"""
        if self.data.empty:
            return {"error": "No data available"}
        
        platform_stats = self.data.groupby('source').agg({
            'spend': 'sum',
            'conversions': 'sum',
            'clicks': 'sum',
            'impressions': 'sum'
        }).round(2)
        
        # Add calculated metrics
        platform_stats['roas'] = platform_stats.apply(
            lambda row: self._calculate_roas(row['conversions'], row['spend']), 
            axis=1
        )
        platform_stats['ctr'] = platform_stats.apply(
            lambda row: self._calculate_ctr(row['clicks'], row['impressions']),
            axis=1
        )
        platform_stats['conversion_rate'] = platform_stats.apply(
            lambda row: self._calculate_conversion_rate(row['conversions'], row['clicks']),
            axis=1
        )
        
        return platform_stats.to_dict('index')
    
    def get_top_campaigns(self, limit: int = 5) -> Dict[str, Any]:
        """Identify top performing campaigns"""
        campaigns_with_spend = self.data[self.data['spend'] > 50].copy()
        
        if campaigns_with_spend.empty:
            return {"message": "No campaigns with significant spend"}
        
        campaign_stats = campaigns_with_spend.groupby(['source', 'campaign_name']).agg({
            'spend': 'sum',
            'conversions': 'sum',
            'clicks': 'sum'
        }).round(2)
        
        campaign_stats['roas'] = campaign_stats.apply(
            lambda row: self._calculate_roas(row['conversions'], row['spend']),
            axis=1
        )
        
        top_campaigns = campaign_stats.nlargest(limit, 'roas')
        
        return {
            "top_campaigns": top_campaigns.to_dict('index'),
            "total_analyzed": len(campaign_stats)
        }
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Find poor performers
        poor_performers = self._find_poor_performers()
        if poor_performers:
            recommendations.append(poor_performers)
        
        # Find scaling opportunities
        scaling_opportunities = self._find_scaling_opportunities()
        if scaling_opportunities:
            recommendations.append(scaling_opportunities)
        
        # Platform recommendations
        platform_rec = self._analyze_platform_efficiency()
        if platform_rec:
            recommendations.append(platform_rec)
        
        return recommendations if recommendations else [{"message": "No specific recommendations"}]
    
    def _find_poor_performers(self) -> Dict[str, Any]:
        """Find campaigns that should be paused"""
        campaigns = self.data[self.data['spend'] > 100].copy()
        if campaigns.empty:
            return {}
        
        campaign_stats = campaigns.groupby(['source', 'campaign_name']).agg({
            'spend': 'sum',
            'conversions': 'sum'
        })
        
        poor_roas = campaign_stats[
            campaign_stats.apply(
                lambda row: self._calculate_roas(row['conversions'], row['spend']) < 0.5,
                axis=1
            )
        ]
        
        if poor_roas.empty:
            return {}
        
        return {
            "type": "pause_campaigns",
            "message": f"Consider pausing {len(poor_roas)} low-performing campaigns",
            "potential_savings": f"${poor_roas['spend'].sum():.2f}",
            "count": len(poor_roas)
        }
    
    def _find_scaling_opportunities(self) -> Dict[str, Any]:
        """Find high-performing campaigns to scale"""
        campaigns = self.data[self.data['spend'] > 50].copy()
        if campaigns.empty:
            return {}
        
        campaign_stats = campaigns.groupby(['source', 'campaign_name']).agg({
            'spend': 'sum',
            'conversions': 'sum'
        })
        
        high_performers = campaign_stats[
            campaign_stats.apply(
                lambda row: self._calculate_roas(row['conversions'], row['spend']) > 2.0,
                axis=1
            )
        ]
        
        if high_performers.empty:
            return {}
        
        return {
            "type": "scale_campaigns",
            "message": f"Consider scaling {len(high_performers)} high-performing campaigns",
            "count": len(high_performers)
        }
    
    def _analyze_platform_efficiency(self) -> Dict[str, Any]:
        """Analyze which platform is most efficient"""
        platform_stats = self.data.groupby('source').agg({
            'spend': 'sum',
            'conversions': 'sum'
        })
        
        if len(platform_stats) < 2:
            return {}
        
        platform_roas = platform_stats.apply(
            lambda row: self._calculate_roas(row['conversions'], row['spend']),
            axis=1
        )
        
        best_platform = platform_roas.idxmax()
        worst_platform = platform_roas.idxmin()
        
        if platform_roas[best_platform] > platform_roas[worst_platform] * 1.5:
            return {
                "type": "platform_shift",
                "message": f"Consider shifting budget from {worst_platform} to {best_platform}",
                "best_platform": best_platform,
                "best_roas": platform_roas[best_platform],
                "worst_platform": worst_platform,
                "worst_roas": platform_roas[worst_platform]
            }
        
        return {}
    
    @staticmethod
    def _calculate_roas(conversions: float, spend: float) -> float:
        """Calculate Return on Ad Spend"""
        if spend == 0:
            return 0.0
        return round(conversions / spend, 2)
    
    @staticmethod
    def _calculate_ctr(clicks: float, impressions: float) -> float:
        """Calculate Click-Through Rate"""
        if impressions == 0:
            return 0.0
        return round((clicks / impressions) * 100, 2)
    
    @staticmethod
    def _calculate_conversion_rate(conversions: float, clicks: float) -> float:
        """Calculate Conversion Rate"""
        if clicks == 0:
            return 0.0
        return round((conversions / clicks) * 100, 2)