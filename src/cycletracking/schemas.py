"""Contratos públicos explícitos, con códigos estables independientes del idioma."""
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Role(str, Enum):
    ADMIN = "ADMIN"
    OPERATIVO = "OPERATIVO"
    INVENTARIOS = "INVENTARIOS"


class IdentifierKind(str, Enum):
    SERIAL = "SERIAL"
    IMEI = "IMEI"
    QR = "QR"
    ECONOMIC = "ECONOMIC"


class CreateAsset(BaseModel):
    equipment_type: str = Field(min_length=2, max_length=60)
    technology: str | None = Field(default=None, max_length=60)
    identifier_kind: IdentifierKind = IdentifierKind.SERIAL
    identifier: str = Field(min_length=2, max_length=128)

    @field_validator("equipment_type", "technology", "identifier")
    @classmethod
    def cleaned(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class ObservationKind(str, Enum):
    MISSING_REPORTED = "MISSING_REPORTED"
    STOLEN_REPORTED = "STOLEN_REPORTED"
    DAMAGED_REPORTED = "DAMAGED_REPORTED"
    SEIZED_REPORTED = "SEIZED_REPORTED"
    FOUND_REPORTED = "FOUND_REPORTED"
    DOCUMENT_RECORDED = "DOCUMENT_RECORDED"


class OfficialStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEPLOYED = "DEPLOYED"
    IN_MAINTENANCE = "IN_MAINTENANCE"
    MISSING = "MISSING"
    STOLEN = "STOLEN"
    SEIZED = "SEIZED"
    DAMAGED = "DAMAGED"
    RETURNED = "RETURNED"
    RETIRED = "RETIRED"


class SharedEvent(BaseModel):
    event_id: UUID
    occurred_at: datetime
    note: str = Field(min_length=5, max_length=4000)
    evidence_ref: str | None = Field(default=None, max_length=160)
    evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")

    @field_validator("occurred_at")
    @classmethod
    def aware_date(cls, v: datetime) -> datetime:
        if v.utcoffset() is None:
            raise ValueError("Se requiere fecha con zona horaria")
        return v


class ReportObservation(SharedEvent):
    event_type: ObservationKind


class ConfirmStatus(SharedEvent):
    expected_version: int = Field(ge=1)
    new_status: OfficialStatus


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
