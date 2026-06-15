import {api} from "./api.js"


export function listPatients(params) {
  return api.get("/patients", {params})
}

export function searchPatientsByCnp(cnp) {
  return api.get("/patients/search", {params: {cnp}})
}

export function createPatient(payload, headers) {
  return api.post("/patients", payload, {headers})
}

export function getPatient(patientId) {
  return api.get(`/patients/${patientId}`)
}

export function getPatientTreatmentAnalysis(patientId) {
  return api.get(`/patients/${patientId}/treatment-analysis`)
}

export function getPatientPostDischargeSummary(patientId) {
  return api.get(`/patients/${patientId}/post-discharge-summary`)
}

export function updatePatient(patientId, payload, headers) {
  return api.patch(`/patients/${patientId}`, payload, {headers})
}

export function getPatientDoctors(patientId) {
  return api.get(`/patients/${patientId}/doctors`)
}

export function updatePatientDepartment(patientId, payload, headers) {
  return api.patch(`/patients/${patientId}/department`, payload, {headers})
}

export function dischargePatient(patientId, payload, headers) {
  return api.patch(`/patients/${patientId}/discharge`, payload, {headers})
}

export function readmitPatient(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/readmit`, payload, {headers})
}

export function transferPatient(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/transfer`, payload, {headers})
}

export function getPatientAdmissionHistory(patientId, page, pageSize) {
  return api.get(`/patients/${patientId}/admission-history?page=${page}&page_size=${pageSize}`)
}

export function getPatientDiagnosis(patientId, page = 1, pageSize = 100) {
  return api.get(`/patients/${patientId}/diagnosis?page=${page}&page_size=${pageSize}`)
}

export function createPatientDiagnosis(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/diagnosis`, payload, {headers})
}

export function updatePatientDiagnosis(diagnosisId, payload, headers) {
  return api.patch(`/patients/diagnosis/${diagnosisId}`, payload, {headers})
}

export function getPatientAllergies(patientId, page = 1, pageSize = 100) {
  return api.get(`/patients/${patientId}/allergies?page=${page}&page_size=${pageSize}`)
}

export function createPatientAllergy(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/allergies`, payload, {headers})
}

export function updatePatientAllergy(allergyId, payload, headers) {
  return api.patch(`/patients/allergies/${allergyId}`, payload, {headers})
}

export function getPatientConditions(patientId) {
  return api.get(`/patients/${patientId}/conditions`)
}

export function assignPatientCondition(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/conditions`, payload, {headers})
}

export function updatePatientCondition(assignmentId, payload, headers) {
  return api.patch(`/patients/condition/${assignmentId}`, payload, {headers})
}

export function getPatientMedications(patientId) {
  return api.get(`/patients/${patientId}/medications`)
}

export function administerMedication(patientId, payload, headers) {
  return api.post(`/patients/${patientId}/medication`, payload, {headers})
}

export function updateMedication(medicationId, payload, headers) {
  return api.patch(`/patients/medications/${medicationId}`, payload, {headers})
}

export function getPatientActivities(patientId) {
  return api.get(`/patients/${patientId}/activities`)
}

export function getDischargeTypes() {
  return api.get("/discharge-types")
}

export function getConditionOptions() {
  return api.get("/conditions")
}

export function getDiagnosisOptions() {
  return api.get("/options/diagnosis")
}

export function getAllergyOptions() {
  return api.get("/options/allergies")
}

export function getMedicationOptions() {
  return api.get("/options/medications")
}

export function getPatientMedicationOptions(patientId) {
  return api.get(`/medications/patients/${patientId}/options`)
}

export function getDosageOptions() {
  return api.get("/medications/dosages")
}

export function getFrequencyOptions() {
  return api.get("/medications/frequencies")
}

export function getConditionStatusOptions() {
  return api.get("/options/condition-statuses")
}

export function getActivityOptions() {
  return api.get("/options/activities")
}

export function getDepartments() {
  return api.get("/departments")
}

export function getVitals(patientId, limit = 100) {
  return api.get("/vitals", {
    params: {
      patient_id: patientId,
      limit,
    },
  })
}

export function getBatchMetrics() {
  return api.get("/metrics/batch")
}

export function getStreamingMetrics() {
  return api.get("/metrics/streaming")
}

export function getStreamingAlerts(page, pageSize) {
  return api.get("/metrics/streaming-alerts", {
    params: {page, page_size: pageSize},
  })
}

export function getMetricsComparison() {
  return api.get("/metrics/comparison")
}

export function getMetricsComparisonHistory(params) {
  return api.get("/metrics/comparison-history", {params})
}

export function getBatchInsights(params) {
  return api.get("/metrics/batch-insights", {params})
}

export function getAlerts(cnp) {
  if (cnp) {
    return api.get("/alerts", {params: {cnp}})
  }
  return api.get("/alerts")
}

export function getPatientAlerts(patientId) {
  return api.get(`/alerts/patients/${patientId}`)
}

export function getAlertDashboardSummary() {
  return api.get("/alerts/dashboard-summary")
}

export function getStats() {
  return api.get("/stats")
}

export function getBatchStatusStats() {
  return api.get("/stats/batch-status")
}

export function getBatchSchedule() {
  return api.get("/batch/schedule")
}

export function updateBatchSchedule(payload) {
  return api.post("/batch/schedule", payload)
}

export function runBatchNow() {
  return api.post("/batch/run")
}

export function getBatchStatus() {
  return api.get("/batch/status")
}
