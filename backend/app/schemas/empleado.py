import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AreaCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)

    @field_validator("nombre")
    @classmethod
    def trim_nombre(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return value


class AreaRead(AreaCreate):
    model_config = ConfigDict(from_attributes=True)

    id_area: int


class CargoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    id_area: int = Field(gt=0)
    sueldo_base: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

    @field_validator("nombre")
    @classmethod
    def trim_nombre(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return value


class CargoRead(CargoCreate):
    id_cargo: int
    area_nombre: str


class EmpleadoCreate(BaseModel):
    rut: str = Field(min_length=8, max_length=12)
    nombres: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=100)
    fecha_nacimiento: date | None = None
    correo: str = Field(min_length=5, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)
    fecha_ingreso: date = Field(default_factory=date.today)
    id_cargo: int = Field(gt=0)
    estado: Literal["activo", "inactivo", "licencia"] = "activo"

    @field_validator("rut")
    @classmethod
    def validate_rut(cls, value: str) -> str:
        normalized = re.sub(r"[.\-\s]", "", value).upper()
        if not re.fullmatch(r"\d{7,8}[0-9K]", normalized):
            raise ValueError("El RUT debe tener un formato válido")

        body, check_digit = normalized[:-1], normalized[-1]
        total = sum(
            int(digit) * ((index % 6) + 2)
            for index, digit in enumerate(reversed(body))
        )
        remainder = 11 - total % 11
        expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
        if check_digit != expected:
            raise ValueError("El dígito verificador del RUT no es válido")

        return f"{body}-{check_digit}"

    @field_validator("nombres", "apellidos")
    @classmethod
    def trim_required_names(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El campo debe tener al menos 2 caracteres")
        return value

    @field_validator("correo")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("El correo electrónico no tiene un formato válido")
        return value


class EmpleadoUpdate(BaseModel):
    nombres: str | None = Field(default=None, min_length=2, max_length=100)
    apellidos: str | None = Field(default=None, min_length=2, max_length=100)
    fecha_nacimiento: date | None = None
    correo: str | None = Field(default=None, min_length=5, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)
    fecha_ingreso: date | None = None
    id_cargo: int | None = Field(default=None, gt=0)
    estado: Literal["activo", "inactivo", "licencia"] | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self):
        required_fields = {
            "nombres",
            "apellidos",
            "correo",
            "fecha_ingreso",
            "id_cargo",
            "estado",
        }
        for field in required_fields & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo")
        return self

    @field_validator("nombres", "apellidos")
    @classmethod
    def trim_optional_names(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El campo debe tener al menos 2 caracteres")
        return value

    @field_validator("correo")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("El correo electrónico no tiene un formato válido")
        return value


class EmpleadoRead(BaseModel):
    id_empleado: int
    rut: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date | None
    correo: str
    telefono: str | None
    direccion: str | None
    fecha_ingreso: date
    estado: str
    id_cargo: int
    cargo: str
    area: str
