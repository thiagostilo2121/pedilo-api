import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Simple logging configuration (Esto fue hecho por GEMINI 3 FLASH Planning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pedilo-api")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Process Time: {process_time:.4f}s"
        )
        
        return response
