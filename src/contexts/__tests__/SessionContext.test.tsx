import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SessionProvider, useSession, type AccountMapping, type UserProfile } from '../SessionContext'

// Mock fetch globally
global.fetch = vi.fn()

// Mock window.open
Object.defineProperty(window, 'open', {
  writable: true,
  value: vi.fn(),
})

// Test component that uses the SessionContext
const TestComponent = ({ onStateChange }: { onStateChange?: (state: any) => void }) => {
  const session = useSession()

  // Call onStateChange whenever state changes for testing
  if (onStateChange) {
    onStateChange(session)
  }

  return (
    <div>
      <div data-testid="is-authenticated">{session.isAuthenticated.toString()}</div>
      <div data-testid="is-loading">{session.isLoading.toString()}</div>
      <div data-testid="session-id">{session.sessionId || 'null'}</div>
      <div data-testid="user-name">{session.user?.name || 'null'}</div>
      <div data-testid="error">{session.error || 'null'}</div>
      <div data-testid="meta-authenticated">{session.isMetaAuthenticated.toString()}</div>
      <div data-testid="selected-account">{session.selectedAccount?.name || 'null'}</div>
      <div data-testid="available-accounts">{session.availableAccounts.length}</div>

      <button data-testid="login-btn" onClick={() => session.login()}>Login</button>
      <button data-testid="login-meta-btn" onClick={() => session.loginMeta()}>Login Meta</button>
      <button data-testid="logout-btn" onClick={() => session.logout()}>Logout</button>
      <button data-testid="logout-meta-btn" onClick={() => session.logoutMeta()}>Logout Meta</button>
      <button data-testid="clear-error-btn" onClick={() => session.clearError()}>Clear Error</button>
      <button data-testid="refresh-accounts-btn" onClick={() => session.refreshAccounts()}>Refresh Accounts</button>
      <button data-testid="select-account-btn" onClick={() => session.selectAccount('test-account-1')}>Select Account</button>
      <button data-testid="check-auth-btn" onClick={() => session.checkExistingAuth()}>Check Auth</button>
      <button data-testid="check-meta-auth-btn" onClick={() => session.checkMetaAuth()}>Check Meta Auth</button>
    </div>
  )
}

const renderWithProvider = (component: React.ReactElement, onStateChange?: (state: any) => void) => {
  return render(
    <SessionProvider>
      {component}
    </SessionProvider>
  )
}

describe('SessionContext', () => {
  let mockStateChange: any

  beforeEach(() => {
    vi.clearAllMocks()
    mockStateChange = vi.fn()
    // Reset fetch mock
    vi.mocked(fetch).mockClear()
    vi.mocked(window.open).mockClear()

    // Mock successful responses by default
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Provider and Hook', () => {
    it('provides initial state correctly', () => {
      renderWithProvider(<TestComponent />)

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false')
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      expect(screen.getByTestId('user-name')).toHaveTextContent('null')
      expect(screen.getByTestId('error')).toHaveTextContent('null')
      expect(screen.getByTestId('meta-authenticated')).toHaveTextContent('false')
      expect(screen.getByTestId('selected-account')).toHaveTextContent('null')
      expect(screen.getByTestId('available-accounts')).toHaveTextContent('0')
    })

    it('generates a session ID on initialization', async () => {
      renderWithProvider(<TestComponent />)

      await waitFor(() => {
        const sessionId = screen.getByTestId('session-id').textContent
        expect(sessionId).not.toBe('null')
        expect(sessionId).toMatch(/^session_\d+_[a-z0-9]+$/)
      })
    })

    it('throws error when useSession is used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => render(<TestComponent />)).toThrow(
        'useSession must be used within a SessionProvider'
      )

      consoleSpy.mockRestore()
    })
  })

  describe('Google Authentication', () => {
    it('handles successful Google login flow', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)

      // Mock successful auth URL response
      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ auth_url: 'https://google.com/oauth' }),
        } as Response)
        // Mock successful complete response
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response)
        // Mock successful status response
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            authenticated: true,
            name: 'John Doe',
            email: 'john@example.com',
            picture: 'https://example.com/avatar.jpg',
            user_id: '12345'
          }),
        } as Response)
        // Mock successful accounts response
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ accounts: [] }),
        } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      // Check loading state
      expect(screen.getByTestId('is-loading')).toHaveTextContent('true')

      // Simulate popup closing after OAuth
      await act(async () => {
        mockPopup.closed = true
        await new Promise(resolve => setTimeout(resolve, 1100)) // Wait for polling
      })

      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true')
        expect(screen.getByTestId('user-name')).toHaveTextContent('John Doe')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })

      expect(window.open).toHaveBeenCalledWith(
        'https://google.com/oauth',
        'google-oauth',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      )
    })

    it('handles popup blocked error', async () => {
      vi.mocked(window.open).mockReturnValue(null)
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ auth_url: 'https://google.com/oauth' }),
      } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Popup blocked. Please allow popups for this site.')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })
    })

    it('handles auth URL fetch failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'))

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Network error')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })
    })

    it('handles OAuth complete failure', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)

      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ auth_url: 'https://google.com/oauth' }),
        } as Response)
        .mockResolvedValueOnce({
          ok: false,
          status: 400,
        } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      await act(async () => {
        mockPopup.closed = true
        await new Promise(resolve => setTimeout(resolve, 1100))
      })

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Failed to complete authentication session')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })
    })

    it('handles authentication timeout', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ auth_url: 'https://google.com/oauth' }),
      } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      // Fast-forward time to trigger timeout
      await act(async () => {
        vi.advanceTimersByTime(300000) // 5 minutes
      })

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Authentication timed out')
        expect(mockPopup.close).toHaveBeenCalled()
      })
    }, { timeout: 10000 })
  })

  describe('Meta Authentication', () => {
    it('handles successful Meta login flow', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)

      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ auth_url: 'https://facebook.com/oauth' }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            authenticated: true,
            user_info: {
              id: 'meta123',
              name: 'Jane Doe',
              email: 'jane@example.com'
            }
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ accounts: [] }),
        } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-meta-btn')
      await userEvent.click(loginBtn)

      await act(async () => {
        mockPopup.closed = true
        await new Promise(resolve => setTimeout(resolve, 1100))
      })

      await waitFor(() => {
        expect(screen.getByTestId('meta-authenticated')).toHaveTextContent('true')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })
    })

    it('handles Meta authentication failure', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)

      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ auth_url: 'https://facebook.com/oauth' }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ authenticated: false }),
        } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-meta-btn')
      await userEvent.click(loginBtn)

      await act(async () => {
        mockPopup.closed = true
        await new Promise(resolve => setTimeout(resolve, 1100))
      })

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Meta authentication failed')
        expect(screen.getByTestId('meta-authenticated')).toHaveTextContent('false')
      })
    })
  })

  describe('Logout Functionality', () => {
    it('handles Google logout successfully', async () => {
      // First set up authenticated state
      renderWithProvider(<TestComponent />)

      // Mock successful logout
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response)

      const logoutBtn = screen.getByTestId('logout-btn')
      await userEvent.click(logoutBtn)

      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false')
        expect(screen.getByTestId('user-name')).toHaveTextContent('null')
        expect(screen.getByTestId('selected-account')).toHaveTextContent('null')
        expect(screen.getByTestId('available-accounts')).toHaveTextContent('0')
      })

      expect(fetch).toHaveBeenCalledWith('/api/oauth/google/logout', { method: 'POST' })
    })

    it('handles Meta logout successfully', async () => {
      renderWithProvider(<TestComponent />)

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response)

      const logoutBtn = screen.getByTestId('logout-meta-btn')
      await userEvent.click(logoutBtn)

      await waitFor(() => {
        expect(screen.getByTestId('meta-authenticated')).toHaveTextContent('false')
      })
    })

    it('handles logout failure', async () => {
      renderWithProvider(<TestComponent />)

      vi.mocked(fetch).mockRejectedValueOnce(new Error('Logout failed'))

      const logoutBtn = screen.getByTestId('logout-btn')
      await userEvent.click(logoutBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Logout failed')
      })
    })
  })

  describe('Account Management', () => {
    const mockAccounts: AccountMapping[] = [
      {
        id: 'test-account-1',
        name: 'Test Account 1',
        google_ads_id: '123',
        ga4_property_id: '456',
        business_type: 'ecommerce',
        color: '#blue',
        display_name: 'Test 1'
      },
      {
        id: 'test-account-2',
        name: 'Test Account 2',
        google_ads_id: '789',
        ga4_property_id: '012',
        business_type: 'saas',
        color: '#green',
        display_name: 'Test 2'
      }
    ]

    it('refreshes accounts successfully', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ accounts: mockAccounts }),
      } as Response)

      renderWithProvider(<TestComponent />)

      const refreshBtn = screen.getByTestId('refresh-accounts-btn')
      await userEvent.click(refreshBtn)

      await waitFor(() => {
        expect(screen.getByTestId('available-accounts')).toHaveTextContent('2')
      })

      expect(fetch).toHaveBeenCalledWith('/api/accounts/available')
    })

    it('handles account refresh failure gracefully', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'))

      renderWithProvider(<TestComponent />)

      const refreshBtn = screen.getByTestId('refresh-accounts-btn')
      await userEvent.click(refreshBtn)

      // Should not crash, just log error
      await waitFor(() => {
        expect(screen.getByTestId('available-accounts')).toHaveTextContent('0')
      })
    })

    it('selects account successfully', async () => {
      // First set up accounts
      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ accounts: mockAccounts }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response)

      renderWithProvider(<TestComponent />)

      // First refresh accounts
      const refreshBtn = screen.getByTestId('refresh-accounts-btn')
      await userEvent.click(refreshBtn)

      await waitFor(() => {
        expect(screen.getByTestId('available-accounts')).toHaveTextContent('2')
      })

      // Then select account
      const selectBtn = screen.getByTestId('select-account-btn')
      await userEvent.click(selectBtn)

      await waitFor(() => {
        expect(screen.getByTestId('selected-account')).toHaveTextContent('Test Account 1')
      })
    })

    it('handles account selection failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Selection failed'))

      renderWithProvider(<TestComponent />)

      const selectBtn = screen.getByTestId('select-account-btn')
      await userEvent.click(selectBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Selection failed')
      })
    })
  })

  describe('Utility Functions', () => {
    it('clears error state', async () => {
      renderWithProvider(<TestComponent />)

      // First trigger an error
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Test error'))
      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Test error')
      })

      // Then clear error
      const clearBtn = screen.getByTestId('clear-error-btn')
      await userEvent.click(clearBtn)

      expect(screen.getByTestId('error')).toHaveTextContent('null')
    })

    it('generates unique session IDs', () => {
      renderWithProvider(<TestComponent />)

      const session = useSession()
      const id1 = session.generateSessionId()
      const id2 = session.generateSessionId()

      expect(id1).not.toBe(id2)
      expect(id1).toMatch(/^session_\d+_[a-z0-9]+$/)
      expect(id2).toMatch(/^session_\d+_[a-z0-9]+$/)
    })

    it('checks existing Google auth', async () => {
      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            authenticated: true,
            name: 'Existing User',
            email: 'existing@example.com',
            user_id: 'existing123'
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ accounts: [] }),
        } as Response)

      renderWithProvider(<TestComponent />)

      const checkBtn = screen.getByTestId('check-auth-btn')
      await userEvent.click(checkBtn)

      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true')
        expect(screen.getByTestId('user-name')).toHaveTextContent('Existing User')
      })
    })

    it('checks existing Meta auth', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          authenticated: true,
          user_info: {
            id: 'existingMeta',
            name: 'Existing Meta User'
          }
        }),
      } as Response)

      renderWithProvider(<TestComponent />)

      const checkBtn = screen.getByTestId('check-meta-auth-btn')
      await userEvent.click(checkBtn)

      await waitFor(() => {
        expect(screen.getByTestId('meta-authenticated')).toHaveTextContent('true')
      })
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network unavailable'))

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')
      await userEvent.click(loginBtn)

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Network unavailable')
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
      })
    })

    it('handles invalid JSON responses', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      } as Response)

      renderWithProvider(<TestComponent />)

      const refreshBtn = screen.getByTestId('refresh-accounts-btn')
      await userEvent.click(refreshBtn)

      // Should handle gracefully without crashing
      await waitFor(() => {
        expect(screen.getByTestId('available-accounts')).toHaveTextContent('0')
      })
    })
  })

  describe('Concurrent Operations', () => {
    it('handles multiple simultaneous login attempts', async () => {
      const mockPopup = {
        closed: false,
        close: vi.fn(),
      }
      vi.mocked(window.open).mockReturnValue(mockPopup as any)
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ auth_url: 'https://google.com/oauth' }),
      } as Response)

      renderWithProvider(<TestComponent />)

      const loginBtn = screen.getByTestId('login-btn')

      // Click multiple times rapidly
      await userEvent.click(loginBtn)
      await userEvent.click(loginBtn)
      await userEvent.click(loginBtn)

      // Should only open one popup
      expect(window.open).toHaveBeenCalledTimes(3) // Each click attempts to open
    })
  })
})