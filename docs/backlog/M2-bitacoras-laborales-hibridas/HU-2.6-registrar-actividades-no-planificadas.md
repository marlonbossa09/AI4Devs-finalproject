# HU-2.6 — Registrar actividades no planificadas

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-20, RN-69, RN-24, RN-70, RN-08, RN-112 |
| **Requisitos** | RF-39, RF-80, RF-59, RF-122 |
| **Dependencias** | HU-2.1, HU-2.8 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero registrar trabajo que no había planificado, para distinguir lo previsto de lo que surgió durante la jornada.

## Criterios de aceptación

- **CA-53** · positivo · RF-39 — DADO mi bitácora CUANDO registro una actividad sin planificación previa ENTONCES se identifica como no planificada y se distingue de las planificadas.
- **CA-54** · positivo · RF-80 — DADO una actividad sin planificación previa CUANDO registro su primer avance con uno de los cuatro estados ENTONCES la actividad inicia con ese estado.
- **CA-55** · negativo · RF-80 — DADO una actividad sin planificación previa CUANDO su primer avance indica el estado Bloqueada sin motivo ENTONCES no se permite.
- **CA-56** · positivo · RF-80 — DADO una actividad sin planificación previa CUANDO su primer avance indica el estado Bloqueada con motivo ENTONCES se registra y el motivo consta.
- **CA-57** · límite · RF-39 — DADO una actividad identificada como no planificada CUANDO consulto su estado ENTONCES esa identificación no es un estado adicional y su estado es uno de los cuatro.
- **CA-58** · negativo · RF-59 — DADO una actividad sin planificación previa CUANDO su primer avance no tiene una descripción no vacía ENTONCES no se permite.
- **CA-296** · negativo · RF-122 — DADO mi bitácora CUANDO intento registrar una actividad no planificada con el título vacío o formado solo por espacios ENTONCES no se permite.
