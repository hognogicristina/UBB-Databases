import {useCallback, useEffect, useMemo, useRef, useState} from "react"
import {
  Alert,
  Box,
  ColumnLayout,
  Container,
  Header,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  AreaChart,
} from "@cloudscape-design/components"
import {useNotifications} from "../hooks/useNotifications.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {getPatient, getPatientTreatmentAnalysis} from "../services/patientApi.js"
import {createWebSocket} from "../services/ws.js"
import LoadingSpinner from "./LoadingSpinner.jsx"
import {alertTypeToVital, getAlertSeverityLevel, isNormalizedAlertType, normalizeAlertType} from "../utils/alerts.js"
import {
  formatAlertFriendlyTime,
  formatBucharestCompactDateTime,
  formatBucharestDateTime,
  formatBucharestShortDateTime,
  formatBucharestTime,
} from "../utils/time.js"

const DIAGNOSIS_PAGE_SIZE = 3
const CONDITION_PAGE_SIZE = 3
const ALERT_HISTORY_EXPANDED_PAGE_SIZE = 4
const OUTCOME_CONFIG = {
  Effective: {value: 2, color: "#22c55e"},
  Improving: {value: 1, color: "#f59e0b"},
  Ineffective: {value: 0, color: "#ef4444"},
}
const AREA_CHART_I18N_STRINGS = {
  chartAriaRoleDescription: "area chart",
  detailPopoverDismissAriaLabel: "Dismiss",
  detailTotalLabel: "Outcome",
  filterLabel: "Filter displayed outcomes",
  filterPlaceholder: "Filter outcomes",
  filterSelectedAriaLabel: "selected",
  legendAriaLabel: "Legend",
  xAxisAriaRoleDescription: "x axis",
  yAxisAriaRoleDescription: "y axis",
}
const TREATMENT_ANALYSIS_HELP_STEPS = [
  {
    title: "Step 1: Latest alert summary",
    body: "Review the latest vital alerts first. These values show what changed recently and whether abnormal readings are still active.",
  },
  {
    title: "Step 2: Clinical context",
    body: "Check diagnosis and conditions next. They provide the clinical context used to understand why medication is needed.",
  },
  {
    title: "Step 3: Medication decision",
    body: "Review the medication, dosage, frequency, and outcome. The decision is evaluated against later vitals and alerts.",
  },
]

function normalizeOutcomeLabel(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (normalized === "effective") {
    return "Effective"
  }
  if (normalized === "improving") {
    return "Improving"
  }
  return "Ineffective"
}

function formatOutcomeScale(value) {
  if (value === 3) {
    return "Effective"
  }
  if (value === 2) {
    return "Improving"
  }
  if (value === 1) {
    return "Ineffective"
  }
  return ""
}

const toTimestamp = (value) => {
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : null
}

function formatDate(value) {
  return formatBucharestDateTime(value)
}

function formatTime(value) {
  return formatBucharestTime(value, "")
}

function formatAlertLastUpdated(value) {
  return formatBucharestShortDateTime(value)
}

function compareAlertsNewestFirst(left, right) {
  const leftTime = toTimestamp(left?.created_at) ?? 0
  const rightTime = toTimestamp(right?.created_at) ?? 0
  if (rightTime !== leftTime) {
    return rightTime - leftTime
  }
  return Number(right?.id || 0) - Number(left?.id || 0)
}

function getTreatmentEventTimestamp(treatment) {
  return treatment?.timestamp || treatment?.prescribed_at || treatment?.created_at || treatment?.updated_at || null
}

function compareTreatmentsAscending(left, right) {
  const leftTime = toTimestamp(getTreatmentEventTimestamp(left)) ?? 0
  const rightTime = toTimestamp(getTreatmentEventTimestamp(right)) ?? 0
  if (leftTime !== rightTime) {
    return leftTime - rightTime
  }

  const leftId = Number(left?.id || 0)
  const rightId = Number(right?.id || 0)
  if (leftId !== rightId) {
    return leftId - rightId
  }

  const actionPriority = {add: 0, modify: 1}
  const leftAction = actionPriority[String(left?.action || "").trim().toLowerCase()] ?? 0
  const rightAction = actionPriority[String(right?.action || "").trim().toLowerCase()] ?? 0
  return leftAction - rightAction
}

function formatCompactDate(value) {
  return formatBucharestCompactDateTime(value)
}

function formatDisplayValue(value) {
  if (value == null || value === "") {
    return "--"
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "--"
    }
    return value.map((item) => formatDisplayValue(item)).join(", ")
  }
  if (typeof value === "object") {
    const entries = Object.entries(value)
      .filter(([, entryValue]) => entryValue != null && entryValue !== "")
      .map(([key, entryValue]) => `${key}: ${formatDisplayValue(entryValue)}`)
    return entries.length ? entries.join("; ") : "--"
  }
  return String(value)
}

function DetailField({label, children}) {
  const value = children == null || children === "" ? "--" : children

  return (
    <div className="medstream-compact-detail-field">
      <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
      <div className="medstream-compact-detail-value">{value}</div>
    </div>
  )
}

function SummaryValue({label, value, meta, alert}) {
  const displayValue = value == null || value === "" ? "--" : value
  const status = alert ? getAlertHistoryStatus(alert) : null
  const statusId = status?.id || "unknown"

  return (
    <div className={`medstream-compact-summary-field medstream-compact-summary-field-${statusId}`}>
      <div className="medstream-compact-summary-heading">
        <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
        {status ? (
          <span className={`medstream-vital-status medstream-vital-status-${status.id}`}>
            {status.label}
          </span>
        ) : null}
      </div>
      <div className="medstream-compact-summary-value">{displayValue}</div>
      {meta ? <Box color="text-body-secondary">{meta}</Box> : null}
    </div>
  )
}

function AttributeSummaryValue({label, value}) {
  const displayValue = value == null || value === "" ? "--" : value

  return (
    <div className="medstream-attribute-summary-cell">
      <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
      <Box className="medstream-attribute-summary-value">{displayValue}</Box>
    </div>
  )
}

function getAttributeStatusType(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (["resolved", "available", "active", "normal"].includes(normalized)) {
    return "success"
  }
  if (["improving", "in progress", "in-progress", "pending"].includes(normalized)) {
    return "in-progress"
  }
  if (["inactive", "closed", "discharged"].includes(normalized)) {
    return "stopped"
  }
  if (["critical", "failed", "error", "unresolved"].includes(normalized)) {
    return "error"
  }
  return "info"
}

function AttributeStatusValue({value}) {
  const displayValue = value == null || value === "" ? "--" : value
  const isImproving = String(displayValue).trim().toLowerCase() === "improving"

  return (
    <div className="medstream-attribute-summary-cell medstream-attribute-status-cell">
      <Box color="text-body-secondary" variant="awsui-key-label">Status</Box>
      <div className={`medstream-attribute-status-value${isImproving ? " medstream-status-improving" : ""}`}>
        <StatusIndicator type={getAttributeStatusType(displayValue)}>
          {formatDisplayValue(displayValue)}
        </StatusIndicator>
      </div>
    </div>
  )
}

function TreatmentAnalysisInfoTour({
  currentStep,
  isOpen,
  onClose,
  onStepChange,
  onToggle,
}) {
  const step = TREATMENT_ANALYSIS_HELP_STEPS[currentStep] || TREATMENT_ANALYSIS_HELP_STEPS[0]
  const isLastStep = currentStep === TREATMENT_ANALYSIS_HELP_STEPS.length - 1

  const goToPreviousStep = () => {
    onStepChange(Math.max(0, currentStep - 1))
  }

  const goToNextStep = () => {
    if (isLastStep) {
      onClose()
      return
    }
    onStepChange(Math.min(TREATMENT_ANALYSIS_HELP_STEPS.length - 1, currentStep + 1))
  }

  return (
    <span className="medstream-aws-info-anchor">
      <button
        type="button"
        className={`medstream-aws-info-trigger${isOpen ? " medstream-aws-info-trigger-open" : ""}`}
        aria-expanded={isOpen}
        aria-label={isOpen ? "Close treatment analysis guide" : "Open treatment analysis guide"}
        onClick={onToggle}
      />
      {isOpen ? (
        <span className="medstream-aws-info-card" role="dialog" aria-label="Treatment analysis guide">
          <button
            type="button"
            className="medstream-aws-info-close"
            aria-label="Close treatment analysis guide"
            onClick={onClose}
          />
          <span className="medstream-aws-info-title">{step.title}</span>
          <span className="medstream-aws-info-body">{step.body}</span>
          <span className="medstream-aws-info-footer">
            <span>Step {currentStep + 1}/{TREATMENT_ANALYSIS_HELP_STEPS.length}</span>
            <span className="medstream-aws-info-actions">
              {currentStep > 0 ? (
                <button type="button" className="medstream-aws-info-link" onClick={goToPreviousStep}>
                  Previous
                </button>
              ) : null}
              <button type="button" className="medstream-aws-info-primary" onClick={goToNextStep}>
                {isLastStep ? "Finish" : "Next"}
              </button>
            </span>
          </span>
        </span>
      ) : null}
    </span>
  )
}

function TreatmentStepTitle({children, stepIndex, analysisHelpStep, isAnalysisHelpOpen, onClose, onStepChange, onToggle}) {
  return (
    <span className="medstream-treatment-step-title">
      <span>{children}</span>
      <TreatmentAnalysisInfoTour
        currentStep={analysisHelpStep}
        isOpen={isAnalysisHelpOpen && analysisHelpStep === stepIndex}
        onClose={onClose}
        onStepChange={onStepChange}
        onToggle={() => onToggle(stepIndex)}
      />
    </span>
  )
}

function StepFunctionsMedicationDecision({
  displayedMedication,
  selectedTreatmentOutcome,
}) {
  const isImprovingOutcome = selectedTreatmentOutcome === "Improving"
  const statusType = selectedTreatmentOutcome === "Effective"
    ? "success"
    : isImprovingOutcome
      ? "in-progress"
      : "error"

  return (
    <section className="medstream-sfn-panel" aria-label="Medication decision details">
      <div className="medstream-sfn-content">
        <div className="medstream-sfn-main">
          <div className="medstream-sfn-section">
            <h4>Execution details</h4>
            <ColumnLayout columns={3} variant="text-grid">
              <DetailField label="Medication">
                {formatDisplayValue(displayedMedication.medication_name)}
              </DetailField>
              <DetailField label="Status">
                <span className={isImprovingOutcome ? "medstream-status-improving" : undefined}>
                  <StatusIndicator type={statusType}>{formatDisplayValue(selectedTreatmentOutcome)}</StatusIndicator>
                </span>
              </DetailField>
              <DetailField label="Started">{formatCompactDate(displayedMedication.timestamp || displayedMedication.created_at)}</DetailField>
              <DetailField label="Medication ID">{displayedMedication.id || "--"}</DetailField>
              <DetailField label="Dosage">{displayedMedication.dosage || "--"}</DetailField>
              <DetailField label="Frequency">{displayedMedication.frequency || "--"}</DetailField>
            </ColumnLayout>
          </div>

          <div className="medstream-sfn-section">
            <h4>Cause</h4>
            <p className="medstream-sfn-cause">{formatDisplayValue(displayedMedication.reasonText)}</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function DynamoAttributeContent({items, emptyText, pagination}) {
  return (
    <SpaceBetween size="s">
      <div className="medstream-attribute-list">
        {items.length ? (
          items.map((item) => (
            <article key={item.id} className="medstream-attribute-row">
              <div className="medstream-attribute-entry">
                <div className="medstream-attribute-primary">
                  <Box color="text-body-secondary" variant="awsui-key-label">Name</Box>
                  <strong>{formatDisplayValue(item.name)}</strong>
                </div>
                <AttributeStatusValue value={item.status}/>
                <AttributeSummaryValue label="Doctor" value={formatDisplayValue(item.modifiedBy)}/>
                <p className="medstream-attribute-note">{formatDisplayValue(item.note)}</p>
              </div>
            </article>
          ))
        ) : (
          <p className="medstream-simple-empty">{formatDisplayValue(emptyText)}</p>
        )}
      </div>
      {pagination ? <div className="medstream-simple-pagination">{pagination}</div> : null}
    </SpaceBetween>
  )
}

function ClinicalContextPanel({
  diagnosisItems,
  diagnosisEmptyText,
  diagnosisPagination,
  conditionItems,
  conditionEmptyText,
  conditionPagination,
  analysisHelpStep,
  isAnalysisHelpOpen,
  onCloseHelp,
  onStepChange,
  onToggleHelp,
}) {
  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Diagnosis and conditions linked to the medication decision."
        >
          <TreatmentStepTitle
            stepIndex={1}
            analysisHelpStep={analysisHelpStep}
            isAnalysisHelpOpen={isAnalysisHelpOpen}
            onClose={onCloseHelp}
            onStepChange={onStepChange}
            onToggle={onToggleHelp}
          >
            Clinical context
          </TreatmentStepTitle>
        </Header>
      }
    >
      <div className="medstream-clinical-context-panel">
        <section className="medstream-clinical-context-section" aria-label="Conditions">
          <h3>Conditions</h3>
          <DynamoAttributeContent
            items={conditionItems}
            emptyText={conditionEmptyText}
            pagination={conditionPagination}
          />
        </section>
        <section className="medstream-clinical-context-section" aria-label="Diagnosis">
          <h3>Diagnosis</h3>
          <DynamoAttributeContent
            items={diagnosisItems}
            emptyText={diagnosisEmptyText}
            pagination={diagnosisPagination}
          />
        </section>
      </div>
    </Container>
  )
}

function AlertHistoryTable({items, pagination}) {
  return (
    <div className="medstream-alert-history-list">
      <div className="medstream-simple-section-header">
        <h3>Alert history</h3>
      </div>
      {items.length ? (
        <div className="medstream-alert-history-items">
          {items.map((alert) => (
            <article key={alert.id} className={`medstream-alert-history-row medstream-alert-history-row-${alert.statusId}`}>
              <div className="medstream-alert-history-main">
                <StatusIndicator type={alert.status.type}>{alert.status.label}</StatusIndicator>
                <strong>{alert.vital}</strong>
                <span>{alert.time}</span>
              </div>
              <div className="medstream-alert-history-values">
                <div>
                  <span>Value</span>
                  <strong>{alert.value}</strong>
                </div>
                <div>
                  <span>Previous</span>
                  <strong>{alert.previous}</strong>
                </div>
                <div>
                  <span>Rule</span>
                  <strong>{alert.triggeredRule}</strong>
                </div>
                <div>
                  <span>State</span>
                  <strong>{alert.state}</strong>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="medstream-simple-empty">No linked alerts.</p>
      )}
      {pagination ? <div className="medstream-simple-pagination">{pagination}</div> : null}
    </div>
  )
}

function formatAlertValue(value) {
  if (!Number.isFinite(value)) {
    return "--"
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function buildCleanAlertHistoryLabel(alert) {
  const parsed = extractVitalsFromMessage(alert.message)
  const vitalKey = alertTypeToVital(alert.type)

  if (vitalKey === "heartRate") {
    const value = Number.isFinite(alert.value) ? alert.value : parsed.heartRate
    return `Heart Rate: ${formatAlertValue(value)} bpm`
  }
  if (vitalKey === "oxygen") {
    const value = Number.isFinite(alert.value) ? alert.value : parsed.oxygen
    return `Oxygen: ${formatAlertValue(value)}%`
  }
  if (vitalKey === "temperature") {
    const value = Number.isFinite(alert.value) ? alert.value : parsed.temperature
    return `Temperature: ${formatAlertValue(value)}°C`
  }
  return String(alert.message || "--")
}

function getAlertHistoryValue(alert) {
  const vitalKey = alertTypeToVital(alert.type)
  const statusVitals = getStatusVitals(alert)
  if (vitalKey === "heartRate") {
    return alert.value ?? statusVitals.heartRate
  }
  if (vitalKey === "oxygen") {
    return alert.value ?? statusVitals.oxygen
  }
  if (vitalKey === "temperature") {
    return alert.value ?? statusVitals.temperature
  }
  return alert.value
}

function getAlertVitalLabel(alert) {
  const vitalKey = alertTypeToVital(alert.type)
  if (vitalKey === "heartRate") {
    return "Heart rate"
  }
  if (vitalKey === "oxygen") {
    return "Oxygen"
  }
  if (vitalKey === "temperature") {
    return "Temperature"
  }
  return "Vital"
}

function formatAlertHistoryValue(value, vital) {
  if (!Number.isFinite(value)) {
    return "--"
  }
  if (vital === "Heart rate") {
    return `${formatAlertValue(value)} bpm`
  }
  if (vital === "Oxygen") {
    return `${formatAlertValue(value)}%`
  }
  if (vital === "Temperature") {
    return `${formatAlertValue(value)}°C`
  }
  return formatAlertValue(value)
}

function getAlertHistoryStatus(alert) {
  const severity = getAlertSeverityLevel(alert)
  if (isNormalizedAlertType(alert?.type)) {
    return {id: "normal", label: "Normal", type: "success"}
  }
  if (severity === "critical") {
    return {id: "critical", label: "Critical", type: "error"}
  }
  if (severity === "high") {
    return {id: "high", label: "High", type: "warning"}
  }
  return {id: "normal", label: "Normal", type: "success"}
}

function getTriggeredRule(alert) {
  const type = String(alert.type || "").trim().toLowerCase()
  if (isNormalizedAlertType(type)) {
    return "Back to normal"
  }
  if (type === "heart_rate_critical") {
    return "HR > 120 bpm"
  }
  if (type === "heart_rate_high") {
    return "HR > 110 bpm"
  }
  if (type === "oxygen_critical") {
    return "SpO2 < 90%"
  }
  if (type === "oxygen_low") {
    return "SpO2 < 92%"
  }
  if (type === "temperature_critical") {
    return "Temp > 39°C"
  }
  if (type === "temperature_high") {
    return "Temp > 38°C"
  }
  return buildCleanAlertHistoryLabel(alert)
}

const extractVitalsFromMessage = (message) => {
  const text = String(message || "")
  const hrMatch = text.match(/HR\s*(-?\d+(?:\.\d+)?)/i)
  const o2Match = text.match(
    /(?:SpO2\s*|oxygen.*?:\s*)(\d+(?:\.\d+)?)/i,
  )
  const tempMatch = text.match(/Temp\s*(-?\d+(?:\.\d+)?)/i)
  return {
    heartRate: hrMatch ? Number(hrMatch[1]) : null,
    oxygen: o2Match ? Number(o2Match[1]) : null,
    temperature: tempMatch ? Number(tempMatch[1]) : null,
  }
}

const getAlertIdentityKey = (alert = {}) => {
  const idPart = alert?.id != null ? `id:${String(alert.id)}` : ""
  const patientPart = String(alert?.patient_id ?? alert?.patientId ?? alert?.patient ?? "")
  const typePart = String(alert?.alert_type ?? alert?.type ?? "").trim().toLowerCase()
  const createdAtPart = String(alert?.created_at ?? alert?.createdAt ?? "")
  const messagePart = String(alert?.message ?? "").trim()
  const valuePart = String(alert?.value ?? "")
  return idPart || [patientPart, typePart, createdAtPart, messagePart, valuePart].join("|")
}

const upsertAlertsNewestFirst = (currentAlerts = [], incomingAlert) => {
  const normalizedCurrent = Array.isArray(currentAlerts) ? currentAlerts : []
  const dedupeMap = new Map(normalizedCurrent.map((alert) => [getAlertIdentityKey(alert), alert]))
  dedupeMap.set(getAlertIdentityKey(incomingAlert), incomingAlert)
  return Array.from(dedupeMap.values()).sort(compareAlertsNewestFirst)
}

const dedupeAlertsNewestFirst = (alerts = []) => {
  const sorted = [...(Array.isArray(alerts) ? alerts : [])].sort(compareAlertsNewestFirst)
  const seenKeys = new Set()
  return sorted.filter((alert) => {
    const key = getAlertIdentityKey(alert)
    if (seenKeys.has(key)) {
      return false
    }
    seenKeys.add(key)
    return true
  })
}

const getMessagePatientId = (msg = {}) => {
  const candidateIds = [
    msg?.data?.patient_id,
    msg?.data?.patientId,
    msg?.data?.patient?.id,
    msg?.data?.payload?.patient_id,
    msg?.data?.payload?.patientId,
    msg?.patient_id,
    msg?.patientId,
  ]
  const matched = candidateIds.find((id) => id != null && String(id).trim() !== "")
  return matched == null ? null : String(matched)
}

const getIncomingAlertPayload = (msg = {}) => {
  const payload = msg?.data?.alert || msg?.data?.payload?.alert || msg?.data || msg?.alert || null
  if (!payload || typeof payload !== "object") {
    return null
  }
  return payload
}

const isAlertRelatedMessage = (msg = {}) => {
  const normalizedType = String(msg?.type || "").trim().toLowerCase()
  if (normalizedType.includes("alert")) {
    return true
  }
  const payload = getIncomingAlertPayload(msg)
  if (!payload) {
    return false
  }
  return Boolean(payload.alert_type || payload.type || payload.severity)
}

const normalizeTreatmentAlert = (alert) => {
  const normalizedType = normalizeAlertType(alert?.alert_type || alert?.type, alert?.severity)
  const normalizedSeverity = String(alert?.severity || "").trim().toLowerCase()
  const numericValue = Number(alert?.value)
  const oxygenValue =
    alert?.vitals?.oxygen != null
      ? Number(alert.vitals.oxygen)
      : null

  return {
    ...alert,
    type: normalizedType,
    severity: normalizedSeverity,
    time: toTimestamp(alert?.created_at),
    value: Number.isFinite(numericValue) ? numericValue : null,
    vitals: {
      heartRate: Number.isFinite(Number(alert?.vitals?.heartRate)) ? Number(alert?.vitals?.heartRate) : null,
      oxygen: Number.isFinite(oxygenValue) ? oxygenValue : null,
      temperature: Number.isFinite(Number(alert?.vitals?.temperature)) ? Number(alert?.vitals?.temperature) : null,
    },
  }
}

const getStatusVitals = (alert) => {
  if (!alert) {
    return {heartRate: null, oxygen: null, temperature: null}
  }
  const parsedFromMessage = extractVitalsFromMessage(alert.message)
  return {
    heartRate: alert.vitals?.heartRate ?? parsedFromMessage.heartRate,
    oxygen: alert.vitals?.oxygen ?? parsedFromMessage.oxygen,
    temperature: alert.vitals?.temperature ?? parsedFromMessage.temperature,
  }
}

export default function PatientTreatmentAnalysisSection({
  selectedPatientId = null,
  showSelectedPatientSummary = false,
}) {
  const {notifyError} = useNotifications()
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(true)
  const [showFullAlertHistory, setShowFullAlertHistory] = useState(false)
  const [alertHistoryPage, setAlertHistoryPage] = useState(1)
  const [medicationPage, setMedicationPage] = useState(1)
  const [diagnosisPage, setDiagnosisPage] = useState(1)
  const [conditionPage, setConditionPage] = useState(1)
  const [isAnalysisHelpOpen, setIsAnalysisHelpOpen] = useState(false)
  const [analysisHelpStep, setAnalysisHelpStep] = useState(0)
  const analysisRefetchDebounceRef = useRef(null)

  const closeAnalysisHelp = useCallback(() => {
    setIsAnalysisHelpOpen(false)
    setAnalysisHelpStep(0)
  }, [])

  const changeAnalysisHelpStep = useCallback((stepIndex) => {
    setAnalysisHelpStep(stepIndex)
    setIsAnalysisHelpOpen(true)
  }, [])

  const toggleAnalysisHelpStep = useCallback((stepIndex) => {
    if (isAnalysisHelpOpen && analysisHelpStep === stepIndex) {
      closeAnalysisHelp()
      return
    }
    setAnalysisHelpStep(stepIndex)
    setIsAnalysisHelpOpen(true)
  }, [analysisHelpStep, closeAnalysisHelp, isAnalysisHelpOpen])

  const loadAnalysis = useCallback(async (patientId, options = {}) => {
    const {isBackground = false} = options
    if (!isBackground) {
      setIsLoadingAnalysis(true)
    }
    try {
      const response = await getPatientTreatmentAnalysis(patientId)
      const responseData = getResponseData(response) || null
      if (!responseData) {
        setAnalysis(null)
      } else {
        setAnalysis({
          ...responseData,
          alerts: dedupeAlertsNewestFirst(responseData.alerts || []),
        })
      }
    } catch (error) {
      if (!isBackground) {
        setAnalysis(null)
        notifyError(getErrorMessage(error))
      }
    } finally {
      if (!isBackground) {
        setIsLoadingAnalysis(false)
      }
    }
  }, [notifyError])

  useEffect(() => {
    if (!selectedPatientId) {
      return
    }
    setShowFullAlertHistory(false)
    setAlertHistoryPage(1)
    setMedicationPage(1)
    setDiagnosisPage(1)
    setConditionPage(1)
    setIsAnalysisHelpOpen(false)
    setAnalysisHelpStep(0)

    const loadInitial = async () => {
      try {
        const patientResponse = await getPatient(selectedPatientId)
        const patientData = getResponseData(patientResponse)
        if (patientData) {
          setSelectedPatient({
            cnp: patientData.cnp,
            full_name: `${patientData.last_name} ${patientData.first_name}`.trim(),
            is_discharged: Boolean(patientData.is_discharged),
          })
        }
      } catch (error) {
        notifyError(getErrorMessage(error))
      }

      await loadAnalysis(selectedPatientId)
    }

    loadInitial().then(() => {
    })
  }, [loadAnalysis, notifyError, selectedPatientId])

  useEffect(() => {
    return () => {
      if (analysisRefetchDebounceRef.current) {
        window.clearTimeout(analysisRefetchDebounceRef.current)
        analysisRefetchDebounceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!selectedPatientId) {
      return
    }

    const scheduleBackgroundAnalysisRefresh = () => {
      if (analysisRefetchDebounceRef.current) {
        window.clearTimeout(analysisRefetchDebounceRef.current)
      }
      analysisRefetchDebounceRef.current = window.setTimeout(() => {
        analysisRefetchDebounceRef.current = null
        loadAnalysis(selectedPatientId, {isBackground: true}).then(() => {
        })
      }, 500)
    }

    const socket = createWebSocket((msg) => {
      if (!isAlertRelatedMessage(msg)) {
        return
      }

      const messagePatientId = getMessagePatientId(msg)
      if (messagePatientId == null || String(messagePatientId) !== String(selectedPatientId)) {
        return
      }

      const incomingAlert = getIncomingAlertPayload(msg)
      if (!incomingAlert) {
        scheduleBackgroundAnalysisRefresh()
        return
      }

      setAnalysis((currentAnalysis) => {
        const base = currentAnalysis || {}
        const incomingAlertWithPatient = {
          ...incomingAlert,
          patient_id: incomingAlert.patient_id ?? incomingAlert.patientId ?? messagePatientId,
          created_at: incomingAlert.created_at || incomingAlert.createdAt || new Date().toISOString(),
        }

        return {
          ...base,
          alerts: upsertAlertsNewestFirst(base.alerts || [], incomingAlertWithPatient),
        }
      })
      setAlertHistoryPage(1)
      scheduleBackgroundAnalysisRefresh()
    })

    return () => {
      if (analysisRefetchDebounceRef.current) {
        window.clearTimeout(analysisRefetchDebounceRef.current)
        analysisRefetchDebounceRef.current = null
      }
      socket.close()
    }
  }, [loadAnalysis, selectedPatientId])

  const parsedAlerts = useMemo(() => {
    return dedupeAlertsNewestFirst(analysis?.alerts || [])
      .map((alert) => normalizeTreatmentAlert(alert))
      .filter((alert) => alert.time !== null)
      .sort((left, right) => compareAlertsNewestFirst(left, right))
  }, [analysis])

  const normalizedTreatments = useMemo(() => {
    const medicationsAscending = [...(analysis?.medications || [])].sort(compareTreatmentsAscending)
    return medicationsAscending.map((medication, index) => {
      const relatedAlerts = medication.reasoning?.alerts || []
      const relatedDiagnoses = medication.reasoning?.diagnoses || []
      const relatedConditions = medication.reasoning?.conditions || []
      const outcome = normalizeOutcomeLabel(medication.outcome)
      const outcomeConfig = OUTCOME_CONFIG[outcome] || OUTCOME_CONFIG.Ineffective
      const actionTime = getTreatmentEventTimestamp(medication)

      let reasonText = "Prescribed based on current clinical assessment."
      if (relatedAlerts.length && relatedDiagnoses.length) {
        reasonText = "Prescribed due to abnormal vital signs (alerts) and to treat diagnosed condition."
      } else if (relatedAlerts.length) {
        reasonText = "Prescribed due to abnormal vital signs (alerts)."
      } else if (relatedDiagnoses.length) {
        reasonText = "Prescribed to treat diagnosed condition."
      }

      return {
        id: medication.id,
        action: medication.action || "add",
        treatment_index: index + 1,
        medication_name: medication.name || "--",
        dosage: medication.dosage,
        frequency: medication.frequency,
        created_at: medication.created_at || medication.prescribed_at,
        updated_at: medication.updated_at,
        timestamp: actionTime,
        displayed_date: formatDate(actionTime || medication.updated_at || medication.created_at),
        outcome,
        outcomeValue: outcomeConfig.value,
        notes: medication.notes || "",
        modified_by: medication.modified_by || "",
        related_alerts: relatedAlerts,
        related_diagnoses: relatedDiagnoses,
        related_conditions: relatedConditions,
        reasonText,
        previous_alert: medication.previous_alert || null,
        selected_vital_source: medication.selected_vital_source || null,
        selected_vital_timestamp: medication.selected_vital_timestamp || null,
        selected_vital: medication.selected_vital || null,
        evaluation_start: medication.evaluation_start || null,
        evaluation_end: medication.evaluation_end || null,
        evaluated_vital_timestamp: medication.evaluated_vital_timestamp || null,
        evaluated_vital: medication.evaluated_vital || null,
        outcome_reason: medication.outcome_reason || null,
        outcome_evidence: medication.outcome_evidence || null,
      }
    })
  }, [analysis])

  const chartData = useMemo(() => {
    return normalizedTreatments.map((treatment) => ({
      treatmentIndex: treatment.treatment_index,
      medicationId: treatment.id,
      medicationName: treatment.medication_name,
      medication: treatment.medication_name,
      time: treatment.displayed_date,
      timestampLabel: formatCompactDate(treatment.timestamp || treatment.updated_at || treatment.created_at),
      decisionTimeLabel: treatment.timestamp ? formatTime(treatment.timestamp) : "",
      previousAlertType: treatment.previous_alert?.alert_type || "--",
      previousAlertSeverity: treatment.previous_alert?.severity || "--",
      previousAlertTimeLabel: treatment.previous_alert?.created_at ? formatDate(treatment.previous_alert.created_at) : "--",
      outcome: treatment.outcome,
      outcomeValue: treatment.outcomeValue,
      outcomeColor: (OUTCOME_CONFIG[treatment.outcome] || OUTCOME_CONFIG.Ineffective).color,
    }))
  }, [normalizedTreatments])
  const treatmentOutcomeAreaSeries = useMemo(() => {
    const formatOutcomeFlag = (x, outcome) => {
      const point = chartData.find((entry) => Number(entry.treatmentIndex) === Number(x))
      return point?.outcome === outcome ? "1" : "0"
    }
    const toAreaData = (minimumLevel) => chartData.map((point) => {
      const level = Number(point.outcomeValue) + 1

      return {
        x: Number(point.treatmentIndex),
        y: level >= minimumLevel ? 1 : 0,
      }
    })

    return [
      {
        type: "area",
        title: "Ineffective",
        color: OUTCOME_CONFIG.Ineffective.color,
        data: toAreaData(1),
        valueFormatter: (_value, x) => formatOutcomeFlag(x, "Ineffective"),
      },
      {
        type: "area",
        title: "Improving",
        color: OUTCOME_CONFIG.Improving.color,
        data: toAreaData(2),
        valueFormatter: (_value, x) => formatOutcomeFlag(x, "Improving"),
      },
      {
        type: "area",
        title: "Effective",
        color: OUTCOME_CONFIG.Effective.color,
        data: toAreaData(3),
        valueFormatter: (_value, x) => formatOutcomeFlag(x, "Effective"),
      },
    ]
  }, [chartData])
  const formatTreatmentOutcomeXTick = useCallback((value) => {
    if (!Number.isInteger(value)) {
      return ""
    }

    const point = chartData.find((entry) => Number(entry.treatmentIndex) === Number(value))
    return point?.timestampLabel || ""
  }, [chartData])
  const treatmentOutcomeXDomain = useMemo(() => {
    const xValues = chartData.map((point) => Number(point.treatmentIndex)).filter(Number.isFinite)
    if (!xValues.length) {
      return [0, 1]
    }

    const min = Math.min(...xValues)
    const max = Math.max(...xValues)
    return min === max ? [min - 0.5, max + 0.5] : [min, max]
  }, [chartData])

  const treatmentTimelineEvaluation = useMemo(() => {
    const latestAlert = parsedAlerts[0] || null
    const latestByVital = (vitalKey, options = {}) => {
      const minTime = options.minTime ?? null
      return parsedAlerts.find((alert) => (
        alertTypeToVital(alert.type) === vitalKey
        && alert.value != null
        && (minTime == null || alert.time > minTime)
      )) || null
    }

    const latestHeartRate = latestByVital("heartRate")
    const latestOxygen = latestByVital("oxygen")
    const latestTemperature = latestByVital("temperature")

    const latestNormalizedByVital = (vitalKey) => parsedAlerts.find((alert) => (
      alertTypeToVital(alert.type) === vitalKey
      && isNormalizedAlertType(alert.type)
    )) || null

    const latestHeartRateNormalized = latestNormalizedByVital("heartRate")
    const latestOxygenNormalized = latestNormalizedByVital("oxygen")
    const latestTemperatureNormalized = latestNormalizedByVital("temperature")

    const heartRateNormalizedVitals = getStatusVitals(latestHeartRateNormalized)
    const oxygenNormalizedVitals = getStatusVitals(latestOxygenNormalized)
    const temperatureNormalizedVitals = getStatusVitals(latestTemperatureNormalized)

    const finalValues = {
      heartRate: latestHeartRate?.value ?? heartRateNormalizedVitals.heartRate ?? null,
      oxygen: latestOxygen?.value ?? oxygenNormalizedVitals.oxygen ?? null,
      temperature: latestTemperature?.value ?? temperatureNormalizedVitals.temperature ?? null,
    }

    const latestVitalAlerts = {
      heartRate: latestHeartRate || latestHeartRateNormalized || null,
      oxygen: latestOxygen || latestOxygenNormalized || null,
      temperature: latestTemperature || latestTemperatureNormalized || null,
    }

    const finalTreatmentOutcome = chartData.length
      ? chartData[chartData.length - 1].outcome
      : "Ineffective"
    const outcome = finalTreatmentOutcome

    const lastUpdated = latestAlert?.created_at ? formatAlertLastUpdated(latestAlert.created_at) : "--"

    return {
      outcome,
      latestAlertSummary: {
        ...finalValues,
        lastUpdated,
        latestVitalAlerts,
        summary: "Values use vital-specific normalized events and are overridden by newer alerts for that same vital.",
      },
    }
  }, [chartData, parsedAlerts])

  const medicationHistory = useMemo(
    () => [...normalizedTreatments].reverse(),
    [normalizedTreatments],
  )

  const diagnosisStatusDetails = useMemo(() => {
    return [...(analysis?.diagnoses || [])]
      .sort((left, right) => {
        const leftTime = toTimestamp(left?.created_at) ?? 0
        const rightTime = toTimestamp(right?.created_at) ?? 0
        if (rightTime !== leftTime) {
          return rightTime - leftTime
        }
        return Number(right?.id || 0) - Number(left?.id || 0)
      })
  }, [analysis])

  const conditionStatusDetails = useMemo(() => {
    return [...(analysis?.conditions || [])]
      .sort((left, right) => {
        const leftTime = toTimestamp(left?.updated_at || left?.diagnosed_at) ?? 0
        const rightTime = toTimestamp(right?.updated_at || right?.diagnosed_at) ?? 0
        if (rightTime !== leftTime) {
          return rightTime - leftTime
        }
        return Number(right?.id || 0) - Number(left?.id || 0)
      })
  }, [analysis])
  const totalDiagnosisPages = Math.max(1, Math.ceil(diagnosisStatusDetails.length / DIAGNOSIS_PAGE_SIZE))
  const totalConditionPages = Math.max(1, Math.ceil(conditionStatusDetails.length / CONDITION_PAGE_SIZE))
  const paginatedDiagnosisStatusDetails = useMemo(() => {
    const start = (diagnosisPage - 1) * DIAGNOSIS_PAGE_SIZE
    const end = diagnosisPage * DIAGNOSIS_PAGE_SIZE
    return diagnosisStatusDetails.slice(start, end)
  }, [diagnosisPage, diagnosisStatusDetails])
  const paginatedConditionStatusDetails = useMemo(() => {
    const start = (conditionPage - 1) * CONDITION_PAGE_SIZE
    const end = conditionPage * CONDITION_PAGE_SIZE
    return conditionStatusDetails.slice(start, end)
  }, [conditionPage, conditionStatusDetails])
  const diagnosisListItems = useMemo(() => paginatedDiagnosisStatusDetails.map((diagnosis) => ({
    id: diagnosis.id || `${diagnosis.diagnosis}-${diagnosis.created_at}`,
    name: diagnosis.diagnosis || "--",
    status: diagnosis.status || "--",
    note: diagnosis.status_note || diagnosis.notes || "--",
    modifiedBy: diagnosis.modified_by || "--",
  })), [paginatedDiagnosisStatusDetails])
  const conditionListItems = useMemo(() => paginatedConditionStatusDetails.map((condition) => ({
    id: condition.id || `${condition.name}-${condition.updated_at || condition.diagnosed_at}`,
    name: condition.name || "--",
    status: condition.status || "--",
    note: condition.notes || "--",
    modifiedBy: condition.modified_by || "--",
  })), [paginatedConditionStatusDetails])

  const totalMedicationPages = Math.max(1, medicationHistory.length)
  const displayedMedication = medicationHistory.length ? medicationHistory[Math.max(0, medicationPage - 1)] : null

  const latestAlertSummary = treatmentTimelineEvaluation.latestAlertSummary
  const finalOutcome = treatmentTimelineEvaluation.outcome
  const selectedTreatmentOutcome = displayedMedication?.outcome || "--"
  const hasInconsistentDischarge = Boolean(selectedPatient?.is_discharged) && finalOutcome !== "Effective"
  const fullAlertHistory = useMemo(() => {
    const normalizedAlerts = dedupeAlertsNewestFirst(analysis?.alerts || [])
      .map((alert) => normalizeTreatmentAlert(alert))
      .map((alert) => ({...alert, time: toTimestamp(alert.created_at)}))
      .filter((alert) => alert.time !== null)
      .sort((left, right) => compareAlertsNewestFirst(left, right))

    const latestAlertKeyByVital = new Map()
    normalizedAlerts.forEach((alert) => {
      const vital = getAlertVitalLabel(alert)
      if (!latestAlertKeyByVital.has(vital)) {
        latestAlertKeyByVital.set(vital, getAlertIdentityKey(alert))
      }
    })

    const previousValueByVital = new Map()
    return [...normalizedAlerts]
      .sort((left, right) => {
        if (left.time !== right.time) {
          return left.time - right.time
        }
        return Number(left?.id || 0) - Number(right?.id || 0)
      })
      .map((alert) => {
        const vital = getAlertVitalLabel(alert)
        const numericValue = getAlertHistoryValue(alert)
        const previousValue = previousValueByVital.get(vital) ?? null
        if (Number.isFinite(numericValue)) {
          previousValueByVital.set(vital, numericValue)
        }
        const status = getAlertHistoryStatus(alert)
        return {
          id: alert.id,
          key: getAlertIdentityKey(alert),
          status,
          statusId: status.id,
          vital,
          value: formatAlertHistoryValue(numericValue, vital),
          previous: formatAlertHistoryValue(previousValue, vital),
          triggeredRule: getTriggeredRule(alert),
          createdAt: alert.created_at,
          time: formatAlertLastUpdated(alert.created_at),
          state: latestAlertKeyByVital.get(vital) === getAlertIdentityKey(alert) ? "Active" : "Replaced",
        }
      })
      .sort((left, right) => {
        const leftTime = toTimestamp(left?.createdAt) ?? 0
        const rightTime = toTimestamp(right?.createdAt) ?? 0
        if (rightTime !== leftTime) {
          return rightTime - leftTime
        }
        return Number(right?.id || 0) - Number(left?.id || 0)
      })
  }, [analysis])

  const totalAlertHistoryPages = Math.max(1, Math.ceil(fullAlertHistory.length / ALERT_HISTORY_EXPANDED_PAGE_SIZE))
  const paginatedAlertHistory = useMemo(() => {
    const start = (alertHistoryPage - 1) * ALERT_HISTORY_EXPANDED_PAGE_SIZE
    const end = alertHistoryPage * ALERT_HISTORY_EXPANDED_PAGE_SIZE
    return fullAlertHistory.slice(start, end)
  }, [alertHistoryPage, fullAlertHistory])

  useEffect(() => {
    if (alertHistoryPage > totalAlertHistoryPages) {
      setAlertHistoryPage(totalAlertHistoryPages)
    }
  }, [alertHistoryPage, totalAlertHistoryPages])

  useEffect(() => {
    if (medicationPage > totalMedicationPages) {
      setMedicationPage(totalMedicationPages)
    }
  }, [medicationPage, totalMedicationPages])
  useEffect(() => {
    if (diagnosisPage > totalDiagnosisPages) {
      setDiagnosisPage(1)
    }
  }, [diagnosisPage, totalDiagnosisPages])
  useEffect(() => {
    if (conditionPage > totalConditionPages) {
      setConditionPage(totalConditionPages)
    }
  }, [conditionPage, totalConditionPages])

  if (isLoadingAnalysis) {
    return (
      <section className="medstream-treatment-analysis-surface">
        <LoadingSpinner/>
      </section>
    )
  }

  return (
    <section className="medstream-treatment-analysis-surface">
      <SpaceBetween size="m">
        <Container
          header={
            <Header
              variant="h2"
              description="Timeline and reasoning for medications, alerts, diagnoses, and conditions."
            >
              Patient treatment analysis
            </Header>
          }
        >
          <SpaceBetween size="m">
            {showSelectedPatientSummary && selectedPatient ? (
              <Box color="text-body-secondary">{selectedPatient.cnp} - {selectedPatient.full_name}</Box>
            ) : null}

            {!isLoadingAnalysis && !analysis ? (
              <Box color="text-body-secondary">Patient treatment analysis is not available.</Box>
            ) : null}

            {!isLoadingAnalysis && analysis ? (
              <div className="medstream-chart-panel medstream-treatment-chart-panel">
                <AreaChart
                  ariaLabel="Treatment outcome trend"
                  height={240}
                  hideFilter
                  i18nStrings={AREA_CHART_I18N_STRINGS}
                  series={treatmentOutcomeAreaSeries}
                  visibleSeries={treatmentOutcomeAreaSeries}
                  onFilterChange={() => {}}
                  statusType="finished"
                  xDomain={treatmentOutcomeXDomain}
                  xScaleType="linear"
                  xTitle="Treatment"
                  xTickFormatter={formatTreatmentOutcomeXTick}
                  yDomain={[0, 3]}
                  yTickFormatter={formatOutcomeScale}
                  yTitle="Outcome"
                  detailTotalFormatter={formatOutcomeScale}
                  empty={<Box color="text-body-secondary">No treatment outcome data available.</Box>}
                />
              </div>
            ) : null}
          </SpaceBetween>
        </Container>

        {!isLoadingAnalysis && analysis ? (
          <SpaceBetween size="m">
          {hasInconsistentDischarge ? (
            <Alert type="warning" header="Inconsistent discharge state">
              Patient is discharged but the final treatment outcome is not Effective.
            </Alert>
          ) : null}

          <SpaceBetween size="m">
            <Container
              header={
                <Header
                  variant="h2"
                  description={`Last update: ${latestAlertSummary.lastUpdated}`}
                  actions={
                    fullAlertHistory.length ? (
                      <button
                        type="button"
                        className="medstream-history-toggle-button"
                        aria-expanded={showFullAlertHistory}
                        onClick={() => {
                          setShowFullAlertHistory((current) => {
                            const next = !current
                            setAlertHistoryPage(1)
                            return next
                          })
                        }}
                      >
                        <span className="medstream-history-toggle-icon" aria-hidden="true" />
                        <span>{showFullAlertHistory ? "Show fewer" : "Show more"}</span>
                      </button>
                    ) : null
                  }
                >
                  <TreatmentStepTitle
                    stepIndex={0}
                    analysisHelpStep={analysisHelpStep}
                    isAnalysisHelpOpen={isAnalysisHelpOpen}
                    onClose={closeAnalysisHelp}
                    onStepChange={changeAnalysisHelpStep}
                    onToggle={toggleAnalysisHelpStep}
                  >
                    Latest alert summary
                  </TreatmentStepTitle>
                </Header>
              }
            >
              <SpaceBetween size="m">
                <ColumnLayout columns={3} variant="text-grid">
                  <SummaryValue
                    label="Heart rate"
                    value={latestAlertSummary.heartRate != null ? `${latestAlertSummary.heartRate} bpm` : "--"}
                    meta={formatAlertFriendlyTime(latestAlertSummary.latestVitalAlerts.heartRate?.created_at)}
                    alert={latestAlertSummary.latestVitalAlerts.heartRate}
                  />
                  <SummaryValue
                    label="Oxygen"
                    value={latestAlertSummary.oxygen != null ? `${latestAlertSummary.oxygen}%` : "--"}
                    meta={formatAlertFriendlyTime(latestAlertSummary.latestVitalAlerts.oxygen?.created_at)}
                    alert={latestAlertSummary.latestVitalAlerts.oxygen}
                  />
                  <SummaryValue
                    label="Temperature"
                    value={latestAlertSummary.temperature != null ? `${latestAlertSummary.temperature}°C` : "--"}
                    meta={formatAlertFriendlyTime(latestAlertSummary.latestVitalAlerts.temperature?.created_at)}
                    alert={latestAlertSummary.latestVitalAlerts.temperature}
                  />
                </ColumnLayout>
                <p className="medstream-latest-alert-copy">{latestAlertSummary.summary}</p>
                {showFullAlertHistory ? (
                  <div className="medstream-alert-history">
                    <AlertHistoryTable
                      items={paginatedAlertHistory}
                      pagination={
                        fullAlertHistory.length > ALERT_HISTORY_EXPANDED_PAGE_SIZE ? (
                          <Pagination
                            currentPageIndex={alertHistoryPage}
                            pagesCount={totalAlertHistoryPages}
                            onChange={({detail}) => setAlertHistoryPage(detail.currentPageIndex)}
                          />
                        ) : null
                      }
                    />
                  </div>
                ) : null}
              </SpaceBetween>
            </Container>

            <ClinicalContextPanel
              diagnosisItems={diagnosisStatusDetails.length ? diagnosisListItems : []}
              diagnosisEmptyText={displayedMedication?.related_diagnoses?.length ? formatDisplayValue(displayedMedication.related_diagnoses) : "No linked diagnosis."}
              diagnosisPagination={
                <Pagination
                  currentPageIndex={diagnosisPage}
                  pagesCount={totalDiagnosisPages}
                  onChange={({detail}) => setDiagnosisPage(detail.currentPageIndex)}
                />
              }
              conditionItems={conditionStatusDetails.length ? conditionListItems : []}
              conditionEmptyText={displayedMedication?.related_conditions?.length ? formatDisplayValue(displayedMedication.related_conditions) : "No linked conditions."}
              conditionPagination={
                <Pagination
                  currentPageIndex={conditionPage}
                  pagesCount={totalConditionPages}
                  onChange={({detail}) => setConditionPage(detail.currentPageIndex)}
                />
              }
              analysisHelpStep={analysisHelpStep}
              isAnalysisHelpOpen={isAnalysisHelpOpen}
              onCloseHelp={closeAnalysisHelp}
              onStepChange={changeAnalysisHelpStep}
              onToggleHelp={toggleAnalysisHelpStep}
            />

            {displayedMedication ? (
              <Container
                header={
                  <Header
                    variant="h2"
                    description="Medication decision, execution details, and clinical cause."
                    actions={
                      <Pagination
                        currentPageIndex={medicationPage}
                        pagesCount={totalMedicationPages}
                        onChange={({detail}) => setMedicationPage(detail.currentPageIndex)}
                      />
                    }
                  >
                    <TreatmentStepTitle
                      stepIndex={2}
                      analysisHelpStep={analysisHelpStep}
                      isAnalysisHelpOpen={isAnalysisHelpOpen}
                      onClose={closeAnalysisHelp}
                      onStepChange={changeAnalysisHelpStep}
                      onToggle={toggleAnalysisHelpStep}
                    >
                      Medication decision
                    </TreatmentStepTitle>
                  </Header>
                }
              >
                <StepFunctionsMedicationDecision
                  displayedMedication={displayedMedication}
                  selectedTreatmentOutcome={selectedTreatmentOutcome}
                />
              </Container>
            ) : (
              <Container>
                <Box color="text-body-secondary">No treatment history available.</Box>
              </Container>
            )}
          </SpaceBetween>
          </SpaceBetween>
        ) : null}

      </SpaceBetween>
    </section>
  )
}
