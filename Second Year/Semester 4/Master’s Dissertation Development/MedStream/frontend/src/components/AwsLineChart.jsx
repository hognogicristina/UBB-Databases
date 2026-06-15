import {useMemo} from "react"
import {Box, LineChart} from "@cloudscape-design/components"

const DEFAULT_I18N_STRINGS = {
  chartAriaRoleDescription: "line chart",
  detailPopoverDismissAriaLabel: "Dismiss",
  filterLabel: "Filter displayed data",
  filterPlaceholder: "Filter data",
  filterSelectedAriaLabel: "selected",
  legendAriaLabel: "Legend",
  xAxisAriaRoleDescription: "x axis",
  yAxisAriaRoleDescription: "y axis",
}
const NOOP_FILTER_CHANGE = () => {}
const EMPTY_THRESHOLDS = []

function defaultValueFormatter(value) {
  if (!Number.isFinite(value)) {
    return "-"
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function toLineData(data, yKey) {
  return (Array.isArray(data) ? data : [])
    .map((point, index) => {
      const x = index + 1
      const rawY = point?.[yKey]
      const y = rawY === null || rawY === "" || rawY === undefined ? Number.NaN : Number(rawY)

      return {x, y}
    })
    .filter((point) => point.x !== "" && point.x != null && Number.isFinite(point.y))
}

function buildLineSeries(data, series) {
  return series.map((item) => ({
    type: "line",
    title: item.title,
    color: item.color,
    valueFormatter: item.valueFormatter || defaultValueFormatter,
    data: toLineData(data, item.key),
  }))
}

export default function AwsLineChart({
  ariaLabel,
  data,
  height = 220,
  highlightedSeriesTitle = undefined,
  hideFilter = true,
  hideLegend = false,
  detailPopoverFooter,
  detailPopoverSeriesContent,
  onHighlightedSeriesTitleChange = null,
  series,
  thresholds = EMPTY_THRESHOLDS,
  xKey = "time",
  xScaleType = "linear",
  xTitle,
  xTickFormatter,
  xDomain,
  yDomain,
  yTickFormatter,
  yTitle,
}) {
  const chartData = useMemo(() => Array.isArray(data) ? data : [], [data])
  const chartSeries = useMemo(() => {
    const lineSeries = buildLineSeries(chartData, series)

    return [
      ...lineSeries,
      ...thresholds.map((threshold) => ({
        type: "threshold",
        title: threshold.title,
        y: threshold.y,
        color: threshold.color,
        valueFormatter: threshold.valueFormatter || defaultValueFormatter,
      })),
    ]
  }, [chartData, series, thresholds])
  const xLabels = useMemo(() => chartData.map((point) => point?.[xKey] ?? ""), [chartData, xKey])
  const resolvedXTickFormatter = useMemo(() => (
    xTickFormatter || ((value) => {
      if (!Number.isInteger(value)) {
        return ""
      }

      return String(xLabels[value - 1] ?? "")
    })
  ), [xLabels, xTickFormatter])
  const resolvedXDomain = xDomain || [1, Math.max(2, chartData.length)]
  const isHighlightControlled = highlightedSeriesTitle !== undefined
  const highlightedSeries = isHighlightControlled
    ? chartSeries.find((item) => item.title === highlightedSeriesTitle) || null
    : undefined
  const handleHighlightChange = isHighlightControlled
    ? ({detail}) => onHighlightedSeriesTitleChange?.(detail.highlightedSeries?.title || null)
    : undefined

  return (
    <LineChart
      ariaLabel={ariaLabel}
      empty={<Box color="text-body-secondary">No chart data available.</Box>}
      height={height}
      highlightedSeries={highlightedSeries}
      hideFilter={hideFilter}
      hideLegend={hideLegend}
      i18nStrings={DEFAULT_I18N_STRINGS}
      detailPopoverFooter={detailPopoverFooter}
      detailPopoverSeriesContent={detailPopoverSeriesContent}
      series={chartSeries}
      statusType="finished"
      visibleSeries={chartSeries}
      onFilterChange={NOOP_FILTER_CHANGE}
      onHighlightChange={handleHighlightChange}
      xDomain={resolvedXDomain}
      xScaleType={xScaleType}
      xTitle={xTitle}
      xTickFormatter={resolvedXTickFormatter}
      yDomain={yDomain}
      yTickFormatter={yTickFormatter}
      yTitle={yTitle}
    />
  )
}
