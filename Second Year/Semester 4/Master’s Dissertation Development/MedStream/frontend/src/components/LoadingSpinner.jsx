export default function LoadingSpinner({text = "Loading..."}) {
  return (
    <div className="loading-spinner-wrap" role="status" aria-live="polite" aria-busy="true">
      <div className="loading-spinner" aria-hidden="true"/>
      <p className="loading-spinner-text">{text}</p>
    </div>
  )
}
