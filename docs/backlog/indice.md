# SMARTWORK — Índice de historias de usuario

| | |
|---|---|
| **Estado** | Borrador para validación |
| **Versión** | 0.9 |
| **Fecha** | 2026-11-06 |
| **Base** | `docs/producto/alcance-mvp.md` (versión 0.14), `docs/producto/prd.md` (versión 0.12) y `docs/modelo-datos/modelo-datos.md` (propuesta) |

Las historias son la descomposición de los cinco módulos del MVP. No añaden funcionalidades.

## Cómo se lee la trazabilidad

- **RN → RF:** en el PRD, sección 6.8.
- **RF → HU:** cada historia lista los requisitos que cubre.
- **HU → CA:** cada criterio de aceptación (CA) pertenece a una sola historia y cita el requisito que verifica.
- Los criterios añadidos en la versión 0.2 continúan la numeración (CA-176 a CA-301) para no renumerar los existentes, por eso algunas historias tienen criterios en dos tramos.

## Estados de preparación

| Estado | Significado |
|---|---|
| **Lista para diseño técnico** | La especificación funcional está completa y no depende de ninguna decisión pendiente que afecte a su comportamiento. |
| **Lista con dependencia técnica pendiente** | La especificación funcional está completa, pero su implementación depende de una decisión técnica o de privacidad pendiente, identificada en la historia. |

Ninguna historia está condicionada funcionalmente: no hay criterios inventados para comportamientos sin aprobar. Las decisiones abiertas que afectan a una historia sin cambiar sus criterios se indican como *decisiones pendientes*.

## Historias

### M1 — Autenticación, usuarios y equipos

| ID | Título | Estado | CA | Decisiones pendientes |
|---|---|---|---|---|
| HU-1.1 | Identificarme para acceder | Lista con dependencia técnica pendiente | CA-01 a CA-05 | PA-12 |
| HU-1.2 | Pertenecer a un único equipo con un único supervisor | Lista para diseño técnico | CA-06 a CA-10, CA-240 a CA-242 | — |
| HU-1.3 | Asignar pertenencias y conservar las anteriores | Lista para diseño técnico | CA-11 a CA-14, CA-243 a CA-248, CA-278 a CA-279 | PA-25 |
| HU-1.4 | Visibilidad histórica de los registros tras un cambio de equipo | Lista para diseño técnico | CA-15 a CA-21, CA-176 a CA-178, CA-212 a CA-217, CA-249 | — |
| HU-1.5 | Crear usuarios y equipos y entregar el primer acceso | Lista con dependencia técnica pendiente | CA-22 a CA-26, CA-250 a CA-253 | PA-12 |
| HU-1.6 | Recuperar el acceso | Lista con dependencia técnica pendiente | CA-27 a CA-28, CA-254 | PA-12 |
| HU-1.7 | Dar de baja lógicamente a una persona | Lista para diseño técnico | CA-29 a CA-31, CA-255 a CA-262 | PA-04, PA-12, PA-24 |

### M2 — Bitácoras laborales híbridas

| ID | Título | Estado | CA | Decisiones pendientes |
|---|---|---|---|---|
| HU-2.1 | Tener mi bitácora por fecha laboral | Lista para diseño técnico | CA-32 a CA-36, CA-280 a CA-282 | — |
| HU-2.2 | Planificar mis actividades | Lista para diseño técnico | CA-37 a CA-41, CA-263, CA-295 | — |
| HU-2.3 | Planificar jornadas futuras | Lista para diseño técnico | CA-42 a CA-44, CA-179 a CA-184, CA-209 a CA-210 | — |
| HU-2.4 | Registrar avances conservando el estado histórico | Lista para diseño técnico | CA-45 a CA-48 | — |
| HU-2.5 | Bloquear una actividad con motivo | Lista para diseño técnico | CA-49 a CA-52 | — |
| HU-2.6 | Registrar actividades no planificadas | Lista para diseño técnico | CA-53 a CA-58, CA-296 | — |
| HU-2.7 | Registrar jornadas pasadas | Lista para diseño técnico | CA-59 a CA-65, CA-264 | — |
| HU-2.8 | Cambiar el estado de una actividad y describir el avance | Lista para diseño técnico | CA-66 a CA-72 | — |
| HU-2.9 | Estado actual y orden de los avances | Lista para diseño técnico | CA-73 a CA-80, CA-185 a CA-186 | — |

### M3 — Seguimiento de actividades y auditoría

| ID | Título | Estado | CA | Decisiones pendientes |
|---|---|---|---|---|
| HU-3.1 | Continuar una actividad sin duplicarla | Lista para diseño técnico | CA-81 a CA-85, CA-265 | — |
| HU-3.2 | Seleccionar la actividad que se continúa | Lista para diseño técnico | CA-86 a CA-88 | — |
| HU-3.3 | Cerrar mi jornada | Lista para diseño técnico | CA-89 a CA-98, CA-283 | — |
| HU-3.4 | Reabrir y corregir mi bitácora cerrada | Lista para diseño técnico | CA-99 a CA-104, CA-266, CA-284 | PA-04 |
| HU-3.5 | Auditar las modificaciones de jornadas pasadas | Lista para diseño técnico | CA-105 a CA-107, CA-267, CA-293 a CA-294 | PA-06 |
| HU-3.6 | Consultar la auditoría | Lista para diseño técnico | CA-108 a CA-114, CA-285 a CA-286 | PA-06 |
| HU-3.7 | Corregir una actividad registrada por error | Lista para diseño técnico | CA-115 a CA-123, CA-268, CA-287 a CA-290, CA-297 a CA-298 | — |
| HU-3.8 | Reactivar una actividad Completada | Lista para diseño técnico | CA-124 a CA-129, CA-187 a CA-192, CA-203 a CA-208, CA-211, CA-236 a CA-239, CA-269 a CA-271 | — |

### M4 — Consulta histórica y supervisión

| ID | Título | Estado | CA | Decisiones pendientes |
|---|---|---|---|---|
| HU-4.1 | Consultar las bitácoras de mi equipo | Lista para diseño técnico | CA-130 a CA-133, CA-193 a CA-194, CA-291 | — |
| HU-4.2 | Consultar el histórico por colaborador y fechas | Lista para diseño técnico | CA-134 a CA-136, CA-299 a CA-300 | — |
| HU-4.3 | Supervisar mi equipo en un período | Lista para diseño técnico | CA-137 a CA-147, CA-195 a CA-198, CA-218 a CA-223, CA-230 a CA-233, CA-272 a CA-274, CA-301 | — |
| HU-4.4 | Consultar el historial de las actividades de mi equipo | Lista para diseño técnico | CA-148 a CA-151, CA-275, CA-292 | — |

### M5 — Informes individuales y consolidados con IA

| ID | Título | Estado | CA | Decisiones pendientes |
|---|---|---|---|---|
| HU-5.1 | Generar un informe individual | Lista con dependencia técnica pendiente | CA-152 a CA-160, CA-224 a CA-227, CA-234, CA-276 | PA-09 |
| HU-5.2 | Informes apoyados en los registros | Lista con dependencia técnica pendiente | CA-161 a CA-167 | PA-09 |
| HU-5.3 | Generar un informe consolidado | Lista con dependencia técnica pendiente | CA-168 a CA-171, CA-228 a CA-229, CA-235, CA-277 | PA-09 |
| HU-5.4 | Informe cuando faltan registros | Lista con dependencia técnica pendiente | CA-172 a CA-173, CA-199 a CA-202 | PA-09 |
| HU-5.5 | Servicio de IA no disponible | Lista con dependencia técnica pendiente | CA-174 a CA-175 | PA-09 |

## Resumen

| Concepto | Cantidad |
|---|---|
| Historias | 33 |
| Listas para diseño técnico | 25 |
| Listas con dependencia técnica pendiente | 8 (HU-1.1, 1.5, 1.6 y HU-5.1 a 5.5) |
| Condicionadas funcionalmente | 0 |
| Criterios de aceptación | 301 |
| Listas para diseño técnico con una decisión pendiente que no cambia sus criterios | 5 (HU-1.3, 1.7, 3.4, 3.5 y 3.6) |
| Listas para diseño técnico sin ninguna decisión pendiente asociada | 20 |

## Requisitos no funcionales transversales

Tres requisitos no funcionales confirmados no tienen un criterio de aceptación propio porque no pertenecen a una sola historia:

| Requisito | Cómo se cubre |
|---|---|
| RNF-01 (control de acceso) | Mediante los criterios de tipo *permisos* repartidos por las historias, y mediante la matriz de permisos del PRD (anexo B). Se verifica con una matriz de pruebas por rol, acción y equipo. |
| RNF-04 (fiabilidad de la IA) | Se verifica con CA-161 sobre una muestra de informes (HU-5.2). |
| RNF-05 (plataforma web) | Es una restricción del producto: se comprueba al ejecutar el producto desde un navegador. Los navegadores soportados están por definir (PA-13). |

## Decisiones abiertas que afectan a las historias

| Punto | Afecta a | Qué falta |
|---|---|---|
| PA-04 | HU-1.7, HU-3.4 | Cómo corregir la bitácora de una persona dada de baja o sin acceso. |
| PA-06 | HU-3.5, HU-3.6 | Política de retención de la auditoría. |
| PA-09 | HU-5.1 a HU-5.5 | Proveedor de IA, conservación y tratamiento de datos, marco legal. |
| PA-12 | HU-1.1, HU-1.5, HU-1.6, HU-1.7 | Detalles del acceso inicial y de la recuperación; reactivación administrativa del acceso; cómo se identifica a quien opera la provisión. |
| PA-24 | HU-1.7 | Reincorporación de personas dadas de baja. |
| PA-25 | HU-1.3 | Ajustes históricos excepcionales de pertenencia y altas históricas. |

## Registro de modificaciones

| Versión | Cambios |
|---|---|
| 0.9 | Se incorporan RN-111 a RN-113 y RF-121 a RF-123 (CA-293 a CA-301, 9 criterios nuevos) en HU-2.2, HU-2.6, HU-3.5, HU-3.7, HU-4.2 y HU-4.3. Se resuelve PA-26 (HU-4.3 y HU-4.4 sin decisiones pendientes) y se acota PA-06. |
| 0.8 | Se incorporan RN-107 a RN-110, RF-117 a RF-120 y RNF-13 (CA-280 a CA-292, 13 criterios nuevos) en HU-2.1, HU-3.3, HU-3.4, HU-3.6, HU-3.7, HU-4.1 y HU-4.4. Se reescriben CA-230 y CA-231 (el corte es el último día del período). Las demás historias no cambian. |
| 0.7 | Se añaden CA-278 y CA-279 a HU-1.3 para que RF-109 sea comprobable en altas futuras y cambios de rol programados. No se añaden reglas ni requisitos. |
| 0.6 | Se incorporan RN-94 a RN-106 y los requisitos RF-104 a RF-116 (CA-240 a CA-277, con 38 criterios nuevos). Se modifican HU-1.2 a HU-1.7, HU-2.2, HU-2.7, HU-3.1, HU-3.4, HU-3.5, HU-3.7, HU-3.8, HU-4.3, HU-4.4, HU-5.1 y HU-5.3. Se reescriben CA-29 (HU-1.7: ahora «con el acceso desactivado o sin pertenencia vigente… intenta operar»; antes «dada de baja… intenta identificarse») y CA-223 (HU-4.3: ya no «con todo su detalle»). Se añaden PA-24, PA-25 y PA-26 y se amplía PA-12. |
| 0.5 | Se resuelven PA-22 y PA-23 (RN-88 a RN-93). Se modifican HU-3.8 (CA-236 a CA-239), HU-4.3 (CA-230 a CA-233), HU-5.1 (CA-234) y HU-5.3 (CA-235). Las demás historias no cambian. |
| 0.4 | Se resuelve PA-21 (RN-81 a RN-87) y se confirma la regla de CA-207 (RN-79). Se modifican HU-1.4 (CA-212 a CA-217), HU-3.8 (CA-211), HU-4.3 (CA-218 a CA-223 y texto de CA-143), HU-5.1 (CA-224 a CA-227) y HU-5.3 (CA-228 y CA-229). Se añaden PA-22 y PA-23. Las demás historias no cambian. |
| 0.3 | Se resuelve PA-20: HU-2.3 (CA-209 y CA-210), HU-3.8 (CA-203 a CA-208) y HU-2.9 (sin decisiones pendientes). Se actualiza el texto de CA-199 y CA-200 de HU-5.4 (el informe deja claro que no representa información que nunca fue registrada). Se normalizan a DADO / CUANDO / ENTONCES 29 criterios de 17 historias, solo en su forma. PA-21 sigue abierto. |
| 0.2 | Se resuelven PA-17, PA-18 y PA-19. Se modifican HU-1.4, HU-2.3, HU-2.9, HU-3.8, HU-4.1, HU-4.3 y HU-5.4: se añaden los criterios CA-176 a CA-202 y se actualizan los textos de CA-172 y CA-173. Las demás historias no cambian. PA-18 deja de ser una decisión pendiente de HU-1.4 y HU-4.1; PA-19 deja de serlo de HU-5.4; PA-17 se sustituye por PA-20 en HU-2.3, HU-2.9 y HU-3.8. Se añade PA-21 a HU-4.3. |
| 0.1 | Versión inicial: 33 historias y 175 criterios. |
