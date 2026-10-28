"""API autoritativa liviana: las PCs realizan el procesamiento pesado."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from cycletracking import __version__
from cycletracking.models import Asset, AssetEvent, AssetIdentifier, Base, SessionToken, User
from cycletracking.schemas import ConfirmStatus, CreateAsset, LoginRequest, ReportObservation
from cycletracking.security import bearer, create_session, get_current_user, hash_password, require_role, verify_password


def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.getenv("CYCLE_DATABASE_URL")
    if not url:
        raise RuntimeError("Configura CYCLE_DATABASE_URL antes de iniciar CycleTracking")
    sqlite = url.startswith("sqlite")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if sqlite else {})
    SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_session():
        with SessionFactory() as db:
            yield db

    current_user = get_current_user(db_session)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # En producción las migraciones estarán gestionadas por Alembic; no auto-crear estructuras.
        yield
        engine.dispose()

    api = FastAPI(title="CycleTracking", version=__version__, lifespan=lifespan)

    @api.get("/health")
    def health(db: Session = Depends(db_session)):
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE"})
        return {"status": "ok", "version": __version__}

    @api.post("/api/v1/auth/login")
    def login(payload: LoginRequest, db: Session = Depends(db_session)):
        user = db.scalar(select(User).where(User.username == payload.username))
        if not user or not user.active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS"})
        return {"token_type": "bearer", "access_token": create_session(db, user), "expires_in_seconds": 28800}

    @api.post("/api/v1/auth/logout")
    def logout(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        user: User = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        token = db.get(SessionToken, digest)
        if token:
            db.delete(token)
            db.commit()
        return {"ok": True}

    @api.get("/api/v1/me")
    def me(user: User = Depends(current_user)):
        return {"id": user.id, "username": user.username, "role": user.role}

    @api.post("/api/v1/assets", status_code=201)
    def register_asset(data: CreateAsset, user: User = Depends(current_user), db: Session = Depends(db_session)):
        require_role(user, "INVENTARIOS")
        normalized = data.identifier.strip().upper()
        if not normalized or not data.equipment_type.strip():
            raise HTTPException(422, detail={"code": "EMPTY_IDENTIFIER_OR_TYPE"})
        asset = Asset(equipment_type=data.equipment_type.strip().upper(), technology=(data.technology or "").strip().upper() or None)
        db.add(asset)
        db.flush()
        db.add(AssetIdentifier(asset_id=asset.id, kind=data.identifier_kind.value, value=data.identifier.strip(), normalized_value=normalized))
        db.add(AssetEvent(
            id=str(uuid4()), asset_id=asset.id, actor_id=user.id, event_type="REGISTERED",
            occurred_at=datetime.now(timezone.utc), note="Alta autorizada",
            request_fingerprint=hashlib.sha256(json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()).hexdigest(),
            version_after=asset.version, new_status=asset.status,
        ))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, detail={"code": "IDENTIFIER_ALREADY_EXISTS"})
        return asset_view(asset)

    def asset_view(asset: Asset) -> dict:
        return {
            "id": asset.id, "equipment_type": asset.equipment_type,
            "technology": asset.technology, "status": asset.status, "version": asset.version,
            "identifiers": [{"kind": i.kind, "value": i.value} for i in asset.identifiers],
        }

    @api.get("/api/v1/assets")
    def list_assets(
        q: str = Query(default="", max_length=128),
        limit: int = Query(default=50, ge=1, le=100),
        user: User = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        stmt = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
        if q.strip():
            ids = select(AssetIdentifier.asset_id).where(AssetIdentifier.normalized_value.contains(q.strip().upper()))
            stmt = stmt.where(Asset.id.in_(ids))
        return [asset_view(a) for a in db.scalars(stmt).all()]

    @api.get("/api/v1/assets/{asset_id}")
    def asset_detail(asset_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
        asset = db.get(Asset, asset_id)
        if not asset:
            raise HTTPException(404, detail={"code": "ASSET_NOT_FOUND"})
        events = db.scalars(select(AssetEvent).where(AssetEvent.asset_id == asset_id).order_by(AssetEvent.recorded_at, AssetEvent.id)).all()
        return {"asset": asset_view(asset), "events": [
            {"event_id": e.id, "type": e.event_type, "occurred_at": e.occurred_at,
             "recorded_at": e.recorded_at, "note": e.note, "actor_id": e.actor_id,
             "evidence_ref": e.evidence_ref, "evidence_sha256": e.evidence_sha256,
             "new_status": e.new_status, "version_after": e.version_after}
            for e in events
        ]}

    def apply_event(asset_id: str, data, user: User, db: Session, event_type: str, new_status: str | None = None):
        # Reintentos idénticos se aceptan sin aplicar dos veces; divergencias se rechazan.
        event_id = str(data.event_id)
        fingerprint = hashlib.sha256(json.dumps({
            "event_type": event_type, "payload": data.model_dump(mode="json"), "actor_id": user.id
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        existing = db.get(AssetEvent, event_id)
        if existing:
            if existing.asset_id == asset_id and existing.request_fingerprint == fingerprint:
                return {"event_id": event_id, "version": existing.version_after, "replayed": True}
            raise HTTPException(409, detail={"code": "EVENT_ID_CONFLICT"})
        asset = db.scalar(select(Asset).where(Asset.id == asset_id).with_for_update())
        if asset is None:
            raise HTTPException(404, detail={"code": "ASSET_NOT_FOUND"})
        if new_status is not None and asset.version != data.expected_version:
            raise HTTPException(409, detail={"code": "STALE_ASSET_VERSION", "current_version": asset.version})
        asset.version += 1
        if new_status:
            asset.status = new_status
        db.add(AssetEvent(
            id=event_id, asset_id=asset.id, actor_id=user.id, event_type=event_type,
            occurred_at=data.occurred_at, note=data.note, evidence_ref=data.evidence_ref,
            evidence_sha256=data.evidence_sha256.lower() if data.evidence_sha256 else None,
            request_fingerprint=fingerprint, version_after=asset.version, new_status=new_status,
        ))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Una segunda petición concurrente con el mismo UUID puede haber confirmado.
            existing = db.get(AssetEvent, event_id)
            if existing and existing.asset_id == asset_id and existing.request_fingerprint == fingerprint:
                return {"event_id": event_id, "version": existing.version_after, "replayed": True}
            raise HTTPException(409, detail={"code": "EVENT_ID_CONFLICT"})
        return {"event_id": event_id, "version": asset.version, "replayed": False}

    @api.post("/api/v1/assets/{asset_id}/observations")
    def report_observation(
        asset_id: str, data: ReportObservation,
        user: User = Depends(current_user), db: Session = Depends(db_session),
    ):
        require_role(user, "OPERATIVO", "INVENTARIOS")
        return apply_event(asset_id, data, user, db, data.event_type.value)

    @api.post("/api/v1/assets/{asset_id}/decisions")
    def confirm_status(
        asset_id: str, data: ConfirmStatus,
        user: User = Depends(current_user), db: Session = Depends(db_session),
    ):
        require_role(user, "INVENTARIOS")
        return apply_event(asset_id, data, user, db, "STATUS_CONFIRMED", data.new_status.value)

    @api.get("/api/v1/i18n/{language}")
    def translations(language: str):
        if language not in {"es-MX", "en", "zh-CN"}:
            raise HTTPException(404, detail={"code": "LANGUAGE_UNSUPPORTED"})
        file = Path(__file__).parent / "locales" / (language + ".json")
        return json.loads(file.read_text(encoding="utf-8"))

    # La interfaz ligera sirve como demostración funcional; las operaciones
    # de negocio se autorizan siempre en los endpoints, nunca desde el HTML.
    web_dir = Path(__file__).parent / "web"
    api.mount("/static", StaticFiles(directory=web_dir), name="static")

    @api.get("/", include_in_schema=False)
    def homepage():
        return FileResponse(web_dir / "index.html")

    @api.middleware("http")
    async def secure_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    return api
