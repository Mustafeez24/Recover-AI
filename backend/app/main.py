import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.recovery import router as recovery_router
from app.core.config import settings

logger = logging.getLogger("recoverai")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Catches anything that isn't already an HTTPException (those keep
    # FastAPI's normal handling). Prevents raw tracebacks/exception text
    # from ever reaching a client in production.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )


app.include_router(health_router)
app.include_router(data_router)
app.include_router(recovery_router)


@app.get("/")
def root():
    return {"service": settings.app_name, "status": "running"}
