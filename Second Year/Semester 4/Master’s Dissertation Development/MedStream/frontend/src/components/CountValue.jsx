import {formatCount} from "../utils/formatCount"
import HoverTextDropdown from "./HoverTextDropdown.jsx"

export default function CountValue({value, className = "", tooltipLabel = "", showFullValue = false}) {
  if (showFullValue) {
    return <span className={className}>{String(value)}</span>
  }

  const displayValue = formatCount(value)
  const defaultTooltip = displayValue !== String(value) ? String(value) : ""
  const resolvedTooltip = tooltipLabel || defaultTooltip

  return (
    <HoverTextDropdown className={className} content={resolvedTooltip}>
      <span>{displayValue}</span>
    </HoverTextDropdown>
  )
}
