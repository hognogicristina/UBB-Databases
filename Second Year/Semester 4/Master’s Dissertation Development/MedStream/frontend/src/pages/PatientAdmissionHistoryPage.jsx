import {useCallback, useEffect, useState} from "react"
import {useParams} from "react-router-dom"
import {
  Badge,
  Box,
  ColumnLayout,
  Container,
  ContentLayout,
  Header,
  Pagination,
  SpaceBetween,
  StatusIndicator,
} from "@cloudscape-design/components"

import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import PatientAdmissionActionCard from "../components/PatientAdmissionActionCard.jsx"
import PatientAssignmentStatus from "../components/PatientAssignmentStatus.jsx"
import {useNotifications} from "../hooks/useNotifications.js"
import {usePatientAdmissionActions} from "../hooks/usePatientAdmissionActions.js"
import {useAuth} from "../hooks/useAuth.js"
import {getPatient, getPatientAdmissionHistory} from "../services/patientApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {formatBucharestDateTime} from "../utils/time.js"

function formatDateTime(value) {
  return formatBucharestDateTime(value)
}

function formatAdmissionType(value) {
  const normalized = String(value || "").trim()
  if (!normalized) {
    return "--"
  }

  return normalized
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1).toLowerCase()}`)
    .join(" ")
}

export default function PatientAdmissionHistoryPage() {
  const {id} = useParams()
  const {notifyError, notifySuccess} = useNotifications()
  const {token} = useAuth()
  const pageSize = 8
  const [patient, setPatient] = useState(null)
  const [entries, setEntries] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)

  const loadPageData = useCallback(async (nextPage = page) => {
    setIsLoading(true)

    try {
      const [patientResponse, historyResponse] = await Promise.all([
        getPatient(id),
        getPatientAdmissionHistory(id, nextPage, pageSize),
      ])

      setPatient(getResponseData(patientResponse))
      const historyData = getResponseData(historyResponse) || {}
      setEntries(historyData.items || [])
      setTotal(historyData.total || 0)
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }, [id, notifyError, page])

  useEffect(() => {
    loadPageData(page)
  }, [loadPageData, page])

  const maxPage = Math.max(1, Math.ceil(total / pageSize))
  const patientName = patient ? `${patient.last_name} ${patient.first_name}`.trim() : "Patient"
  const patientStatusText = patient?.is_discharged ? "Discharged" : "Admitted"
  const lastEntry = entries[0]

  useEffect(() => {
    if (page > maxPage) {
      setPage(maxPage)
    }
  }, [maxPage, page])

  const admissionActions = usePatientAdmissionActions({
    authHeaders: token ? {Authorization: `Bearer ${token}`} : {},
    patientId: id,
    onPatientChange: setPatient,
    onHistoryRefresh: async () => {
      await loadPageData(1)
      setPage(1)
    },
    notifyError,
    notifySuccess,
  })
  const {loadDischargeTypes} = admissionActions

  useEffect(() => {
    loadDischargeTypes().then(() => {
    })
  }, [loadDischargeTypes])

  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">{patientName}</h1>
              <p>Admission History</p>
              <div className="medstream-page-filter-row">
                <StatusIndicator type={patient?.is_discharged ? "stopped" : "success"}>
                  {patientStatusText}
                </StatusIndicator>
                <PatientAssignmentStatus patientId={id}/>
                <span className="medstream-department-badge">
                  <Badge color="blue">{patient?.department || "--"}</Badge>
                </span>
              </div>
            </div>
          </div>
        </div>

        {isLoading ? (
          <LoadingSpinner/>
        ) : (
          <div className="medstream-admission-history-stack">
            <Container>
              <ColumnLayout columns={4} variant="text-grid">
                <SpaceBetween size="xs">
                  <Box color="text-body-secondary" variant="awsui-key-label">History entries</Box>
                  <Box variant="h2">{total}</Box>
                </SpaceBetween>
                <SpaceBetween size="xs">
                  <Box color="text-body-secondary" variant="awsui-key-label">Current state</Box>
                  <Box variant="h2">{patientStatusText}</Box>
                </SpaceBetween>
                <SpaceBetween size="xs">
                  <Box color="text-body-secondary" variant="awsui-key-label">Latest event</Box>
                  <Box variant="h2">{formatAdmissionType(lastEntry?.type)}</Box>
                </SpaceBetween>
                <SpaceBetween size="xs">
                  <Box color="text-body-secondary" variant="awsui-key-label">Department</Box>
                  <Box variant="h2">{patient?.department || "--"}</Box>
                </SpaceBetween>
              </ColumnLayout>
            </Container>

            <div className="medstream-dashboard-split medstream-admission-history-layout">
              <div className="medstream-stretch-container">
                <Container
                  fitHeight
                  header={
                    <Header
                      variant="h2"
                      description="Admission, discharge, and readmission activity for this patient."
                      actions={
                        <Pagination
                          currentPageIndex={page}
                          pagesCount={maxPage}
                          onChange={({detail}) => setPage(detail.currentPageIndex)}
                        />
                      }
                    >
                      Admissions and discharges
                    </Header>
                  }
                >
              <ul className="medstream-timeline-list">
                {entries.length === 0 && (
                  <li className="medstream-timeline-empty">
                    {isLoading ? "Loading admission history..." : "No admission history recorded for this patient."}
                  </li>
                )}

                {entries.map((entry) => (
                  <li key={entry.id} className="medstream-timeline-item">
                    <div className="medstream-timeline-item-row">
                      <div>
                        <Box variant="h3">{formatAdmissionType(entry.type)}</Box>
                        <Box color="text-body-secondary">{entry.note || entry.reason || "--"}</Box>
                      </div>
                      <Box color="text-body-secondary" variant="small">{formatDateTime(entry.created_at)}</Box>
                    </div>
                  </li>
                ))}
              </ul>

                </Container>
              </div>

              <div className="medstream-stretch-container">
              <PatientAdmissionActionCard
                patient={patient}
                canManagePatient={Boolean(token)}
                dischargeReason={admissionActions.dischargeReason}
                dischargeType={admissionActions.dischargeType}
                dischargeTypes={admissionActions.dischargeTypes}
                readmitArrivalMethod={admissionActions.readmitArrivalMethod}
                onDischargeReasonChange={admissionActions.setDischargeReason}
                onDischargeTypeChange={admissionActions.setDischargeType}
                onReadmitArrivalMethodChange={admissionActions.setReadmitArrivalMethod}
                onDischargeSubmit={admissionActions.handleDischargeSubmit}
                onReadmitSubmit={admissionActions.handleReadmitSubmit}
                isSubmittingDischarge={admissionActions.isSubmittingDischarge}
                isSubmittingReadmit={admissionActions.isSubmittingReadmit}
              />
              </div>
            </div>
          </div>
        )}
      </SpaceBetween>
    </ContentLayout>
  )
}
