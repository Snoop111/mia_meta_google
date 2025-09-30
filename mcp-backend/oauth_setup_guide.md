# Complete OAuth + MCP Setup Guide

## Phase 1: One-Time OAuth Setup via Browser

### Step 1: Start Your FastAPI Server
```bash
cd /Users/martinstolk/Projects/Mia/brain
source venv/bin/activate  # if using venv
uvicorn main:app --reload --port 8000
```

Your FastAPI server will be running at `http://localhost:8000` with these OAuth endpoints:
- `GET /google-oauth/auth-url` - Generate OAuth URL
- `POST /google-oauth/exchange-token` - Exchange code for tokens
- `GET /google-oauth/callback` - Handle OAuth callback
- `GET /google-oauth/user-info` - Get current user info

### Step 2: Configure Google Cloud Console

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**

2. **Create or Select Project**
   - Create new project or select existing one
   - Note your project ID

3. **Enable Required APIs**
   ```
   Google Ads API
   Google Analytics Reporting API  
   Google Analytics Data API (GA4)
   ```

4. **Create OAuth 2.0 Credentials**
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > OAuth 2.0 Client ID
   - Application type: Web application
   - Name: "Marketing Analytics MCP"
   - Authorized redirect URIs:
     ```
     http://localhost:8000/google-oauth/callback
     http://localhost:5173/oauth/callback  (for frontend)
     ```
   - Download the client configuration JSON

5. **Get Google Ads Developer Token**
   - Go to [Google Ads API Center](https://developers.google.com/google-ads/api)
   - Apply for developer token (may take 1-2 days for approval)

### Step 3: Set Environment Variables
```bash
# Create .env file in your brain directory
cat > .env << EOF
GOOGLE_CLIENT_ID="your_client_id_from_step_4"
GOOGLE_CLIENT_SECRET="your_client_secret_from_step_4"
GOOGLE_ADS_DEVELOPER_TOKEN="your_developer_token_from_step_5"
GA4_PROPERTY_ID="your_ga4_property_id"
GOOGLE_REDIRECT_URI="http://localhost:8000/google-oauth/callback"
FRONTEND_URL="http://localhost:5173"
EOF
```

### Step 4: Perform OAuth Flow

1. **Get Authorization URL**
   ```bash
   curl http://localhost:8000/google-oauth/auth-url
   ```
   
   Response:
   ```json
   {
     "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
     "state": "random_state_string"
   }
   ```

2. **Open URL in Browser**
   - Copy the `auth_url` and open in browser
   - Sign in with your Google account
   - Grant permissions for:
     - Google Ads access
     - Google Analytics access
   - You'll be redirected to `http://localhost:8000/google-oauth/callback?code=...`

3. **Verify Credentials Are Stored**
   ```bash
   curl http://localhost:8000/google-oauth/user-info
   ```
   
   Should return your Google user info if successful.

### Step 5: Test Data Access
```bash
# Test comprehensive insights endpoint
curl -X POST http://localhost:8000/comprehensive-insights \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "current_user",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31", 
    "min_spend_threshold": 100,
    "budget_increase_limit": 50,
    "data_selections": [
      {
        "platform": "google_ads",
        "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
      },
      {
        "platform": "google_analytics", 
        "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
      }
    ]
  }'
```

## Phase 2: MCP Server Setup

### Step 1: Install MCP Dependencies
```bash
source venv/bin/activate
./setup_mcp_venv.sh
```

### Step 2: Test MCP Server
```bash
python test_mcp_server.py
```

Expected output:
```
✅ All tests passed! Your MCP server is ready to use.
```

### Step 3: Configure Claude Desktop

1. **Create Claude Desktop MCP Config**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add MCP Server Configuration**
   ```json
   {
     "mcpServers": {
       "marketing-analytics": {
         "command": "/Users/martinstolk/Projects/Mia/brain/venv/bin/python",
         "args": ["/Users/martinstolk/Projects/Mia/brain/mcp_server.py"],
         "env": {
           "GOOGLE_CLIENT_ID": "your_client_id",
           "GOOGLE_CLIENT_SECRET": "your_client_secret",
           "GOOGLE_ADS_DEVELOPER_TOKEN": "your_developer_token",
           "GA4_PROPERTY_ID": "your_property_id",
           "PYTHONPATH": "/Users/martinstolk/Projects/Mia/brain"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

## Phase 3: Using MCP with Claude

### Available MCP Tools

1. **comprehensive_insights**
   ```
   Please analyze my marketing performance for the last 30 days across Google Ads and GA4
   ```

2. **campaign_analysis**  
   ```
   Please analyze my Google Ads campaigns and tell me which ones need restructuring
   ```

3. **setup_credentials** (if needed)
   ```
   Help me configure additional API credentials for Meta Ads
   ```

### Example Claude Conversation

**You:** "Analyze my marketing performance for January 2024"

**Claude with MCP:** 
```
I'll analyze your marketing performance using the comprehensive insights tool.

[Tool: comprehensive_insights]
- Analyzing Google Ads and GA4 data
- Date range: January 1-31, 2024
- Platforms: Google Ads, Google Analytics

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
- **DFSA-DC-LEADS** 📈 PROFITABLE
  - Spend: $587.61 | Conversions: 95.0 | ROAS: 0.162x
- **DFSA-SC-LEADS-PROMO** 🚨 CRITICAL
  - Spend: $876.40 | Conversions: 7.0 | ROAS: 0.008x

## Key Recommendations
- **[URGENT]** Consider pausing DFSA-SC-LEADS-PROMO - negative ROI
- **[HIGH]** Scale DFSA-DC-LEADS campaign with 20% budget increase
- **[MEDIUM]** Improve targeting for underperforming campaigns
```

## Credential Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│   Browser       │    │  FastAPI Server  │    │   MCP Server    │
│   (One-time     │    │  (OAuth Handler) │    │   (Analytics)   │
│    OAuth)       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. GET /auth-url      │                       │
         │<─────────────────────▶│                       │
         │                       │                       │
         │ 2. Browser OAuth      │                       │
         │   + Callback          │                       │
         │<─────────────────────▶│                       │
         │                       │                       │
         │                       │ 3. Store credentials  │
         │                       │   in SQLite           │
         │                       │<─────────────────────▶│
         │                       │                       │
         │                       │ 4. MCP uses stored    │
         │                       │   credentials         │
         │                       │<─────────────────────▶│
```

## Security Features

1. **Credential Storage**
   - Encrypted SQLite database
   - User-isolated credential storage
   - Automatic token refresh

2. **OAuth Scopes**
   ```python
   SCOPES = [
       'openid',
       'https://www.googleapis.com/auth/adwords',
       'https://www.googleapis.com/auth/analytics.readonly',
       'https://www.googleapis.com/auth/userinfo.email',
       'https://www.googleapis.com/auth/userinfo.profile'
   ]
   ```

3. **MCP Isolation**
   - MCP server runs in isolated process
   - No direct browser access
   - Credentials loaded from secure storage

## Troubleshooting

### Common Issues

1. **"Invalid credentials" error in MCP**
   ```bash
   # Re-run OAuth flow
   curl http://localhost:8000/google-oauth/auth-url
   # Follow browser flow again
   ```

2. **"No module named 'mcp'" error**
   ```bash
   source venv/bin/activate
   pip install mcp
   ```

3. **Claude Desktop not finding MCP server**
   - Check file paths in `claude_desktop_config.json`
   - Ensure venv python path is correct
   - Restart Claude Desktop

4. **API quota exceeded**
   - Check Google Cloud Console quotas
   - Implement request caching if needed

### Verification Commands

```bash
# Check if OAuth worked
curl http://localhost:8000/google-oauth/user-info

# Test comprehensive insights
curl -X POST http://localhost:8000/comprehensive-insights -H "Content-Type: application/json" -d '{...}'

# Test MCP server
python test_mcp_server.py

# Check Claude Desktop logs (macOS)
tail -f ~/Library/Logs/Claude/claude_desktop.log
```

## Next Steps

1. **Complete Phase 1** - OAuth setup via browser
2. **Complete Phase 2** - MCP server configuration  
3. **Complete Phase 3** - Use with Claude Desktop
4. **Optional**: Set up additional platforms (Meta Ads, etc.)
5. **Optional**: Create custom MCP clients for other applications

The beauty of this approach is:
- ✅ OAuth happens once via familiar browser flow
- ✅ Credentials are securely stored
- ✅ MCP server uses stored credentials automatically
- ✅ No complex OAuth handling in MCP client
- ✅ Works with any MCP client (Claude Desktop, VS Code, custom clients)