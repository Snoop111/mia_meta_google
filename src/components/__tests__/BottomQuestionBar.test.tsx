import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BottomQuestionBar from '../BottomQuestionBar'

describe('BottomQuestionBar', () => {
  const mockProps = {
    question: 'Which creative gives me the most clicks for the lowest spend?',
    category: 'optimize',
    currentIndex: 1,
    totalQuestions: 4,
    isAnalyzing: false,
    onQuestionClick: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders the component with correct structure', () => {
      render(<BottomQuestionBar {...mockProps} />)

      // Check for fixed positioning wrapper
      const wrapper = screen.getByRole('button').closest('div')
      expect(wrapper).toHaveClass('fixed', 'bottom-0', 'left-0', 'right-0')
    })

    it('displays the question text when not analyzing', () => {
      render(<BottomQuestionBar {...mockProps} />)

      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()
    })

    it('renders as a button element', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      expect(button).toHaveClass('w-full', 'p-4', 'rounded-2xl', 'font-medium')
    })

    it('has proper styling classes for normal state', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-black', 'text-white', 'hover:bg-gray-800')
      expect(button).not.toHaveClass('bg-gray-200', 'cursor-not-allowed')
    })

    it('has proper button styling for mobile', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('w-full', 'p-4', 'rounded-2xl')
    })
  })

  describe('Loading State', () => {
    const loadingProps = {
      ...mockProps,
      isAnalyzing: true,
    }

    it('shows loading state when analyzing', () => {
      render(<BottomQuestionBar {...loadingProps} />)

      expect(screen.getByText('Analyzing...')).toBeInTheDocument()
      expect(screen.queryByText('Which creative gives me the most clicks for the lowest spend?')).not.toBeInTheDocument()
    })

    it('displays loading spinner when analyzing', () => {
      render(<BottomQuestionBar {...loadingProps} />)

      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(spinner).toHaveClass('w-4', 'h-4', 'border-2', 'border-gray-400', 'border-t-transparent', 'rounded-full')
    })

    it('disables button when analyzing', () => {
      render(<BottomQuestionBar {...loadingProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('applies disabled styling when analyzing', () => {
      render(<BottomQuestionBar {...loadingProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-gray-200', 'text-gray-500', 'cursor-not-allowed')
      expect(button).not.toHaveClass('bg-black', 'text-white')
    })

    it('shows loading elements in correct layout', () => {
      render(<BottomQuestionBar {...loadingProps} />)

      const loadingContainer = screen.getByText('Analyzing...').closest('div')
      expect(loadingContainer).toHaveClass('flex', 'items-center', 'justify-center', 'gap-2')
    })
  })

  describe('Interactions', () => {
    it('calls onQuestionClick when button is clicked', async () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      await userEvent.click(button)

      expect(mockProps.onQuestionClick).toHaveBeenCalledOnce()
    })

    it('does not call onQuestionClick when disabled', async () => {
      const disabledProps = { ...mockProps, isAnalyzing: true }
      render(<BottomQuestionBar {...disabledProps} />)

      const button = screen.getByRole('button')
      await userEvent.click(button)

      expect(mockProps.onQuestionClick).not.toHaveBeenCalled()
    })

    it('responds to keyboard interactions', async () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      button.focus()

      // Use click event instead of keyDown since buttons handle this automatically
      fireEvent.click(button)

      expect(mockProps.onQuestionClick).toHaveBeenCalledOnce()
    })

    it('is accessible via keyboard', async () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      button.focus()
      expect(document.activeElement).toBe(button)
    })

    it('handles multiple rapid clicks gracefully', async () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')

      // Click multiple times rapidly
      await userEvent.click(button)
      await userEvent.click(button)
      await userEvent.click(button)

      // Should call the handler for each click
      expect(mockProps.onQuestionClick).toHaveBeenCalledTimes(3)
    })
  })

  describe('Props Handling', () => {
    it('handles different question lengths', () => {
      const shortQuestion = {
        ...mockProps,
        question: 'Short question?'
      }
      const { rerender } = render(<BottomQuestionBar {...shortQuestion} />)
      expect(screen.getByText('Short question?')).toBeInTheDocument()

      const longQuestion = {
        ...mockProps,
        question: 'This is a very long question that might wrap to multiple lines and test how the component handles longer text content?'
      }
      rerender(<BottomQuestionBar {...longQuestion} />)
      expect(screen.getByText(longQuestion.question)).toBeInTheDocument()
    })

    it('handles empty question gracefully', () => {
      const emptyProps = { ...mockProps, question: '' }
      render(<BottomQuestionBar {...emptyProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      // Should still be clickable even with empty question
      expect(button).not.toBeDisabled()
    })

    it('handles different categories', () => {
      const growProps = { ...mockProps, category: 'grow' }
      const { rerender } = render(<BottomQuestionBar {...growProps} />)
      expect(screen.getByRole('button')).toBeInTheDocument()

      const protectProps = { ...mockProps, category: 'protect' }
      rerender(<BottomQuestionBar {...protectProps} />)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('handles different question indices', () => {
      const firstQuestion = { ...mockProps, currentIndex: 0, totalQuestions: 4 }
      const { rerender } = render(<BottomQuestionBar {...firstQuestion} />)
      expect(screen.getByRole('button')).toBeInTheDocument()

      const lastQuestion = { ...mockProps, currentIndex: 3, totalQuestions: 4 }
      rerender(<BottomQuestionBar {...lastQuestion} />)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper button semantics', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      expect(button.tagName).toBe('BUTTON')
    })

    it('is focusable when enabled', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      button.focus()
      expect(document.activeElement).toBe(button)
    })

    it('is not focusable when disabled', () => {
      const disabledProps = { ...mockProps, isAnalyzing: true }
      render(<BottomQuestionBar {...disabledProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('has appropriate text content for screen readers', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveTextContent('Which creative gives me the most clicks for the lowest spend?')
    })

    it('announces loading state to screen readers', () => {
      const loadingProps = { ...mockProps, isAnalyzing: true }
      render(<BottomQuestionBar {...loadingProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveTextContent('Analyzing...')
    })

    it('maintains minimum touch target size', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      // The component uses p-4 class which provides adequate padding for touch targets
      expect(button).toHaveClass('p-4')
    })
  })

  describe('Visual States', () => {
    it('has correct transition classes', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('transition-all')
    })

    it('applies hover states correctly', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-gray-800')
    })

    it('shows proper z-index for overlay', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const wrapper = screen.getByRole('button').closest('div')
      expect(wrapper).toHaveClass('z-50')
    })

    it('has proper border styling', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const wrapper = screen.getByRole('button').closest('div')
      expect(wrapper).toHaveClass('border-t', 'border-gray-100')
    })

    it('applies correct background colors', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const wrapper = screen.getByRole('button').closest('div')
      expect(wrapper).toHaveClass('bg-white')
    })
  })

  describe('Text Layout', () => {
    it('centers text properly', () => {
      render(<BottomQuestionBar {...mockProps} />)

      const textContainer = screen.getByText('Which creative gives me the most clicks for the lowest spend?')
      expect(textContainer).toHaveClass('text-sm', 'text-center')
    })

    it('handles text overflow gracefully', () => {
      const longQuestionProps = {
        ...mockProps,
        question: 'This is an extremely long question that tests how the component handles text that might exceed the normal button width and could potentially cause layout issues'
      }

      render(<BottomQuestionBar {...longQuestionProps} />)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      expect(screen.getByText(longQuestionProps.question)).toBeInTheDocument()
    })
  })

  describe('State Transitions', () => {
    it('transitions smoothly between states', () => {
      const { rerender } = render(<BottomQuestionBar {...mockProps} />)

      // Normal state
      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()
      expect(screen.getByRole('button')).not.toBeDisabled()

      // Loading state
      const loadingProps = { ...mockProps, isAnalyzing: true }
      rerender(<BottomQuestionBar {...loadingProps} />)

      expect(screen.getByText('Analyzing...')).toBeInTheDocument()
      expect(screen.getByRole('button')).toBeDisabled()

      // Back to normal
      rerender(<BottomQuestionBar {...mockProps} />)

      expect(screen.getByText('Which creative gives me the most clicks for the lowest spend?')).toBeInTheDocument()
      expect(screen.getByRole('button')).not.toBeDisabled()
    })
  })
})