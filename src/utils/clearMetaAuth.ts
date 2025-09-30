import { apiFetch } from '../utils/api'
/**
 * Utility to clear all Meta authentication data from browser storage
 */
export const clearMetaAuth = (): void => {
  try {
    // Clear Meta-specific localStorage items
    const metaKeys = [
      'meta_auth_status',
      'meta_user_info',
      'meta_access_token',
      'meta_session',
      'facebook_auth_status',
      'facebook_user_info'
    ]

    metaKeys.forEach(key => {
      localStorage.removeItem(key)
    })

    // Clear Meta-specific sessionStorage items
    metaKeys.forEach(key => {
      sessionStorage.removeItem(key)
    })

    // Clear any Meta-related cookies (if accessible)
    const metaCookies = [
      'meta_oauth_state',
      'facebook_oauth_state',
      'fb_auth'
    ]

    metaCookies.forEach(cookieName => {
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.facebook.com;`
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.meta.com;`
    })

  } catch (error) {
    console.error('[CLEAR-META] Error clearing Meta auth data:', error)
  }
}

/**
 * Clear Meta auth and call the server logout endpoint
 */
export const logoutMeta = async (sessionId?: string): Promise<void> => {
  try {
    // Clear browser storage first
    clearMetaAuth()

    // Call server logout endpoint
    const response = await apiFetch('/api/oauth/meta/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId || sessionStorage.getItem('session_id') || ''
      }
    })

    const result = await response.json()

  } catch (error) {
    console.error('[LOGOUT-META] Error during Meta logout:', error)
  }
}

/**
 * Check if there's any Meta auth data in browser storage
 */
export const hasMetaAuthData = (): boolean => {
  const metaKeys = [
    'meta_auth_status',
    'meta_user_info',
    'meta_access_token',
    'meta_session'
  ]

  return metaKeys.some(key =>
    localStorage.getItem(key) !== null || sessionStorage.getItem(key) !== null
  )
}