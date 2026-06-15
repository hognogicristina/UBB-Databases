import {useEffect, useState} from "react"
import {
  Box,
  Button,
  ColumnLayout,
  FormField,
  Header,
  Input,
  Modal,
  Select,
  SpaceBetween,
} from "@cloudscape-design/components"
import {
  buildPatientPhoneNumber,
  normalizeRomanianPhoneNumber,
  ROMANIA_PHONE_PLACEHOLDER,
} from "../utils/patientPhone.js"
import {getCityOptions, getCountyOptions} from "../utils/addressOptions.js"
import {buildPatientAddressForm, normalizePatientAddress} from "../utils/patientAddress.js"
import AwsDatePicker from "./AwsDatePicker.jsx"
import InfoHelp from "./InfoHelp.jsx"
import {getTodayIsoDate, isIsoDateInRange} from "../utils/date.js"
import {INPUT_LIMITS, limitDigits, limitText} from "../utils/inputLimits.js"

const TOTAL_STEPS = 2

const genderOptions = [
  {value: "male", label: "Male"},
  {value: "female", label: "Female"},
  {value: "other", label: "Other"},
]

const pregnantOptions = [
  {value: "false", label: "No"},
  {value: "true", label: "Yes"},
]

function getSelectedOption(options, value) {
  return options.find((option) => option.value === value) || null
}

function buildPatientEditForm(patient) {
  return {
    first_name: patient?.first_name || "",
    last_name: patient?.last_name || "",
    gender: patient?.gender || "",
    birth_date: patient?.birth_date || "",
    is_pregnant: Boolean(patient?.is_pregnant),
  }
}

export default function EditPatientDialog({
                                            isOpen,
                                            isSubmitting,
                                            patient,
                                            onClose,
                                            onSubmit,
                                          }) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(buildPatientEditForm())
  const [address, setAddress] = useState(buildPatientAddressForm())
  const [phoneNumber, setPhoneNumber] = useState("")
  const maxBirthDate = getTodayIsoDate()

  useEffect(() => {
    if (!isOpen || !patient) {
      return
    }

    const resetTimer = window.setTimeout(() => {
      setStep(1)
      setForm(buildPatientEditForm(patient))
      setAddress(buildPatientAddressForm(patient.address))
      setPhoneNumber(normalizeRomanianPhoneNumber(patient.phone_number))
    }, 0)

    return () => window.clearTimeout(resetTimer)
  }, [isOpen, patient])

  if (!isOpen || !patient) {
    return null
  }

  const normalizedPhoneNumber = buildPatientPhoneNumber(phoneNumber)
  const normalizedCurrentValues = {
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    gender: form.gender.trim(),
    birth_date: form.birth_date,
    is_pregnant: Boolean(form.is_pregnant),
    phone_number: normalizedPhoneNumber,
    address: normalizePatientAddress(address),
  }
  const normalizedInitialValues = {
    first_name: (patient.first_name || "").trim(),
    last_name: (patient.last_name || "").trim(),
    gender: (patient.gender || "").trim(),
    birth_date: patient.birth_date || "",
    is_pregnant: Boolean(patient.is_pregnant),
    phone_number: normalizeRomanianPhoneNumber(patient.phone_number),
    address: normalizePatientAddress(patient.address),
  }

  const isDirty = Object.keys(normalizedInitialValues).some(
    (key) => JSON.stringify(normalizedInitialValues[key]) !== JSON.stringify(normalizedCurrentValues[key]),
  )
  const isStepOneValid = Boolean(
    normalizedCurrentValues.first_name
    && normalizedCurrentValues.last_name
    && normalizedCurrentValues.gender
    && isIsoDateInRange(normalizedCurrentValues.birth_date, {max: maxBirthDate})
    && normalizedCurrentValues.phone_number,
  )
  const isStepTwoValid = Boolean(
    normalizedCurrentValues.address.street
    && normalizedCurrentValues.address.number
    && normalizedCurrentValues.address.city
    && normalizedCurrentValues.address.county
    && normalizedCurrentValues.address.postal_code,
  )
  const canSubmit = isDirty && !isSubmitting

  const handleFormValueChange = (name, value) => {
    setForm((current) => {
      const fieldLimits = {
        first_name: INPUT_LIMITS.firstName,
        last_name: INPUT_LIMITS.lastName,
      }
      const nextValue = fieldLimits[name] ? limitText(value, fieldLimits[name]) : value
      const next = {...current, [name]: nextValue}

      if (name === "gender" && value !== "female") {
        next.is_pregnant = false
      }

      return next
    })
  }

  const handleAddressChange = (event) => {
    const {name, value} = event.target
    setAddress((current) => {
      if (name === "county") {
        return {...current, county: value, city: ""}
      }

      const fieldLimits = {
        street: INPUT_LIMITS.addressStreet,
        number: INPUT_LIMITS.addressNumber,
        apartment: INPUT_LIMITS.addressApartment,
      }
      const nextValue = name === "postal_code"
        ? limitDigits(value, INPUT_LIMITS.postalCode)
        : fieldLimits[name]
          ? limitText(value, fieldLimits[name])
          : value

      return {...current, [name]: nextValue}
    })
  }

  const handleNext = () => {
    if (!isStepOneValid) {
      return
    }

    setStep(2)
  }

  const countyOptions = getCountyOptions()
  const cityOptions = getCityOptions(address.county)
  const countySelectOptions = countyOptions.map((county) => ({value: county.name, label: county.name}))
  const citySelectOptions = cityOptions.map((city) => ({value: city, label: city}))

  return (
    <Modal
      visible={isOpen}
      onDismiss={isSubmitting ? undefined : onClose}
      size="large"
      header={
        <Header
          variant="h2"
          description="Update identity, contact, and address information."
        >
          Edit Patient Details
        </Header>
      }
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            {step > 1 ? (
              <Button onClick={() => setStep(1)} disabled={isSubmitting}>
                Previous
              </Button>
            ) : (
              <Button className="medstream-cancel-button" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </Button>
            )}

            {step < TOTAL_STEPS ? (
              <Button
                variant="primary"
                className="medstream-submit-button"
                onClick={handleNext}
                disabled={!isStepOneValid}
              >
                Next
              </Button>
            ) : (
              <Button
                variant="primary"
                className="medstream-submit-button"
                onClick={() => {
                  if (!canSubmit || !isStepTwoValid) return
                  onSubmit(normalizedCurrentValues)
                }}
                disabled={!canSubmit || !isStepTwoValid}
              >
                {isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            )}
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <ColumnLayout columns={2} variant="text-grid">
          <SpaceBetween size="xxs">
            <Box color="text-body-secondary" variant="awsui-key-label">Current Patient</Box>
            <Box variant="h3">{patient.last_name} {patient.first_name}</Box>
          </SpaceBetween>
          <SpaceBetween size="xxs">
            <Box color="text-body-secondary" variant="awsui-key-label">CNP</Box>
            <Box variant="h3">{patient.cnp}</Box>
          </SpaceBetween>
        </ColumnLayout>

        <SpaceBetween size="m">
          {step === 1 && (
            <SpaceBetween size="m">
              <Header variant="h3">Basic Info</Header>

              <div className="medstream-form-grid">
                <FormField label="First Name">
                  <Input
                    value={form.first_name}
                    onChange={({detail}) => handleFormValueChange("first_name", detail.value)}
                    placeholder="Andrei"
                    maxLength={100}
                  />
                </FormField>
                <FormField label="Last Name">
                  <Input
                    value={form.last_name}
                    onChange={({detail}) => handleFormValueChange("last_name", detail.value)}
                    placeholder="Popescu"
                    maxLength={100}
                  />
                </FormField>
                <FormField label="Gender">
                  <Select
                    selectedOption={getSelectedOption(genderOptions, form.gender)}
                    onChange={({detail}) => handleFormValueChange("gender", detail.selectedOption.value)}
                    options={genderOptions}
                    placeholder="Gender"
                  />
                </FormField>
                <FormField label="Birth Date">
                  <AwsDatePicker
                    value={form.birth_date}
                    onChange={(value) => handleFormValueChange("birth_date", value)}
                    className="login-input"
                    max={maxBirthDate}
                  />
                </FormField>
                <FormField label="Phone Number">
                  <Input
                    type="tel"
                    value={phoneNumber}
                    onChange={({detail}) => setPhoneNumber(limitDigits(detail.value, INPUT_LIMITS.phone))}
                    placeholder={ROMANIA_PHONE_PLACEHOLDER}
                    maxLength={INPUT_LIMITS.phone}
                  />
                </FormField>
                <FormField
                  label={
                    <span className="medstream-label-with-help">
                      <span>Pregnant</span>
                      <InfoHelp
                        ariaLabel="pregnancy status help"
                        title="Pregnancy status"
                        body={[
                          "Pregnancy status is enabled only when gender is Female.",
                          "Selecting Male or Other clears pregnancy status to No.",
                        ]}
                        footer="Choose the patient's gender first, then set pregnancy status when applicable."
                      />
                    </span>
                  }
                >
                  <Select
                    selectedOption={getSelectedOption(pregnantOptions, form.is_pregnant ? "true" : "false")}
                    onChange={({detail}) => setForm((current) => ({...current, is_pregnant: detail.selectedOption.value === "true"}))}
                    options={pregnantOptions}
                    disabled={form.gender !== "female"}
                  />
                </FormField>
              </div>
            </SpaceBetween>
          )}

          {step === 2 && (
            <SpaceBetween size="m">
              <Header variant="h3">Address</Header>
              <div className="medstream-form-grid">
                <FormField label="Street">
                  <Input
                    value={address.street}
                    onChange={({detail}) => handleAddressChange({target: {name: "street", value: detail.value}})}
                    placeholder="Liberty Street"
                    maxLength={120}
                  />
                </FormField>
                <FormField label="Number">
                  <Input
                    value={address.number}
                    onChange={({detail}) => handleAddressChange({target: {name: "number", value: detail.value}})}
                    placeholder="12A"
                    maxLength={30}
                  />
                </FormField>
                <FormField label="Apartment">
                  <Input
                    value={address.apartment}
                    onChange={({detail}) => handleAddressChange({target: {name: "apartment", value: detail.value}})}
                    placeholder="24"
                    maxLength={30}
                  />
                </FormField>
                <FormField label="County">
                  <Select
                    selectedOption={getSelectedOption(countySelectOptions, address.county)}
                    onChange={({detail}) => handleAddressChange({target: {name: "county", value: detail.selectedOption.value}})}
                    options={countySelectOptions}
                    placeholder="Select county"
                  />
                </FormField>
                <FormField label="City">
                  <Select
                    selectedOption={getSelectedOption(citySelectOptions, address.city)}
                    onChange={({detail}) => handleAddressChange({target: {name: "city", value: detail.selectedOption.value}})}
                    options={citySelectOptions}
                    placeholder={cityOptions.length === 0 ? "Select county first" : "Select city"}
                    disabled={cityOptions.length === 0}
                  />
                </FormField>
                <FormField label="Postal Code">
                  <Input
                    value={address.postal_code}
                    onChange={({detail}) => handleAddressChange({target: {name: "postal_code", value: detail.value}})}
                    placeholder="010101"
                    maxLength={INPUT_LIMITS.postalCode}
                  />
                </FormField>
                <div className="medstream-form-field-wide">
                  <FormField label="Country" stretch>
                    <Input value="Romania" maxLength={INPUT_LIMITS.country} disabled/>
                  </FormField>
                </div>
              </div>
            </SpaceBetween>
          )}
        </SpaceBetween>
      </SpaceBetween>
    </Modal>
  )
}
