import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import FigmaLoginModal from './FigmaLoginModal'
import { authService } from '../services/auth'

interface VideoIntroViewProps {
  onAuthSuccess?: () => void
}

const VideoIntroView = ({ onAuthSuccess }: VideoIntroViewProps) => {
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [videoPhase, setVideoPhase] = useState<'intro' | 'looping'>('intro')
  const [modalTimerSet, setModalTimerSet] = useState(false)
  const [videoLoaded, setVideoLoaded] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const modalTimerRef = useRef<NodeJS.Timeout | null>(null)
  
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      const currentTime = video.currentTime
      const duration = video.duration

      // Show modal at 33 seconds (only once)
      if (duration && currentTime >= 33 && !modalTimerSet && !showLoginModal) {
        setModalTimerSet(true)
        setShowLoginModal(true)
      }

      // Check if we've reached the looping section (last 10 seconds)
      if (duration && currentTime >= (duration - 10) && videoPhase === 'intro') {
        setVideoPhase('looping')
      }

      // Handle seamless looping - jump back to loop start before video ends
      if (videoPhase === 'looping' && duration && currentTime >= duration - 0.1) {
        video.currentTime = duration - 10
      }
    }

    const handleEnded = () => {
      // This should rarely fire due to seamless loop handling above
      if (videoPhase === 'intro') {
        setVideoPhase('looping')
        const duration = video.duration
        if (duration) {
          video.currentTime = duration - 10
          video.play()
        }
        // Show modal after delay
        modalTimerRef.current = setTimeout(() => {
          setShowLoginModal(true)
        }, 3000)
      } else {
        // In loop phase - restart the loop section
        const duration = video.duration
        if (duration) {
          video.currentTime = duration - 10
          video.play()
        }
      }
    }

    const handleLoadedMetadata = () => {
      setVideoLoaded(true)
    }

    const handleCanPlayThrough = () => {
      video.play().catch(error => {
        console.error('🚫 Video autoplay failed:', error)
        // Fallback: show modal immediately if video fails to play
        setShowLoginModal(true)
      })
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('ended', handleEnded)
    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('canplaythrough', handleCanPlayThrough)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('ended', handleEnded)
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('canplaythrough', handleCanPlayThrough)
      
      if (modalTimerRef.current) {
        clearTimeout(modalTimerRef.current)
      }
    }
  }, []) // Remove videoPhase dependency to prevent effect re-running

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Fullscreen Video Background */}
      <video
        ref={videoRef}
        className="absolute inset-0 w-full h-full object-cover"
        muted
        playsInline
        preload="auto"
        crossOrigin="anonymous"
        style={{ willChange: 'transform' }}
      >
        <source src="/videos/Mia_AppIntroVideo_v03.1.mp4" type="video/mp4" />
        <div className="w-full h-full bg-gradient-to-br from-purple-600 via-blue-600 to-pink-600">
          {/* Fallback gradient if video fails to load */}
          <div className="flex items-center justify-center h-full">
            <div className="text-white text-4xl font-bold">Mia</div>
          </div>
        </div>
      </video>

      {/* Login Modal - slides up from bottom */}
      <AnimatePresence>
        {showLoginModal && (
          <FigmaLoginModal 
            onAuthSuccess={onAuthSuccess}
          />
        )}
      </AnimatePresence>

    </div>
  )
}

export default VideoIntroView