# Comprehensive Marketing Insights Endpoint 🚀

**One endpoint that runs ALL 7 analyses with maximum flexibility for data inputs.**

## 🎯 The Super Endpoint

### `POST /comprehensive-insights`

**What it does:** Executes all available marketing analyses in a single API call, automatically adapting to whatever data you provide.

## 📊 All 7 Analyses Included

1. **File Consolidation** - Combines uploaded CSV files
2. **Ad Performance Analysis** - Comprehensive platform performance  
3. **Campaign Comparison** - Side-by-side campaign rankings
4. **User Journey Analysis** - Funnel from ads to conversions
5. **Funnel Optimization** - Specific improvement recommendations
6. **Recommendations Engine** - Actionable optimization suggestions
7. **Action Plan Generator** - Step-by-step implementation guide

## 🔧 Flexible Input Options

### Option 1: Upload CSV Files Only
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-01-31" \
  -F "ga4_file=@analytics.csv" \
  -F "meta_file=@meta_ads.csv" \
  -F "google_file=@google_ads.csv"
```

### Option 2: Use API Credentials Only  
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-01-31" \
  -F "use_api_data=true"
```

### Option 3: Mixed Sources
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-01-31" \
  -F "meta_file=@meta_ads.csv" \
  -F "use_api_data=true" \
  -F "min_spend_threshold=200"
```

### Option 4: Skip What You Don't Have
```bash
# Only Meta ads data
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-01-31" \
  -F "meta_file=@meta_ads.csv"
```

## 📝 Parameters

### Required
- `user_id` - Your user identifier
- `start_date` - Analysis start date (YYYY-MM-DD)  
- `end_date` - Analysis end date (YYYY-MM-DD)

### Optional Files
- `ga4_file` - Google Analytics 4 CSV export
- `meta_file` - Meta Ads CSV export
- `google_file` - Google Ads CSV export

### Optional Configuration
- `use_api_data` - Use stored API credentials (default: false)
- `min_spend_threshold` - Minimum spend for recommendations (default: 100)
- `budget_increase_limit` - Max budget increase % (default: 50)
- `data_sources` - API sources to use (default: "meta_ads,google_ads")

## 🧠 Smart Data Handling

The endpoint automatically:

✅ **Adapts to available data** - Runs analyses based on what you provide  
✅ **Falls back gracefully** - Prefers API data, falls back to uploaded files  
✅ **Skips impossible analyses** - Won't run funnel analysis without GA4 data  
✅ **Combines data sources** - Merges uploaded + API data when beneficial  
✅ **Handles missing columns** - Fills in missing data automatically  

## 📊 Response Structure

```json
{
  "success": true,
  "user_id": "123",
  "analysis_period": "2024-01-01 to 2024-01-31",
  "configuration": {
    "uploaded_files": {
      "ga4_file": true,
      "meta_file": true,
      "google_file": false
    },
    "used_api_data": true,
    "data_sources": ["meta_ads", "google_ads"],
    "min_spend_threshold": 100,
    "budget_increase_limit": 50
  },
  "analyses_performed": [
    "file_consolidation",
    "ad_performance", 
    "campaign_comparison",
    "user_journey",
    "funnel_optimization",
    "recommendations",
    "action_plan"
  ],
  
  // All 7 analysis results
  "file_consolidation": { 
    "summary": {...},
    "platform_performance": {...},
    "top_campaigns": {...},
    "recommendations": [...]
  },
  "ad_performance": {
    "overall_metrics": {...},
    "platform_comparison": {...},
    "top_performers": {...},
    "bottom_performers": {...}
  },
  "campaign_comparison": {
    "campaign_comparison": {...},
    "campaign_rankings": {...}
  },
  "user_journey": {
    "funnel_overview": {...},
    "conversion_rates": {...},
    "drop_off_analysis": {...}
  },
  "funnel_optimization": {
    "immediate_fixes": [...],
    "week_1_optimizations": [...],
    "month_1_improvements": [...],
    "expected_impact": {...}
  },
  "recommendations": [
    {
      "type": "pause_campaigns",
      "priority": "high",
      "message": "Consider pausing 3 underperforming campaigns",
      "potential_savings": "$1,250.00"
    }
  ],
  "action_plan": {
    "immediate_actions": [...],
    "weekly_actions": [...],
    "monthly_actions": [...],
    "expected_impact": {...}
  },
  
  // Summary of what was analyzed
  "analysis_summary": {
    "total_analyses_run": 7,
    "data_sources_used": {
      "uploaded_files": true,
      "api_ga4_data": true,
      "api_ad_data": true
    }
  }
}
```

## 🎯 Use Cases

### Perfect for:
- **Dashboard applications** that need comprehensive insights
- **Automated reporting** systems
- **Client deliverables** requiring multiple analysis types
- **API integrations** that want everything at once
- **Flexible data scenarios** where you don't know what data is available

### Analysis Coverage Based on Data:

| Data Available | Analyses That Run |
|----------------|-------------------|
| Only uploaded files | File consolidation, ad performance, campaign comparison, recommendations, action plan |
| Only API credentials | Ad performance, campaign comparison, recommendations, action plan |
| GA4 + Ad data | ALL 7 analyses |
| Ad data only | 5 analyses (excludes user journey & funnel optimization) |
| GA4 data only | File consolidation only |

## ⚡ Benefits

✅ **One call does it all** - No need for multiple API requests  
✅ **Maximum flexibility** - Works with whatever data you have  
✅ **Intelligent fallbacks** - Always gets you the best possible analysis  
✅ **Time efficient** - Parallel processing of all analyses  
✅ **Complete insights** - Every possible recommendation and action item  

**The ultimate marketing insights endpoint that adapts to your data!** 🎉