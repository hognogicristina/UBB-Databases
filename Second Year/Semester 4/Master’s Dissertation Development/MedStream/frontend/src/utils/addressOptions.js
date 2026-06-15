import {State, City} from 'country-state-city'

export function getCountyOptions() {
  const states = State.getStatesOfCountry("RO")
  return states.map(state => ({
    name: state.name.replace(/ County/g, ""),
    isoCode: state.isoCode
  })).sort((a, b) => a.name.localeCompare(b.name))
}

export function getCityOptions(countyName) {
  if (!countyName) return []

  const state = State.getStatesOfCountry("RO").find(
    s => s.name === countyName || s.name.replace(/ County/g, "") === countyName || s.isoCode === countyName
  )

  if (!state) return []

  const cities = City.getCitiesOfState("RO", state.isoCode)
  const uniqueCities = Array.from(new Set(cities.map(city => city.name)))
  return uniqueCities.sort((a, b) => a.localeCompare(b))
}
