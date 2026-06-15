import {api} from "./api.js"


export function loginDoctor(payload) {
  return api.post("/doctors/login", payload)
}

export function registerDoctor(payload) {
  return api.post("/register", payload)
}

export function requestPasswordReset(payload) {
  return api.post("/auth/forgot-password", payload)
}

export function resetPassword(payload) {
  return api.post("/auth/reset-password", payload)
}

export function verifyEmailToken(token) {
  return api.get("/auth/verify-email", {params: {token}})
}

export function requestAccountRecovery(payload) {
  return api.post("/auth/recover-account", payload)
}

export function verifyRecoverAccountToken(token) {
  return api.get("/auth/recover-account/verify", {params: {token}})
}

export function resendVerificationEmail({headers, token} = {}) {
  return api.post("/auth/resend-verification", null, {
    headers,
    params: token ? {token} : undefined,
  })
}
