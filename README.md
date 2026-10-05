# RRHH AquaChile

Sebastian Hidalgo

Proyecto académico de Ingeniería Informática (4° semestre). Sistema web de Recursos Humanos para AquaChile.

## Tecnologías

- **Frontend:** React + Vite
- **Backend:** Python con FastAPI
- **Base de datos:** PostgreSQL (con SQLAlchemy)

## Avances

### Etapa anterior

- Estructura del proyecto separada en `backend/` y `frontend/`.
- API en FastAPI con CORS habilitado para el frontend.
- Endpoints de prueba `/health` y `/db-check`.
- Archivo `.env.example` con la configuración de conexión a PostgreSQL.
- Dependencias del backend definidas en `requirements.txt`.
- Proyecto React creado con Vite y ESLint configurado.
- `.gitignore` configurado (no se suben `.env`, `venv` ni `node_modules`).

### Avances de hoy (05-10-2026)

**Base de datos**

- Diseño y creación de la base de datos `rrhh_aquachile` en PostgreSQL con 8 tablas:
  `areas`, `cargos`, `empleados`, `contratos`, `asistencias`, `permisos`, `postulantes` y `usuarios`.
- Relaciones entre tablas con llaves foráneas y restricciones (`CHECK`, `UNIQUE`, `NOT NULL`).
- Datos de prueba cargados en todas las tablas.
- Revisión y corrección del script SQL (paréntesis, nombres de columnas y referencias).

**Subida de CV (postulantes)**

- Tabla `postulantes` para las personas que envían su currículum, con estado de la postulación (recibido, en revisión, entrevista, contratado, rechazado).
- Los CV se guardan como archivo en `backend/uploads/cvs/` y en la base de datos se guarda solo su nombre.
- Validación de archivos: solo PDF, DOC o DOCX, de hasta 5 MB.
- Endpoints nuevos:
  - `POST /api/postulantes`: recibe los datos y el CV.
  - `GET /api/postulantes`: lista los postulantes.
  - `GET /api/postulantes/{id}/cv`: descarga el CV.
- Formulario de postulación en React (`FormularioPostulacion.jsx`) que envía los datos al backend.

**Conexión del backend con la base de datos**

- `database.py`: conexión a PostgreSQL con SQLAlchemy, leyendo `DATABASE_URL` desde el archivo `.env`.
- Modelo `Postulante` y router de postulantes organizados en `models/` y `routers/`.
- `app/main.py` unificado, con CORS, `/health`, `/db-check` y las rutas de postulantes.

## Estructura

```
rrhh-aquachile/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   └── postulante.py
│   │   ├── routers/
│   │   │   └── postulantes.py
│   │   ├── database.py
│   │   └── main.py
│   ├── uploads/cvs/          (se crea sola, no se sube a Git)
│   ├── .env                  (no se sube a Git)
│   ├── .env.example
│   └── requirements.txt
├── database/
│   └── rrhh_aquachile.sql
├── frontend/
│   └── src/
│       ├── FormularioPostulacion.jsx
│       └── FormularioPostulacion.css
└── .gitignore
```

## Cómo ejecutar

**1. Base de datos**

En pgAdmin, crear la base `rrhh_aquachile`, abrir el Query Tool y ejecutar `database/rrhh_aquachile.sql`.

**2. Backend**

```bash
cd backend
pip install -r requirements.txt
pip install python-multipart
```

Crear el archivo `backend/.env` a partir de `.env.example`:

```
DATABASE_URL=postgresql+psycopg2://postgres:TU_PASSWORD@localhost:5432/rrhh_aquachile
```

Levantar la API:

```bash
python -m uvicorn app.main:app --reload
```

- Documentación de la API: `http://localhost:8000/docs`
- Prueba de conexión a la base de datos: `http://localhost:8000/db-check` (debe responder `{"db": 1}`)

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Aplicación en `http://localhost:5173`.
