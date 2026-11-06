# SMARTWORK — Tickets de implementación: índice

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, tickets documentales para la fase de implementación |
| **Versión** | 0.1 |
| **Fecha** | 2026-11-06 |
| **Fuente** | `docs/backlog/` (historias y criterios), `docs/api/` (contratos), `docs/modelo-datos/modelo-datos.md`, `docs/arquitectura/` |

Los tickets están organizados por capa: [base de datos](base-de-datos.md), [backend](backend.md) y [frontend](frontend.md). Son 34 tickets para las cinco funcionalidades del MVP. Cada ticket agrupa los criterios de aceptación por historia; **no hay un ticket por criterio**, y las operaciones de un mismo contrato no se repiten en varios tickets. En la fase de documentación no se ha implementado nada.

## Flujo principal de extremo a extremo (FP-1)

El primer objetivo de implementación es un recorrido completo que atraviesa los módulos y valida la arquitectura:

| Paso | Qué ocurre | Contratos | Tickets |
|---|---|---|---|
| 1 | La provisión crea un equipo, su supervisor y un colaborador con datos ficticios | M1-02a, M1-02b | BE-04, DB-01, DB-07 |
| 2 | El colaborador inicia sesión | M1-01a, M1-01c | BE-03, FE-02, FE-03, DB-02 |
| 3 | Abre su bitácora de hoy y planifica una actividad | M2-01b, M2-03 | BE-06, BE-07, FE-04, FE-05, DB-03 |
| 4 | Registra un avance con su estado y descripción | M2-05 | BE-08, FE-05 |
| 5 | Escribe el resumen y cierra la jornada | M2-02, M3-01 | BE-06, BE-09, BE-10, FE-04, DB-04 |
| 6 | El supervisor inicia sesión y consulta la vista de su equipo del período | M1-01a, M4-03 | BE-13, BE-02, FE-08 |

Cubre M1, M2, M3 y M4 con prioridad P0 y ejercita la autorización por equipo histórico, la auditoría y el estado actual. M5 queda en P1 (agregaciones deterministas, BE-15) y P2 (narrativa con IA, BE-16 y FE-10), porque su integración depende de decisiones aún abiertas del proveedor.

## ¿Es un MVP viable?

| Funcionalidad | Qué aporta al flujo | Prioridad |
|---|---|---|
| M1 Autenticación, usuarios y equipos | Acceso, pertenencia a equipos, provisión | P0 (sesión y pertenencias); P1 (códigos de acceso y recuperación) |
| M2 Bitácoras híbridas | Planificar, registrar avances y resumen | P0 |
| M3 Seguimiento y auditoría | Estado actual, cierre y auditoría | P0 (cierre y registro de auditoría); P1 (reapertura, correcciones, marca de error) |
| M4 Consulta y supervisión | Vista del equipo para el supervisor | P0 (vista de supervisión); P1 (lectura de compañeros e histórico) |
| M5 Informes con IA | Informes individuales y consolidados | P1 (núcleo determinista); P2 (narrativa con IA, condicionada) |

El flujo FP-1 resuelve el problema central (registrar lo planificado y lo hecho, y que el supervisor lo consulte) sin depender de la IA ni del envío de códigos.

## Prioridades

- **P0:** necesario para el flujo FP-1. Se implementa primero.
- **P1:** completa el núcleo del MVP.
- **P2:** condicionado a decisiones abiertas o posterior al flujo principal.

## Orden sugerido

1. **Fundamentos (P0):** DB-01 a DB-04, DB-07, BE-01, BE-02, FE-01.
2. **Acceso (P0):** BE-03, BE-04, FE-02, FE-03.
3. **Jornada (P0):** BE-06 a BE-10, FE-04, FE-05.
4. **Supervisión (P0):** BE-13, FE-08. Con esto queda completo FP-1.
5. **Núcleo completo (P1):** DB-05, DB-06, BE-05, BE-11, BE-12, BE-14, BE-15, FE-06, FE-07, FE-09, FE-11.
6. **Informes con IA (P2):** BE-16, FE-10.

## Todos los tickets

| Ticket | Título | Capa | Prioridad | Dependencias |
|---|---|---|---|---|
| [DB-01](base-de-datos.md) | Personas, equipos y pertenencias | Base de datos | P0 | ninguna |
| [DB-02](base-de-datos.md) | Identidad, sesiones, códigos y operadores | Base de datos | P0 | DB-01 |
| [DB-03](base-de-datos.md) | Bitácoras, actividades, planificaciones y avances | Base de datos | P0 | DB-01 |
| [DB-04](base-de-datos.md) | Auditoría de solo anexado | Base de datos | P0 | DB-03 |
| [DB-05](base-de-datos.md) | Registro de claves de idempotencia | Base de datos | P1 | DB-01 |
| [DB-06](base-de-datos.md) | Índices y consultas históricas | Base de datos | P1 | DB-01, DB-03, DB-04 |
| [DB-07](base-de-datos.md) | Datos ficticios para el flujo principal | Base de datos | P0 | DB-01, DB-02, DB-03 |
| [BE-01](backend.md) | Estructura del servicio y convenciones comunes | Backend | P0 | ninguna |
| [BE-02](backend.md) | Autorización histórica centralizada | Backend | P0 | BE-01, DB-01, DB-06 |
| [BE-03](backend.md) | Autenticación con sesiones revocables | Backend | P0 | BE-01, BE-02, DB-02 |
| [BE-04](backend.md) | Provisión: personas, equipos y pertenencias | Backend | P0 | BE-01, BE-02, DB-01, DB-04 |
| [BE-05](backend.md) | Códigos de acceso, recuperación y desactivación | Backend | P1 | BE-03, BE-04, DB-02 |
| [BE-06](backend.md) | Bitácoras y resumen | Backend | P0 | BE-02, DB-03, DB-04 |
| [BE-07](backend.md) | Actividades y planificación | Backend | P0 | BE-06, DB-03 |
| [BE-08](backend.md) | Avances, secuencia y estado actual | Backend | P0 | BE-07, DB-03 |
| [BE-09](backend.md) | Cierre y reapertura de jornada | Backend | P0 (cierre) y P1 (reapertura) | BE-06, BE-08 |
| [BE-10](backend.md) | Auditoría: registro y consulta | Backend | P0 (registro transaccional) y P1 (consulta) | DB-04, BE-02 |
| [BE-11](backend.md) | Correcciones, reactivación y marca de error | Backend | P1 | BE-08, BE-09, BE-10 |
| [BE-12](backend.md) | Consulta de equipo e histórico | Backend | P1 | BE-02, BE-06 |
| [BE-13](backend.md) | Vista de supervisión e historial de actividad | Backend | P0 (vista) y P1 (historial) | BE-02, BE-08 |
| [BE-14](backend.md) | Idempotencia y concurrencia | Backend | P1 | BE-01, DB-05 |
| [BE-15](backend.md) | Informes: núcleo determinista | Backend | P1 | BE-02, BE-08 |
| [BE-16](backend.md) | Informes: generación de texto y fallos | Backend | P2 | BE-15 y las decisiones de ADR-003 |
| [FE-01](frontend.md) | Estructura del cliente y acceso a la API | Frontend | P0 | BE-01 |
| [FE-02](frontend.md) | Acceso: sesión, primer acceso y recuperación | Frontend | P0 (inicio de sesión) y P1 (primer acceso y recuperación) | FE-01, BE-03 (y BE-05 para primer acceso y recuperación) |
| [FE-03](frontend.md) | Navegación y contexto por rol | Frontend | P0 | FE-02, BE-03 |
| [FE-04](frontend.md) | Mi jornada: bitácora, resumen, cierre y reapertura | Frontend | P0 | FE-01, BE-06, BE-09 |
| [FE-05](frontend.md) | Actividades: planificar, registrar avances, listar y detalle | Frontend | P0 | FE-04, BE-07, BE-08 |
| [FE-06](frontend.md) | Correcciones, reactivación y marca de error | Frontend | P1 | FE-05, BE-11 |
| [FE-07](frontend.md) | Consulta de equipo e histórico | Frontend | P1 | FE-01, BE-12 |
| [FE-08](frontend.md) | Vista de supervisión e historial de actividad | Frontend | P0 (vista) y P1 (historial) | FE-03, BE-13 |
| [FE-09](frontend.md) | Auditoría de un registro | Frontend | P1 | FE-01, BE-10 |
| [FE-10](frontend.md) | Informes | Frontend | P2 | FE-01, BE-15 (BE-16 para la narrativa) |
| [FE-11](frontend.md) | Accesibilidad y calidad de la interfaz | Frontend | P1 | FE-01 |

## Definición de terminado común

Aplica a todos los tickets, además de sus condiciones específicas:

- El código pasa la revisión de una pull request.
- Las pruebas automatizadas de los criterios de aceptación del ticket pasan.
- La operación respeta el contrato de `docs/api/` (entradas, respuestas, errores y auditoría).
- No hay credenciales, claves ni datos reales en el repositorio.
- La documentación afectada está actualizada.

## Cobertura de historias

Las 33 historias están cubiertas por al menos un ticket:

| Historias | Tickets |
|---|---|
| HU-1.1 | BE-03, FE-02, FE-03, DB-02 |
| HU-1.2, HU-1.3 | BE-04, DB-01 |
| HU-1.4 | BE-02, DB-06 |
| HU-1.5, HU-1.6, HU-1.7 | BE-04, BE-05, FE-02, DB-01, DB-02 |
| HU-2.1 a HU-2.9 | BE-06, BE-07, BE-08, FE-04, FE-05, DB-03 |
| HU-3.1, HU-3.2 | BE-07, BE-08, FE-05 |
| HU-3.3, HU-3.4 | BE-09, BE-11, FE-04, FE-06 |
| HU-3.5, HU-3.6 | BE-10, FE-09, DB-04 |
| HU-3.7, HU-3.8 | BE-11, FE-06 |
| HU-4.1, HU-4.2 | BE-12, FE-07 |
| HU-4.3, HU-4.4 | BE-13, FE-08, DB-06 |
| HU-5.1 a HU-5.5 | BE-15, BE-16, FE-10 |

## Trazabilidad

Ticket, historia (HU), criterio (CA) y contrato están enlazados en cada ficha. Las historias y los criterios están en [docs/backlog/](../indice.md) y los contratos en [docs/api/](../../api/indice.md).
