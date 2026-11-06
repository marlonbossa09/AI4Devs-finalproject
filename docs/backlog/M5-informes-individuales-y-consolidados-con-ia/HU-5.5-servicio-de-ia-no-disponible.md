# HU-5.5 — Servicio de IA no disponible

| | |
|---|---|
| **Módulo** | M5 — Informes individuales y consolidados con IA |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-58 |
| **Requisitos** | RF-76 |
| **Dependencias** | HU-5.1 |
| **Decisiones pendientes** | PA-09 (proveedor de IA y condiciones del servicio) |

## Historia

Como persona que genera un informe, quiero saber que el informe no pudo generarse cuando el servicio de IA falla, para no confundir un contenido parcial con un informe completo.

## Criterios de aceptación

- **CA-174** · positivo · RF-76 — DADO que el servicio de IA no está disponible CUANDO genero un informe ENTONCES recibo el aviso de que el informe no pudo generarse.
- **CA-175** · negativo · RF-76 — DADO que el servicio de IA falla CUANDO genero un informe ENTONCES no se muestra contenido parcial como si fuera un informe completo.
