# 🍕 Pedilo - Backend API

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![SQLModel](https://img.shields.io/badge/SQLModel-FF6F00?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlmodel.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Sistema de pedidos online sin comisiones para pequeños negocios**

[Pedilo](https://pediloarg.netlify.app) · [Frontend Repo](https://github.com/thiagostilo2121/pedilo-web) · [Reportar Bug](https://github.com/thiagostilo2121/pedilo-api/issues)

</div>

---

## 📖 Sobre el Proyecto

**Pedilo** es una plataforma que permite a pequeños comercios (pizzerías, heladerías, kioscos) recibir pedidos online sin pagar comisiones por transacción. Cada negocio obtiene su propia página pública con catálogo, carrito y checkout con integración a WhatsApp.

Este repositorio contiene el **backend API** construido con FastAPI, siguiendo patrones de arquitectura limpia.

### ✨ Características

- 🏪 **Multi-tenant**: Cada usuario puede tener su propio negocio
- 📦 **Catálogo Digital**: Productos con categorías, imágenes, stock y **toppings/extras** configurable
- 🛒 **Sistema de Pedidos**: Estados, notificaciones, tracking por código y checkout optimizado
- 🎟️ **Cupones de Descuento**: Reglas flexibles (2x1, porcentaje, monto fijo, envío gratis)
- � **Métricas y Estadísticas**: Seguimiento de ventas, pedidos diarios y ticket promedio
- �💳 **Suscripciones**: Integración con MercadoPago para planes premium
- 🔐 **Autenticación y Seguridad**: JWT con Argon2 y **Rate Limiting** para prevención de abusos
- 🖼️ **Multimedia**: Upload de imágenes a Cloudinary con soporte para banners
- 📱 **PWA Ready**: Personalización de colores y estética que afectan directamente al PWA del negocio

---

## 🏗️ Arquitectura

```
app/
├── api/              # Capa de presentación
│   ├── routes/       # Endpoints REST
│   ├── deps.py       # Dependency Injection
│   └── middleware.py # Logging, CORS
├── core/             # Configuración central
│   ├── config.py     # Settings con pydantic-settings
│   ├── database.py   # Engine SQLModel
│   ├── security.py   # JWT + Argon2
│   ├── rate_limit.py # Configuración de SlowAPI
│   └── exceptions.py # Domain exceptions
├── models/           # Entidades de dominio
├── schemas/          # DTOs (Pydantic)
├── services/         # Lógica de negocio (sin dependencias HTTP)
└── utils/            # Helpers (Cloudinary, etc.)
```

### Decisiones de Diseño

| Decisión | Razón |
|----------|-------|
| **Argon2** sobre bcrypt | Winner de Password Hashing Competition, resistente a GPU cracking |
| **Bulk Queries** | Eliminación de N+1 queries en validación de pedidos y cupones mediante precarga de datos en memoria |
| **Rate Limiting** | Implementación de `slowapi` para proteger endpoints críticos contra fuerza bruta y spam |
| **Domain Exceptions** | Services desacoplados de HTTP, testeables unitariamente |
| **Soft Delete** | `activo=False` en lugar de DELETE para auditoría |
| **SQLModel** | Unifica SQLAlchemy + Pydantic, menos boilerplate |

---

## 🛠️ Tech Stack

| Categoría | Tecnología |
|-----------|------------|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **ORM** | [SQLModel](https://sqlmodel.tiangolo.com/) |
| **Rate Limit** | [SlowAPI](https://github.com/laurentS/slowapi) |
| **Base de Datos** | PostgreSQL / SQLite (dev) |
| **Auth** | JWT (`python-jose`) + Argon2 (`argon2-cffi`) |
| **Pagos** | [MercadoPago](https://www.mercadopago.com.ar/developers/) |
| **Imágenes** | [Cloudinary](https://cloudinary.com/) |
| **Validación** | Pydantic v2 + `pydantic-settings` |
| **Linting** | Ruff, Black, MyPy, Bandit |

---

## 🚀 Quick Start

### Requisitos

- Python 3.10+
- PostgreSQL (o SQLite para desarrollo)

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/thiagostilo2121/pedilo-api.git
cd pedilo-api

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .envtemplate .env
# Editar .env con tus credenciales
```

### Variables de Entorno

```env
# Ambiente
ENVIRONMENT=development          # development | production
FRONTEND_URL=http://localhost:5173

# Seguridad
SECRET_KEY=tu-clave-secreta-muy-larga

# Base de Datos
DATABASE_URL=sqlite:///./dev.db  # o postgresql://...

# Cloudinary
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx

# MercadoPago (opcional)
MP_ACCESS_TOKEN=xxx
MP_PLAN_ID=xxx
MP_WEBHOOK_SECRET=xxx
```

### Ejecutar

```bash
# Desarrollo
uvicorn app.main:app --reload

# La API estará en http://localhost:8000
# Documentación: http://localhost:8000/docs
```

---

## 📚 API Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/register` | Registrar usuario |
| POST | `/api/auth/login` | Login (retorna JWT) |
| GET | `/api/auth/usuario` | Obtener perfil actual |

### Negocios (Requiere Auth)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/negocios/me` | Mi negocio |
| POST | `/api/negocios/` | Crear negocio |
| PUT | `/api/negocios/me` | Actualizar negocio |

### Productos (Requiere Auth)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/productos` | Listar productos |
| POST | `/api/productos` | Crear producto |
| PUT | `/api/productos/{id}` | Actualizar producto |
| DELETE | `/api/productos/{id}` | Desactivar producto |

### Public API (Sin Auth - Rate Limited)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/public/{slug}` | Info del negocio |
| GET | `/api/public/{slug}/productos` | Catálogo público |
| POST | `/api/public/{slug}/pedidos` | Crear pedido |
| GET | `/api/public/pedidos/{codigo}` | Tracking de pedido |
| POST | `/api/public/{slug}/validate-coupon` | Validar cupón en tiempo real |

### Estadísticas (Requiere Premium)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/stats/dashboard` | Resumen de ventas hoy, pedidos y ticket promedio |
| GET | `/api/stats/daily-sales` | Histórico de ventas de los últimos X días |

> 📖 Documentación completa en `/docs` (Swagger UI)

---

## 🧪 Testing

```bash
# Ejecutar tests (coming soon)
pytest

# Linting
ruff check .
black --check .
mypy .

# Security check
bandit -r app/
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! 

1. Fork el proyecto
2. Creá tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push a la branch (`git push origin feature/AmazingFeature`)
5. Abrí un Pull Request

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Ver [LICENSE](LICENSE) para más información.

---

## 👤 Autor

**Thiago Valentín Stilo Limarino**

- GitHub: [@thiagostilo2121](https://github.com/thiagostilo2121)

---

<div align="center">

⭐ Si te sirvió este proyecto, dejá una estrella!

</div>
