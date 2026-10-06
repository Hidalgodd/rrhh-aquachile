import getpass
import re
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.empleado import Area, Cargo, Empleado
from app.models.usuario import Usuario
from app.schemas.empleado import AreaCreate, CargoCreate, EmpleadoCreate
from app.security import hash_password


def _prompt_required(label: str) -> str:
    value = input(f"{label}: ").strip()
    while not value:
        print(f"{label} es obligatorio.")
        value = input(f"{label}: ").strip()
    return value


def main() -> None:
    username = _prompt_required("Usuario administrador").lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,50}", username):
        raise SystemExit("El usuario debe tener 3-50 caracteres: letras, números, . _ -")

    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Repite la contraseña: ")
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")

    try:
        sueldo_base = Decimal(_prompt_required("Sueldo base mensual del cargo"))
    except InvalidOperation as exc:
        raise SystemExit("El sueldo debe ser un número válido.") from exc

    try:
        area_data = AreaCreate(
            nombre=_prompt_required("Nombre del área"),
            descripcion=input("Descripción del área (opcional): ").strip() or None,
        )
    except ValidationError as exc:
        raise SystemExit(f"Datos del área inválidos:\n{exc}") from exc
    nombre_cargo = _prompt_required("Nombre del cargo")
    empleado_data = {
        "rut": _prompt_required("RUT"),
        "nombres": _prompt_required("Nombres"),
        "apellidos": _prompt_required("Apellidos"),
        "correo": _prompt_required("Correo"),
        "telefono": input("Teléfono (opcional): ").strip() or None,
        "direccion": input("Dirección (opcional): ").strip() or None,
    }
    try:
        empleado_data = EmpleadoCreate.model_validate(
            {
                **empleado_data,
                "id_cargo": 1,
            }
        )
    except ValidationError as exc:
        raise SystemExit(f"Datos del empleado inválidos:\n{exc}") from exc

    with SessionLocal() as db:
        if db.query(Usuario).count():
            raise SystemExit(
                "Ya existen cuentas de usuario. Usa app.create_user para agregar otra."
            )

        area = Area(nombre=area_data.nombre, descripcion=area_data.descripcion)
        db.add(area)
        try:
            db.flush()
            cargo_data = CargoCreate(
                nombre=nombre_cargo,
                id_area=area.id_area,
                sueldo_base=sueldo_base,
            )
            cargo = Cargo(
                nombre=cargo_data.nombre,
                id_area=cargo_data.id_area,
                sueldo_base=cargo_data.sueldo_base,
            )
            db.add(cargo)
            db.flush()
            empleado = Empleado(
                **empleado_data.model_dump(exclude={"id_cargo"}),
                id_cargo=cargo.id_cargo,
            )
            db.add(empleado)
            db.flush()
            db.add(
                Usuario(
                    id_empleado=empleado.id_empleado,
                    username=username,
                    password_hash=hash_password(password),
                    rol="admin",
                )
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit(
                "No se pudo crear la cuenta inicial por una restricción de datos."
            ) from exc
        except ValidationError as exc:
            db.rollback()
            raise SystemExit(f"Datos iniciales inválidos:\n{exc}") from exc

    print(f"Cuenta administradora '{username}' creada y vinculada al empleado.")


if __name__ == "__main__":
    main()
