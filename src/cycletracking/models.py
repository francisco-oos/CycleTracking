"""Entidades del primer corte. El estado actual NO reemplaza al historial."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(24))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SessionToken(Base):
    __tablename__ = "session_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    equipment_type: Mapped[str] = mapped_column(String(60), index=True)
    technology: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="REGISTERED")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    identifiers: Mapped[list["AssetIdentifier"]] = relationship(back_populates="asset", lazy="selectin")


class AssetIdentifier(Base):
    __tablename__ = "asset_identifiers"
    __table_args__ = (UniqueConstraint("kind", "normalized_value", name="uq_identifier_kind_value"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    value: Mapped[str] = mapped_column(String(128))
    normalized_value: Mapped[str] = mapped_column(String(128))
    asset: Mapped[Asset] = relationship(back_populates="identifiers")


class AssetEvent(Base):
    __tablename__ = "asset_events"
    __table_args__ = (Index("ix_asset_events_asset_time", "asset_id", "recorded_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(48))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    note: Mapped[str] = mapped_column(Text, default="")
    evidence_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    version_after: Mapped[int] = mapped_column(Integer)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
