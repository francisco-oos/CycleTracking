# Instalación para pruebas (no producción)

Python 3.11+ y PostgreSQL. No requiere Node.js.

En Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:CYCLE_DATABASE_URL = "postgresql+psycopg://cycle_app:CONTRASENA@127.0.0.1:5432/cycletracking"
cyclectl init-db
cyclectl create-user --username responsable-inv --role INVENTARIOS
cyclectl create-user --username operador-a --role OPERATIVO
python -m uvicorn cycletracking.app:create_app --factory --host 127.0.0.1 --port 8000
```

En Linux cambia la activación por `source .venv/bin/activate` y usa `export CYCLE_DATABASE_URL=...`. El usuario y la base PostgreSQL deben crearse con permisos propios (sin superusuario).

Abre `http://127.0.0.1:8000` para la interfaz de prueba. La API interactiva se encuentra en `/docs`.

```bash
python -m pytest -q
python -m compileall -q src
```

**Advertencias:** usar únicamente datos ficticios; proteger el tráfico antes de abrir acceso LAN; no usar `--host 0.0.0.0` sin TLS/red aislada; no almacenar datos reales en repositorios públicos. El esquema inicial se crea por CLI, no se migra automáticamente.
