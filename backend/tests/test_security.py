import pytest
import jwt

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_verified_without_storing_plaintext(monkeypatch):
    password = "UnaClaveLargaYSegura123!"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("otra-clave", hashed_password)


def test_access_token_contains_username_and_rejects_tampering(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    token = create_access_token("admin")

    assert decode_access_token(token)["sub"] == "admin"
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token + "invalid")


def test_secret_key_must_be_configured(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_access_token("admin")
