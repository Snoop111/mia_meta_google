interface MetaUserInfo {
  id: string
  name: string
  email?: string
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'

class MetaAuthService {
  private isAuthenticated: boolean = false
  private userInfo: MetaUserInfo | null = null

  constructor() {
    this.checkAuthStatus()
  }

  async getAuthUrl(): Promise<string> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/oauth/meta/auth-url`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionStorage.getItem('session_id') || ''
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to get Meta auth URL: ${response.status}`)
      }

      const data = await response.json()
      return data.auth_url
    } catch (error) {
      console.error('Error getting Meta auth URL:', error)
      throw new Error('Failed to get Meta authorization URL')
    }
  }

  async exchangeCodeForTokens(code: string): Promise<void> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/oauth/meta/exchange-token`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          },
          body: JSON.stringify({ code })
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to exchange code for tokens: ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        this.isAuthenticated = true
        this.userInfo = data.user_info
        localStorage.setItem('meta_auth_status', 'authenticated')
        localStorage.setItem('meta_user_info', JSON.stringify(this.userInfo))
      }
    } catch (error) {
      console.error('Error exchanging code for Meta tokens:', error)
      throw new Error('Failed to authenticate with Meta')
    }
  }

  async getUserInfo(): Promise<MetaUserInfo | null> {
    if (this.userInfo) {
      return this.userInfo
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/oauth/meta/user-info`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionStorage.getItem('session_id') || ''
        }
      })

      if (!response.ok) {
        this.logout()
        return null
      }

      const data = await response.json()
      if (data.authenticated) {
        this.userInfo = data.user_info
        this.isAuthenticated = true
        localStorage.setItem('meta_auth_status', 'authenticated')
        localStorage.setItem('meta_user_info', JSON.stringify(this.userInfo))
        return this.userInfo
      }
    } catch (error) {
      console.error('Error fetching Meta user info:', error)
      this.logout()
    }

    return null
  }

  isUserAuthenticated(): boolean {
    return this.isAuthenticated
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/api/oauth/meta/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionStorage.getItem('session_id') || ''
        }
      })
    } catch (error) {
      console.error('Error during Meta logout:', error)
    } finally {
      this.isAuthenticated = false
      this.userInfo = null
      localStorage.removeItem('meta_auth_status')
      localStorage.removeItem('meta_user_info')
    }
  }

  private async checkAuthStatus(): Promise<void> {
    const authStatus = localStorage.getItem('meta_auth_status')
    const userInfoStr = localStorage.getItem('meta_user_info')

    if (authStatus === 'authenticated' && userInfoStr) {
      try {
        // Verify with backend that we're still authenticated
        const response = await fetch(`${API_BASE_URL}/api/oauth/meta/user-info`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          }
        })

        if (response.ok) {
          const data = await response.json()
          if (data.authenticated) {
            this.isAuthenticated = true
            this.userInfo = data.user_info
          } else {
            this.logout()
          }
        } else {
          this.logout()
        }
      } catch {
        this.logout()
      }
    }
  }
}

export const metaAuthService = new MetaAuthService()
export type { MetaUserInfo }