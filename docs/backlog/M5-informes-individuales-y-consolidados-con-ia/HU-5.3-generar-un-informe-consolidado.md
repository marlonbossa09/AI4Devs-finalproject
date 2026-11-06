# HU-5.3 — Generar un informe consolidado

| | |
|---|---|
| **Módulo** | M5 — Informes individuales y consolidados con IA |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-03, RN-54, RN-29, RN-36, RN-86, RN-88, RN-101 |
| **Requisitos** | RF-30, RF-48, RF-83, RF-98, RF-111 |
| **Dependencias** | HU-5.1, HU-5.2 |
| **Decisiones pendientes** | PA-09 (proveedor de IA, conservación y tratamiento de datos) |

## Historia

Como supervisor, quiero un informe consolidado de mi equipo para un período, para disponer del resumen del equipo sin elaborarlo a mano.

## Criterios de aceptación

- **CA-168** · positivo · RF-30 — DADO un supervisor CUANDO genera el informe consolidado de su equipo para un período ENTONCES lo obtiene.
- **CA-169** · permisos · RF-30 — DADO un colaborador CUANDO intenta generar un informe consolidado ENTONCES no puede.
- **CA-170** · permisos · RF-30 — DADO un supervisor CUANDO intenta generar el informe consolidado de otro equipo ENTONCES no puede.
- **CA-171** · positivo · RF-48 — DADO un informe consolidado generado CUANDO se lee ENTONCES indica el período que cubre y su fecha de generación.
- **CA-228** · permisos · RF-83 — DADO una persona trasladada de T a U CUANDO el supervisor de U genera el informe consolidado de un período que incluye fechas anteriores al traslado ENTONCES no incluye los registros de esa persona de esas fechas.
- **CA-229** · permisos · RF-83 — DADO una persona trasladada de T a U CUANDO el supervisor de T genera el informe consolidado de un período que incluye fechas posteriores al traslado ENTONCES no incluye los registros de esa persona de esas fechas.
- **CA-235** · permisos · RF-98 — DADO el informe consolidado del equipo nuevo CUANDO incluye una actividad heredada ENTONCES no muestra un estado al corte derivado exclusivamente de registros de otro equipo.
- **CA-277** · permisos · RF-111 — DADO una actividad iniciada en el equipo T con avances posteriores del equipo U CUANDO el supervisor de U genera el informe consolidado de su equipo ENTONCES el informe no incluye su título original ni los motivos de bloqueo de T.
- Los informes usan la misma política de referencia neutral que las vistas (RN-101).
