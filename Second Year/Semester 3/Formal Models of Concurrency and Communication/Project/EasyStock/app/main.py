from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes import router as api_router
from app.data.db import init_db
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(title="EasyStock Library API")
UI_DIR = Path(__file__).resolve().parent / "ui"

@app.on_event("startup")
def startup_event() -> None:
    init_db()
    logging.getLogger(__name__).info("Database initialized")

@app.get("/")
def ui() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")

@app.get("/operations")
def operations_ui() -> FileResponse:
    return FileResponse(UI_DIR / "operations.html")

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

app.include_router(api_router, prefix="/api")
