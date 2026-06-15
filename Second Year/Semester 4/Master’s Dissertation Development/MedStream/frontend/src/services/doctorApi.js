import {api} from "./api.js"


export function getCurrentDoctor(headers) {
  return api.get("/doctors/me", {headers})
}

export function listDoctors() {
  return api.get("/doctors")
}

export function getAvailableDoctors(department, excludeDoctorId, headers) {
  return api.get("/doctors/available", {
    params: {
      department,
      exclude_doctor_id: excludeDoctorId,
    },
    headers,
  })
}

export function getDoctorPatients(doctorId) {
  return api.get(`/doctors/${doctorId}/patients`)
}

export function getDoctorActivities(doctorId) {
  return api.get(`/doctors/${doctorId}/activities`)
}

export function createDoctorActivity(doctorId, payload, headers) {
  return api.post(`/doctors/${doctorId}/activities`, payload, {headers})
}

export function updateDoctorActivity(doctorId, activityId, payload, headers) {
  return api.patch(`/doctors/${doctorId}/activities/${activityId}`, payload, {headers})
}

export function updateCurrentDoctor(payload, headers) {
  return api.patch("/doctors/me", payload, {headers})
}

export function updateCurrentDoctorEmail(payload, headers) {
  return api.patch("/doctors/me/email", payload, {headers})
}

export function assignPatientToDoctor(doctorId, patientId, headers) {
  return api.post(`/doctors/${doctorId}/patients/${patientId}`, null, {headers})
}

export function removePatientFromDoctor(doctorId, patientId, headers) {
  return api.delete(`/doctors/${doctorId}/patients/${patientId}`, {headers})
}

export function deactivateDoctor(doctorId, headers) {
  return api.delete(`/doctors/${doctorId}`, {headers})
}
