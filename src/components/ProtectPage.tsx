import { apiFetch } from '../utils/api'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { authService } from '../services/auth'

interface ProtectData {
  header: {
    percentage: number
    description: string
    icon: string
  }
  insights: string[]
  roas: {
    percentage: number
    trend: string
    label: string
  }
  boxes: Array<{
    value: string
    label: string
    trend: string
    unit?: string
  }>
  prediction: {
    amount: string
    confidence: string
    description: string
  }
}

interface ProtectPageProps {
  onBack?: () => void
  question?: string
  isLoading?: boolean
  data?: ProtectData
}

const ProtectPage = ({ onBack, question = "What needs protecting?", isLoading = false, data }: ProtectPageProps) => {
  const [protectData, setProtectData] = useState<ProtectData | null>(data || null)
  const [loading, setLoading] = useState(isLoading)
  const [error, setError] = useState<string | null>(null)

  // Fetch data when component mounts if not provided
  useEffect(() => {
    if (data) {
      // Use pre-loaded data
      setProtectData(data)
      setLoading(false)
    } else if (question) {
      // Fallback to fetch if no pre-loaded data
      fetchProtectData()
    }
  }, [data, question])

  const fetchProtectData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Get selected account from auth service
      const session = authService.getSession()
      const selectedAccount = session?.selectedAccount
      
      const response = await apiFetch('/api/fix-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          context: 'protect',
          user: 'trystin@11and1.com',
          selected_account: selectedAccount,
          user_id: '106540664695114193744' // TODO: Get from auth service
        }),
      })
      
      const result = await response.json()
      
      if (result.success && result.data) {
        setProtectData(result.data)
        setError(null)
      } else {
        setError('Unable to load protection data. Please try again.')
        setProtectData(getErrorFallbackData())
      }
    } catch (error) {
      console.error('💥 [PROTECT-PAGE] Failed to fetch protect data:', error)
      setError('Connection error. Please check your connection.')
      setProtectData(getErrorFallbackData())
    } finally {
      setLoading(false)
    }
  }

  // Error fallback data
  const getErrorFallbackData = (): ProtectData => ({
    header: {
      percentage: 0,
      description: "Unable to load\nmarketing data",
      icon: "error"
    },
    insights: [
      "Marketing data unavailable",
      "Please check your connection and try again",
      "Contact support if issues persist"
    ],
    roas: {
      percentage: 0,
      trend: "neutral",
      label: "Error"
    },
    boxes: [
      {
        value: "N/A",
        label: "Data unavailable",
        trend: "neutral"
      },
      {
        value: "N/A",
        label: "Try again",
        unit: "",
        trend: "neutral"
      }
    ],
    prediction: {
      amount: "N/A",
      confidence: "0%",
      description: "Unable to generate recommendations without data"
    }
  })

  // Default loading fallback data
  const defaultData: ProtectData = {
    header: {
      percentage: 0,
      description: "Loading marketing\ninsights...",
      icon: "loading"
    },
    insights: [
      "Analyzing campaign performance data...",
      "Processing conversion metrics...",
      "Calculating optimization opportunities..."
    ],
    roas: {
      percentage: 0,
      trend: "neutral",
      label: "Loading..."
    },
    boxes: [
      {
        value: "...",
        label: "Loading metrics...",
        trend: "neutral"
      },
      {
        value: "...",
        label: "Loading data...",
        unit: "",
        trend: "neutral"
      }
    ],
    prediction: {
      amount: "Loading...",
      confidence: "0%",
      description: "Generating AI-powered recommendations based on your data..."
    }
  }

  const displayData = protectData || defaultData
  return (
    <motion.div 
      className="w-full h-screen bg-white overflow-y-auto"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      style={{ maxWidth: '393px', margin: '0 auto' }}
    >
      {/* Top Navigation Bar - aligned with blue container rounded edges */}
      <div 
        className="flex justify-between items-center bg-white"
        style={{ 
          height: '50px', // Reduced height
          paddingTop: '8px', // Even less top padding
          paddingLeft: '16px', // Move burger further left 
          paddingRight: '16px' // Move clipboard further right
        }}
      >
        {/* Burger Menu (left) */}
        <button className="w-6 h-6 flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M3 12H21" stroke="#3C3C3C" strokeWidth="2" strokeLinecap="round"/>
            <path d="M3 6H21" stroke="#3C3C3C" strokeWidth="2" strokeLinecap="round"/>
            <path d="M3 18H21" stroke="#3C3C3C" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        
        {/* Mia Text (center) */}
        <h1 
          style={{
            fontSize: '20px',
            fontWeight: 600,
            color: '#000000',
            fontFamily: 'Figtree, Inter, sans-serif'
          }}
        >
          Mia
        </h1>
        
        {/* Clipboard Icon (right) */}
        <button className="w-6 h-6 flex items-center justify-center relative">
          {/* Clipboard Icon */}
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style={{ position: 'absolute' }}>
            <path d="M11 4H6.8C5.11984 4 4.27976 4 3.63803 4.32698C3.07354 4.6146 2.6146 5.07354 2.32698 5.63803C2 6.27976 2 7.11984 2 8.8V17.2C2 18.8802 2 19.7202 2.32698 20.362C2.6146 20.9265 3.07354 21.3854 3.63803 21.673C4.27976 22 5.11984 22 6.8 22H15.2C16.8802 22 17.7202 22 18.362 21.673C18.9265 21.3854 19.3854 20.9265 19.673 20.362C20 19.7202 20 18.8802 20 17.2V13" stroke="#3C3C3C" strokeOpacity="0.3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M8 14.3255C8 13.8363 8 13.5917 8.05526 13.3615C8.10425 13.1575 8.18506 12.9624 8.29472 12.7834C8.4184 12.5816 8.59136 12.4086 8.93726 12.0627L18.5 2.5C19.3285 1.67157 20.6716 1.67157 21.5 2.5V2.5C22.3285 3.32843 22.3285 4.67157 21.5 5.5L11.9373 15.0627C11.5914 15.4086 11.4184 15.5816 11.2166 15.7053C11.0377 15.8149 10.8426 15.8957 10.6385 15.9447C10.4083 16 10.1637 16 9.67454 16H8V14.3255Z" stroke="#3C3C3C" strokeOpacity="0.3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
      
      {/* Header with gradient background - moved up closer to top nav */}
      <div 
        className="relative flex flex-col"
        style={{
          height: '200px', // Exact Figma height
          marginTop: '5px', // Reduced margin to move blue header up
          background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.60) 0%, rgba(255, 255, 255, 0.00) 67.79%), #FFC5B0',
          backgroundBlendMode: 'screen, normal',
          padding: '19.109px 31.848px', // Exact Figma padding
          borderRadius: '20px', // Exact Figma border-radius
          justifyContent: 'flex-end', // Pushes content to bottom - KEY FIX!
          alignItems: 'flex-start',
          gap: '14px',
          alignSelf: 'stretch'
        }}
      >
        {/* Dynamic icon - Facebook/Google/LinkedIn */}
        {displayData.header.icon === 'facebook' && (
          <svg 
            width="24" 
            height="24" 
            viewBox="0 0 24 24" 
            fill="none"
            style={{
              position: 'absolute',
              top: '50px',
              left: '31px'
            }}
          >
            <circle cx="12" cy="12" r="12" fill="#000000" />
            <path 
              d="M15.12 12.72H13.2V18H10.56V12.72H9.24V10.56H10.56V9.36C10.56 7.92 11.28 6.96 13.08 6.96H14.64V9.12H13.68C13.08 9.12 13.2 9.36 13.2 9.84V10.56H14.64L14.4 12.72H13.2Z" 
              fill="white"
            />
          </svg>
        )}
        {displayData.header.icon === 'google' && (
          <svg 
            width="24" 
            height="24" 
            viewBox="0 0 24 24" 
            fill="none"
            style={{
              position: 'absolute',
              top: '50px',
              left: '31px'
            }}
          >
            <circle cx="12" cy="12" r="12" fill="#000000" />
            <path 
              d="M12 7.5C13.4 7.5 14.6 8 15.5 8.9L17.4 7C16 5.7 14.1 5 12 5C9.1 5 6.6 6.6 5.4 9.1L7.7 10.9C8.3 8.9 10 7.5 12 7.5Z" 
              fill="white"
            />
            <path 
              d="M19 12C19 11.3 18.9 10.7 18.8 10H12V14H16.1C15.8 15.3 15.1 16.4 14 17.1L16.3 18.9C18.1 17.2 19 14.8 19 12Z" 
              fill="white"
            />
            <path 
              d="M7.7 13.1L5.4 14.9C6.6 17.4 9.1 19 12 19C14.1 19 16 18.3 17.4 17L15.1 15.2C14.4 15.7 13.3 16 12 16C10 16 8.3 14.6 7.7 13.1Z" 
              fill="white"
            />
          </svg>
        )}

        {/* Main percentage and text - COPIED FROM PERFECT GROWTH PAGE */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'baseline', 
          gap: '8px'
        }}>
          {/* Percentage container - EXACT GROWTH PAGE STRUCTURE */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'baseline', 
            gap: '2px',
            transform: 'translateY(6px)' // EXACT SAME AS GROWTH PAGE
          }}>
            <span 
              style={{
                fontSize: '100px', // FIXED SIZE LIKE GROWTH PAGE
                fontWeight: '600',
                lineHeight: '0.8', // Tighter line height for better baseline alignment
                color: '#000000',
                fontFamily: 'Inter, sans-serif',
                letterSpacing: '-5px' // EXACT SAME AS GROWTH PAGE
              }}
            >
              {loading ? '...' : displayData.header.percentage}
            </span>
            <span 
              style={{
                fontSize: '50px', // FIXED SIZE LIKE GROWTH PAGE
                fontWeight: '600',
                lineHeight: '0.8', // Match line height
                color: '#000000',
                fontFamily: 'Inter, sans-serif',
                letterSpacing: '-2.5px'
              }}
            >
              %
            </span>
          </div>
          
          {/* Dynamic description text - EXACT GROWTH PAGE STRUCTURE */}
          <div 
            style={{
              fontSize: '14px',
              fontWeight: '500', // Slightly bolder (was 400)
              color: '#000000',
              lineHeight: '1.2',
              marginLeft: '4px',
              letterSpacing: '-0.3px', // Compact letter spacing to reduce width
              transform: 'translateY(-15px)' // EXACT SAME AS GROWTH PAGE
            }}
          >
            {loading ? 'Loading...' : displayData.header.description.split('\n').map((line, i) => (
              <span key={i}>
                {line}
                {i < displayData.header.description.split('\n').length - 1 && <br />}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Navigation bar with back and bookmark - adjusted positioning */}
      <div 
        className="flex justify-between items-center bg-white"
        style={{ padding: '14px 24px 14px 24px', height: '71px' }} // Reduced horizontal padding to allow more movement
      >
        {/* Back button - moved slightly left with centered, bolder arrow */}
        <button 
          onClick={onBack}
          className="flex items-center justify-center gap-1 bg-white border border-gray-300 rounded-full hover:bg-gray-50 active:bg-gray-100 transition-colors"
          style={{
            width: '72px',
            height: '32px',
            fontSize: '14px',
            color: '#000000',
            marginLeft: '-4px' // Move slightly left
          }}
        >
          <span style={{ 
            fontSize: '16px', 
            fontWeight: '600',
            color: '#333333',
            lineHeight: '1',
            transform: 'translateY(-2px)' // Move arrow up slightly higher to center with "B"
          }}>←</span>
          <span>Back</span>
        </button>

        {/* Bookmark icon with circle background - moved slightly right */}
        <div 
          className="flex items-center justify-center relative"
          style={{
            width: '43px',
            height: '43px',
            marginRight: '-4px' // Move slightly right
          }}
        >
          {/* Circle background */}
          <svg width="43" height="43" viewBox="0 0 43 43" fill="none" style={{ position: 'absolute' }}>
            <g style={{ mixBlendMode: 'multiply' }}>
              <circle cx="21.5" cy="21.5" r="21" stroke="#ADADAD"/>
            </g>
          </svg>
          
          {/* Bookmark icon */}
          <svg width="15" height="21" viewBox="0 0 15 21" fill="none">
            <g style={{ mixBlendMode: 'multiply' }}>
              <path fillRule="evenodd" clipRule="evenodd" d="M0.87868 0.87868C1.44129 0.316071 2.20435 0 3 0H12C12.7956 0 13.5587 0.316071 14.1213 0.87868C14.6839 1.44129 15 2.20435 15 3V20.25C15 20.5453 14.8267 20.8132 14.5572 20.9342C14.2878 21.0552 13.9725 21.0068 13.7517 20.8106L7.5 15.2535L1.24827 20.8106C1.02753 21.0068 0.712183 21.0552 0.442758 20.9342C0.173333 20.8132 0 20.5453 0 20.25V3C0 2.20435 0.316071 1.44129 0.87868 0.87868ZM3 1.5C2.60218 1.5 2.22064 1.65804 1.93934 1.93934C1.65804 2.22064 1.5 2.60218 1.5 3V18.5799L7.00173 13.6894C7.28589 13.4369 7.71411 13.4369 7.99827 13.6894L13.5 18.5799V3C13.5 2.60218 13.342 2.22064 13.0607 1.93934C12.7794 1.65804 12.3978 1.5 12 1.5H3Z" fill="#ADADAD"/>
            </g>
          </svg>
        </div>
      </div>

      {/* Overall section - pushed up more to show 67% */}
      <div style={{ padding: '16px 31px 12px 31px' }}>
        <h3 
          style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#000000',
            marginBottom: '6px', // Reduced from 12px to create smaller gap
            fontFamily: 'Figtree, Inter, sans-serif',
            marginLeft: '-16px' // Push "OVERALL" closer to left edge (half the current padding)
          }}
        >
          OVERALL
        </h3>
        
        <div className="space-y-4">
          {loading ? (
            <div 
              style={{
                fontSize: '14px',
                lineHeight: '1.4',
                color: '#000000',
                paddingLeft: '10px',
                textIndent: '-10px'
              }}
            >
              • Loading insights...
            </div>
          ) : (
            displayData.insights.map((insight, index) => (
              <div 
                key={index}
                style={{
                  fontSize: '14px',
                  lineHeight: '1.4',
                  color: '#000000',
                  paddingLeft: '10px',
                  textIndent: '-10px'
                }}
              >
                • {insight}
              </div>
            ))
          )}
        </div>
      </div>

      {/* ROAS Section - Reduced spacing to show 67% without scrolling */}
      <div 
        style={{
          padding: '0 16px', // Much smaller horizontal padding to push content left
          marginTop: '24px', // Reduced to match new OVERALL spacing
          marginBottom: '24px'
        }}
      >
        <div className="flex items-center" style={{ gap: '12px' }}>
          {/* Grey ROAS container - widened to match Figma */}
          <div 
            className="rounded-3xl flex-shrink-0"
            style={{
              backgroundColor: '#F2F2F2',
              padding: '16px',
              width: '200px', // Wider to match Figma proportions
              height: '247px'
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <h4 
                style={{
                  fontSize: '13px', // Exact Figma measurement
                  fontWeight: '600',
                  color: '#21272A' // Exact Figma color (CoolGray-90)
                }}
              >
                {loading ? 'LOADING' : displayData.roas.label}
              </h4>
              {/* Info icon with exact Figma specifications */}
              <div 
                style={{
                  display: 'flex',
                  width: '13.334px',
                  height: '13.334px',
                  padding: '1.841px 7.365px',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '9.206px',
                  borderRadius: '9.206px',
                  opacity: '0.2',
                  background: '#C2C2C2' // Correct outer circle color
                }}
              >
                <svg width="3" height="10" viewBox="0 0 3 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M0.758591 9.3145V3.33048H1.89555V9.3145H0.758591ZM1.33306 2.06187C1.14955 2.06187 0.989973 1.99405 0.854336 1.85841C0.718698 1.7148 0.650879 1.55123 0.650879 1.36772C0.650879 1.17624 0.718698 1.01666 0.854336 0.889003C0.989973 0.753366 1.14955 0.685547 1.33306 0.685547C1.52455 0.685547 1.68412 0.753366 1.81178 0.889003C1.94742 1.01666 2.01523 1.17624 2.01523 1.36772C2.01523 1.55123 1.94742 1.7148 1.81178 1.85841C1.68412 1.99405 1.52455 2.06187 1.33306 2.06187Z" fill="#000000"/>
                </svg>
              </div>
            </div>

            {/* 3/4 arc progress chart - using peachy page sizing + 3/4 arc + thick stroke */}
            <div className="flex justify-center">
              <div className="relative flex items-center justify-center" style={{ width: '160px', height: '160px' }}>
                <svg width="160" height="160" viewBox="0 0 160 160" fill="none">
                  {/* Background 3/4 arc - thicker */}
                  <path 
                    d="M 30 125 A 60 60 0 1 1 130 125"
                    stroke="#DBDFEC"
                    strokeWidth="12"
                    fill="none"
                    strokeLinecap="round"
                  />
                  {/* Dynamic blue progress - thicker, proper calculation */}
                  <path 
                    d="M 30 125 A 60 60 0 1 1 130 125"
                    stroke="#71BBEA"
                    strokeWidth="12"
                    fill="none"
                    strokeLinecap="round"
                    pathLength="100"
                    strokeDasharray="100"
                    strokeDashoffset={`${100 - (protectData?.roas?.percentage || 0)}`}
                    style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
                  />
                </svg>
                
                {/* Center percentage - moved down to center with 3/4 arc */}
                <div 
                  className="absolute inset-0 flex items-center justify-center"
                  style={{
                    fontSize: '32px',
                    fontWeight: '600',
                    color: '#000000',
                    fontFamily: 'Figtree',
                    lineHeight: '100%',
                    letterSpacing: '-0.64px',
                    textAlign: 'center',
                    transform: 'translateY(10px)' // Move down to center with 3/4 arc
                  }}
                >
                  {loading ? '...' : `${displayData.roas.percentage}%`}
                </div>
              </div>
            </div>
          </div>

          {/* Black boxes - Squashed to match Figma proportions */}
          <div className="flex flex-col" style={{ gap: '8px', width: '140px' }}>
            {/* Top box - 6% - Shorter height to match Figma proportions */}
            <div 
              className="relative text-white"
              style={{
                backgroundColor: '#000000',
                borderRadius: '20px',
                border: '1px solid #000',
                height: '95px', // Reduced from 113px - more compact like Figma
                padding: '14px'
              }}
            >
              {/* Dynamic trend text + arrow - positioned top-left above value */}
              <div 
                className="absolute flex items-center"
                style={{ 
                  top: '8px',
                  left: '20px', // Will align with left edge of value
                  gap: '6px' // Small gap between text and arrow
                }}
              >
                <span
                  style={{
                    fontSize: '9px', // Same as "Up from last month" text
                    fontWeight: '400', 
                    lineHeight: '12.6px', // Same as "Up from last month"
                    letterSpacing: '0.1px', // Wider letter spacing (not negative)
                    color: '#F2F2F2',
                    fontFamily: 'Inter, sans-serif'
                  }}
                >
                  {loading ? 'Loading' : (displayData.boxes[0]?.trend === 'up' ? 'Improved' : displayData.boxes[0]?.trend === 'down' ? 'Declined' : 'Stable')}
                </span>
                
                {/* Arrow - to the right of "Improved" text */}
                <svg width="19" height="20" viewBox="0 0 19 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4.08939 2.33139C4.08945 1.74702 4.56299 1.27349 5.14729 1.2735H17.3684C17.9527 1.27355 18.4262 1.7471 18.4263 2.33139V14.5525C18.4263 15.1368 17.9527 15.6103 17.3684 15.6104C16.7841 15.6103 16.3105 15.1368 16.3105 14.5525V5.61005L16.3112 4.88568L2.0316 19.1652L0.534523 17.6682L14.8141 3.3886L14.0897 3.38929H5.14729C4.56297 3.38929 4.08948 2.91569 4.08939 2.33139Z" fill="#F2F2F2" stroke="black" strokeWidth="0.6"/>
                </svg>
              </div>

              {/* Main content: Dynamic value */}
              <div className="flex flex-col justify-center h-full" style={{ marginTop: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px' }}>
                  <span
                    style={{
                      fontSize: '46.484px',
                      fontWeight: '600',
                      lineHeight: '1.0', // Tighter for better baseline control
                      letterSpacing: '-2.324px',
                      color: '#F2F2F2',
                      fontFamily: 'SF Pro Rounded, Avenir Next, Futura, system-ui, sans-serif' // Try rounded/curved fonts
                    }}
                  >
                    {loading ? '...' : (displayData.boxes[0]?.value || '').replace('%', '')}
                  </span>
                  {(displayData.boxes[0]?.value || '').includes('%') && (
                    <span
                      style={{
                        fontSize: '23px', // Scaled down like 67% proportion
                        fontWeight: '600',
                        lineHeight: '1.0', // Match the baseline
                        letterSpacing: '-0.64px', // Scaled down letter spacing
                        color: '#F2F2F2',
                        fontFamily: 'SF Pro Rounded, Avenir Next, Futura, system-ui, sans-serif', // Match font
                        marginLeft: '1px' // Push % closer back toward number
                      }}
                    >
                      %
                    </span>
                  )}
                </div>
                
                {/* Dynamic label - positioned below number */}
                <div 
                  style={{
                    fontSize: '9px',
                    fontWeight: '400',
                    lineHeight: '12.6px',
                    letterSpacing: '-0.169px',
                    color: '#F2F2F2',
                    fontFamily: 'Inter, sans-serif',
                    marginTop: '2px', // Moved up (reduced from 4px)
                    marginLeft: '2px' // Moved slightly to the right
                  }}
                >
                  {loading ? 'Loading...' : displayData.boxes[0]?.label || 'Up from last month'}
                </div>
              </div>
            </div>

            {/* Bottom box - 1:45 min - Taller rectangle to match Figma proportions */}
            <div 
              className="relative text-white"
              style={{
                backgroundColor: '#000000',
                borderRadius: '20px',
                border: '1px solid #000',
                height: '144px', // Increased from 113px - more rectangular like Figma
                padding: '14px'
              }}
            >
              {/* Dynamic trend text + arrow - positioned top-left */}
              <div 
                className="absolute flex items-center"
                style={{ 
                  top: '8px', // Same relative position as top box
                  left: '20px', // Same relative position as top box
                  gap: '6px' // Same gap as top box
                }}
              >
                <span
                  style={{
                    fontSize: '9px', // Same as "Improved" and "Up from last month" 
                    fontWeight: '400', 
                    lineHeight: '12.6px', // Same as "Improved"
                    letterSpacing: '0.1px', // Same wider spacing as "Improved"
                    color: '#F2F2F2',
                    fontFamily: 'Inter, sans-serif'
                  }}
                >
                  {loading ? 'Loading' : (displayData.boxes[1]?.trend === 'up' ? 'Improved' : displayData.boxes[1]?.trend === 'down' ? 'Declined' : 'Stable')}
                </span>
                
                {/* Down-right arrow - using same SVG but rotated for down-right */}
                <svg width="19" height="20" viewBox="0 0 19 20" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ transform: 'rotate(90deg)' }}>
                  <path d="M4.08939 2.33139C4.08945 1.74702 4.56299 1.27349 5.14729 1.2735H17.3684C17.9527 1.27355 18.4262 1.7471 18.4263 2.33139V14.5525C18.4263 15.1368 17.9527 15.6103 17.3684 15.6104C16.7841 15.6103 16.3105 15.1368 16.3105 14.5525V5.61005L16.3112 4.88568L2.0316 19.1652L0.534523 17.6682L14.8141 3.3886L14.0897 3.38929H5.14729C4.56297 3.38929 4.08948 2.91569 4.08939 2.33139Z" fill="#F2F2F2" stroke="black" strokeWidth="0.6"/>
                </svg>
              </div>

              {/* Main content: Dynamic value repositioned left-aligned with more padding above */}
              <div className="flex flex-col h-full" style={{ paddingTop: '40px', paddingLeft: '8px', paddingRight: '8px' }}>
                
                {/* Dynamic main value */}
                <div style={{ marginBottom: '0px', marginLeft: '-4px', marginTop: '-2px' }}>
                  <span
                    style={{
                      fontSize: '46.484px', // Keep it big
                      fontWeight: '600',
                      lineHeight: '1.0',
                      letterSpacing: '-2.324px',
                      color: '#F2F2F2',
                      fontFamily: 'SF Pro Rounded, Avenir Next, Futura, system-ui, sans-serif'
                    }}
                  >
                    {loading ? '...' : displayData.boxes[1]?.value || ''}
                  </span>
                </div>
                
                {/* Dynamic unit - pushed up closer to main value, further left and thinner */}
                {displayData.boxes[1]?.unit && (
                  <div 
                    style={{
                      fontSize: '23.242px',
                      fontWeight: '500', // Reduced from 600 to 500 (thinner)
                      lineHeight: '32.529px',
                      letterSpacing: '-1.162px',
                      color: '#F2F2F2',
                      fontFamily: 'Inter, sans-serif',
                      marginLeft: '-6px', // Pushed further left
                      marginTop: '-8px', // Pull up closer to main value
                      marginBottom: '4px' // Further reduced spacing to bottom text
                    }}
                  >
                    {displayData.boxes[1].unit}
                  </div>
                )}
                
                {/* Dynamic label - spaced out more to extend further right */}
                <div 
                  style={{
                    fontSize: '8px', // Made smaller (was 9px)
                    fontWeight: '400',
                    lineHeight: '11.2px', // Proportionally adjusted
                    letterSpacing: '0.2px', // Increased from -0.169px to spread out more
                    color: '#F2F2F2',
                    fontFamily: 'Inter, sans-serif',
                    marginLeft: '-4px', // Align with unit text
                    marginTop: '-2px', // Just a small nudge up
                    whiteSpace: 'nowrap' // Keep it on single line
                  }}
                >
                  {loading ? 'Loading...' : displayData.boxes[1]?.label || 'Avg. time spent on-site'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mia's Prediction Section - moderate white space */}
      <div style={{ padding: '12px 31px 20px 31px', marginTop: '8px' }}>
        <div className="flex items-start justify-between mb-3" style={{ alignItems: 'flex-start' }}>
          <h3 
            style={{
              fontSize: '16px',
              fontWeight: '600',
              color: '#000000'
            }}
          >
            Mia's Prediction
          </h3>
          <div className="flex gap-2" style={{ marginTop: '-8px', marginRight: '8px' }}>
            <button 
              className="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: '1px solid #E5E5E5'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 12L6 8L10 4" stroke="#666" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <button 
              className="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: '1px solid #E5E5E5'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 4L10 8L6 12" stroke="#666" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        <div className="mb-4" style={{ marginLeft: '12px' }}>
          <p 
            style={{
              fontSize: '12px',
              lineHeight: '1.4',
              color: '#000000',
              marginBottom: '16px',
              paddingLeft: '8px',
              textIndent: '-8px'
            }}
          >
            • {loading ? 'Loading prediction...' : displayData.prediction.description}
          </p>
        </div>

        <div 
          style={{
            fontSize: '52px', // 1 size bigger
            fontWeight: '600',
            color: '#000000',
            marginBottom: '12px', // Reduced from 16px
            marginTop: '-12px', // Raised up more (was -8px)
            marginLeft: '8px', // Moved left a bit (was 12px)
            letterSpacing: '0.5px', // Stretch out more to extend right
            fontFamily: 'SF Pro Display, Helvetica Neue, Arial, sans-serif' // Different font
          }}
        >
          {loading ? '...' : displayData.prediction.amount}
        </div>

        <button 
          className="rounded-full text-white text-sm font-medium"
          style={{ 
            backgroundColor: '#000000',
            marginLeft: '6px', // Pushed slightly more left (was 8px)
            paddingLeft: '14px', // Very slightly more compact (was px-4 = 16px)
            paddingRight: '14px',
            paddingTop: '8px', // Same as py-2
            paddingBottom: '8px'
          }}
        >
          {loading ? 'Loading...' : `${displayData.prediction.confidence} Confidence Score`}
        </button>
      </div>

      {/* Bottom padding to ensure scrolling past confidence score */}
      <div style={{ height: '85px', backgroundColor: 'white' }}>
        {/* Extra space for scrolling */}
      </div>
    </motion.div>
  )
}

export default ProtectPage