# MedStream

MedStream is a full-stack hospital monitoring demo for patient operations, live vital signs, clinical alerts, medical records, and streaming-versus-batch analytics.

The application is built around a doctor workflow: authenticate, manage assigned patients, monitor patient condition in real time, review clinical context, and compare immediate streaming signals with scheduled batch insights.

## Features

- Doctor registration, login, email verification, password reset, and account recovery.
- Doctor profile management, assigned patients, clinical activities, and account deactivation.
- Patient admission, editing, doctor assignment, department transfer, discharge, and readmission.
- Department views with patient filters and batch status context.
- Live monitoring for heart rate, oxygen saturation, temperature, and alert events.
- Clinical records for diagnoses, allergies, conditions, medication, admission history, and activities.
- Treatment analysis and post-discharge clinical summaries.
- Streaming metrics, batch metrics, comparison history, alert history, and manual batch runs.
- Background simulator that generates patients, vital signs, alerts, activities, transfers, and discharges for demo data.

## Tech Stack

| Area | Technologies |
| --- | --- |
| Frontend | React 19, Vite, React Router, Cloudscape Design, Recharts, Axios |
| Backend | FastAPI, SQLAlchemy, Pydantic, Uvicorn |
| Database | PostgreSQL |
| Streaming | Kafka, Confluent Kafka client, WebSocket |
| Batch processing | APScheduler, Python aggregation jobs |
| Local tooling | Docker Compose, pgAdmin, Kafka UI, MailCatcher |

## Architecture

```mermaid
flowchart LR
  Doctor["Doctor browser"] --> Frontend["React + Vite"]
  Frontend --> API["FastAPI REST API"]
  Frontend --> WS["WebSocket /ws"]
  API --> DB["PostgreSQL"]
  API --> Batch["Batch scheduler"]
  Simulator["Simulator"] --> Kafka["Kafka topics"]
  Kafka --> Consumer["Kafka consumer"]
  Consumer --> DB
  Consumer --> WS
  Batch --> DB
  API --> Mail["MailCatcher SMTP"]
```

The backend initializes the database schema from SQLAlchemy models, ensures Kafka topics exist, starts the Kafka consumer, starts the simulator, and schedules the batch job when the API starts.

## Project Structure

```text
MedStream/
  backend/
    app/
      api/              REST and WebSocket routes
      alerts/           vital-sign alert classification
      batch/            scheduler, runtime status, aggregation job
      core/             configuration, errors, shared HTTP response format
      db/               database setup and sessions
      helpers/          CSV source data for clinical options
      kafka/            topic setup, producer, consumer
      models/           SQLAlchemy models
      repositories/     data access layer
      schemas/          Pydantic request/response models
      service/          business logic
      simulator/        demo data generation
      validators/       domain validation helpers
  frontend/
    src/
      components/       reusable UI components
      hooks/            notification and patient-action hooks
      pages/            route pages
      services/         REST and WebSocket clients
      utils/            formatting and UI helpers
  docker-compose.yml
```

## Run Locally With Docker

Docker is the recommended setup because the app depends on PostgreSQL, Kafka, and MailCatcher.

```bash
docker compose up -d
```

Services:

| Service | URL |
| --- | --- |
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| pgAdmin | `http://localhost:5050` |
| Kafka UI | `http://localhost:8080` |
| MailCatcher | `http://localhost:1080` |
| PostgreSQL | `localhost:5432` |
| Kafka | `localhost:9092` |

Default pgAdmin credentials from `docker-compose.yml`:

```text
Email: admin@medstream.com
Password: admin123
```

Stop the stack:

```bash
docker compose down
```

Remove local database and tool volumes:

```bash
docker compose down -v
```

## Manual Development

Manual development still requires PostgreSQL, Kafka, and MailCatcher to be running locally or reachable through custom environment variables.

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Configuration

The backend reads environment variables from the project `.env` and `backend/.env`.

Important backend variables:

```env
DATABASE_URL=postgresql://medstream_user:medstream_pass@localhost:5432/medstream
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_VITALS_TOPIC=vitals-events
KAFKA_ALERTS_TOPIC=alerts-events
KAFKA_BATCH_TOPIC=batch-events
BATCH_INTERVAL_SECONDS=30
FRONTEND_BASE_URL=http://localhost:5173
SMTP_HOST=localhost
SMTP_PORT=1025
AUTH_SECRET_KEY=medstream-dev-auth-secret
AUTH_TOKEN_TTL_MINUTES=4320
HEART_RATE_ALERT_THRESHOLD=120
OXYGEN_ALERT_THRESHOLD=92
TEMPERATURE_ALERT_THRESHOLD=39
```

Frontend variables:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

For Docker Compose, container-specific values are already defined in `docker-compose.yml`.

## Main App Routes

| Route | Purpose |
| --- | --- |
| `/login`, `/register` | Doctor authentication and account creation |
| `/forgot-password`, `/reset-password`, `/recover-account` | Account recovery flows |
| `/dashboard` | Operational overview, patient status, and alert summary |
| `/departments`, `/departments/:name` | Department patient views and filters |
| `/patients/new` | Patient intake |
| `/patient/:id` | Live patient monitoring and patient actions |
| `/patients/:id/clinical-records` | Diagnoses, allergies, conditions, and medication |
| `/patients/:id/admission-history` | Admission, discharge, transfer, and readmission history |
| `/patients/:id/analysis` | Treatment analysis and clinical timeline |
| `/patients/:id/post-discharge-summary` | Batch-backed post-discharge summary |
| `/alerts` | Global alert feed and severity data |
| `/metrics/streaming` | Live streaming metrics |
| `/metrics/batch` | Batch analytics, schedule, status, and manual run controls |
| `/metrics/comparison` | Streaming and batch comparison |
| `/profile` | Current doctor profile, activities, and assignments |
| `/how-it-works` | Visual explanation of the data flow |

## Main API Areas

FastAPI documentation is available at `http://localhost:8000/docs` when the backend is running.

- Auth: `POST /login`, `POST /register`, `GET /auth/verify-email`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/recover-account`.
- Doctors: `/doctors`, `/doctors/me`, doctor activities, doctor-patient assignments, profile updates, and account deactivation.
- Patients: `/patients`, search, patient details, discharge, readmission, transfer, doctors, activities, clinical records, treatment analysis, and post-discharge summary.
- Clinical options: diagnoses, allergies, medications, dosages, conditions, activities, condition statuses, and discharge types.
- Monitoring: `/vitals`, `/alerts`, `/alerts/dashboard-summary`, `WS /ws`.
- Metrics: `/metrics/streaming`, `/metrics/batch`, `/metrics/batch-insights`, `/metrics/streaming-alerts`, `/metrics/comparison`, `/metrics/comparison-history`, `/metrics/batch-alerts-history`.
- Batch runtime: `/batch/status`, `/batch/schedule`, `POST /batch/schedule`, `POST /batch/run`.
- Health: `GET /health`.

## Streaming And Batch Behavior

Streaming handles fast operational signals. Vital-sign events are consumed from Kafka, saved to PostgreSQL, reflected in streaming metrics, and broadcast to the frontend through WebSocket.

Batch processing handles slower analysis. The scheduler aggregates historical data, refreshes batch snapshots, computes comparison metrics, and supports interval, daily, weekly, custom cron, and manual runs from the batch page.

Patient state thresholds used by the simulator:

| Signal | High / unstable | Critical |
| --- | --- | --- |
| Heart rate | `> 110` | `> 130` |
| Oxygen saturation | `< 92` | `< 88` |
| Temperature | `> 38` | `> 39` |

Configurable alert thresholds are also available through environment variables for heart rate, oxygen, and temperature.

## Quality Checks

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Development Notes

- This is a demo/portfolio application, not a production clinical system.
- Simulator data is synthetic and must not be treated as real medical data.
- `init_db()` creates tables directly from models; use migrations such as Alembic before running this pattern in long-lived environments.
- CORS is open for local development.
- Change `AUTH_SECRET_KEY` outside local development.
- MailCatcher is for local email testing only.
