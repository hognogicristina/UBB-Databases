import {useEffect, useState} from "react"
import {useNavigate, useSearchParams} from "react-router-dom"
import {verifyRecoverAccountToken} from "../services/authApi.js"
import {getErrorMessage} from "../services/apiMessages.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"

export default function RecoverAccountVerifyPage() {
  const navigate = useNavigate()
  const {notifySuccess, notifyError} = useNotifications()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") || ""
  const [isLoading, setIsLoading] = useState(true)
  const [resultMessage, setResultMessage] = useState("")

  useEffect(() => {
    let active = true

    const verifyRecovery = async () => {
      if (!token) {
        setResultMessage("Invalid link.")
        setIsLoading(false)
        return
      }

      try {
        await verifyRecoverAccountToken(token)
        if (!active) {
          return
        }
        setResultMessage("Email verified successfully.")
        notifySuccess("Email verified successfully.", {duration: 5000})
      } catch (error) {
        if (!active) {
          return
        }
        const nextMessage = getErrorMessage(error)
        const message = nextMessage.toLowerCase().includes("expired") ? "Verification link expired." : "Invalid link."
        setResultMessage(message)
        notifyError(nextMessage, {duration: 5000})
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    verifyRecovery()

    return () => {
      active = false
    }
  }, [notifyError, notifySuccess, token])

  return (
    <div className="app-shell login-page login-page-centered">
      <div className="login-card monitor-card">
        <div className="login-layout">
          <aside className="login-aside">
            <div className="auth-brand-row">
              <p className="login-brand">MedStream Console</p>
            </div>
            <h1 className="login-title">{"Account Recovery"}</h1>
            <p className="login-subtitle">{"Validate your recovery link to reactivate your account."}</p>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">{"Recovery"}</p>
              <h1 className="login-title">{"Verify Recovery Link"}</h1>
              <p className="login-subtitle">{"Your recovery verification request is being processed."}</p>
            </div>
            <div className="login-form">
              {isLoading && <p className="login-subtitle">Loading...</p>}
              {!isLoading && resultMessage && <p className="login-subtitle">{resultMessage}</p>}
              <div className="auth-actions">
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
