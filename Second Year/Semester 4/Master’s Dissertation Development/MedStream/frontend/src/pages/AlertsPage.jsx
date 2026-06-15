import {useEffect, useMemo, useRef, useState} from "react"
import {useNavigate, useSearchParams} from "react-router-dom"
import {
  Alert,
  Box,
  Button,
  ColumnLayout,
  Container,
  ContentLayout,
  Header,
  Pagination,
  Select,
  SpaceBetween,
  StatusIndicator,
  Table,
  TextFilter,
} from "@cloudscape-design/components"
import CountValue from "../components/CountValue.jsx"
import {useNotifications} from "../hooks/useNotifications.js"
import {getAlerts, getPatientAlerts, listPatients} from "../services/patientApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {createWebSocket} from "../services/ws.js"
import {formatPatientFullName} from "../utils/patients.js"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import {formatBucharestNumericDateTime} from "../utils/time.js"

const ALL_ALERTS_TITLE = "Alert System"
const PATIENT_TITLE_FALLBACK = "Alert System - Patient"
const DEFAULT_PAGE_SIZE = 10

const SEVERITY_OPTIONS = [
  {value: "all", label: "All severities"},
  {value: "critical", label: "Critical"},
  {value: "high", label: "High"},
  {value: "normal", label: "Normal"},
]

const SORT_OPTIONS = [
  {value: "newest", label: "Newest first"},
  {value: "oldest", label: "Oldest first"},
]

const PAGE_SIZE_OPTIONS = [5, 10, 15, 25].map((value) => ({value: String(value), label: String(value)}))

function normalizeTimestamp(value) {
  const timestamp = new Date(value).getTime()
  return Number.isFinite(timestamp) ? timestamp : 0
}

function compareNewestFirst(left, right) {
  const rightTime = normalizeTimestamp(right?.created_at)
  const leftTime = normalizeTimestamp(left?.created_at)
  if (rightTime !== leftTime) {
    return rightTime - leftTime
  }

  return Number(right?.id || 0) - Number(left?.id || 0)
}

function compareOldestFirst(left, right) {
  const leftTime = normalizeTimestamp(left?.created_at)
  const rightTime = normalizeTimestamp(right?.created_at)
  if (leftTime !== rightTime) {
    return leftTime - rightTime
  }

  return Number(left?.id || 0) - Number(right?.id || 0)
}

function buildPatientTitle(patient) {
  if (!patient) {
    return PATIENT_TITLE_FALLBACK
  }

  const fullName = formatPatientFullName(patient)
  if (!fullName || fullName.toLowerCase() === "unknown") {
    return PATIENT_TITLE_FALLBACK
  }

  return `Alert System - Patient: ${fullName}`
}

function formatDateTimeWithSeconds(value) {
  return formatBucharestNumericDateTime(value)
}

function getSeverityIndicator(severity) {
  if (severity === "critical") {
    return <StatusIndicator type="error">Critical</StatusIndicator>
  }
  if (severity === "high") {
    return <StatusIndicator type="warning">High</StatusIndicator>
  }
  return <StatusIndicator type="success">Normal</StatusIndicator>
}

function getSelectedOption(options, value) {
  return options.find((option) => option.value === String(value)) || options[0]
}

export default function AlertsPage() {
  const navigate = useNavigate()
  const {notifyError} = useNotifications()
  const [searchParams, setSearchParams] = useSearchParams()
  const [alerts, setAlerts] = useState([])
  const [patients, setPatients] = useState([])
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(true)
  const [alertsError, setAlertsError] = useState("")
  const [flashAlertId, setFlashAlertId] = useState(null)
  const [severityFilter, setSeverityFilter] = useState("all")
  const [cnpFilter, setCnpFilter] = useState(searchParams.get("cnp") || "")
  const [sortOrder, setSortOrder] = useState("newest")
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [currentPage, setCurrentPage] = useState(1)
  const requestSerialRef = useRef(0)

  const scopedCnp = searchParams.get("cnp") || ""
  const scopedPatientIdRaw = searchParams.get("patientId")
  const scopedAlertIdRaw = searchParams.get("alertId")
  const scopedPatientId = scopedPatientIdRaw && /^\d+$/.test(scopedPatientIdRaw) ? Number(scopedPatientIdRaw) : null
  const scopedAlertId = scopedAlertIdRaw && /^\d+$/.test(scopedAlertIdRaw) ? Number(scopedAlertIdRaw) : null

  const patientById = useMemo(
    () => Object.fromEntries((Array.isArray(patients) ? patients : []).map((patient) => [patient.id, patient])),
    [patients],
  )
  const patientByCnp = useMemo(
    () => Object.fromEntries((Array.isArray(patients) ? patients : []).map((patient) => [patient.cnp, patient])),
    [patients],
  )

  const scopedPatient = scopedPatientId
    ? patientById[scopedPatientId]
    : (scopedCnp ? patientByCnp[scopedCnp] : null)

  useEffect(() => {
    setCnpFilter(scopedCnp)
  }, [scopedCnp])

  useEffect(() => {
    if (!scopedPatientId && !scopedCnp) {
      document.title = ALL_ALERTS_TITLE
      return
    }

    document.title = buildPatientTitle(scopedPatient)
  }, [scopedCnp, scopedPatient, scopedPatientId])

  useEffect(() => {
    let isMounted = true
    const requestId = requestSerialRef.current + 1
    requestSerialRef.current = requestId

    const loadAlerts = async () => {
      setIsLoadingAlerts(true)
      setAlertsError("")

      try {
        const patientsPromise = listPatients()
        const alertsPromise = scopedPatientId ? getPatientAlerts(scopedPatientId) : getAlerts(scopedCnp ? scopedCnp : undefined)

        const [alertsResponse, patientsResponse] = await Promise.all([alertsPromise, patientsPromise])
        if (!isMounted || requestSerialRef.current !== requestId) {
          return
        }

        const nextAlerts = Array.isArray(getResponseData(alertsResponse)) ? getResponseData(alertsResponse) : []
        const nextPatients = Array.isArray(getResponseData(patientsResponse)) ? getResponseData(patientsResponse) : []

        setPatients(nextPatients)
        setAlerts(nextAlerts)
      } catch (error) {
        if (!isMounted || requestSerialRef.current !== requestId) {
          return
        }

        setAlerts([])
        setAlertsError(getErrorMessage(error) || "Unable to load alerts.")
        notifyError(getErrorMessage(error))
      } finally {
        if (isMounted && requestSerialRef.current === requestId) {
          setIsLoadingAlerts(false)
        }
      }
    }

    loadAlerts().then(() => {
    })

    return () => {
      isMounted = false
    }
  }, [notifyError, scopedCnp, scopedPatientId])

  useEffect(() => {
    const socket = createWebSocket((msg) => {
      if (msg.type !== "alert") {
        return
      }

      const nextAlert = msg.data
      const patientId = Number(nextAlert?.patient_id)
      if (!Number.isInteger(patientId)) {
        return
      }

      if (scopedPatientId && patientId !== scopedPatientId) {
        return
      }

      if (!scopedPatientId && scopedCnp) {
        const matchedPatient = patientById[patientId]
        if (!matchedPatient || String(matchedPatient.cnp || "") !== scopedCnp) {
          return
        }
      }

      setAlerts((prev) => [nextAlert, ...prev.filter((alert) => alert.id !== nextAlert.id)].sort(compareNewestFirst))
    })

    return () => socket.close()
  }, [patientById, scopedCnp, scopedPatientId])

  const patientNameById = useMemo(
    () => Object.fromEntries((Array.isArray(patients) ? patients : []).map((patient) => [patient.id, formatPatientFullName(patient)])),
    [patients],
  )
  const patientCnpById = useMemo(
    () => Object.fromEntries((Array.isArray(patients) ? patients : []).map((patient) => [patient.id, patient.cnp])),
    [patients],
  )
  const validPatientIds = useMemo(() => new Set((Array.isArray(patients) ? patients : []).map((patient) => patient.id)), [patients])

  const validAlerts = useMemo(
    () => (Array.isArray(alerts) ? alerts : []).filter((alert) => Number.isInteger(alert?.patient_id) && validPatientIds.has(alert.patient_id)),
    [alerts, validPatientIds],
  )

  const visibleAlerts = useMemo(() => {
    if (scopedPatientId) {
      return validAlerts.filter((alert) => alert.patient_id === scopedPatientId)
    }
    if (scopedCnp) {
      return validAlerts.filter((alert) => patientCnpById[alert.patient_id] === scopedCnp)
    }
    return validAlerts
  }, [patientCnpById, scopedCnp, scopedPatientId, validAlerts])

  const chronologicallySortedAlerts = useMemo(() => [...visibleAlerts].sort(compareNewestFirst), [visibleAlerts])

  const severityCounts = useMemo(
    () => ({
      critical: chronologicallySortedAlerts.filter((alert) => String(alert.severity || "").toLowerCase() === "critical").length,
      high: chronologicallySortedAlerts.filter((alert) => String(alert.severity || "").toLowerCase() === "high").length,
      normal: chronologicallySortedAlerts.filter((alert) => String(alert.severity || "").toLowerCase() === "normal").length,
    }),
    [chronologicallySortedAlerts],
  )

  const filteredAlerts = useMemo(() => {
    const query = cnpFilter.trim()
    return chronologicallySortedAlerts.filter((alert) => {
      const severityMatches = severityFilter === "all" || String(alert.severity || "").toLowerCase() === severityFilter
      const cnpMatches = query === "" || String(patientCnpById[alert.patient_id] || "").includes(query)
      return severityMatches && cnpMatches
    })
  }, [chronologicallySortedAlerts, cnpFilter, patientCnpById, severityFilter])

  const sortedAlerts = useMemo(() => {
    const compare = sortOrder === "oldest" ? compareOldestFirst : compareNewestFirst
    return [...filteredAlerts].sort(compare)
  }, [filteredAlerts, sortOrder])

  const pagesCount = Math.max(1, Math.ceil(sortedAlerts.length / pageSize))
  const paginatedAlerts = useMemo(
    () => sortedAlerts.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    [currentPage, pageSize, sortedAlerts],
  )

  useEffect(() => {
    setCurrentPage(1)
  }, [cnpFilter, scopedCnp, scopedPatientId, severityFilter, sortOrder, pageSize])

  useEffect(() => {
    if (currentPage > pagesCount) {
      setCurrentPage(pagesCount)
    }
  }, [currentPage, pagesCount])

  useEffect(() => {
    if (!scopedAlertId) {
      return
    }
    setFlashAlertId(scopedAlertId)
    const timeoutId = window.setTimeout(() => setFlashAlertId(null), 1800)
    return () => window.clearTimeout(timeoutId)
  }, [scopedAlertId])

  useEffect(() => {
    if (!scopedAlertId || isLoadingAlerts) {
      return
    }
    const animationFrameId = window.requestAnimationFrame(() => {
      const row = document.querySelector(`.alert-row-${scopedAlertId}`)
      if (!row) {
        return
      }
      row.scrollIntoView({behavior: "smooth", block: "center"})
    })
    return () => window.cancelAnimationFrame(animationFrameId)
  }, [paginatedAlerts, isLoadingAlerts, scopedAlertId])

  const handleCnpFilterChange = (value) => {
    setCnpFilter(value)
    const next = value.trim()
    if (next === "") {
      setSearchParams({})
      return
    }

    if (scopedCnp && next !== scopedCnp) {
      if (next.length === 13 && /^\d{13}$/.test(next)) {
        setSearchParams({cnp: next})
      } else {
        setSearchParams({})
      }
      return
    }

    if (next.length === 13 && /^\d{13}$/.test(next)) {
      setSearchParams({cnp: next})
    }
  }

  if (isLoadingAlerts) {
    return (
      <ContentLayout>
        <SpaceBetween size="m">
          <div className="medstream-page-header">
            <AppBreadcrumbs/>
            <div className="medstream-page-heading-row">
              <div>
                <h1 className="medstream-page-title">Alerts</h1>
                <p>Live alert queue with filters, sort order, and paging.</p>
              </div>
            </div>
          </div>
          <LoadingSpinner text="Loading alert queue..."/>
        </SpaceBetween>
      </ContentLayout>
    )
  }

  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">Alerts</h1>
              <p>Live alert queue with filters, sort order, and paging.</p>
            </div>
          </div>
        </div>

        <Container>
          <ColumnLayout columns={4} variant="text-grid">
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Total alerts</Box>
              <Box variant="h2"><CountValue value={visibleAlerts.length}/></Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Critical</Box>
              <Box variant="h2"><CountValue value={severityCounts.critical}/></Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">High</Box>
              <Box variant="h2"><CountValue value={severityCounts.high}/></Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Normal</Box>
              <Box variant="h2"><CountValue value={severityCounts.normal}/></Box>
            </SpaceBetween>
          </ColumnLayout>
        </Container>

        {alertsError && !isLoadingAlerts ? (
          <Alert type="error" header="Unable to load alerts">
            {alertsError}
          </Alert>
        ) : null}

        <Container
          header={
            <Header
              variant="h2"
              description="Review patient alerts using AWS-style filtering, status indicators, and table controls."
            >
              Alert queue
            </Header>
          }
        >
          <SpaceBetween size="m">
            <div className="medstream-controls-grid medstream-alert-controls-grid">
              <SpaceBetween size="xxs">
                <Box color="text-body-secondary" variant="awsui-key-label">Severity</Box>
                <Select
                  selectedOption={getSelectedOption(SEVERITY_OPTIONS, severityFilter)}
                  onChange={({detail}) => setSeverityFilter(detail.selectedOption.value)}
                  options={SEVERITY_OPTIONS}
                  ariaLabel="Filter by severity"
                />
              </SpaceBetween>
              <SpaceBetween size="xxs" className="medstream-alert-cnp-filter">
                <Box color="text-body-secondary" variant="awsui-key-label">Patient CNP</Box>
                <div className="medstream-alert-cnp-filter-control">
                  <TextFilter
                    filteringText={cnpFilter}
                    filteringPlaceholder="Filter by CNP"
                    filteringAriaLabel="Filter alerts by patient CNP"
                    disabled={Boolean(scopedPatientId)}
                    onChange={({detail}) => handleCnpFilterChange(detail.filteringText)}
                  />
                </div>
              </SpaceBetween>
              <SpaceBetween size="xxs">
                <Box color="text-body-secondary" variant="awsui-key-label">Sort order</Box>
                <Select
                  selectedOption={getSelectedOption(SORT_OPTIONS, sortOrder)}
                  onChange={({detail}) => setSortOrder(detail.selectedOption.value)}
                  options={SORT_OPTIONS}
                  ariaLabel="Sort alerts"
                />
              </SpaceBetween>
              <SpaceBetween size="xxs">
                <Box color="text-body-secondary" variant="awsui-key-label">Page size</Box>
                <Select
                  selectedOption={getSelectedOption(PAGE_SIZE_OPTIONS, pageSize)}
                  onChange={({detail}) => setPageSize(Number(detail.selectedOption.value))}
                  options={PAGE_SIZE_OPTIONS}
                  ariaLabel="Rows per page"
                />
              </SpaceBetween>
            </div>

            <div className="medstream-column-divider-table">
              <Table
                variant="borderless"
                items={paginatedAlerts}
                trackBy="id"
                empty={<Box color="text-body-secondary">No alerts match the current filters.</Box>}
                pagination={
                  <Pagination
                    currentPageIndex={currentPage}
                    pagesCount={pagesCount}
                    onChange={({detail}) => setCurrentPage(detail.currentPageIndex)}
                  />
                }
                columnDefinitions={[
                  {
                    id: "severity",
                    header: "Severity",
                    cell: (item) => (
                      <span className={`alert-row-${item.id} ${flashAlertId === item.id ? "alert-row-flash" : ""}`}>
                        {getSeverityIndicator(item.severity)}
                      </span>
                    ),
                  },
                  {
                    id: "cnp",
                    header: "CNP",
                    cell: (item) => patientCnpById[item.patient_id] || "--",
                  },
                  {
                    id: "patient",
                    header: "Patient",
                    cell: (item) => {
                      const patient = patientById[item.patient_id]
                      if (!patient) {
                        return patientNameById[item.patient_id] || "Unknown patient"
                      }
                      return formatPatientFullName(patient)
                    },
                  },
                  {
                    id: "message",
                    header: "Message",
                    cell: (item) => item.message,
                  },
                  {
                    id: "created",
                    header: "Created",
                    cell: (item) => formatDateTimeWithSeconds(item.created_at),
                  },
                  {
                    id: "action",
                    header: "Action",
                    cell: (item) => (
                      <Button
                        variant="inline-link"
                        onClick={() => navigate(`/patient/${item.patient_id}?from=alerts`)}
                      >
                        Open
                      </Button>
                    ),
                  },
                ]}
              />
            </div>
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    </ContentLayout>
  )
}
