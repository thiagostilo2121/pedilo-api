# 🤖 AGENTS.md - AI Agent Guide for Pedilo Backend

This document provides essential context for AI agents working on the **Pedilo Backend API**.

---

## 📋 Project Overview

**Pedilo** is a commission-free online ordering platform for small businesses.

### 🧠 Backend Philosophy
AI Agents **MUST** strictly follow this philosophy:
- **`models/`**: Your Database. Contains SQLModel entities and relationships.
- **`schemas/`**: Your Templates. Pydantic models for request validation and response formatting.
- **`services/`**: Your Logic. All business logic and DB operations live here. **Routes must remain logic-free.**
- **`routes/`**: Your Endpoints. They only handle HTTP entry, call services, and return responses.
- **`core/`**: Your Config. Centralized settings, security, and global exceptions.
- **`utils/`**: Your Tools. Small, reusable utility functions (Cloudinary, helpers).

- **Tech Stack**: FastAPI + SQLModel + PostgreSQL/SQLite
- **Language**: Python 3.10+
- **Auth**: JWT with Argon2 password hashing
- **Integrations**: Cloudinary (images), MercadoPago (subscriptions)

---

## 🏗️ Project Structure

```
app/
├── api/                    # Presentation layer
│   ├── routes/             # REST endpoints (auth, negocios, productos, etc.)
│   ├── deps.py             # Dependency injection (DB sessions, current user)
│   └── middleware.py       # Custom middleware (logging, CORS)
├── core/                   # Core configuration
│   ├── config.py           # Settings using pydantic-settings
│   ├── database.py         # SQLModel engine and session
│   ├── security.py         # JWT tokens + Argon2 hashing
│   └── exceptions.py       # Domain exceptions (not HTTP)
├── models/                 # Domain entities (SQLModel)
│   └── models.py           # Usuario, Negocio, Producto, Pedido, etc.
├── schemas/                # DTOs (Pydantic models for API I/O)
│   ├── usuario.py
│   ├── negocio.py
│   ├── producto.py
│   └── pedido.py
├── services/               # Business logic layer (DB operations)
│   ├── categoria_service.py
│   ├── producto_service.py
│   ├── pedido_service.py
│   └── suscripcion_service.py
├── utils/                  # Utilities
│   ├── cloudinary.py       # Image upload helper
│   └── utils.py            # General helpers
├── tests/                  # Automated tests (pytest)
│   ├── conftest.py         # DB fixtures and TestClient
│   ├── test_auth.py        # Authentication flows
│   └── test_public.py      # Public endpoints
└── main.py                 # FastAPI app initialization
```

---

## 🎯 Key Architectural Decisions

| Pattern | Rationale |
|---------|-----------|
| **Domain Exceptions** | Services throw `PediloException` subclasses (not HTTP exceptions). Mapped to HTTP codes in `main.py` exception handlers. This keeps services testable and HTTP-agnostic. |
| **Bulk Operations** | Avoid N+1 issues by pre-fetching data in bulk (e.g., `obtener_toppings_para_varios_productos`). Validation is performed in-memory when possible. |
| **Rate Limiting** | Use `slowapi` to protect sensitive endpoints (login, register, order creation) from abuse and brute-force attacks. |
| **Argon2 over bcrypt** | Argon2 is the Password Hashing Competition winner and more resistant to GPU cracking. |
| **Soft Delete** | Entities use `activo=False` instead of hard deletion for audit trails. |
| **SQLModel** | Combines SQLAlchemy ORM + Pydantic validation, reducing boilerplate. |
| **Dependency Injection** | `app/api/deps.py` provides reusable dependencies like `get_current_user`, `get_db`. |

---

## 🔑 Core Concepts

### Authentication Flow
1. User registers via `/api/auth/register` → password hashed with Argon2
2. User logs in via `/api/auth/login` → JWT token returned
3. Protected routes require `Depends(get_current_user)` dependency
4. Token validated using `SECRET_KEY` from environment

### Multi-Tenant Model
- Each `Usuario` can have one `Negocio` (business)
- `Negocio` has a unique `slug` for public access (`/api/public/{slug}`)
- Products and orders belong to a specific `Negocio`
- Authorization checks ensure users only access their own resources

### Exception Handling
Services raise domain exceptions:
```python
from app.core.exceptions import EntityNotFoundError, BusinessLogicError, PermissionDeniedError

# Example
if not producto:
    raise EntityNotFoundError("Producto no encontrado")
```

These are caught by exception handlers in `main.py`:
- `EntityNotFoundError` → HTTP 404
- `BusinessLogicError` → HTTP 400
- `PermissionDeniedError` → HTTP 403

---

## 🛠️ Development Workflow

### Environment Setup
1. Create `.env` from `.envtemplate`
2. Required variables:
   - `ENVIRONMENT` (development/production)
   - `SECRET_KEY` (JWT signing)
   - `DATABASE_URL` (sqlite:///./dev.db for dev, postgresql://... for prod)
   - `CLOUDINARY_*` (for image uploads)
   - `MP_*` (optional, for MercadoPago subscriptions)

### Running the App
```bash
# Activate virtual environment (PowerShell on Windows)
.venv\Scripts\Activate.ps1

# Run development server
uvicorn app.main:app --reload

# Access API docs
# http://localhost:8000/docs
```

### Code Quality Tools
```bash
# Format code
make format      # Runs black + ruff format

# Lint and security checks
make lint        # Runs ruff + mypy + bandit

# Full check
make check       # Format + lint
```

**Linting Rules** (from `pyproject.toml`):
- Line length: 100 characters
- Ruff rules: E, F, I, B, C4, UP, SIM
- Ignores: E501 (line too long, handled by formatter)

---

## 📝 Code Patterns

### Adding a New Entity

#### 1. Define Model (`app/models/models.py`)
```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class MiModelo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    activo: bool = True
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
```

#### 2. Create Schemas (`app/schemas/mi_modelo.py`)
```python
from pydantic import BaseModel

class MiModeloCreate(BaseModel):
    nombre: str

class MiModeloUpdate(BaseModel):
    nombre: str | None = None

class MiModeloResponse(BaseModel):
    id: int
    nombre: str
    activo: bool
```

#### 3. Create Service (`app/services/mi_modelo_service.py`)
```python
from sqlmodel import Session, select
from app.models.models import MiModelo
from app.core.exceptions import EntityNotFoundError

def crear_modelo(session: Session, data: MiModeloCreate) -> MiModelo:
    modelo = MiModelo(**data.model_dump())
    session.add(modelo)
    session.commit()
    session.refresh(modelo)
    return modelo

def obtener_modelo(session: Session, modelo_id: int) -> MiModelo:
    modelo = session.get(MiModelo, modelo_id)
    if not modelo or not modelo.activo:
        raise EntityNotFoundError("Modelo no encontrado")
    return modelo
```

#### 4. Create Route (`app/api/routes/mi_modelo.py`)
```python
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.api.deps import get_db, get_current_user
from app.schemas.mi_modelo import MiModeloCreate, MiModeloResponse
from app.services import mi_modelo_service

router = APIRouter(prefix="/api/mi-modelo", tags=["Mi Modelo"])

@router.post("/", response_model=MiModeloResponse)
def crear(
    data: MiModeloCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return mi_modelo_service.crear_modelo(db, data)
```

#### 5. Register Route (`app/main.py`)
```python
from app.api.routes import mi_modelo
app.include_router(mi_modelo.router)
```

### Database Queries
Use SQLModel's `select()` for queries:
```python
from sqlmodel import select

# Get all active records
statement = select(MiModelo).where(MiModelo.activo == True)
results = session.exec(statement).all()

# Get one with filters
statement = select(Producto).where(
    Producto.negocio_id == negocio_id,
    Producto.activo == True
)
producto = session.exec(statement).first()
```

### Soft Delete Pattern
```python
def eliminar_producto(session: Session, producto_id: int):
    producto = session.get(Producto, producto_id)
    if not producto:
        raise EntityNotFoundError("Producto no encontrado")
    producto.activo = False  # Soft delete
    session.add(producto)
    session.commit()
```

---

## 🔐 Security Best Practices

1. **Password Hashing**: Always use `security.get_password_hash()` and `verify_password()`
2. **JWT Tokens**: Created via `security.create_access_token()`
3. **Authorization**: Check resource ownership in services:
   ```python
   if producto.negocio_id != current_user.negocio.id:
       raise PermissionDeniedError("No tiene permisos")
   ```
4. **Environment Secrets**: Never commit `.env` file. Use `.envtemplate` for reference.

---

## 🧪 Testing & Validation

### Automated Tests
- **Framework**: `pytest`
- **Setup**: `tests/conftest.py` configures an in-memory SQLite database and a `client` (FastAPI `TestClient`) with dependency overrides.
- **Rules**:
    - Tests must be independent.
    - Use `db_session` fixture for direct DB access.
    - Use `client` fixture for API endpoint testing.
    - Prefer `session.exec(select(...))` over legacy SQLAlchemy query syntax.

### Validation
- Pydantic v2 handles all schema validation automatically.
- Complex multi-field validation should be done with `@model_validator`.

### Manual Testing
1. Use Swagger UI at `http://localhost:8000/docs`
2. Test flow:
   - Register user → Login → Get token
   - Use "Authorize" button in Swagger with token: `Bearer <token>`
   - Test CRUD operations

### Pre-commit Checks
Before committing code, run:
```bash
make check  # Formats, lints, type-checks, and security scans
```

---

## 🚨 Common Pitfalls & Solutions

### Issue: "Module not found" errors
**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: Database changes not reflected
**Solution**: SQLModel creates tables on startup. Delete `dev.db` to recreate:
```bash
rm dev.db
uvicorn app.main:app --reload
```
*Note: In production, use Alembic migrations (included in requirements)*

### Issue: CORS errors from frontend
**Solution**: 
- Dev: CORS allows all origins (`"*"`)
- Prod: Only `FRONTEND_URL` from `.env` is allowed
- Check `app/main.py` CORS middleware config

### Issue: JWT token expired
**Solution**: Token lifetime is set in `app/core/security.py`. Re-login to get new token.

### Issue: Rate Limiter "Request object missing"
**Solution**: Any endpoint decorated with `@limiter.limit(...)` **must** include `request: Request` as a function parameter.
```python
@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: LoginSchema, ...):
    ...
```

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `app/main.py` | App entry point, middleware, exception handlers |
| `app/core/config.py` | Environment variables and settings |
| `app/core/security.py` | JWT and Argon2 utilities |
| `app/api/deps.py` | Reusable dependencies (DB, auth) |
| `app/models/models.py` | All database models |
| `requirements.txt` | Python dependencies |
| `MakeFile` | Code quality commands |

---

## 🎨 Code Style Guide

- **Naming**: 
  - Variables/functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
- **Type Hints**: Always use (enforced by mypy)
- **Docstrings**: Use for complex functions (not enforced but recommended)
- **Line Length**: 100 characters (auto-formatted by black)
- **Imports**: Sorted by ruff (stdlib → third-party → local)

---

## 🌐 API Conventions

### Response Formats
- **Success**: Returns schema object or list
- **Error**: JSON with `detail` field
  ```json
  {"detail": "Error message"}
  ```

### HTTP Methods
- `GET`: Retrieve (no side effects)
- `POST`: Create new resource
- `PUT`: Full update (all fields)
- `PATCH`: Partial update (not used currently)
- `DELETE`: Soft delete (sets `activo=False`)

### Authentication
- **Public routes**: `/api/public/*` (no auth required)
- **Protected routes**: All others require JWT via `Authorization: Bearer <token>` header

---

## 🔄 Typical Task Workflows

### Adding a New Endpoint
1. Check if entity exists in `models/models.py` (create if needed)
2. Create/update schemas in `schemas/`
3. Add service function in `services/`
4. Create route in `api/routes/`
5. Register router in `main.py`
6. Test in Swagger UI
7. Run `make check` before commit

### Modifying Business Logic
1. Locate service in `app/services/`
2. Make changes (ensure exceptions are raised properly)
3. Update route if API contract changes
4. Test manually
5. Run `make check`

### Adding New Environment Variable
1. Add to `.envtemplate`
2. Add to `app/core/config.py` in `Settings` class
3. Document in README.md if user-facing

---

## 📖 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLModel Docs**: https://sqlmodel.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Project README**: See `README.md` for user-facing documentation
- **API Docs**: http://localhost:8000/docs (when running)

---

## 💡 Tips for AI Agents

1. **Always check existing patterns**: Before creating new code, examine similar existing files
2. **Respect the architecture**: Keep services HTTP-agnostic (no `Request` or `Response` objects in services)
3. **All limited endpoints need Request**: If you add `@limiter.limit`, the function signature **must** have `request: Request`.
4. **Use domain exceptions**: Never raise `HTTPException` from services
5. **Check dependencies**: Import from correct modules (`app.models`, `app.schemas`, etc.)
6. **Follow soft delete**: Never hard-delete records unless explicitly required
7. **SQLModel Syntax**: Always use `session.exec(select(Model).where(...))` for consistency.
8. **Test before committing**: Run `pytest` and `make check`.
9. **Windows paths**: Use raw strings or forward slashes for cross-platform compatibility

---

## 📞 Questions?

If you encounter unclear patterns or need clarification:
1. Check this guide first
2. Read `README.md` for high-level overview
3. Examine similar existing code in the codebase
4. Check FastAPI/SQLModel official docs

---

**Last Updated**: 2026-02-11  
**Project Version**: 0.5.0  
**Maintained by**: Thiago Valentín Stilo Limarino
