# 🚀 One-Click Deploy - Marketing Analytics MCP Server

Deploy both FastAPI (OAuth) and MCP Server in **5 minutes** with a single command.

## 🎯 What Gets Deployed

✅ **FastAPI Server** (port 8000) - OAuth authentication & comprehensive insights API  
✅ **MCP Server** (port 8001) - Claude Desktop integration  
✅ **Automatic HTTPS** - SSL certificates managed automatically  
✅ **Global CDN** - Fast response times worldwide  
✅ **Auto-scaling** - Handles traffic spikes automatically  
✅ **Health monitoring** - Automatic restarts if needed  

## 🚀 One-Click Deploy

### Prerequisites (2 minutes)
1. **GitHub repo** - Push your code to GitHub (if not already done)
2. **API credentials** - Have your Google API credentials ready:
   - Google OAuth Client ID
   - Google OAuth Client Secret  
   - Google Ads Developer Token
   - GA4 Property ID (optional)

### Deploy Command (3 minutes)
```bash
./one-click-deploy.sh
```

That's it! The script will:
1. 🔍 Check/install DigitalOcean CLI
2. 🔐 Collect your API credentials securely
3. 📦 Create deployment configuration
4. 🚀 Deploy to DigitalOcean App Platform
5. 🧪 Test the deployment
6. 📋 Show you next steps

## 📋 What Happens During Deploy

```
╔══════════════════════════════════════════════════════════════╗
║  🔍 Checking requirements...                                ║
║  🔐 Collecting API credentials...                           ║
║  📦 Creating app specification...                           ║
║  🚀 Deploying to DigitalOcean App Platform...              ║
║  🧪 Testing deployment...                                   ║
║  ✅ DEPLOYMENT COMPLETE!                                    ║
╚══════════════════════════════════════════════════════════════╝
```

## 🌐 After Deployment

Your app will be live at:
```
FastAPI Server:    https://marketing-analytics-mcp.ondigitalocean.app
API Documentation: https://marketing-analytics-mcp.ondigitalocean.app/docs
Health Check:      https://marketing-analytics-mcp.ondigitalocean.app/health
MCP Endpoint:      https://marketing-analytics-mcp.ondigitalocean.app:8001
```

## 🔧 Complete OAuth Setup

1. **Get OAuth URL**:
   ```bash
   curl https://your-app.ondigitalocean.app/google-oauth/auth-url
   ```

2. **Open in browser** and complete Google OAuth flow

3. **Update Google Console** redirect URIs:
   ```
   https://your-app.ondigitalocean.app/google-oauth/callback
   ```

## 🤖 Configure Claude Desktop

Add to your Claude Desktop MCP configuration:
```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "python",
      "args": ["/path/to/remote_mcp_client.py"],
      "env": {
        "MCP_SERVER_URL": "https://your-app.ondigitalocean.app"
      }
    }
  }
}
```

## 🛠️ Management Commands

```bash
# View live logs
doctl apps logs <app-id> --follow

# Check app status  
doctl apps get <app-id>

# Update deployment
doctl apps update <app-id> --spec /tmp/app-spec.yaml

# Delete app
doctl apps delete <app-id>
```

## 💰 Cost

**$5/month** for basic plan (512MB RAM, 1 vCPU)
- Perfect for development and small-scale production
- Automatic scaling included
- SSL certificates included
- Global CDN included

## 🔧 Troubleshooting

### App won't start
```bash
doctl apps logs <app-id>
```

### OAuth redirect errors
- Verify redirect URI in Google Console matches your app URL
- Check environment variables are set correctly

### Both services running?
```bash
curl https://your-app.ondigitalocean.app/health  # FastAPI
curl https://your-app.ondigitalocean.app:8001    # MCP Server
```

## 🎯 Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│  Claude Desktop │    │  DigitalOcean App    │    │  Google APIs    │
│                 │    │ ┌──────────────────┐ │    │                 │
│  MCP Client     │───▶│ │ FastAPI :8000    │ │───▶│ • OAuth         │
│                 │    │ │ MCP Server :8001 │ │    │ • Google Ads    │
│                 │    │ │ (Supervisor)     │ │    │ • GA4           │
└─────────────────┘    │ └──────────────────┘ │    └─────────────────┘
                       │  Auto HTTPS + CDN    │
                       └──────────────────────┘
```

## 🚀 Ready to Deploy?

```bash
# Make sure you're in the brain directory
cd /Users/martinstolk/Projects/Mia/brain

# Run the one-click deploy
./one-click-deploy.sh
```

In 5 minutes, you'll have:
- ✅ Live FastAPI server with OAuth
- ✅ Live MCP server for Claude
- ✅ Global HTTPS deployment
- ✅ Auto-scaling and monitoring
- ✅ Professional production setup

**No Docker knowledge required. No server management. No DevOps complexity.**

Just run the script and start analyzing your marketing data with Claude! 🎉