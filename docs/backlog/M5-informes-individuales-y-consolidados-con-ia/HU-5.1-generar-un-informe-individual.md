# HU-5.1 — Generar un informe individual

| | |
|---|---|
| **Módulo** | M5 — Informes individuales y consolidados con IA |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-03, RN-29, RN-30, RN-36, RN-53, RN-56, RN-84, RN-86, RN-88, RN-90, RN-101 |
| **Requisitos** | RF-29, RF-48, RF-49, RF-50, RF-75, RF-96, RF-94, RF-93, RF-100, RF-111 |
| **Dependencias** | HU-1.4, HU-5.2 |
| **Decisiones pendientes** | PA-09 (proveedor de IA, conservación y tratamiento de datos) |

## Historia

Como propietario de mis registros o supervisor autorizado de mi equipo, quiero generar un informe individual de un período, para disponer del resumen de la actividad sin elaborarlo a mano.

## Criterios de aceptación

- **CA-152** · positivo · RF-29 — DADO una persona propietaria de registros CUANDO genera su propio informe individual de un período ENTONCES obtiene el informe.
- **CA-153** · positivo · RF-29 — DADO un supervisor CUANDO genera el informe individual de una persona de su equipo ENTONCES lo obtiene.
- **CA-154** · permisos · RF-29 — DADO un compañero que no es el propietario ni su supervisor CUANDO intenta generar el informe individual ENTONCES no puede.
- **CA-155** · positivo · RF-48 — DADO un informe generado CUANDO se lee ENTONCES indica el período que cubre y su fecha de generación.
- **CA-156** · positivo · RF-49 — DADO un informe generado por una persona CUANDO se revisa su contenido ENTONCES solo incluye información que esa persona está autorizada a consultar, correspondiente al período solicitado.
- **CA-157** · permisos · RF-49 — DADO una persona que cambió de equipo durante el período CUANDO el supervisor de su equipo actual genera su informe ENTONCES solo incluye los registros que pertenecen históricamente a su equipo.
- **CA-158** · positivo · RF-75 — DADO un informe generado CUANDO lo consulto ENTONCES se muestra en pantalla y no se edita.
- **CA-159** · límite · RF-75 — DADO un informe generado CUANDO salgo de él ENTONCES no queda guardado automáticamente en un historial de informes.
- **CA-160** · positivo · RF-50 — DADO un informe ya generado CUANDO lo genero de nuevo ENTONCES obtengo un informe nuevo con su propia fecha de generación.
- **CA-224** · permisos · RF-96 — DADO una persona P que ya no integra el equipo T CUANDO el supervisor de T genera el informe individual de P ENTONCES el informe solo incluye los registros históricos de T y los períodos para los que T conserva autorización.
- **CA-225** · negativo · RF-96 — DADO el informe individual de P generado por el supervisor de T CUANDO se revisa su contenido ENTONCES no incluye información posterior al traslado ni del equipo nuevo.
- **CA-226** · permisos · RF-94 — DADO el supervisor del equipo nuevo CUANDO genera el informe individual de P ENTONCES no incluye los detalles históricos del equipo anterior y puede incluir la referencia mínima de sus actividades pendientes.
- **CA-227** · positivo · RF-93 — DADO P trasladada CUANDO genera su propio informe de un período que abarca ambos equipos ENTONCES incluye todos sus registros del período.
- **CA-234** · permisos · RF-100 — DADO el supervisor del equipo nuevo CUANDO genera el informe individual de P de un período con una actividad heredada ENTONCES el informe no incluye un estado al corte derivado exclusivamente de registros de otro equipo.
- **CA-276** · permisos · RF-111 — DADO una actividad iniciada en el equipo T con avances posteriores del equipo U CUANDO el supervisor de U genera el informe individual de su propietaria ENTONCES el informe no incluye su título original ni los motivos de bloqueo de T.

## Notas

- La dependencia técnica es el proveedor del servicio de IA y el tratamiento de los datos (PA-09).
- Los informes usan la misma política de referencia neutral que las vistas (RN-101).
