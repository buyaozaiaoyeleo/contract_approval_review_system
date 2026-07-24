"""Global exception handlers."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.response import ApiResponse
from app.core.exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-defined exceptions with unified payloads."""
    trace_id = getattr(request.state, "trace_id", "")
    logger.bind(trace_id=trace_id).warning(
        "Business exception | type={} | code={} | message={}",
        exc.__class__.__name__,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(
            code=exc.code,
            message=exc.message,
            trace_id=trace_id,
            data=exc.detail,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTP exceptions."""
    trace_id = getattr(request.state, "trace_id", "")
    logger.bind(trace_id=trace_id).warning(
        "HTTP exception | status={} | detail={}",
        exc.status_code,
        str(exc.detail),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(
            code=exc.status_code * 100,
            message=str(exc.detail),
            trace_id=trace_id,
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    trace_id = getattr(request.state, "trace_id", "")
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"]})

    logger.bind(trace_id=trace_id).warning(
        "Validation failed | errors={}",
        errors,
    )
    return JSONResponse(
        status_code=422,
        content=ApiResponse.error(
            code=42200,
            message="请求参数校验失败",
            trace_id=trace_id,
            data=errors,
        ).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    trace_id = getattr(request.state, "trace_id", "")
    logger.bind(trace_id=trace_id).opt(exception=exc).error(
        "Unhandled exception | type={} | detail={}",
        exc.__class__.__name__,
        str(exc),
    )

    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(
            code=50000,
            message="服务内部错误，请联系管理员",
            trace_id=trace_id,
        ).model_dump(),
    )
