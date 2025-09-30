
interface BottomQuestionBarProps {
  question: string
  category: string
  currentIndex: number
  totalQuestions: number
  isAnalyzing: boolean
  onQuestionClick: () => void
}

const BottomQuestionBar = ({
  question,
  // category,
  // currentIndex,
  // totalQuestions,
  isAnalyzing,
  onQuestionClick
}: BottomQuestionBarProps) => {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4 z-50">
      <button
        className={`w-full p-4 rounded-2xl font-medium transition-all ${
          isAnalyzing 
            ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
            : 'bg-black text-white hover:bg-gray-800'
        }`}
        onClick={onQuestionClick}
        disabled={isAnalyzing}
      >
        {isAnalyzing ? (
          <div className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            Analyzing...
          </div>
        ) : (
          <div className="text-sm text-center">{question}</div>
        )}
      </button>
    </div>
  )
}

export default BottomQuestionBar