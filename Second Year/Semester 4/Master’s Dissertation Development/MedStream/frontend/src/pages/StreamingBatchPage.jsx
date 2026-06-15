import {useEffect, useMemo, useRef, useState} from "react"
import {
  Box,
  Button,
  Container,
  ContentLayout,
  FormField,
  Header,
  Input,
  SegmentedControl,
  Select,
  SpaceBetween,
} from "@cloudscape-design/components"
import {
  getBatchMetrics,
  getMetricsComparison,
  getMetricsComparisonHistory,
  getStreamingMetrics,
} from "../services/patientApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {downloadCSV} from "../utils/downloadCSV.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AwsLineChart from "../components/AwsLineChart.jsx"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import {formatBucharestNumericDateTime, formatBucharestTime} from "../utils/time.js"

const POLL_INTERVAL_MS = 4000
const MAX_HISTORY_POINTS = 900
const CHART_HISTORY_MAX_SECONDS = 5 * 365 * 24 * 60 * 60
const STORAGE_KEYS = {
  throughputHistory: "medstream.streamingBatch.v2.throughputHistory",
  latencyHistory: "medstream.streamingBatch.v2.latencyHistory",
  chartTimeRange: "medstream.streamingBatch.v2.chartTimeRange",
  throughputChartTimeRange: "medstream.streamingBatch.v2.throughputChartTimeRange",
  latencyChartTimeRange: "medstream.streamingBatch.v2.latencyChartTimeRange",
}
const CHART_PRESET_RANGE_OPTIONS = [
  {key: "15m", type: "relative", amount: 15, unit: "minute"},
  {key: "30m", type: "relative", amount: 30, unit: "minute"},
  {key: "1h", type: "relative", amount: 1, unit: "hour"},
]
const DEFAULT_CUSTOM_CHART_TIME_RANGE = {key: "custom", type: "relative", amount: 1, unit: "minute"}
const DEFAULT_CHART_TIME_RANGE = DEFAULT_CUSTOM_CHART_TIME_RANGE
const CHART_RANGE_CONTROL_OPTIONS = [
  {id: "15m", text: "15m"},
  {id: "30m", text: "30m"},
  {id: "1h", text: "1h"},
  {id: "custom", text: "Custom"},
]
const CUSTOM_CHART_TIME_UNIT_OPTIONS = [
  {label: "minutes", value: "minute"},
  {label: "hours", value: "hour"},
  {label: "days", value: "day"},
  {label: "weeks", value: "week"},
  {label: "months", value: "month"},
  {label: "years", value: "year"},
]
const FULL_TIME_AXIS_RANGE_SECONDS = 24 * 60 * 60
const THROUGHPUT_CHART_SERIES = [
  {key: "streaming_alerts_per_minute", title: "Streaming Alerts/minute", color: "#f97316", valueFormatter: (value) => `${value.toFixed(0)}`},
  {key: "batch_alerts_per_minute", title: "Batch Alerts/minute", color: "#60a5fa", valueFormatter: (value) => `${value.toFixed(2)}`},
]
const LATENCY_CHART_SERIES = [
  {key: "streaming_latency_ms", title: "Streaming Latency", color: "#f97316", valueFormatter: (value) => formatLatencyDuration(value)},
  {key: "batch_latency_ms", title: "Batch Latency Avg", color: "#60a5fa", valueFormatter: (value) => formatLatencyDuration(value)},
]
const STREAMING_LATENCY_CHART_SERIES = [
  LATENCY_CHART_SERIES[0],
]
const BATCH_LATENCY_CHART_SERIES = [
  LATENCY_CHART_SERIES[1],
]

function formatFixed(value, digits = 2) {
  const safeValue = Number.isFinite(value) ? value : 0
  return safeValue.toFixed(digits)
}

function roundNumber(value, digits = 2) {
  const safeValue = Number(value)
  return Number.isFinite(safeValue) ? Number(safeValue.toFixed(digits)) : 0
}

function ratioOrBlank(numerator, denominator, digits = 4) {
  const safeNumerator = Number(numerator)
  const safeDenominator = Number(denominator)
  if (!Number.isFinite(safeNumerator) || !Number.isFinite(safeDenominator) || safeDenominator <= 0) {
    return ""
  }
  return roundNumber(safeNumerator / safeDenominator, digits)
}

function formatLatencyDuration(value) {
  const safeValue = Number.isFinite(value) ? value : 0
  if (safeValue >= 60000) {
    return `${formatFixed(safeValue / 60000, 2)} min`
  }
  if (safeValue >= 1000) {
    return `${formatFixed(safeValue / 1000, 2)} sec`
  }
  return `${formatFixed(safeValue, 2)} ms`
}

function formatLatencyAxisValue(value, unit = "ms") {
  const safeValue = Number.isFinite(value) ? value : 0

  if (unit === "min") {
    return `${formatFixed(safeValue / 60000, 2)} min`
  }

  return `${formatFixed(safeValue, 2)} ms`
}

function getRangeOptionByKey(key) {
  return CHART_PRESET_RANGE_OPTIONS.find((range) => range.key === key) || null
}

function getRelativeRangeSeconds(value) {
  if (!value || value.type !== "relative") {
    return 0
  }

  const amount = Number(value.amount) || 0
  if (value.unit === "second") {
    return amount
  }
  if (value.unit === "minute") {
    return amount * 60
  }
  if (value.unit === "hour") {
    return amount * 60 * 60
  }
  if (value.unit === "day") {
    return amount * 24 * 60 * 60
  }
  if (value.unit === "week") {
    return amount * 7 * 24 * 60 * 60
  }
  if (value.unit === "month") {
    return amount * 30 * 24 * 60 * 60
  }
  if (value.unit === "year") {
    return amount * 365 * 24 * 60 * 60
  }
  return 0
}

function formatRelativeRangeLabel(value) {
  const amount = Number(value?.amount) || 0
  const unit = value?.unit || "minute"
  const pluralUnit = amount === 1 ? unit : `${unit}s`

  return `Last ${amount} ${pluralUnit}`
}

function parseStoredChartTimeRange(storedValue) {
  if (!storedValue) {
    return DEFAULT_CHART_TIME_RANGE
  }

  const legacyRange = getRangeOptionByKey(storedValue)
  if (legacyRange) {
    return legacyRange
  }

  try {
    const parsedValue = JSON.parse(storedValue)
    if (parsedValue?.type === "relative") {
      const presetRange = getRangeOptionByKey(parsedValue.key)
      if (presetRange) {
        return presetRange
      }
      return {
        key: "custom",
        type: "relative",
        amount: Number(parsedValue.amount) || DEFAULT_CHART_TIME_RANGE.amount,
        unit: parsedValue.unit || DEFAULT_CHART_TIME_RANGE.unit,
      }
    }
  } catch {
    return DEFAULT_CHART_TIME_RANGE
  }

  return DEFAULT_CHART_TIME_RANGE
}

function getChartRangeWindow(rangeValue, nowMs = Date.now()) {
  const seconds = getRelativeRangeSeconds(rangeValue)
  return {startMs: nowMs - seconds * 1000, endMs: nowMs}
}

function getHistoryIntervalSeconds(seconds) {
  return Math.max(Math.round(POLL_INTERVAL_MS / 1000), Math.ceil(seconds / Math.max(1, MAX_HISTORY_POINTS - 1)))
}

function getCombinedHistoryRequestParams(rangeValues) {
  const seconds = Math.max(
    60,
    ...rangeValues.map((rangeValue) => getRelativeRangeSeconds(rangeValue) || 0),
  )

  return {
    seconds,
    interval_seconds: getHistoryIntervalSeconds(seconds),
  }
}

function getChartRangeLabel(rangeValue) {
  return formatRelativeRangeLabel(rangeValue || DEFAULT_CHART_TIME_RANGE)
}

function getChartRangeControlId(rangeValue) {
  return getRangeOptionByKey(rangeValue?.key)?.key || "custom"
}

function getCustomTimeUnitOption(unit) {
  return CUSTOM_CHART_TIME_UNIT_OPTIONS.find((option) => option.value === unit) || CUSTOM_CHART_TIME_UNIT_OPTIONS[1]
}

function shouldShowFullTimestamp(rangeValue) {
  return getRelativeRangeSeconds(rangeValue) > FULL_TIME_AXIS_RANGE_SECONDS
}

function getHistoryPointLabel(point, useFullTimestamp) {
  if (!point) {
    return ""
  }

  if (!useFullTimestamp) {
    return point.time || ""
  }

  if (point.time_iso) {
    return formatBucharestNumericDateTime(point.time_iso, point.time || "")
  }

  return point.time || ""
}

function buildChartXAxisTickFormatter(points, rangeValue) {
  const useFullTimestamp = shouldShowFullTimestamp(rangeValue)

  return (value) => {
    if (!Number.isInteger(value)) {
      return ""
    }

    return getHistoryPointLabel(points[value - 1], useFullTimestamp)
  }
}

function toMillis(value) {
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : null
}

function getStoredValue(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function setStoredValue(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Chart history is useful but non-critical when browser storage is unavailable.
  }
}

function normalizeHistoryPoint(point) {
  const timestampMs = toMillis(point?.time_iso)
  if (timestampMs == null) {
    return null
  }

  return {
    ...point,
    time_iso: new Date(timestampMs).toISOString(),
    time: formatBucharestTime(timestampMs),
  }
}

function normalizeHistory(points) {
  return (Array.isArray(points) ? points : [])
    .map(normalizeHistoryPoint)
    .filter(Boolean)
    .sort((a, b) => toMillis(a.time_iso) - toMillis(b.time_iso))
    .slice(-MAX_HISTORY_POINTS)
}

function mergeHistoryPoints(currentPoints, nextPoints) {
  const pointsByTimestamp = new Map()

  normalizeHistory(currentPoints).forEach((point) => {
    pointsByTimestamp.set(point.time_iso, point)
  })
  normalizeHistory(nextPoints).forEach((point) => {
    pointsByTimestamp.set(point.time_iso, point)
  })

  return normalizeHistory([...pointsByTimestamp.values()])
}

function loadStoredHistory(storageKey) {
  const storedValue = getStoredValue(storageKey)
  if (!storedValue) {
    return []
  }

  try {
    const parsed = JSON.parse(storedValue)
    return normalizeHistory(parsed)
  } catch {
    return []
  }
}

function loadStoredChartTimeRange(storageKey = STORAGE_KEYS.chartTimeRange) {
  return parseStoredChartTimeRange(getStoredValue(storageKey) || getStoredValue(STORAGE_KEYS.chartTimeRange))
}

function padHistoryToWindow(points, rangeWindow) {
  if (!Array.isArray(points) || points.length === 0) {
    return []
  }

  const pointsWithTime = points
    .map((point) => ({point, time: toMillis(point?.time_iso)}))
    .filter(({time}) => time != null && Number.isFinite(time))
    .sort((a, b) => a.time - b.time)

  if (pointsWithTime.length === 0) {
    return []
  }

  const inRange = pointsWithTime.filter(({time}) => time >= rangeWindow.startMs && time <= rangeWindow.endMs)

  if (inRange.length === 0) {
    return []
  }

  return inRange.map(({point}) => point)
}

function filterHistoryByRange(points, rangeValue) {
  if (!Array.isArray(points) || points.length === 0) {
    return []
  }

  const rangeWindow = getChartRangeWindow(rangeValue)
  if (!rangeWindow) {
    return []
  }

  const padded = padHistoryToWindow(points, rangeWindow)
  const clamped = padded.filter((point) => {
    const pointTime = toMillis(point?.time_iso)
    return pointTime != null && pointTime >= rangeWindow.startMs && pointTime <= rangeWindow.endMs
  })

  return clamped
}

function MetricCard({label, value, hint}) {
  return (
    <SpaceBetween size="xxs" className="medstream-comparison-metric-card">
      <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
      <div className="medstream-comparison-metric-value">{value}</div>
      <Box color="text-body-secondary" variant="small">{hint}</Box>
    </SpaceBetween>
  )
}

export default function StreamingBatchPage() {
  const {notifyError} = useNotifications()
  const [comparison, setComparison] = useState(null)
  const [streamingMetricsSnapshot, setStreamingMetricsSnapshot] = useState(null)
  const [batchMetricsSnapshot, setBatchMetricsSnapshot] = useState(null)
  const [throughputHistory, setThroughputHistory] = useState(() => loadStoredHistory(STORAGE_KEYS.throughputHistory))
  const [latencyHistory, setLatencyHistory] = useState(() => loadStoredHistory(STORAGE_KEYS.latencyHistory))
  const [isLoading, setIsLoading] = useState(true)
  const [highlightedThroughputSeries, setHighlightedThroughputSeries] = useState(null)
  const [highlightedStreamingLatencySeries, setHighlightedStreamingLatencySeries] = useState(null)
  const [highlightedBatchLatencySeries, setHighlightedBatchLatencySeries] = useState(null)
  const [throughputChartTimeRange, setThroughputChartTimeRange] = useState(() => loadStoredChartTimeRange(STORAGE_KEYS.throughputChartTimeRange))
  const [latencyChartTimeRange, setLatencyChartTimeRange] = useState(() => loadStoredChartTimeRange(STORAGE_KEYS.latencyChartTimeRange))
  const [isThroughputCustomRangeOpen, setIsThroughputCustomRangeOpen] = useState(false)
  const [isLatencyCustomRangeOpen, setIsLatencyCustomRangeOpen] = useState(false)
  const [throughputCustomRangeDraft, setThroughputCustomRangeDraft] = useState(throughputChartTimeRange)
  const [latencyCustomRangeDraft, setLatencyCustomRangeDraft] = useState(latencyChartTimeRange)
  const throughputCustomRangeRef = useRef(null)
  const latencyCustomRangeRef = useRef(null)

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.throughputHistory, JSON.stringify(throughputHistory.slice(-MAX_HISTORY_POINTS)))
  }, [throughputHistory])

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.latencyHistory, JSON.stringify(latencyHistory.slice(-MAX_HISTORY_POINTS)))
  }, [latencyHistory])

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.throughputChartTimeRange, JSON.stringify(throughputChartTimeRange))
  }, [throughputChartTimeRange])

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.latencyChartTimeRange, JSON.stringify(latencyChartTimeRange))
  }, [latencyChartTimeRange])

  useEffect(() => {
    setThroughputCustomRangeDraft(throughputChartTimeRange)
  }, [throughputChartTimeRange])

  useEffect(() => {
    setLatencyCustomRangeDraft(latencyChartTimeRange)
  }, [latencyChartTimeRange])

  useEffect(() => {
    if (!isThroughputCustomRangeOpen && !isLatencyCustomRangeOpen) {
      return undefined
    }

    const handleDocumentMouseDown = (event) => {
      if (isThroughputCustomRangeOpen && !throughputCustomRangeRef.current?.contains(event.target)) {
        setIsThroughputCustomRangeOpen(false)
      }
      if (isLatencyCustomRangeOpen && !latencyCustomRangeRef.current?.contains(event.target)) {
        setIsLatencyCustomRangeOpen(false)
      }
    }
    const handleDocumentKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsThroughputCustomRangeOpen(false)
        setIsLatencyCustomRangeOpen(false)
      }
    }

    document.addEventListener("mousedown", handleDocumentMouseDown)
    document.addEventListener("keydown", handleDocumentKeyDown)

    return () => {
      document.removeEventListener("mousedown", handleDocumentMouseDown)
      document.removeEventListener("keydown", handleDocumentKeyDown)
    }
  }, [isLatencyCustomRangeOpen, isThroughputCustomRangeOpen])

  useEffect(() => {
    let active = true
    let isFirstLoad = true

    const loadData = async () => {
      if (isFirstLoad) {
        setIsLoading(true)
      }

      try {
        const historyRequestParams = getCombinedHistoryRequestParams([throughputChartTimeRange, latencyChartTimeRange])
        const [comparisonResponse, streamingResponse, batchResponse, historyResponse] = await Promise.all([
          getMetricsComparison(),
          getStreamingMetrics(),
          getBatchMetrics(),
          getMetricsComparisonHistory(historyRequestParams),
        ])

        if (!active) {
          return
        }

        const nextComparison = getResponseData(comparisonResponse)
        const streamingMetrics = getResponseData(streamingResponse)
        const batchMetrics = getResponseData(batchResponse)
        const comparisonHistory = getResponseData(historyResponse)

        setComparison(nextComparison)
        setStreamingMetricsSnapshot(streamingMetrics || null)
        setBatchMetricsSnapshot(batchMetrics || null)
        setThroughputHistory(mergeHistoryPoints([], comparisonHistory?.throughput))
        setLatencyHistory(mergeHistoryPoints([], comparisonHistory?.latency))
      } catch (loadError) {
        if (active) {
          notifyError(getErrorMessage(loadError), {duration: 5000})
        }
      } finally {
        if (active) {
          setIsLoading(false)
          isFirstLoad = false
        }
      }
    }

    loadData()
    const intervalId = window.setInterval(loadData, POLL_INTERVAL_MS)

    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [latencyChartTimeRange, notifyError, throughputChartTimeRange])

  const data = comparison ?? {
    streaming_latency_avg: 0,
    batch_latency_avg: 0,
    total_events: 0,
    total_alerts: 0,
    events_per_second: 0,
    alert_rate: 0,
    batch_total_events: 0,
    batch_total_alerts: 0,
    batch_events_per_second: 0,
    batch_alert_rate: 0,
  }

  const batchLatencyMinutes = (Number(data.batch_latency_avg) || 0) / 60
  const streamingLatencyMs = Number(data.streaming_latency_avg) || 0
  const streamingExecutionTimeMs = Number(streamingMetricsSnapshot?.execution_time_ms) || 0
  const batchLatencyMs = (Number(data.batch_latency_avg) || 0) * 1000
  const batchExecutionTimeMs = Number(batchMetricsSnapshot?.execution_time_ms) || 0
  const latestThroughputPoint = throughputHistory[throughputHistory.length - 1] || {}
  const latestLatencyPoint = latencyHistory[latencyHistory.length - 1] || {}
  const visibleThroughputHistory = useMemo(
    () => filterHistoryByRange(throughputHistory, throughputChartTimeRange),
    [throughputChartTimeRange, throughputHistory],
  )
  const visibleLatencyHistory = useMemo(
    () => filterHistoryByRange(latencyHistory, latencyChartTimeRange),
    [latencyChartTimeRange, latencyHistory],
  )
  const throughputXAxisTickFormatter = useMemo(
    () => buildChartXAxisTickFormatter(visibleThroughputHistory, throughputChartTimeRange),
    [throughputChartTimeRange, visibleThroughputHistory],
  )
  const latencyXAxisTickFormatter = useMemo(
    () => buildChartXAxisTickFormatter(visibleLatencyHistory, latencyChartTimeRange),
    [latencyChartTimeRange, visibleLatencyHistory],
  )
  const latestStreamingAlertsPerMinute = Number(latestThroughputPoint.streaming_alerts_per_minute) || 0
  const latestBatchAlertsPerMinute = Number(latestThroughputPoint.batch_alerts_per_minute) || 0
  const eventsPerSecond = Number(data.events_per_second) || 0
  const alertRate = Number(data.alert_rate) || 0
  const batchEventsPerSecond = Number(data.batch_events_per_second) || 0
  const batchAlertRate = Number(data.batch_alert_rate) || 0
  const batchTotalEvents = Number(data.batch_total_events) || 0
  const batchTotalAlerts = Number(data.batch_total_alerts) || 0
  const alertsPerSecondEstimate = eventsPerSecond * alertRate
  const batchSnapshotAgeSeconds = batchMetricsSnapshot?.timestamp
    ? Math.max(0, (Date.now() - new Date(batchMetricsSnapshot.timestamp).getTime()) / 1000)
    : ""
  const throughputChartYDomain = useMemo(() => [
    0,
    Math.max(
      1,
      ...visibleThroughputHistory.flatMap((point) => [
        Number(point.streaming_alerts_per_minute) || 0,
        Number(point.batch_alerts_per_minute) || 0,
      ]),
    ),
  ], [visibleThroughputHistory])
  const streamingLatencyChartYDomain = useMemo(() => [
    0,
    Math.max(
      1,
      ...visibleLatencyHistory.map((point) => Number(point.streaming_latency_ms) || 0),
    ),
  ], [visibleLatencyHistory])
  const batchLatencyChartYDomain = useMemo(() => [
    0,
    Math.max(
      1,
      ...visibleLatencyHistory.map((point) => Number(point.batch_latency_ms) || 0),
    ),
  ], [visibleLatencyHistory])

  const updateChartTimeRange = ({detail}, currentRange, setRange, setIsOpen, setRangeDraft) => {
    const selectedId = detail?.selectedId || DEFAULT_CHART_TIME_RANGE.key
    const presetRange = getRangeOptionByKey(selectedId)

    if (presetRange) {
      setRange(presetRange)
      setIsOpen(false)
      return
    }

    setRangeDraft({
      ...DEFAULT_CUSTOM_CHART_TIME_RANGE,
      ...(getChartRangeControlId(currentRange) === "custom" ? currentRange : {}),
      key: "custom",
    })
    setIsOpen(true)
  }

  const updateCustomDuration = ({detail}, setRangeDraft, setIsOpen) => {
    const nextAmount = Math.max(1, Number(detail?.value) || 1)
    setRangeDraft((currentRange) => ({
      ...DEFAULT_CUSTOM_CHART_TIME_RANGE,
      ...(getChartRangeControlId(currentRange) === "custom" ? currentRange : {}),
      key: "custom",
      amount: nextAmount,
    }))
    setIsOpen(true)
  }

  const updateCustomUnit = ({detail}, setRangeDraft, setIsOpen) => {
    const nextUnit = detail?.selectedOption?.value || DEFAULT_CUSTOM_CHART_TIME_RANGE.unit
    setRangeDraft((currentRange) => ({
      ...DEFAULT_CUSTOM_CHART_TIME_RANGE,
      ...(getChartRangeControlId(currentRange) === "custom" ? currentRange : {}),
      key: "custom",
      unit: nextUnit,
    }))
    setIsOpen(true)
  }

  const renderChartTimeRangeControl = ({
    rangeValue,
    setRangeValue,
    rangeDraftValue,
    setRangeDraftValue,
    isOpen,
    setIsOpen,
    rangeRef,
  }) => (
    <div
      className="medstream-comparison-chart-actions"
      ref={rangeRef}
      onClickCapture={(event) => {
        const triggerButton = event.target.closest?.("button")
        if (triggerButton?.textContent?.trim() === "Custom") {
          setRangeDraftValue({
            ...DEFAULT_CUSTOM_CHART_TIME_RANGE,
            ...(getChartRangeControlId(rangeValue) === "custom" ? rangeValue : {}),
            key: "custom",
          })
          setIsOpen(true)
        }
      }}
    >
      <SegmentedControl
        selectedId={getChartRangeControlId(rangeValue)}
        label="Chart time range"
        options={CHART_RANGE_CONTROL_OPTIONS}
        onChange={(event) => updateChartTimeRange(
          event,
          rangeValue,
          setRangeValue,
          setIsOpen,
          setRangeDraftValue,
        )}
      />
      {isOpen && (
        <div className="medstream-comparison-custom-range-popover" role="dialog" aria-label="Custom chart time range">
          <div className="medstream-comparison-custom-range-controls">
            <div className="medstream-comparison-custom-range-duration">
              <FormField label="Duration">
                <Input
                  type="number"
                  inputMode="numeric"
                  min={1}
                  value={String(rangeDraftValue.amount || "")}
                  placeholder="Duration"
                  onChange={(event) => updateCustomDuration(event, setRangeDraftValue, setIsOpen)}
                />
              </FormField>
            </div>
            <div className="medstream-comparison-custom-range-unit">
              <FormField label="Unit of time">
                <Select
                  selectedOption={getCustomTimeUnitOption(rangeDraftValue.unit)}
                  options={CUSTOM_CHART_TIME_UNIT_OPTIONS}
                  onChange={(event) => updateCustomUnit(event, setRangeDraftValue, setIsOpen)}
                />
              </FormField>
            </div>
            <div className="medstream-comparison-custom-range-apply">
              <Button
                variant="primary"
                onClick={() => {
                  setRangeValue(rangeDraftValue)
                  setIsOpen(false)
                }}
              >
                Apply
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const exportComparisonMetrics = () => {
    const exportTimestamp = new Date().toISOString()
    const throughputDifference = latestBatchAlertsPerMinute - latestStreamingAlertsPerMinute
    const latencyDifferenceMs = batchLatencyMs - streamingLatencyMs
    const executionTimeDifferenceMs = batchExecutionTimeMs - streamingExecutionTimeMs
    const rows = [
      ["summary_metric", "value"],
      ["export_timestamp", exportTimestamp],
      ["throughput_chart_time_range", getChartRangeLabel(throughputChartTimeRange)],
      ["latency_chart_time_range", getChartRangeLabel(latencyChartTimeRange)],
      ["latest_history_timestamp", latestThroughputPoint.time_iso || latestLatencyPoint.time_iso || ""],
      ["latest_streaming_alerts_per_minute", latestStreamingAlertsPerMinute],
      ["latest_batch_alerts_per_minute", latestBatchAlertsPerMinute],
      ["throughput_difference_batch_alerts_per_minute_minus_streaming_alerts_per_minute", throughputDifference],
      ["throughput_ratio_batch_to_streaming", ratioOrBlank(latestBatchAlertsPerMinute, latestStreamingAlertsPerMinute)],
      ["streaming_latency_ms", roundNumber(streamingLatencyMs)],
      ["batch_latency_avg_ms", roundNumber(batchLatencyMs)],
      ["batch_latency_avg_seconds", roundNumber(batchLatencyMs / 1000, 4)],
      ["batch_latency_avg_minutes", roundNumber(batchLatencyMinutes, 4)],
      ["latency_difference_batch_minus_streaming_ms", roundNumber(latencyDifferenceMs)],
      ["latency_ratio_batch_to_streaming", ratioOrBlank(batchLatencyMs, streamingLatencyMs)],
      ["streaming_event_to_alert_latency_avg_ms", roundNumber(streamingLatencyMs)],
      ["streaming_execution_time_ms", roundNumber(streamingExecutionTimeMs)],
      ["batch_execution_time_ms", roundNumber(batchExecutionTimeMs)],
      ["execution_time_difference_batch_minus_streaming_ms", roundNumber(executionTimeDifferenceMs)],
      ["execution_time_ratio_batch_to_streaming", ratioOrBlank(batchExecutionTimeMs, streamingExecutionTimeMs)],
      ["total_events_window", Number(data.total_events) || 0],
      ["total_alerts_window", Number(data.total_alerts) || 0],
      ["events_per_second", roundNumber(eventsPerSecond, 4)],
      ["events_per_minute", roundNumber(eventsPerSecond * 60, 4)],
      ["alert_rate", roundNumber(alertRate, 4)],
      ["alert_rate_percent", roundNumber(alertRate * 100, 2)],
      ["estimated_alerts_per_second", roundNumber(alertsPerSecondEstimate, 4)],
      ["estimated_alerts_per_minute", roundNumber(alertsPerSecondEstimate * 60, 4)],
      ["batch_total_events_window", batchTotalEvents],
      ["batch_total_alerts_window", batchTotalAlerts],
      ["batch_events_per_second", roundNumber(batchEventsPerSecond, 4)],
      ["batch_alert_rate", roundNumber(batchAlertRate, 4)],
      ["batch_alert_rate_percent", roundNumber(batchAlertRate * 100, 2)],
      ["streaming_avg_heart_rate", roundNumber(streamingMetricsSnapshot?.avg_heart_rate)],
      ["batch_avg_heart_rate", roundNumber(batchMetricsSnapshot?.avg_heart_rate)],
      ["streaming_avg_oxygen", roundNumber(streamingMetricsSnapshot?.avg_oxygen)],
      ["batch_avg_oxygen", roundNumber(batchMetricsSnapshot?.avg_oxygen)],
      ["streaming_avg_temperature", roundNumber(streamingMetricsSnapshot?.avg_temperature)],
      ["batch_avg_temperature", roundNumber(batchMetricsSnapshot?.avg_temperature)],
      ["batch_patients_count", Number(batchMetricsSnapshot?.patients_count) || 0],
      ["batch_generated_discharge_summaries_count", Number(batchMetricsSnapshot?.generated_discharge_summaries_count) || 0],
      ["batch_pending_discharge_summaries_count", Number(batchMetricsSnapshot?.pending_discharge_summaries_count) || 0],
      ["streaming_snapshot_timestamp", streamingMetricsSnapshot?.timestamp ? new Date(streamingMetricsSnapshot.timestamp).toISOString() : ""],
      ["batch_snapshot_timestamp", batchMetricsSnapshot?.timestamp ? new Date(batchMetricsSnapshot.timestamp).toISOString() : ""],
      ["batch_snapshot_age_seconds", batchSnapshotAgeSeconds === "" ? "" : roundNumber(batchSnapshotAgeSeconds, 1)],
      [],
      [
        "throughput_timestamp",
        "streaming_alerts_per_minute",
        "batch_alerts_per_minute",
        "difference_batch_minus_streaming",
        "ratio_batch_to_streaming",
        "batch_snapshot_timestamp",
      ],
      ...visibleThroughputHistory.map((point) => [
        point.time_iso || "",
        Number(point.streaming_alerts_per_minute) || 0,
        Number(point.batch_alerts_per_minute) || 0,
        (Number(point.batch_alerts_per_minute) || 0) - (Number(point.streaming_alerts_per_minute) || 0),
        ratioOrBlank(point.batch_alerts_per_minute, point.streaming_alerts_per_minute),
        point.batch_timestamp || "",
      ]),
      [],
      [
        "latency_timestamp",
        "streaming_latency_ms",
        "batch_latency_ms",
        "difference_batch_minus_streaming_ms",
        "ratio_batch_to_streaming",
      ],
      ...visibleLatencyHistory.map((point) => [
        point.time_iso || "",
        roundNumber(point.streaming_latency_ms),
        roundNumber(point.batch_latency_ms),
        roundNumber((Number(point.batch_latency_ms) || 0) - (Number(point.streaming_latency_ms) || 0)),
        ratioOrBlank(point.batch_latency_ms, point.streaming_latency_ms),
      ]),
    ]
    downloadCSV("streaming_batch_comparison.csv", rows)
  }

  return (
    <ContentLayout>
      <div className="medstream-comparison-page">
        <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">Streaming vs Batch</h1>
              <p>Compare low-latency stream processing with scheduled batch analytics.</p>
            </div>
            <Button iconName="download" onClick={exportComparisonMetrics}>Export</Button>
          </div>
        </div>

        {isLoading ? <LoadingSpinner/> : (
          <>
            <div className="medstream-dashboard-split">
              <div className="medstream-stretch-container">
                <Container header={<Header variant="h2" description="Immediate event handling and low-latency alerting.">Streaming</Header>}>
                  <div className="medstream-comparison-metrics-grid">
                    <MetricCard
                      label="Streaming Latency"
                      value={formatLatencyDuration(streamingLatencyMs)}
                      hint="Event to alert processing time"
                    />
                    <MetricCard
                      label="Streaming Execution Time"
                      value={formatLatencyDuration(streamingExecutionTimeMs)}
                      hint="Time spent updating streaming metrics"
                    />
                    <MetricCard
                      label="Events per Second"
                      value={formatFixed(Number(data.events_per_second) || 0, 4)}
                      hint="Recent ingestion rate"
                    />
                  </div>
                </Container>
              </div>

              <div className="medstream-stretch-container">
                <Container header={<Header variant="h2" description="Periodic processing with delayed but broader analysis.">Batch</Header>}>
                  <div className="medstream-comparison-metrics-grid">
                    <MetricCard
                      label="Batch Latency"
                      value={`${formatFixed(batchLatencyMinutes, 2)} min`}
                      hint="Event to latest batch output"
                    />
                    <MetricCard
                      label="Batch Execution Time"
                      value={formatLatencyDuration(batchExecutionTimeMs)}
                      hint="Time spent running latest batch job"
                    />
                    <MetricCard
                      label="Alert Rate"
                      value={`${formatFixed(batchAlertRate * 100, 2)}%`}
                      hint="Batch alerts as share of batch events"
                    />
                  </div>
                </Container>
              </div>
            </div>

            <div className="medstream-comparison-snapshots-spacer">
              <SpaceBetween size="m">
                <Container
                  header={
                    <Header
                      variant="h2"
                      description="Streaming and batch values are stored by the backend sampler, using comparable alerts-per-minute rates."
                      actions={renderChartTimeRangeControl({
                        rangeValue: throughputChartTimeRange,
                        setRangeValue: setThroughputChartTimeRange,
                        rangeDraftValue: throughputCustomRangeDraft,
                        setRangeDraftValue: setThroughputCustomRangeDraft,
                        isOpen: isThroughputCustomRangeOpen,
                        setIsOpen: setIsThroughputCustomRangeOpen,
                        rangeRef: throughputCustomRangeRef,
                      })}
                    >
                      Streaming throughput vs batch runs
                    </Header>
                  }
                >
                  <div className="medstream-chart-panel medstream-throughput-chart-panel">
                    <AwsLineChart
                      ariaLabel="Streaming throughput vs batch runs"
                      data={visibleThroughputHistory}
                      highlightedSeriesTitle={highlightedThroughputSeries}
                      hideLegend
                      onHighlightedSeriesTitleChange={setHighlightedThroughputSeries}
                      series={THROUGHPUT_CHART_SERIES}
                      xTitle="Time"
                      yTitle=""
                      xTickFormatter={throughputXAxisTickFormatter}
                      yDomain={throughputChartYDomain}
                      yTickFormatter={(value) => String(Math.round(value))}
                    />
                  </div>
                </Container>
                <div
                  className="medstream-throughput-legend awsui_root_1kjc7_qgpiu_167"
                  role="toolbar"
                  aria-label="Legend"
                  onMouseLeave={() => setHighlightedThroughputSeries(null)}
                >
                  <div className="awsui_list_1kjc7_qgpiu_206">
                    {THROUGHPUT_CHART_SERIES.map((item, index) => {
                      const isHighlighted = highlightedThroughputSeries === item.title
                      const isDimmed = highlightedThroughputSeries && !isHighlighted

                      return (
                          <div
                            className={[
                              "awsui_marker_1kjc7_qgpiu_153",
                              "medstream-throughput-legend-item",
                              isHighlighted ? "awsui_marker--highlighted_1kjc7_qgpiu_255" : "",
                              isHighlighted ? "medstream-throughput-legend-item-active" : "",
                              isDimmed ? "awsui_marker--dimmed_1kjc7_qgpiu_252" : "",
                              isDimmed ? "medstream-throughput-legend-item-dimmed" : "",
                            ].filter(Boolean).join(" ")}
                          key={item.key}
                          role="button"
                          aria-pressed={isHighlighted}
                          tabIndex={index === 0 ? 0 : -1}
                          onBlur={() => setHighlightedThroughputSeries(null)}
                          onFocus={() => setHighlightedThroughputSeries(item.title)}
                          onMouseEnter={() => setHighlightedThroughputSeries(item.title)}
                        >
                          <span
                            className="awsui_marker_1isd1_1nqfm_145 awsui_marker--line_1isd1_1nqfm_185"
                            style={{backgroundColor: item.color}}
                            aria-hidden="true"
                          />
                          {" "}
                          {item.title}
                        </div>
                      )
                    })}
                  </div>
                </div>

                <Container
                  header={
                    <Header
                      variant="h2"
                      description="Average time from recorded event to streaming alert or latest batch output."
                      actions={renderChartTimeRangeControl({
                        rangeValue: latencyChartTimeRange,
                        setRangeValue: setLatencyChartTimeRange,
                        rangeDraftValue: latencyCustomRangeDraft,
                        setRangeDraftValue: setLatencyCustomRangeDraft,
                        isOpen: isLatencyCustomRangeOpen,
                        setIsOpen: setIsLatencyCustomRangeOpen,
                        rangeRef: latencyCustomRangeRef,
                      })}
                    >
                      Latency trend
                    </Header>
                  }
                >
                  <div className="medstream-comparison-chart-grid medstream-comparison-latency-grid">
                    <div
                      className={[
                        "medstream-chart-panel",
                        "medstream-latency-chart-panel",
                        highlightedStreamingLatencySeries ? "medstream-latency-chart-panel-active" : "",
                      ].filter(Boolean).join(" ")}
                      style={{"--medstream-latency-series-color": STREAMING_LATENCY_CHART_SERIES[0].color}}
                    >
                      <AwsLineChart
                        ariaLabel="Streaming latency"
                        data={visibleLatencyHistory}
                        height={280}
                        highlightedSeriesTitle={highlightedStreamingLatencySeries}
                        hideLegend
                        onHighlightedSeriesTitleChange={setHighlightedStreamingLatencySeries}
                        series={STREAMING_LATENCY_CHART_SERIES}
                        xTickFormatter={latencyXAxisTickFormatter}
                        xTitle="Time"
                        yDomain={streamingLatencyChartYDomain}
                        yTitle=""
                        yTickFormatter={(value) => formatLatencyAxisValue(Number(value) || 0, "ms")}
                      />
                      <div
                        className="medstream-latency-legend awsui_root_1kjc7_qgpiu_167"
                        role="toolbar"
                        aria-label="Streaming latency legend"
                        onMouseLeave={() => setHighlightedStreamingLatencySeries(null)}
                      >
                        <div className="awsui_list_1kjc7_qgpiu_206">
                          <div
                            className={[
                              "awsui_marker_1kjc7_qgpiu_153",
                              "medstream-latency-legend-item",
                              highlightedStreamingLatencySeries ? "awsui_marker--highlighted_1kjc7_qgpiu_255" : "",
                              highlightedStreamingLatencySeries ? "medstream-latency-legend-item-active" : "",
                            ].filter(Boolean).join(" ")}
                            role="button"
                            aria-pressed={Boolean(highlightedStreamingLatencySeries)}
                            tabIndex={0}
                            onBlur={() => setHighlightedStreamingLatencySeries(null)}
                            onFocus={() => setHighlightedStreamingLatencySeries(STREAMING_LATENCY_CHART_SERIES[0].title)}
                            onMouseEnter={() => setHighlightedStreamingLatencySeries(STREAMING_LATENCY_CHART_SERIES[0].title)}
                          >
                            <span
                              className="awsui_marker_1isd1_1nqfm_145 awsui_marker--line_1isd1_1nqfm_185"
                              style={{backgroundColor: STREAMING_LATENCY_CHART_SERIES[0].color}}
                              aria-hidden="true"
                            />
                            {" "}
                            {STREAMING_LATENCY_CHART_SERIES[0].title}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div
                      className={[
                        "medstream-chart-panel",
                        "medstream-latency-chart-panel",
                        highlightedBatchLatencySeries ? "medstream-latency-chart-panel-active" : "",
                      ].filter(Boolean).join(" ")}
                      style={{"--medstream-latency-series-color": BATCH_LATENCY_CHART_SERIES[0].color}}
                    >
                      <AwsLineChart
                        ariaLabel="Batch latency"
                        data={visibleLatencyHistory}
                        height={280}
                        highlightedSeriesTitle={highlightedBatchLatencySeries}
                        hideLegend
                        onHighlightedSeriesTitleChange={setHighlightedBatchLatencySeries}
                        series={BATCH_LATENCY_CHART_SERIES}
                        xTickFormatter={latencyXAxisTickFormatter}
                        xTitle="Time"
                        yDomain={batchLatencyChartYDomain}
                        yTitle=""
                        yTickFormatter={(value) => formatLatencyAxisValue(Number(value) || 0, "min")}
                      />
                      <div
                        className="medstream-latency-legend awsui_root_1kjc7_qgpiu_167"
                        role="toolbar"
                        aria-label="Batch latency legend"
                        onMouseLeave={() => setHighlightedBatchLatencySeries(null)}
                      >
                        <div className="awsui_list_1kjc7_qgpiu_206">
                          <div
                            className={[
                              "awsui_marker_1kjc7_qgpiu_153",
                              "medstream-latency-legend-item",
                              highlightedBatchLatencySeries ? "awsui_marker--highlighted_1kjc7_qgpiu_255" : "",
                              highlightedBatchLatencySeries ? "medstream-latency-legend-item-active" : "",
                            ].filter(Boolean).join(" ")}
                            role="button"
                            aria-pressed={Boolean(highlightedBatchLatencySeries)}
                            tabIndex={0}
                            onBlur={() => setHighlightedBatchLatencySeries(null)}
                            onFocus={() => setHighlightedBatchLatencySeries(BATCH_LATENCY_CHART_SERIES[0].title)}
                            onMouseEnter={() => setHighlightedBatchLatencySeries(BATCH_LATENCY_CHART_SERIES[0].title)}
                          >
                            <span
                              className="awsui_marker_1isd1_1nqfm_145 awsui_marker--line_1isd1_1nqfm_185"
                              style={{backgroundColor: BATCH_LATENCY_CHART_SERIES[0].color}}
                              aria-hidden="true"
                            />
                            {" "}
                            {BATCH_LATENCY_CHART_SERIES[0].title}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Container>
              </SpaceBetween>
            </div>
          </>
        )}
        </SpaceBetween>
      </div>
    </ContentLayout>
  )
}
