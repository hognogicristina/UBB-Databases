import {useLayoutEffect, useMemo, useRef, useState} from "react"
import {Box} from "@cloudscape-design/components"

const AWS_BAR_BLUE = "#4f6bed"
const CHART_WIDTH = 1000
const DEFAULT_CHART_HEIGHT = 360
const SVG_BOTTOM_GAP = 24
const PLOT = {
  top: 30,
  right: 8,
  left: 46,
}

function defaultValueFormatter(value) {
  if (!Number.isFinite(value)) {
    return "-"
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function buildTicks(maxValue) {
  const safeMax = Math.max(1, Math.ceil(maxValue))
  if (safeMax <= 4) {
    return Array.from({length: safeMax + 1}, (_, index) => index)
  }

  const interval = Math.max(1, Math.ceil(safeMax / 5))
  return Array.from({length: 6}, (_, index) => interval * index)
}

function normalizeChartPoint(point, labelKey, valueKey) {
  const label = String(point?.[labelKey] ?? "")
  const value = Number(point?.[valueKey])

  return {
    x: label,
    y: Number.isFinite(value) ? value : 0,
  }
}

export default function AwsBarChart({
  ariaLabel,
  barColor = AWS_BAR_BLUE,
  barWidthRatio = 0.68,
  className = "",
  colorKey = null,
  data,
  emptyText = "No chart data available.",
  height = 260,
  highlightedKey = undefined,
  hideFilter = true,
  hideLegend = false,
  hideZeroValues = false,
  labelKey = "label",
  legendPosition = "center",
  seriesTitle = "Value",
  tooltipValueFormatter = null,
  onHighlightedKeyChange = null,
  valueFormatter = defaultValueFormatter,
  valueKey = "value",
  xTitle,
  yDomain,
  yTickFormatter = (value) => String(Math.round(value)),
  yTitle,
}) {
  void hideFilter

  const chartRef = useRef(null)
  const [chartSize, setChartSize] = useState({width: 0, height: 0})
  const [hoveredKey, setHoveredKey] = useState(null)
  const chartData = useMemo(() => Array.isArray(data) ? data : [], [data])
  const isHighlightControlled = highlightedKey !== undefined
  const activeKey = isHighlightControlled ? highlightedKey : hoveredKey
  const updateActiveKey = (nextKey) => {
    if (isHighlightControlled) {
      onHighlightedKeyChange?.(nextKey)
      return
    }

    setHoveredKey(nextKey)
  }

  useLayoutEffect(() => {
    const node = chartRef.current
    if (!node || typeof ResizeObserver === "undefined") {
      return undefined
    }

    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width)
      const height = Math.round(entry.contentRect.height)
      setChartSize((current) => (
        current.width === width && current.height === height
          ? current
          : {width, height}
      ))
    })

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const points = useMemo(
    () => chartData
      .map((point) => {
        const barPoint = normalizeChartPoint(point, labelKey, valueKey)
        return {
          ...barPoint,
          color: point?.[colorKey] || barColor,
        }
      })
      .filter((point) => point.x),
    [barColor, chartData, colorKey, labelKey, valueKey],
  )
  const visiblePoints = useMemo(
    () => hideZeroValues ? points.filter((point) => point.y > 0) : points,
    [hideZeroValues, points],
  )
  const {resolvedYDomain, ticks} = useMemo(() => {
    if (yDomain) {
      const maxValue = Math.max(1, Number(yDomain[1]) || 1)
      return {resolvedYDomain: yDomain, ticks: buildTicks(maxValue)}
    }

    const maxValue = Math.max(0, ...visiblePoints.map((point) => point.y))
    const nextTicks = buildTicks(Math.max(1, Math.ceil(maxValue * 1.15)))

    return {resolvedYDomain: [0, nextTicks[nextTicks.length - 1]], ticks: nextTicks}
  }, [visiblePoints, yDomain])
  const svgBottomGap = hideLegend ? 0 : SVG_BOTTOM_GAP
  const chartHeight = chartSize.width && chartSize.height
    ? Math.max(260, Math.round(CHART_WIDTH * Math.max(180, chartSize.height - svgBottomGap) / chartSize.width))
    : DEFAULT_CHART_HEIGHT
  const plotTop = yTitle ? PLOT.top : 28
  const plotBottom = chartHeight - (xTitle ? 78 : 44)
  const plotWidth = CHART_WIDTH - PLOT.left - PLOT.right
  const plotHeight = plotBottom - plotTop
  const categoryWidth = visiblePoints.length ? plotWidth / visiblePoints.length : plotWidth
  const barWidth = Math.min(380, categoryWidth * barWidthRatio)
  const maxDomainValue = Number(resolvedYDomain[1]) || 1
  const bars = visiblePoints.map((point, index) => {
    const heightRatio = Math.max(0, Math.min(1, point.y / maxDomainValue))
    const barHeight = Math.max(point.y > 0 ? 3 : 0, plotHeight * heightRatio)
    const svgX = PLOT.left + (index * categoryWidth) + ((categoryWidth - barWidth) / 2)
    const svgY = plotBottom - barHeight

    return {
      ...point,
      barHeight,
      barWidth,
      centerX: svgX + barWidth / 2,
      svgX,
      tooltipY: Math.min(
        plotBottom - 26,
        Math.max(plotTop + 26, svgY + (barHeight / 2)),
      ),
      svgY,
    }
  })
  const hoveredBar = activeKey == null ? null : bars.find((bar) => bar.x === activeKey) || null
  const formatTooltipValue = tooltipValueFormatter || ((bar) => valueFormatter(bar.y))
  const hasActiveBar = activeKey != null
  const legendItems = colorKey ? points : [{x: seriesTitle, color: barColor}]
  const tooltipLeft = hoveredBar ? Math.min(78, Math.max(22, (hoveredBar.centerX / CHART_WIDTH) * 100)) : 50
  const tooltipPlacement = hoveredBar && hoveredBar.centerX > CHART_WIDTH * 0.62 ? "left" : "right"

  return (
    <div
      aria-label={ariaLabel}
      ref={chartRef}
      className={["medstream-aws-bar-chart", className].filter(Boolean).join(" ")}
      onMouseLeave={() => updateActiveKey(null)}
      role="img"
      style={{height, paddingBottom: svgBottomGap}}
    >
      {visiblePoints.length ? (
        <>
          <svg className="medstream-aws-bar-chart-svg" viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`} aria-hidden="true">
            {yTitle ? (
              <text
                className="medstream-aws-bar-chart-title"
                textAnchor="start"
                x={0}
                y="12"
              >
                {yTitle}
              </text>
            ) : null}
            {ticks.map((tick) => {
              const y = plotBottom - ((tick - resolvedYDomain[0]) / maxDomainValue) * plotHeight
              return (
                <g key={tick}>
                  <line className="medstream-aws-bar-chart-grid" x1={PLOT.left} x2={CHART_WIDTH - PLOT.right} y1={y} y2={y}/>
                  <text className="medstream-aws-bar-chart-tick" x={PLOT.left - 16} y={y + 6} textAnchor="end">
                    {yTickFormatter(tick)}
                  </text>
                </g>
              )
            })}
            <line className="medstream-aws-bar-chart-baseline" x1={PLOT.left} x2={CHART_WIDTH - PLOT.right} y1={plotBottom} y2={plotBottom}/>
            {bars.map((bar) => (
              <g
                key={bar.x}
                onBlur={() => updateActiveKey(null)}
                onFocus={() => updateActiveKey(bar.x)}
                onMouseEnter={() => updateActiveKey(bar.x)}
                tabIndex={0}
              >
                <rect
                  className={[
                    "medstream-aws-bar-chart-bar",
                    activeKey === bar.x ? "medstream-aws-bar-chart-bar-hovered" : "",
                    hasActiveBar && activeKey !== bar.x ? "medstream-aws-bar-chart-bar-muted" : "",
                  ].filter(Boolean).join(" ")}
                  fill={bar.color}
                  height={bar.barHeight}
                  rx="5"
                  ry="5"
                  width={bar.barWidth}
                  x={bar.svgX}
                  y={bar.svgY}
                />
                {activeKey === bar.x ? (
                  <rect
                    className="medstream-aws-bar-chart-bar-overlay"
                    height={bar.barHeight}
                    rx="5"
                    ry="5"
                    width={bar.barWidth}
                    x={bar.svgX}
                    y={bar.svgY}
                  />
                ) : null}
                <text className="medstream-aws-bar-chart-x-label" x={bar.centerX} y={plotBottom + 32} textAnchor="middle">
                  {bar.x}
                </text>
              </g>
            ))}
            {xTitle ? (
              <text className="medstream-aws-bar-chart-axis-title" x={PLOT.left + plotWidth / 2} y={chartHeight - 12} textAnchor="middle">
                {xTitle}
              </text>
            ) : null}
          </svg>

          {hoveredBar ? (
            <div
              className="medstream-aws-bar-chart-tooltip"
              data-placement={tooltipPlacement}
              style={{
                left: `${tooltipLeft}%`,
                top: `${(hoveredBar.tooltipY / chartHeight) * 100}%`,
              }}
            >
              <strong>{hoveredBar.x}</strong>
              <span>
                <i style={{backgroundColor: hoveredBar.color}}/>
                <em>{seriesTitle}</em>
                <b>{formatTooltipValue(hoveredBar)}</b>
              </span>
            </div>
          ) : null}

          {!hideLegend ? (
            <div className={`medstream-aws-bar-chart-legend medstream-aws-bar-chart-legend-${legendPosition}`}>
              {legendItems.map((item) => (
                <span
                  className={[
                    "medstream-aws-bar-chart-legend-item",
                    activeKey === item.x ? "medstream-aws-bar-chart-legend-item-active" : "",
                    hasActiveBar && activeKey !== item.x ? "medstream-aws-bar-chart-legend-item-muted" : "",
                  ].filter(Boolean).join(" ")}
                  key={item.x}
                  onBlur={() => updateActiveKey(null)}
                  onFocus={() => updateActiveKey(item.x)}
                  onMouseEnter={() => updateActiveKey(item.x)}
                  tabIndex={0}
                >
                  <i style={{backgroundColor: item.color}}/>
                  {item.x}
                </span>
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <Box color="text-body-secondary">{emptyText}</Box>
      )}
    </div>
  )
}
