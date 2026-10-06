import argparse
import getpass
import re

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.empleado import Empleado
from app.models.usuario import Usuario
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea una cuenta interna vinculada a un empleado existente."
    )
    parser.add_argument("--employee-id", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=("admin", "rrhh", "empleado"), required=True)
    args = parser.parse_args()

    username = args.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,50}", username):
        parser.error("El usuario debe tener 3-50 caracteres: letras, números, . _ -")

    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Repite la contraseña: ")
    if len(password) < 12:
        parser.error("La contraseña debe tener al menos 12 caracteres.")
    if password != confirmation:
        parser.error("Las contraseñas no coinciden.")

    with SessionLocal() as db:
        if db.get(Empleado, args.employee_id) is None:
            parser.error(f"No existe el empleado con id {args.employee_id}.")
        existing_user = (
            db.query(Usuario)
            .filter(
                (Usuario.username == username)
                | (Usuario.id_empleado == args.employee_id)
            )
            .first()
        )
        if existing_user is not None:
            parser.error("El usuario o el empleado ya tienen una cuenta.")

        db.add(
            Usuario(
                id_empleado=args.employee_id,
                username=username,
                password_hash=hash_password(password),
                rol=args.role,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.error(
                "No se pudo crear la cuenta: el usuario o el empleado ya están asociados."
            )

    print(f"Cuenta '{username}' creada con rol '{args.role}'.")


if __name__ == "__main__":
    main()
