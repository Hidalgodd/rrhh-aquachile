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

### Avances de hoy (06-10-2026)

**Estructura y configuración del backend**

- Se mejoró la carga de configuración desde `backend/.env`; si falta `DATABASE_URL`, el backend ahora informa el error al iniciar.
- Se habilitó la comprobación de conexiones del pool de SQLAlchemy y se completó `requirements.txt` con las dependencias necesarias para ejecutar la API.
- Se incorporó Alembic para versionar cambios del esquema y se agregaron migraciones para `postulantes`, `areas`, `cargos`, `empleados` y `usuarios`.
- Se documentó la instalación, ejecución de migraciones y pruebas. El script `database/rrhh_aquachile.sql` se mantiene solo para desarrollo porque elimina y recrea tablas.

**Autenticación y permisos**

- Se agregó `POST /api/auth/token`, que autentica usuarios internos y entrega tokens Bearer con vencimiento.
- Las contraseñas se almacenan con hash Argon2; la clave para firmar tokens se configura en `SECRET_KEY`.
- Se restringieron `GET /api/postulantes` y `GET /api/postulantes/{id}/cv` a usuarios activos con rol `rrhh` o `admin`. La recepción pública de postulaciones permanece abierta.
- Se agregó `app/create_user.py` para crear cuentas desde la consola, vinculadas a empleados existentes. No hay registro público; el comando solicita la contraseña de forma interactiva.
- Se añadieron pruebas para el estado del servicio, el acceso a postulantes sin credenciales y las funciones de seguridad. Quedan pendientes de ejecución cuando Python esté instalado.

**Áreas, cargos y empleados**

- Se agregaron endpoints protegidos por los roles `rrhh` y `admin` para consultar y crear áreas y cargos, con validación de montos y relaciones.
- Se incorporó la gestión de empleados: creación, consulta individual, listado con búsqueda/filtro/paginación y actualización parcial.
- Se valida el formato y dígito verificador del RUT, se normalizan los correos y se evita repetir RUT, correo o nombre de área.
- Al marcar como inactivo a un empleado con cuenta asociada, su usuario de acceso también se desactiva.
- Se añadió `app/bootstrap_admin.py` para inicializar de forma local la primera área, cargo, empleado y cuenta administradora cuando la base está vacía. Se agregaron pruebas de flujos y validaciones; pendientes de ejecución al instalar Python.

## Estructura

```
rrhh-aquachile/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── empleado.py
│   │   │   ├── postulante.py
│   │   │   └── usuario.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── empleados.py
│   │   │   └── postulantes.py
│   │   ├── schemas/
│   │   │   └── empleado.py
│   │   ├── bootstrap_admin.py
│   │   ├── create_user.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── uploads/cvs/          (se crea sola, no se sube a Git)
│   ├── .env                  (no se sube a Git)
│   ├── .env.example
│   ├── alembic.ini
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

En PostgreSQL, crear una base vacía llamada `rrhh_aquachile`.

**2. Backend**

```bash
cd backend
pip install -r requirements.txt
```

Crear el archivo `backend/.env` a partir de `.env.example`:

```
DATABASE_URL=postgresql+psycopg2://postgres:TU_CLAVE@localhost:5432/rrhh_aquachile
```

Crear las tablas implementadas actualmente en los modelos del backend y levantar la API:

```bash
alembic upgrade head
python -m app.bootstrap_admin
python -m uvicorn app.main:app --reload
```

- Documentación de la API: `http://localhost:8000/docs`
- Prueba de conexión a la base de datos: `http://localhost:8000/db-check` (debe responder `{"db": 1}`)

Antes, configura `SECRET_KEY` en `backend/.env` con un valor aleatorio propio. Puedes generarlo localmente con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

La API entrega tokens en `POST /api/auth/token` (OAuth2 password form). La lista de postulantes y la descarga de CV requieren sesión de un usuario `rrhh` o `admin`; la postulación pública sigue disponible sin iniciar sesión. Para crear una cuenta local, el empleado debe existir primero en la base de datos:

```bash
python -m app.create_user --employee-id 1 --username admin --role admin
```

En una base nueva creada con Alembic, primero inicializa los datos y la cuenta de administración con `python -m app.bootstrap_admin`; el comando solicita los datos y contraseñas interactivamente. Para bases donde el empleado ya existe, usa `app.create_user` como en el ejemplo anterior. Para agregar cuentas `rrhh` o `empleado`, ejecuta `app.create_user` con el rol correspondiente. No existe una ruta pública de registro.

Las rutas de gestión son `GET/POST /api/areas`, `GET/POST /api/cargos` y `GET/POST /api/empleados`, además de `GET/PATCH /api/empleados/{id}`. Todas requieren un token de usuario `rrhh` o `admin`.

Las pruebas requieren instalar también las dependencias de desarrollo (`pip install -r requirements-dev.txt`) y se ejecutan desde `backend/` con `pytest`.

`database/rrhh_aquachile.sql` es un script de desarrollo que elimina y vuelve a crear tablas; ejecútalo solo en una base desechable. Si ya inicializaste una base con ese script, no lo ejecutes de nuevo: desde `backend/`, registra su estado inicial con `alembic stamp head`.

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Aplicación en `http://localhost:5173`.
