import {useState} from "react"

export default function InfoHelp({
                                   ariaLabel = "Information",
                                   body = [],
                                   footer = "",
                                   title,
                                 }) {
  const [isOpen, setIsOpen] = useState(false)
  const bodyItems = Array.isArray(body) ? body : [body]

  return (
    <span className="medstream-transfer-help-anchor">
      <button
        type="button"
        className={`medstream-transfer-help-trigger${isOpen ? " medstream-transfer-help-trigger-open" : ""}`}
        aria-expanded={isOpen}
        aria-label={isOpen ? `Close ${ariaLabel}` : `Open ${ariaLabel}`}
        onClick={() => setIsOpen((current) => !current)}
      />
      {isOpen ? (
        <span className="medstream-transfer-help-card" role="dialog" aria-label={title || ariaLabel}>
          <button
            type="button"
            className="medstream-transfer-help-close"
            aria-label={`Close ${ariaLabel}`}
            onClick={() => setIsOpen(false)}
          />
          {title ? <span className="medstream-transfer-help-title">{title}</span> : null}
          {bodyItems.filter(Boolean).map((item) => (
            <span className="medstream-transfer-help-body" key={item}>{item}</span>
          ))}
          {footer ? <span className="medstream-transfer-help-footer">{footer}</span> : null}
        </span>
      ) : null}
    </span>
  )
}
