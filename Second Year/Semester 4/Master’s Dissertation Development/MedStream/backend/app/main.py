from contextlib import asynccontextmanager
from time import perf_counter
import threading
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.alerts import router as alerts_router
from app.api.batch import router as batch_router
from app.api.conditions import router as conditions_router
from app.api.doctors import auth_router, router as doctors_router
from app.api.medications import router as medications_router
from app.api.metrics import router as metrics_router
from app.api.patients import option_router, router as patients_router
from app.api.departments import router as departments_router
from app.api.stats import router as stats_router
from app.api.vitals import router as vitals_router
from app.api.ws import router as ws_router
from app.batch.patient_stats_job import run as run_batch
from app.batch.runtime import batch_runtime_controller
from app.batch.status import batch_status_store, utc_now
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.kafka.consumer import run as run_consumer
from app.kafka.topics import ensure_topics
from app.service.metrics import refresh_batch_snapshot
from app.service.metrics_sampler import metrics_sampler_controller
from app.simulator.run_simulator import run as run_simulator

background_threads_started = False
background_threads_lock = threading.Lock()


def execute_batch_job():
    started_at = utc_now()
    batch_status_store.mark_started(started_at, batch_runtime_controller.next_run_time(), "Loading data")

    try:
        duration_started_at = perf_counter()
        batch_status_store.mark_progress(10, "Loading data")
        batch_status_store.mark_progress(40, "Aggregating vitals")
        run_batch()
        batch_status_store.mark_progress(70, "Computing insights")
        duration_ms = round((perf_counter() - duration_started_at) * 1000, 2)
        with SessionLocal() as db:
            refresh_batch_snapshot(db, duration_ms)
        batch_status_store.mark_progress(90, "Finalizing")
        finished_at = utc_now()
        batch_status_store.mark_success(finished_at, batch_runtime_controller.next_run_time(), duration_ms)
    except Exception as error:
        print("Batch error:", error)
        finished_at = utc_now()
        duration_ms = round((perf_counter() - duration_started_at) * 1000, 2)
        batch_status_store.mark_failure(finished_at, error, batch_runtime_controller.next_run_time(), duration_ms)


def start_background_threads(app: FastAPI):
    global background_threads_started

    with background_threads_lock:
        if background_threads_started:
            return

        threading.Thread(target=run_consumer, args=(app.state.loop,), daemon=True, name="medstream-consumer").start()
        threading.Thread(target=run_simulator, daemon=True, name="medstream-simulator").start()
        batch_runtime_controller.start(execute_batch_job, settings.batch_interval_seconds)
        metrics_sampler_controller.start()
        background_threads_started = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.loop = asyncio.get_running_loop()
    init_db()
    ensure_topics()
    start_background_threads(app)
    yield
    metrics_sampler_controller.shutdown()
    batch_runtime_controller.shutdown()


app = FastAPI(title="MedStream", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_error_message(detail) -> str:
    if isinstance(detail, str) and detail.strip():
        return detail

    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message.strip():
            return message

    return "Unexpected error occurred"


def format_validation_error(exc: RequestValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = [str(item) for item in first_error.get("loc", []) if item != "body"]
    location_label = " ".join(location).replace("_", " ").strip().capitalize()
    message = first_error.get("msg", "Unexpected error occurred")

    if message == "Field required":
        return f"{location_label or 'Field'} is required."

    return message


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": extract_error_message(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": format_validation_error(exc),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Unexpected error occurred",
        },
    )


app.include_router(patients_router)
app.include_router(option_router)
app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(conditions_router)
app.include_router(medications_router)
app.include_router(vitals_router)
app.include_router(alerts_router)
app.include_router(ws_router)
app.include_router(stats_router)
app.include_router(departments_router)
app.include_router(metrics_router)
app.include_router(batch_router)


@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request):
    return Response(status_code=200)


@app.get("/health")
def health():
    return {
        "success": True,
        "message": "Service is healthy.",
        "data": {"status": "ok"},
    }
