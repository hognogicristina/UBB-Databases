export const BUCHAREST_TIME_ZONE = "Europe/Bucharest"

function toValidDate(value) {
  const date = new Date(value)
  return Number.isFinite(date.getTime()) ? date : null
}

function formatBucharest(value, options, fallback = "--") {
  const date = toValidDate(value)
  if (!date) {
    return fallback
  }

  return new Intl.DateTimeFormat("en-GB", {
    ...options,
    timeZone: BUCHAREST_TIME_ZONE,
    hour12: false,
  }).format(date)
}

export function formatBucharestTime(value, fallback = "--") {
  return formatBucharest(value, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }, fallback)
}

export function formatBucharestDate(value, fallback = "--") {
  return formatBucharest(value, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }, fallback)
}

export function formatBucharestDateTime(value, fallback = "--") {
  return formatBucharest(value, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }, fallback)
}

export function formatBucharestNumericDateTime(value, fallback = "--") {
  return formatBucharest(value, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }, fallback)
}

export function formatBucharestShortDateTime(value, fallback = "--") {
  return formatBucharest(value, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }, fallback)
}

export function formatBucharestCompactDateTime(value, fallback = "--") {
  return formatBucharest(value, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }, fallback)
}

export function getBucharestDateParts(value) {
  const date = toValidDate(value)
  if (!date) {
    return null
  }

  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: BUCHAREST_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date)

  return Object.fromEntries(parts.map((part) => [part.type, part.value]))
}

export function formatAlertFriendlyTime(value) {
  return formatBucharestDateTime(value)
}

export function isValidTime(value) {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(value)
}
