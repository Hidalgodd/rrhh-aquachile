from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.empleado import Empleado
from app.models.usuario import Usuario
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> Usuario:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión vencida",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credentials_error
    except jwt.InvalidTokenError as exc:
        raise credentials_error from exc

    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None or not usuario.activo:
        raise credentials_error
    return usuario


def require_rrhh(
    usuario: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    if usuario.rol not in {"admin", "rrhh"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere el rol de RR. HH. o administración",
        )
    return usuario


RRHH_ROLES = {"admin", "rrhh"}


def empleado_actual(
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: DbSession,
) -> Empleado:
    empleado = db.get(Empleado, usuario.id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Tu cuenta no tiene ficha de empleado")
    return empleado


def exigir_acceso_a(usuario: Usuario, id_empleado: int) -> None:
    """RR. HH. ve a cualquiera; el resto, solo su propia ficha."""
    if usuario.rol not in RRHH_ROLES and usuario.id_empleado != id_empleado:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta ficha")
