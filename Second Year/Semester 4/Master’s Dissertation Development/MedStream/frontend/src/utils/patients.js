export function formatPatientFullName(patient) {
  if (!patient) {
    return "Unknown patient"
  }

  const lastName = String(patient.last_name || "").trim()
  const firstName = String(patient.first_name || "").trim()
  const fullName = `${lastName} ${firstName}`.trim()

  return fullName || "Unknown patient"
}
