import {INPUT_LIMITS, limitDigits} from "./inputLimits.js"

export const ROMANIA_PHONE_PLACEHOLDER = "0712345678"

export function normalizeRomanianPhoneNumber(value) {
  const digits = limitDigits(value, 15)

  if (!digits) {
    return ""
  }

  if (digits.startsWith("40") && digits.length === 11) {
    return `0${digits.slice(2)}`
  }

  return digits.slice(0, INPUT_LIMITS.phone)
}

export function buildPatientPhoneNumber(value) {
  return normalizeRomanianPhoneNumber(value)
}

export function formatPatientPhoneWithCode(phoneNumber) {
  return normalizeRomanianPhoneNumber(phoneNumber)
}
