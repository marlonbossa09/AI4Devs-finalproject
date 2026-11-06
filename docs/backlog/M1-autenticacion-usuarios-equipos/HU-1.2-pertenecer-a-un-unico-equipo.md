# HU-1.2 — Pertenecer a un único equipo con un único supervisor

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-15, RN-28, RN-37, RN-98 |
| **Requisitos** | RF-03, RF-35, RF-36, RF-67, RF-108 |
| **Dependencias** | HU-1.3 (cómo se asigna una pertenencia), HU-1.5 (provisión) |
| **Decisiones pendientes** | Ninguna |

## Historia

Como persona usuaria, quiero pertenecer a un único equipo con un único supervisor, para saber con quién comparto mi trabajo y quién lo supervisa.

## Criterios de aceptación

- **CA-06** · positivo · RF-03 — DADO una organización con varios equipos CUANDO se consulta su composición ENTONCES cada equipo agrupa a sus propias personas.
- **CA-07** · negativo · RF-35 — DADO una persona que pertenece a un equipo CUANDO se intenta mantener su pertenencia a otro equipo a la vez ENTONCES no es posible.
- **CA-08** · negativo · RF-36 — DADO un equipo que ya tiene supervisor CUANDO se intenta asignarle un segundo supervisor ENTONCES no es posible.
- **CA-09** · positivo · RF-67 — DADO un supervisor CUANDO se consulta la composición de su equipo ENTONCES figura como miembro del equipo que supervisa.
- **CA-10** · negativo · RF-67 — DADO un supervisor de un equipo CUANDO se intenta asignarle la supervisión de otro equipo ENTONCES no es posible.
- **CA-240** · negativo · RF-108 — DADO un equipo con colaboradores CUANDO se intenta finalizar la pertenencia de su único supervisor sin otro supervisor desde la misma fecha efectiva ENTONCES se rechaza sin modificar ninguna pertenencia.
- **CA-241** · negativo · RF-108 — DADO un equipo con colaboradores CUANDO se intenta trasladar a su único supervisor sin otro supervisor desde la misma fecha efectiva ENTONCES se rechaza sin modificar ninguna pertenencia.
- **CA-242** · positivo · RF-108 — DADO un equipo con colaboradores CUANDO se sustituye a su supervisor por otra persona que asume la supervisión desde la misma fecha efectiva ENTONCES se acepta y el equipo no queda ningún día sin supervisor.

## Notas

- Estos criterios describen invariantes de la organización. La forma de asignar pertenencias es la provisión controlada (HU-1.3 y HU-1.5).
- Un equipo puede estar incompleto durante su provisión; un equipo con colaboradores tiene siempre un supervisor válido (RN-98).
