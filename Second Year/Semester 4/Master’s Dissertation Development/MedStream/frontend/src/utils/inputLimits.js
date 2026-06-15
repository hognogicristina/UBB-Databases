export const INPUT_LIMITS = {
  activityDescription: 500,
  activityTitle: 120,
  addressApartment: 30,
  addressNumber: 30,
  addressStreet: 120,
  cnp: 13,
  clinicalNote: 1000,
  country: 100,
  diagnosis: 120,
  email: 255,
  firstName: 100,
  identifier: 255,
  lastName: 100,
  licenseNumber: 50,
  password: 72,
  phone: 10,
  postalCode: 6,
  scheduleInterval: 3,
  search: 100,
  time: 5,
}

export function limitText(value, maxLength) {
  return String(value || "").slice(0, maxLength)
}

export function limitDigits(value, maxLength) {
  return String(value || "").replace(/\D/g, "").slice(0, maxLength)
}
