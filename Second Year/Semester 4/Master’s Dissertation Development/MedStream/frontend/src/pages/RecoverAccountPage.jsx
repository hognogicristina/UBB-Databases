import {useState} from "react"
import {Link} from "react-router-dom"
import {requestAccountRecovery} from "../services/authApi.js"
import {getErrorMessage, getResponseMessage} from "../services/apiMessages.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

export default function RecoverAccountPage() {
  const {notifySuccess, notifyError} = useNotifications()
  const [identifier, setIdentifier] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const canRecoverAccount = identifier.trim().length > 0

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!canRecoverAccount || isSubmitting) {
      return
    }
    setIsSubmitting(true)

    try {
      const response = await requestAccountRecovery({
        identifier,
      })
      notifySuccess(getResponseMessage(response), {duration: 5000})
    } catch (error) {
      notifyError(getErrorMessage(error), {duration: 5000})
    } finally {
      setIsSubmitting(false)
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
            <h1 className="login-title">{"Account Recovery"}</h1>
            <p className="login-subtitle">{"Request an account recovery email for the doctor account associated with MedStream."}</p>
            <div className="auth-metrics">
              <div className="auth-metric">
                <p className="auth-metric-label">Access</p>
                <p className="auth-metric-value">Protected Data Flow</p>
                <p className="auth-metric-copy">Authentication ensures only authorized clinicians access sensitive records.</p>
              </div>
              <div className="auth-metric">
                <p className="auth-metric-label">Intake</p>
                <p className="auth-metric-value">Quick Registration</p>
                <p className="auth-metric-copy">New patients can be added in seconds with structured input forms.</p>
              </div>
            </div>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">{"Recovery"}</p>
              <h1 className="login-title">{"Recover Account"}</h1>
              <p className="login-subtitle">{"Enter your email to start account recovery."}</p>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              <div className="login-field">
                <input
                  id="identifier"
                  type="text"
                  value={identifier}
                  onChange={(event) => setIdentifier(limitText(event.target.value, INPUT_LIMITS.identifier))}
                  className="login-input"
                  placeholder={"Email address"}
                  maxLength={INPUT_LIMITS.identifier}
                  required
                />
              </div>

              <div className="auth-actions">
                <button
                  type="submit"
                  disabled={!canRecoverAccount || isSubmitting}
                  className="login-button"
                >
                  {isSubmitting ? ("Requesting...") : ("Recover Account")}
                </button>

                <div className="auth-link-row">
                  <Link className="auth-link" to="/login">
                    {"Back to login"}
                  </Link>
                  <Link className="auth-link" to="/forgot-password">
                    {"Forgot password?"}
                  </Link>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
