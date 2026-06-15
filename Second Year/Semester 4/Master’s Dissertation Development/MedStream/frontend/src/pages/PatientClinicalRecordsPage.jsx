import {useCallback, useEffect, useMemo, useState} from "react"
import {useParams} from "react-router-dom"
import {
  Alert,
  Badge,
  Box,
  Button,
  ButtonDropdown,
  ColumnLayout,
  Container,
  ContentLayout,
  FormField,
  Header,
  Input,
  Modal,
  Select,
  SpaceBetween,
  StatusIndicator,
  Table,
  Textarea,
} from "@cloudscape-design/components"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import DataTable from "../components/DataTable.jsx"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import InfoHelp from "../components/InfoHelp.jsx"
import {useNotifications} from "../hooks/useNotifications.js"
import {useAuth} from "../hooks/useAuth.js"
import {getCurrentDoctor} from "../services/doctorApi.js"
import {
  administerMedication,
  assignPatientCondition,
  createPatientAllergy,
  createPatientDiagnosis,
  getAllergyOptions,
  getConditionOptions,
  getConditionStatusOptions,
  getDiagnosisOptions,
  getDosageOptions,
  getFrequencyOptions,
  getMedicationOptions,
  getPatient,
  getPatientAllergies,
  getPatientConditions,
  getPatientDiagnosis,
  getPatientDoctors,
  getPatientMedicationOptions,
  getPatientMedications,
  updateMedication,
  updatePatientAllergy,
  updatePatientCondition,
  updatePatientDiagnosis,
} from "../services/patientApi.js"
import {getErrorMessage, getResponseData, getResponseMessage} from "../services/apiMessages.js"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"
import {formatBucharestNumericDateTime} from "../utils/time.js"

function formatDateTime(value) {
  return formatBucharestNumericDateTime(value)
}

function trimValue(value) {
  return String(value || "").trim()
}

const normalize = (value) => String(value || "").trim().toLowerCase()

function normalizeMedicationForm(form) {
  return {
    name: trimValue(form.name),
    dosage: trimValue(form.dosage),
    frequency: trimValue(form.frequency),
  }
}

function normalizeMedicationUpdateForm(form) {
  return {
    dosage: trimValue(form.dosage),
    frequency: trimValue(form.frequency),
    note: trimValue(form.note),
  }
}

function normalizeConditionUpdateForm(form) {
  return {
    status: trimValue(form.status),
    notes: trimValue(form.notes),
  }
}

function hasChanges(initialValues, currentValues, keys) {
  return keys.some((key) => initialValues[key] !== currentValues[key])
}

const INITIAL_FORMS = {
  diagnosis: {diagnosis: "", notes: "", status: ""},
  editDiagnosis: {diagnosis: "", notes: "", status: "", note: ""},
  medication: {name: "", dosage: "", frequency: ""},
  editMedication: {dosage: "", frequency: "", note: ""},
  allergy: {name: "", severity: ""},
  editAllergy: {name: "", severity: "mild"},
  editCondition: {status: "", notes: ""},
}

const FILTER_OPTIONS = [
  {label: "All records", value: "all"},
  {label: "Diagnosis", value: "diagnosis"},
  {label: "Medication", value: "medication"},
  {label: "Allergy", value: "allergy"},
  {label: "Condition", value: "condition"},
]

const DIAGNOSIS_STATUS_OPTIONS = ["active", "resolved", "chronic", "inactive"].map((status) => ({
  label: status,
  value: status,
}))

const ALLERGY_SEVERITY_OPTIONS = ["mild", "moderate", "severe"].map((severity) => ({
  label: severity,
  value: severity,
}))

const RECORD_TYPE_LABELS = {
  diagnosis: "Diagnosis",
  medication: "Medication",
  allergy: "Allergy",
  condition: "Condition",
}

function getSelectedOption(options, value) {
  if (!trimValue(value)) {
    return null
  }

  return options.find((option) => option.value === value) || null
}

function mapValueOptions(values) {
  return values
    .map((value) => trimValue(value))
    .filter(Boolean)
    .map((value) => ({label: value, value}))
}

function mapMergedValueOptions(values, ...extraValues) {
  const mergedValues = [...values, ...extraValues]
    .map((value) => trimValue(value))
    .filter(Boolean)

  return Array.from(new Set(mergedValues)).map((value) => ({label: value, value}))
}

function formatStatusLabel(value) {
  const text = trimValue(value)
  if (!text) {
    return "--"
  }
  return text
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1).toLowerCase()}`)
    .join(" ")
}

function getRecordStatusType(item) {
  const value = normalize(item.status || item.severity)

  if (item.type === "allergy") {
    if (value === "severe") {
      return "error"
    }
    if (value === "moderate") {
      return "warning"
    }
    return "success"
  }

  if (["critical", "worsening", "severe", "failed", "error"].includes(value)) {
    return "error"
  }
  if (["chronic", "moderate", "warning"].includes(value)) {
    return "warning"
  }
  if (["improving", "pending", "in-progress", "in progress"].includes(value)) {
    return "in-progress"
  }
  if (["inactive", "closed", "discharged"].includes(value)) {
    return "stopped"
  }
  if (["active", "resolved", "stable", "mild", "normal", "available"].includes(value)) {
    return "success"
  }

  return "info"
}

export default function PatientClinicalRecordsPage() {
  const {id} = useParams()
  const {notifyError, notifySuccess} = useNotifications()
  const {token} = useAuth()

  const [patient, setPatient] = useState(null)
  const [currentDoctor, setCurrentDoctor] = useState(null)
  const [diagnosis, setDiagnosis] = useState([])
  const [medications, setMedications] = useState([])
  const [allergies, setAllergies] = useState([])
  const [patientConditions, setPatientConditions] = useState([])
  const [conditionOptions, setConditionOptions] = useState([])
  const [doctors, setDoctors] = useState([])
  const [showDoctorsModal, setShowDoctorsModal] = useState(false)

  const [filter, setFilter] = useState("all")
  const [conditionSearch, setConditionSearch] = useState("")
  const [showDialog, setShowDialog] = useState(null)
  const [editItem, setEditItem] = useState(null)

  const [diagnosisForm, setDiagnosisForm] = useState(INITIAL_FORMS.diagnosis)
  const [editDiagnosisForm, setEditDiagnosisForm] = useState(INITIAL_FORMS.editDiagnosis)
  const [medicationForm, setMedicationForm] = useState(INITIAL_FORMS.medication)
  const [editMedicationForm, setEditMedicationForm] = useState(INITIAL_FORMS.editMedication)
  const [allergyForm, setAllergyForm] = useState(INITIAL_FORMS.allergy)
  const [editAllergyForm, setEditAllergyForm] = useState(INITIAL_FORMS.editAllergy)
  const [conditionId, setConditionId] = useState("")
  const [editConditionForm, setEditConditionForm] = useState(INITIAL_FORMS.editCondition)

  const [allergyOptions, setAllergyOptions] = useState([])
  const [medicationOptions, setMedicationOptions] = useState([])
  const [dosageOptions, setDosageOptions] = useState([])
  const [frequencyOptions, setFrequencyOptions] = useState([])
  const [conditionStatusOptions, setConditionStatusOptions] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const initialAllergySeverity =
    editItem && showDialog === "edit_allergy"
      ? trimValue(editItem.severity)
      : ""

  const currentAllergySeverity = trimValue(editAllergyForm.severity)

  const canSubmitAllergy =
    initialAllergySeverity !== currentAllergySeverity && Boolean(currentAllergySeverity)

  const authHeaders = token ? {Authorization: `Bearer ${token}`} : {}

  useEffect(() => {
    const loadMe = async () => {
      if (!token) return

      try {
        const res = await getCurrentDoctor({Authorization: `Bearer ${token}`})
        setCurrentDoctor(getResponseData(res))
      } catch (error) {
        console.error("Failed to load current doctor", error)
      }
    }

    loadMe()
  }, [token])

  const loadData = useCallback(async () => {
    setIsLoading(true)

    try {
      const [
        patientRes,
        diagnosisRes,
        medicationsRes,
        allergiesRes,
        patientConditionsRes,
        conditionOptionsRes,
        doctorsRes,
        allergyOptRes,
        medOptRes,
        dosageOptRes,
        frequencyOptRes,
        conditionStatusRes,
        diagnosisOptionsRes,
        medicationOptionsRes,
      ] = await Promise.all([
        getPatient(id),
        getPatientDiagnosis(id, 1, 100),
        getPatientMedications(id),
        getPatientAllergies(id, 1, 100),
        getPatientConditions(id),
        getConditionOptions(),
        getPatientDoctors(id),
        getAllergyOptions(),
        getPatientMedicationOptions(id),
        getDosageOptions(),
        getFrequencyOptions(),
        getConditionStatusOptions(),
        getDiagnosisOptions(),
        getMedicationOptions(),
      ])

      setPatient(getResponseData(patientRes))
      setDiagnosis((getResponseData(diagnosisRes) || {}).items || [])
      setMedications(getResponseData(medicationsRes) || [])
      setAllergies((getResponseData(allergiesRes) || {}).items || [])
      setPatientConditions(getResponseData(patientConditionsRes) || [])
      setConditionOptions(getResponseData(conditionOptionsRes) || [])
      setDoctors(getResponseData(doctorsRes) || [])

      setAllergyOptions(getResponseData(allergyOptRes) || [])
      setMedicationOptions(getResponseData(medOptRes) || [])
      setDosageOptions(getResponseData(dosageOptRes) || [])
      setFrequencyOptions(getResponseData(frequencyOptRes) || [])
      setConditionStatusOptions(getResponseData(conditionStatusRes) || [])
      void diagnosisOptionsRes
      void medicationOptionsRes
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }, [id, notifyError])

  useEffect(() => {
    loadData()
  }, [loadData])

  const items = useMemo(() => {
    const mapped = [
      ...diagnosis.map((item) => ({
        ...item,
        type: "diagnosis",
        label: item.diagnosis,
        timestamp: item.updated_at || item.created_at || item.diagnosed_at
      })),
      ...medications.map((item) => ({...item, type: "medication", label: item.name, timestamp: item.updated_at || item.created_at})),
      ...allergies.map((item) => ({...item, type: "allergy", label: item.allergy_name, timestamp: item.updated_at || item.created_at})),
      ...patientConditions.map((item) => ({
        ...item,
        type: "condition",
        label: item.name,
        id: item.assignment_id || item.id,
        timestamp: item.updated_at || item.diagnosed_at || item.created_at,
      })),
    ]

    const filtered = filter === "all" ? mapped : mapped.filter((item) => item.type === filter)
    return filtered.sort((left, right) => new Date(right.timestamp) - new Date(left.timestamp))
  }, [allergies, diagnosis, filter, medications, patientConditions])

  const doctorNameById = useMemo(() => {
    return Object.fromEntries(
      doctors.map((doctor) => [doctor.id, `${doctor.first_name || ""} ${doctor.last_name || ""}`.trim()]),
    )
  }, [doctors])

  const filteredConditionOptions = useMemo(() => {
    const normalizedQuery = conditionSearch.trim().toLowerCase()
    const assignedNames = new Set(patientConditions.map((item) => item.name))

    return conditionOptions.filter((item) => {
      if (assignedNames.has(item.name)) {
        return false
      }

      if (!normalizedQuery) {
        return true
      }

      return item.name.toLowerCase().includes(normalizedQuery)
    })
  }, [conditionOptions, conditionSearch, patientConditions])

  const patientName = patient ? `${patient.last_name} ${patient.first_name}` : "Patient"
  const isDoctorAssigned = Boolean(currentDoctor && doctors.some((doctor) => doctor.id === currentDoctor.id))
  const canMutateRecords = Boolean(isDoctorAssigned && !patient?.is_discharged)
  const recordCounts = {
    diagnosis: diagnosis.length,
    medication: medications.length,
    allergy: allergies.length,
    condition: patientConditions.length,
  }
  const totalRecords = items.length
  const patientStatusText = patient?.is_discharged ? "Discharged" : "Admitted"
  const actionItems = [
    {id: "view-doctors", text: "View assigned doctors"},
    {id: "add-diagnosis", text: "Add diagnosis", disabled: !canMutateRecords},
    {id: "add-medication", text: "Add medication", disabled: !canMutateRecords},
    {id: "add-allergy", text: "Add allergy", disabled: !canMutateRecords},
    {id: "add-condition", text: "Add condition", disabled: !canMutateRecords},
  ]

  const handleRecordAction = ({detail}) => {
    if (detail.id === "view-doctors") {
      setShowDoctorsModal(true)
      return
    }

    const dialogByAction = {
      "add-diagnosis": "diagnosis",
      "add-medication": "medication",
      "add-allergy": "allergy",
      "add-condition": "condition",
    }

    if (dialogByAction[detail.id]) {
      setShowDialog(dialogByAction[detail.id])
    }
  }

  const recordActions = (
    <ButtonDropdown items={actionItems} onItemClick={handleRecordAction}>
      Actions
    </ButtonDropdown>
  )

  const initialMedicationValues = editItem && showDialog === "edit_medication"
    ? normalizeMedicationUpdateForm({
      dosage: editItem.dosage,
      frequency: editItem.frequency || "",
      note: editItem.last_updated_note || "",
    })
    : normalizeMedicationForm({name: "", dosage: "", frequency: ""})
  const currentMedicationValues = showDialog === "edit_medication"
    ? normalizeMedicationUpdateForm(editMedicationForm)
    : normalizeMedicationForm(medicationForm)
  const canSubmitAddMedication = hasChanges(
    normalizeMedicationForm({name: "", dosage: "", frequency: ""}),
    normalizeMedicationForm(medicationForm),
    ["name", "dosage", "frequency"],
  ) && Boolean(
    trimValue(medicationForm.name)
    && trimValue(medicationForm.dosage)
    && trimValue(medicationForm.frequency),
  )

  const canSubmitEditMedication = hasChanges(
    initialMedicationValues,
    currentMedicationValues,
    ["dosage", "frequency"],
  ) && Boolean(
    currentMedicationValues.dosage
    && currentMedicationValues.frequency
    && currentMedicationValues.note,
  )

  const initialConditionValues = editItem && showDialog === "edit_condition"
    ? normalizeConditionUpdateForm({
      status: editItem.status,
      notes: editItem.notes || "",
    })
    : normalizeConditionUpdateForm({status: "", notes: ""})
  const currentConditionValues = normalizeConditionUpdateForm(editConditionForm)
  const canSubmitCondition = hasChanges(
    initialConditionValues,
    currentConditionValues,
    ["status"],
  ) && Boolean(currentConditionValues.notes)

  const selectedConditionName = useMemo(() => {
    if (!conditionId) {
      return ""
    }
    const selected = conditionOptions.find((condition) => String(condition.id) === String(conditionId))
    return selected?.name || ""
  }, [conditionId, conditionOptions])

  const isDuplicateMedication = useMemo(() => {
    const name = normalize(medicationForm.name)
    if (!name) {
      return false
    }
    return medications.some((item) => normalize(item.name) === name)
  }, [medicationForm.name, medications])

  const isDuplicateAllergy = useMemo(() => {
    const name = normalize(allergyForm.name)
    if (!name) {
      return false
    }
    return allergies.some((item) => normalize(item.allergy_name) === name)
  }, [allergies, allergyForm.name])

  const isDuplicateCondition = useMemo(() => {
    const name = normalize(selectedConditionName)
    if (!name) {
      return false
    }
    return patientConditions.some((item) => normalize(item.name) === name)
  }, [patientConditions, selectedConditionName])

  const medicationSelectOptions = medicationOptions.map((medication) => ({
    label: medication.name,
    value: medication.name,
    description: medication.pregnancy_category ? `Pregnancy category ${medication.pregnancy_category}` : undefined,
  }))
  const dosageSelectOptions = mapMergedValueOptions(dosageOptions, medicationForm.dosage, editMedicationForm.dosage, editItem?.dosage)
  const frequencySelectOptions = mapMergedValueOptions(frequencyOptions, medicationForm.frequency, editMedicationForm.frequency, editItem?.frequency)
  const allergySelectOptions = mapValueOptions(allergyOptions)
  const conditionSelectOptions = filteredConditionOptions.map((condition) => ({
    label: condition.name,
    value: String(condition.id),
  }))
  const conditionStatusSelectOptions = mapValueOptions(conditionStatusOptions)
  const selectedMedicationOption = getSelectedOption(medicationSelectOptions, medicationForm.name)
  const selectedMedicationDosageOption = getSelectedOption(dosageSelectOptions, medicationForm.dosage)
  const selectedMedicationFrequencyOption = getSelectedOption(frequencySelectOptions, medicationForm.frequency)
  const selectedAllergyOption = getSelectedOption(allergySelectOptions, allergyForm.name)
  const selectedAllergySeverityOption = getSelectedOption(ALLERGY_SEVERITY_OPTIONS, allergyForm.severity)
  const selectedConditionOption = getSelectedOption(conditionSelectOptions, String(conditionId))
  const selectedDiagnosisStatusOption = getSelectedOption(DIAGNOSIS_STATUS_OPTIONS, diagnosisForm.status)
  const selectedEditDiagnosisStatusOption = getSelectedOption(DIAGNOSIS_STATUS_OPTIONS, editDiagnosisForm.status)
  const selectedEditAllergySeverityOption = getSelectedOption(ALLERGY_SEVERITY_OPTIONS, editAllergyForm.severity)
  const selectedEditMedicationDosageOption = getSelectedOption(dosageSelectOptions, editMedicationForm.dosage)
  const selectedEditMedicationFrequencyOption = getSelectedOption(frequencySelectOptions, editMedicationForm.frequency)
  const selectedEditConditionStatusOption = getSelectedOption(conditionStatusSelectOptions, editConditionForm.status)
  const initialDiagnosisValues = editItem && showDialog === "edit_diagnosis"
    ? {
      notes: trimValue(editItem.notes),
      status: trimValue(editItem.status),
    }
    : {notes: "", status: ""}
  const currentDiagnosisValues = {
    notes: trimValue(editDiagnosisForm.notes),
    status: trimValue(editDiagnosisForm.status),
  }
  const isDiagnosisStatusChanged = initialDiagnosisValues.status !== currentDiagnosisValues.status
  const isDiagnosisNotesChanged = initialDiagnosisValues.notes !== currentDiagnosisValues.notes
  const canSubmitEditDiagnosis = (isDiagnosisStatusChanged || isDiagnosisNotesChanged)
    && Boolean(currentDiagnosisValues.status)
    && (!isDiagnosisStatusChanged || Boolean(trimValue(editDiagnosisForm.note)))
  const isEditDialog = Boolean(showDialog?.startsWith("edit_"))
  const dialogRecordType = showDialog
    ? showDialog.replace("edit_", "").replaceAll("_", " ")
    : ""
  const dialogTitle = showDialog
    ? `${isEditDialog ? "Update" : "Add"} ${dialogRecordType}`
    : ""
  const canSubmitDialog = Boolean(
    showDialog
    && !isSubmitting
    && canMutateRecords
    && !(showDialog === "edit_diagnosis" && !canSubmitEditDiagnosis)
    && !(showDialog === "medication" && (!canSubmitAddMedication || isDuplicateMedication))
    && !(showDialog === "edit_medication" && !canSubmitEditMedication)
    && !(showDialog === "edit_allergy" && !canSubmitAllergy)
    && !(showDialog === "edit_condition" && !canSubmitCondition)
    && !(showDialog === "condition" && (!conditionId || isDuplicateCondition))
    && !(showDialog === "diagnosis" && (!trimValue(diagnosisForm.diagnosis) || !trimValue(diagnosisForm.status)))
    && !(showDialog === "allergy" && ((!trimValue(allergyForm.name) || !trimValue(allergyForm.severity)) || isDuplicateAllergy))
  )

  const appendDoctorNote = (note) => {
    const doctorName = currentDoctor
      ? `${currentDoctor.first_name} ${currentDoctor.last_name}`
      : "Unknown"

    const suffix = `Modified by doctor: ${doctorName}`

    if (!note) return suffix
    if (note.includes(suffix)) return note

    return `${note}\n${suffix}`
  }

  const handleSubmit = async (type) => {
    if (!currentDoctor || isSubmitting) {
      return
    }
    if (type === "medication" && isDuplicateMedication) {
      return
    }
    if (type === "allergy" && isDuplicateAllergy) {
      return
    }
    if (type === "condition" && isDuplicateCondition) {
      return
    }

    setIsSubmitting(true)

    try {
      let response

      if (type === "diagnosis") {
        response = await createPatientDiagnosis(id, diagnosisForm, authHeaders)
        setDiagnosisForm({diagnosis: "", notes: "", status: ""})
      }

      if (type === "medication") {
        response = await administerMedication(id, normalizeMedicationForm(medicationForm), authHeaders)
        setMedicationForm({name: "", dosage: "", frequency: ""})
      }

      if (type === "edit_diagnosis") {
        const payload = {}

        if (trimValue(editDiagnosisForm.status) !== trimValue(editItem.status)) {
          payload.status = trimValue(editDiagnosisForm.status)
        }

        if (trimValue(editDiagnosisForm.note)) {
          payload.note = appendDoctorNote(trimValue(editDiagnosisForm.note))
        }

        if (trimValue(editDiagnosisForm.notes) !== trimValue(editItem.notes)) {
          payload.notes = trimValue(editDiagnosisForm.notes)
        }

        response = await updatePatientDiagnosis(editItem.id, payload, authHeaders)
        setEditDiagnosisForm({diagnosis: "", notes: "", status: "", note: ""})
      }

      if (type === "edit_medication") {
        const normalized = normalizeMedicationUpdateForm(editMedicationForm)
        const payload = {note: appendDoctorNote(normalized.note)}

        if (normalized.dosage !== trimValue(editItem.dosage)) {
          payload.dosage = normalized.dosage
        }

        if (normalized.frequency !== trimValue(editItem.frequency)) {
          payload.frequency = normalized.frequency
        }

        response = await updateMedication(editItem.id, payload, authHeaders)
        setEditMedicationForm({dosage: "", frequency: "", note: ""})
      }

      if (type === "allergy") {
        response = await createPatientAllergy(id, {
          allergy_name: allergyForm.name,
          severity: allergyForm.severity,
        }, authHeaders)
        setAllergyForm(INITIAL_FORMS.allergy)
      }

      if (type === "edit_allergy") {
        response = await updatePatientAllergy(editItem.id, {
          severity: trimValue(editAllergyForm.severity),
        }, authHeaders)
        setEditAllergyForm({name: "", severity: "mild"})
      }

      if (type === "condition") {
        response = await assignPatientCondition(id, {
          condition_id: Number(conditionId),
        }, authHeaders)
        setConditionId("")
        setConditionSearch("")
      }

      if (type === "edit_condition") {
        const normalized = normalizeConditionUpdateForm(editConditionForm)
        const payload = {
          notes: appendDoctorNote(normalized.notes),
        }

        if (normalized.status !== trimValue(editItem.status)) {
          payload.status = normalized.status
        }

        response = await updatePatientCondition(editItem.id, payload, authHeaders)
        setEditConditionForm({status: "", notes: ""})
      }

      notifySuccess(getResponseMessage(response))
      setShowDialog(null)
      setEditItem(null)
      loadData()
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  const openEdit = (item) => {
    if (!isDoctorAssigned) {
      return
    }

    setEditItem(item)

    if (item.type === "diagnosis") {
      setEditDiagnosisForm({
        diagnosis: item.diagnosis || "",
        notes: item.notes || "",
        status: item.status || "",
        note: "",
      })
      setShowDialog("edit_diagnosis")
    }

    if (item.type === "medication") {
      setEditMedicationForm({
        dosage: item.dosage,
        frequency: item.frequency || "",
        note: "",
      })
      setShowDialog("edit_medication")
    }

    if (item.type === "allergy") {
      setEditAllergyForm({
        name: item.allergy_name || "",
        severity: item.severity || "mild",
      })
      setShowDialog("edit_allergy")
    }

    if (item.type === "condition") {
      setEditConditionForm({
        status: item.status || "",
        notes: "",
      })
      setShowDialog("edit_condition")
    }
  }

  const resetAllDialogState = () => {
    setDiagnosisForm(INITIAL_FORMS.diagnosis)
    setEditDiagnosisForm(INITIAL_FORMS.editDiagnosis)
    setMedicationForm(INITIAL_FORMS.medication)
    setEditMedicationForm(INITIAL_FORMS.editMedication)
    setAllergyForm(INITIAL_FORMS.allergy)
    setEditAllergyForm(INITIAL_FORMS.editAllergy)
    setConditionId("")
    setConditionSearch("")
    setEditConditionForm(INITIAL_FORMS.editCondition)
  }

  const handleCancelDialog = () => {
    resetAllDialogState()
    setShowDialog(null)
    setEditItem(null)
  }

  const getRecordStatusMeta = (item) => {
    if (item.type === "diagnosis" && item.status) {
      return {label: formatStatusLabel(item.status), type: getRecordStatusType(item)}
    }

    if (item.type === "condition" && item.status) {
      return {label: formatStatusLabel(item.status), type: getRecordStatusType(item)}
    }

    if (item.type === "allergy" && item.severity) {
      return {label: formatStatusLabel(item.severity), type: getRecordStatusType(item)}
    }

    return null
  }

  if (isLoading) {
    return (
      <ContentLayout>
        <LoadingSpinner/>
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
              <h1 className="medstream-page-title">{patientName}</h1>
              <p>Clinical Records</p>
              <div className="medstream-page-filter-row">
                <StatusIndicator type={patient?.is_discharged ? "stopped" : "success"}>
                  {patientStatusText}
                </StatusIndicator>
                <StatusIndicator type={isDoctorAssigned ? "success" : "pending"}>
                  {isDoctorAssigned ? "Assigned" : "Unassigned"}
                </StatusIndicator>
                <span className="medstream-department-badge">
                  <Badge color="blue">{patient?.department || "--"}</Badge>
                </span>
              </div>
            </div>
          </div>
        </div>

        <Container>
          <ColumnLayout columns={4} variant="text-grid">
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Diagnosis</Box>
              <Box variant="h2">{recordCounts.diagnosis}</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Medication</Box>
              <Box variant="h2">{recordCounts.medication}</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Allergy</Box>
              <Box variant="h2">{recordCounts.allergy}</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Condition</Box>
              <Box variant="h2">{recordCounts.condition}</Box>
            </SpaceBetween>
          </ColumnLayout>
        </Container>

        {patient?.is_discharged || (currentDoctor && !isDoctorAssigned) ? (
          <Alert type={patient?.is_discharged ? "info" : "warning"}>
            {patient?.is_discharged
              ? "This patient is discharged, so clinical records are read-only."
              : "This patient is not assigned to you. Clinical records are read-only until assignment."}
          </Alert>
        ) : null}

        <Container
          header={
            <Header
              variant="h2"
              description="Review diagnosis, medication, allergy, and condition records."
              actions={recordActions}
            >
              <span className="medstream-transfer-title">
                <span>Clinical records</span>
                {(patient?.is_discharged || (currentDoctor && !isDoctorAssigned)) ? (
                  <InfoHelp
                    ariaLabel="clinical records help"
                    title="Clinical records actions"
                    body={[
                      "Clinical records are read-only for discharged patients.",
                      "If the patient is not assigned to you, you can review records, but only assigned doctors can add or edit diagnosis, medication, allergy, or condition records.",
                    ]}
                    footer="Assignment and discharge status keep clinical changes tied to the responsible care team."
                  />
                ) : null}
              </span>
            </Header>
          }
        >
          <SpaceBetween size="m">
            <div className="medstream-controls-grid medstream-clinical-controls-grid">
              <SpaceBetween size="xxs">
                <Box color="text-body-secondary" variant="awsui-key-label">Record type</Box>
                <Select
                  selectedOption={getSelectedOption(FILTER_OPTIONS, filter)}
                  onChange={({detail}) => setFilter(detail.selectedOption.value)}
                  options={FILTER_OPTIONS}
                  ariaLabel="Filter clinical records"
                />
              </SpaceBetween>
              <SpaceBetween size="xxs">
                <Box color="text-body-secondary" variant="awsui-key-label">Visible records</Box>
                <Box variant="h2">{totalRecords}</Box>
              </SpaceBetween>
            </div>

            <DataTable
              items={items}
              loading={isLoading}
              pageSize={8}
              emptyMessage="No records match the current filter."
              controlsLayoutClassName="medstream-hidden"
              shellClassName="medstream-clinical-record-shell"
              bodyClassName="medstream-clinical-record-list"
              getItemKey={(item) => `${item.type}-${item.id}`}
              renderRow={(item) => {
                const involvedDoctorStr = item.doctor_id
                  ? doctorNameById[item.doctor_id] || "--"
                  : "--"
                const itemDoctorName = trimValue(item.modified_by) || (
                  item.doctor_id ? doctorNameById[item.doctor_id] || "" : ""
                )
                const statusMeta = getRecordStatusMeta(item)
                const medicationDoseFrequency = item.type === "medication"
                  ? [trimValue(item.dosage), trimValue(item.frequency)].filter(Boolean).join(" • ")
                  : ""

                return (
                  <div className={`medstream-clinical-record-row ${item.type === "medication" ? "medstream-clinical-record-row-medication" : ""}`}>
                    <div className="medstream-clinical-record-main">
                      <p className="medstream-clinical-record-type">{RECORD_TYPE_LABELS[item.type] || item.type}</p>
                      <div className="medstream-clinical-record-title-row">
                        <h3>{item.label}</h3>
                        {statusMeta && (
                          <StatusIndicator type={statusMeta.type}>{statusMeta.label}</StatusIndicator>
                        )}
                        {!statusMeta && medicationDoseFrequency && (
                          <span className="medstream-clinical-record-medication-meta">{medicationDoseFrequency}</span>
                        )}
                      </div>
                      {item.type === "diagnosis" && item.notes && (
                        <p className="medstream-clinical-record-description">{item.notes}</p>
                      )}
                      {(
                        (item.type === "diagnosis" && item.status_note)
                        || (item.type === "medication" && item.last_updated_note)
                        || (item.type === "condition" && item.notes)
                        || ((item.type === "diagnosis" || item.type === "condition") && itemDoctorName)
                      ) && (() => {
                        const raw =
                          item.type === "diagnosis"
                            ? item.status_note
                            : item.type === "medication"
                              ? item.last_updated_note
                              : item.notes
                        const normalizedRaw = typeof raw === "string" ? raw : ""
                        const splitIndex = normalizedRaw.indexOf("Modified by doctor:")

                        const mainText = splitIndex !== -1 ? normalizedRaw.slice(0, splitIndex).trim() : normalizedRaw
                        const doctorText = splitIndex !== -1
                          ? normalizedRaw.slice(splitIndex).trim()
                          : itemDoctorName
                            ? `Modified by doctor: ${itemDoctorName}`
                            : null

                        return (
                          <div className="medstream-clinical-record-note">
                            {mainText && <p>{mainText}</p>}
                            {doctorText && <p>{doctorText}</p>}
                          </div>
                        )
                      })()}
                    </div>

                    <div className="medstream-clinical-record-side">
                      <div className="medstream-clinical-record-meta">
                        <p className="medstream-clinical-record-meta-line">
                          <span>Doctor:</span> {involvedDoctorStr}
                        </p>
                        <p className="medstream-clinical-record-meta-line">
                          <span>Last update:</span> {formatDateTime(item.timestamp)}
                        </p>
                      </div>

                      {["diagnosis", "medication", "allergy", "condition"].includes(item.type) && (
                        <Button
                          onClick={() => openEdit(item)}
                          disabled={!isDoctorAssigned || Boolean(patient?.is_discharged)}
                        >
                          Edit
                        </Button>
                      )}
                    </div>
                  </div>
                )
              }}
            />
          </SpaceBetween>
        </Container>

        {showDialog && (
          <Modal
            visible={Boolean(showDialog)}
            onDismiss={isSubmitting ? undefined : handleCancelDialog}
            size="medium"
            header={
              <Header
                variant="h2"
                description={isEditDialog ? "Update the selected clinical record." : "Create a new clinical record for this patient."}
              >
                {dialogTitle}
              </Header>
            }
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button className="medstream-cancel-button" onClick={handleCancelDialog} disabled={isSubmitting}>
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    className="medstream-submit-button"
                    onClick={() => {
                      if (canSubmitDialog) {
                        handleSubmit(showDialog)
                      }
                    }}
                    disabled={!canSubmitDialog}
                  >
                    {isSubmitting ? "Saving..." : isEditDialog ? "Save Changes" : "Add Record"}
                  </Button>
                </SpaceBetween>
              </Box>
            }
          >
            <SpaceBetween size="m">
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="xxs">
                  <Box color="text-body-secondary" variant="awsui-key-label">Patient</Box>
                  <Box variant="h3">{patientName}</Box>
                </SpaceBetween>
                <SpaceBetween size="xxs">
                  <Box color="text-body-secondary" variant="awsui-key-label">Record Type</Box>
                  <Box variant="h3" textTransform="capitalize">{dialogRecordType}</Box>
                </SpaceBetween>
              </ColumnLayout>

              <div className="medstream-form-grid">
                {showDialog === "diagnosis" && (
                  <>
                    <FormField label="Diagnosis">
                      <Input
                        value={diagnosisForm.diagnosis}
                        onChange={({detail}) => setDiagnosisForm({...diagnosisForm, diagnosis: limitText(detail.value, INPUT_LIMITS.diagnosis)})}
                        placeholder="Enter diagnosis"
                        maxLength={INPUT_LIMITS.diagnosis}
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <FormField label="Status">
                      <Select
                        selectedOption={selectedDiagnosisStatusOption}
                        onChange={({detail}) => setDiagnosisForm({...diagnosisForm, status: detail.selectedOption.value})}
                        options={DIAGNOSIS_STATUS_OPTIONS}
                        placeholder="Select status"
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <div className="medstream-form-field-wide">
                      <FormField label="Notes" stretch>
                        <Textarea
                          value={diagnosisForm.notes}
                          onChange={({detail}) => setDiagnosisForm({...diagnosisForm, notes: limitText(detail.value, INPUT_LIMITS.clinicalNote)})}
                          placeholder="Optional clinical notes"
                          maxLength={INPUT_LIMITS.clinicalNote}
                          rows={3}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                  </>
                )}

                {showDialog === "medication" && (
                  <>
                    <div className="medstream-form-field-wide">
                      <FormField
                        label="Medication"
                        errorText={isDuplicateMedication ? "This medication already exists for this patient." : undefined}
                        stretch
                      >
                        <Select
                          selectedOption={selectedMedicationOption}
                          onChange={({detail}) => setMedicationForm({...medicationForm, name: detail.selectedOption.value})}
                          options={medicationSelectOptions}
                          placeholder="Select medication"
                          statusType={isDuplicateMedication ? "error" : "finished"}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                    <FormField label="Dosage">
                      <Select
                        selectedOption={selectedMedicationDosageOption}
                        onChange={({detail}) => setMedicationForm({...medicationForm, dosage: detail.selectedOption.value})}
                        options={dosageSelectOptions}
                        placeholder="Select dosage"
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <FormField label="Frequency">
                      <Select
                        selectedOption={selectedMedicationFrequencyOption}
                        onChange={({detail}) => setMedicationForm({...medicationForm, frequency: detail.selectedOption.value})}
                        options={frequencySelectOptions}
                        placeholder="Select frequency"
                        disabled={isSubmitting}
                      />
                    </FormField>
                  </>
                )}

                {showDialog === "allergy" && (
                  <>
                    <FormField
                      label="Allergy"
                      errorText={isDuplicateAllergy ? "This allergy already exists for this patient." : undefined}
                    >
                      <Select
                        selectedOption={selectedAllergyOption}
                        onChange={({detail}) => setAllergyForm({...allergyForm, name: detail.selectedOption.value})}
                        options={allergySelectOptions}
                        placeholder="Select allergy"
                        statusType={isDuplicateAllergy ? "error" : "finished"}
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <FormField label="Severity">
                      <Select
                        selectedOption={selectedAllergySeverityOption}
                        onChange={({detail}) => setAllergyForm({...allergyForm, severity: detail.selectedOption.value})}
                        options={ALLERGY_SEVERITY_OPTIONS}
                        placeholder="Select severity"
                        disabled={isSubmitting}
                      />
                    </FormField>
                  </>
                )}

                {showDialog === "condition" && (
                  <>
                    <FormField label="Search condition">
                      <Input
                        value={conditionSearch}
                        onChange={({detail}) => setConditionSearch(limitText(detail.value, INPUT_LIMITS.search))}
                        placeholder="Search by condition name"
                        maxLength={INPUT_LIMITS.search}
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <FormField
                      label="Condition"
                      errorText={isDuplicateCondition ? "This condition already exists for this patient." : undefined}
                    >
                      <Select
                        selectedOption={selectedConditionOption}
                        onChange={({detail}) => setConditionId(detail.selectedOption.value)}
                        options={conditionSelectOptions}
                        placeholder="Select condition"
                        statusType={isDuplicateCondition ? "error" : "finished"}
                        disabled={isSubmitting}
                      />
                    </FormField>
                  </>
                )}

                {showDialog === "edit_diagnosis" && (
                  <>
                    <div className="medstream-form-field-wide">
                      <FormField label="Notes" stretch>
                        <Textarea
                          value={editDiagnosisForm.notes}
                          onChange={({detail}) => setEditDiagnosisForm({...editDiagnosisForm, notes: limitText(detail.value, INPUT_LIMITS.clinicalNote)})}
                          placeholder="Clinical notes"
                          maxLength={INPUT_LIMITS.clinicalNote}
                          rows={3}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                    <div className="medstream-form-field-wide">
                      <FormField label="Status" stretch>
                        <Select
                          selectedOption={selectedEditDiagnosisStatusOption}
                          onChange={({detail}) => setEditDiagnosisForm({...editDiagnosisForm, status: detail.selectedOption.value})}
                          options={DIAGNOSIS_STATUS_OPTIONS}
                          placeholder="Keep current status"
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                    <div className="medstream-form-field-wide">
                      <FormField
                        label="Status Note"
                        description={isDiagnosisStatusChanged ? "Required when the status changes." : undefined}
                        stretch
                      >
                        <Textarea
                          value={editDiagnosisForm.note}
                          onChange={({detail}) => setEditDiagnosisForm({...editDiagnosisForm, note: limitText(detail.value, INPUT_LIMITS.clinicalNote)})}
                          placeholder="Document the reason for the status update."
                          maxLength={INPUT_LIMITS.clinicalNote}
                          rows={3}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                  </>
                )}

                {showDialog === "edit_allergy" && (
                  <div className="medstream-form-field-wide">
                    <FormField label="Severity" stretch>
                      <Select
                        selectedOption={selectedEditAllergySeverityOption}
                        onChange={({detail}) => setEditAllergyForm({...editAllergyForm, severity: detail.selectedOption.value})}
                        options={ALLERGY_SEVERITY_OPTIONS}
                        placeholder="Select severity"
                        disabled={isSubmitting}
                      />
                    </FormField>
                  </div>
                )}

                {showDialog === "edit_medication" && (
                  <>
                    <FormField label="Dosage">
                      <Select
                        selectedOption={selectedEditMedicationDosageOption}
                        onChange={({detail}) => setEditMedicationForm({...editMedicationForm, dosage: detail.selectedOption.value})}
                        options={dosageSelectOptions}
                        placeholder="Select dosage"
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <FormField label="Frequency">
                      <Select
                        selectedOption={selectedEditMedicationFrequencyOption}
                        onChange={({detail}) => setEditMedicationForm({...editMedicationForm, frequency: detail.selectedOption.value})}
                        options={frequencySelectOptions}
                        placeholder="Select frequency"
                        disabled={isSubmitting}
                      />
                    </FormField>
                    <div className="medstream-form-field-wide">
                      <FormField label="Reason / Notes" stretch>
                        <Textarea
                          value={editMedicationForm.note}
                          onChange={({detail}) => setEditMedicationForm({...editMedicationForm, note: limitText(detail.value, INPUT_LIMITS.clinicalNote)})}
                          placeholder="Document the reason for this medication update."
                          maxLength={INPUT_LIMITS.clinicalNote}
                          rows={3}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                  </>
                )}

                {showDialog === "edit_condition" && (
                  <>
                    <div className="medstream-form-field-wide">
                      <FormField label="Status" stretch>
                        <Select
                          selectedOption={selectedEditConditionStatusOption}
                          onChange={({detail}) => setEditConditionForm({...editConditionForm, status: detail.selectedOption.value})}
                          options={conditionStatusSelectOptions}
                          placeholder="Select status"
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                    <div className="medstream-form-field-wide">
                      <FormField label="Reason / Notes" stretch>
                        <Textarea
                          value={editConditionForm.notes}
                          onChange={({detail}) => setEditConditionForm({...editConditionForm, notes: limitText(detail.value, INPUT_LIMITS.clinicalNote)})}
                          placeholder="Document the reason for this condition update."
                          maxLength={INPUT_LIMITS.clinicalNote}
                          rows={3}
                          disabled={isSubmitting}
                        />
                      </FormField>
                    </div>
                  </>
                )}
              </div>
            </SpaceBetween>
          </Modal>
        )}

        <Modal
          visible={showDoctorsModal}
          onDismiss={() => setShowDoctorsModal(false)}
          size="medium"
          header={
            <Header
              variant="h2"
              description="Doctors currently assigned to this patient."
            >
              Assigned Doctors
            </Header>
          }
          footer={
            <Box float="right">
              <Button onClick={() => setShowDoctorsModal(false)}>
                Close
              </Button>
            </Box>
          }
        >
          {isLoading ? (
            <LoadingSpinner text="Loading assigned doctors..."/>
          ) : (
            <div className="medstream-assigned-doctors-table">
              <Table
                variant="borderless"
                items={doctors}
                trackBy="id"
                empty={<Box color="text-body-secondary">No doctors are assigned.</Box>}
                columnDefinitions={[
                  {
                    id: "doctor",
                    header: "Doctor",
                    cell: (doctor) => `Dr. ${doctor.first_name} ${doctor.last_name}`,
                  },
                  {
                    id: "specialization",
                    header: "Specialization",
                    cell: (doctor) => doctor.specialization || "--",
                  },
                  {
                    id: "email",
                    header: "Email",
                    cell: (doctor) => doctor.email || "--",
                  },
                ]}
              />
            </div>
          )}
        </Modal>
      </SpaceBetween>
    </ContentLayout>
  )
}
