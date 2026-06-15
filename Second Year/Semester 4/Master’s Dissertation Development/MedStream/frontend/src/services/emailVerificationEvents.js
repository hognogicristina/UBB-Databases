const EMAIL_VERIFICATION_EVENT_NAME = "medstream-email-verified"
const EMAIL_VERIFICATION_STORAGE_KEY = "medstream_email_verified_at"

function buildPayload() {
  return {verifiedAt: Date.now()}
}

export function announceEmailVerified() {
  const payload = buildPayload()

  window.dispatchEvent(new CustomEvent(EMAIL_VERIFICATION_EVENT_NAME, {detail: payload}))

  try {
    localStorage.setItem(EMAIL_VERIFICATION_STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // Storage may be unavailable in private contexts; the same-tab event still works.
  }

  if ("BroadcastChannel" in window) {
    const channel = new BroadcastChannel(EMAIL_VERIFICATION_EVENT_NAME)
    channel.postMessage(payload)
    channel.close()
  }
}

export function subscribeToEmailVerified(callback) {
  const handleEvent = () => {
    callback()
  }
  const handleStorage = (event) => {
    if (event.key === EMAIL_VERIFICATION_STORAGE_KEY && event.newValue) {
      callback()
    }
  }
  const channel = "BroadcastChannel" in window
    ? new BroadcastChannel(EMAIL_VERIFICATION_EVENT_NAME)
    : null

  window.addEventListener(EMAIL_VERIFICATION_EVENT_NAME, handleEvent)
  window.addEventListener("storage", handleStorage)
  channel?.addEventListener("message", handleEvent)

  return () => {
    window.removeEventListener(EMAIL_VERIFICATION_EVENT_NAME, handleEvent)
    window.removeEventListener("storage", handleStorage)
    channel?.removeEventListener("message", handleEvent)
    channel?.close()
  }
}
