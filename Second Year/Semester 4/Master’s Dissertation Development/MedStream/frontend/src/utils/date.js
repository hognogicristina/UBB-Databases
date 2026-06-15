import {getBucharestDateParts} from "./time.js"

export function formatDateAsIso(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")

  return `${year}-${month}-${day}`
}

export function getTodayIsoDate() {
  const parts = getBucharestDateParts(new Date())
  return parts ? `${parts.year}-${parts.month}-${parts.day}` : formatDateAsIso(new Date())
}

export function parseIsoDate(value) {
  if (typeof value !== "string") {
    return null
  }

  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) {
    return null
  }

  const [, yearValue, monthValue, dayValue] = match
  const year = Number(yearValue)
  const month = Number(monthValue)
  const day = Number(dayValue)
  const date = new Date(year, month - 1, day)

  if (
    date.getFullYear() !== year
    || date.getMonth() !== month - 1
    || date.getDate() !== day
  ) {
    return null
  }

  return date
}

export function isValidIsoDate(value) {
  return Boolean(parseIsoDate(value))
}

export function isIsoDateInRange(value, {min, max} = {}) {
  if (!isValidIsoDate(value)) {
    return false
  }

  if (min && value < min) {
    return false
  }

  if (max && value > max) {
    return false
  }

  return true
}
