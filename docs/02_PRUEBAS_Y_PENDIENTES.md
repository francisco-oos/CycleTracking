# Pruebas y criterios de salida (primer corte)

## Automatizadas
- No hay acceso a activos sin autenticación.
- Control Operativo y administrador técnico no pueden dar de alta equipos ni confirmar estados patrimoniales.
- Control de Inventarios puede dar de alta equipos; no pueden existir dos identificadores idénticos del mismo tipo.
- Reportar extravío NO equivale a confirmar pérdida.
- El mismo UUID reintentado no genera otro evento; reutilizar UUID con datos distintos produce 409.
- La confirmación exige la versión actual. La historia anterior permanece.
- Observación de "encontrado" NO cambia un estado oficial `MISSING`.
- Carga de diccionarios `es-MX`, `en`, `zh-CN` con las mismas claves.
- Caducidad y revocación de tokens.

## Pendientes de validar
1. Configurar PostgreSQL real y correr un ciclo con dos usuarios en computadoras distintas.
2. Pruebas concurrentes y carga; usar transacciones `SELECT ... FOR UPDATE` contra PostgreSQL.
3. Probar reinicios, cortes de red y sincronización reintentada.
4. Auditar inventarios y archivos históricos de campo; jamás subirlos al repositorio público.
5. Reproducir los resultados de macros y Python existentes sobre archivos ficticios comprobados.
6. Integrar transferencia de originales y restauración NAS.
7. Incorporar migraciones versionadas, cuotas, rate limiting y despliegue con TLS.
8. Evaluar traducciones humanas del glosario técnico español/inglés/chino.
9. Añadir importador, stock por cantidad, múltiples identificadores por activo y control de custodia.
