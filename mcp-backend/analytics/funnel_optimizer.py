"""
Funnel Optimization Module
Generates specific optimization recommendations for conversion funnels
"""

import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class FunnelOptimizer:
    """Generates optimization recommendations for conversion funnels"""
    
    def __init__(self, ga4_data: pd.DataFrame, ad_data: pd.DataFrame):
        self.ga4_data = ga4_data
        self.ad_data = ad_data
    
    def generate_optimization_plan(self, budget_limit: float = 50) -> Dict[str, Any]:
        """Generate comprehensive optimization plan"""
        if hasattr(self.ga4_data, 'empty') and self.ga4_data.empty:
            return {"error": "No GA4 data available"}
        
        current_performance = self._analyze_current_performance()
        
        return {
            "immediate_fixes": self._get_immediate_fixes(current_performance),
            "week_1_optimizations": self._get_weekly_optimizations(current_performance),
            "month_1_improvements": self._get_monthly_improvements(),
            "expected_impact": self._calculate_expected_impact(current_performance)
        }
    
    def _analyze_current_performance(self) -> Dict[str, float]:
        """Analyze current baseline performance"""
        return {
            'engagement_rate': self.ga4_data.get('engagementRate', pd.Series([50])).mean(),
            'conversion_rate': self._calculate_conversion_rate(),
            'avg_duration': self.ga4_data.get('avgSessionDuration', pd.Series([0])).mean()
        }
    
    def _calculate_conversion_rate(self) -> float:
        """Calculate overall conversion rate"""
        if 'conversions' not in self.ga4_data.columns or 'sessions' not in self.ga4_data.columns:
            return 0.0
        
        total_conversions = self.ga4_data['conversions'].sum()
        total_sessions = self.ga4_data['sessions'].sum()
        
        if total_sessions == 0:
            return 0.0
        
        return round((total_conversions / total_sessions) * 100, 2)
    
    def _get_immediate_fixes(self, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get immediate fixes (24-48 hours)"""
        fixes = []
        
        # Low engagement rate fix
        if performance['engagement_rate'] < 40:
            fixes.append({
                "priority": "CRITICAL",
                "issue": f"Low engagement rate: {performance['engagement_rate']:.1f}%",
                "action": "Optimize landing page message match",
                "specific_steps": [
                    "Review top 3 ad headlines vs landing page headlines",
                    "Ensure value proposition matches exactly",
                    "Test page load speed with GTmetrix",
                    "Fix loading issues over 3 seconds"
                ],
                "expected_impact": "Increase engagement rate by 15-25%",
                "time_required": "2-4 hours"
            })
        
        # Mobile performance issues
        mobile_issues = self._detect_mobile_issues()
        if mobile_issues:
            fixes.append(mobile_issues)
        
        return fixes
    
    def _detect_mobile_issues(self) -> Dict[str, Any]:
        """Detect mobile performance issues"""
        if 'deviceCategory' not in self.ga4_data.columns:
            return {}
        
        device_perf = self.ga4_data.groupby('deviceCategory').agg({
            'engagementRate': 'mean',
            'sessions': 'sum'
        }).round(2)
        
        mobile_engagement = device_perf.get('mobile', {}).get('engagementRate', 50)
        desktop_engagement = device_perf.get('desktop', {}).get('engagementRate', 50)
        
        if mobile_engagement < desktop_engagement * 0.7:
            return {
                "priority": "HIGH",
                "issue": f"Poor mobile experience - {mobile_engagement:.1f}% vs {desktop_engagement:.1f}%",
                "action": "Fix mobile landing page experience",
                "specific_steps": [
                    "Test landing page on mobile device",
                    "Ensure buttons are large enough to tap",
                    "Check forms are mobile-friendly",
                    "Optimize images for mobile loading speed"
                ],
                "expected_impact": "Increase mobile engagement by 20-30%",
                "time_required": "3-6 hours"
            }
        
        return {}
    
    def _get_weekly_optimizations(self, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get week 1 optimizations"""
        optimizations = []
        
        # Conversion rate optimization
        if performance['conversion_rate'] < 2.0:
            optimizations.append({
                "priority": "HIGH",
                "issue": f"Low conversion rate: {performance['conversion_rate']:.2f}%",
                "action": "Implement conversion rate optimization tactics",
                "specific_steps": [
                    "Add customer testimonials above the fold",
                    "Include trust signals (security badges, guarantees)",
                    "Create urgency with limited-time offers",
                    "Simplify forms (reduce required fields)",
                    "A/B test different call-to-action buttons"
                ],
                "expected_impact": "Increase conversion rate by 0.5-1.5%",
                "time_required": "8-12 hours"
            })
        
        # Traffic quality improvement
        traffic_optimization = self._analyze_traffic_quality()
        if traffic_optimization:
            optimizations.append(traffic_optimization)
        
        return optimizations
    
    def _analyze_traffic_quality(self) -> Dict[str, Any]:
        """Analyze traffic quality for optimization"""
        if hasattr(self.ad_data, 'empty') and self.ad_data.empty:
            return {}
        
        # Identify campaigns with high spend but low quality
        ad_summary = self.ad_data.groupby('campaign_name').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'conversions': 'sum'
        }).round(2)
        
        ad_summary['conversion_rate'] = round(
            (ad_summary['conversions'] / (ad_summary['clicks'] + 0.001)) * 100, 2
        )
        
        low_quality_campaigns = ad_summary[ad_summary['conversion_rate'] < 1.0]
        
        if hasattr(low_quality_campaigns, 'empty') and not low_quality_campaigns.empty:
            return {
                "priority": "MEDIUM",
                "issue": f"{len(low_quality_campaigns)} campaigns driving low-quality traffic",
                "action": "Improve ad targeting and relevance",
                "specific_steps": [
                    "Review audience targeting for low-converting campaigns",
                    "Add negative keywords to exclude irrelevant searches",
                    "Test ad copy variations focused on qualified leads",
                    "Adjust geographic targeting if needed"
                ],
                "expected_impact": "Improve overall conversion rate by 10-20%",
                "time_required": "6-10 hours"
            }
        
        return {}
    
    def _get_monthly_improvements(self) -> List[Dict[str, Any]]:
        """Get month 1 improvements"""
        return [{
            "priority": "MEDIUM",
            "issue": "Comprehensive funnel optimization",
            "action": "Implement advanced conversion optimization",
            "specific_steps": [
                "Set up heat mapping to understand user behavior",
                "Implement exit-intent popups with special offers",
                "Create retargeting campaigns for website visitors",
                "A/B test completely different landing page designs",
                "Optimize page loading speed to under 2 seconds"
            ],
            "expected_impact": "Overall conversion improvement of 25-50%",
            "time_required": "20-30 hours"
        }]
    
    def _calculate_expected_impact(self, performance: Dict[str, float]) -> Dict[str, Any]:
        """Calculate expected impact of optimizations"""
        if hasattr(self.ga4_data, 'empty') and self.ga4_data.empty:
            return {}
        
        total_sessions = self.ga4_data['sessions'].sum()
        current_conversions = self.ga4_data.get('conversions', pd.Series([0])).sum()
        current_conv_rate = performance['conversion_rate']
        
        # Conservative impact estimates
        immediate_impact = current_conversions * 0.20  # 20% improvement
        weekly_impact = current_conversions * 0.35     # 35% improvement
        monthly_impact = current_conversions * 0.60    # 60% improvement
        
        return {
            "current_monthly_conversions": int(current_conversions),
            "current_conversion_rate": f"{current_conv_rate:.2f}%",
            "after_immediate_fixes": {
                "conversions": int(current_conversions + immediate_impact),
                "additional_conversions": int(immediate_impact)
            },
            "after_week_1": {
                "conversions": int(current_conversions + weekly_impact),
                "additional_conversions": int(weekly_impact)
            },
            "after_month_1": {
                "conversions": int(current_conversions + monthly_impact),
                "additional_conversions": int(monthly_impact)
            }
        }