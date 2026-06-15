import {useEffect, useState} from "react"
import {useNavigate, useSearchParams} from "react-router-dom"
import {resendVerificationEmail, verifyEmailToken} from "../services/authApi.js"
import {getErrorMessage, getResponseMessage} from "../services/apiMessages.js"
import {
  VERIFICATION_LINK_EXPIRED_MESSAGE,
  VERIFICATION_LINK_REPLACED_MESSAGE,
} from "../services/appMessages.js"
import {announceEmailVerified} from "../services/emailVerificationEvents.js"
import {useAuth} from "../hooks/useAuth.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const {refreshCurrentDoctor, token: authToken} = useAuth()
  const {notifySuccess, notifyError} = useNotifications()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token")
  const [isLoading, setIsLoading] = useState(true)
  const [showResendButton, setShowResendButton] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [resultMessage, setResultMessage] = useState("")

  useEffect(() => {
    let active = true

    const verify = async () => {
      try {
        await verifyEmailToken(token)

        if (!active) {
          return
        }

        setResultMessage("Email verified successfully.")
        announceEmailVerified()
        if (authToken) {
          refreshCurrentDoctor().catch(() => {})
        }
        notifySuccess("Email verified successfully.", {duration: 5000})
        setShowResendButton(false)
      } catch (error) {
        if (!active) {
          return
        }

        const nextMessage = getErrorMessage(error)
        notifyError(nextMessage, {duration: 5000})
        setResultMessage(nextMessage)
        setShowResendButton(Boolean(token) && (
          nextMessage === VERIFICATION_LINK_EXPIRED_MESSAGE
          || nextMessage === VERIFICATION_LINK_REPLACED_MESSAGE
          || nextMessage === "Invalid verification link."
        ))
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    verify()

    return () => {
      active = false
    }
  }, [authToken, navigate, notifyError, notifySuccess, refreshCurrentDoctor, token])

  const handleResend = async () => {
    if (isResending || !showResendButton) {
      return
    }

    setIsResending(true)
    try {
      const response = await resendVerificationEmail({token})
      setShowResendButton(false)
      notifySuccess(getResponseMessage(response), {duration: 5000})
    } catch (error) {
      notifyError(getErrorMessage(error), {duration: 5000})
    } finally {
      setIsResending(false)
    }
  }

  return (
    <div className="app-shell login-page login-page-centered">
      <div className="login-card monitor-card">
        <div className="login-layout">
          <aside className="login-aside">
            <div className="auth-brand-row">
              <p className="login-brand">MedStream Console</p>
            </div>
            <h1 className="login-title">{"Email Verification"}</h1>
            <p className="login-subtitle">{"Confirm your doctor account email using the secure verification link."}</p>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">{"Verification"}</p>
              <h1 className="login-title">{"Verify Email"}</h1>
              <p className="login-subtitle">{"Your verification request is being processed."}</p>
            </div>

            <div className="login-form">
              {isLoading && <p className="login-subtitle">Loading...</p>}
              {!isLoading && resultMessage && <p className="login-subtitle">{resultMessage}</p>}

              <div className="auth-actions">
                {showResendButton && (
                  <button
                    type="button"
                    className="login-button"
                    disabled={isResending}
                    onClick={handleResend}
                  >
                    {isResending ? "Sending..." : "Resend verification email"}
                  </button>
                )}
                <button
                  type="button"
                  className="login-button"
                  onClick={() => navigate("/login")}
                >
                  {"Go to Login"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
