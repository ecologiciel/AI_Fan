import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validate_runtime_security()
    configure_logging()
    yield


app = FastAPI(title="Football AI Fan Intelligence Platform", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_hardening(request: Request, call_next):  # type: ignore[no-untyped-def]
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > get_settings().max_request_bytes:
                return JSONResponse({"detail": "Request payload too large"}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length header"}, status_code=400)
    started = perf_counter()
    response = await call_next(request)
    logging.getLogger(__name__).info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((perf_counter() - started) * 1000),
        },
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(api_router)
