import {useEffect, useMemo, useRef, useState} from "react"
import {formatDateAsIso, parseIsoDate} from "../utils/date.js"

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]
const WEEKDAY_LABELS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

function getVisibleMonth(value) {
  const parsedDate = parseIsoDate(value)
  const baseDate = parsedDate || new Date()

  return new Date(baseDate.getFullYear(), baseDate.getMonth(), 1)
}

function buildCalendarDays(visibleMonth) {
  const firstDay = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1)
  const startDate = new Date(firstDay)
  startDate.setDate(firstDay.getDate() - firstDay.getDay())

  return Array.from({length: 42}, (_, index) => {
    const date = new Date(startDate)
    date.setDate(startDate.getDate() + index)
    return date
  })
}

function isDateDisabled(dateIso, min, max) {
  return Boolean((min && dateIso < min) || (max && dateIso > max))
}

function formatTypedDate(value) {
  const digits = value.replace(/\D/g, "").slice(0, 8)

  if (digits.length <= 4) {
    return digits
  }

  if (digits.length <= 6) {
    return `${digits.slice(0, 4)}-${digits.slice(4)}`
  }

  return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6)}`
}

export default function AwsDatePicker({
  id,
  name,
  value,
  onChange,
  className = "login-input",
  placeholder = "YYYY-MM-DD",
  required = false,
  disabled = false,
  min,
  max,
  autoComplete = "bday",
}) {
  const rootRef = useRef(null)
  const inputRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [visibleMonth, setVisibleMonth] = useState(() => getVisibleMonth(value))
  const selectedDate = parseIsoDate(value)
  const selectedIso = selectedDate ? formatDateAsIso(selectedDate) : ""
  const todayIso = formatDateAsIso(new Date())

  const calendarDays = useMemo(() => buildCalendarDays(visibleMonth), [visibleMonth])
  const monthLabel = `${MONTH_NAMES[visibleMonth.getMonth()]} ${visibleMonth.getFullYear()}`

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    const handleDocumentMouseDown = (event) => {
      if (!rootRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }
    const handleDocumentKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false)
        inputRef.current?.focus()
      }
    }

    document.addEventListener("mousedown", handleDocumentMouseDown)
    document.addEventListener("keydown", handleDocumentKeyDown)

    return () => {
      document.removeEventListener("mousedown", handleDocumentMouseDown)
      document.removeEventListener("keydown", handleDocumentKeyDown)
    }
  }, [isOpen])

  const updateValue = (nextValue) => {
    onChange(nextValue)
  }

  const handleInputChange = (event) => {
    updateValue(formatTypedDate(event.target.value))
  }

  const shiftMonth = (offset) => {
    setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1))
  }

  const handleDateSelection = (date) => {
    const dateIso = formatDateAsIso(date)

    if (isDateDisabled(dateIso, min, max)) {
      return
    }

    updateValue(dateIso)
    setIsOpen(false)
    inputRef.current?.focus()
  }

  const openCalendar = () => {
    if (disabled) {
      return
    }

    setVisibleMonth(getVisibleMonth(value))
    setIsOpen((current) => !current)
  }

  return (
    <div className="aws-date-picker" ref={rootRef}>
      <input
        ref={inputRef}
        id={id}
        name={name}
        type="text"
        value={value}
        onChange={handleInputChange}
        className={`${className} aws-date-picker-input`}
        placeholder={placeholder}
        inputMode="numeric"
        pattern="\d{4}-\d{2}-\d{2}"
        maxLength={10}
        required={required}
        disabled={disabled}
        min={min}
        max={max}
        autoComplete={autoComplete}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
      />
      <button
        type="button"
        className="aws-date-picker-trigger"
        onClick={openCalendar}
        disabled={disabled}
        aria-label={isOpen ? "Close calendar" : "Open calendar"}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
          <rect x="3" y="4" width="18" height="17" rx="2"/>
          <path d="M8 2v4M16 2v4M3 10h18"/>
        </svg>
      </button>

      {isOpen && (
        <div className="aws-date-picker-popover" role="dialog" aria-label="Choose date">
          <div className="aws-date-picker-header">
            <button
              type="button"
              className="aws-date-picker-nav"
              onClick={() => shiftMonth(-1)}
              aria-label="Previous month"
            >
              <span aria-hidden="true">{"<"}</span>
            </button>
            <div className="aws-date-picker-month">{monthLabel}</div>
            <button
              type="button"
              className="aws-date-picker-nav"
              onClick={() => shiftMonth(1)}
              aria-label="Next month"
            >
              <span aria-hidden="true">{">"}</span>
            </button>
          </div>

          <div className="aws-date-picker-weekdays" aria-hidden="true">
            {WEEKDAY_LABELS.map((weekday) => (
              <span key={weekday}>{weekday}</span>
            ))}
          </div>

          <div className="aws-date-picker-grid">
            {calendarDays.map((date) => {
              const dateIso = formatDateAsIso(date)
              const isOutsideMonth = date.getMonth() !== visibleMonth.getMonth()
              const isSelected = dateIso === selectedIso
              const isToday = dateIso === todayIso
              const isDisabled = isDateDisabled(dateIso, min, max)
              const buttonClassName = [
                "aws-date-picker-day",
                isOutsideMonth ? "aws-date-picker-day-muted" : "",
                isSelected ? "aws-date-picker-day-selected" : "",
                isToday ? "aws-date-picker-day-today" : "",
              ].filter(Boolean).join(" ")

              return (
                <button
                  key={dateIso}
                  type="button"
                  className={buttonClassName}
                  onClick={() => handleDateSelection(date)}
                  disabled={isDisabled}
                  aria-pressed={isSelected}
                >
                  {date.getDate()}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
