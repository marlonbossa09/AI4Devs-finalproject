# HU-4.2 — Consultar el histórico por colaborador y fechas

| | |
|---|---|
| **Módulo** | M4 — Consulta histórica y supervisión |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-25, RN-05, RN-36 |
| **Requisitos** | RF-26 |
| **Dependencias** | HU-4.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador o supervisor, quiero filtrar el histórico por colaborador y rango de fechas laborales, para recuperar lo que se hizo en un período.

## Criterios de aceptación

- **CA-134** · positivo · RF-26 — DADO el histórico CUANDO filtro por un colaborador y un rango de fechas laborales ENTONCES obtengo sus bitácoras de ese rango.
- **CA-135** · permisos · RF-26 — DADO el histórico CUANDO filtro por un colaborador ENTONCES solo obtengo los registros que estoy autorizado a consultar.
- **CA-136** · límite · RF-26 — DADO el histórico CUANDO intento buscar por texto ENTONCES no existe esa búsqueda.
- **CA-299** · negativo · RF-26 — DADO el histórico CUANDO intento consultar sin indicar un rango de fechas laborales ENTONCES no se permite.
- **CA-300** · positivo · RF-26 — DADO el histórico CUANDO indico un rango de fechas laborales sin indicar un colaborador ENTONCES obtengo solo los registros que estoy autorizado a consultar, de las personas que puedo consultar.
- El rango de fechas laborales es obligatorio; el colaborador es opcional (RN-25).
