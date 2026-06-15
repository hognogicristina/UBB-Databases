import {useCallback, useEffect, useState} from "react"
import {useParams} from "react-router-dom"
import {Button, Pagination} from "@cloudscape-design/components"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import {useNotifications} from "../hooks/useNotifications.js"
import {createPatientDiagnosis, getPatient, getPatientDiagnosis} from "../services/patientApi.js"
import {getErrorMessage, getResponseData, getResponseMessage} from "../services/apiMessages.js"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"
import {formatBucharestDateTime} from "../utils/time.js"

function formatDateTime(value) {
  return formatBucharestDateTime(value)
}

export default function PatientDiagnosisPage() {
  const {id} = useParams()
  const {notifyError, notifySuccess} = useNotifications()
  const pageSize = 5
  const [patient, setPatient] = useState(null)
  const [diagnosisEntries, setDiagnosisEntries] = useState([])
  const [diagnosisTotal, setDiagnosisTotal] = useState(0)
  const [diagnosisPage, setDiagnosisPage] = useState(1)
  const [form, setForm] = useState({
    diagnosis: "",
    notes: "",
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadPageData = useCallback(async (page = diagnosisPage) => {
    setIsLoading(true)

    try {
      const [patientResponse, diagnosisResponse] = await Promise.all([
        getPatient(id),
        getPatientDiagnosis(id, page, pageSize),
      ])

      setPatient(getResponseData(patientResponse))
      const diagnosisData = getResponseData(diagnosisResponse) || {}
      setDiagnosisEntries(diagnosisData.items || [])
      setDiagnosisTotal(diagnosisData.total || 0)
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }, [diagnosisPage, id, notifyError])

  useEffect(() => {
    loadPageData(diagnosisPage).then(r => r)
  }, [diagnosisPage, loadPageData])

  const handleChange = (event) => {
    const {name, value} = event.target
    const fieldLimits = {
      diagnosis: INPUT_LIMITS.diagnosis,
      notes: INPUT_LIMITS.clinicalNote,
    }
    setForm((current) => ({...current, [name]: limitText(value, fieldLimits[name])}))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!form.diagnosis.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)

    try {
      const response = await createPatientDiagnosis(id, {
        diagnosis: form.diagnosis,
        notes: form.notes.trim() || null,
      })
      setForm({
        diagnosis: "",
        notes: "",
      })
      await loadPageData(1)
      setDiagnosisPage(1)
      notifySuccess(getResponseMessage(response))
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  const patientName = patient ? `${patient.last_name} ${patient.first_name}`.trim() : "Patient"
  const maxDiagnosisPage = Math.max(1, Math.ceil(diagnosisTotal / pageSize))

  useEffect(() => {
    if (diagnosisPage > maxDiagnosisPage) {
      setDiagnosisPage(maxDiagnosisPage)
    }
  }, [diagnosisPage, maxDiagnosisPage])

  return (
    <div className="app-shell medstream-diagnosis-page">
      <div className="medstream-diagnosis-shell">
        <header className="console-topbar medstream-diagnosis-topbar">
          <div className="medstream-diagnosis-header-row">
            <div>
              <p className="medstream-diagnosis-eyebrow medstream-diagnosis-page-eyebrow">Diagnosis</p>
              <h1 className="medstream-diagnosis-title">{patientName}</h1>
              <p className="medstream-diagnosis-subtitle">Structured diagnosis entries for this patient.</p>
            </div>
            <AppBreadcrumbs/>
          </div>
        </header>

        {isLoading ? <LoadingSpinner/> : (
          <section className="medstream-diagnosis-layout">
            <div className="monitor-card medstream-diagnosis-card">
              <div className="medstream-diagnosis-card-header">
                <div>
                  <p className="medstream-diagnosis-eyebrow">Add Diagnosis</p>
                  <h2 className="medstream-diagnosis-section-title">New Entry</h2>
                </div>
              </div>

              <form className="medstream-diagnosis-form" onSubmit={handleSubmit}>
                <input
                  type="text"
                  name="diagnosis"
                  value={form.diagnosis}
                  onChange={handleChange}
                  placeholder="Diagnosis"
                  className="console-input medstream-diagnosis-input"
                  maxLength={INPUT_LIMITS.diagnosis}
                  required
                />

                <textarea
                  name="notes"
                  value={form.notes}
                  onChange={handleChange}
                  placeholder="Notes"
                  className="console-input medstream-diagnosis-input medstream-diagnosis-textarea"
                  maxLength={INPUT_LIMITS.clinicalNote}
                />

                <Button
                  formAction="submit"
                  variant="primary"
                  className="medstream-submit-button"
                  disabled={!form.diagnosis.trim() || isSubmitting}
                >
                  {isSubmitting ? "Saving..." : "Add Diagnosis"}
                </Button>
              </form>
            </div>

            <div className="monitor-card medstream-diagnosis-card">
              <div className="medstream-diagnosis-card-header">
                <div>
                  <p className="medstream-diagnosis-eyebrow">Entries</p>
                  <h2 className="medstream-diagnosis-section-title">Diagnosis Timeline</h2>
                </div>
                <span className="console-chip medstream-diagnosis-count">
                {diagnosisTotal} total
              </span>
              </div>

              <div className="medstream-diagnosis-pagination">
                <Pagination
                  currentPageIndex={diagnosisPage}
                  pagesCount={maxDiagnosisPage}
                  onChange={({detail}) => setDiagnosisPage(detail.currentPageIndex)}
                />
              </div>

              <ul className="medstream-diagnosis-list">
                {diagnosisEntries.length === 0 && (
                  <li className="medstream-diagnosis-empty">
                    {isLoading ? "Loading diagnosis entries..." : "No diagnosis entries recorded for this patient."}
                  </li>
                )}

                {diagnosisEntries.map((entry) => (
                  <li key={entry.id} className="medstream-diagnosis-entry">
                    <div className="medstream-diagnosis-entry-row">
                      <div>
                        <p className="medstream-diagnosis-entry-title">{entry.diagnosis}</p>
                        {entry.notes && (
                          <p className="medstream-diagnosis-entry-note">{entry.notes}</p>
                        )}
                        {String(entry.modified_by || "").trim() ? (
                          <p className="medstream-diagnosis-entry-doctor">Modified by doctor: {entry.modified_by}</p>
                        ) : null}
                      </div>
                      <span className="medstream-diagnosis-entry-date">{formatDateTime(entry.updated_at || entry.created_at)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
