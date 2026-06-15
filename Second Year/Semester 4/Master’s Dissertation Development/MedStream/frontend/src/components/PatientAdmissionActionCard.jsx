import {Button, Container, FormField, Header, Select, SpaceBetween, Textarea} from "@cloudscape-design/components"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

function getSelectedOption(options, value) {
  return options.find((option) => option.value === value) || null
}

export default function PatientAdmissionActionCard({
                                                     patient,
                                                     canManagePatient = true,
                                                     dischargeReason,
                                                     dischargeType,
                                                     dischargeTypes = [],
                                                     readmitArrivalMethod,
                                                     onDischargeReasonChange,
                                                     onDischargeTypeChange,
                                                     onReadmitArrivalMethodChange,
                                                     onDischargeSubmit,
                                                     onReadmitSubmit,
                                                     isSubmittingDischarge,
                                                     isSubmittingReadmit,
                                                   }) {
  const canSubmitDischarge = canManagePatient && dischargeReason.trim().length > 0 && Boolean(dischargeType) && !patient?.is_discharged
  const canSubmitReadmit = canManagePatient && Boolean(readmitArrivalMethod) && Boolean(patient?.is_discharged)
  const arrivalMethodOptions = [
    {label: "Self", value: "self"},
    {label: "Ambulance", value: "ambulance"},
  ]
  const dischargeTypeOptions = dischargeTypes.map((type) => ({label: type, value: type}))

  return (
    <Container
      header={
        <Header
          variant="h2"
          description={patient?.is_discharged ? "Restore this patient to admitted status." : "Close the current admission when discharge criteria are met."}
        >
          {patient?.is_discharged ? "Readmit patient" : "Discharge patient"}
        </Header>
      }
    >
      {patient?.is_discharged ? (
        <form onSubmit={onReadmitSubmit}>
          <SpaceBetween size="m">
            <FormField label="Arrival Method" description="Admission note is generated automatically from arrival method.">
            <Select
              selectedOption={getSelectedOption(arrivalMethodOptions, readmitArrivalMethod)}
              onChange={({detail}) => onReadmitArrivalMethodChange(detail.selectedOption.value)}
              options={arrivalMethodOptions}
              selectedAriaLabel="Selected arrival method"
              disabled={!canManagePatient || isSubmittingReadmit}
            />
            </FormField>
          <Button
            formAction="submit"
            variant="primary"
            className="medstream-submit-button"
            disabled={!canSubmitReadmit || isSubmittingReadmit}
          >
            {isSubmittingReadmit ? "Submitting..." : "Readmit Patient"}
          </Button>
          </SpaceBetween>
        </form>
      ) : (
        <form onSubmit={onDischargeSubmit}>
          <SpaceBetween size="m">
            <FormField label="Type">
            <Select
              selectedOption={getSelectedOption(dischargeTypeOptions, dischargeType)}
              onChange={({detail}) => onDischargeTypeChange(detail.selectedOption.value)}
              options={dischargeTypeOptions}
              placeholder="Select type"
              selectedAriaLabel="Selected discharge type"
              disabled={!canManagePatient || isSubmittingDischarge}
            />
            </FormField>
            <FormField label="Reason for discharge">
          <Textarea
            value={dischargeReason}
            onChange={({detail}) => onDischargeReasonChange(limitText(detail.value, INPUT_LIMITS.clinicalNote))}
            placeholder="Reason for discharge"
            maxLength={INPUT_LIMITS.clinicalNote}
            disabled={!canManagePatient || isSubmittingDischarge}
          />
            </FormField>

          <Button
            formAction="submit"
            variant="primary"
            className="medstream-submit-button"
            disabled={!canSubmitDischarge || isSubmittingDischarge}
          >
            {isSubmittingDischarge ? "Submitting..." : "Discharge Patient"}
          </Button>
          </SpaceBetween>
        </form>
      )}
    </Container>
  )
}
