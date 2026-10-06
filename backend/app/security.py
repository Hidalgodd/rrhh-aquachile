import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


def get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")
    if (
        not secret_key
        or len(secret_key) < 32
        or secret_key.startswith("REEMPLAZA_")
    ):
        raise RuntimeError(
            "SECRET_KEY debe configurarse con al menos 32 caracteres aleatorios."
        )
    return secret_key


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode(
        {"sub": username, "exp": expires_at},
        get_secret_key(),
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
