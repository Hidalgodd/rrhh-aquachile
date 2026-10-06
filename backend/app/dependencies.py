from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
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
