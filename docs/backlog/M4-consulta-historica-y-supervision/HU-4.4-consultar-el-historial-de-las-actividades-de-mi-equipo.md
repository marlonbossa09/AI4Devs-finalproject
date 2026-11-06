# HU-4.4 — Consultar el historial de las actividades de mi equipo

| | |
|---|---|
| **Módulo** | M4 — Consulta histórica y supervisión |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-13, RN-17, RN-23, RN-48, RN-101 |
| **Requisitos** | RF-28, RF-25, RF-45, RF-111, RF-99 |
| **Dependencias** | HU-3.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como supervisor, quiero ver el historial de las actividades de mi equipo, para seguir su evolución sin modificarla.

## Criterios de aceptación

- **CA-148** · positivo · RF-28 — DADO un supervisor CUANDO abre una actividad de su equipo ENTONCES ve sus avances con su fecha laboral y su estado histórico.
- **CA-149** · permisos · RF-25 — DADO un supervisor CUANDO consulta los registros de su equipo ENTONCES los ve en modo lectura.
- **CA-150** · negativo · RF-25 — DADO un supervisor CUANDO intenta modificar un registro de su equipo ENTONCES no es posible.
- **CA-151** · negativo · RF-45 — DADO el historial que consulta el supervisor CUANDO se revisa su contenido ENTONCES no incluye clasificaciones, rankings ni puntuaciones de personas.
- **CA-275** · permisos · RF-111 — DADO una actividad iniciada en el equipo T con avances del equipo U CUANDO el supervisor de U consulta el historial de las actividades de su equipo ENTONCES no se muestra su título original.
- **CA-292** · permisos · RF-99 — DADO una actividad heredada pendiente sin avances autorizados para el equipo CUANDO el supervisor abre su historial ENTONCES solo ve la referencia mínima y ningún título, descripción, motivo ni estado al corte de otro equipo.
- Los títulos de actividades iniciadas en otro equipo no se muestran (RN-101): se usa la referencia neutral.
- Una actividad heredada sin avances autorizados solo se muestra mediante la referencia mínima (RN-89).
