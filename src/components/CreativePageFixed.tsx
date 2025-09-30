import { apiFetch } from '../utils/api'
import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import BottomQuestionBar from './BottomQuestionBar'
import CreativeDatePicker from './CreativeDatePicker'
import { useSession } from '../contexts/SessionContext'

// Import all the logic from the old CreativePage
interface CreativePageProps {
  onBack?: () => void
}

// 12 Preset Creative Questions (from original)
const PRESET_QUESTIONS = {
  grow: [
    "Which visual styles or themes perform best?",
    "Which messaging angle appeals most to our audience?",
    "Which creative format is driving the most engagement?",
    "Which captions or headlines resonate best with my audience?"
  ],
  optimise: [
    "Which creative gives me the most clicks for the lowest spend?",
    "Which advert delivered the highest click-through rate (CTR)?",
    "Which headlines or CTAs perform best?",
    "How should I optimise creative to increase engagement?"
  ],
  protect: [
    "Which ads are starting to lose engagement over time?",
    "Is creative fatigue affecting my ads?",
    "Which creative assets are showing declining performance trends?",
    "Are my audiences seeing the same creative too often?"
  ]
} as const

type Category = keyof typeof PRESET_QUESTIONS

interface Message {
  id: string
  type: 'question' | 'response'
  content: string
  category: Category
  questionIndex: number
  timestamp: Date
  isLoading?: boolean
}

const CreativePageFixed = ({ onBack }: CreativePageProps) => {
  const { sessionId, selectedAccount, logout, availableAccounts, selectAccount } = useSession()

  const [activeCategory, setActiveCategory] = useState<Category>('grow')
  const [showBurgerMenu, setShowBurgerMenu] = useState(false)
  const [showAccountSelector, setShowAccountSelector] = useState(false) // New state for account selection popout
  const [isAccountSwitching, setIsAccountSwitching] = useState(false)
  const [messagesByCategory, setMessagesByCategory] = useState<{
    grow: Message[]
    optimise: Message[]
    protect: Message[]
  }>({
    grow: [],
    optimise: [],
    protect: []
  })
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  
  // New state for question flow management
  const [askedQuestionsByCategory, setAskedQuestionsByCategory] = useState<{
    grow: number[]
    optimise: number[]
    protect: number[]
  }>({
    grow: [],
    optimise: [],
    protect: []
  })
  const [questionFlow, setQuestionFlow] = useState<'initial' | 'cycling'>('initial')

  // Date picker state
  const [showDatePicker, setShowDatePicker] = useState(false)
  const [userSelectedStartDate, setUserSelectedStartDate] = useState<string>('2025-08-03') // Default start date: Aug 3

  // Account switching handler
  const handleAccountSwitch = async (accountId: string) => {
    if (isAccountSwitching) return

    setIsAccountSwitching(true)
    setShowBurgerMenu(false)
    setShowAccountSelector(false)

    try {
      const success = await selectAccount(accountId)

      if (success) {
        const newAccount = availableAccounts.find(acc => acc.id === accountId)

        // Clear chat messages when switching accounts
        setMessagesByCategory({
          grow: [],
          optimise: [],
          protect: []
        })

        // Reset state
        setQuestionFlow('initial')
        setCurrentQuestionIndex(0)

        // Small delay for UX feedback
        setTimeout(() => {
          setIsAccountSwitching(false)
        }, 500)
      } else {
        console.error('❌ [CREATIVE] Failed to switch account')
        setIsAccountSwitching(false)
      }
    } catch (error) {
      console.error('❌ [CREATIVE] Account switch error:', error)
      setIsAccountSwitching(false)
    }
  }

  // Get account icon helper function
  const getAccountIcon = (businessType: string) => {
    switch (businessType?.toLowerCase()) {
      case 'engineering': return '⚙️'
      case 'food': return '🍒'
      default: return '🏢'
    }
  }

  // Enhanced image preloading with loading state
  const [imagesLoaded, setImagesLoaded] = useState(false)

  useEffect(() => {
    const imagesToPreload = [
      '/images/Grow Nav.png',
      '/images/Optimise Nav.png',
      '/images/Protect Nav.png'
    ]

    let loadedCount = 0
    const totalImages = imagesToPreload.length

    const checkAllLoaded = () => {
      loadedCount += 1
      if (loadedCount === totalImages) {
        setImagesLoaded(true)
      }
    }

    imagesToPreload.forEach(src => {
      const img = new Image()
      img.onload = checkAllLoaded
      img.onerror = () => {
        console.error('[PRELOAD] Failed to load:', src)
        checkAllLoaded() // Still continue even if one fails
      }
      img.src = src
    })
  }, [])

  // Close date picker when clicking outside (but not when clicking inside dropdowns)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showDatePicker) {
        const target = event.target as Element
        // Only close if clicking completely outside the date picker container
        if (!target.closest('.date-picker-container') && !target.closest('select')) {
          setShowDatePicker(false)
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showDatePicker])
  
  // Date utility functions - now handled by CreativeDatePicker component
  // calculateDateRange and formatDateRangeForDisplay moved to CreativeDatePicker

  // Dynamic date range based on category and user selection
  const getDateRangeForCategory = (category: Category, customStartDate?: string) => {
    const startDate = customStartDate || userSelectedStartDate
    const start = new Date(startDate)
    const daysToAdd = category === 'protect' ? 6 : 30 // 7 days total for protect, 31 days for grow/optimize
    const end = new Date(start)
    end.setDate(start.getDate() + daysToAdd)

    return {
      start: startDate,
      end: end.toISOString().split('T')[0] // Format as YYYY-MM-DD
    }
  }

  // Format date for display in header
  const formatDateRangeForDisplay = (startDate: string, endDate: string) => {
    const start = new Date(startDate)
    const end = new Date(endDate)

    const formatDate = (date: Date) => {
      const day = date.getDate().toString().padStart(2, '0')
      const month = date.toLocaleDateString('en-GB', { month: 'short' })
      return `${day} ${month}`
    }

    return `${formatDate(start)} - ${formatDate(end)}`
  }
  
  const [selectedDateRange, setSelectedDateRange] = useState(() => {
    const initialRange = getDateRangeForCategory(activeCategory, userSelectedStartDate)
    return initialRange
  })

  // Scroll functionality
  const chatAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Get current messages and question
  const messages = messagesByCategory[activeCategory]
  const askedQuestions = askedQuestionsByCategory[activeCategory]
  
  // Get available questions (not yet asked) for the current category
  const getAvailableQuestions = () => {
    const allQuestions = [0, 1, 2, 3]
    return allQuestions.filter(index => !askedQuestions.includes(index))
  }
  
  // Get current question based on flow state
  const getCurrentQuestion = () => {
    if (questionFlow === 'initial') {
      return null // No specific question in initial state
    }
    
    const availableQuestions = getAvailableQuestions()
    if (availableQuestions.length === 0) {
      // All questions asked, start cycling through all questions again
      const questions = PRESET_QUESTIONS[activeCategory]
      return questions[currentQuestionIndex % questions.length]
    }
    
    // Get current available question
    const currentAvailableIndex = currentQuestionIndex % availableQuestions.length
    const questionIndex = availableQuestions[currentAvailableIndex]
    return PRESET_QUESTIONS[activeCategory][questionIndex]
  }

  // Smart autoscroll functions from old CreativePage
  const scrollToLatestMessage = () => {
    if (messagesEndRef.current && chatAreaRef.current) {
      // Scroll so the latest message is at the TOP of the view area
      const chatArea = chatAreaRef.current
      const messagesEnd = messagesEndRef.current
      const lastMessageElement = messagesEnd.previousElementSibling as HTMLElement
      
      if (lastMessageElement) {
        const offsetTop = lastMessageElement.offsetTop - chatArea.offsetTop
        chatArea.scrollTo({ top: offsetTop, behavior: 'smooth' })
      }
    }
  }

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  // Smart auto-scroll when messages change (mobile iPhone 16 Pro UX)
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      
      // If it's a new response (not loading), scroll to show latest message at top of view
      if (lastMessage.type === 'response' && !lastMessage.isLoading) {
        setTimeout(() => scrollToLatestMessage(), 100)
      }
      // If it's loading or question, scroll to bottom to show latest
      else {
        setTimeout(() => scrollToBottom(), 100)
      }
    }
  }, [messages])

  // Handle initial question click (when user clicks one of the 4 initial questions)
  const handleInitialQuestionClick = async (questionIndex: number) => {
    const question = PRESET_QUESTIONS[activeCategory][questionIndex]
    if (!question || isAnalyzing) return


    // Mark this question as asked and switch to cycling mode
    setAskedQuestionsByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], questionIndex]
    }))
    setQuestionFlow('cycling')
    
    // Reset currentQuestionIndex to 0 for cycling through remaining questions
    setCurrentQuestionIndex(0)

    // Add question message
    const questionMessage: Message = {
      id: `q-${Date.now()}`,
      type: 'question',
      content: question,
      category: activeCategory,
      questionIndex: questionIndex,
      timestamp: new Date()
    }

    setMessagesByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], questionMessage]
    }))
    setIsAnalyzing(true)

    // Add loading response
    const loadingMessage: Message = {
      id: `r-${Date.now()}`,
      type: 'response',
      content: "Mia is analyzing",
      category: activeCategory,
      questionIndex: questionIndex,
      timestamp: new Date(),
      isLoading: true
    }

    setMessagesByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], loadingMessage]
    }))

    await performQuestionAnalysis(question, questionIndex, loadingMessage)
  }

  // Handle cycling question click (bottom bar questions)
  const handleCyclingQuestionClick = async () => {
    const question = getCurrentQuestion()
    if (!question || isAnalyzing) return

    // Find which question index this is
    const availableQuestions = getAvailableQuestions()
    const currentAvailableIndex = currentQuestionIndex % availableQuestions.length
    const questionIndex = availableQuestions[currentAvailableIndex]


    // Mark this question as asked
    setAskedQuestionsByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], questionIndex]
    }))

    // Add question message
    const questionMessage: Message = {
      id: `q-${Date.now()}`,
      type: 'question',
      content: question,
      category: activeCategory,
      questionIndex: questionIndex,
      timestamp: new Date()
    }

    setMessagesByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], questionMessage]
    }))
    setIsAnalyzing(true)

    // Add loading response
    const loadingMessage: Message = {
      id: `r-${Date.now()}`,
      type: 'response',
      content: "Mia is analyzing",
      category: activeCategory,
      questionIndex: questionIndex,
      timestamp: new Date(),
      isLoading: true
    }

    setMessagesByCategory(prev => ({
      ...prev,
      [activeCategory]: [...prev[activeCategory], loadingMessage]
    }))

    await performQuestionAnalysis(question, questionIndex, loadingMessage)
    
    // Move to next available question
    setCurrentQuestionIndex(prev => prev + 1)
  }

  // Shared analysis logic
  // Refresh functionality - reset to initial state
  const handleRefresh = () => {
    
    // Reset current tab only - don't change activeCategory
    setIsAnalyzing(false)
    setQuestionFlow('initial')
    setCurrentQuestionIndex(0)
    
    // Clear current category's messages and asked questions
    setMessagesByCategory(prev => ({
      ...prev,
      [activeCategory]: []
    }))
    
    setAskedQuestionsByCategory(prev => ({
      ...prev,
      [activeCategory]: []
    }))
  }

  // Sign out functionality
  const handleSignOut = async () => {
    try {
      await logout()
      if (onBack) {
        onBack() // Go back to main view
      }
    } catch (error) {
      console.error('[CREATIVE-SIGNOUT] Error:', error)
    }
    setShowBurgerMenu(false)
  }

  const performQuestionAnalysis = async (question: string, questionIndex: number, loadingMessage: Message) => {
    try {
      // Ensure we have session and account selected
      if (!sessionId || !selectedAccount) {
        throw new Error('No session or account selected. Please log in and select an account.')
      }


      // Use session-based account switching - backend will resolve account IDs
      const response = await apiFetch('/api/creative-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          category: activeCategory,
          session_id: sessionId,
          user_id: '106540664695114193744',
          google_ads_id: selectedAccount?.google_ads_id || '7574136388', // Fallback to DFSA
          ga4_property_id: selectedAccount?.ga4_property_id || '458016659', // Fallback to DFSA
          start_date: selectedDateRange.start,
          end_date: selectedDateRange.end
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      // Replace loading message with actual response
      setMessagesByCategory(prev => ({
        ...prev,
        [activeCategory]: prev[activeCategory].map(msg => 
          msg.id === loadingMessage.id 
            ? {
                ...msg,
                content: result.success ? result.creative_response : `Error: ${result.error}`,
                isLoading: false
              }
            : msg
        )
      }))

    } catch (error) {
      console.error('[CREATIVE-PAGE-FIXED] API Error:', error)
      
      setMessagesByCategory(prev => ({
        ...prev,
        [activeCategory]: prev[activeCategory].map(msg => 
          msg.id === loadingMessage.id 
            ? {
                ...msg,
                content: `Sorry, there was an error analyzing your creative assets. Please try again.`,
                isLoading: false
              }
            : msg
        )
      }))
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Handle category change - reset flow state when switching tabs
  const handleCategoryChange = (category: Category) => {
    setActiveCategory(category)
    setCurrentQuestionIndex(0)

    // Update date range based on new category and current user selection
    setSelectedDateRange(getDateRangeForCategory(category))

    // Check if the new category has any messages - if so, stay in cycling mode
    const newCategoryMessages = messagesByCategory[category]
    setQuestionFlow(newCategoryMessages.length > 0 ? 'cycling' : 'initial')
  }

  // Handle date selection from CreativeDatePicker component
  const handleDateSelection = (newStartDate: string, shouldClose = false) => {

    setUserSelectedStartDate(newStartDate)
    const newDateRange = getDateRangeForCategory(activeCategory, newStartDate)


    setSelectedDateRange(newDateRange)

    // Close picker if requested
    if (shouldClose) {
      setShowDatePicker(false)
    }
  }

  const currentQuestion = getCurrentQuestion()
  const totalQuestions = PRESET_QUESTIONS[activeCategory].length

  // Dynamic gradient based on Figma frames - Using CSS gradients for instant loading
  const getGradientForCategory = (category: Category) => {
    switch (category) {
      case 'grow':
        return {
          background: 'linear-gradient(135deg, #290068 0%, #4A148C 50%, #6A1B9A 100%)',
          imagePath: '/images/Grow Nav.png'
        }
      case 'optimise':
        return {
          background: 'linear-gradient(135deg, #290068 0%, #4A148C 50%, #6A1B9A 100%)',
          imagePath: '/images/Optimise Nav.png'
        }
      case 'protect':
        return {
          background: 'linear-gradient(135deg, #290068 0%, #4A148C 50%, #6A1B9A 100%)',
          imagePath: '/images/Protect Nav.png'
        }
      default:
        return {
          background: 'linear-gradient(135deg, #290068 0%, #4A148C 50%, #6A1B9A 100%)',
          imagePath: '/images/Grow Nav.png'
        }
    }
  }

  // Tab accent colors from Figma - Exact hex values
  const getTabAccent = (category: Category) => {
    switch (category) {
      case 'grow':
        return { color: '#27D1F4' } // Cyan
      case 'optimise':
        return { color: '#F32F94' } // Pink  
      case 'protect':
        return { color: '#FAA90B' } // Orange
      default:
        return { color: '#000000' }
    }
  }

  return (
    <div className="w-full h-full relative flex flex-col" style={{ backgroundColor: '#290068' }}>
      {/* Header - Full width */}
      <div className="flex items-center px-4 py-3 relative z-20 flex-shrink-0 bg-white">
        <div className="flex-1 flex justify-start pl-2">
          <div className="relative">
            <button
              onClick={() => setShowBurgerMenu(!showBurgerMenu)}
              className="w-6 h-6 flex items-center justify-center"
            >
              <img src="/icons/menu.svg" alt="Menu" className="w-6 h-6" />
            </button>

            {/* New Clean Menu Dropdown */}
            {showBurgerMenu && !showAccountSelector && (
              <div className="absolute top-8 left-0 bg-white rounded-lg shadow-lg border border-gray-200 min-w-64 z-30">
                {/* Accounts Button */}
                <button
                  onClick={() => setShowAccountSelector(true)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs"
                      style={{ backgroundColor: selectedAccount?.color }}
                    >
                      {getAccountIcon(selectedAccount?.business_type || '')}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 text-sm">Accounts</div>
                      <div className="text-xs text-gray-500">{selectedAccount?.name}</div>
                    </div>
                  </div>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                {/* Sign Out */}
                <div className="border-t border-gray-100">
                  <button
                    onClick={handleSignOut}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 transition-colors"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M9 21H5C4.44772 21 4 20.5523 4 20V4C4 3.44772 4.44772 3 5 3H9" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <polyline points="16,17 21,12 16,7" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="21" y1="12" x2="9" y2="12" stroke="#6B7280" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    <span className="text-sm text-gray-600">Sign Out</span>
                  </button>
                </div>
              </div>
            )}

            {/* Account Selector Popout */}
            {showBurgerMenu && showAccountSelector && (
              <div className="absolute top-8 left-0 bg-white rounded-lg shadow-lg border border-gray-200 min-w-64 z-30">
                {/* Back Button */}
                <button
                  onClick={() => setShowAccountSelector(false)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100"
                >
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                  </svg>
                  <div className="font-medium text-gray-900 text-sm">Back</div>
                </button>

                {/* Available Accounts */}
                <div className="px-2 py-2">
                  {availableAccounts.map((account) => (
                    <button
                      key={account.id}
                      onClick={() => handleAccountSwitch(account.id)}
                      disabled={isAccountSwitching || account.id === selectedAccount?.id}
                      className={`w-full px-3 py-2 text-left rounded-lg flex items-center gap-3 text-sm transition-colors ${
                        account.id === selectedAccount?.id
                          ? 'bg-gray-50 text-gray-400 cursor-default'
                          : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-xs"
                        style={{ backgroundColor: account.color }}
                      >
                        {getAccountIcon(account.business_type)}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{account.name}</div>
                        <div className="text-xs text-gray-500">{account.business_type}</div>
                      </div>
                      {account.id === selectedAccount?.id && (
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      {isAccountSwitching && account.id !== selectedAccount?.id && (
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <h1 className="text-xl font-normal text-black text-center" style={{ fontFamily: 'Geologica, sans-serif', fontSize: '20px', fontWeight: 400, lineHeight: '110%' }}>Creative Insights</h1>

        <div className="flex-1 flex justify-end pr-2">
          <div className="relative date-picker-container">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="w-6 h-6 flex items-center justify-center"
            >
              <img src="/icons/calendar.svg" alt="Calendar" className="w-6 h-6" />
            </button>

            {/* Date Picker Component */}
            <CreativeDatePicker
              isOpen={showDatePicker}
              startDate={userSelectedStartDate}
              category={activeCategory}
              onDateChange={handleDateSelection}
              onClose={() => setShowDatePicker(false)}
            />
          </div>
        </div>
      </div>

      {/* Dynamic Gradient Header - Full width like Figma */}
      <div 
        className="relative flex items-center justify-between px-4 py-4 overflow-hidden"
        style={{
          minHeight: '100px'
        }}
      >
        {/* Figma-accurate gradient background for all tabs */}
        <div
          className="absolute inset-0"
          style={{
            background: getGradientForCategory(activeCategory).background, // CSS gradient shows instantly
            backgroundImage: imagesLoaded ? `url("${getGradientForCategory(activeCategory).imagePath}")` : 'none',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            zIndex: 0,
            transition: 'background-image 0.3s ease-out'
          }}
        />
        <button
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()

            if (onBack) {
              onBack()
            } else {
            }
          }}
          onTouchStart={(e) => {
            e.currentTarget.style.transform = 'scale(0.9) translateY(-5px) translateX(15px)'
          }}
          onTouchEnd={(e) => {
            e.currentTarget.style.transform = 'scale(1) translateY(-5px) translateX(15px)'
          }}
          onTouchCancel={(e) => {
            e.currentTarget.style.transform = 'scale(1) translateY(-5px) translateX(15px)'
            e.currentTarget.style.opacity = '1'
          }}
          className="flex items-center justify-center active:scale-90 transition-all duration-100"
          style={{
            color: '#FFF',
            padding: '12px',
            marginLeft: '-8px',
            minWidth: '44px',
            minHeight: '44px',
            WebkitTapHighlightColor: 'transparent',
            touchAction: 'manipulation',
            position: 'relative',
            transform: 'translateY(-5px) translateX(15px)',
            zIndex: 20 // Ensure it stays below date picker
          }}
        >
          <svg width="16" height="13" viewBox="0 0 16 13" fill="none">
            <path d="M7.18572 13L0.822088 6.63636L7.18572 0.272727L8.27947 1.35227L3.77663 5.85511H15.4386V7.41761H3.77663L8.27947 11.9062L7.18572 13Z" fill="white"/>
          </svg>
        </button>

        <div className="flex flex-col items-end" style={{ zIndex: 10, position: 'relative', transform: 'translateY(-5px) translateX(-20px)' }}>
          <span className="text-white font-medium text-lg">
            {(() => {
              const displayText = formatDateRangeForDisplay(selectedDateRange.start, selectedDateRange.end)
              return displayText
            })()}
          </span>
          {selectedAccount && (
            <span className="text-white/80 text-sm font-normal mt-0.5">{selectedAccount.name}</span>
          )}
        </div>
      </div>

      {/* Tabs - Full width, rounded corners */}
      <div className="relative -mt-4">
        <div className="flex w-full bg-gray-50 rounded-t-2xl overflow-hidden">
          {(['grow', 'optimise', 'protect'] as Category[]).map((category, index) => {
            const accent = getTabAccent(category)
            const isFirst = index === 0
            const isLast = index === 2
            return (
              <button
                key={category}
                className={`flex-1 py-3 px-4 text-center capitalize font-medium transition-colors ${
                  activeCategory === category 
                    ? 'bg-white font-semibold' 
                    : 'text-gray-600 hover:text-gray-800'
                } ${isFirst ? 'rounded-tl-3xl' : ''} ${isLast ? 'rounded-tr-3xl' : ''}`}
                style={{
                  color: activeCategory === category ? accent.color : undefined
                }}
                onClick={() => handleCategoryChange(category)}
              >
                {category}
              </button>
            )
          })}
        </div>
      </div>

      {/* Chat Area */}
      <div
        ref={chatAreaRef}
        className={`flex-1 bg-white p-6 space-y-4 overflow-y-auto`}
        style={{
          paddingBottom: messages.length > 0 ? '200px' : '0px' // Increased padding for mobile
        }}
      >
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.type === 'question' ? 'justify-end -mr-2' : 'justify-start -ml-2'}`}>
            <div className={`${message.type === 'question' ? 'max-w-[80%]' : 'max-w-[85%]'} ${
              message.type === 'question' 
                ? 'text-white px-6 py-4 flex items-center justify-center text-center' 
                : 'bg-gray-100 text-gray-800 p-4 rounded-2xl'
            }`} style={{
              backgroundColor: message.type === 'question' ? '#000000' : undefined,
              borderRadius: message.type === 'question' ? '32px 32px 0px 32px' : undefined
            }}>
              {message.isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <span className="text-sm font-medium">{message.content}</span>
                  <div className="flex space-x-1 items-end" style={{ transform: 'translateY(2px)' }}>
                    <div 
                      className="w-2 h-2 rounded-full animate-bounce bg-gray-100" 
                      style={{ 
                        border: '1px solid #000000',
                        boxSizing: 'border-box'
                      }}
                    ></div>
                    <div 
                      className="w-2 h-2 rounded-full animate-bounce bg-gray-100" 
                      style={{ 
                        animationDelay: '0.1s',
                        border: '1px solid #000000',
                        boxSizing: 'border-box'
                      }}
                    ></div>
                    <div 
                      className="w-2 h-2 rounded-full animate-bounce bg-gray-100" 
                      style={{ 
                        animationDelay: '0.2s',
                        border: '1px solid #000000',
                        boxSizing: 'border-box'
                      }}
                    ></div>
                  </div>
                </div>
              ) : (
                <div className={`text-sm w-full ${message.type === 'question' ? '' : 'prose prose-sm'}`}>
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => <h2 className={`text-base font-semibold mb-3 mt-4 break-words ${message.type === 'question' ? 'text-white' : 'text-gray-900'}`}>{children}</h2>,
                      h2: ({ children }) => <h3 className={`text-sm font-semibold mb-2 mt-4 break-words ${message.type === 'question' ? 'text-white' : 'text-gray-900'}`}>{children}</h3>,
                      h3: ({ children }) => <h4 className={`text-sm font-medium mb-2 mt-3 break-words ${message.type === 'question' ? 'text-white' : 'text-gray-800'}`}>{children}</h4>,
                      ul: ({ children }) => <ul className="list-none space-y-1 mb-3 ml-0">{children}</ul>,
                      ol: ({ children }) => <ol className="list-none space-y-1 mb-3 ml-0">{children}</ol>,
                      li: ({ children }) => <li className={`text-sm break-words flex items-start ${message.type === 'question' ? 'text-white' : 'text-gray-800'}`}>
                        <span className="text-gray-400 mr-2 mt-0.5 flex-shrink-0">•</span>
                        <span className="flex-1">{children}</span>
                      </li>,
                      p: ({ children }) => <p className={`text-sm ${message.type === 'question' ? 'mb-0' : 'mb-3'} leading-relaxed break-words ${message.type === 'question' ? 'text-white' : 'text-gray-800'}`}>{children}</p>,
                      strong: ({ children }) => <span className={`font-semibold ${message.type === 'question' ? 'text-white' : 'text-gray-900'}`}>{children}</span>
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* Invisible div for auto-scroll target */}
        <div ref={messagesEndRef} />
        
        {(() => {
          return questionFlow === 'initial' && messages.length === 0
        })() && (
          <div className="flex flex-col items-center space-y-3 mt-8">
            {PRESET_QUESTIONS[activeCategory].slice(0, 4).map((question, index) => (
              <button
                key={index}
                onClick={() => handleInitialQuestionClick(index)}
                className="bg-gray-100 text-black px-6 py-4 rounded-full text-center w-80 h-16 flex items-center justify-center hover:bg-gray-200 transition-colors"
              >
                <span className="text-sm font-medium leading-tight">{question}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* New Clean Bottom Question Bar - only show in cycling mode */}
      {questionFlow === 'cycling' && messages.length > 0 && currentQuestion && (
        <BottomQuestionBar
          question={currentQuestion}
          category={activeCategory}
          currentIndex={currentQuestionIndex}
          totalQuestions={totalQuestions}
          isAnalyzing={isAnalyzing}
          onQuestionClick={handleCyclingQuestionClick}
        />
      )}

      {/* Click outside to close burger menu */}
      {showBurgerMenu && (
        <div
          className="fixed inset-0 z-10"
          onClick={() => {
            setShowBurgerMenu(false)
            setShowAccountSelector(false)
          }}
        />
      )}
    </div>
  )
}

export default CreativePageFixed