# Ad Agency Analysis Guide

## Overview

Your Brain API is **perfectly suited for ad agency analysis** and can tell you exactly "what works and what doesn't work" for ads. Here's your complete implementation guide.

## What Your System Can Do

### ✅ Current Capabilities
- **Multi-Platform Data Collection**: Meta Ads, Google Ads, GA4
- **AutoML Prediction**: Predict conversion rates, CTR, ROAS
- **Feature Importance**: SHAP analysis shows which factors drive performance
- **Clustering**: Group similar campaigns/ads for pattern analysis
- **Persistent User Management**: Each agency client gets their own stored credentials

### ✅ New Ad-Specific Endpoints Added
- **Performance Analysis**: Identify top/bottom performers
- **Campaign Comparison**: Side-by-side campaign analysis
- **Actionable Recommendations**: AI-powered optimization suggestions
- **Trend Analysis**: Performance over time analysis

## Complete Workflow for Ad Agencies

### 1. Setup Client Credentials (One-time)

```bash
# Configure Meta Ads + Google Ads for client "nike_agency"
curl --location 'http://localhost:8000/configure-data-sources' \
--header 'Content-Type: application/json' \
--data '{
  "user_id": "nike_agency",
  "credentials": {
    "meta_ads": {
      "access_token": "CLIENT_META_TOKEN",
      "app_id": "CLIENT_APP_ID", 
      "app_secret": "CLIENT_APP_SECRET"
    },
    "google_ads": {
      "developer_token": "CLIENT_DEV_TOKEN",
      "client_id": "CLIENT_ID",
      "client_secret": "CLIENT_SECRET", 
      "refresh_token": "CLIENT_REFRESH_TOKEN"
    }
  }
}'
```

### 2. Ad Performance Analysis - "What Works & What Doesn't"

```bash
# Get comprehensive performance insights
curl --location 'http://localhost:8000/ad-performance-analysis' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"data_sources\": [\"meta_ads\", \"google_ads\"]
}"'
```

**Returns:**
- **Top Performers**: Best CTR, CPC, ROAS, conversion rate ads
- **Bottom Performers**: Worst performing ads (with minimum spend filter)
- **Campaign Summary**: Performance by campaign
- **Platform Comparison**: Meta vs Google Ads performance
- **Overall Metrics**: Total spend, conversions, ROAS

### 3. Campaign Comparison

```bash
# Compare specific campaigns
curl --location 'http://localhost:8000/campaign-comparison' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"campaigns\": [\"Summer Sale\", \"Winter Collection\", \"Brand Awareness\"]
}"'
```

**Returns:**
- Side-by-side campaign metrics
- Campaign rankings by ROAS, CTR, conversions
- Spend efficiency analysis

### 4. Actionable Recommendations

```bash
# Get AI-powered optimization recommendations
curl --location 'http://localhost:8000/ad-recommendations' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"min_spend\": 100
}"'
```

**Returns:**
- **Stop Ads**: Which ads to pause (low CTR + ROAS < 1.0)
- **Scale Ads**: Which ads to increase budget (high ROAS + above-average CTR)
- **Platform Shift**: Move budget to better-performing platform
- **Campaign Review**: Campaigns with ROAS < 0.5 needing attention

### 5. **NEW** Optimization Action Plan - Step-by-Step Instructions

```bash
# Get detailed action plan with specific steps
curl --location 'http://localhost:8000/optimization-action-plan' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"budget_increase_limit\": 50
}"'
```

**Returns:**
- **Immediate Actions** (Do Today): 
  - Exact ads to pause with step-by-step instructions
  - Specific budget increases with platform steps
  - Time required: 15-20 minutes each
- **Weekly Actions** (Do This Week):
  - Platform budget shifts with calculations  
  - Campaign restructuring guides
  - Time required: 2-6 hours
- **Monthly Actions** (Do This Month):
  - Creative testing strategies
  - Audience expansion plans
  - Time required: 4-8 hours

### 6. **NEW** Budget Reallocation Plan - Exact Dollar Amounts

```bash
# Get precise budget reallocation with dollar amounts
curl --location 'http://localhost:8000/budget-reallocation-plan' \
--form 'request="{
  \"user_id\": \"nike_agency\", 
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"total_monthly_budget\": 15000
}"'
```

**Returns:**
- **Current vs Optimal Allocation**: Campaign-by-campaign breakdown
- **Reallocation Steps**: 
  - Step 1: Decrease budgets (which campaigns, by how much)
  - Step 2: Increase budgets (which campaigns, by how much)
- **Impact Projections**: Expected conversion increase %

### 7. Performance Trends

```bash
# Analyze CTR trends over time
curl --location 'http://localhost:8000/performance-trends' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"metric\": \"ctr\"
}"'
```

**Returns:**
- Daily trend data
- Trend direction (improving/declining/stable)
- Best and worst performing days
- Average performance

### 8. Predictive Analysis (Existing)

```bash
# Predict what drives conversions
curl --location 'http://localhost:8000/predict-with-user-data' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"target\": \"conversions\",
  \"id\": \"nike_conversion_model\",
  \"use_external_data\": true,
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\"
}"'
```

**Returns:**
- Conversion predictions
- SHAP feature importance (which factors drive conversions most)
- Clustering of similar ads
- Feature columns used

## Data You'll Get

### From Meta Ads:
- `campaign_name`, `adset_name`, `ad_name`
- `impressions`, `clicks`, `spend`, `reach`, `frequency`
- `ctr`, `cpc`, `cpm`, `conversions`
- `date` for time-series analysis

### From Google Ads:
- `campaign_name`, `ad_group_name`
- `impressions`, `clicks`, `spend`, `conversions`
- `ctr`, `average_cpc`
- `date` for time-series analysis

### Calculated Metrics:
- **ROAS**: Return on Ad Spend (conversions / spend)
- **Conversion Rate**: conversions / clicks
- **Cost Per Conversion**: spend / conversions

## What This Tells Ad Agencies

### 1. **What Works** ✅
- **Top performing ads** by CTR, ROAS, conversion rate
- **Best campaigns** ranked by performance metrics  
- **Optimal platforms** (Meta vs Google performance)
- **High-impact features** from SHAP analysis
- **Successful ad patterns** from clustering

### 2. **What Doesn't Work** ❌
- **Underperforming ads** wasting budget
- **Poor campaigns** with ROAS < 1.0
- **Inefficient platforms** with lower returns
- **Low-impact features** to ignore
- **Failed ad patterns** to avoid

### 3. **What to Do Next** 🎯
**NEW: Step-by-Step Action Plans:**
- **Immediate Actions** (15-20 min each):
  - Pause specific underperforming ads with exact steps
  - Increase budget for high-ROAS ads with platform instructions
- **Weekly Actions** (2-6 hours):
  - Shift budget between platforms with dollar amounts
  - Restructure underperforming campaigns with detailed guides
- **Monthly Actions** (4-8 hours):
  - Launch creative testing with A/B test setups
  - Expand audiences for successful campaigns

**NEW: Precise Budget Reallocation:**
- Campaign-by-campaign dollar amount adjustments
- Exact budget decreases and increases
- Projected impact on conversions and ROAS

## Advanced Use Cases

### A. Client Reporting Automation
```python
# Generate monthly client report
results = []
results.append(requests.post("http://localhost:8000/ad-performance-analysis", ...))
results.append(requests.post("http://localhost:8000/ad-recommendations", ...))
results.append(requests.post("http://localhost:8000/campaign-comparison", ...))

# Combine into client report
```

### B. Budget Optimization
```python
# Get recommendations for budget reallocation
recommendations = requests.post("http://localhost:8000/ad-recommendations", ...)

# Parse recommendations to automatically pause/scale ads
for rec in recommendations['recommendations']:
    if rec['type'] == 'stop_ads':
        # Pause these ads via Meta/Google APIs
    elif rec['type'] == 'scale_ads':
        # Increase budget via Meta/Google APIs
```

### C. Predictive Campaign Planning
```python
# Use historical data to predict new campaign performance
prediction = requests.post("http://localhost:8000/predict-with-user-data", ...)

# Use SHAP values to design new campaigns
# Focus on high-importance features
```

## Example Agency Report

### Nike Agency - January 2025 Performance Report

**Overall Performance:**
- Total Spend: $45,230
- Total Conversions: 1,247
- Overall ROAS: 2.8
- Average CTR: 2.1%

**Top Performing Ads:**
1. "Air Max Flash Sale" - 4.2% CTR, 3.8 ROAS
2. "Basketball Collection" - 3.9% CTR, 3.2 ROAS
3. "Running Shoes Winter" - 3.1% CTR, 2.9 ROAS

**Immediate Actions (Do Today - 35 minutes total):**
- **PAUSE**: 12 specific ads (exact names provided)
  - Steps: Login → Ads tab → Filter → Select → Pause
  - Saves: $3,400/month, Time: 15 minutes
- **SCALE**: 8 high-performing ads (exact campaigns listed)
  - Steps: Campaign level → Increase budget 50% → Monitor 3-5 days
  - Impact: +20-40% conversions, Time: 20 minutes

**Weekly Actions (Do This Week - 4 hours total):**
- **PLATFORM SHIFT**: Move $2,800 from Google to Meta
  - Step 1: Reduce Google campaign budgets by 30%
  - Step 2: Create new Meta campaigns with shifted budget
  - Expected: +0.6 ROAS improvement

**Predicted Impact:**
- Expected 15% increase in conversions
- Projected 22% reduction in cost per conversion
- Estimated additional ROAS: +0.4

## Integration with Existing Tools

Your system can integrate with:
- **Meta Business Manager**: Auto-pause/scale ads based on recommendations
- **Google Ads Editor**: Bulk campaign optimizations
- **Client Dashboards**: Real-time performance streaming
- **Slack/Teams**: Automated alert system for performance changes

## Getting Started

1. **Set up one client** with the credential configuration
2. **Run ad-performance-analysis** to see immediate insights
3. **Get recommendations** for quick wins
4. **Use predictions** to understand what drives success
5. **Scale to all clients** with the user-based system

## NEW: Website Drop-off Analysis

The most critical piece for ad agencies - understanding WHY users drop off after clicking ads!

### 9. User Journey Analysis - From Ad Click to Conversion

```bash
# Analyze complete user journey with drop-off points
curl --location 'http://localhost:8000/user-journey-analysis' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\"
}"'
```

**Returns:**
- **Funnel Overview**: Ad clicks → Website sessions → Engaged sessions → Conversions
- **Conversion Rates**: Click-to-session, session-to-engagement, session-to-conversion
- **Drop-off Analysis**: Exact number of users lost at each stage with potential reasons
- **Traffic Source Performance**: Which sources convert best vs worst

### 10. Drop-off Analysis with Specific Reasons

```bash
# Get detailed reasons WHY users are dropping off
curl --location 'http://localhost:8000/drop-off-analysis' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\",
  \"funnel_steps\": [\"landing_page\", \"product_page\", \"cart\", \"checkout\", \"purchase\"]
}"'
```

**Returns:**
- **High Bounce Rate Analysis**: Which traffic sources have >70% bounce rate and why
- **Mobile vs Desktop Issues**: Specific mobile experience problems
- **Technical Issues**: Page loading, mobile optimization, checkout problems
- **User Behavior Patterns**: Session duration analysis and user intent mismatch

### 11. Conversion Funnel Optimization Plan

```bash
# Get step-by-step plan to fix drop-offs
curl --location 'http://localhost:8000/conversion-funnel-optimization' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\"
}"'
```

**Returns:**
- **Immediate Fixes** (24-48 hours): Fix high bounce rate, mobile issues
- **Week 1 Optimizations**: CRO tactics, traffic quality improvements  
- **Month 1 Improvements**: Advanced funnel optimization, retargeting
- **Expected Impact**: Projected conversion increases at each stage

### 12. Traffic Quality Analysis

```bash
# Analyze which ad traffic actually converts well
curl --location 'http://localhost:8000/traffic-quality-analysis' \
--form 'request="{
  \"user_id\": \"nike_agency\",
  \"start_date\": \"2025-01-01\",
  \"end_date\": \"2025-01-31\"
}"'
```

**Returns:**
- **Traffic Source Quality Scores**: Ranked by conversion rate, bounce rate, engagement
- **Campaign Quality Analysis**: High-spend campaigns with poor website performance
- **Recommendations**: Which campaigns to optimize vs pause

## Complete Drop-off Analysis Workflow

### Problem: "My ads get clicks but users drop off"

**Step 1**: Run `/user-journey-analysis` 
- See exactly where users drop off (ads → website → engagement → conversion)
- Identify the biggest problem stage

**Step 2**: Run `/drop-off-analysis`
- Get specific reasons WHY they're dropping off
- Technical issues, mobile problems, content mismatch

**Step 3**: Run `/conversion-funnel-optimization` 
- Get exact steps to fix each issue
- Prioritized by impact and time required

**Step 4**: Run `/traffic-quality-analysis`
- Identify which ad campaigns bring quality traffic
- Which ones to optimize vs pause

## What This Solves for Ad Agencies

### 🔍 **What You Can Now Tell Clients:**

**Instead of**: *"Your conversion rate is low"*
**Now**: *"67% of users drop off between ad click and website session due to 4.2-second loading times and mobile optimization issues. Here's the 3-step fix that will recover 40% of those lost users."*

**Instead of**: *"Your ads aren't converting well"*  
**Now**: *"Your Facebook campaign 'Summer Sale' has a 78% bounce rate because the ad promises '50% off' but the landing page shows '30% off'. Fix this message match and expect 25% more conversions."*

**Instead of**: *"Optimize your website"*
**Now**: *"Mobile users have 2.3x higher bounce rate than desktop. Implement these 5 mobile UX fixes (15 hours total) to increase mobile conversions by 35%."*

### 🎯 **Specific Issues You Can Identify:**

- **Ad-to-Website Mismatch**: Ad messaging vs landing page content
- **Mobile Experience Problems**: Poor mobile UX causing drops
- **Technical Issues**: Slow loading, broken checkout, form problems  
- **Traffic Quality Issues**: Which campaigns bring visitors who don't convert
- **Trust/Security Concerns**: Missing testimonials, security badges
- **Conversion Process Problems**: Complicated checkout, poor CTAs

### 📊 **Data You'll Get:**

From **GA4 Enhanced Tracking**:
- Page-by-page user journey with exit points
- Device-specific performance (mobile vs desktop)
- Traffic source behavior and conversion quality
- Session duration and engagement patterns
- Bounce rate analysis by source/campaign

**Combined with Ad Data**:
- Campaign performance correlated with website behavior
- Cost per quality visitor (not just clicks)
- Which ad targeting brings converters vs browsers
- Message match analysis between ads and landing pages

Your Brain API now provides **complete end-to-end analysis** - from ad impression to final conversion, with specific reasons for every drop-off and actionable fixes! 🚀







Here are the updated curl examples with automatic date detection for all ad insights endpoints:

  1. Ad Performance Analysis (with automatic dates)

  curl --location 'http://localhost:8000/ad-performance-analysis' \
  --form 'request="{
    \"user_id\": \"Martin\"
  }"'

  2. Campaign Comparison (with automatic dates)

  curl --location 'http://localhost:8000/campaign-comparison' \
  --form 'request="{
    \"user_id\": \"Martin\"
  }"'

  3. Ad Recommendations (with automatic dates)

  curl --location 'http://localhost:8000/ad-recommendations' \
  --form 'request="{
    \"user_id\": \"Martin\",
    \"min_spend\": 100
  }"'

  4. Performance Trends (with automatic dates)

  curl --location 'http://localhost:8000/performance-trends' \
  --form 'request="{
    \"user_id\": \"Martin\",
    \"metric\": \"ctr\"
  }"'

  5. Optimization Action Plan (with automatic dates)

  curl --location 'http://localhost:8000/optimization-action-plan' \
  --form 'request="{
    \"user_id\": \"Martin\",
    \"budget_increase_limit\": 50
  }"'

  6. Budget Reallocation Plan (with automatic dates)

  curl --location 'http://localhost:8000/budget-reallocation-plan' \
  --form 'request="{
    \"user_id\": \"Martin\",
    \"total_monthly_budget\": 15000
  }"'

  How the Automatic Date Detection Works:

  1. Default Range: Uses last 30 days from current date
  2. Data Availability Check: Tries to fetch sample data to verify data exists
  3. Fallback to 90 days: If no data in last 30 days, tries last 90 days
  4. Actual Data Range: Uses the actual date range where data exists
  5. Ultimate Fallback: Uses last 30 days even if no data found

  Response Includes Auto-Detection Info:

  All responses now include an auto_detected_dates field that shows true when dates were automatically determined:

  {
    "user_id": "Martin",
    "analysis_period": "2025-01-06 to 2025-02-05",
    "auto_detected_dates": true,
    "data_sources": ["meta_ads", "google_ads"],
    "total_records": 1247,
    ...
  }

  You can still override by providing specific dates:
  curl --location 'http://localhost:8000/ad-performance-analysis' \
  --form 'request="{
    \"user_id\": \"Martin\",
    \"start_date\": \"2025-01-01\",
    \"end_date\": \"2025-01-31\"
  }"'