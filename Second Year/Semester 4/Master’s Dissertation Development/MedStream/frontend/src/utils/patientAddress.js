import {INPUT_LIMITS, limitDigits, limitText} from "./inputLimits.js"

export function buildEmptyPatientAddress() {
  return {
    street: "",
    number: "",
    apartment: "",
    city: "",
    county: "",
    postal_code: "",
  }
}

export function buildPatientAddressForm(address) {
  return {
    street: limitText(address?.street, INPUT_LIMITS.addressStreet),
    number: limitText(address?.number, INPUT_LIMITS.addressNumber),
    apartment: limitText(address?.apartment, INPUT_LIMITS.addressApartment),
    city: limitText(address?.city, INPUT_LIMITS.country),
    county: limitText(address?.county, INPUT_LIMITS.country),
    postal_code: limitDigits(address?.postal_code, INPUT_LIMITS.postalCode),
  }
}

export function normalizePatientAddress(address) {
  return {
    street: limitText(address?.street, INPUT_LIMITS.addressStreet).trim(),
    number: limitText(address?.number, INPUT_LIMITS.addressNumber).trim(),
    apartment: limitText(address?.apartment, INPUT_LIMITS.addressApartment).trim(),
    city: limitText(address?.city, INPUT_LIMITS.country).trim(),
    county: limitText(address?.county, INPUT_LIMITS.country).trim(),
    postal_code: limitDigits(address?.postal_code, INPUT_LIMITS.postalCode),
  }
}
