# 🚀 Quick Deploy Guide - DigitalOcean App Platform

Deploy your Marketing Analytics MCP Server in under 10 minutes.

## Why DigitalOcean App Platform?

- ⚡ **Fastest setup** - No Docker knowledge needed
- 💰 **$5/month** starting cost
- 🔒 **Automatic SSL** certificates
- 📈 **Auto-scaling** included
- 🛠️ **Zero DevOps** required

## Step-by-Step Deployment

### 1. Prepare Your Repository

```bash
# Push your code to GitHub (if not already)
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2. Create DigitalOcean Account

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Sign up (get $200 credit with referral links)
3. Verify your account

### 3. Deploy Your App

1. **Click "Create App"**
2. **Connect GitHub repository**: `your-username/marketing-analytics-mcp`
3. **Configure the app**:
   ```yaml
   Name: marketing-analytics-mcp
   Region: New York (closest to you)
   Branch: main
   Source Directory: /
   ```

4. **Set Environment Variables**:
   ```env
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
   GA4_PROPERTY_ID=your_property_id
   PYTHONPATH=/app
   LOG_LEVEL=INFO
   ```

5. **Configure Build Settings**:
   ```
   Build Command: (leave empty - uses Dockerfile)
   Run Command: python start_mcp_server.py --host 0.0.0.0 --port 8080
   HTTP Port: 8080
   ```

6. **Click Deploy** 🚀

### 4. Complete OAuth Setup

Once deployed (5-10 minutes):

```bash
# Your app will be available at:
https://your-app-name.ondigitalocean.app

# Complete OAuth setup
curl https://your-app-name.ondigitalocean.app/google-oauth/auth-url
# Follow the browser flow
```

### 5. Configure Claude Desktop

Update your Claude Desktop config:
```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "docker",
      "args": [
        "run", "--rm", 
        "-e", "MCP_SERVER_URL=https://your-app-name.ondigitalocean.app",
        "marketing-analytics-mcp-client"
      ]
    }
  }
}
```

## Alternative: One-Click Deploy Button

I'll create a one-click deploy button for you:

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/your-username/marketing-analytics-mcp/tree/main)

## Cost Breakdown

### DigitalOcean Pricing
- **Basic Plan**: $5/month
  - 512MB RAM
  - 1 vCPU  
  - Good for development/small scale

- **Professional Plan**: $12/month
  - 1GB RAM
  - 1 vCPU
  - Good for production

### Google Cloud Run (Alternative)
- **Free Tier**: 2M requests/month
- **After free tier**: $0.40 per 1M requests
- **Memory**: $0.0000025 per GB-second

## Monitoring Your Deployment

### DigitalOcean Dashboard
1. Go to Apps dashboard
2. Click your app name
3. View:
   - Build logs
   - Runtime logs  
   - Metrics
   - Environment variables

### Health Checks
```bash
# Check if your app is running
curl https://your-app-name.ondigitalocean.app/health

# Test MCP endpoints
curl https://your-app-name.ondigitalocean.app/docs
```

## Scaling & Updates

### Auto-Scaling
DigitalOcean App Platform automatically scales based on:
- CPU usage
- Memory usage
- Request volume

### Updates
```bash
# Any push to main branch automatically deploys
git push origin main
```

## Troubleshooting

### Common Issues

1. **Build fails**
   - Check build logs in DigitalOcean dashboard
   - Verify Dockerfile syntax

2. **App crashes on startup**
   - Check runtime logs
   - Verify environment variables are set

3. **OAuth redirect errors**
   - Update Google Console redirect URIs to include:
     ```
     https://your-app-name.ondigitalocean.app/google-oauth/callback
     ```

### Debug Commands
```bash
# View app logs
doctl apps logs <app-id>

# Get app info
doctl apps get <app-id>

# Update environment variables
doctl apps update <app-id> --spec digitalocean-app.yaml
```

## Production Considerations

### Custom Domain
1. Add custom domain in DigitalOcean dashboard
2. Update DNS records
3. SSL certificate automatically provided

### Database
Add managed PostgreSQL:
```yaml
databases:
- name: marketing-analytics-db
  engine: PG
  version: "15"
  size: db-s-1vcpu-1gb
```

### Monitoring
Add monitoring services:
- Uptime monitoring
- Error tracking
- Performance monitoring

## Next Steps

1. ✅ **Deploy to DigitalOcean** (10 minutes)
2. ✅ **Complete OAuth setup** via browser
3. ✅ **Test with health endpoints**
4. ✅ **Configure Claude Desktop**
5. 🎉 **Start analyzing marketing data!**

Your Marketing Analytics MCP Server will be live and accessible globally in under 10 minutes! 🚀