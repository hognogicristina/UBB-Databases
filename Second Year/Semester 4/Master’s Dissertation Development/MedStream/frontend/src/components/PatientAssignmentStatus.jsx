import {useEffect, useState} from "react"
import {StatusIndicator} from "@cloudscape-design/components"
import {useAuth} from "../hooks/useAuth.js"
import {getCurrentDoctor} from "../services/doctorApi.js"
import {getPatientDoctors} from "../services/patientApi.js"
import {getResponseData} from "../services/apiMessages.js"

export default function PatientAssignmentStatus({patientId}) {
  const {token} = useAuth()
  const [isAssigned, setIsAssigned] = useState(null)

  useEffect(() => {
    let active = true

    const loadAssignmentStatus = async () => {
      setIsAssigned(null)

      if (!patientId || !token) {
        if (active) {
          setIsAssigned(false)
        }
        return
      }

      try {
        const authHeaders = {Authorization: `Bearer ${token}`}
        const [doctorResponse, doctorsResponse] = await Promise.all([
          getCurrentDoctor(authHeaders),
          getPatientDoctors(patientId),
        ])

        if (!active) {
          return
        }

        const currentDoctor = getResponseData(doctorResponse)
        const doctors = getResponseData(doctorsResponse) || []
        setIsAssigned(Boolean(currentDoctor && doctors.some((doctor) => doctor.id === currentDoctor.id)))
      } catch (error) {
        void error
        if (active) {
          setIsAssigned(false)
        }
      }
    }

    loadAssignmentStatus()

    return () => {
      active = false
    }
  }, [patientId, token])

  if (isAssigned === null) {
    return null
  }

  return (
    <StatusIndicator type={isAssigned ? "success" : "pending"}>
      {isAssigned ? "Assigned" : "Unassigned"}
    </StatusIndicator>
  )
}
