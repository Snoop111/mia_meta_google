from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import func
from database import Base


class AdCreative(Base):
    __tablename__ = "ad_creatives"

    id = Column(Integer, primary_key=True, index=True)
    
    # Campaign and Ad Group info
    account_id = Column(String, index=True)  # Google Ads account ID
    campaign_id = Column(String, index=True)  # Campaign ID
    campaign_name = Column(String, index=True)  # Campaign name (DFSA-PM-LEADS, etc.)
    ad_group_id = Column(String, index=True)  # Ad Group ID
    ad_group_name = Column(String, index=True)  # Ad Group name (adset_name equivalent)
    ad_id = Column(String, index=True)  # Individual ad ID
    ad_name = Column(String)  # Individual ad name
    ad_type = Column(String, default='RESPONSIVE_SEARCH_AD')  # Ad type
    
    # Creative Elements - Store as JSON text
    headlines = Column(Text)  # JSON array of headlines
    descriptions = Column(Text)  # JSON array of descriptions
    
    # Performance Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)  # Click-through rate
    conversion_rate = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)  # Cost in original currency
    cost_per_conversion = Column(Float, default=0.0)
    
    # Asset Performance Labels (from Google Ads)
    headline_performance = Column(Text)  # JSON: {"headline_1": "BEST", "headline_2": "GOOD", etc.}
    description_performance = Column(Text)  # JSON: {"description_1": "GOOD", etc.}
    
    # Data Collection Info
    date_range_start = Column(DateTime)  # Performance data date range
    date_range_end = Column(DateTime)
    data_source = Column(String, default='MANUAL_EXPORT')  # Track data source
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Flag for active/current ads
    is_active = Column(Boolean, default=True)


class CreativeInsight(Base):
    """Store processed creative insights for quick retrieval"""
    __tablename__ = "creative_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String, index=True)
    
    # Insight type and content
    insight_type = Column(String)  # 'BEST_HEADLINES', 'BEST_DESCRIPTIONS', 'TOP_PERFORMING_ADS', etc.
    insight_data = Column(Text)  # JSON data with the actual insights
    
    # Performance context
    total_clicks = Column(Integer)
    total_conversions = Column(Float)
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())