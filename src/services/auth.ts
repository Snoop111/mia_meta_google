import { GoogleAdsAccount, GA4Account, CombinedAccount } from './accountService'
import { apiFetch } from '../utils/api'

// Enhanced authentication service for MIA
export interface AuthUser {
  email: string
  isAuthenticated: boolean
  needsSetup?: boolean // First time user needs account setup
}

export interface UserSession {
  user: AuthUser
  selectedAccount?: GoogleAdsAccount | GA4Account | CombinedAccount
  hasCompletedSetup: boolean
}

class AuthService {
  private session: UserSession | null = null

  async login(): Promise<AuthUser | null> {
    try {
      // Step 1: Get auth URL
      const response = await apiFetch('/api/oauth/google/auth-url', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to get auth URL')
      }
      
      const data = await response.json()
      
      // Step 2: Store return URL and flag for OAuth flow
      const currentUrl = window.location.href
      localStorage.setItem('mia_oauth_pending', 'true')
      localStorage.setItem('mia_return_url', currentUrl)
      
      // Step 3: Use popup for all OAuth (mobile-friendly approach)
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
      
      // Force popup for testing - change to true
      if (true) {
        // Mobile: Use popup approach with MCP redirect
        return new Promise((resolve, reject) => {
          // Open popup window for OAuth (use original auth URL from MCP)
          const popup = window.open(
            data.auth_url,
            'google-oauth',
            'width=500,height=600,scrollbars=yes,resizable=yes'
          )
          
          if (!popup) {
            reject(new Error('Popup blocked. Please allow popups and try again.'))
            return
          }
          
          // Listen for popup completion
          const checkClosed = setInterval(() => {
            if (popup.closed) {
              clearInterval(checkClosed)
              // Check if auth was successful by polling our status
              setTimeout(() => {
                this.checkAuthStatus().then(isAuth => {
                  if (isAuth) {
                    resolve(null)
                  } else {
                    reject(new Error('Authentication was cancelled or failed'))
                  }
                })
              }, 2000) // Longer delay for MCP processing
            }
          }, 1000)
          
          // Listen for messages from popup (if MCP sends them)
          window.addEventListener('message', (event) => {
            if (event.data && event.data.auth === 'success') {
              popup.close()
              clearInterval(checkClosed)
              resolve(null)
            }
          }, { once: true })
        })
      }
      
      // Step 4: Desktop - redirect to Google OAuth
      window.location.href = data.auth_url
      
      return null // Will redirect, so no immediate return
    } catch (error) {
      console.error('Login error:', error)
      return null
    }
  }

  async logout(): Promise<void> {
    try {
      
      // Call new smart logout endpoint
      const response = await apiFetch('/api/oauth/google/logout', {
        method: 'POST',
        headers: {
          'X-Session-ID': this.getSessionId(), // Include session ID for proper tracking
        }
      })
      
      const result = await response.json()
      
      // Clear local session
      this.session = null
      localStorage.removeItem('mia_session')
      
    } catch (error) {
      console.error('Logout error:', error)
      // Always clear local session even on error
      this.session = null
      localStorage.removeItem('mia_session')
    }
  }

  async forceLogoutAndClearTokens(): Promise<void> {
    try {
      
      // Clear all local storage items related to auth
      localStorage.removeItem('mia_session')
      localStorage.removeItem('mia_oauth_pending')
      localStorage.removeItem('mia_return_url')
      
      // Clear session
      this.session = null
      
      // Call force logout endpoint for complete reset
      const response = await apiFetch('/api/oauth/google/force-logout', {
        method: 'POST',
        headers: {
          'X-Session-ID': this.getSessionId(),
        }
      })
      
      const result = await response.json()
      
    } catch (error) {
      console.error('Force logout error:', error)
      // Still clear local data on error
      localStorage.clear()
      this.session = null
    }
  }

  // Get or generate session ID for backend tracking
  private getSessionId(): string {
    let sessionId = localStorage.getItem('mia_session_id')
    if (!sessionId) {
      sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
      localStorage.setItem('mia_session_id', sessionId)
    }
    return sessionId
  }

  async checkAuthStatus(): Promise<AuthUser | null> {
    try {
      const response = await apiFetch('/api/oauth/google/status', {
        headers: {
          'X-Session-ID': this.getSessionId(), // Include session ID for backend tracking
        }
      })
      
      if (!response.ok) {
        return null
      }
      
      const data = await response.json()
      
      if (data.authenticated && data.user_info) {
        const user: AuthUser = {
          email: data.user_info.email,
          isAuthenticated: true,
          needsSetup: !this.hasCompletedSetup()
        }
        
        return user
      }
      
      return null
    } catch (error) {
      console.error('Auth status check error:', error)
      return null
    }
  }

  // Session management
  saveSession(session: UserSession): void {
    this.session = session
    localStorage.setItem('mia_session', JSON.stringify({
      selectedAccount: session.selectedAccount,
      hasCompletedSetup: session.hasCompletedSetup,
      userEmail: session.user.email
    }))
  }

  getSession(): UserSession | null {
    if (this.session) return this.session
    
    // Try to restore from localStorage
    const stored = localStorage.getItem('mia_session')
    if (stored) {
      try {
        const data = JSON.parse(stored)
        return {
          user: { 
            email: data.userEmail, 
            isAuthenticated: true,
            needsSetup: !data.hasCompletedSetup 
          },
          selectedAccount: data.selectedAccount,
          hasCompletedSetup: data.hasCompletedSetup
        }
      } catch (e) {
        localStorage.removeItem('mia_session')
      }
    }
    
    return null
  }

  hasCompletedSetup(): boolean {
    const session = this.getSession()
    return session?.hasCompletedSetup || false
  }

  completeSetup(account: GoogleAdsAccount | GA4Account | CombinedAccount, user: AuthUser): void {
    const session: UserSession = {
      user,
      selectedAccount: account,
      hasCompletedSetup: true
    }
    this.saveSession(session)
  }

  updateSelectedAccount(account: GoogleAdsAccount | GA4Account | CombinedAccount): void {
    if (this.session) {
      this.session.selectedAccount = account
      this.saveSession(this.session)
    }
  }
}

export const authService = new AuthService()
export default authService