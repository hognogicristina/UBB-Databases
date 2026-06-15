import {useState} from "react"
import {
  Alert,
  Box,
  Container,
  Header,
  SegmentedControl,
  SpaceBetween,
  Steps,
} from "@cloudscape-design/components"
import LoadingSpinner from "./LoadingSpinner.jsx"
import {formatBucharestDateTime} from "../utils/time.js"

const SUMMARY_VIEW_OPTIONS = [
  {id: "overview", text: "Overview"},
  {id: "metrics", text: "Metrics"},
  {id: "clinical", text: "Clinical notes"},
]

function formatDateTime(value) {
  return formatBucharestDateTime(value)
}

function formatVital(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (!normalized || normalized === "none") {
    return "None"
  }
  if (normalized === "heart_rate") {
    return "Heart rate"
  }
  if (normalized === "oxygen_saturation") {
    return "Oxygen saturation"
  }
  if (normalized === "temperature") {
    return "Temperature"
  }
  return normalized.replaceAll("_", " ")
}

function normalizeOutcome(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (normalized === "effective") {
    return "Effective"
  }
  if (normalized === "improving") {
    return "Improving"
  }
  if (normalized === "ineffective") {
    return "Ineffective"
  }
  return "Not available"
}

function normalizePatientState(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (!normalized) {
    return "Not available"
  }
  return normalized.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function StatTile({label, value, tone = "neutral"}) {
  return (
    <SummaryValue label={label} value={value} tone={tone}/>
  )
}

function outcomeTone(value) {
  const normalized = normalizeOutcome(value)
  if (normalized === "Effective") {
    return "success"
  }
  if (normalized === "Improving") {
    return "warning"
  }
  if (normalized === "Ineffective") {
    return "danger"
  }
  return "neutral"
}

function vitalTone(value) {
  const normalized = String(value || "").trim().toLowerCase()
  if (normalized === "oxygen_saturation") {
    return "info"
  }
  if (normalized === "heart_rate") {
    return "danger"
  }
  if (normalized === "temperature") {
    return "warning"
  }
  return "neutral"
}

function toSafeCount(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric < 0) {
    return 0
  }
  return Math.round(numeric)
}

function responseInterpretation(score) {
  if (score >= 75) {
    return "Strong treatment response"
  }
  if (score >= 45) {
    return "Partial treatment response"
  }
  return "Limited treatment response"
}

function Section({title, children}) {
  return (
    <section className="post-discharge-unframed-section">
      <div className="post-discharge-unframed-section-header">
        <Header variant="h2">{title}</Header>
      </div>
      {children}
    </section>
  )
}

function PlainSection({title, children}) {
  return (
    <div className="post-discharge-plain-section">
      <Box variant="h2">{title}</Box>
      {children}
    </div>
  )
}

function SummaryText({title, children}) {
  return (
    <SpaceBetween size="xs">
      <Box variant="h3">{title}</Box>
      <Box color="text-body-primary" variant="p">{children}</Box>
    </SpaceBetween>
  )
}

function LegendItem({label, value, tone}) {
  return <SummaryValue label={label} value={value} tone={tone}/>
}

function stepStatusFromTone(tone) {
  if (tone === "success") {
    return "success"
  }
  if (tone === "warning") {
    return "warning"
  }
  if (tone === "danger") {
    return "error"
  }
  return "info"
}

function MetricStepValue({value, tone = "neutral"}) {
  const displayValue = value == null || value === "" ? "--" : value

  return (
    <div className={`post-discharge-summary-value post-discharge-step-value post-discharge-summary-value-${tone}`}>
      {displayValue}
    </div>
  )
}

function MetricStepsSection({title, subtitle, items}) {
  return (
    <section className="post-discharge-metric-steps-section">
      <div className="post-discharge-metric-steps-header">
        <Header variant="h2" description={subtitle}>{title}</Header>
      </div>
      <Steps
        ariaLabel={title}
        className="post-discharge-metric-steps"
        steps={items.map(({label, value, tone = "neutral"}) => ({
          status: stepStatusFromTone(tone),
          statusIconAriaLabel: label,
          header: label,
          details: <MetricStepValue value={value} tone={tone}/>,
        }))}
      />
    </section>
  )
}

function TreatmentResponseMeter({value, description, additionalInfo}) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0))

  return (
    <div
      className="post-discharge-response-meter"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={safeValue}
      aria-label="Treatment response score"
    >
      <div className="post-discharge-response-meter-header">
        <div>
          <div className="post-discharge-response-meter-label">Treatment response score</div>
          <div className="post-discharge-response-meter-description">{description}</div>
        </div>
        <div className="post-discharge-response-meter-percent">{safeValue}%</div>
      </div>
      <div className="post-discharge-response-meter-track">
        <div className="post-discharge-response-meter-fill" style={{width: `${safeValue}%`}}/>
      </div>
      <div className="post-discharge-response-meter-info">{additionalInfo}</div>
    </div>
  )
}

function SummaryValue({label, value, tone = "neutral"}) {
  const displayValue = value == null || value === "" ? "--" : value

  return (
    <div className="post-discharge-value-block">
      <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
      <div className={`post-discharge-summary-value post-discharge-summary-value-${tone}`}>
        {displayValue}
      </div>
    </div>
  )
}

export default function PostDischargeClinicalSummaryCard({summary, isLoading = false}) {
  const [selectedView, setSelectedView] = useState("overview")

  if (isLoading) {
    return <LoadingSpinner text="Loading post-discharge clinical summary..."/>
  }

  if (!summary) {
    return null
  }

  const status = String(summary.status || "").trim().toLowerCase()
  if (status === "not_available") {
    return null
  }

  const dischargeReason = summary.discharge_reason || "Not recorded."
  const finalOutcome = normalizeOutcome(summary.final_treatment_outcome)
  const finalPatientState = normalizePatientState(summary.final_patient_state)
  const problematicVital = formatVital(summary.most_problematic_vital)
  const generatedAt = formatDateTime(summary.generated_at)

  if (status === "pending") {
    return (
      <Container
        header={
          <Header
            variant="h2"
            description="The discharge record is available while generated insights are still pending."
          >
            Post-Discharge Clinical Summary
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Alert type="info" header="Clinical summary is being prepared.">
            Generated insights will appear here when processing is complete.
          </Alert>
          <div className="post-discharge-fit-grid">
            <StatTile label="Discharge reason" value={dischargeReason}/>
            <StatTile label="Discharge date" value={formatDateTime(summary.discharge_date)}/>
          </div>
        </SpaceBetween>
      </Container>
    )
  }

  const alertMetrics = summary.alert_metrics || {}
  const treatmentMetrics = summary.treatment_metrics || {}
  const effectiveCount = toSafeCount(treatmentMetrics.effective)
  const improvingCount = toSafeCount(treatmentMetrics.improving)
  const ineffectiveCount = toSafeCount(treatmentMetrics.ineffective)
  const totalTreatmentsRaw = toSafeCount(treatmentMetrics.total)
  const totalTreatments = totalTreatmentsRaw || (effectiveCount + improvingCount + ineffectiveCount)
  const hasTreatmentData = totalTreatments > 0
  const responseScore = hasTreatmentData
    ? ((effectiveCount + (improvingCount * 0.5)) / totalTreatments) * 100
    : null
  const roundedResponseScore = responseScore == null ? null : Math.round(responseScore)
  const responseLabel = roundedResponseScore == null ? "Not enough treatment data" : `${roundedResponseScore}%`
  const responseInterpretationText = roundedResponseScore == null ? null : responseInterpretation(roundedResponseScore)
  const treatmentOutcomeItems = [
    {label: "Effective", value: effectiveCount, tone: "success"},
    {label: "Improving", value: improvingCount, tone: "warning"},
    {label: "Ineffective", value: ineffectiveCount, tone: "danger"},
  ]
  const alertProfileItems = [
    {label: "Normal / stable", value: alertMetrics.normal ?? 0, tone: "success"},
    {label: "High", value: alertMetrics.high ?? 0, tone: "warning"},
    {label: "Critical", value: alertMetrics.critical ?? 0, tone: "danger"},
  ]
  const isOverviewView = selectedView === "overview"
  const isMetricsView = selectedView === "metrics"
  const isClinicalView = selectedView === "clinical"

  return (
    <Container
      className="post-discharge-summary-card"
      header={
        <Header
          variant="h2"
          description="Readmission overview generated from historical patient data."
        >
          Post-Discharge Clinical Summary
        </Header>
      }
    >
      <SpaceBetween size="m">
        <div className="post-discharge-control-row">
          <SegmentedControl
            selectedId={selectedView}
            label="Summary view"
            options={SUMMARY_VIEW_OPTIONS}
            onChange={({detail}) => setSelectedView(detail.selectedId)}
          />
        </div>

        {isOverviewView && (
          <SpaceBetween size="m">
            <div className="post-discharge-fit-grid">
              <SummaryValue label="Generated at" value={generatedAt}/>
              <SummaryValue label="Final treatment outcome" value={finalOutcome} tone={outcomeTone(summary.final_treatment_outcome)}/>
              <SummaryValue label="Most monitored issue" value={problematicVital} tone={vitalTone(summary.most_problematic_vital)}/>
            </div>

            <PlainSection title="Discharge details">
              <div className="post-discharge-fit-grid">
                <StatTile label="Discharge reason" value={dischargeReason}/>
                <StatTile label="Discharge date" value={formatDateTime(summary.discharge_date)}/>
                <StatTile label="Final treatment outcome" value={finalOutcome} tone={outcomeTone(summary.final_treatment_outcome)}/>
              </div>
            </PlainSection>
          </SpaceBetween>
        )}

        {isMetricsView && (
          <SpaceBetween size="m">
            <Section title="Treatment response">
              <SpaceBetween size="m">
                <div className="post-discharge-response-summary-grid">
                  <SummaryValue label="Response score" value={responseLabel}/>
                  <SummaryValue label="Response" value={responseInterpretationText || "Not enough treatment data"}/>
                </div>
                <TreatmentResponseMeter
                  value={roundedResponseScore || 0}
                  description={responseInterpretationText || "Not enough treatment data"}
                  additionalInfo={`${effectiveCount} effective, ${improvingCount} improving, ${ineffectiveCount} ineffective`}
                />
                <div className="post-discharge-response-outcome-grid">
                  <LegendItem label="Effective" value={effectiveCount} tone="success"/>
                  <LegendItem label="Improving" value={improvingCount} tone="warning"/>
                  <LegendItem label="Ineffective" value={ineffectiveCount} tone="danger"/>
                </div>
              </SpaceBetween>
            </Section>

            <div className="post-discharge-section-divider" role="separator"/>

            <div className="post-discharge-metric-steps-layout">
              <MetricStepsSection
                title="Treatment outcomes"
                subtitle={`${totalTreatments} recorded treatment actions`}
                items={treatmentOutcomeItems}
              />

              <div className="post-discharge-metric-steps-divider" role="separator" aria-orientation="vertical"/>

              <MetricStepsSection
                title="Alert profile"
                subtitle={`${alertMetrics.total ?? 0} alert events captured`}
                items={alertProfileItems}
              />
            </div>
          </SpaceBetween>
        )}

        {isClinicalView && (
          <PlainSection title="Clinical summary">
            <div className="post-discharge-text-stack">
              <SummaryText title="Final patient state">
                {finalPatientState}
              </SummaryText>

              <SummaryText title="Summary">
                {summary.clinical_summary || "No clinical summary available."}
              </SummaryText>

              <div className="post-discharge-inline-panel">
                <SummaryText title="Readmission notes">
                  {summary.readmission_notes || "No readmission notes available."}
                </SummaryText>
              </div>
            </div>
          </PlainSection>
        )}
      </SpaceBetween>
    </Container>
  )
}
