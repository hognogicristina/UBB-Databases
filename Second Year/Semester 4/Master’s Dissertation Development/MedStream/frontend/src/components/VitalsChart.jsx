import AwsLineChart from "./AwsLineChart.jsx"

function EmptyVitalsChart({height}) {
  const ticks = [0, 25, 50, 75, 100]
  const plot = {
    top: 18,
    right: 18,
    bottom: 42,
    left: 48,
  }
  const width = 1000
  const resolvedHeight = Math.max(180, height)
  const plotHeight = resolvedHeight - plot.top - plot.bottom
  const plotWidth = width - plot.left - plot.right

  return (
    <div
      aria-label="Vital signs trend"
      className="medstream-empty-vitals-chart"
      role="img"
      style={{height}}
    >
      <svg viewBox={`0 0 ${width} ${resolvedHeight}`} aria-hidden="true">
        {ticks.map((tick) => {
          const y = plot.top + plotHeight - ((tick / 100) * plotHeight)
          return (
            <g key={tick}>
              <line className="medstream-empty-vitals-chart-grid" x1={plot.left} x2={width - plot.right} y1={y} y2={y}/>
              <text className="medstream-empty-vitals-chart-tick" x={plot.left - 16} y={y + 5} textAnchor="end">
                {tick}
              </text>
            </g>
          )
        })}
        <line className="medstream-empty-vitals-chart-axis" x1={plot.left} x2={width - plot.right} y1={plot.top + plotHeight} y2={plot.top + plotHeight}/>
        <line className="medstream-empty-vitals-chart-axis" x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.top + plotHeight}/>
        <text className="medstream-empty-vitals-chart-axis-title" x={plot.left + plotWidth / 2} y={resolvedHeight - 10} textAnchor="middle">
          Time
        </text>
      </svg>
    </div>
  )
}

export default function VitalsChart({
  data,
  height = 250,
  highlightedSeriesTitle = undefined,
  hideLegend = false,
  detailPopoverFooter = undefined,
  detailPopoverSeriesContent = undefined,
  onHighlightedSeriesTitleChange = null,
  xTickFormatter = undefined,
}) {
  if (!Array.isArray(data) || data.length === 0) {
    return <EmptyVitalsChart height={height}/>
  }

  return (
    <AwsLineChart
      ariaLabel="Vital signs trend"
      data={data}
      height={height}
      highlightedSeriesTitle={highlightedSeriesTitle}
      hideLegend={hideLegend}
      detailPopoverFooter={detailPopoverFooter}
      detailPopoverSeriesContent={detailPopoverSeriesContent}
      onHighlightedSeriesTitleChange={onHighlightedSeriesTitleChange}
      series={[
        {key: "heart_rate", title: "Heart Rate", color: "#f97316", valueFormatter: (value) => `${value.toFixed(0)} bpm`},
        {key: "oxygen_saturation", title: "Oxygen Saturation", color: "#3b82f6", valueFormatter: (value) => `${value.toFixed(0)}%`},
        {key: "temperature", title: "Temperature", color: "#22c55e", valueFormatter: (value) => `${value.toFixed(1)}°C`},
      ]}
      xTitle="Time"
      xTickFormatter={xTickFormatter}
    />
  )
}
