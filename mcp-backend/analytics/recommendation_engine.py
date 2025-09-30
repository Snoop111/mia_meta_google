"""
Recommendation Engine Module
Generates actionable recommendations for ad optimization
"""

import pandas as pd
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Generates actionable optimization recommendations"""
    
    def __init__(self, ad_data: pd.DataFrame, min_spend: float = 100):
        self.ad_data = ad_data.copy()
        self.min_spend = min_spend
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with calculated metrics"""
        if self.ad_data.empty:
            return
        
        self.ad_data['roas'] = self.ad_data['conversions'] / (self.ad_data['spend'] + 0.001)
        self.ad_data['conversion_rate'] = self.ad_data['conversions'] / (self.ad_data['clicks'] + 0.001)
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate all types of recommendations"""
        recommendations = []
        
        # Find campaigns to pause
        pause_rec = self._recommend_pausing()
        if pause_rec:
            recommendations.append(pause_rec)
        
        # Find campaigns to scale
        scale_rec = self._recommend_scaling()
        if scale_rec:
            recommendations.append(scale_rec)
        
        # Platform optimization
        platform_rec = self._recommend_platform_shifts()
        if platform_rec:
            recommendations.append(platform_rec)
        
        # Campaign restructuring
        restructure_rec = self._recommend_campaign_restructuring()
        if restructure_rec:
            recommendations.append(restructure_rec)
        
        return recommendations if recommendations else [{"message": "No specific recommendations"}]
    
    def _recommend_pausing(self) -> Dict[str, Any]:
        """Recommend campaigns to pause"""
        significant_spend = self.ad_data[self.ad_data['spend'] >= self.min_spend]
        
        if significant_spend.empty:
            return {}
        
        poor_performers = significant_spend[
            (significant_spend['ctr'] < significant_spend['ctr'].quantile(0.2)) &
            (significant_spend['roas'] < 1.0)
        ]
        
        if poor_performers.empty:
            return {}
        
        total_waste = poor_performers['spend'].sum()
        
        return {
            "type": "pause_campaigns",
            "priority": "high",
            "message": f"Consider pausing {len(poor_performers)} underperforming campaigns",
            "details": f"These campaigns have low CTR and ROAS < 1.0, wasting ${total_waste:.2f}",
            "potential_savings": f"${total_waste:.2f}",
            "affected_campaigns": self._format_campaign_list(poor_performers)
        }
    
    def _recommend_scaling(self) -> Dict[str, Any]:
        """Recommend campaigns to scale"""
        significant_spend = self.ad_data[self.ad_data['spend'] >= self.min_spend]
        
        if significant_spend.empty:
            return {}
        
        top_performers = significant_spend[
            (significant_spend['roas'] > significant_spend['roas'].quantile(0.8)) &
            (significant_spend['ctr'] > significant_spend['ctr'].mean())
        ]
        
        if top_performers.empty:
            return {}
        
        return {
            "type": "scale_campaigns",
            "priority": "high",
            "message": f"Consider increasing budget for {len(top_performers)} high-performing campaigns",
            "details": "These campaigns have high ROAS and above-average CTR",
            "affected_campaigns": self._format_campaign_list(top_performers)
        }
    
    def _recommend_platform_shifts(self) -> Dict[str, Any]:
        """Recommend platform budget shifts"""
        if 'source' not in self.ad_data.columns:
            return {}
        
        platform_performance = self.ad_data.groupby('source').agg({
            'roas': 'mean',
            'ctr': 'mean',
            'spend': 'sum'
        }).round(4)
        
        if len(platform_performance) < 2:
            return {}
        
        best_platform = platform_performance['roas'].idxmax()
        worst_platform = platform_performance['roas'].idxmin()
        
        best_roas = platform_performance.loc[best_platform, 'roas']
        worst_roas = platform_performance.loc[worst_platform, 'roas']
        
        # Only recommend if there's a significant difference
        if best_roas > worst_roas * 1.5:
            return {
                "type": "platform_shift",
                "priority": "medium",
                "message": f"Consider shifting budget from {worst_platform} to {best_platform}",
                "details": f"{best_platform} shows {best_roas:.2f} ROAS vs {worst_platform} at {worst_roas:.2f} ROAS",
                "best_platform": best_platform,
                "worst_platform": worst_platform
            }
        
        return {}
    
    def _recommend_campaign_restructuring(self) -> Dict[str, Any]:
        """Recommend campaign restructuring"""
        if 'campaign_name' not in self.ad_data.columns:
            return {}
        
        campaign_performance = self.ad_data.groupby('campaign_name').agg({
            'roas': 'mean',
            'spend': 'sum',
            'conversions': 'sum'
        }).round(4)
        
        underperforming = campaign_performance[
            (campaign_performance['roas'] < 0.5) & 
            (campaign_performance['spend'] > 500)
        ]
        
        if underperforming.empty:
            return {}
        
        total_wasted = underperforming['spend'].sum()
        
        return {
            "type": "campaign_restructure",
            "priority": "medium",
            "message": f"Review {len(underperforming)} campaigns with ROAS < 0.5",
            "details": f"These campaigns spent ${total_wasted:.2f} with poor returns",
            "affected_campaigns": underperforming.head(5).to_dict('index')
        }
    
    def _format_campaign_list(self, campaigns_df: pd.DataFrame, limit: int = 5) -> List[Dict[str, Any]]:
        """Format campaign list for recommendations"""
        columns = ['campaign_name', 'spend', 'roas', 'ctr', 'conversions']
        available_columns = [col for col in columns if col in campaigns_df.columns]
        
        return campaigns_df[available_columns].head(limit).to_dict('records')

class ActionPlanGenerator:
    """Generates detailed action plans for optimization"""
    
    def __init__(self, ad_data: pd.DataFrame):
        self.ad_data = ad_data.copy()
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with calculated metrics"""
        if self.ad_data.empty:
            return
        
        self.ad_data['roas'] = self.ad_data['conversions'] / (self.ad_data['spend'] + 0.001)
        self.ad_data['conversion_rate'] = self.ad_data['conversions'] / (self.ad_data['clicks'] + 0.001)
    
    def generate_action_plan(self, budget_increase_limit: float = 50) -> Dict[str, Any]:
        """Generate comprehensive action plan"""
        if self.ad_data.empty:
            return {"error": "No data available"}
        
        return {
            "immediate_actions": self._get_immediate_actions(),
            "weekly_actions": self._get_weekly_actions(),
            "monthly_actions": self._get_monthly_actions(),
            "expected_impact": self._calculate_expected_impact()
        }
    
    def _get_immediate_actions(self) -> List[Dict[str, Any]]:
        """Actions to take today"""
        actions = []
        
        # Pause worst performers
        worst_performers = self.ad_data[
            (self.ad_data['spend'] >= 50) & 
            (self.ad_data['roas'] < 0.5) & 
            (self.ad_data['ctr'] < self.ad_data['ctr'].quantile(0.2))
        ]
        
        if not worst_performers.empty:
            total_savings = worst_performers['spend'].sum()
            actions.append({
                "action": "PAUSE_ADS",
                "priority": "CRITICAL",
                "title": f"Pause {len(worst_performers)} underperforming ads",
                "description": f"Save ${total_savings:.2f}/month with minimal conversion loss",
                "time_required": "15 minutes"
            })
        
        # Scale top performers
        top_performers = self.ad_data[
            (self.ad_data['roas'] > self.ad_data['roas'].quantile(0.8)) & 
            (self.ad_data['ctr'] > self.ad_data['ctr'].mean()) &
            (self.ad_data['spend'] >= 100)
        ]
        
        if not top_performers.empty:
            actions.append({
                "action": "INCREASE_BUDGET",
                "priority": "HIGH",
                "title": f"Increase budget for {len(top_performers)} top performers",
                "description": "Scale high-ROAS campaigns for better returns",
                "time_required": "20 minutes"
            })
        
        return actions
    
    def _get_weekly_actions(self) -> List[Dict[str, Any]]:
        """Actions for this week"""
        actions = []
        
        # Platform optimization
        if 'source' in self.ad_data.columns and len(self.ad_data['source'].unique()) > 1:
            actions.append({
                "action": "OPTIMIZE_PLATFORMS",
                "priority": "MEDIUM",
                "title": "Optimize budget allocation across platforms",
                "description": "Shift budget from low-performing to high-performing platforms",
                "time_required": "2-3 hours"
            })
        
        # Campaign restructuring
        if 'campaign_name' in self.ad_data.columns:
            actions.append({
                "action": "RESTRUCTURE_CAMPAIGNS",
                "priority": "MEDIUM",
                "title": "Review and restructure underperforming campaigns",
                "description": "Consolidate audiences and refresh ad creatives",
                "time_required": "4-6 hours"
            })
        
        return actions
    
    def _get_monthly_actions(self) -> List[Dict[str, Any]]:
        """Actions for this month"""
        return [
            {
                "action": "CREATIVE_TESTING",
                "priority": "LOW",
                "title": "Launch creative testing for top campaigns",
                "description": "Prevent ad fatigue and improve CTR",
                "time_required": "6-8 hours"
            },
            {
                "action": "AUDIENCE_EXPANSION",
                "priority": "LOW",
                "title": "Expand audiences for successful campaigns",
                "description": "Scale reach while maintaining performance",
                "time_required": "4-5 hours"
            }
        ]
    
    def _calculate_expected_impact(self) -> Dict[str, Any]:
        """Calculate expected impact of actions"""
        total_spend = self.ad_data['spend'].sum()
        total_conversions = self.ad_data['conversions'].sum()
        current_roas = total_conversions / (total_spend + 0.001)
        
        # Conservative estimates
        immediate_improvement = total_conversions * 0.20
        weekly_improvement = total_conversions * 0.35
        monthly_improvement = total_conversions * 0.60
        
        return {
            "current_performance": {
                "spend": f"${total_spend:.2f}",
                "conversions": int(total_conversions),
                "roas": f"{current_roas:.2f}"
            },
            "projected_improvements": {
                "immediate": f"+{int(immediate_improvement)} conversions",
                "weekly": f"+{int(weekly_improvement)} conversions",
                "monthly": f"+{int(monthly_improvement)} conversions"
            }
        }