import json
import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from backend.app.core.config import CORS_ORIGINS
from backend.app.db.session import SessionLocal
from backend.app.api.routes import router
from backend.app.api.monitoring import router as monitoring_router
from backend.app.api.sessions import router as sessions_router
from backend.app.services.pipeline import load_engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("radar")
app = FastAPI(
    title="Explainable Fraud Radar",
    version="1.0.0",
    description="Synthetic financial decision support. Predictions are not verified fraud.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)
app.include_router(monitoring_router)
app.include_router(sessions_router)
request_count = 0
error_count = 0


@app.middleware("http")
async def request_context(request: Request, call_next):
    global request_count, error_count
    request.state.request_id = str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    request_count += 1
    error_count += int(response.status_code >= 500)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code, content={"error": {"message": exc.detail, "request_id": getattr(request.state, "request_id", None)}}
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Invalid request",
                "details": [{"location": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def internal_error(request, exc):
    logger.error(json.dumps({"request_id": getattr(request.state, "request_id", None), "error_type": type(exc).__name__}))
    return JSONResponse(
        status_code=500, content={"error": {"message": "Internal server error", "request_id": getattr(request.state, "request_id", None)}}
    )


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
            if not db.execute(text("SELECT version FROM model_versions WHERE active = true LIMIT 1")).first():
                return JSONResponse(status_code=503, content={"status": "needs_seed", "database": "connected"})
            model = load_engine(db)
            if model is None or not model.model_info().get("version"):
                return JSONResponse(status_code=503, content={"status": "model_unavailable"})
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return f"# TYPE radar_http_requests_total counter\nradar_http_requests_total {request_count}\n# TYPE radar_http_errors_total counter\nradar_http_errors_total {error_count}\n"
