export function normalizeAlertType(type, severity) {
  const normalizedType = String(type || "").trim().toLowerCase()
  const normalizedSeverity = String(severity || "").trim().toLowerCase()

  if (
    normalizedType.endsWith("_high")
    || normalizedType.endsWith("_critical")
    || normalizedType.endsWith("_low")
    || normalizedType.endsWith("_normalized")
    || normalizedType.endsWith("_normal")
    || normalizedType.endsWith("_stable")
  ) {
    return normalizedType
  }

  if (normalizedType === "heart_rate") {
    return normalizedSeverity === "critical" ? "heart_rate_critical" : "heart_rate_high"
  }

  if (normalizedType === "oxygen" || normalizedType === "oxygen_saturation") {
    return normalizedSeverity === "critical" ? "oxygen_critical" : "oxygen_low"
  }

  if (normalizedType === "temperature") {
    return normalizedSeverity === "critical" ? "temperature_critical" : "temperature_high"
  }

  if (normalizedType === "status" || normalizedType === "normal vitals") {
    return "heart_rate_normalized"
  }

  return normalizedType
}

export function alertTypeToVital(type) {
  const normalizedType = String(type || "").trim().toLowerCase()
  if (normalizedType === "heart_rate" || normalizedType.startsWith("heart_rate_")) {
    return "heartRate"
  }
  if (normalizedType === "oxygen" || normalizedType === "oxygen_saturation" || normalizedType.startsWith("oxygen_")) {
    return "oxygen"
  }
  if (normalizedType === "temperature" || normalizedType.startsWith("temperature_")) {
    return "temperature"
  }
  return null
}

export function isNormalizedAlertType(type) {
  const normalizedType = String(type || "").trim().toLowerCase()
  return normalizedType.endsWith("_normalized") || normalizedType.endsWith("_normal") || normalizedType.endsWith("_stable")
}

export function getAlertSeverityLevel(alert = {}) {
  const severity = String(alert?.severity || "").trim().toLowerCase()
  if (severity === "critical") {
    return "critical"
  }
  if (severity === "high" || severity === "warning") {
    return "high"
  }
  return "normal"
}
