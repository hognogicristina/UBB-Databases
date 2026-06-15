import {useEffect, useState} from "react"
import {useLocation, useNavigate, useParams} from "react-router-dom"
import {
  Badge,
  Button,
  Container,
  ContentLayout,
  SpaceBetween,
  StatusIndicator,
} from "@cloudscape-design/components"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import PatientTreatmentAnalysisSection from "../components/PatientTreatmentAnalysisSection.jsx"
import PatientAssignmentStatus from "../components/PatientAssignmentStatus.jsx"
import {useNotifications} from "../hooks/useNotifications.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {getPatient} from "../services/patientApi.js"
import LoadingSpinner from "../components/LoadingSpinner.jsx"

export default function PatientTreatmentAnalysisPage() {
  const {id} = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const {notifyError} = useNotifications()
  const [patient, setPatient] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const patientId = Number(id)

  useEffect(() => {
    if (!Number.isFinite(patientId)) {
      return
    }

    let active = true

    const loadPatient = async () => {
      setIsLoading(true)
      try {
        const response = await getPatient(patientId)
        const patient = getResponseData(response)
        if (!active || !patient) {
          return
        }

        setPatient(patient)
      } catch (error) {
        if (active) {
          notifyError(getErrorMessage(error))
        }
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    loadPatient().then(() => {
    })

    return () => {
      active = false
    }
  }, [notifyError, patientId])

  const patientName = patient ? `${patient.last_name || ""} ${patient.first_name || ""}`.trim() || "Patient" : "Patient"
  const patientStatusText = patient?.is_discharged ? "Discharged" : "Admitted"

  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">{patientName}</h1>
              <p>Treatment Analysis</p>
              <div className="medstream-page-filter-row">
                <StatusIndicator type={patient?.is_discharged ? "stopped" : "success"}>
                  {patientStatusText}
                </StatusIndicator>
                <PatientAssignmentStatus patientId={patientId}/>
                <span className="medstream-department-badge">
                  <Badge color="blue">{patient?.department || "--"}</Badge>
                </span>
              </div>
            </div>
            <Button onClick={() => navigate(`/patients/${id}/post-discharge-summary${location.search || ""}`)}>
              Post-discharge summary
            </Button>
          </div>
        </div>

        {isLoading ? (
          <LoadingSpinner/>
        ) : (
          <PatientTreatmentAnalysisSection
            selectedPatientId={patientId}
            showSelectedPatientSummary={false}
          />
        )}
      </SpaceBetween>
    </ContentLayout>
  )
}
