# HU-1.1 — Identificarme para acceder

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-61, RN-11, RN-64 |
| **Requisitos** | RF-01, RF-02, RNF-08 |
| **Dependencias** | HU-1.5 (primer acceso) |
| **Decisiones pendientes** | PA-12 (detalles del acceso inicial y de la credencial) |

## Historia

Como persona usuaria, quiero identificarme antes de acceder al producto, para que solo vea y haga lo que mi rol me permite.

## Criterios de aceptación

- **CA-01** · negativo · RF-01 — DADO una persona que no se ha identificado CUANDO intenta acceder a una bitácora o a cualquier función del producto ENTONCES no se le muestra ningún dato.
- **CA-02** · negativo · RF-01 — DADO una persona que no se ha identificado CUANDO intenta generar un informe ENTONCES el informe no se genera.
- **CA-03** · permisos · RF-02 — DADO un colaborador identificado CUANDO accede al producto ENTONCES no dispone de la vista consolidada del equipo.
- **CA-04** · permisos · RF-02 — DADO un supervisor identificado CUANDO accede al producto ENTONCES dispone de la vista consolidada de su equipo.
- **CA-05** · límite · RNF-08 — DADO el uso de credenciales en el producto CUANDO se revisan las pantallas, los registros del sistema y los informes ENTONCES ninguno contiene credenciales en claro.

## Notas

- La dependencia técnica es el mecanismo de autenticación, que depende de los detalles pendientes del acceso inicial (PA-12). No se definen criterios sobre caducidad, credencial propia ni medio de entrega.
