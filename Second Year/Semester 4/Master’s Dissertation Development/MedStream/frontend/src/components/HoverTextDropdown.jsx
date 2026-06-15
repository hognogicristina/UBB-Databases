export default function HoverTextDropdown({
  children,
  className = "",
  content = "",
  position = "bottom",
}) {
  if (!content) {
    return <span className={className}>{children}</span>
  }

  return (
    <span
      className={["medstream-hover-dropdown", className].filter(Boolean).join(" ")}
      data-position={position}
      tabIndex={0}
    >
      <span className="medstream-hover-dropdown-trigger">{children}</span>
      <span className="medstream-hover-dropdown-content" role="tooltip">
        {content}
      </span>
    </span>
  )
}
