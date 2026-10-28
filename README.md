# CycleTracking

Sistema de Control Operativo e Inventarios; desarrollo propio y modular.

## Dirección del proyecto (28 de octubre de 2026)

- **Control Operativo**: recepción, procesamiento local y validación de reportes de campo; tendido, levantado, rotación y observaciones.
- **Control de Inventarios**: autoridad sobre altas de equipos, existencias, custodia, investigaciones y decisiones patrimoniales.
- **Historial inalterado**: el estado actual es una proyección; ningún reporte elimina hechos o evidencia anteriores.
- **Colaboración**: una única base oficial PostgreSQL, API con permisos y control de concurrencia.
- **Procesamiento distribuido**: Excel, macros migradas y cruces pesados se procesarán en PCs de oficina; la API sólo recibe transacciones verificadas.
- **Server Oficina**: consulta e indexa resultados confirmados; no mantiene una segunda autoridad de inventarios.
- **Respaldo**: originales y respaldos en QNAP, copia versionada en Synology; prueba de restauración pendiente.
- **Idiomas**: español de México, inglés y chino simplificado desde el inicio.
- **Seguridad**: sin credenciales por defecto, sin datos reales en Git y sin subir archivos sin validaciones.

Este repositorio es nuevo. NodeTrack, macros anteriores y Server Oficina se consultarán **como referencias**, sin copiar estructuras completas ni dependencias vulnerables. Los contratos entre sistemas se versionarán.

El trabajo inicial se desarrollará en una rama y se revisará antes de declararlo apto para operación real.
