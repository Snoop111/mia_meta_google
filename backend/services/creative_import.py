"""
Creative Data Import Service
Handles manual Google Ads export CSV files for ad creative data
"""
import csv
import json
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.creative import AdCreative, CreativeInsight
import logging

logger = logging.getLogger(__name__)

class CreativeDataImporter:
    """Handles import of ad creative data from manual Google Ads exports"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_from_csv(self, csv_file_path: str, account_id: str) -> Dict[str, Any]:
        """
        Import ad creative data from Google Ads CSV export
        
        Expected CSV columns (from Google Ads export):
        - Campaign, Ad group, Ad, Ad type, Headline 1, Headline 2, Headline 3, etc.
        - Description line 1, Description line 2, etc.
        - Clicks, Impressions, Conversions, CTR, Cost, Cost / conv.
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            logger.info(f"Loaded CSV with {len(df)} rows and columns: {list(df.columns)}")
            
            results = {
                'success': True,
                'imported_ads': 0,
                'updated_ads': 0,
                'errors': []
            }
            
            for index, row in df.iterrows():
                try:
                    # Extract creative data
                    creative_data = self._extract_creative_from_row(row, account_id)
                    
                    if creative_data:
                        # Check if ad already exists
                        existing_ad = self.db.query(AdCreative).filter_by(
                            account_id=account_id,
                            ad_id=creative_data.get('ad_id', ''),
                            campaign_name=creative_data.get('campaign_name', '')
                        ).first()
                        
                        if existing_ad:
                            # Update existing ad
                            self._update_ad_creative(existing_ad, creative_data)
                            results['updated_ads'] += 1
                        else:
                            # Create new ad
                            new_ad = AdCreative(**creative_data)
                            self.db.add(new_ad)
                            results['imported_ads'] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing row {index}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            # Generate insights after import
            self._generate_creative_insights(account_id)
            
            return results
            
        except Exception as e:
            logger.error(f"Error importing CSV: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'imported_ads': 0,
                'updated_ads': 0
            }
    
    def _extract_creative_from_row(self, row: pd.Series, account_id: str) -> Optional[Dict[str, Any]]:
        """Extract creative data from a CSV row"""
        try:
            # Map common Google Ads export column names
            campaign_name = self._get_column_value(row, ['Campaign', 'campaign', 'Campaign name'])
            ad_group_name = self._get_column_value(row, ['Ad group', 'ad_group', 'Ad Group', 'Adgroup'])
            ad_name = self._get_column_value(row, ['Ad', 'ad', 'Ad name'])
            ad_type = self._get_column_value(row, ['Ad type', 'ad_type', 'Type'], default='RESPONSIVE_SEARCH_AD')
            
            # Extract headlines (up to 15 for RSAs)
            headlines = []
            for i in range(1, 16):  # Google Ads RSAs can have up to 15 headlines
                headline = self._get_column_value(row, [f'Headline {i}', f'headline_{i}', f'Headline{i}'])
                if headline and headline.strip():
                    headlines.append(headline.strip())
            
            # Extract descriptions (up to 4 for RSAs)
            descriptions = []
            for i in range(1, 5):  # Google Ads RSAs can have up to 4 descriptions
                desc = self._get_column_value(row, [f'Description line {i}', f'description_{i}', f'Description {i}'])
                if desc and desc.strip():
                    descriptions.append(desc.strip())
            
            # Extract performance metrics
            clicks = self._get_numeric_value(row, ['Clicks', 'clicks'], default=0)
            impressions = self._get_numeric_value(row, ['Impressions', 'impressions', 'Impr.'], default=0)
            conversions = self._get_numeric_value(row, ['Conversions', 'conversions', 'Conv.'], default=0.0)
            ctr = self._get_numeric_value(row, ['CTR', 'ctr', 'Click-through rate'], default=0.0)
            cost = self._get_numeric_value(row, ['Cost', 'cost', 'Spend'], default=0.0)
            cost_per_conversion = self._get_numeric_value(row, ['Cost / conv.', 'cost_per_conversion', 'CPA'], default=0.0)
            
            # Calculate conversion rate if not provided
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            
            # Skip if no headlines found (invalid ad)
            if not headlines:
                return None
            
            creative_data = {
                'account_id': account_id,
                'campaign_name': campaign_name or 'Unknown Campaign',
                'ad_group_name': ad_group_name or 'Unknown Ad Group', 
                'ad_name': ad_name or 'Unknown Ad',
                'ad_type': ad_type,
                'headlines': json.dumps(headlines),
                'descriptions': json.dumps(descriptions),
                'clicks': int(clicks),
                'impressions': int(impressions),
                'conversions': float(conversions),
                'ctr': float(ctr),
                'conversion_rate': float(conversion_rate),
                'cost': float(cost),
                'cost_per_conversion': float(cost_per_conversion),
                'data_source': 'MANUAL_EXPORT',
                'is_active': True
            }
            
            return creative_data
            
        except Exception as e:
            logger.error(f"Error extracting creative data: {str(e)}")
            return None
    
    def _get_column_value(self, row: pd.Series, possible_columns: List[str], default: str = '') -> str:
        """Get value from row using multiple possible column names"""
        for col in possible_columns:
            if col in row.index and pd.notna(row[col]):
                return str(row[col])
        return default
    
    def _get_numeric_value(self, row: pd.Series, possible_columns: List[str], default: float = 0.0) -> float:
        """Get numeric value from row, handling various formats"""
        for col in possible_columns:
            if col in row.index and pd.notna(row[col]):
                try:
                    # Remove common formatting characters
                    value_str = str(row[col]).replace(',', '').replace('%', '').replace('$', '').replace('R', '').strip()
                    return float(value_str) if value_str else default
                except (ValueError, TypeError):
                    continue
        return default
    
    def _update_ad_creative(self, existing_ad: AdCreative, creative_data: Dict[str, Any]):
        """Update existing ad creative with new data"""
        for key, value in creative_data.items():
            if hasattr(existing_ad, key):
                setattr(existing_ad, key, value)
        existing_ad.updated_at = datetime.utcnow()
    
    def _generate_creative_insights(self, account_id: str):
        """Generate creative insights after data import"""
        try:
            # Get all ads for the account
            ads = self.db.query(AdCreative).filter_by(account_id=account_id, is_active=True).all()
            
            if not ads:
                return
            
            insights = []
            
            # Top performing headlines by CTR
            headline_performance = {}
            for ad in ads:
                if ad.headlines:
                    headlines = json.loads(ad.headlines)
                    for headline in headlines:
                        if headline not in headline_performance:
                            headline_performance[headline] = {'clicks': 0, 'impressions': 0, 'conversions': 0, 'ads': 0}
                        headline_performance[headline]['clicks'] += ad.clicks
                        headline_performance[headline]['impressions'] += ad.impressions
                        headline_performance[headline]['conversions'] += ad.conversions
                        headline_performance[headline]['ads'] += 1
            
            # Calculate CTR for each headline
            for headline, data in headline_performance.items():
                if data['impressions'] > 0:
                    data['ctr'] = (data['clicks'] / data['impressions']) * 100
                    data['conversion_rate'] = (data['conversions'] / data['clicks']) * 100 if data['clicks'] > 0 else 0
            
            # Sort by CTR and get top performers
            top_headlines = sorted(
                headline_performance.items(), 
                key=lambda x: x[1]['ctr'], 
                reverse=True
            )[:10]
            
            # Store insights
            insights_data = {
                'top_headlines_by_ctr': [
                    {
                        'headline': headline,
                        'ctr': data['ctr'],
                        'clicks': data['clicks'],
                        'impressions': data['impressions'],
                        'conversions': data['conversions'],
                        'ads_used_in': data['ads']
                    }
                    for headline, data in top_headlines
                ],
                'generated_at': datetime.utcnow().isoformat(),
                'total_ads_analyzed': len(ads)
            }
            
            # Save or update insights
            existing_insights = self.db.query(CreativeInsight).filter_by(
                account_id=account_id,
                insight_type='BEST_HEADLINES'
            ).first()
            
            if existing_insights:
                existing_insights.insight_data = json.dumps(insights_data)
                existing_insights.updated_at = datetime.utcnow()
            else:
                new_insights = CreativeInsight(
                    account_id=account_id,
                    insight_type='BEST_HEADLINES',
                    insight_data=json.dumps(insights_data),
                    total_clicks=sum(ad.clicks for ad in ads),
                    total_conversions=sum(ad.conversions for ad in ads)
                )
                self.db.add(new_insights)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")


def get_creative_insights(db: Session, account_id: str, insight_type: str = None) -> Dict[str, Any]:
    """Get creative insights for an account"""
    query = db.query(CreativeInsight).filter_by(account_id=account_id)
    
    if insight_type:
        query = query.filter_by(insight_type=insight_type)
    
    insights = query.all()
    
    result = {
        'account_id': account_id,
        'insights': {}
    }
    
    for insight in insights:
        try:
            insight_data = json.loads(insight.insight_data) if insight.insight_data else {}
            result['insights'][insight.insight_type] = {
                'data': insight_data,
                'updated_at': insight.updated_at.isoformat() if insight.updated_at else None,
                'total_clicks': insight.total_clicks,
                'total_conversions': insight.total_conversions
            }
        except json.JSONDecodeError:
            logger.error(f"Error parsing insight data for {insight.insight_type}")
    
    return result


def get_ad_creative_summary(db: Session, account_id: str, campaign_name: str = None) -> Dict[str, Any]:
    """Get summary of ad creative data for an account or campaign"""
    query = db.query(AdCreative).filter_by(account_id=account_id, is_active=True)
    
    if campaign_name:
        query = query.filter_by(campaign_name=campaign_name)
    
    ads = query.all()
    
    if not ads:
        return {'error': 'No ad creative data found'}
    
    # Aggregate data
    total_clicks = sum(ad.clicks for ad in ads)
    total_impressions = sum(ad.impressions for ad in ads)
    total_conversions = sum(ad.conversions for ad in ads)
    total_cost = sum(ad.cost for ad in ads)
    
    # Calculate averages
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cost_per_conversion = (total_cost / total_conversions) if total_conversions > 0 else 0
    
    # Get unique headlines and descriptions
    all_headlines = set()
    all_descriptions = set()
    
    for ad in ads:
        if ad.headlines:
            headlines = json.loads(ad.headlines)
            all_headlines.update(headlines)
        if ad.descriptions:
            descriptions = json.loads(ad.descriptions)
            all_descriptions.update(descriptions)
    
    return {
        'account_id': account_id,
        'campaign_name': campaign_name,
        'summary': {
            'total_ads': len(ads),
            'total_clicks': total_clicks,
            'total_impressions': total_impressions,
            'total_conversions': total_conversions,
            'total_cost': total_cost,
            'average_ctr': avg_ctr,
            'average_cost_per_conversion': avg_cost_per_conversion,
            'unique_headlines': len(all_headlines),
            'unique_descriptions': len(all_descriptions),
            'campaigns': list(set(ad.campaign_name for ad in ads))
        },
        'top_performing_ads': [
            {
                'campaign_name': ad.campaign_name,
                'ad_group_name': ad.ad_group_name,
                'ad_name': ad.ad_name,
                'clicks': ad.clicks,
                'conversions': ad.conversions,
                'ctr': ad.ctr,
                'cost_per_conversion': ad.cost_per_conversion,
                'headlines': json.loads(ad.headlines) if ad.headlines else [],
                'descriptions': json.loads(ad.descriptions) if ad.descriptions else []
            }
            for ad in sorted(ads, key=lambda x: x.conversions, reverse=True)[:5]
        ]
    }