import { useState } from 'react'
import { authService } from '../services/auth'
import { useSession } from '../contexts/SessionContext'
import { apiFetch } from '../utils/api'

interface MainViewProps {
  onLogout: () => void
  onQuestionClick: (questionType: 'growth' | 'improve' | 'fix', data?: any) => void
  onCreativeClick?: () => void
}

const MainViewCopy = ({ onLogout: _onLogout, onQuestionClick, onCreativeClick }: MainViewProps) => {
  const { selectedAccount, availableAccounts, selectAccount, sessionId } = useSession()
  const [showChat, setShowChat] = useState(false)
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'assistant', content: string}>>([])
  const [loadingQuestion, setLoadingQuestion] = useState<string | null>(null) // Track which question is loading
  const [showBurgerMenu, setShowBurgerMenu] = useState(false)
  const [showAccountSelector, setShowAccountSelector] = useState(false) // New state for account selection popout
  const [isChatLoading, setIsChatLoading] = useState(false) // Track chat loading state
  const [isAccountSwitching, setIsAccountSwitching] = useState(false)

  const handleAccountSwitch = async (accountId: string) => {
    if (isAccountSwitching) return

    setIsAccountSwitching(true)
    setShowBurgerMenu(false)
    setShowAccountSelector(false)

    try {
      const success = await selectAccount(accountId)

      if (success) {
        const newAccount = availableAccounts.find(acc => acc.id === accountId)

        // Clear any existing chat messages when switching accounts
        setChatMessages([])

        // Small delay for UX feedback
        setTimeout(() => {
          setIsAccountSwitching(false)
        }, 500)
      } else {
        console.error('❌ [MAIN] Failed to switch account')
        setIsAccountSwitching(false)
      }
    } catch (error) {
      console.error('❌ [MAIN] Account switch error:', error)
      setIsAccountSwitching(false)
    }
  }

  const getAccountIcon = (businessType: string) => {
    switch (businessType?.toLowerCase()) {
      case 'food':
        return '🍎'
      case 'engineering':
        return '⚙️'
      case 'retail':
        return '🏪'
      default:
        return '🏢'
    }
  }

  const starterQuestions = [
    { text: "Where can we grow?", color: "#A2FAE0", dotColor: "#A2FAE0" },
    { text: "What can we improve?", color: "#A7D3FF", dotColor: "#A7D3FF" },  
    { text: "What needs fixing?", color: "#FFC5B0", dotColor: "#FFC5B0" }
  ]

  // Dynamic API URL - works for both desktop and mobile ngrok, context-aware
  const getApiUrl = (context: 'growth' | 'improve' | 'fix') => {
    const endpointMap = {
      'growth': 'growth-data',
      'improve': 'improve-data', 
      'fix': 'fix-data'
    }
    
    const endpoint = endpointMap[context]
    
    // If running via ngrok or production, use relative URL (will be proxied)
    if (window.location.hostname.includes('ngrok') || window.location.hostname !== 'localhost') {
      return `/api/${endpoint}` // Relative URL for proxy
    }
    // Local development - direct backend call
    return `/api/${endpoint}`
  }

  const handleChatSubmit = async (message: string) => {
    if (!message.trim()) return

    // Add user message to chat
    setChatMessages(prev => [...prev, { role: 'user', content: message }])
    
    // Set loading state and scroll to show loading indicator
    setIsChatLoading(true)
    
    // Auto-scroll after user message is added
    setTimeout(() => {
      const chatContainer = document.querySelector('.chat-messages-container')
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight
      }
    }, 100)

    try {
      
      const response = await apiFetch('/api/mia-chat-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId || 'default',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId,
          user_id: '106540664695114193744',
          google_ads_id: selectedAccount?.google_ads_id || '7574136388', // Fallback to DFSA
          ga4_property_id: selectedAccount?.ga4_property_id || '458016659' // Fallback to DFSA
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()

      setIsChatLoading(false) // Remove loading state

      if (result.success && result.claude_response) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: result.claude_response }])
      } else {
        setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I had trouble processing your question. Please try again.' }])
      }
      
      // Auto-scroll to show the top of Mia's response
      setTimeout(() => {
        const chatContainer = document.querySelector('.chat-messages-container')
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight - 100 // Show top of message
        }
      }, 100)
      
    } catch (error) {
      console.error('[CHAT] Error:', error)
      setIsChatLoading(false)
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Please check your connection and try again.' }])
    }
  }

  const fetchQuestionData = async (context: 'growth' | 'improve' | 'fix', question: string) => {
    try {
      // Get selected account from auth service
      const session = authService.getSession()
      const selectedAccount = session?.selectedAccount
      
      const apiUrl = getApiUrl(context)
      const response = await apiFetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          context: context,
          user: 'trystin@11and1.com',
          selected_account: selectedAccount,
          user_id: '106540664695114193744'
        }),
      })
      
      const result = await response.json()
      
      if (result.success && result.data) {
        return result.data
      }
      return null
    } catch (error) {
      console.error(`❌ [MAIN-VIEW] Pre-fetch failed for ${context}:`, error)
      return null
    }
  }

  const handleQuestionClick = async (question: string) => {
    // Start loading state
    setLoadingQuestion(question)
    
    try {
      // Fetch data FIRST, then navigate with data
      let questionType: 'growth' | 'improve' | 'fix'
      let data: any = null
      
      if (question === "Where can we grow?") {
        questionType = 'growth'
        data = await fetchQuestionData('growth', question)
      } else if (question === "What can we improve?") {
        questionType = 'improve' 
        data = await fetchQuestionData('improve', question)
      } else if (question === "What needs fixing?") {
        questionType = 'fix'
        data = await fetchQuestionData('fix', question)
      } else {
        throw new Error('Unknown question')
      }
      
      // Only navigate AFTER data is ready
      onQuestionClick(questionType, data)
      
    } catch (error) {
      console.error('Question handling error:', error)
      // Navigate anyway with fallback (no pre-fetched data)
      if (question === "Where can we grow?") onQuestionClick('growth')
      else if (question === "What can we improve?") onQuestionClick('improve')
      else if (question === "What needs fixing?") onQuestionClick('fix')
    } finally {
      setLoadingQuestion(null) // Clear loading state
    }
  }

  return (
    <div className="w-full h-full safe-full relative bg-white flex flex-col">
      {/* Header - Conditional: Burger Menu OR Back Button - Moved up 20px total */}
      <div className="flex justify-between items-center px-4 py-3 relative z-20 flex-shrink-0" style={{ marginTop: '-20px' }}>
        {!showChat ? (
          <>
            {/* Menu Icon - Using Figma SVG */}
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

                  {/* Divider */}
                  <div className="border-t border-gray-100"></div>

                  {/* Sign Out Button */}
                  <button
                    onClick={() => {
                      _onLogout()
                      setShowBurgerMenu(false)
                    }}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-gray-700">
                      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <div className="font-medium text-gray-900 text-base">Sign Out</div>
                  </button>
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

            {/* Mia Title - Centered properly */}
            <h1 style={{
              color: '#000',
              fontFamily: 'Geologica, system-ui, sans-serif',
              fontSize: '25.518px',
              fontWeight: 400,
              lineHeight: '110%',
              textAlign: 'center'
            }}>Mia</h1>

            {/* Edit Icon - Using Figma SVG */}
            <button className="w-6 h-6 flex items-center justify-center">
              <img src="/icons/edit.svg" alt="Edit" className="w-6 h-6" />
            </button>
          </>
        ) : (
          <>
            {/* Chat Header - Replace burger menu */}
            <button 
              onClick={() => setShowChat(false)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-full border border-gray-100 text-gray-800 font-medium hover:bg-gray-100 transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Back
            </button>
            <h2 className="text-lg font-semibold text-black">Mia</h2>
            <div style={{ width: '60px' }}></div>
          </>
        )}
      </div>

      {/* Main Content - iPhone 16 Pro Layout with better spacing */}
      <div className="flex-1 flex flex-col items-center relative px-6 overflow-hidden">
        {!showChat ? (
          <>
            {/* Mia Avatar - Moved up 10px more (220px to 210px) */}
            <div className="absolute left-1/2 transform -translate-x-1/2" style={{ top: '210px' }}>
              <div 
                className="relative w-[91px] h-[91px] active:scale-95 transition-transform duration-150 cursor-pointer"
                style={{
                  WebkitTapHighlightColor: 'transparent',
                  touchAction: 'manipulation'
                }}
              >
                {/* Vector.png background */}
                <img 
                  src="/icons/Vector.png" 
                  alt="Mia Avatar Background" 
                  className="w-full h-full object-cover"
                />
                
                {/* Mia.png text overlay - perfectly centered */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <img 
                    src="/icons/Mia.png" 
                    alt="Mia" 
                    className="w-[37px] h-[23px] object-contain"
                    style={{
                      position: 'absolute',
                      top: '47%',
                      left: '52%',
                      transform: 'translate(-50%, -50%)'
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Greeting - Moved down 5px (301px to 306px), wider for single line */}
            <div className="absolute left-1/2 transform -translate-x-1/2 text-center" style={{ top: '306px', width: '320px' }}>
              <h2 style={{
                color: '#000',
                textAlign: 'center',
                fontFamily: 'Inter, system-ui, sans-serif',
                fontSize: '26px',
                fontStyle: 'normal',
                fontWeight: 400,
                lineHeight: '110%',
                letterSpacing: '-0.78px',
                marginBottom: '0px'
              }}>Hey Sean,</h2>
              <p style={{
                color: 'rgba(0, 0, 0, 0.40)',
                fontFamily: 'Inter, system-ui, sans-serif',
                fontSize: '26px',
                fontStyle: 'normal',
                fontWeight: 400,
                lineHeight: '110%',
                letterSpacing: '-0.78px',
                margin: '0px'
              }}>How can I help today?</p>
            </div>

            {/* Starter Questions - TEMPORARILY HIDDEN FOR UI REDESIGN */}

            {/* Chat with Mia Button - Moved up 20px more (465px to 445px) */}
            <div className="absolute left-1/2 transform -translate-x-1/2" style={{ top: '445px' }}>
              <button
                onClick={(e) => {
                  e.preventDefault()
                  // Small delay to show touch feedback before navigation
                  setTimeout(() => setShowChat(true), 150)
                }}
                className="inline-flex items-center gap-2 px-4 py-3 bg-black text-white rounded-full font-medium text-sm hover:bg-gray-800 transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95"
                style={{ 
                  minWidth: '160px', 
                  justifyContent: 'center',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                  WebkitTapHighlightColor: 'transparent',
                  touchAction: 'manipulation'
                }}
              >
                <img src="/icons/message-square.svg" alt="Chat" width="16" height="16" />
                Chat with Mia
              </button>
            </div>

            {/* Creative Insights Button - Moved up 20px more (520px to 500px) */}
            {onCreativeClick && (
              <div className="absolute left-1/2 transform -translate-x-1/2" style={{ top: '500px' }}>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    // Small delay to show touch feedback before navigation
                    if (onCreativeClick) {
                      setTimeout(() => onCreativeClick(), 150)
                    }
                  }}
                  className="inline-flex items-center gap-2 px-5 py-3 bg-black text-white rounded-full font-medium text-sm hover:bg-gray-800 transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95"
                  style={{ 
                    minWidth: '190px', 
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                    WebkitTapHighlightColor: 'transparent',
                    touchAction: 'manipulation'
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13,2 3,14 12,14 11,22 21,10 12,10"></polygon>
                  </svg>
                  Creative Insights
                </button>
              </div>
            )}
            
          </>
        ) : (
          /* Chat Interface - iPhone 16 Optimized with proper flex layout */
          <div className="w-full h-full flex flex-col" style={{ maxWidth: '393px' }}>
            {/* Chat Messages - Scrollable area */}
            <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4 chat-messages-container">
              {chatMessages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-2xl ${
                    message.role === 'user' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-50 text-gray-800 border border-gray-100'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                  </div>
                </div>
              ))}
              
              {/* Loading Indicator */}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-50 border border-gray-100 rounded-2xl p-3 max-w-[85%]">
                    <div className="flex items-center gap-2 text-gray-600">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm">Mia is analyzing...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input - Fixed at bottom and centered */}
            <div className="flex-shrink-0 p-3 border-t border-gray-100 bg-white flex justify-center">
              <div className="flex gap-2" style={{ maxWidth: '393px', width: '100%' }}>
                <input
                  type="text"
                  placeholder="Ask about your marketing performance..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      const target = e.target as HTMLInputElement
                      handleChatSubmit(target.value)
                      target.value = ''
                    }
                  }}
                />
                <button
                  onClick={() => {
                    const input = document.querySelector('input[type="text"]') as HTMLInputElement
                    if (input?.value.trim()) {
                      handleChatSubmit(input.value)
                      input.value = ''
                    }
                  }}
                  className="px-4 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors text-sm font-medium"
                  disabled={isChatLoading}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        )}
      </div>


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

export default MainViewCopy