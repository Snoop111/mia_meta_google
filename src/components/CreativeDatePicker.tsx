import { useState, useEffect } from 'react'

type Category = 'grow' | 'optimise' | 'protect'

interface CreativeDatePickerProps {
  isOpen: boolean
  startDate: string  // Current selected start date from parent
  category: Category  // Affects date range calculation
  onDateChange: (newStartDate: string, shouldClose?: boolean) => void
  onClose: () => void
}

const CreativeDatePicker = ({ isOpen, startDate, category, onDateChange, onClose }: CreativeDatePickerProps) => {
  // Internal temporary state for the picker (separate from parent's actual selected date)
  const [tempSelectedStartDate, setTempSelectedStartDate] = useState<string>(startDate)

  // Sync temp state when parent startDate changes or picker opens
  useEffect(() => {
    setTempSelectedStartDate(startDate)
  }, [startDate, isOpen])

  // Smart date range calculation - user selects start date, system calculates end date
  const calculateDateRange = (startDate: string, category: Category) => {
    const start = new Date(startDate)
    const daysToAdd = category === 'protect' ? 6 : 30 // 7 days total for protect, 31 days for grow/optimize
    const end = new Date(start)
    end.setDate(start.getDate() + daysToAdd)

    return {
      start: startDate,
      end: end.toISOString().split('T')[0] // Format as YYYY-MM-DD
    }
  }

  // Format date for display (e.g., "02 Jan - 01 Feb") - D/M/Y format (not American M/D/Y)
  const formatDateRangeForDisplay = (startDate: string, endDate: string) => {
    const start = new Date(startDate)
    const end = new Date(endDate)

    const formatDate = (date: Date) => {
      const day = date.getDate().toString().padStart(2, '0')
      const month = date.toLocaleDateString('en-GB', { month: 'short' }) // British format ensures correct month names
      return `${day} ${month}` // Day first, then month (D/M format)
    }

    return `${formatDate(start)} - ${formatDate(end)}`
  }

  // Handle confirming the date selection
  const handleConfirm = () => {
    onDateChange(tempSelectedStartDate, true) // true = close the picker
  }

  // Generate day options (1-31)
  const dayOptions = Array.from({ length: 31 }, (_, i) => i + 1)

  // Generate month options
  const monthOptions = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ]

  // Generate year options (current year ± 2 years)
  const currentYear = new Date().getFullYear()
  const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - 2 + i)

  if (!isOpen) return null

  return (
    <div className="absolute top-8 right-0 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50 min-w-80">
      <div className="text-sm font-medium text-gray-900 mb-3">Select Start Date (DD/MM/YYYY)</div>

      {/* Custom Date Picker - D/M/Y Format */}
      <div className="flex gap-2 mb-3">
        {/* Day */}
        <select
          value={new Date(tempSelectedStartDate).getDate()}
          onChange={(e) => {
            const currentDate = new Date(tempSelectedStartDate)
            currentDate.setDate(parseInt(e.target.value))
            setTempSelectedStartDate(currentDate.toISOString().split('T')[0])
          }}
          className="px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        >
          {dayOptions.map(day => (
            <option key={day} value={day}>{day.toString().padStart(2, '0')}</option>
          ))}
        </select>

        {/* Month */}
        <select
          value={new Date(tempSelectedStartDate).getMonth()}
          onChange={(e) => {
            const currentDate = new Date(tempSelectedStartDate)
            currentDate.setMonth(parseInt(e.target.value))
            setTempSelectedStartDate(currentDate.toISOString().split('T')[0])
          }}
          className="px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm flex-1"
        >
          {monthOptions.map((month, index) => (
            <option key={month} value={index}>{month}</option>
          ))}
        </select>

        {/* Year */}
        <select
          value={new Date(tempSelectedStartDate).getFullYear()}
          onChange={(e) => {
            const currentDate = new Date(tempSelectedStartDate)
            currentDate.setFullYear(parseInt(e.target.value))
            setTempSelectedStartDate(currentDate.toISOString().split('T')[0])
          }}
          className="px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        >
          {yearOptions.map(year => (
            <option key={year} value={year}>{year}</option>
          ))}
        </select>
      </div>

      {/* Preview and Confirm Button */}
      <div className="flex justify-between items-center mt-1">
        <div className="text-xs text-gray-600 font-medium">
          Preview: {formatDateRangeForDisplay(
            tempSelectedStartDate,
            calculateDateRange(tempSelectedStartDate, category).end
          )}
        </div>
        <button
          onClick={handleConfirm}
          className="px-3 py-1.5 bg-black text-white text-xs font-medium rounded-md hover:bg-gray-800 transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  )
}

export default CreativeDatePicker