
# Marketing Analytics MCP Server

A comprehensive Model Context Protocol (MCP) server that provides advanced marketing analytics capabilities across Google Ads, Google Analytics 4 (GA4), and Meta Ads platforms.

## Features

### 🎯 Comprehensive Analytics
- **Multi-platform support**: Google Ads, GA4, Meta Ads
- **Cross-platform insights**: User journey analysis, funnel optimization
- **Campaign performance analysis**: ROAS, CTR, conversion tracking
- **Automated recommendations**: Budget optimization, campaign restructuring

### 🔧 MCP Tools Available

#### 1. `comprehensive_insights`
Generates complete marketing analysis across multiple platforms with:
- Individual platform insights (Google Ads, GA4, Meta Ads)
- Cross-platform user journey analysis
- Funnel optimization recommendations
- Campaign performance scoring and restructuring advice

#### 2. `campaign_analysis`
Deep-dive analysis of specific campaigns with:
- Performance metrics breakdown
- Top/bottom performer identification
- Specific restructuring recommendations
- Budget allocation suggestions

#### 3. `setup_credentials`
Secure credential management for:
- Google Ads API access
- Google Analytics 4 API access
- Meta Ads API access
- OAuth token management

### 📊 Analysis Capabilities

#### Campaign Performance Analysis
- **ROAS Tracking**: Return on ad spend analysis with benchmarking
- **Cost Efficiency**: CPC, CPM, cost-per-conversion optimization
- **Engagement Metrics**: CTR, conversion rates, engagement quality
- **Performance Scoring**: Automated campaign health scoring

#### Cross-Platform Insights
- **User Journey Mapping**: Track users from ad click to conversion
- **Attribution Analysis**: Multi-touch attribution across platforms
- **Funnel Optimization**: Identify and fix conversion bottlenecks
- **Traffic Source Analysis**: Understand which channels drive quality traffic

#### Strategic Recommendations
- **Budget Reallocation**: Data-driven budget optimization suggestions
- **Campaign Restructuring**: Identify underperforming campaigns for overhaul
- **Scaling Opportunities**: Pinpoint high-ROAS campaigns ready for scaling
- **Creative Optimization**: Ad fatigue detection and refresh recommendations

## Installation

### Prerequisites
- Python 3.9+
- Google Ads API developer token
- Google Analytics 4 property access
- Meta Ads API access (optional)

### Setup

1. **Install the MCP server**:
```bash
cd /Users/martinstolk/Projects/Mia/brain
pip install -e .
```

2. **Set up environment variables**:
```bash
# Copy and customize the environment file
cp .env.example .env

# Required environment variables:
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"
export GOOGLE_ADS_DEVELOPER_TOKEN="your_google_ads_dev_token"
export GA4_PROPERTY_ID="your_ga4_property_id"
export META_APP_ID="your_meta_app_id"  # Optional
export META_APP_SECRET="your_meta_app_secret"  # Optional
```

3. **Initialize the database**:
```bash
python3 -c "from database import credential_storage; credential_storage._init_database()"
```

### Running the MCP Server

#### Standalone Mode
```bash
python3 mcp_server.py
```

#### As MCP Server (recommended)
The server will automatically start when called by an MCP client.

## Usage Examples

### Setting Up Credentials

Before running analysis, configure your API credentials:

```python
# Through MCP tool call
{
    "tool": "setup_credentials",
    "arguments": {
        "user_id": "your_user_id",
        "platform": "google_ads",
        "credentials": {
            "client_id": "your_client_id",
            "client_secret": "your_client_secret", 
            "refresh_token": "your_refresh_token",
            "developer_token": "your_developer_token"
        }
    }
}
```

### Running Comprehensive Analysis

```python
# Analyze multiple platforms
{
    "tool": "comprehensive_insights",
    "arguments": {
        "user_id": "your_user_id",
        "platforms": ["google_ads", "google_analytics"],
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "min_spend_threshold": 100,
        "budget_increase_limit": 50
    }
}
```

### Campaign-Specific Analysis

```python
# Analyze specific Google Ads campaigns
{
    "tool": "campaign_analysis", 
    "arguments": {
        "platform": "google_ads",
        "campaign_names": ["Campaign 1", "Campaign 2"],
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
}
```

## Integration with MCP Clients

### Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
    "mcp": {
        "servers": {
            "marketing-analytics": {
                "command": "python3",
                "args": ["/path/to/mcp_server.py"],
                "env": {
                    "GOOGLE_CLIENT_ID": "your_client_id",
                    "GOOGLE_CLIENT_SECRET": "your_client_secret",
                    "GOOGLE_ADS_DEVELOPER_TOKEN": "your_dev_token",
                    "GA4_PROPERTY_ID": "your_property_id"
                }
            }
        }
    }
}
```

### VS Code MCP Integration

Use with VS Code MCP extension by configuring the server endpoint.

### Custom MCP Client

```python
import asyncio
from mcp_client import Client

async def analyze_marketing_data():
    client = Client("marketing-analytics")
    
    # List available tools
    tools = await client.list_tools()
    print("Available tools:", [tool.name for tool in tools])
    
    # Run comprehensive analysis
    result = await client.call_tool(
        "comprehensive_insights",
        {
            "platforms": ["google_ads", "google_analytics"],
            "start_date": "2024-01-01", 
            "end_date": "2024-01-31"
        }
    )
    
    print("Analysis complete:", result)

asyncio.run(analyze_marketing_data())
```

## Output Examples

### Comprehensive Insights Report
```markdown
# Marketing Analytics Report

**Analysis Period:** 2024-01-01 to 2024-01-31
**Platforms Analyzed:** Google Ads, Google Analytics

## Google Ads Performance
### Key Metrics
- **Total Spend:** $1,464.02
- **Total Conversions:** 102.0
- **Overall ROAS:** 0.070x
- **Average CPC:** $3.62

### Campaign Performance
- **DFSA-DC-LEADS** 📈
  - Spend: $587.61 | Conversions: 95.0 | ROAS: 0.162x
- **DFSA-SC-LEADS-PROMO** 🚨
  - Spend: $876.40 | Conversions: 7.0 | ROAS: 0.008x

## Key Recommendations
- **[HIGH]** Review 2 campaigns with ROAS < 0.5
- **[URGENT]** Consider pausing DFSA-SC-LEADS-PROMO - negative ROI
- **[MEDIUM]** Optimize targeting for underperforming campaigns
```

### Campaign Analysis Report
```markdown
# Google Ads Campaign Analysis

## Campaign Performance Summary

### Overall Performance
- **Total Spend:** $1,464.02
- **Total Conversions:** 102.0
- **Overall ROAS:** 0.070x

### Individual Campaign Analysis

#### DFSA-DC-LEADS - 📈 PROFITABLE
- **Spend:** $587.61
- **Conversions:** 95.0
- **ROAS:** 0.162x
- **CTR:** 4.26%
- **📋 ACTION:** Reduce budget 50% and optimize targeting

#### DFSA-SC-LEADS-PROMO - 🚨 CRITICAL  
- **Spend:** $876.40
- **Conversions:** 7.0
- **ROAS:** 0.008x
- **CTR:** 8.99%
- **⚠️ URGENT:** Consider pausing immediately - negative ROI
```

## Architecture

### Core Components
- **MCP Server**: Main server handling MCP protocol communication
- **Analytics Engine**: Modular analytics system for different platforms
- **Credential Manager**: Secure API credential storage and management
- **Data Integrators**: Platform-specific data fetching and normalization

### Data Flow
1. **Credential Setup**: Securely store API credentials per user
2. **Data Fetching**: Async retrieval from Google Ads, GA4, Meta Ads APIs
3. **Data Processing**: Normalization and metric calculation
4. **Analysis Engine**: Performance analysis, recommendations, insights
5. **Response Formatting**: MCP-compatible response generation

### Security Features
- **Encrypted Storage**: API credentials encrypted at rest
- **User Isolation**: Per-user credential and data isolation
- **Token Management**: Automatic OAuth token refresh
- **Rate Limiting**: Built-in API rate limiting and retry logic

## Development

### Project Structure
```
brain/
├── mcp_server.py              # Main MCP server
├── analytics/                 # Analysis modules
│   ├── ad_performance.py      # Ad performance analysis
│   ├── journey_analyzer.py    # User journey analysis  
│   ├── funnel_optimizer.py    # Conversion funnel optimization
│   └── recommendation_engine.py # Recommendation generation
├── routes/                    # API route handlers
├── database.py                # Database models and storage
├── credential_manager.py      # API credential management
└── shared_integrator.py       # Data integration layer
```

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=./ --cov-report=html
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint
flake8 .

# Type checking  
mypy .
```

## API Reference

### Tools

#### comprehensive_insights
**Parameters:**
- `user_id` (string): User identifier for credential management
- `platforms` (array): Platforms to analyze ["google_ads", "google_analytics", "facebook"]
- `start_date` (string): Start date in YYYY-MM-DD format
- `end_date` (string): End date in YYYY-MM-DD format  
- `min_spend_threshold` (number): Minimum spend for analysis inclusion
- `budget_increase_limit` (number): Maximum budget increase percentage

**Returns:** Comprehensive marketing analysis with individual platform insights, cross-platform analysis, and recommendations.

#### campaign_analysis  
**Parameters:**
- `user_id` (string): User identifier
- `platform` (string): Platform to analyze ["google_ads", "facebook"]
- `campaign_names` (array): Specific campaigns to analyze (optional)
- `start_date` (string): Analysis start date
- `end_date` (string): Analysis end date

**Returns:** Detailed campaign performance analysis with restructuring recommendations.

#### setup_credentials
**Parameters:**
- `user_id` (string): User identifier  
- `platform` (string): Platform for credentials ["google_ads", "ga4", "meta_ads"]
- `credentials` (object): Platform-specific credential configuration

**Returns:** Confirmation of successful credential setup.

## Support

### Troubleshooting

**Common Issues:**
1. **API Authentication Errors**: Verify API credentials and token validity
2. **Data Not Found**: Check date ranges and platform configuration
3. **Rate Limiting**: Built-in retry logic should handle this automatically
4. **Memory Issues**: Large datasets are processed in chunks

**Logging:**
Enable debug logging for detailed troubleshooting:
```bash
export LOG_LEVEL=DEBUG
python3 mcp_server.py
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run code quality checks  
5. Submit a pull request

## License

MIT License - see LICENSE file for details.