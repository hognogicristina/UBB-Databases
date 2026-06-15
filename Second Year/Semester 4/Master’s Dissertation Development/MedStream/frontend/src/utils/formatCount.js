export function formatCount(value) {
  if (value > 999) {
    return "999+"
  }

  return String(value)
}
