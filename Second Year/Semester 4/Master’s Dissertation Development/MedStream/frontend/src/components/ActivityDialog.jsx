import {useMemo, useState} from "react"
import {Box, Button, Header, Modal, Multiselect, Pagination, RadioGroup, Select, SpaceBetween} from "@cloudscape-design/components"
import AwsDatePicker from "./AwsDatePicker.jsx"
import AwsTimeInput from "./AwsTimeInput.jsx"
import InfoHelp from "./InfoHelp.jsx"
import {getBucharestDateParts, isValidTime} from "../utils/time.js"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

function ClearableInput({disabled = false, onChange, required = false, type = "text", value, ...props}) {
  return (
    <div className="medstream-clearable-field">
      <input
        {...props}
        className="medstream-clearable-input"
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        type={type}
        value={value}
      />
    </div>
  )
}

function ClearableTextarea({disabled = false, onChange, value, ...props}) {
  return (
    <div className="medstream-clearable-field medstream-clearable-textarea-field">
      <textarea
        {...props}
        className="medstream-clearable-input medstream-activity-description"
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </div>
  )
}

function getSelectedOption(options, value) {
  return options.find((option) => option.value === value) || null
}

function toDateParts(value) {
  if (!value) {
    return {date: "", time: ""}
  }

  const scheduled = getBucharestDateParts(value)
  if (!scheduled) {
    return {date: "", time: ""}
  }

  return {
    date: `${scheduled.year}-${scheduled.month}-${scheduled.day}`,
    time: `${scheduled.hour}:${scheduled.minute}`,
  }
}

function buildScheduledAt(date, time) {
  if (!date || !time) {
    return ""
  }

  return `${date}T${time}`
}

function normalizeSearchValue(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
}

export default function ActivityDialog({
                                         activity,
                                         activityTypes,
                                         currentDoctorId,
                                         doctors,
                                         isOpen,
                                         isSubmitting,
                                         mode = "create",
                                         onClose,
                                         onSubmit,
                                         patientSelectionMode = "multiple",
                                         patients,
                                       }) {
  const patientPageSize = 4
  const buildInitialForm = () => {
    const selectedDoctorIds = Array.from(new Set([
      currentDoctorId,
      ...(activity?.doctor_ids || []),
    ].filter((doctorId) => doctorId !== undefined && doctorId !== null)))
    const selectedPatientIds = activity?.patient_ids?.length
      ? activity.patient_ids
      : patients.filter((patient) => patient.isCurrent).map((patient) => patient.id)
    const {date, time} = toDateParts(activity?.scheduled_at)

    return {
      type: activity?.type || "",
      title: activity?.title || "",
      description: activity?.description || "",
      scheduledDate: date,
      scheduledTime: time,
      doctorIds: selectedDoctorIds,
      patientIds: selectedPatientIds.slice(0, 1),
    }
  }
  const [form, setForm] = useState(buildInitialForm)
  const [patientPage, setPatientPage] = useState(1)
  const [patientSearchQuery, setPatientSearchQuery] = useState("")
  const activityTypeOptions = activityTypes.map((activityType) => ({label: activityType, value: activityType}))

  const filteredPatients = useMemo(
    () => patients
      .filter((patient) =>
        !patient.is_discharged &&
        patient.department === doctors.find(d => d.id === currentDoctorId)?.specialization
      ),
    [patients, doctors, currentDoctorId],
  )
  const patientOptions = useMemo(
    () => filteredPatients.map((patient) => ({
      label: `${patient.last_name} ${patient.first_name}${patient.isCurrent ? " (Current patient)" : ""}`,
      value: String(patient.id),
    })),
    [filteredPatients],
  )
  const patientSearchValues = useMemo(
    () => new Map(filteredPatients.map((patient) => [
      String(patient.id),
      normalizeSearchValue(`${patient.last_name} ${patient.first_name}`),
    ])),
    [filteredPatients],
  )
  const filteredPatientOptions = useMemo(() => {
    const query = normalizeSearchValue(patientSearchQuery.trim())

    if (!query) {
      return patientOptions
    }

    return patientOptions.filter((option) => patientSearchValues.get(option.value)?.includes(query))
  }, [patientOptions, patientSearchQuery, patientSearchValues])
  const patientByValue = useMemo(
    () => new Map(filteredPatients.map((patient) => [String(patient.id), patient])),
    [filteredPatients],
  )
  const selectedPatientValue = form.patientIds.length ? String(form.patientIds[0]) : null
  const maxPatientPage = Math.max(1, Math.ceil(filteredPatientOptions.length / patientPageSize))
  const currentPatientPage = Math.min(patientPage, maxPatientPage)
  const visiblePatientOptions = filteredPatientOptions.slice((currentPatientPage - 1) * patientPageSize, currentPatientPage * patientPageSize)
  const doctorOptions = useMemo(
    () => doctors.map((doctor) => {
      const isCurrentDoctor = doctor.id === currentDoctorId

      return {
        label: `Dr. ${doctor.first_name} ${doctor.last_name}${isCurrentDoctor ? " (You)" : ""}`,
        value: String(doctor.id),
        disabled: isCurrentDoctor,
      }
    }),
    [doctors, currentDoctorId],
  )
  const doctorByValue = useMemo(
    () => new Map(doctors.map((doctor) => [String(doctor.id), doctor])),
    [doctors],
  )
  const selectedDoctorOptions = useMemo(() => {
    const selectedValues = new Set(form.doctorIds.map((doctorId) => String(doctorId)))

    if (currentDoctorId !== undefined && currentDoctorId !== null) {
      selectedValues.add(String(currentDoctorId))
    }

    return doctorOptions.filter((option) => selectedValues.has(option.value))
  }, [doctorOptions, form.doctorIds, currentDoctorId])

  if (!isOpen) {
    return null
  }

  const selectDoctors = (selectedOptions) => {
    const nextDoctorIds = selectedOptions
      .map((option) => doctorByValue.get(option.value)?.id)
      .filter((doctorId) => doctorId !== undefined && doctorId !== null)

    setForm((current) => ({
      ...current,
      doctorIds: Array.from(new Set([currentDoctorId, ...nextDoctorIds].filter((doctorId) => doctorId !== undefined && doctorId !== null))),
    }))
  }

  const selectPatient = (patientValue) => {
    const nextPatientId = patientByValue.get(patientValue)?.id

    setForm((current) => ({
      ...current,
      patientIds: nextPatientId !== undefined && nextPatientId !== null ? [nextPatientId] : [],
    }))
  }

  const isValid = form.title.trim()
    && form.type
    && form.scheduledDate
    && isValidTime(form.scheduledTime)
    && form.doctorIds.length > 0
    && form.patientIds.length > 0

  const handleSubmit = () => {
    if (!isValid || isSubmitting) {
      return
    }

    const payload = {
      type: form.type,
      title: form.title.trim(),
      description: form.description.trim(),
      scheduled_at: buildScheduledAt(form.scheduledDate, form.scheduledTime),
      doctor_ids: Array.from(new Set([currentDoctorId, ...form.doctorIds].filter((doctorId) => doctorId !== undefined && doctorId !== null))),
    }

    if (mode !== "edit") {
      payload.patient_ids = form.patientIds
    }

    onSubmit(payload)
  }

  return (
    <Modal
      visible={isOpen}
      onDismiss={isSubmitting ? undefined : onClose}
      size="large"
      header={
        <Header
          variant="h2"
          description={mode === "edit" ? "Update the schedule, details, and assigned doctors." : "Schedule a new care activity and assign the responsible team."}
        >
          {mode === "edit" ? "Edit Activity" : "Add Activity"}
        </Header>
      }
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              className="medstream-cancel-button"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="medstream-submit-button"
              onClick={handleSubmit}
              disabled={!isValid || isSubmitting}
            >
              {isSubmitting ? "Saving..." : mode === "edit" ? "Save Changes" : "Add Activity"}
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <form
        className="medstream-form medstream-activity-dialog-form"
        onSubmit={(event) => {
          event.preventDefault()
          handleSubmit()
        }}
      >
          <div className="medstream-form-grid">
            <div className="login-field">
              <label className="login-label" htmlFor="activity-type">Type</label>
              <Select
                selectedOption={getSelectedOption(activityTypeOptions, form.type)}
                onChange={({detail}) => setForm((current) => ({...current, type: detail.selectedOption.value}))}
                options={activityTypeOptions}
                placeholder="Select type"
                selectedAriaLabel="Selected activity type"
              />
            </div>

            <div className="medstream-activity-date-grid">
              <div className="login-field">
                <label className="login-label" htmlFor="activity-date">Date</label>
                <AwsDatePicker
                  id="activity-date"
                  value={form.scheduledDate}
                  onChange={(value) => setForm((current) => ({...current, scheduledDate: value}))}
                  className="medstream-clearable-input"
                  autoComplete="off"
                  required
                />
              </div>

              <div className="login-field">
                <label className="login-label" htmlFor="activity-time">Time</label>
                <AwsTimeInput
                  id="activity-time"
                  value={form.scheduledTime}
                  onChange={(value) => setForm((current) => ({...current, scheduledTime: value}))}
                  className="medstream-clearable-input"
                  required
                />
              </div>
            </div>
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="activity-title">Title</label>
            <ClearableInput
              id="activity-title"
              type="text"
              value={form.title}
              onChange={(value) => setForm((current) => ({...current, title: limitText(value, INPUT_LIMITS.activityTitle)}))}
              placeholder="Post-op monitoring review"
              maxLength={INPUT_LIMITS.activityTitle}
              required
            />
          </div>

          <div className="login-field medstream-form-field-wide">
            <label className="login-label" htmlFor="activity-description">Description</label>
            <ClearableTextarea
              id="activity-description"
              value={form.description}
              onChange={(value) => setForm((current) => ({...current, description: limitText(value, INPUT_LIMITS.activityDescription)}))}
              placeholder="Optional details"
              maxLength={INPUT_LIMITS.activityDescription}
              rows={2}
            />
          </div>

          <div className={`medstream-activity-participants ${patientSelectionMode === "hidden" || mode === "edit" ? "medstream-activity-participants-single" : ""}`}>
            {patientSelectionMode !== "hidden" && mode !== "edit" && (
              <section className="medstream-activity-participant-panel">
                <div className="medstream-activity-panel-header">
                  <p className="medstream-activity-panel-title">
                    {patientSelectionMode === "single" ? "Patient" : "Patients Involved"}
                  </p>
                  <span className="medstream-activity-panel-count">{filteredPatientOptions.length}</span>
                </div>

                <div className="medstream-activity-patient-search">
                  <ClearableInput
                    aria-label="Search patient by full name"
                    type="search"
                    value={patientSearchQuery}
                    onChange={(value) => {
                      setPatientSearchQuery(limitText(value, INPUT_LIMITS.search))
                      setPatientPage(1)
                    }}
                    placeholder="Search by full name"
                    maxLength={INPUT_LIMITS.search}
                  />
                </div>

                <div className="medstream-activity-participant-multiselect">
                  {visiblePatientOptions.length > 0 ? (
                    <RadioGroup
                      ariaLabel={patientSelectionMode === "single" ? "Patient" : "Patients involved"}
                      value={selectedPatientValue}
                      onChange={({detail}) => selectPatient(detail.value)}
                      items={visiblePatientOptions}
                    />
                  ) : (
                    <Box color="text-body-secondary">No patients match your search.</Box>
                  )}
                </div>

                {maxPatientPage > 1 && (
                  <div className="medstream-activity-participant-pagination">
                    <Pagination
                      currentPageIndex={currentPatientPage}
                      pagesCount={maxPatientPage}
                      onChange={({detail}) => setPatientPage(detail.currentPageIndex)}
                    />
                  </div>
                )}
              </section>
            )}
            <section className="medstream-activity-participant-panel">
              <div className="medstream-activity-panel-header">
                <div className="medstream-activity-panel-title-row">
                  <p className="medstream-activity-panel-title">Doctors Involved</p>
                  <InfoHelp
                    ariaLabel="Doctors involved information"
                    title="Default doctor"
                    body="The doctor creating the activity is required for ownership and audit history, so they stay selected and cannot be removed."
                  />
                </div>
                <span className="medstream-activity-panel-count">{doctors.length}</span>
              </div>
              <div className="medstream-activity-doctor-multiselect">
                <Multiselect
                  ariaLabel="Doctors involved"
                  selectedOptions={selectedDoctorOptions}
                  onChange={({detail}) => selectDoctors(detail.selectedOptions)}
                  options={doctorOptions}
                  placeholder="Choose options"
                  selectedAriaLabel="Selected doctor"
                  deselectAriaLabel={(option) => `Remove ${option.label}`}
                  empty="No doctors available"
                  enableSelectAll
                  keepOpen
                  i18nStrings={{selectAllText: "Select all"}}
                />
              </div>
            </section>
          </div>

      </form>
    </Modal>
  )
}
