# HU-1.6 — Recuperar el acceso

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-34, RN-33, RN-96 |
| **Requisitos** | RF-55, RF-106 |
| **Dependencias** | HU-1.5 |
| **Decisiones pendientes** | PA-12 (cómo se verifica la identidad de quien recupera el acceso, medio de entrega) |

## Historia

Como persona usuaria que ha perdido su acceso, quiero recuperarlo, para volver a usar el producto.

## Criterios de aceptación

- **CA-27** · positivo · RF-55 — DADO una persona que ha perdido su acceso CUANDO se ejecuta el procedimiento de recuperación de acceso para ella ENTONCES recupera el acceso.
- **CA-28** · permisos · RF-55 — DADO un supervisor CUANDO intenta recuperar el acceso de otra persona ENTONCES no dispone de esa función.
- **CA-254** · negativo · RF-106 — DADO una persona con el acceso desactivado administrativamente CUANDO completa el procedimiento de recuperación de acceso ENTONCES su acceso sigue desactivado.

## Notas

- La recuperación se hace mediante el mismo procedimiento de provisión controlada (RN-33, RN-34).
- No se definen criterios sobre la verificación de identidad ni sobre el medio de entrega: están pendientes (PA-12).
- La recuperación no reactiva un acceso desactivado administrativamente (RN-96). La operación para reactivarlo está pendiente de especificar (PA-12).
