import {useEffect, useState} from "react"
import {
  Box,
  Button,
  Container,
  ContentLayout,
  Header,
  Pagination,
  SpaceBetween,
  StatusIndicator,
} from "@cloudscape-design/components"
import {
  getMetricsComparison,
  getMetricsComparisonHistory,
  getStreamingAlerts,
  getStreamingMetrics,
} from "../services/patientApi.js"
import {getErrorMessage, getResponseData} from "../services/apiMessages.js"
import {downloadCSV} from "../utils/downloadCSV.js"
import {useNotifications} from "../hooks/useNotifications.js"
import AwsLineChart from "../components/AwsLineChart.jsx"
import AppBreadcrumbs from "../components/AppBreadcrumbs.jsx"
import LoadingSpinner from "../components/LoadingSpinner.jsx"
import {formatBucharestTime} from "../utils/time.js"

const POLL_INTERVAL_MS = 2500
const MAX_POINTS = 30
const MAX_ALERT_RATE_POINTS = 900
const ALERTS_HISTORY_SECONDS = 60 * 60
const ALERTS_PAGE_SIZE = 2

const VITAL_STREAMS = [
  {
    key: "heart_rate",
    avgKey: "avg_heart_rate",
    title: "Heart Rate",
    color: "#60a5fa",
    unit: "bpm",
    yDomain: [40, 150],
    thresholds: [
      {title: "High > 110", y: 110, color: "#f97316"},
      {title: "Critical > 130", y: 130, color: "#dc2626"},
    ],
    valueFormatter: (value) => `${value.toFixed(0)} bpm`,
    yTickFormatter: (value) => String(Math.round(value)),
  },
  {
    key: "oxygen_saturation",
    avgKey: "avg_oxygen",
    title: "Oxygen Saturation",
    color: "#22c55e",
    unit: "%",
    yDomain: [84, 100],
    thresholds: [
      {title: "Low < 92", y: 92, color: "#f97316"},
      {title: "Critical < 88", y: 88, color: "#dc2626"},
    ],
    valueFormatter: (value) => `${value.toFixed(0)}%`,
    yTickFormatter: (value) => String(Math.round(value)),
  },
  {
    key: "temperature",
    avgKey: "avg_temperature",
    title: "Temperature",
    color: "#f97316",
    unit: "°C",
    yDomain: [35, 40],
    thresholds: [
      {title: "High > 38", y: 38, color: "#f97316"},
      {title: "Critical > 39", y: 39, color: "#dc2626"},
    ],
    valueFormatter: (value) => `${value.toFixed(1)}°C`,
    yTickFormatter: (value) => value.toFixed(1),
  },
]

function formatMetric(value, unit = "") {
  const safeValue = Number.isFinite(value) ? value : 0
  return `${safeValue.toFixed(2)}${unit}`
}

function MetricTile({label, value}) {
  return (
    <div className="medstream-streaming-summary-tile">
      <Box color="text-body-secondary" variant="awsui-key-label">{label}</Box>
      <div className="medstream-streaming-summary-value">{value}</div>
    </div>
  )
}

function formatAlertTime(value) {
  return formatBucharestTime(value, "Unknown time")
}

function formatStreamTime(value, fallback = "") {
  if (!value) {
    return fallback
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return fallback
  }

  return formatBucharestTime(date, fallback)
}

function normalizeRecentVitals(rawVitals) {
  return (Array.isArray(rawVitals) ? rawVitals : [])
    .map((point) => ({
      time: formatStreamTime(point?.recorded_at),
      recorded_at: point?.recorded_at,
      patient_id: point?.patient_id,
      heart_rate: Number(point?.heart_rate),
      oxygen_saturation: Number(point?.oxygen_saturation),
      temperature: Number(point?.temperature),
    }))
    .filter((point) => (
      Number.isFinite(point.heart_rate)
      && Number.isFinite(point.oxygen_saturation)
      && Number.isFinite(point.temperature)
    ))
    .slice(-MAX_POINTS)
}

function normalizeAlertsRateHistory(rawPoints) {
  const normalizedPoints = (Array.isArray(rawPoints) ? rawPoints : [])
    .map((point) => {
      const timestampMs = new Date(point?.time_iso).getTime()
      const alertsPerMinute = Number(point?.streaming_alerts_per_minute)

      if (!Number.isFinite(timestampMs) || !Number.isFinite(alertsPerMinute)) {
        return null
      }

      return {
        time_iso: new Date(timestampMs).toISOString(),
        time: formatStreamTime(timestampMs),
        alerts_per_minute: alertsPerMinute,
        alerts_per_second: Number((alertsPerMinute / 60).toFixed(3)),
      }
    })
    .filter(Boolean)
    .sort((left, right) => new Date(left.time_iso).getTime() - new Date(right.time_iso).getTime())
    .slice(-MAX_ALERT_RATE_POINTS)

  return normalizedPoints.map((point, index) => {
    const previousPoint = normalizedPoints[index - 1]
    const previousAlertsPerMinute = Number(previousPoint?.alerts_per_minute)
    const newAlertsTick = Number.isFinite(previousAlertsPerMinute)
      ? Math.max(0, Number(point.alerts_per_minute) - previousAlertsPerMinute)
      : Number(point.alerts_per_minute)

    return {
      ...point,
      new_alerts_tick: newAlertsTick,
    }
  })
}

function getPaddedAlertsRateYMax(points) {
  const maxValue = Math.max(1, ...points.map((point) => Number(point.alerts_per_minute) || 0))
  return Math.ceil(maxValue + Math.max(1, maxValue * 0.1))
}

export default function StreamingMetricsPage() {
  const {notifyError} = useNotifications()
  const [metrics, setMetrics] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [alertsPage, setAlertsPage] = useState(1)
  const [recentAlerts, setRecentAlerts] = useState({items: [], total: 0, page: 1, page_size: ALERTS_PAGE_SIZE})
  const [vitalsHistory, setVitalsHistory] = useState([])
  const [alertsRateHistory, setAlertsRateHistory] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [highlightedAlertsRateSeries, setHighlightedAlertsRateSeries] = useState(null)
  const [highlightedVitalSeries, setHighlightedVitalSeries] = useState(null)

  useEffect(() => {
    let active = true
    let isFirstLoad = true

    const loadData = async () => {
      if (isFirstLoad) {
        setIsLoading(true)
      }
      try {
        const [metricsResponse, alertsResponse, comparisonResponse, comparisonHistoryResponse] = await Promise.all([
          getStreamingMetrics(),
          getStreamingAlerts(alertsPage, ALERTS_PAGE_SIZE),
          getMetricsComparison(),
          getMetricsComparisonHistory({
            seconds: ALERTS_HISTORY_SECONDS,
            interval_seconds: Math.round(POLL_INTERVAL_MS / 1000),
          }),
        ])

        if (!active) {
          return
        }

        const nextMetrics = getResponseData(metricsResponse)
        const nextAlerts = getResponseData(alertsResponse)
        const nextComparison = getResponseData(comparisonResponse)
        const comparisonHistory = getResponseData(comparisonHistoryResponse)
        setComparison(nextComparison || null)
        const totalPages = Math.max(1, Math.ceil((nextAlerts.total || 0) / ALERTS_PAGE_SIZE))

        if (alertsPage > totalPages) {
          setAlertsPage(totalPages)
          return
        }

        setMetrics(nextMetrics)
        setRecentAlerts(nextAlerts)

        const tickTime = formatBucharestTime(new Date())
        const nextVitalHistory = normalizeRecentVitals(nextMetrics.recent_vitals)

        if (nextVitalHistory.length) {
          setVitalsHistory(nextVitalHistory)
        } else {
          setVitalsHistory((current) => [
            ...current.slice(-(MAX_POINTS - 1)),
            {
              time: tickTime,
              heart_rate: nextMetrics.avg_heart_rate,
              oxygen_saturation: nextMetrics.avg_oxygen,
              temperature: nextMetrics.avg_temperature,
            },
          ])
        }
        setAlertsRateHistory(normalizeAlertsRateHistory(comparisonHistory?.throughput))
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
  }, [alertsPage, notifyError])

  const data = metrics ?? {
    avg_heart_rate: 0,
    avg_oxygen: 0,
    avg_temperature: 0,
    alerts: 0,
    execution_time_ms: 0,
    recent_vitals: [],
  }

  const latestRatePoint = alertsRateHistory[alertsRateHistory.length - 1] || {
    alerts_per_second: 0,
    alerts_per_minute: 0,
    new_alerts_tick: 0,
  }

  const alertsTotalPages = Math.max(1, Math.ceil((recentAlerts.total || 0) / ALERTS_PAGE_SIZE))
  const alertsRateYMax = getPaddedAlertsRateYMax(alertsRateHistory)

  const exportStreamingMetrics = () => {
    const exportTimestamp = new Date().toISOString()
    const totalEvents = Number(comparison?.total_events) || 0
    const totalAlerts = Number(comparison?.total_alerts) || Number(data.alerts) || 0
    const alertsPerSecond = Number(comparison?.events_per_second) > 0
      ? (Number(comparison?.alert_rate) || 0) * Number(comparison?.events_per_second)
      : Number(latestRatePoint.alerts_per_second) || 0
    const alertsPerMinute = alertsPerSecond * 60
    const alertRate = totalEvents > 0 ? totalAlerts / totalEvents : 0
    const streamingLatencyAvgMs = Number(comparison?.streaming_latency_avg) || 0
    const rows = [
      [
        "timestamp",
        "total_events",
        "total_alerts",
        "alerts_per_second",
        "alerts_per_minute",
        "alert_rate",
        "streaming_latency_avg_ms",
      ],
      [
        exportTimestamp,
        totalEvents,
        totalAlerts,
        Number(alertsPerSecond.toFixed(4)),
        Number(alertsPerMinute.toFixed(2)),
        Number(alertRate.toFixed(4)),
        Number(streamingLatencyAvgMs.toFixed(2)),
      ],
      [],
      ["recent_alert_id", "recent_alert_patient_id", "recent_alert_type", "recent_alert_severity", "recent_alert_message", "recent_alert_created_at"],
      ...(recentAlerts.items || []).map((alert) => [
        alert.id,
        alert.patient_id,
        alert.alert_type,
        alert.severity,
        alert.message,
        alert.created_at ? new Date(alert.created_at).toISOString() : "",
      ]),
    ]
    downloadCSV("streaming_all_metrics.csv", rows)
  }

  const exportVitalStreams = () => {
    const exportTimestamp = new Date().toISOString()
    const summaryRows = VITAL_STREAMS.map((vital) => {
      const values = vitalsHistory
        .map((point) => Number(point?.[vital.key]))
        .filter(Number.isFinite)
      const latestValue = values[values.length - 1]
      const averageValue = values.length
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : Number(data[vital.avgKey]) || 0

      return [
        vital.title,
        vital.unit,
        Number.isFinite(latestValue) ? Number(latestValue.toFixed(2)) : "",
        Number(averageValue.toFixed(2)),
        values.length ? Number(Math.min(...values).toFixed(2)) : "",
        values.length ? Number(Math.max(...values).toFixed(2)) : "",
        vital.thresholds.map((threshold) => threshold.title).join("; "),
        vitalsHistory.length,
      ]
    })

    const historyRows = vitalsHistory.map((point) => [
      point.recorded_at || point.time || "",
      point.patient_id || "",
      Number.isFinite(Number(point.heart_rate)) ? Number(Number(point.heart_rate).toFixed(2)) : "",
      Number.isFinite(Number(point.oxygen_saturation)) ? Number(Number(point.oxygen_saturation).toFixed(2)) : "",
      Number.isFinite(Number(point.temperature)) ? Number(Number(point.temperature).toFixed(2)) : "",
    ])

    downloadCSV("streaming_vital_streams.csv", [
      ["exported_at", exportTimestamp],
      [],
      ["metric", "unit", "latest", "average", "minimum", "maximum", "alert_thresholds", "visible_points"],
      ...summaryRows,
      [],
      ["timestamp", "patient_id", "heart_rate_bpm", "oxygen_saturation_percent", "temperature_celsius"],
      ...historyRows,
    ])
  }

  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <AppBreadcrumbs/>
          <div className="medstream-page-heading-row">
            <div>
              <h1 className="medstream-page-title">Streaming Alert Processing</h1>
              <p>Live alert throughput, recent alerts, and low-latency vital trends.</p>
            </div>
            <Button iconName="download" onClick={exportStreamingMetrics}>Export</Button>
          </div>
        </div>

        {isLoading ? (
          <LoadingSpinner/>
        ) : (
          <Container>
            <div className="medstream-streaming-summary-grid">
              <MetricTile label="Alerts per Second" value={formatMetric(latestRatePoint.alerts_per_second)}/>
              <MetricTile label="Alerts per Minute" value={formatMetric(latestRatePoint.alerts_per_minute)}/>
              <MetricTile label="New Alerts (last tick)" value={String(latestRatePoint.new_alerts_tick ?? 0)}/>
              <MetricTile label="Live Alerts (window)" value={String(data.alerts ?? 0)}/>
              <MetricTile label="Avg Heart Rate" value={formatMetric(data.avg_heart_rate, " bpm")}/>
              <MetricTile label="Execution Time" value={formatMetric(data.execution_time_ms, " ms")}/>
            </div>
          </Container>
        )}

        {!isLoading && (
          <>
            <div className="medstream-dashboard-split">
              <div className="medstream-stretch-container">
                <Container
                  className="medstream-streaming-card"
                  fitHeight
                  header={
                    <Header
                      variant="h2"
                      description="Alerts are appended with their metric, severity, patient, and processing time."
                    >
                      Generated alert timeline
                    </Header>
                  }
                >
                  <SpaceBetween size="xs">
                  {recentAlerts.items?.length ? recentAlerts.items.map((alert) => (
                    <Container key={alert.id} fitHeight>
                      <SpaceBetween size="xxs">
                        <Box variant="small">
                          <StatusIndicator type={alert.severity === "critical" ? "error" : alert.severity === "high" ? "warning" : "success"}>
                            {alert.severity}
                          </StatusIndicator>
                        </Box>
                        <Box variant="small">{alert.message}</Box>
                        <Box color="text-body-secondary" variant="small">
                            {alert.alert_type} | Patient ID: {alert.patient_id} | {formatAlertTime(alert.created_at)}
                        </Box>
                      </SpaceBetween>
                    </Container>
                  )) : (
                    <Box color="text-body-secondary">No alerts in the current feed.</Box>
                  )}
                  </SpaceBetween>

                  <div className="medstream-pagination-end medstream-pagination-end-medium">
                  <Pagination
                    currentPageIndex={recentAlerts.page || 1}
                    pagesCount={alertsTotalPages}
                    onChange={({detail}) => setAlertsPage(detail.currentPageIndex)}
                  />
                  </div>
                </Container>
              </div>

              <div className="medstream-stretch-container">
                <div className="medstream-alerts-rate-stack">
                  <Container
                    className="medstream-streaming-card"
                    fitHeight
                    header={
                      <Header variant="h2" description="Stored by the backend sampler from alerts in a rolling 60-second window.">
                        Alerts per minute
                      </Header>
                    }
                  >
                    <div
                      className={[
                        "medstream-chart-panel medstream-alerts-rate-chart-panel",
                        highlightedAlertsRateSeries === "Alerts/Minute" ? "medstream-alerts-rate-chart-panel-active" : "",
                      ].filter(Boolean).join(" ")}
                    >
                      <AwsLineChart
                        ariaLabel="Alerts per minute"
                        data={alertsRateHistory}
                        highlightedSeriesTitle={highlightedAlertsRateSeries}
                        hideLegend
                        onHighlightedSeriesTitleChange={setHighlightedAlertsRateSeries}
                        series={[
                          {key: "alerts_per_minute", title: "Alerts/Minute", color: "#f97316", valueFormatter: (value) => `${value.toFixed(0)}`},
                        ]}
                        xTitle="Time"
                        yDomain={[0, alertsRateYMax]}
                        yTickFormatter={(value) => String(Math.round(value))}
                      />
                    </div>
                    <div
                      className="medstream-alerts-rate-legend"
                      role="toolbar"
                      aria-label="Legend"
                      onMouseLeave={() => setHighlightedAlertsRateSeries(null)}
                    >
                      <button
                        className={[
                          "medstream-alerts-rate-legend-item",
                          highlightedAlertsRateSeries === "Alerts/Minute" ? "medstream-alerts-rate-legend-item-active" : "",
                        ].filter(Boolean).join(" ")}
                        type="button"
                        aria-pressed={highlightedAlertsRateSeries === "Alerts/Minute"}
                        onBlur={() => setHighlightedAlertsRateSeries(null)}
                        onFocus={() => setHighlightedAlertsRateSeries("Alerts/Minute")}
                        onMouseEnter={() => setHighlightedAlertsRateSeries("Alerts/Minute")}
                      >
                        <span className="medstream-alerts-rate-legend-line" aria-hidden="true"/>
                        Alerts/Minute
                      </button>
                    </div>
                  </Container>
                </div>
              </div>
            </div>

            <div className="medstream-streaming-vitals-spacer">
              <Container
                className="medstream-streaming-vitals-card"
                header={
                  <Header
                    variant="h2"
                    description="Each stream uses its own clinical scale and alert thresholds, so changes are visible as events arrive."
                    actions={<Button iconName="download" onClick={exportVitalStreams}>Export metrics</Button>}
                  >
                    Vital streams by alert rule
                  </Header>
                }
              >
                <div className="medstream-streaming-vitals-grid">
                  {VITAL_STREAMS.map((vital) => {
                    const latestPoint = vitalsHistory[vitalsHistory.length - 1]
                    const latestValue = Number(latestPoint?.[vital.key])
                    const fallbackValue = Number(data[vital.avgKey])
                    const displayValue = Number.isFinite(latestValue) ? latestValue : fallbackValue

                    return (
                      <section className="medstream-streaming-vital-panel" key={`${vital.key}-panel`} aria-label={`${vital.title} stream`}>
                        <div className="medstream-streaming-vital-panel-header">
                          <div>
                            <Box color="text-body-secondary" variant="awsui-key-label">{vital.title}</Box>
                            <div className="medstream-streaming-vital-value">
                              {Number.isFinite(displayValue) ? vital.valueFormatter(displayValue) : "--"}
                            </div>
                          </div>
                        </div>
                        <div className="medstream-streaming-vital-rules" aria-label={`${vital.title} alert rules`}>
                          {vital.thresholds.map((threshold) => (
                            <span key={threshold.title} style={{"--medstream-rule-color": threshold.color}}>
                              {threshold.title}
                            </span>
                          ))}
                        </div>
                        <div
                          className={[
                            "medstream-streaming-vital-chart",
                            highlightedVitalSeries === vital.title ? "medstream-streaming-vital-chart-active" : "",
                          ].filter(Boolean).join(" ")}
                          style={{"--medstream-vital-series-color": vital.color}}
                        >
                          <AwsLineChart
                            ariaLabel={`${vital.title} streaming trend`}
                            data={vitalsHistory}
                            height={190}
                            highlightedSeriesTitle={highlightedVitalSeries === vital.title ? vital.title : null}
                            hideLegend
                            onHighlightedSeriesTitleChange={setHighlightedVitalSeries}
                            series={[
                              {
                                key: vital.key,
                                title: vital.title,
                                color: vital.color,
                                valueFormatter: vital.valueFormatter,
                              },
                            ]}
                            thresholds={vital.thresholds}
                            xTitle="Time"
                            yDomain={vital.yDomain}
                            yTickFormatter={vital.yTickFormatter}
                            yTitle={vital.unit}
                          />
                        </div>
                      </section>
                    )
                  })}
                </div>
                <div
                  className="medstream-alerts-rate-legend medstream-streaming-vitals-legend"
                  role="toolbar"
                  aria-label="Legend"
                  onMouseLeave={() => setHighlightedVitalSeries(null)}
                >
                  {VITAL_STREAMS.map((vitalItem) => (
                    <button
                      className={[
                        "medstream-alerts-rate-legend-item",
                        highlightedVitalSeries === vitalItem.title ? "medstream-alerts-rate-legend-item-active" : "",
                      ].filter(Boolean).join(" ")}
                      key={vitalItem.key}
                      type="button"
                      aria-pressed={highlightedVitalSeries === vitalItem.title}
                      onBlur={() => setHighlightedVitalSeries(null)}
                      onFocus={() => setHighlightedVitalSeries(vitalItem.title)}
                      onMouseEnter={() => setHighlightedVitalSeries(vitalItem.title)}
                    >
                      <span
                        className="medstream-alerts-rate-legend-line"
                        style={{backgroundColor: vitalItem.color}}
                        aria-hidden="true"
                      />
                      {vitalItem.title}
                    </button>
                  ))}
                </div>
              </Container>
            </div>
          </>
        )}
      </SpaceBetween>
    </ContentLayout>
  )
}
