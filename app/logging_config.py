import logging
import time

from fastapi import Request

logger = logging.getLogger("kyomei_api")


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    client_ip = request.client.host if request.client else "-"
    logger.info(
        "%s %s %s %.1fms client=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        client_ip,
    )
    return response
