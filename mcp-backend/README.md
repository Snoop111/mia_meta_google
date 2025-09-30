.# Brain - Enhanced AutoML API with External Data Integration

A FastAPI-based AutoML service that integrates data from Meta Ads, Google Ads, and Google Analytics 4 (GA4) to enhance your machine learning predictions.

## Features

- **AutoML Training**: Uses AutoGluon for automated machine learning
- **External Data Integration**: Pull data from Meta Ads, Google Ads, and GA4
- **Persistent Credential Storage**: Save credentials once, use across server restarts
- **User-based Credential Management**: Multiple users can have different data source credentials
- **Concurrent Data Fetching**: Async operations for fast data retrieval
- **SHAP Explanations**: Get feature importance and model explanations
- **EDA Reports**: Generate exploratory data analysis reports
- **Flexible Data Sources**: Use all or specific external data sources

## Installation

1. **Install core dependencies**:
```bash
pip install fastapi uvicorn pandas autogluon shap ydata-profiling
```

2. **Install external API dependencies**:
```bash
pip install -r requirements-data-apis.txt
```

## API Endpoints

### 🚀 Comprehensive Marketing Insights (NEW)

#### Unified Marketing Analytics Endpoint
```
POST /comprehensive-insights
```
**One endpoint that runs ALL 7 marketing analyses with maximum flexibility.**

**What it does**: Executes all available marketing analyses in a single API call, automatically adapting to whatever data you provide (CSV uploads, API credentials, or mixed).

**All 7 Analyses Included**:
1. **File Consolidation** - Combines uploaded CSV files
2. **Ad Performance Analysis** - Comprehensive platform performance  
3. **Campaign Comparison** - Side-by-side campaign rankings
4. **User Journey Analysis** - Funnel from ads to conversions
5. **Funnel Optimization** - Specific improvement recommendations
6. **Recommendations Engine** - Actionable optimization suggestions
7. **Action Plan Generator** - Step-by-step implementation guide

**Required Parameters**:
- `user_id` - Your user identifier
- `start_date` - Analysis start date (YYYY-MM-DD) *(optional - defaults to maximum available)*
- `end_date` - Analysis end date (YYYY-MM-DD) *(optional - defaults to maximum available)*

**Optional Parameters**:
- `ga4_file` - Google Analytics 4 CSV upload
- `meta_file` - Meta Ads CSV upload
- `google_file` - Google Ads CSV upload
- `use_api_data` - Use stored API credentials (default: false)
- `min_spend_threshold` - Minimum spend for recommendations (default: 100)
- `budget_increase_limit` - Max budget increase % (default: 50)
- `data_sources` - API sources to use (default: "meta_ads,google_ads")

**Usage Examples**:

*Upload files only:*
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-01-31" \
  -F "ga4_file=@analytics.csv" \
  -F "meta_file=@meta_ads.csv"
```

*Use API credentials only:*
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "use_api_data=true"
```

*Mixed sources:*
```bash
curl -X POST "http://localhost:8000/comprehensive-insights" \
  -F "user_id=123" \
  -F "meta_file=@meta_ads.csv" \
  -F "use_api_data=true" \
  -F "min_spend_threshold=200"
```

### Core Endpoints

#### 1. Basic Predict (Original)
```
POST /predict
```
Upload a CSV file and train a model without external data.

**Request**:
- `file`: CSV file upload
- `request`: JSON string with model configuration

**Example Request**:
```json
{
  "target": "sales",
  "id": "my_model_001"
}
```

#### 2. Enhanced Predict with External Data
```
POST /predict-with-external-data
```
Train a model with optional external data integration.

**Request**:
- `file`: CSV file upload
- `request`: JSON string with enhanced configuration

**Example Request**:
```json
{
  "target": "conversion_rate",
  "id": "enhanced_model_001",
  "use_external_data": true,
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "data_sources": ["meta_ads", "google_ads", "ga4"]
}
```

**Response**:
```json
{
  "predictions": [0.85, 0.72, 0.91, ...],
  "shap_summary": [0.12, 0.08, 0.15, ...],
  "data_shape": [100, 25],
  "external_data_used": true,
  "feature_columns": ["original_feature1", "impressions", "clicks", "sessions", ...]
}
```

### Data Source Management

#### 3. Configure Data Sources (with User)
```
POST /configure-data-sources
```
Set up credentials for external data sources with user association. Credentials are stored persistently.

**🔐 API Credentials Setup Guide**:

**Meta Ads Required Fields**:
- `access_token` - Meta Business access token
- `app_id` - Facebook App ID
- `app_secret` - Facebook App Secret  
- `ad_account_id` - Meta Ad Account ID

**Google Ads Required Fields**:
- `client_id` - Google OAuth client ID
- `client_secret` - Google OAuth client secret
- `refresh_token` - OAuth refresh token
- `developer_token` - Google Ads API developer token
- `customer_id` - Google Ads customer ID

**GA4 Required Fields**:
- `credentials_json` - Service account JSON (as string)
- `property_id` - GA4 property ID

**Example Request**:
```json
{
  "user_id": "martin",
  "credentials": {
    "meta_ads": {
      "access_token": "YOUR_META_ACCESS_TOKEN",
      "app_id": "YOUR_APP_ID",
      "app_secret": "YOUR_APP_SECRET",
      "ad_account_id": "YOUR_AD_ACCOUNT_ID"
    },
    "google_ads": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET",
      "refresh_token": "YOUR_REFRESH_TOKEN",
      "developer_token": "YOUR_DEVELOPER_TOKEN",
      "customer_id": "YOUR_CUSTOMER_ID"
    },
    "ga4": {
      "credentials_json": "YOUR_SERVICE_ACCOUNT_JSON_STRING",
      "property_id": "YOUR_GA4_PROPERTY_ID"
    }
  }
}
```

**cURL Example**:
```bash
curl --location 'http://localhost:8000/configure-data-sources' \
--header 'Content-Type: application/json' \
--data '{
  "user_id": "martin",
  "credentials": {
    "ga4": {
      "credentials_path": "/Users/martinstolk/Projects/brain/and1-signal-41ea5b72c066.json",
      "property_id": "318302899"
    }
  }
}'
```

#### 4. Load User Credentials
```
POST /load-user-credentials
```
Load stored credentials for a user. Automatically configures all data sources for the user.

**Example Request**:
```json
{
  "user_id": "martin"
}
```

**cURL Example**:
```bash
curl --location 'http://localhost:8000/load-user-credentials' \
--header 'Content-Type: application/json' \
--data '{"user_id": "martin"}'
```

#### 5. Predict with User Data
```
POST /predict-with-user-data
```
Train a model using a user's stored credentials for external data integration.

**cURL Example**:
```bash
curl --location 'http://localhost:8000/predict-with-user-data' \
--form 'request="{
  \"user_id\": \"martin\",
  \"target\": \"conversion_rate\",
  \"id\": \"enhanced_model_001\",
  \"use_external_data\": true,
  \"start_date\": \"2023-01-01\",
  \"end_date\": \"2025-07-31\",
  \"data_sources\": [\"ga4\"]
}"'
```

#### 6. Check Data Source Status
```
GET /data-sources/status
```
View the status of all configured data sources.

**Response**:
```json
{
  "available_connectors": ["meta_ads", "google_ads", "ga4"],
  "connector_status": {
    "meta_ads": true,
    "google_ads": true,
    "ga4": false
  }
}
```

#### 7. Get User's Data Sources
```
GET /users/{user_id}/data-sources
```
View all configured data sources for a specific user.

**Example**:
```bash
curl --location 'http://localhost:8000/users/martin/data-sources'
```

#### 8. Remove User's Data Source
```
DELETE /users/{user_id}/data-sources/{source_name}
```
Remove a specific data source for a user.

**Example**:
```bash
curl --location --request DELETE 'http://localhost:8000/users/martin/data-sources/ga4'
```

#### 9. Fetch External Data (Testing)
```
POST /fetch-external-data
```
Test data fetching without training a model.

**Request**:
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `data_sources`: Optional JSON array of source names

#### 10. Remove Data Source (Global)
```
DELETE /data-sources/{source_name}
```
Remove a configured data source from the active session.

### Other Endpoints

#### 11. EDA Report
```
POST /eda
```
Generate an exploratory data analysis report.

#### 12. Full Analysis
```
POST /analyze
```
Combine prediction, SHAP analysis, and EDA in one endpoint.

## Setting Up External Data Sources

### Meta Ads (Facebook)

1. **Create a Facebook App**:
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app and get your App ID and App Secret

2. **Get Access Token**:
   - Use Facebook's Graph API Explorer or generate via OAuth flow
   - Ensure the token has `ads_read` permission

3. **Find your Ad Account ID**:
   - Use Facebook Ads Manager or API to get your account ID
   - Format: `act_XXXXXXXXXX`

### Google Ads

1. **Enable Google Ads API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Ads API

2. **Get Developer Token**:
   - Apply for a developer token in your Google Ads account
   - Go to Tools & Settings > Setup > API Center

3. **Create OAuth2 Credentials**:
   - Create OAuth2 client ID and secret in Google Cloud Console
   - Generate refresh token using OAuth2 flow

4. **Find Customer ID**:
   - Located in your Google Ads account (format: XXX-XXX-XXXX)

### Google Analytics 4 (GA4)

1. **Create Service Account**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a service account and download JSON credentials

2. **Enable GA4 API**:
   - Enable the Google Analytics Data API in your project

3. **Grant Access**:
   - In GA4, add the service account email as a viewer
   - Get your GA4 Property ID from GA4 settings

4. **Store Credentials**:
   - Save the JSON file securely on your server
   - Use the file path in the API configuration

## Usage Examples

### Basic Workflow

1. **Start the server**:
```bash
uvicorn main:app --reload
```

2. **Configure data sources** (one-time setup):
```bash
# Set up GA4 credentials for user "martin"
curl --location 'http://localhost:8000/configure-data-sources' \
--header 'Content-Type: application/json' \
--data '{
  "user_id": "martin",
  "credentials": {
    "ga4": {
      "credentials_path": "/path/to/service_account.json",
      "property_id": "318302899"
    }
  }
}'
```

3. **Train model with user's stored credentials**:
```bash
# Use stored credentials to train model with external data
curl --location 'http://localhost:8000/predict-with-user-data' \
--form 'request="{
  \"user_id\": \"martin\",
  \"target\": \"conversion_rate\",
  \"id\": \"model_123\",
  \"use_external_data\": true,
  \"start_date\": \"2023-01-01\",
  \"end_date\": \"2025-07-31\",
  \"data_sources\": [\"ga4\"]
}"'
```

### Python Usage Examples

```python
import requests
import json

# 1. Configure credentials (one-time setup)
config_data = {
    "user_id": "martin",
    "credentials": {
        "meta_ads": {
            "access_token": "your_token",
            "app_id": "your_app_id",
            "app_secret": "your_secret"
        },
        "ga4": {
            "credentials_path": "/path/to/service_account.json",
            "property_id": "318302899"
        }
    }
}

response = requests.post("http://localhost:8000/configure-data-sources", json=config_data)
print("Credentials configured:", response.json())

# 2. Train model with user's data
files = {"file": open("your_data.csv", "rb")}
request_data = {
    "user_id": "martin",
    "target": "conversion_rate",
    "id": "model_123",
    "use_external_data": True,
    "start_date": "2025-01-01", 
    "end_date": "2025-01-31",
    "data_sources": ["meta_ads", "ga4"]
}

data = {"request": json.dumps(request_data)}
response = requests.post("http://localhost:8000/predict-with-user-data", files=files, data=data)
print("Predictions:", response.json())

# 3. Check user's configured data sources
response = requests.get("http://localhost:8000/users/martin/data-sources")
print("User's data sources:", response.json())
```

### Data Requirements

#### Your CSV Data
- Must include a `date` column for merging with external data
- Date format should be YYYY-MM-DD or convertible to datetime
- Target column must be specified in the request

#### External Data Integration
- External data is aggregated by date and merged with your dataset
- Missing external data values are filled with 0
- External columns get descriptive prefixes (e.g., `impressions`, `clicks_google_ads`)

### Advanced Configuration

#### Custom Data Source Configurations

You can pass specific configurations for each data source:

```python
request_data = {
    "target": "sales",
    "id": "advanced_model",
    "use_external_data": True,
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "connector_configs": {
        "meta_ads": {
            "account_id": "act_123456789",
            "fields": ["impressions", "clicks", "spend", "conversions"]
        },
        "google_ads": {
            "customer_id": "123-456-7890",
            "query": "SELECT segments.date, metrics.clicks FROM campaign WHERE segments.date BETWEEN '2025-01-01' AND '2025-01-31'"
        },
        "ga4": {
            "dimensions": ["date", "sessionDefaultChannelGrouping"],
            "metrics": ["sessions", "users", "conversions"]
        }
    }
}
```

## Error Handling

The API includes comprehensive error handling:

- **Missing Credentials**: Returns clear error messages for unconfigured data sources
- **API Failures**: Gracefully handles external API failures and continues with available data
- **Data Format Issues**: Validates data formats and provides helpful error messages
- **Rate Limiting**: Implements proper retry logic for API rate limits

## Performance Considerations

- **Concurrent Fetching**: External data sources are queried in parallel for faster response times
- **Data Caching**: Consider implementing caching for frequently requested date ranges
- **Memory Management**: Large datasets are processed efficiently with pandas
- **Model Storage**: Trained models are persisted for reuse

## Security Notes

- **Credential Storage**: Store API credentials securely, never in code
- **Access Control**: Implement proper authentication for production use
- **API Limits**: Monitor usage to stay within API quotas
- **Data Privacy**: Ensure compliance with data protection regulations

## Troubleshooting

### Common Issues

1. **"Package not installed" errors**:
   ```bash
   pip install facebook-business google-ads google-analytics-data
   ```

2. **"GA4 not found" errors**:
   - Use the new `/predict-with-user-data` endpoint instead of `/predict-with-external-data`
   - Ensure you've configured credentials with a user_id first
   - Load user credentials if connectors aren't active

3. **Authentication failures**:
   - Verify credentials are correct and have proper permissions
   - Check token expiration dates
   - Ensure service account has access to GA4 property

4. **No data returned**:
   - Verify date ranges have data in the external sources
   - Check account IDs and property IDs are correct
   - Review API quota limits

5. **Merge issues**:
   - Ensure your CSV has a `date` column
   - Check date format compatibility
   - Verify date ranges overlap with external data

6. **Credentials not persisting**:
   - Check that `credentials.db` file is created in your project directory
   - Ensure write permissions in the project folder
   - Verify user_id is consistent across requests

### Logs and Debugging

The application uses Python logging. Check console output for detailed error messages and API call status.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation for external services
3. Verify your credentials and permissions
4. Check server logs for detailed error information









MiaCreate API Key
AIzaSyCY9Zxe8MZ51VUMFggGfa70WSs3PBuB8ec
