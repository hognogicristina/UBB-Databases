from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "MedStream API"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_vitals_topic: str = "vitals-events"
    kafka_alerts_topic: str = "alerts-events"
    kafka_batch_topic: str = "batch-events"
    batch_interval_seconds: int = 30
    metrics_sample_interval_seconds: int = 4
    metrics_sample_retention_hours: int = 6
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_pass: str = ""
    frontend_base_url: str = "http://localhost:5173"
    auth_secret_key: str = "medstream-dev-auth-secret"
    auth_token_ttl_minutes: int = 4320

    heart_rate_alert_threshold: int = 120
    oxygen_alert_threshold: int = 92
    temperature_alert_threshold: int = 39

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_DIR / ".env",
            BACKEND_DIR / ".env",
        ),
        extra="ignore",
    )


settings = Settings()
