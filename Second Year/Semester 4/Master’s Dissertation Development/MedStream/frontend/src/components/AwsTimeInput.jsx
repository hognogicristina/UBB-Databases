import {useEffect, useRef, useState} from "react"

const HOURS = Array.from({length: 24}, (_, index) => String(index).padStart(2, "0"))
const MINUTES = ["00", "15", "30", "45"]

function formatTypedTime(value) {
  const digits = value.replace(/\D/g, "").slice(0, 4)

  if (digits.length <= 2) {
    return digits
  }

  return `${digits.slice(0, 2)}:${digits.slice(2)}`
}

function splitTime(value) {
  const [hour, minute] = value.split(":")

  return {
    hour: HOURS.includes(hour) ? hour : "00",
    minute: /^\d{2}$/.test(minute) ? minute : "00",
  }
}

export default function AwsTimeInput({
  id,
  name,
  value,
  onChange,
  className = "login-input",
  placeholder = "HH:MM",
  required = false,
  disabled = false,
}) {
  const rootRef = useRef(null)
  const inputRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const {hour: selectedHour, minute: selectedMinute} = splitTime(value)

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

  const updateTime = (hour, minute) => {
    onChange(`${hour}:${minute}`)
  }

  return (
    <div className="aws-date-picker aws-time-input" ref={rootRef}>
      <input
        ref={inputRef}
        id={id}
        name={name}
        type="text"
        value={value}
        onChange={(event) => onChange(formatTypedTime(event.target.value))}
        className={`${className} aws-date-picker-input`}
        placeholder={placeholder}
        inputMode="numeric"
        pattern="([01]\d|2[0-3]):[0-5]\d"
        maxLength={5}
        required={required}
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
      />
      <button
        type="button"
        className="aws-date-picker-trigger"
        onClick={() => {
          if (!disabled) {
            setIsOpen((current) => !current)
          }
        }}
        disabled={disabled}
        aria-label={isOpen ? "Close time picker" : "Open time picker"}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
          <circle cx="12" cy="12" r="9"/>
          <path d="M12 7v5l3 2"/>
        </svg>
      </button>

      {isOpen && (
        <div className="aws-time-input-popover" role="dialog" aria-label="Choose time">
          <div className="aws-time-input-column" aria-label="Hour">
            {HOURS.map((hour) => (
              <button
                key={hour}
                type="button"
                className={hour === selectedHour ? "aws-time-input-option aws-time-input-option-selected" : "aws-time-input-option"}
                onClick={() => updateTime(hour, selectedMinute)}
              >
                {hour}
              </button>
            ))}
          </div>
          <div className="aws-time-input-column aws-time-input-minute-column" aria-label="Minute">
            {MINUTES.map((minute) => (
              <button
                key={minute}
                type="button"
                className={minute === selectedMinute ? "aws-time-input-option aws-time-input-option-selected" : "aws-time-input-option"}
                onClick={() => {
                  updateTime(selectedHour, minute)
                  setIsOpen(false)
                  inputRef.current?.focus()
                }}
              >
                {minute}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
