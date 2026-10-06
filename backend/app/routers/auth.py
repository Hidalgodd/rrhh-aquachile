from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/token")
def iniciar_sesion(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    username = form_data.username.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if (
        usuario is None
        or not usuario.activo
        or not verify_password(form_data.password, usuario.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(usuario.username),
        "token_type": "bearer",
    }
