DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS postulantes CASCADE;
DROP TABLE IF EXISTS permisos CASCADE;
DROP TABLE IF EXISTS asistencias CASCADE;
DROP TABLE IF EXISTS contratos CASCADE;
DROP TABLE IF EXISTS empleados CASCADE;
DROP TABLE IF EXISTS cargos CASCADE;
DROP TABLE IF EXISTS areas CASCADE;
 
CREATE TABLE areas (
    id_area SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(255)
);
 
CREATE TABLE cargos (
    id_cargo SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_area INT NOT NULL REFERENCES areas(id_area),
    sueldo_base NUMERIC(10,2) NOT NULL CHECK (sueldo_base >= 0)
);
 
CREATE TABLE empleados (
    id_empleado SERIAL PRIMARY KEY,
    rut VARCHAR(12) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    correo VARCHAR(150) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    direccion VARCHAR(200),
    fecha_ingreso DATE NOT NULL DEFAULT CURRENT_DATE,
    id_cargo INT NOT NULL REFERENCES cargos(id_cargo),
    estado VARCHAR(20) NOT NULL DEFAULT 'activo'
        CHECK (estado IN ('activo', 'inactivo', 'licencia'))
);
 
CREATE TABLE contratos (
    id_contrato SERIAL PRIMARY KEY,
    id_empleado INT NOT NULL REFERENCES empleados(id_empleado) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL
        CHECK (tipo IN ('indefinido', 'plazo fijo', 'por obra')),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    sueldo NUMERIC(10,2) NOT NULL CHECK (sueldo >= 0),
    CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);
 
CREATE TABLE asistencias (
    id_asistencia SERIAL PRIMARY KEY,
    id_empleado INT NOT NULL REFERENCES empleados(id_empleado) ON DELETE CASCADE,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora_entrada TIME,
    hora_salida TIME,
    UNIQUE (id_empleado, fecha)
);
 
CREATE TABLE permisos (
    id_permiso SERIAL PRIMARY KEY,
    id_empleado INT NOT NULL REFERENCES empleados(id_empleado) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL
        CHECK (tipo IN ('vacaciones', 'licencia medica', 'administrativo')),
    fecha_inicio DATE NOT NULL,
    fecha_termino DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    CHECK (fecha_termino >= fecha_inicio)
);
 
CREATE TABLE postulantes (
    id_postulante SERIAL PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    cargo_postulado VARCHAR(100) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'recibido'
        CHECK (estado IN ('recibido', 'en revisión', 'entrevista', 'contratado', 'rechazado')),
    cv_nombre_original VARCHAR(255) NOT NULL,  -- nombre con que lo subió la persona
    cv_archivo VARCHAR(255) NOT NULL,          -- nombre con que se guardó en el servidor
    fecha_postulacion TIMESTAMP NOT NULL DEFAULT NOW()
);
 
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    id_empleado INT NOT NULL UNIQUE REFERENCES empleados(id_empleado) ON DELETE CASCADE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'empleado'
        CHECK (rol IN ('admin', 'rrhh', 'empleado')),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
 
-- DATOS DE PRUEBA
INSERT INTO areas (nombre, descripcion) VALUES
    ('Recursos Humanos', 'Gestión del personal'),
    ('Producción', 'Operación de centros de cultivo y planta'),
    ('Finanzas', 'Contabilidad y presupuesto');
 
INSERT INTO cargos (nombre, id_area, sueldo_base) VALUES
    ('Analista de RRHH', 1, 900000),
    ('Operario de Planta', 2, 650000),
    ('Contador', 3, 1100000);
 
INSERT INTO empleados (rut, nombres, apellidos, correo, id_cargo) VALUES
    ('11.111.111-1', 'Ana',   'Pérez', 'ana.perez@example.com',   1),
    ('22.222.222-2', 'Luis',  'Soto',  'luis.soto@example.com',   2),
    ('33.333.333-3', 'María', 'Rojas', 'maria.rojas@example.com', 3);
 
INSERT INTO contratos (id_empleado, tipo, fecha_inicio, sueldo) VALUES
    (1, 'indefinido', '2024-03-01', 900000),
    (2, 'plazo fijo', '2025-01-15', 650000),
    (3, 'indefinido', '2023-06-01', 1100000);
 
INSERT INTO asistencias (id_empleado, fecha, hora_entrada, hora_salida) VALUES
    (1, CURRENT_DATE, '08:00', '17:00'),
    (2, CURRENT_DATE, '08:10', '17:05');
 
INSERT INTO permisos (id_empleado, tipo, fecha_inicio, fecha_termino) VALUES
    (3, 'vacaciones', '2026-12-20', '2026-12-31');
 
INSERT INTO postulantes (nombres, apellidos, correo, cargo_postulado, cv_nombre_original, cv_archivo) VALUES
    ('Pedro', 'Muñoz', 'pedro.munoz@example.com', 'Operario de Planta', 'cv_pedro.pdf', 'ejemplo.pdf');
	
 SELECT * FROM empleados;