import {Link} from "react-router-dom"
import {useEffect, useRef, useState} from "react"
import {useLocation, useNavigate, useSearchParams} from "react-router-dom"
import {useAuth} from "../hooks/useAuth.js"
import {useNotifications} from "../hooks/useNotifications.js"
import {loginDoctor} from "../services/authApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const {login} = useAuth()
  const {notifySuccess, notifyError} = useNotifications()
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const handledLocationKeyRef = useRef("")
  const isLoginValid = identifier.trim().length > 0 && password.trim().length > 0

  useEffect(() => {
    if (searchParams.get("recovered") !== "1") {
      return
    }

    notifySuccess("Account recovery verified. Please sign in.", {duration: 5000})
    navigate("/login", {replace: true})
  }, [navigate, notifySuccess, searchParams])

  useEffect(() => {
    if (!location.state?.message) {
      return
    }

    if (handledLocationKeyRef.current === location.key) {
      return
    }

    handledLocationKeyRef.current = location.key
    notifySuccess(location.state.message)
    navigate(location.pathname, {replace: true, state: {}})
  }, [location.key, location.pathname, location.state, navigate, notifySuccess])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!isLoginValid || isSubmitting) {
      return
    }
    setIsSubmitting(true)

    try {
      const response = await loginDoctor({
        identifier,
        password,
      })

      login(getResponseData(response).token)
      navigate("/dashboard")
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
            <h1 className="login-title">{"Doctor Access"}</h1>
            <p
              className="login-subtitle">{"Authenticate into the operations console to monitor vitals, review alerts, and manage patient workflows."}</p>
            <div className="auth-metrics">
              <div className="auth-metric">
                <p className="auth-metric-label">Workspace</p>
                <p className="auth-metric-value">Clinical Operations</p>
                <p className="auth-metric-copy">A single console for admissions, alerting, and patient review.</p>
              </div>
              <div className="auth-metric">
                <p className="auth-metric-label">Availability</p>
                <p className="auth-metric-value">Live Signal Feed</p>
                <p className="auth-metric-copy">Vitals and alerts continue updating while you work.</p>
              </div>
            </div>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">{"Sign In"}</p>
              <h1 className="login-title">{"Doctor Login"}</h1>
              <p className="login-subtitle">{"Secure access to the hospital monitoring console."}</p>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>

              <div className="login-field">
                <input
                  id="identifier"
                  type="text"
                  value={identifier}
                  onChange={(event) => setIdentifier(limitText(event.target.value, INPUT_LIMITS.identifier))}
                  className="login-input"
                  placeholder={"Enter your email or phone number"}
                  maxLength={INPUT_LIMITS.identifier}
                  required
                />
              </div>

              <div className="login-field">
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(limitText(event.target.value, INPUT_LIMITS.password))}
                  className="login-input"
                  placeholder={"Enter your password"}
                  maxLength={INPUT_LIMITS.password}
                  required
                />
              </div>

              <div className="auth-link-row">
                <Link className="auth-link" to="/forgot-password">
                  {"Forgot password?"}
                </Link>
                <Link className="auth-link" to="/recover-account">
                  {"Recover account"}
                </Link>
              </div>

              <button
                type="submit"
                disabled={!isLoginValid || isSubmitting}
                className="login-button"
              >
                {isSubmitting ? ("Signing in...") : ("Login")}
              </button>

              <div className="auth-link-row">
                <Link className="auth-link" to="/register">
                  {"Need an account? Register"}
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
