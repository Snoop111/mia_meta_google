import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreativePageFixed from '../CreativePageFixed'
import { useSession } from '../../contexts/SessionContext'

// Mock fetch globally
global.fetch = vi.fn()

// Mock react-markdown
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown-content">{children}</div>
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock the useSession hook
const mockSession = {
  isAuthenticated: true,
  user: {
    name: 'Test User',
    email: 'test@example.com',
    picture_url: 'https://example.com/avatar.jpg',
    google_user_id: '12345'
  },
  selectedAccount: {
    id: 'test-account',
    name: 'Test Account',
    google_ads_id: '123456',
    ga4_property_id: '789012',
    business_type: 'ecommerce',
    color: '#blue',
    display_name: 'Test Account'
  },
  availableAccounts: [
    {
      id: 'test-account',
      name: 'Test Account',
      google_ads_id: '123456',
      ga4_property_id: '789012',
      business_type: 'ecommerce',
      color: '#blue',
      display_name: 'Test Account'
    }
  ],
  sessionId: 'test-session-123',
  isLoading: false,
  error: null,
  isMetaAuthenticated: false,
  metaUser: null,
  login: vi.fn(),
  loginMeta: vi.fn(),
  logout: vi.fn(),
  logoutMeta: vi.fn(),
  selectAccount: vi.fn(),
  refreshAccounts: vi.fn(),
  clearError: vi.fn(),
  generateSessionId: vi.fn(),
  checkExistingAuth: vi.fn(),
  checkMetaAuth: vi.fn(),
}

vi.mock('../../contexts/SessionContext', () => ({
  useSession: vi.fn(),
}))

// Mock BottomQuestionBar component
vi.mock('../BottomQuestionBar', () => ({
  default: ({ question, onQuestionClick, isAnalyzing }: any) => (
    <div data-testid="bottom-question-bar">
      <button
        data-testid="bottom-question-btn"
        onClick={onQuestionClick}
        disabled={isAnalyzing}
      >
        {isAnalyzing ? 'Analyzing...' : question}
      </button>
    </div>
  )
}))

// Note: AccountPicker and DatePicker components have been removed as they were unused

describe('CreativePageFixed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useSession).mockReturnValue(mockSession)
    vi.mocked(fetch).mockClear()

    // Mock successful API responses by default
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        response: 'Test analysis response with insights about your creative performance.'
      }),
    } as Response)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders the page with initial UI elements', () => {
      render(<CreativePageFixed />)

      expect(screen.getByText('Creative Insights')).toBeInTheDocument()
      expect(screen.getByText('grow')).toBeInTheDocument()
      expect(screen.getByText('optimise')).toBeInTheDocument()
      expect(screen.getByText('protect')).toBeInTheDocument()
    })

    it('shows account information in header', () => {
      render(<CreativePageFixed />)

      expect(screen.getByText('Test Account')).toBeInTheDocument()
    })

    it('displays preset questions for initial category', () => {
      render(<CreativePageFixed />)

      // Should show grow questions initially
      expect(screen.getByText('Which creative format is driving the most engagement?')).toBeInTheDocument()
      expect(screen.getByText('Which captions or headlines resonate best with my audience?')).toBeInTheDocument()
    })

    it('renders with no messages initially', () => {
      render(<CreativePageFixed />)

      // Should not show chat messages initially
      expect(screen.queryAllByTestId('markdown-content')).toHaveLength(0)
    })
  })

  describe('Category Navigation', () => {
    it('switches between categories', async () => {
      render(<CreativePageFixed />)

      // Click on Optimise tab
      const optimiseTab = screen.getByText('optimise')
      await userEvent.click(optimiseTab)

      // Should show optimise questions
      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()

      // Click on Protect tab
      const protectTab = screen.getByText('protect')
      await userEvent.click(protectTab)

      // Should show protect questions
      expect(screen.getByText('Is creative fatigue affecting my ads?')).toBeInTheDocument()
    })

    it('preserves messages when switching categories', async () => {
      render(<CreativePageFixed />)

      // Ask a question in Grow category
      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
      })

      // Switch to Optimise
      const optimiseTab = screen.getByText('optimise')
      await userEvent.click(optimiseTab)

      // Should show initial questions again
      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()

      // Switch back to Grow
      const growTab = screen.getByText('grow')
      await userEvent.click(growTab)

      // Should show the message again
      expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
    })

    it('resets question flow when switching to empty category', async () => {
      render(<CreativePageFixed />)

      // Ask a question in Grow
      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.queryByTestId('bottom-question-bar')).toBeInTheDocument()
      })

      // Switch to empty Optimise category
      const optimiseTab = screen.getByText('optimise')
      await userEvent.click(optimiseTab)

      // Should show initial questions again
      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()
    })
  })

  describe('Question Interactions', () => {
    it('handles initial question click', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      // Should call API
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/creative-analysis', expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: expect.stringContaining('Which creative format is driving the most engagement?'),
        }))
      })

      // Should show response
      await waitFor(() => {
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
      })
    })

    it('shows loading state during analysis', async () => {
      // Mock delayed response
      vi.mocked(fetch).mockImplementation(() =>
        new Promise(resolve =>
          setTimeout(() => resolve({
            ok: true,
            json: () => Promise.resolve({ response: 'Analysis complete' })
          } as Response), 100)
        )
      )

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      // Should show loading message
      expect(screen.getByText('Mia is analyzing...')).toBeInTheDocument()

      // Wait for response
      await waitFor(() => {
        // Analysis should complete and show response
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
      })
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('API Error'))

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Sorry, I encountered an error analyzing your creative data. Please try again.')).toBeInTheDocument()
      })
    })

    it('shows bottom question bar after first response', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByTestId('bottom-question-bar')).toBeInTheDocument()
      })
    })

    it('cycles through questions using bottom bar', async () => {
      render(<CreativePageFixed />)

      // Ask first question
      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByTestId('bottom-question-bar')).toBeInTheDocument()
      })

      // Click next question from bottom bar
      const bottomBtn = screen.getByTestId('bottom-question-btn')
      await userEvent.click(bottomBtn)

      // Should call API for second question
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Account Management', () => {
    it('displays account information', async () => {
      render(<CreativePageFixed />)

      const accountButton = screen.getByText('Test Account')
      expect(accountButton).toBeInTheDocument()
    })

    it('clears messages when switching accounts', async () => {
      render(<CreativePageFixed />)

      // Ask a question first
      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
      })

      // Switch account
      const accountButton = screen.getByText('Test Account')
      await userEvent.click(accountButton)

      const selectBtn = screen.getByTestId('select-account-btn')
      await userEvent.click(selectBtn)

      // Messages should be cleared (check that we're back to initial state)
      expect(screen.getByText('Which creative format is driving the most engagement?')).toBeInTheDocument()
    })
  })

  describe('Date Range Management', () => {
    it('manages date range state', async () => {
      render(<CreativePageFixed />)

      // Component manages date range internally
      expect(screen.getByText('03 Aug - 02 Sept')).toBeInTheDocument()
    })
  })

  describe('Message Rendering', () => {
    it('renders question messages correctly', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        // Should show question in black bubble on right
        const questionElements = screen.getAllByText('Which creative format is driving the most engagement?')
        expect(questionElements.length).toBeGreaterThan(0)
      })
    })

    it('renders response messages correctly', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        // Should show response in gray bubble on left
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
        // Response is rendered via ReactMarkdown
      })
    })

    it('shows loading dots animation', async () => {
      vi.mocked(fetch).mockImplementation(() =>
        new Promise(resolve =>
          setTimeout(() => resolve({
            ok: true,
            json: () => Promise.resolve({ response: 'Done' })
          } as Response), 200)
        )
      )

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      // Should show loading dots
      expect(screen.getByText('Mia is analyzing...')).toBeInTheDocument()

      await waitFor(() => {
        // Loading should complete
        expect(screen.queryByText('Mia is analyzing...')).not.toBeInTheDocument()
      })
    })
  })

  describe('Scroll Behavior', () => {
    it('auto-scrolls to new messages', async () => {
      // Mock scrollIntoView
      const mockScrollIntoView = vi.fn()
      Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
        value: mockScrollIntoView,
        writable: true
      })

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getAllByTestId('markdown-content').length).toBeGreaterThan(0)
      })

      // Should have triggered scroll behavior
      expect(mockScrollIntoView).toHaveBeenCalled()
    })
  })

  describe('Error States', () => {
    it('handles network errors', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'))

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Sorry, I encountered an error analyzing your creative data. Please try again.')).toBeInTheDocument()
      })
    })

    it('handles API response errors', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: 'Server error' })
      } as Response)

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Sorry, I encountered an error analyzing your creative data. Please try again.')).toBeInTheDocument()
      })
    })

    it('handles malformed JSON responses', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON'))
      } as Response)

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Sorry, I encountered an error analyzing your creative data. Please try again.')).toBeInTheDocument()
      })
    })
  })

  describe('Session Validation', () => {
    it('handles missing session ID', async () => {
      vi.mocked(useSession).mockReturnValue({
        ...mockSession,
        sessionId: null
      })

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Please ensure you are logged in and have selected an account.')).toBeInTheDocument()
      })
    })

    it('handles missing selected account', async () => {
      vi.mocked(useSession).mockReturnValue({
        ...mockSession,
        selectedAccount: null
      })

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      await waitFor(() => {
        expect(screen.getByText('Please ensure you are logged in and have selected an account.')).toBeInTheDocument()
      })
    })
  })

  describe('Performance', () => {
    it('debounces rapid question clicks', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')

      // Click multiple times rapidly
      await userEvent.click(questionBtn)
      await userEvent.click(questionBtn)
      await userEvent.click(questionBtn)

      // Should only make one API call
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledTimes(1)
      })
    })

    it('prevents question clicks during analysis', async () => {
      vi.mocked(fetch).mockImplementation(() =>
        new Promise(resolve =>
          setTimeout(() => resolve({
            ok: true,
            json: () => Promise.resolve({ response: 'Done' })
          } as Response), 200)
        )
      )

      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')
      await userEvent.click(questionBtn)

      // Try clicking another question while analyzing
      const secondQuestionBtn = screen.getByText('Which captions or headlines resonate best with my audience?')
      await userEvent.click(secondQuestionBtn)

      // Should still only have one API call
      expect(fetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('Accessibility', () => {
    it('has proper button roles and labels', () => {
      render(<CreativePageFixed />)

      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)

      // Check specific buttons have text content
      expect(screen.getByText('Which creative format is driving the most engagement?')).toBeInTheDocument()
    })

    it('provides keyboard navigation', async () => {
      render(<CreativePageFixed />)

      const questionBtn = screen.getByText('Which creative format is driving the most engagement?')

      // Focus and activate with keyboard
      questionBtn.focus()
      fireEvent.keyDown(questionBtn, { key: 'Enter', code: 'Enter' })

      await waitFor(() => {
        expect(fetch).toHaveBeenCalled()
      })
    })
  })
})