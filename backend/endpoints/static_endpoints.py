"""
Static Endpoints - HTML pages and health checks

Contains endpoints for serving static HTML content and system health checks.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "message": "MIA Marketing Intelligence Agent is running"}

@router.get("/")
async def root_health_check():
    """Root health check endpoint for DigitalOcean App Platform"""
    return {"status": "healthy", "message": "MIA Marketing Intelligence Agent is running", "service": "mia-backend"}

@router.get("/auth-test", response_class=HTMLResponse)
async def auth_test_page():
    """Simple auth test page for debugging authentication flow"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Auth Flow Test - Mia</title>
        <style>
            body { font-family: system-ui; padding: 20px; max-width: 600px; margin: 0 auto; }
            .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .authenticated { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .not-authenticated { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            pre { background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Auth Flow Test - Mia</h1>
            <p>Test the complete login/logout authentication cycle</p>
        </div>
        
        <div id="authStatus" class="status">Checking authentication...</div>
        
        <div>
            <button onclick="checkAuth()">🔄 Check Auth Status</button>
            <button onclick="login()">🚀 Start Login</button>
            <button onclick="logout()">🚪 Logout</button>
            <button onclick="forceLogout()">💥 Force Logout</button>
        </div>
        
        <h3>📋 Auth Response:</h3>
        <pre id="response">Click a button to see the response...</pre>
        
        <div style="margin-top: 20px; padding: 15px; background: #e9ecef; border-radius: 5px;">
            <h4>🧪 Testing Instructions:</h4>
            <ol>
                <li><strong>Check Auth Status</strong> - See current authentication state</li>
                <li><strong>Start Login</strong> - Opens Google OAuth popup window</li>
                <li><strong>Logout</strong> - Logs out locally (maintains MCP session)</li>
                <li><strong>Force Logout</strong> - Complete logout (clears everything)</li>
            </ol>
        </div>
        
        <script>
            let authData = null;
            
            async function checkAuth() {
                try {
                    const response = await fetch('/api/oauth/google/status');
                    authData = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(authData, null, 2);
                    updateAuthStatus();
                } catch (error) {
                    document.getElementById('response').textContent = 'Error: ' + error.message;
                }
            }
            
            async function login() {
                try {
                    const response = await fetch('/api/oauth/google/auth-url');
                    const data = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                    if (data.auth_url) {
                        const popup = window.open(data.auth_url, '_blank', 'width=500,height=600');
                        // Check if popup was blocked
                        if (!popup || popup.closed || typeof popup.closed == 'undefined') {
                            alert('Popup blocked! Please allow popups for this site.');
                        }
                    }
                } catch (error) {
                    document.getElementById('response').textContent = 'Login Error: ' + error.message;
                }
            }
            
            async function logout() {
                try {
                    const response = await fetch('/api/oauth/google/logout', { method: 'POST' });
                    const data = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                    setTimeout(checkAuth, 500);
                } catch (error) {
                    document.getElementById('response').textContent = 'Logout Error: ' + error.message;
                }
            }
            
            async function forceLogout() {
                try {
                    const response = await fetch('/api/oauth/google/force-logout', { method: 'POST' });
                    const data = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                    setTimeout(checkAuth, 500);
                } catch (error) {
                    document.getElementById('response').textContent = 'Force Logout Error: ' + error.message;
                }
            }
            
            function updateAuthStatus() {
                const statusDiv = document.getElementById('authStatus');
                if (authData && authData.authenticated) {
                    statusDiv.className = 'status authenticated';
                    statusDiv.innerHTML = `✅ <strong>Authenticated</strong><br>User: ${authData.user_info?.name || 'Unknown'}<br>Email: ${authData.user_info?.email || 'No email'}`;
                } else {
                    statusDiv.className = 'status not-authenticated';
                    statusDiv.innerHTML = `❌ <strong>Not Authenticated</strong><br>Reason: ${authData?.error || 'Unknown status'}`;
                }
            }
            
            // Check auth on page load
            checkAuth();
            
            // Listen for auth success messages from popup
            window.addEventListener('message', function(event) {
                if (event.data.auth === 'success') {
                    console.log('Auth success message received from popup');
                    setTimeout(checkAuth, 1000);
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/mia-chat-test", response_class=HTMLResponse)
async def mia_chat_test_page():
    """Serve the mobile test chat HTML page"""
    try:
        with open("mia-chat-test.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<html><body><h1>Test page not found</h1><p>mia-chat-test.html not found</p></body></html>",
            status_code=404
        )