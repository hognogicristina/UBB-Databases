import {useCallback, useState} from "react"

import {dischargePatient, getDischargeTypes, readmitPatient} from "../services/patientApi.js"
import {getErrorMessage, getResponseData, getResponseMessage} from "../services/apiMessages.js"

export function usePatientAdmissionActions({authHeaders = {}, patientId, onPatientChange, onHistoryRefresh, notifyError, notifySuccess}) {
  const [dischargeReason, setDischargeReason] = useState("")
  const [dischargeType, setDischargeType] = useState("")
  const [dischargeTypes, setDischargeTypes] = useState([])
  const [readmitArrivalMethod, setReadmitArrivalMethod] = useState("self")
  const [isSubmittingDischarge, setIsSubmittingDischarge] = useState(false)
  const [isSubmittingReadmit, setIsSubmittingReadmit] = useState(false)

  const loadDischargeTypes = useCallback(async () => {
    try {
      const response = await getDischargeTypes()
      const nextTypes = getResponseData(response) || []
      setDischargeTypes(nextTypes)
      setDischargeType((current) => current || nextTypes[0] || "")
    } catch (error) {
      notifyError(getErrorMessage(error))
    }
  }, [notifyError])

  const handleDischargeSubmit = async (event) => {
    event.preventDefault()

    if (!dischargeReason.trim() || !dischargeType || isSubmittingDischarge) {
      return
    }

    setIsSubmittingDischarge(true)

    try {
      const response = await dischargePatient(patientId, {
        type: dischargeType,
        reason: dischargeReason,
      }, authHeaders)
      onPatientChange(getResponseData(response))
      setDischargeReason("")
      setDischargeType((current) => current)
      await onHistoryRefresh?.()
      notifySuccess(getResponseMessage(response))
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsSubmittingDischarge(false)
    }
  }

  const handleReadmitSubmit = async (event) => {
    event.preventDefault()

    if (!readmitArrivalMethod || isSubmittingReadmit) {
      return
    }

    setIsSubmittingReadmit(true)

    try {
      const response = await readmitPatient(patientId, {
        arrival_method: readmitArrivalMethod,
      }, authHeaders)
      onPatientChange(getResponseData(response))
      setReadmitArrivalMethod("self")
      await onHistoryRefresh?.()
      notifySuccess(getResponseMessage(response))
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsSubmittingReadmit(false)
    }
  }

  return {
    dischargeReason,
    dischargeType,
    dischargeTypes,
    loadDischargeTypes,
    setDischargeReason,
    setDischargeType,
    readmitArrivalMethod,
    setReadmitArrivalMethod,
    isSubmittingDischarge,
    isSubmittingReadmit,
    handleDischargeSubmit,
    handleReadmitSubmit,
  }
}
