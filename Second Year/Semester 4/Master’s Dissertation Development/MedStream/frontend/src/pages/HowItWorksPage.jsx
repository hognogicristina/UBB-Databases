import {
  Box,
  ColumnLayout,
  Container,
  ContentLayout,
  Header,
  SpaceBetween,
  Tabs,
} from "@cloudscape-design/components"

const streamingCards = [
  {
    title: "What you are seeing",
    items: [
      "Live averages updated every few seconds",
      "A continuously updating heart rate trend",
      "A real-time alert feed triggered by abnormal values",
      "Execution time of streaming computations",
    ],
  },
  {
    title: "Why streaming processing matters",
    items: [
      "Enables immediate detection of critical conditions",
      "Supports real-time monitoring systems, such as ICU dashboards",
      "Allows instant reaction to anomalies and alerts",
    ],
  },
  {
    title: "Technical flow",
    items: [
      "Data is produced continuously by simulated sensors or real inputs",
      "Events are sent through a streaming platform such as Kafka",
      "A streaming processor consumes and processes events in real time",
      "Alerts are generated instantly when thresholds are exceeded",
      "Results are exposed through APIs and refreshed in the UI every few seconds",
    ],
  },
  {
    title: "Trade-offs",
    items: [
      "Very low latency with near instant updates",
      "Higher variability because values may fluctuate",
      "Less suitable for deep historical analysis",
      "More complex infrastructure because event streaming systems are required",
    ],
  },
]

const batchCards = [
  {
    title: "What you are seeing",
    items: [
      "Aggregated metrics computed over a time window",
      "Stable averages across multiple patients",
      "Reduced noise compared with real-time values",
      "Summary insights derived from historical data",
    ],
  },
  {
    title: "Why batch processing matters",
    items: [
      "Provides more accurate and consistent results",
      "Enables long-term trend analysis",
      "Helps evaluate treatment effectiveness",
      "Supports reporting and decision-making",
    ],
  },
  {
    title: "Technical flow",
    items: [
      "Data is collected over time from the streaming layer",
      "Events are accumulated into a dataset",
      "Batch jobs process the dataset periodically",
      "Metrics and insights are computed",
      "Results are exposed through APIs and visualized in the dashboard",
    ],
  },
  {
    title: "Trade-offs",
    items: [
      "Higher latency because results are delayed",
      "More stable and reliable outputs",
      "Better suited for analytics than live monitoring",
      "Requires scheduled execution",
    ],
  },
]

const comparisonCards = [
  {
    title: "Streaming processing",
    items: [
      "Processes data immediately as it arrives",
      "Very low latency with near-instant updates",
      "Values fluctuate more due to real-time noise",
      "Ideal for alerts and monitoring",
    ],
  },
  {
    title: "Batch processing",
    items: [
      "Processes data periodically, for example every few minutes",
      "Higher latency but more stable results",
      "Aggregates larger datasets",
      "Ideal for analytics and reporting",
    ],
  },
  {
    title: "Key insight",
    items: [
      "Streaming prioritizes speed",
      "Batch prioritizes accuracy",
      "Difference values show how real-time metrics can deviate from aggregated results",
      "The two layers complement each other rather than replacing each other",
    ],
  },
]

function BulletList({items}) {
  return (
    <ul className="medstream-how-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

function ExplanationGrid({cards, variant = "default"}) {
  return (
    <div className={`medstream-how-grid ${variant === "comparison" ? "medstream-how-grid-comparison" : ""}`}>
      {cards.map((card, index) => (
        <div
          key={card.title}
          className={variant === "comparison" && index === cards.length - 1 ? "medstream-how-card-wide" : "medstream-how-card"}
        >
          <Container header={<Header variant="h3">{card.title}</Header>}>
            <BulletList items={card.items}/>
          </Container>
        </div>
      ))}
    </div>
  )
}

export default function HowItWorksPage() {
  return (
    <ContentLayout>
      <SpaceBetween size="m">
        <div className="medstream-page-header">
          <h1 className="medstream-page-title">How it works</h1>
          <p>Architecture and processing logic behind streaming, batch analytics, and their comparison.</p>
        </div>

        <Container>
          <ColumnLayout columns={3} variant="text-grid">
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Streaming layer</Box>
              <Box variant="h3">Real-time monitoring</Box>
              <Box color="text-body-secondary">Low-latency vitals ingestion, alerting, and live clinical visibility.</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Batch layer</Box>
              <Box variant="h3">Periodic analytics</Box>
              <Box color="text-body-secondary">Stable aggregated metrics, deeper insight, and reporting support.</Box>
            </SpaceBetween>
            <SpaceBetween size="xs">
              <Box color="text-body-secondary" variant="awsui-key-label">Comparison layer</Box>
              <Box variant="h3">Speed vs accuracy</Box>
              <Box color="text-body-secondary">Direct evaluation of responsiveness against aggregated reliability.</Box>
            </SpaceBetween>
          </ColumnLayout>
        </Container>

        <Tabs
          tabs={[
            {
              id: "streaming",
              label: "Streaming",
              content: (
                <SpaceBetween size="m">
                  <Container header={<Header variant="h2">Streaming processing</Header>}>
                    <SpaceBetween size="s">
                      <Box color="text-body-secondary">
                        This layer processes patient vitals immediately as they are generated, without waiting for accumulation.
                        Heart rate, oxygen saturation, and temperature are continuously ingested, analyzed, and displayed in near real time.
                      </Box>
                      <Box color="text-body-secondary">
                        The purpose is instant visibility into patient condition and fast escalation when abnormal thresholds are exceeded.
                      </Box>
                    </SpaceBetween>
                  </Container>
                  <ExplanationGrid cards={streamingCards}/>
                </SpaceBetween>
              ),
            },
            {
              id: "batch",
              label: "Batch analytics",
              content: (
                <SpaceBetween size="m">
                  <Container header={<Header variant="h2">Batch processing</Header>}>
                    <SpaceBetween size="s">
                      <Box color="text-body-secondary">
                        This layer collects data over time and processes it in scheduled intervals rather than instantly.
                        Instead of reacting to each event individually, it aggregates data across patients and time windows.
                      </Box>
                      <Box color="text-body-secondary">
                        The purpose is to generate more stable, reliable, and academically useful insights from historical data.
                      </Box>
                    </SpaceBetween>
                  </Container>
                  <ExplanationGrid cards={batchCards}/>
                </SpaceBetween>
              ),
            },
            {
              id: "comparison",
              label: "Streaming vs Batch",
              content: (
                <SpaceBetween size="m">
                  <Container header={<Header variant="h2">Streaming vs Batch</Header>}>
                    <SpaceBetween size="s">
                      <Box color="text-body-secondary">
                        The comparison uses the same patient data to show how real-time and periodic processing behave differently.
                        Streaming processes events instantly, while batch processes accumulated data over a time window.
                      </Box>
                      <Box color="text-body-secondary">
                        Streaming is fast and responsive. Batch is slower but more stable and more appropriate for historical analytics.
                      </Box>
                    </SpaceBetween>
                  </Container>
                  <ExplanationGrid cards={comparisonCards} variant="comparison"/>
                </SpaceBetween>
              ),
            },
          ]}
        />
      </SpaceBetween>
    </ContentLayout>
  )
}
