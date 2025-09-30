/**
 * API utility for handling base URL configuration
 * Uses environment variable for production deployment
 */

// Get API base URL from environment variable with smart defaults
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname.includes('ondigitalocean.app')
    ? 'https://dolphin-app-b869e.ondigitalocean.app'
    : 'http://localhost:8002')

/**
 * Create a full API URL from a relative path
 * @param path - API path starting with /api/
 * @returns Full API URL
 */
export function createApiUrl(path: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  return `${API_BASE_URL}/${cleanPath}`
}

/**
 * Fetch wrapper that automatically uses the correct API base URL
 * @param path - API path (e.g., '/api/oauth/meta/auth-url')
 * @param options - Fetch options
 * @returns Promise<Response>
 */
export function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  return fetch(createApiUrl(path), options)
}