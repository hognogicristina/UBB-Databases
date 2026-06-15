import {useState} from "react"
import {Link} from "react-router-dom"
import {useNotifications} from "../hooks/useNotifications.js"
import {requestPasswordReset} from "../services/authApi.js"
import {getErrorMessage, getResponseMessage} from "../services/apiMessages.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

export default function ForgotPasswordPage() {
  const {notifySuccess, notifyError} = useNotifications()
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const canRequestReset = email.trim().length > 0

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!canRequestReset || isSubmitting) {
      return
    }
    setIsSubmitting(true)

    try {
      const response = await requestPasswordReset({
        identifier: email.trim(),
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
            <h1 className="login-title">{"Password Recovery"}</h1>
            <p className="login-subtitle">{"Request a secure password reset email for your doctor account."}</p>
            <div className="auth-metrics">
              <div className="auth-metric">
                <p className="auth-metric-label">Live</p>
                <p className="auth-metric-value">Continuous Tracking</p>
                <p className="auth-metric-copy">Every patient interaction is logged and displayed in real time.</p>
              </div>
              <div className="auth-metric">
                <p className="auth-metric-label">Scalable</p>
                <p className="auth-metric-value">Built to Grow</p>
                <p className="auth-metric-copy">The system is designed to handle increasing numbers of patients and data streams
                  effortlessly.</p>
              </div>
            </div>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">{"Recovery"}</p>
              <h1 className="login-title">{"Forgot Password"}</h1>
              <p className="login-subtitle">{"Enter your email address to receive a password reset link."}</p>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              <div className="login-field">
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(limitText(event.target.value, INPUT_LIMITS.email))}
                  className="login-input"
                  placeholder={"Email address"}
                  maxLength={INPUT_LIMITS.email}
                  required
                />
              </div>

              <div className="auth-actions">
                <button
                  type="submit"
                  disabled={!canRequestReset || isSubmitting}
                  className="login-button"
                >
                  {isSubmitting ? ("Requesting...") : ("Request Password Reset")}
                </button>

                <div className="auth-link-row">
                  <Link className="auth-link" to="/login">
                    {"Back to login"}
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
