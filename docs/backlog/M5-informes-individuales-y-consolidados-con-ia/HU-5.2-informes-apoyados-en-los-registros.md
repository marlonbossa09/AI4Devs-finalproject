# HU-5.2 — Informes apoyados en los registros

| | |
|---|---|
| **Módulo** | M5 — Informes individuales y consolidados con IA |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-06, RN-26, RN-29, RN-31, RN-55, RN-60 |
| **Requisitos** | RF-32, RF-46, RF-47, RF-51, RF-74, RF-78, RNF-04, RNF-12 |
| **Dependencias** | HU-5.1 |
| **Decisiones pendientes** | PA-09 (proveedor de IA, conservación y tratamiento de datos) |

## Historia

Como persona que lee un informe, quiero que se apoye únicamente en los registros, para poder fiarme de él.

## Criterios de aceptación

- **CA-161** · positivo · RF-32 — DADO un informe CUANDO lo contrasto con los registros de su período ENTONCES cada hecho que afirma consta en ellos.
- **CA-162** · positivo · RF-46 — DADO un informe con datos calculados CUANDO lo leo ENTONCES se distinguen de los hechos registrados.
- **CA-163** · negativo · RF-47 — DADO un informe CUANDO se revisa su contenido ENTONCES no contiene valoraciones sobre personas ni rankings.
- **CA-164** · positivo · RF-51 — DADO los mismos registros autorizados CUANDO se calculan dos veces los indicadores cuantitativos ENTONCES el valor es el mismo y coincide con un recuento manual.
- **CA-165** · positivo · RF-74 — DADO un informe de un período con una actividad bloqueada CUANDO se genera ENTONCES muestra la actividad y su motivo de bloqueo.
- **CA-166** · límite · RNF-12 — DADO una bitácora cuyo texto libre contiene órdenes dirigidas al generador del informe CUANDO se genera un informe ENTONCES esas órdenes no alteran su comportamiento ni su contenido.
- **CA-167** · negativo · RF-78 — DADO una actividad marcada como registrada por error CUANDO se genera un informe ENTONCES no se cuenta en los indicadores del informe.

## Notas

- RNF-04 se verifica con CA-161 sobre una muestra de informes.
