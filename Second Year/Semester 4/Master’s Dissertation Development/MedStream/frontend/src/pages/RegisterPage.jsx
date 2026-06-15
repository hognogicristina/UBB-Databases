import {useEffect, useState} from "react"
import {Link, useNavigate} from "react-router-dom"
import {Select} from "@cloudscape-design/components"
import {registerDoctor} from "../services/authApi.js"
import {getDepartments} from "../services/patientApi.js"
import {getErrorMessage, getResponseData, getResponseMessage} from "../services/apiMessages.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AuthThemeToggle from "../components/AuthThemeToggle.jsx"
import AwsDatePicker from "../components/AwsDatePicker.jsx"
import {
  buildPatientPhoneNumber,
  ROMANIA_PHONE_PLACEHOLDER,
} from "../utils/patientPhone.js"
import {getTodayIsoDate, isIsoDateInRange} from "../utils/date.js"
import {INPUT_LIMITS, limitDigits, limitText} from "../utils/inputLimits.js"

function getSelectedOption(options, value) {
  return options.find((option) => option.value === value) || null
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const {notifyError} = useNotifications()

  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    birth_date: "",
    email: "",
    phone_number: "",
    specialization: "",
    license_number: "",
    password: "",
    confirm_password: "",
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [departments, setDepartments] = useState([])
  const departmentOptions = departments.map((department) => ({label: department, value: department}))
  const maxBirthDate = getTodayIsoDate()

  useEffect(() => {
    const loadDepartments = async () => {
      try {
        const res = await getDepartments()
        setDepartments(getResponseData(res))
      } catch (error) {
        notifyError(getErrorMessage(error), {duration: 5000})
      }
    }
    loadDepartments()
  }, [notifyError])

  const normalizedPhoneNumber = buildPatientPhoneNumber(form.phone_number)

  const isStepOneValid = Boolean(
    form.first_name.trim()
    && form.last_name.trim()
    && form.email.trim()
    && normalizedPhoneNumber.trim(),
  )

  const isStepTwoValid = Boolean(
    form.specialization.trim()
    && form.license_number.trim()
    && isIsoDateInRange(form.birth_date, {max: maxBirthDate})
  )

  const isStepThreeValid = Boolean(
    form.password.trim()
    && form.confirm_password.trim()
  )

  const handleChange = (event) => {
    const {name, value} = event.target
    const fieldLimits = {
      first_name: INPUT_LIMITS.firstName,
      last_name: INPUT_LIMITS.lastName,
      email: INPUT_LIMITS.email,
      license_number: INPUT_LIMITS.licenseNumber,
      password: INPUT_LIMITS.password,
      confirm_password: INPUT_LIMITS.password,
    }
    const nextValue = fieldLimits[name] ? limitText(value, fieldLimits[name]) : value
    setForm((prev) => ({...prev, [name]: nextValue}))
  }

  const handlePhoneChange = (event) => {
    const digitsOnly = limitDigits(event.target.value, INPUT_LIMITS.phone)

    setForm((prev) => ({
      ...prev,
      phone_number: digitsOnly,
    }))
  }

  const handleNextStep = () => {
    if (step === 1 && !isStepOneValid) {
      return
    }

    if (step === 2 && !isStepTwoValid) {
      return
    }

    setStep((current) => Math.min(current + 1, 3))
  }

  const handlePreviousStep = () => {
    setStep((current) => Math.max(current - 1, 1))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!isStepThreeValid || isSubmitting) {
      return
    }

    setIsSubmitting(true)

    try {
      const response = await registerDoctor({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        birth_date: form.birth_date,
        email: form.email.trim(),
        phone_number: normalizedPhoneNumber,
        specialization: form.specialization.trim(),
        license_number: form.license_number.trim(),
        password: form.password,
        confirm_password: form.confirm_password,
      })

      navigate("/login", {
        state: {
          message: getResponseMessage(response),
        },
      })
    } catch (error) {
      notifyError(getErrorMessage(error), {duration: 5000})
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="app-shell login-page login-page-centered register-page">
      <div className="login-card monitor-card">
        <div className="login-layout">
          <aside className="login-aside">
            <div className="auth-brand-row">
              <p className="login-brand">MedStream Console</p>
            </div>

            <h1 className="login-title">
              {"Create Doctor Account"}
            </h1>

            <p className="login-subtitle">
              {"Provision a clinician account for access to monitoring, alerts, and patient operations."}
            </p>
            <div className="auth-metrics">
              <div className="auth-metric">
                <p className="auth-metric-label">Monitoring</p>
                <p className="auth-metric-value">Live Patient Insights</p>
                <p className="auth-metric-copy">Patient vitals update instantly through WebSocket streaming.</p>
              </div>
              <div className="auth-metric">
                <p className="auth-metric-label">Alerting</p>
                <p className="auth-metric-value">Instant Risk Detection</p>
                <p className="auth-metric-copy">Critical conditions trigger alerts the moment thresholds are exceeded.</p>
              </div>
            </div>
          </aside>

          <div className="auth-divider" aria-hidden="true"/>

          <div className="login-panel">
            <div className="login-header">
              <AuthThemeToggle/>
              <p className="login-brand">
                {"Registration"}
              </p>

              <h1 className="login-title">
                {"Doctor Registration"}
              </h1>

              <p className="login-subtitle">
                {"Enter account and professional details to activate console access."}
              </p>

              <div className="auth-step-indicator">
                {"Step"} {step} / 3
              </div>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              {step === 1 && (
                <div className="auth-section register-step-card">
                  <div className="auth-section-header">
                    <p className="auth-section-label">
                      {"Account Details"}
                    </p>
                    <p className="auth-section-copy">
                      {"Basic identity and contact information."}
                    </p>
                  </div>

                  <div className="register-grid">
                    <div className="login-field">
                      <label className="login-label" htmlFor="first_name">
                        {"First Name"}
                      </label>
                      <input
                        id="first_name"
                        name="first_name"
                        type="text"
                        value={form.first_name}
                        onChange={handleChange}
                        className="login-input"
                        placeholder={"Elena"}
                        maxLength={100}
                        required
                      />
                    </div>

                    <div className="login-field">
                      <label className="login-label" htmlFor="last_name">
                        {"Last Name"}
                      </label>
                      <input
                        id="last_name"
                        name="last_name"
                        type="text"
                        value={form.last_name}
                        onChange={handleChange}
                        className="login-input"
                        placeholder={"Popescu"}
                        maxLength={100}
                        required
                      />
                    </div>
                  </div>

                  <div className="login-field">
                    <label className="login-label" htmlFor="email">
                      Email
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      value={form.email}
                      onChange={handleChange}
                      className="login-input"
                      placeholder={"doctor@medstream.ro"}
                      maxLength={255}
                      required
                    />
                  </div>

                  <div className="login-field">
                    <label className="login-label" htmlFor="doctor-register-phone-number">
                      {"Phone Number"}
                    </label>
                    <input
                      id="doctor-register-phone-number"
                      name="phone_number"
                      type="text"
                      inputMode="numeric"
                      value={form.phone_number}
                      onChange={handlePhoneChange}
                      placeholder={ROMANIA_PHONE_PLACEHOLDER}
                      className="login-input"
                      maxLength={INPUT_LIMITS.phone}
                      required
                    />
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="auth-section register-step-card">
                  <div className="auth-section-header">
                    <p className="auth-section-label">
                      {"Professional Details"}
                    </p>
                    <p className="auth-section-copy">
                      {"Clinical role and license information."}
                    </p>
                  </div>

                  <div className="register-professional-grid">
                    <div className="login-field register-field-layer">
                      <label className="login-label" htmlFor="specialization">
                        {"Specialization"}
                      </label>
                      <Select
                        selectedOption={getSelectedOption(departmentOptions, form.specialization)}
                        onChange={({detail}) => handleChange({target: {name: "specialization", value: detail.selectedOption.value}})}
                        options={departmentOptions}
                        placeholder="Specialization"
                        selectedAriaLabel="Selected specialization"
                      />
                    </div>

                    <div className="login-field register-field-layer">
                      <label className="login-label" htmlFor="license_number">
                        {"License Number"}
                      </label>
                      <input
                        id="license_number"
                        name="license_number"
                        type="text"
                        value={form.license_number}
                        onChange={handleChange}
                        className="login-input"
                        placeholder={"DOC-20458"}
                        maxLength={50}
                        required
                      />
                    </div>

                    <div className="login-field register-field-layer-raised register-field-wide">
                      <label className="login-label" htmlFor="birth_date">
                        {"Birth Date"}
                      </label>
                      <AwsDatePicker
                        id="birth_date"
                        name="birth_date"
                        value={form.birth_date}
                        onChange={(value) => handleChange({target: {name: "birth_date", value}})}
                        className="login-input"
                        max={maxBirthDate}
                        required
                      />
                    </div>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="auth-section register-step-card">
                  <div className="auth-section-header">
                    <p className="auth-section-label">
                      {"Password Setup"}
                    </p>
                    <p className="auth-section-copy">
                      {"Set and confirm the password for the doctor account."}
                    </p>
                  </div>

                  <div className="login-field">
                    <label className="login-label" htmlFor="password">
                      {"Password"}
                    </label>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      value={form.password}
                      onChange={handleChange}
                      className="login-input"
                      maxLength={72}
                      required
                    />
                  </div>

                  <div className="login-field">
                    <label className="login-label" htmlFor="confirm_password">
                      {"Confirm Password"}
                    </label>
                    <input
                      id="confirm_password"
                      name="confirm_password"
                      type="password"
                      value={form.confirm_password}
                      onChange={handleChange}
                      className="login-input"
                      maxLength={72}
                      required
                    />
                  </div>
                </div>
              )}

              <div className="auth-actions">
                {step < 3 ? (
                  <div className="form-action-block auth-action-full">
                    <div className="auth-button-row">
                      {step > 1 && (
                        <button
                          type="button"
                          onClick={handlePreviousStep}
                          disabled={isSubmitting}
                          className="console-button-secondary auth-step-secondary-button auth-button-fill"
                        >
                          {"Back"}
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={handleNextStep}
                        disabled={isSubmitting || (step === 1 ? !isStepOneValid : !isStepTwoValid)}
                        className="login-button auth-step-primary-button auth-button-fill"
                      >
                        {"Next"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="form-action-block auth-action-full">
                    <div className="auth-button-row">
                      <button
                        type="button"
                        onClick={handlePreviousStep}
                        disabled={isSubmitting}
                        className="console-button-secondary auth-step-secondary-button auth-button-fill"
                      >
                        {"Back"}
                      </button>

                      <button
                        type="submit"
                        disabled={!isStepThreeValid || isSubmitting}
                        className="login-button auth-button-fill"
                      >
                        {isSubmitting
                          ? ("Creating account...")
                          : ("Create Account")}
                      </button>
                    </div>
                  </div>
                )}

                <div className="auth-link-row">
                  <Link className="auth-link" to="/login">
                    {"Already have an account? Login"}
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
