# Arquitectura inicial de CycleTracking (v0.1.0-alpha)

**Decisión:** repositorio nuevo, NodeTrack sólo como referencia. No mezclar su base SQLite de desarrollo ni sus paquetes npm en el nuevo producto.

## Propiedad del dato

- CycleTracking / perfil INVENTARIOS **confirma** identidad de activos, altas y estados patrimoniales.
- CycleTracking / perfil OPERATIVO registra hechos observados de campo. Un reporte de extravío NO confirma por sí solo baja, pérdida definitiva ni recuperación.
- El historial de `asset_events` nunca se sobreescribe para simular que un hecho no ocurrió.
- Cada cambio de estado confirmado exige versión esperada (`expected_version`). PostgreSQL bloquea la fila durante el cambio y rechaza versiones anteriores.
- Cada operación cliente incorpora un UUID estable (`event_id`), que permite reintentos sin doble aplicación; reutilizarlo con un payload diferente genera conflicto.
- Las consultas y datos se comparten mediante una API. Nunca entregar claves PostgreSQL a las estaciones.
- Los operadores pueden procesar archivos en sus equipos; la base autoritativa sólo registra resultados revisados, con permisos.

## Almacenamiento y conocimiento

- PostgreSQL en SSD del host central (Dell 7220 en piloto; host dedicado a evaluar para producción).
- QNAP: originales y respaldos consistentes; Synology: respaldo secundario con versiones y restauración ensayada.
- Server Oficina: índice de resultados **confirmados**, búsqueda, expedientes agregados y conocimiento; **no escribe directamente** en tablas de CycleTracking.
- Las evidencias reales NO se suben a GitHub. En esta alpha sólo existe la referencia documental (`evidence_ref`) y su hash declarado; la transferencia y validación real de archivos está pendiente.
- Primero desarrollaremos Inventarios y Control Operativo; después sus procesadores Python y Taller Portable; HSE será el segundo producto.

## Seguridad y operaciones

- Roles: `ADMIN` (administración técnica), `OPERATIVO` (observa), `INVENTARIOS` (alta y confirmación patrimonial). Ningún admin obtiene automáticamente permisos patrimoniales.
- Contraseñas Argon2; tokens opacos revocables SHA-256 en BD. Sin usuarios precargados.
- La interfaz sólo mantiene el token en memoria. El servidor sigue validando permisos en cada operación.
- La API se debe utilizar sólo en localhost durante las primeras pruebas. Antes de otros equipos: HTTPS, segmentación de red y protección de intentos de autenticación.
- Nunca abrir puerto 5432 ni la API a Internet.
- Esta alpha usa `init-db`; **falta Alembic y migración versionada** antes de producción.
- No se ha validado la concurrencia real con PostgreSQL, ni restauración QNAP/Synology, ni importadores reales.

## Contratos pendientes

- `POST /sync/events` y bandeja de salida transaccional para replicar eventos al índice de Server Oficina.
- Carga de archivos como **ingesta con vista previa, observaciones y confirmación**, sin sobrescribir originales.
- Referencias documentales con integridad verificada, ACL por documento, evidencias NAS y cadena de custodia.
- Inventario por cantidades, ubicaciones, responsables, custodia, líneas, estacas, lotes, proyectos, refacciones y requisiciones.
- Procesadores de SERCEL/INOVA, macros VBA migradas, CSV Topografía y cruces de series con ejemplos artificiales.
- Contrato SQLite portable Taller y reconciliación de paquetes por USB.
