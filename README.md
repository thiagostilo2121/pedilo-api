# 🚀 Pedilo - Backend API

**Pedilo API** es el motor principal del sistema Pedilo, diseñado para gestionar pedidos online de manera eficiente y sin comisiones. Construido con **FastAPI**, ofrece un rendimiento excepcional, validación automática de datos y documentación interactiva.

---

## 🛠️ Tech Stack

- **Lenguaje**: [Python 3.14](https://www.python.org/)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
- **Base de Datos**: PostgreSQL (Soporte para SQLite en desarrollo)
- **Migraciones**: [Alembic](https://alembic.sqlalchemy.org/)
- **Seguridad**: JWT (JSON Web Tokens) con `python-jose` y hashing con `passlib`
- **Multimedia**: [Cloudinary](https://cloudinary.com/) (Gestión de imágenes)
- **Validación de Entorno**: `pydantic-settings`

---

## 🌟 Características Principales

- **Gestión de Negocios**: CRUD completo para perfiles comerciales y configuración.
- **Catálogo Digital**: API para productos, variaciones y categorías.
- **Sistema de Pedidos**: Recepción, validación y actualización de estados en tiempo real.
- **Autenticación y Autorización**: Registro de usuarios, login seguro y control de acceso (RBAC).
- **Public API**: Endpoints optimizados para el consumo del frontend público de clientes.
- **Integración con Nube**: Carga y optimización de imágenes en Cloudinary.
- **Suscripciones**: Lógica para el manejo de planes y estados de cuenta premium.

---

## 📂 Estructura del Proyecto

```text
app/
├── api/          # Rutas (routes) y middlewares
├── core/         # Configuración central (DB, seguridad, logs)
├── models/       # Modelos de base de datos (SQLModel)
├── schemas/      # Modelos de validación (Pydantic schemas)
├── services/     # Lógica de negocio
├── utils/        # Funciones auxiliares
└── main.py       # Punto de entrada de la aplicación
```

---

## ⚙️ Configuración e Instalación

### Requisitos Previos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- PostgreSQL (opcional, configurado por defecto)

### Pasos para iniciar el proyecto

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/thiagostilo2121/pedilo-backapi.git
   cd pedilo-backapi
   ```

2. **Crear y activar entorno virtual**:
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Variables de Entorno**:
   Copia el archivo `.envtemplate` a `.env` y completa los valores necesarios:
   ```bash
   cp .envtemplate .env
   ```
   Asegúrate de configurar:
   - `DATABASE_URL`
   - `SECRET_KEY` (para JWT)
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `MP_ACCESS_TOKEN`
   - `MP_PLAN_ID`

5. **Iniciar en modo desarrollo**:
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Acceder a la documentación**:
   - Swagger UI: `http://localhost:8000/docs`
   - Redoc: `http://localhost:8000/redoc`

---

## 🐳 Docker Deployment

Mentira, aún no configuré Docker.

---

## 🤝 Contribución

Si quieres mejorar la API de Pedilo, siéntete libre de abrir un issue o enviar un pull request.

---

## 📄 Licencia

Este proyecto está bajo la Licencia [MIT](LICENSE).
