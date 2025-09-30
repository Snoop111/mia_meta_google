import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FigmaLoginModal from '../FigmaLoginModal'
import { useSession } from '../../contexts/SessionContext'

// Mock fetch globally
global.fetch = vi.fn()

// Mock the useSession hook
const mockSessionContext = {
  login: vi.fn(),
  loginMeta: vi.fn(),
  isLoading: false,
  error: null,
  sessionId: 'test-session-id',
  checkExistingAuth: vi.fn(),
  refreshAccounts: vi.fn(),
  isAuthenticated: false,
  user: null,
  selectedAccount: null,
  availableAccounts: [],
  isMetaAuthenticated: false,
  metaUser: null,
  logout: vi.fn(),
  selectAccount: vi.fn(),
  clearError: vi.fn(),
  generateSessionId: vi.fn(),
  checkMetaAuth: vi.fn(),
  logoutMeta: vi.fn(),
}

vi.mock('../../contexts/SessionContext', () => ({
  useSession: vi.fn(),
}))

const renderWithSessionContext = (
  component: React.ReactElement,
  contextOverrides = {}
) => {
  const contextValue = { ...mockSessionContext, ...contextOverrides }
  vi.mocked(useSession).mockReturnValue(contextValue)
  return render(component)
}

describe('FigmaLoginModal', () => {
  const mockOnAuthSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset fetch mock
    vi.mocked(fetch).mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders all login buttons', () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      expect(screen.getByText('Continue with Meta')).toBeInTheDocument()
      expect(screen.getByText('Continue with Google')).toBeInTheDocument()
      expect(screen.getByText('Sign up with email')).toBeInTheDocument()
      expect(screen.getByText('Log in')).toBeInTheDocument()
    })

    it('displays Meta icon', () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      const metaIcon = screen.getByAltText('Meta')
      expect(metaIcon).toBeInTheDocument()
      expect(metaIcon).toHaveAttribute('src', '/icons/meta-color.svg')
    })

    it('displays Google icon SVG', () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      const googleButton = screen.getByText('Continue with Google').closest('button')
      const googleIcon = googleButton?.querySelector('svg')
      expect(googleIcon).toBeInTheDocument()
    })
  })

  describe('Google Authentication', () => {
    it('calls login method when Google button is clicked', async () => {
      const mockLogin = vi.fn().mockResolvedValue(true)
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      expect(mockLogin).toHaveBeenCalledOnce()
    })

    it('shows loading state during Google authentication', async () => {
      const mockLogin = vi.fn().mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(true), 100))
      )

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      expect(screen.getByText('Opening Google sign-in...')).toBeInTheDocument()
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('calls onAuthSuccess callback on successful Google login', async () => {
      const mockLogin = vi.fn().mockResolvedValue(true)
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      await waitFor(() => {
        expect(mockOnAuthSuccess).toHaveBeenCalledOnce()
      })
    })

    it('shows alert on Google authentication failure', async () => {
      const mockLogin = vi.fn().mockRejectedValue(new Error('Auth failed'))
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('Authentication failed: Auth failed')
      })
    })

    it('handles Google authentication failure without error object', async () => {
      const mockLogin = vi.fn().mockRejectedValue('String error')
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('Authentication failed. Please try again.')
      })
    })
  })

  describe('Meta Authentication', () => {
    it('calls loginMeta method when Meta button is clicked', async () => {
      const mockLoginMeta = vi.fn().mockResolvedValue(true)
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { loginMeta: mockLoginMeta }
      )

      const metaButton = screen.getByText('Continue with Meta')
      await userEvent.click(metaButton)

      expect(mockLoginMeta).toHaveBeenCalledOnce()
    })

    it('shows loading state during Meta authentication', async () => {
      const mockLoginMeta = vi.fn().mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(true), 100))
      )

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { loginMeta: mockLoginMeta }
      )

      const metaButton = screen.getByText('Continue with Meta')
      await userEvent.click(metaButton)

      expect(screen.getByText('Opening Meta sign-in...')).toBeInTheDocument()
    })

    it('calls onAuthSuccess callback on successful Meta login', async () => {
      const mockLoginMeta = vi.fn().mockResolvedValue(true)
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { loginMeta: mockLoginMeta }
      )

      const metaButton = screen.getByText('Continue with Meta')
      await userEvent.click(metaButton)

      await waitFor(() => {
        expect(mockOnAuthSuccess).toHaveBeenCalledOnce()
      })
    })

    it('shows alert on Meta authentication failure', async () => {
      const mockLoginMeta = vi.fn().mockRejectedValue(new Error('Meta auth failed'))
      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { loginMeta: mockLoginMeta }
      )

      const metaButton = screen.getByText('Continue with Meta')
      await userEvent.click(metaButton)

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('Meta authentication failed: Meta auth failed')
      })
    })
  })

  describe('Bypass Login', () => {
    it('calls bypass endpoint when Login button is clicked', async () => {
      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ authenticated: true })
        } as Response)

      const mockCheckExistingAuth = vi.fn().mockResolvedValue(true)
      const mockRefreshAccounts = vi.fn().mockResolvedValue(undefined)

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        {
          checkExistingAuth: mockCheckExistingAuth,
          refreshAccounts: mockRefreshAccounts,
          sessionId: 'test-session-id'
        }
      )

      const loginButton = screen.getByText('Log in')
      await userEvent.click(loginButton)

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/oauth/bypass-login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': 'test-session-id'
          }
        })
      })
    })

    it('shows loading state during bypass login', async () => {
      vi.mocked(fetch).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ success: true })
        } as Response), 100))
      )

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { sessionId: 'test-session-id' }
      )

      const loginButton = screen.getByText('Log in')
      await userEvent.click(loginButton)

      expect(screen.getByText('Creating bypass session...')).toBeInTheDocument()
    })

    it('handles bypass login failure', async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Bypass failed' })
      } as Response)

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { sessionId: 'test-session-id' }
      )

      const loginButton = screen.getByText('Log in')
      await userEvent.click(loginButton)

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('Login bypass failed: Bypass failed')
      })
    })
  })

  describe('Email Button', () => {
    it('shows coming soon alert when email button is clicked', async () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      const emailButton = screen.getByText('Sign up with email')
      await userEvent.click(emailButton)

      expect(global.alert).toHaveBeenCalledWith('Email login coming soon!')
    })
  })

  describe('Accessibility', () => {
    it('has proper button roles', () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      const buttons = screen.getAllByRole('button')
      expect(buttons).toHaveLength(4)
    })

    it('disables buttons during loading states', async () => {
      const mockLogin = vi.fn().mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(true), 100))
      )

      renderWithSessionContext(
        <FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      expect(googleButton.closest('button')).toBeDisabled()
    })

    it('has proper touch manipulation classes for mobile', () => {
      renderWithSessionContext(<FigmaLoginModal onAuthSuccess={mockOnAuthSuccess} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach(button => {
        expect(button).toHaveClass('touch-manipulation')
      })
    })
  })

  describe('Props', () => {
    it('works without onAuthSuccess callback', async () => {
      const mockLogin = vi.fn().mockResolvedValue(true)
      renderWithSessionContext(
        <FigmaLoginModal />,
        { login: mockLogin }
      )

      const googleButton = screen.getByText('Continue with Google')
      await userEvent.click(googleButton)

      // Should not throw error even without callback
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledOnce()
      })
    })
  })
})