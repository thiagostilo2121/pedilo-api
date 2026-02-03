from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, categorias, negocios, pedidos, productos, public, suscripciones
from app.api.middleware import LoggingMiddleware
from app.core.database import create_db_and_tables
from app.core.exceptions import PediloException, EntityNotFoundError, BusinessLogicError, PermissionDeniedError


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Pedilo API",
    description="Backend del sistema Pedilo - pedidos online sin comisiones",
    version="0.1.0",
    lifespan=lifespan,
)

@app.exception_handler(EntityNotFoundError)
async def entity_not_found_exception_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})

@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    return JSONResponse(status_code=400, content={"detail": exc.message})

@app.exception_handler(PermissionDeniedError)
async def permission_denied_exception_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(status_code=403, content={"detail": exc.message})

app.add_middleware(LoggingMiddleware)

app.include_router(negocios.router)
app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(pedidos.router)
app.include_router(public.router)
app.include_router(categorias.router)
app.include_router(suscripciones.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
