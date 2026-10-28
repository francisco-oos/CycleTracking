"""Administración inicial local. Nunca se crean cuentas o contraseñas demo."""
from __future__ import annotations

import argparse
import getpass
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cycletracking.models import Base, User
from cycletracking.security import ROLES, hash_password


def main():
    parser = argparse.ArgumentParser(prog="cyclectl")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init-db", help="Crea las tablas de la primera alpha (no migraciones)")
    create = sub.add_parser("create-user", help="Crea una cuenta local (password solicitado sin eco)")
    create.add_argument("--username", required=True)
    create.add_argument("--role", choices=sorted(ROLES), required=True)
    args = parser.parse_args()
    url = os.getenv("CYCLE_DATABASE_URL")
    if not url:
        parser.error("Configura CYCLE_DATABASE_URL")
    engine = create_engine(url, pool_pre_ping=True)
    if args.action == "init-db":
        Base.metadata.create_all(engine)
        print("Esquema alpha inicial creado. Antes de producción: migraciones y backup.")
        return
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirm = getpass.getpass("Confirma contraseña: ")
    if password != confirm:
        parser.error("Las contraseñas no coinciden")
    with Session(engine) as db:
        if db.scalar(select(User).where(User.username == args.username)):
            parser.error("Ya existe este usuario")
        db.add(User(username=args.username, role=args.role, password_hash=hash_password(password)))
        db.commit()
    print("Usuario creado correctamente (no se imprimió ninguna contraseña).")


if __name__ == "__main__":
    main()
