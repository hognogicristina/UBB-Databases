import {useEffect, useState} from "react"
import {
  Box,
  Button,
  ColumnLayout,
  Container,
  ContentLayout,
  Header,
  Select,
  SpaceBetween,
} from "@cloudscape-design/components"
import {useNotifications} from "../hooks/useNotifications.js"
import {useAuth} from "../hooks/useAuth.js"
import {useNavigate} from "react-router-dom"
import {createPatient} from "../services/patientApi.js"
import {assignPatientToDoctor, getCurrentDoctor} from "../services/doctorApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {buildPatientPhoneNumber, ROMANIA_PHONE_PLACEHOLDER} from "../utils/patientPhone.js"
import {getCityOptions, getCountyOptions} from "../utils/addressOptions.js"
import {buildEmptyPatientAddress, normalizePatientAddress} from "../utils/patientAddress.js"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import AwsDatePicker from "../components/AwsDatePicker.jsx"
import InfoHelp from "../components/InfoHelp.jsx"
import {getTodayIsoDate, isIsoDateInRange} from "../utils/date.js"
import {INPUT_LIMITS, limitDigits, limitText} from "../utils/inputLimits.js"

const TOTAL_STEPS = 2
const GENDER_OPTIONS = [
  {label: "Male", value: "male"},
  {label: "Female", value: "female"},
  {label: "Other", value: "other"},
]
const PREGNANT_OPTIONS = [
  {label: "No", value: "false"},
  {label: "Yes", value: "true"},
]
const ARRIVAL_METHOD_OPTIONS = [
  {label: "Self", value: "self"},
  {label: "Ambulance", value: "ambulance"},
]

function getSelectedOption(options, value) {
  return options.find((option) => option.value === value) || null
}

export default function AddPatientPage() {
  const navigate = useNavigate()
  const {notifyError} = useNotifications()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    cnp: "",
    birth_date: "",
    gender: "",
    arrival_method: "self",
    is_pregnant: false,
  })
  const [address, setAddress] = useState(buildEmptyPatientAddress())
  const [phoneNumber, setPhoneNumber] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const {token} = useAuth()
  const [currentDoctor, setCurrentDoctor] = useState(null)
  const maxBirthDate = getTodayIsoDate()


  const normalizedPhoneNumber = buildPatientPhoneNumber(phoneNumber)
  const isStepOneValid = Boolean(
    form.first_name.trim()
    && form.last_name.trim()
    && form.cnp.trim()
    && isIsoDateInRange(form.birth_date, {max: maxBirthDate})
    && form.gender.trim()
    && normalizedPhoneNumber.trim(),
  )
  const isStepTwoValid = Boolean(
    address.street.trim()
    && address.number.trim()
    && address.city.trim()
    && address.county.trim()
    && address.postal_code.trim(),
  )

  const handleChange = (event) => {
    const {name, value} = event.target
    setForm((prev) => {
      const fieldLimits = {
        first_name: INPUT_LIMITS.firstName,
        last_name: INPUT_LIMITS.lastName,
        cnp: INPUT_LIMITS.cnp,
      }
      const nextValue = fieldLimits[name] ? limitText(value, fieldLimits[name]) : value
      const updates = {[name]: name === "is_pregnant" ? value === "true" : nextValue}
      if (name === "gender" && value !== "female") {
        updates.is_pregnant = false
      }
      return {...prev, ...updates}
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

  const countyOptions = getCountyOptions()
  const cityOptions = getCityOptions(address.county)
  const countySelectOptions = countyOptions.map((county) => ({label: county.name, value: county.name}))
  const citySelectOptions = cityOptions.map((city) => ({label: city, value: city}))

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (step < TOTAL_STEPS) {
      if (isStepOneValid && !isSubmitting) setStep(2)
      return
    }

    if (!isStepOneValid || !isStepTwoValid || isSubmitting) {
      return
    }

    setIsSubmitting(true)

    try {
      const response = await createPatient({
        ...form,
        department: currentDoctor?.specialization || "ER",
        phone_number: normalizedPhoneNumber,
        address: normalizePatientAddress(address),
      }, token ? {Authorization: `Bearer ${token}`} : {})
      const patientData = getResponseData(response)

      if (currentDoctor?.id) {
        try {
          await assignPatientToDoctor(currentDoctor.id, patientData.id, token ? {Authorization: `Bearer ${token}`} : {})
        } catch (assignError) {
          console.error("Failed to assign patient to doctor", assignError)
        }
      }

      navigate(`/patient/${patientData.id}`)
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    const fetchMe = async () => {
      if (!token) return
      try {
        const res = await getCurrentDoctor({Authorization: `Bearer ${token}`})
        setCurrentDoctor(getResponseData(res))
      } catch (error) {
        console.error("Failed to load current doctor", error)
      }
    }
    fetchMe()
  }, [token])

  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">Add Patient</h1>
              <p>Create a patient admission record for the current department.</p>
            </div>
          </div>
        </div>

        <Container>
          <ColumnLayout columns={3} variant="text-grid">
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Workflow</Box>
              <Box variant="h2">Patient intake</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Department</Box>
              <Box variant="h2">{currentDoctor?.specialization || "ER"}</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Step</Box>
              <Box variant="h2">{step} / {TOTAL_STEPS}</Box>
            </SpaceBetween>
          </ColumnLayout>
        </Container>

        <Container
          header={
            <Header
              variant="h2"
              description={step === 1 ? "Enter identity, contact, and arrival details." : "Enter the patient's address details."}
            >
              Create patient record
            </Header>
          }
        >
          <form className="medstream-form" onSubmit={handleSubmit}>
            {step === 1 && (
              <SpaceBetween size="m">
                <Header variant="h3">Basic info</Header>
                <div className="medstream-form-grid">
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-first-name">{"First Name"}</label>
                    <input id="patient-first-name" type="text" name="first_name" value={form.first_name} onChange={handleChange}
                           placeholder={"Andrei"} className="login-input" maxLength={100} required/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-last-name">{"Last Name"}</label>
                    <input id="patient-last-name" type="text" name="last_name" value={form.last_name} onChange={handleChange}
                           placeholder={"Popescu"} className="login-input" maxLength={100} required/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-gender">{"Gender"}</label>
                    <Select
                      selectedOption={getSelectedOption(GENDER_OPTIONS, form.gender)}
                      onChange={({detail}) => handleChange({target: {name: "gender", value: detail.selectedOption.value}})}
                      options={GENDER_OPTIONS}
                      placeholder="Gender"
                      selectedAriaLabel="Selected gender"
                    />
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-birth-date">{"Birth Date"}</label>
                    <AwsDatePicker
                      id="patient-birth-date"
                      name="birth_date"
                      value={form.birth_date}
                      onChange={(value) => handleChange({target: {name: "birth_date", value}})}
                      className="login-input"
                      max={maxBirthDate}
                      required
                    />
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-cnp">CNP</label>
                    <input id="patient-cnp" type="text" name="cnp" value={form.cnp} onChange={handleChange}
                           placeholder={"6010101123451"} className="login-input" maxLength={13} required/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-phone-number">{"Phone Number"}</label>
                    <input id="patient-phone-number" type="tel" value={phoneNumber}
                           onChange={(event) => setPhoneNumber(limitDigits(event.target.value, INPUT_LIMITS.phone))}
                           placeholder={ROMANIA_PHONE_PLACEHOLDER} className="login-input" maxLength={INPUT_LIMITS.phone} required/>
                  </div>
                  <div className="login-field">
                    <span className="medstream-label-with-help">
                      <label className="login-label" htmlFor="patient-pregnant">{"Pregnant"}</label>
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
                    <Select
                      selectedOption={getSelectedOption(PREGNANT_OPTIONS, String(form.is_pregnant))}
                      onChange={({detail}) => handleChange({target: {name: "is_pregnant", value: detail.selectedOption.value}})}
                      options={PREGNANT_OPTIONS}
                      selectedAriaLabel="Selected pregnancy status"
                      disabled={form.gender !== "female"}
                    />
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="patient-arrival-method">{"Arrival Method"}</label>
                    <Select
                      selectedOption={getSelectedOption(ARRIVAL_METHOD_OPTIONS, form.arrival_method)}
                      onChange={({detail}) => handleChange({target: {name: "arrival_method", value: detail.selectedOption.value}})}
                      options={ARRIVAL_METHOD_OPTIONS}
                      selectedAriaLabel="Selected arrival method"
                    />
                  </div>
                </div>
              </SpaceBetween>
            )}

            {step === 2 && (
              <SpaceBetween size="m">
                <Header variant="h3">Address</Header>
                <div className="medstream-form-grid">
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-street">{"Street"}</label>
                    <input id="add-street" type="text" name="street" value={address.street} onChange={handleAddressChange}
                           placeholder={"Liberty Street"} className="login-input" maxLength={120} required/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-number">{"Number"}</label>
                    <input id="add-number" type="text" name="number" value={address.number} onChange={handleAddressChange}
                           placeholder={"12A"} className="login-input" maxLength={30} required/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-apartment">{"Apartment"}</label>
                    <input id="add-apartment" type="text" name="apartment" value={address.apartment} onChange={handleAddressChange}
                           placeholder={"24"} className="login-input" maxLength={30}/>
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-county">{"County"}</label>
                    <Select
                      selectedOption={getSelectedOption(countySelectOptions, address.county)}
                      onChange={({detail}) => handleAddressChange({target: {name: "county", value: detail.selectedOption.value}})}
                      options={countySelectOptions}
                      placeholder="Select county"
                      selectedAriaLabel="Selected county"
                      disabled={countyOptions.length === 0}
                    />
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-city">{"City"}</label>
                    <Select
                      selectedOption={getSelectedOption(citySelectOptions, address.city)}
                      onChange={({detail}) => handleAddressChange({target: {name: "city", value: detail.selectedOption.value}})}
                      options={citySelectOptions}
                      placeholder={cityOptions.length === 0 ? "Select county first" : "Select city"}
                      selectedAriaLabel="Selected city"
                      disabled={cityOptions.length === 0}
                    />
                  </div>
                  <div className="login-field">
                    <label className="login-label" htmlFor="add-postal-code">{"Postal Code"}</label>
                    <input id="add-postal-code" type="text" name="postal_code" value={address.postal_code}
                           onChange={(event) => handleAddressChange({
                             target: {
                               name: "postal_code",
                               value: event.target.value,
                             }
                           })} placeholder="010101" className="login-input" maxLength={INPUT_LIMITS.postalCode} required/>
                  </div>
                  <div className="login-field medstream-form-field-wide">
                    <label className="login-label" htmlFor="add-country">{"Country"}</label>
                    <input id="add-country" type="text" value={"Romania"} className="login-input" maxLength={INPUT_LIMITS.country} disabled/>
                  </div>
                </div>
              </SpaceBetween>
            )}

            <div className="medstream-form-actions">
              <SpaceBetween direction="horizontal" size="xs">
                {step > 1 ? (
                  <Button formAction="none" onClick={() => setStep(1)} disabled={isSubmitting}>Previous</Button>
                ) : (
                  <Button formAction="none" className="medstream-cancel-button" onClick={() => navigate("/dashboard")}>Cancel</Button>
                )}

                {step < TOTAL_STEPS ? (
                  <Button formAction="none" variant="primary" className="medstream-submit-button" onClick={() => setStep(2)} disabled={!isStepOneValid || isSubmitting}>Next</Button>
                ) : (
                  <Button formAction="submit" variant="primary" className="medstream-submit-button" disabled={!isStepTwoValid || isSubmitting}>
                    {isSubmitting ? "Creating patient..." : "Create patient"}
                  </Button>
                )}
              </SpaceBetween>
            </div>
          </form>
        </Container>
      </SpaceBetween>
    </ContentLayout>
  )
}
