# SMARTWORK — Documento de Requisitos del Producto (PRD)

| | |
|---|---|
| **Estado** | Borrador para revisión |
| **Versión** | 0.12 |
| **Fecha** | 2026-11-06 |
| **Base** | `docs/producto/alcance-mvp.md`, versión 0.14 |

Este documento define **qué** debe hacer SMARTWORK y **por qué**. No describe diseño técnico, estructura de datos ni interfaces de programación; esas decisiones se toman en fases posteriores.

## Leyenda de estados

| Marca | Significado |
|---|---|
| `[CONFIRMADO]` | Aprobado por la persona responsable del producto (reglas `RN-XX` del documento de alcance). Solo esto constituye un requisito en firme. |
| `[PROPUESTO]` | Pendiente de aprobación. Se registra, pero no se implementa ni se trata como requisito. |
| `[ABIERTO]` | Decisión pendiente (`PA-XX`). |
| `[SUPUESTO]` | Afirmación sin evidencia verificada. |

Un requisito que se **deduce** de una regla confirmada, pero que ella no formula, se registra como `[PROPUESTO]` con el origen "Deducido de…" hasta que se ratifique de forma expresa. En la versión 0.3 se ratificaron RF-01, RF-16 y RF-24 (RN-61 a RN-63).

## Resumen del estado documental

| Elemento | Total | Confirmados | Propuestos | Abiertos | Retirados |
|---|---|---|---|---|---|
| Reglas de negocio (RN) | 113 | 113 | — | — | — |
| Requisitos funcionales (RF) | 123 | 121 | 1 (RF-34) | — | 1 (RF-31) |
| Requisitos no funcionales (RNF) | 13 | 8 | 2 (RNF-06, RNF-09) | 1 (RNF-10) | 2 (RNF-07, RNF-11) |
| Métricas de éxito (ME) | 6 | — | 6 | — | — |

---

## 1. Problema y contexto

Los equipos de trabajo comunican hoy sus actividades diarias mediante mensajería instantánea (WhatsApp). `[CONFIRMADO]`

Esto provoca:

- **Pérdida de información:** lo reportado queda enterrado en conversaciones.
- **Dificultad para consultar antecedentes:** no hay una forma fiable de saber qué se hizo, cuándo y por qué.
- **Trabajo manual para elaborar informes:** quien necesita un informe lo reconstruye a mano a partir de mensajes dispersos.

El problema de fondo no es solo registrar actividades. Es poder distinguir **lo previsto de lo realmente hecho**, y conservar **lo que quedó pendiente** y **los bloqueos**, de forma consultable y verificable.

Qué hacen hoy las personas en su lugar: reportan y consultan actividades por mensajes de chat y elaboran los informes a mano. `[CONFIRMADO]`

## 2. Personas usuarias y necesidades

Existen dos roles funcionales y no se añade un tercero. `[CONFIRMADO]` (RN-11, RN-33) En el MVP cada persona pertenece a un único equipo y cada equipo tiene un único supervisor, que pertenece al equipo que supervisa y supervisa únicamente un equipo. (RN-28, RN-37)

| Rol | Necesidades | Origen |
|---|---|---|
| **Colaborador** | Planificar lo que prevé hacer, también con antelación, y después actualizar lo realizado. Registrar qué quedó pendiente y qué lo bloquea, con su motivo. Retomar una actividad propia en jornadas posteriores sin duplicarla. Consultar, en modo lectura, lo que hacen sus compañeros de equipo. Obtener su propio informe sin elaborarlo a mano. | RN-07, RN-24, RN-39, RN-46, RN-12, RN-36, RN-53 |
| **Supervisor** | Registrar su propia bitácora, como cualquier otra persona. Disponer, para un período, de una vista consolidada de su equipo con el estado al corte y el estado actual, sin modificar los registros ajenos. Obtener informes individuales de su equipo y consolidados. Consultar la auditoría del equipo. | RN-11, RN-13, RN-23, RN-47, RN-48, RN-51, RN-53, RN-54 |

La creación de usuarios y equipos, la asignación de pertenencias, la baja lógica y la recuperación de acceso las realiza una provisión administrativa controlada, que no es un rol funcional (RN-33, RN-34).

Las necesidades se derivan de las reglas confirmadas. No hay entrevistas ni datos de uso que las respalden todavía. `[SUPUESTO]` (S-01)

**Quién no es el usuario:** quien busca una herramienta de evaluación del desempeño individual (PP-09, `[CONFIRMADO]`) y las personas externas al equipo, como clientes (PP-03, `[PROPUESTO]`).

## 3. Propuesta de valor

Un único lugar donde cada persona registra qué planea hacer, qué hizo realmente, qué quedó pendiente y qué bloqueos tuvo. `[CONFIRMADO]` Con ello:

- Lo planificado se conserva aunque después se actualice lo realizado.
- La información se conserva y se puede consultar después, conforme al equipo de cada persona en la fecha laboral.
- El trabajo que continúa de una jornada a otra se sigue sin duplicarse.
- Cualquier corrección retroactiva queda auditada.
- Los informes se generan con apoyo de IA y se apoyan únicamente en lo realmente registrado, sin valoraciones de desempeño.

## 4. Alcance y fuera de alcance

### 4.1 Alcance
El MVP lo forman los cinco módulos de la sección 5, diseñados para **una organización con varios equipos** (RN-15) y entregados como **plataforma web**. `[CONFIRMADO]` Lo que no pertenece a esos módulos queda fuera del MVP mientras no se apruebe explícitamente lo contrario.

La **planificación diaria y anticipada de actividades** forma parte del MVP (RN-07, RN-46).

### 4.2 Fuera de alcance `[CONFIRMADO]`

| ID | Exclusión |
|---|---|
| PP-06 | Notificaciones y recordatorios (correo, push, mensajería). |
| PP-07 | Aplicación móvil nativa. |
| PP-08 | Importación de conversaciones desde WhatsApp u otra mensajería. |
| PP-09 | Evaluación del desempeño, rankings o métricas de productividad por persona. |
| PP-10 | Gestión avanzada de proyectos y tareas (sprints, asignaciones complejas, estimaciones, tableros tipo gestor de proyectos). |

También quedan fuera: un panel administrativo avanzado (no obligatorio), un calendario de días festivos, el historial automático de informes, la edición de informes y el borrado físico de actividades.

Consecuencia de RN-15 `[A CONFIRMAR]`: no se contempla servir a varias organizaciones aisladas entre sí.

## 5. Módulos principales

| Módulo | Nombre | Qué agrupa |
|---|---|---|
| **M1** | Autenticación, usuarios y equipos | Acceso de las personas al sistema, los dos roles funcionales, la organización en equipos y la provisión administrativa controlada. |
| **M2** | Bitácoras laborales híbridas | Registro de la jornada con actividades estructuradas y resumen libre, planificación diaria y anticipada, y actualización de lo realizado mediante avances. |
| **M3** | Seguimiento de actividades y auditoría | Continuidad de actividades entre jornadas, cierre manual de la jornada, reapertura y corrección con auditoría, y corrección lógica de errores. |
| **M4** | Consulta histórica y supervisión | Consulta del histórico con filtros, lectura de bitácoras del equipo y vista consolidada del supervisor. |
| **M5** | Informes individuales y consolidados con IA | Informes por persona y consolidados por equipo, asistidos por IA y apoyados en los registros almacenados. |

---

## 6. Requisitos funcionales

Cada requisito describe un comportamiento **observable** y se puede responder con "se cumple" o "no se cumple". La columna **Cómo se verifica** indica la comprobación. Los identificadores existentes se conservan; los nuevos continúan la numeración.

### 6.1 M1 — Autenticación, usuarios y equipos

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RF-01 | Solo las personas que se han identificado pueden acceder a las bitácoras y al resto de funciones. | `[CONFIRMADO]` | RN-61 | Un intento de acceso sin identificarse no muestra ningún dato. |
| RF-02 | El sistema distingue dos roles funcionales: colaborador y supervisor. | `[CONFIRMADO]` | RN-11 | Un supervisor ve la vista consolidada de su equipo (RF-27) y un colaborador no la ve. |
| RF-03 | Las personas usuarias se organizan en equipos, y una misma organización puede tener varios equipos. | `[CONFIRMADO]` | RN-15 | En una organización con al menos dos equipos, la consulta de compañeros de cada persona se limita a su equipo (RF-23, RF-66). |
| RF-35 | Cada persona pertenece a un único equipo. | `[CONFIRMADO]` | RN-28 | No es posible asignar a una misma persona a dos equipos a la vez. |
| RF-36 | Cada equipo tiene un único supervisor. | `[CONFIRMADO]` | RN-28 | No es posible asignar dos supervisores al mismo equipo. |
| RF-67 | El supervisor pertenece al equipo que supervisa y supervisa únicamente un equipo. Su bitácora es visible en modo lectura conforme a RF-66. | `[CONFIRMADO]` | RN-37 | Un supervisor figura como miembro del equipo que supervisa; no es posible asignarle la supervisión de un segundo equipo; los integrantes autorizados de su equipo pueden leer su bitácora. |
| RF-37 | Cuando una persona cambia de equipo, el sistema conserva el registro de sus pertenencias anteriores y de las fechas en que estuvo en cada una. | `[CONFIRMADO]` | RN-28 | Tras un cambio de equipo se pueden consultar los equipos anteriores de la persona y las fechas de cada pertenencia. |
| RF-52 | El producto permite crear usuarios y equipos mediante procedimientos de provisión controlada. | `[CONFIRMADO]` | RN-33, RN-34 | Al ejecutar el procedimiento se crea una persona usuaria con su rol y un equipo, y la persona puede acceder con su primer acceso. |
| RF-53 | El producto permite asignar una persona a un equipo, asignar un supervisor a su equipo y cambiar a una persona de equipo, mediante procedimientos de provisión controlada. | `[CONFIRMADO]` | RN-34, RN-28, RN-37 | Tras ejecutar el procedimiento, la persona figura en el equipo asignado y consta su pertenencia anterior. |
| RF-54 | La baja de una persona es lógica y se compone de la desactivación administrativa del acceso y la finalización de su pertenencia; su histórico se conserva. | `[CONFIRMADO]` | RN-34, RN-38, RN-96 | Tras la desactivación del acceso, la persona no puede operar y sus registros siguen siendo consultables por quienes están autorizados. |
| RF-55 | El producto permite recuperar el acceso de una persona mediante un procedimiento de provisión controlada. No reactiva un acceso desactivado administrativamente. | `[CONFIRMADO]` | RN-34, RN-96 | Tras ejecutar el procedimiento, la persona recupera el acceso, salvo que esté desactivado administrativamente. Los detalles están abiertos (PA-12). |
| RF-56 | El primer acceso de cada persona se provee de forma segura, individual y de un solo uso. | `[CONFIRMADO]` | RN-35 | El primer acceso entregado a una persona solo sirve para ella y no puede usarse una segunda vez. Caducidad, credencial propia y medio de entrega están abiertos (PA-12). |
| RF-57 | El supervisor no dispone de funciones para crear usuarios o equipos ni para modificar pertenencias, y no existe un tercer rol funcional. | `[CONFIRMADO]` | RN-33 | Un supervisor no puede crear usuarios, equipos ni cambiar pertenencias; el producto distingue solo dos roles. |
| RF-104 | Las pertenencias de una persona forman períodos de actividad sin solapes ni huecos. No se admite un registro cuya fecha laboral no esté cubierta por una pertenencia de su propietaria. | `[CONFIRMADO]` | RN-94, RN-28 | Una persona cuya primera pertenencia empieza el día D no puede registrar una bitácora anterior a D; en su período de actividad cada fecha laboral tiene un único equipo. |
| RF-105 | Los traslados ordinarios tienen fecha efectiva posterior a la fecha actual en la zona horaria de la organización y no reasignan los registros existentes. No hay corrección histórica ordinaria de pertenencias. | `[CONFIRMADO]` | RN-95 | Un traslado con fecha efectiva igual o anterior a hoy se rechaza; tras un traslado programado, la bitácora creada hoy sigue perteneciendo al equipo anterior. |
| RF-106 | La baja lógica comprende la desactivación administrativa del acceso, que puede ser inmediata, y la finalización de la pertenencia con fecha efectiva posterior a la actual. Ninguna elimina ni reasigna registros, y recuperar el acceso no reactiva un acceso desactivado. | `[CONFIRMADO]` | RN-96, RN-38 | Desde la desactivación la persona no realiza operaciones autenticadas; con una finalización con efecto en F no puede registrar bitácoras desde F; tras recuperar la credencial el acceso sigue desactivado. |
| RF-107 | Una persona sin pertenencia vigente no opera, aunque su acceso no se haya desactivado. | `[CONFIRMADO]` | RN-97 | Una persona cuya pertenencia ya finalizó no puede operar aunque nadie haya desactivado su acceso. |
| RF-108 | Un equipo puede estar incompleto durante su provisión; un equipo con colaboradores tiene un supervisor válido en toda fecha. La desactivación inmediata del acceso del único supervisor no se bloquea: el equipo queda pendiente de supervisión efectiva, sin transferir permisos de supervisión y conservando la pertenencia histórica del supervisor. El supervisor con acceso desactivado no ejerce funciones de supervisión y el reemplazo no se asigna automáticamente. | `[CONFIRMADO]` | RN-98, RN-28, RN-37 | No se finaliza ni se traslada al único supervisor de un equipo con colaboradores sin otro supervisor desde la misma fecha; al desactivar su acceso, el equipo queda identificado como pendiente de supervisión efectiva, ningún colaborador recibe permisos de supervisión y no se asigna reemplazo por sí solo. |
| RF-109 | Las operaciones administrativas de pertenencia programadas que todavía no han surtido efecto (traslados, cambios de rol, finalizaciones y altas futuras) pueden cancelarse o sustituirse mediante provisión controlada y auditoría, que conserva la operación original, su cancelación, el autor y los valores retirados, y respeta la integridad de las pertenencias. Una operación ya efectiva no se modifica retroactivamente. | `[CONFIRMADO]` | RN-99 | Un traslado programado se cancela y la persona permanece en su equipo; un alta futura cancelada deja a la persona sin pertenencia; uno ya efectivo no puede cancelarse; una cancelación que dejaría un equipo con colaboradores sin supervisor se rechaza. |
| RF-112 | Toda operación de provisión administrativa queda auditada con un autor identificable y trazabilidad, sin credenciales ni códigos de acceso y sin crear un tercer rol funcional. | `[CONFIRMADO]` | RN-102, RN-33 | Tras una operación de provisión consta una entrada con autor, operación y valores anterior y nuevo, sin credenciales. El mecanismo concreto para identificar a quien opera la provisión está abierto (PA-12). |
| RF-116 | La primera pertenencia de una persona comienza en una fecha igual o posterior a la fecha actual de la organización. No hay altas históricas excepcionales en el MVP. | `[CONFIRMADO]` | RN-106 | Una primera pertenencia con inicio anterior a hoy se rechaza. |

### 6.2 M2 — Bitácoras laborales híbridas

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RF-04 | Cada persona, sea colaborador o supervisor, dispone de su propia bitácora por fecha laboral, donde registra su jornada. | `[CONFIRMADO]` | RN-11, RN-16 | Un supervisor y un colaborador registran cada uno su bitácora del mismo día. |
| RF-12 | Existe una única bitácora por persona y fecha laboral. | `[CONFIRMADO]` | RN-16 | No existen dos bitácoras de la misma persona con la misma fecha laboral. |
| RF-05 | Una bitácora combina actividades estructuradas y un resumen libre de texto. | `[CONFIRMADO]` | M2, RN-21 | Una bitácora permite registrar actividades y, aparte, un resumen en texto libre. |
| RF-06 | La persona puede registrar las actividades que tiene previstas para su jornada. | `[CONFIRMADO]` | RN-07 | Tras registrar una actividad prevista, esta aparece en la bitácora de la jornada. |
| RF-38 | La planificación original de una actividad se conserva y permanece consultable aunque después se actualice lo realizado. | `[CONFIRMADO]` | RN-20 | Tras actualizar una actividad, sigue siendo posible consultar lo que se había previsto originalmente. |
| RF-39 | Una actividad puede registrarse sin planificación previa; en ese caso se identifica como no planificada. Esa identificación no es un estado. | `[CONFIRMADO]` | RN-20, RN-08 | Una actividad registrada sin planificación aparece identificada como no planificada y se distingue de las planificadas. |
| RF-07 | Una actividad recién planificada tiene el estado Pendiente. | `[CONFIRMADO]` | RN-08 | Toda actividad planificada aparece como Pendiente. Una actividad planificada sin avances conserva el estado Pendiente (RF-61). El estado inicial de una actividad no planificada está en RF-80. |
| RF-80 | Una actividad registrada sin planificación previa inicia con el estado de su primer avance, que es uno de los cuatro estados. Si inicia Bloqueada, es obligatorio un motivo. No se incorpora un quinto estado. | `[CONFIRMADO]` | RN-69 | El primer avance de una actividad no planificada fija su estado inicial; con Bloqueada y sin motivo no se acepta; no existe ningún estado fuera de los cuatro. |
| RF-81 | La planificación inicial de una actividad no constituye por sí misma un avance de ejecución: se distinguen la planificación original, los registros de avance y el estado actual. | `[CONFIRMADO]` | RN-71, RN-20 | Una actividad recién planificada, sin avances, figura Pendiente, conserva su planificación original y no cuenta como continuada; el primer avance de ejecución se registra aparte. |
| RF-08 | El estado de una actividad solo puede ser Pendiente, En progreso, Bloqueada o Completada. No existe un estado adicional de "planificada". | `[CONFIRMADO]` | RN-08 | Ninguna actividad muestra un estado distinto de los cuatro; el sistema no ofrece otros. |
| RF-09 | La persona puede actualizar lo realizado sobre sus actividades: registrar avances y cambiar su estado. | `[CONFIRMADO]` | RN-07, RN-08, RN-09, RN-40 | Tras registrar un avance o cambiar el estado de una actividad no completada, la actividad lo refleja. La reactivación de una Completada está en RF-65. |
| RF-59 | Cada registro de avance exige una descripción no vacía del trabajo realizado o del cambio relevante, y conserva su fecha laboral y su estado histórico. | `[CONFIRMADO]` | RN-41, RN-70 | No se puede registrar un avance sin descripción ni con una descripción solo de espacios; un avance consultado muestra su fecha laboral, el estado que tenía la actividad entonces y su descripción. |
| RF-60 | Se permiten varios avances de una misma actividad en una misma jornada. | `[CONFIRMADO]` | RN-41 | Se registran dos avances de la misma actividad en la misma fecha laboral y ambos constan. |
| RF-40 | Cada registro de avance conserva el estado que tenía la actividad en ese momento; la actividad mantiene además su estado actual. | `[CONFIRMADO]` | RN-17 | Tras cambiar el estado actual de una actividad, los avances anteriores siguen mostrando el estado que tenían. |
| RF-61 | El estado actual de una actividad es el estado de su último avance de ejecución según el orden de RF-62. Una actividad planificada sin avances conserva el estado Pendiente. Un avance retroactivo anterior no sustituye el estado correspondiente a un avance con fecha laboral posterior. Las planificaciones futuras no participan en el cálculo. | `[CONFIRMADO]` | RN-42, RN-66, RN-75 | Con avances Pendiente (lunes) y En progreso (martes), el estado actual es En progreso; si el miércoles se registra con retraso un avance Completada con fecha laboral del lunes, el estado actual sigue siendo En progreso; una continuación planificada para una fecha futura no cambia el resultado. Una actividad sin avances figura como Pendiente. |
| RF-62 | Los avances de ejecución de una actividad se ordenan por fecha laboral, momento real de registro y un identificador estable de desempate. | `[CONFIRMADO]` | RN-65 | Con dos avances de la misma fecha laboral registrados a las 9:00 y a las 15:00, el de las 15:00 es posterior; con la misma fecha laboral y el mismo momento de registro, el orden lo determina el identificador estable y es siempre el mismo. |
| RF-63 | Cada actividad tiene un único propietario. | `[CONFIRMADO]` | RN-43 | Una actividad figura con una sola persona propietaria y no puede asignársele un segundo propietario. |
| RF-41 | Para marcar una actividad como Bloqueada es obligatorio indicar un motivo, que se conserva en el historial. | `[CONFIRMADO]` | RN-24 | No se puede marcar una actividad como Bloqueada sin motivo; el motivo consta en el avance correspondiente. |
| RF-10 | Todo registro conserva y muestra por separado la fecha laboral, la fecha real de registro y la fecha de modificación. | `[CONFIRMADO]` | RN-05, RN-14, RN-18 | Un registro creado hoy para la jornada de ayer y modificado mañana muestra tres fechas distintas. |
| RF-11 | Se pueden registrar jornadas con fecha laboral anterior a la actual (registro retroactivo), sin un límite fijo de días. | `[CONFIRMADO]` | RN-14 | Una jornada de hace varios meses se registra sin rechazo por antigüedad y conserva su fecha real de registro. |
| RF-58 | La fecha laboral de un registro se interpreta según la zona horaria configurada para la organización. No se aplica un calendario de días festivos. | `[CONFIRMADO]` | RN-44 | Dos personas que registran en el mismo instante obtienen la misma fecha laboral actual, con independencia de dónde estén; un día festivo no restringe el registro. |
| RF-42 | Se pueden planificar actividades nuevas en jornadas con fecha laboral futura, únicamente en estado Pendiente. | `[CONFIRMADO]` | RN-27, RN-46 | Se puede registrar una actividad nueva, en estado Pendiente, para una fecha laboral posterior a la actual. |
| RF-43 | No se puede registrar ejecución futura: en una jornada con fecha laboral futura no se acepta ningún avance de ejecución ni un estado distinto de Pendiente para una actividad nueva. | `[CONFIRMADO]` | RN-27, RN-46 | En una jornada con fecha laboral futura no se acepta un avance de ejecución sobre una actividad existente ni una actividad nueva En progreso, Bloqueada o Completada. |
| RF-84 | Se puede planificar la continuación de una actividad propia existente para una jornada con fecha laboral futura, sin crear otra actividad. | `[CONFIRMADO]` | RN-76 | Tras planificar la continuación de una actividad para una fecha futura, el número de actividades es el mismo y la jornada futura muestra la continuación planificada. Para una actividad Completada rige RF-89. |
| RF-89 | No se puede planificar la continuación futura de una actividad Completada sin reactivarla previamente. | `[CONFIRMADO]` | RN-78 | Sobre una actividad Completada no se acepta una continuación planificada; tras reactivarla, sí. |
| RF-114 | La planificación original se conserva sin edición ordinaria y el título de una actividad no se edita en el flujo ordinario. Esto no elimina las correcciones auditadas ya permitidas expresamente. | `[CONFIRMADO]` | RN-104 | Tras nuevos avances, la planificación original y el título de la actividad conservan su contenido. |
| RF-115 | Cuando finaliza una pertenencia, las planificaciones futuras existentes se conservan con su identidad y trazabilidad, sin mostrarse como trabajo vigente ni pendiente de un equipo sin autorización. | `[CONFIRMADO]` | RN-105 | Una planificación posterior a la finalización de la pertenencia se conserva con su actividad y su propietaria y no aparece como trabajo vigente ni pendiente en la vista de ningún equipo. |
| RF-117 | La bitácora de una persona y fecha laboral es única. Se abre de forma explícita o se crea de forma implícita al registrar su primer contenido. Abrir una bitácora que ya existe devuelve la misma sin modificarla, y consultar una fecha sin bitácora no la crea. | `[CONFIRMADO]` | RN-107, RN-16 | Abrir dos veces la misma fecha deja una sola bitácora, igual en ambos casos; registrar el primer contenido de una fecha sin bitácora crea la bitácora; consultar una fecha sin bitácora no la crea. |
| RF-85 | Una planificación futura no modifica el estado actual de la actividad, no constituye un avance de ejecución y no participa en la secuencia de avances ni en el cálculo del estado actual. | `[CONFIRMADO]` | RN-75 | Una actividad En progreso a la que se le planifica una continuación futura sigue En progreso, y la continuación planificada no aparece entre sus avances. |

### 6.3 M3 — Seguimiento de actividades y auditoría

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RF-13 | Continuar una actividad en jornadas posteriores no genera otra actividad; la actividad conserva su identidad. | `[CONFIRMADO]` | RN-04, RN-09, RN-32 | Tras registrar avances en tres jornadas distintas sigue existiendo una única actividad. |
| RF-64 | Para continuar una actividad, la persona selecciona de forma explícita una actividad propia existente. | `[CONFIRMADO]` | RN-39 | Registrar un avance en una jornada posterior exige elegir una actividad propia ya existente; el sistema no asocia avances por similitud de títulos. |
| RF-14 | Una actividad puede tener múltiples registros de avance, cada uno asociado a una fecha laboral. | `[CONFIRMADO]` | RN-09 | Una actividad con avances en tres fechas laborales muestra los tres. |
| RF-15 | La persona puede registrar, en una jornada posterior, un avance sobre una actividad existente sin crear una nueva. | `[CONFIRMADO]` | RN-09 | Antes y después de registrar el avance, el número de actividades es el mismo y la actividad incluye el nuevo avance. |
| RF-16 | La persona puede consultar los avances de una actividad junto con su fecha laboral y el estado de cada uno. | `[CONFIRMADO]` | RN-62 | Al abrir una actividad con avances se ven todos, con su fecha laboral y su estado. |
| RF-65 | Una actividad Completada puede reactivarse mediante una acción explícita de su propietario, sin duplicarla. La reactivación se registra en una jornada no futura, con fecha laboral igual o posterior a la del avance que completó la actividad, queda posterior a él en la secuencia y queda auditada. | `[CONFIRMADO]` | RN-40, RN-68, RN-74 | Tras reactivar una actividad Completada, la misma actividad figura En progreso, no se crea otra, la reactivación consta como último avance y hay una entrada de auditoría; con una fecha laboral anterior a la del avance que la completó, o futura, la reactivación no se acepta. |
| RF-86 | Una actividad Completada requiere una reactivación explícita y auditada para recibir nuevos avances de ejecución posteriores a su finalización. | `[CONFIRMADO]` | RN-73 | Sobre una actividad Completada no se acepta un nuevo avance de ejecución que, según la secuencia, quedaría después del avance que la completó, si no se reactiva antes. |
| RF-88 | Se puede registrar un avance retroactivo sobre una actividad Completada, sin reactivarla, cuando su fecha laboral es anterior a la fecha laboral de finalización. El avance se inserta en la secuencia histórica, queda auditado y no modifica el estado actual si existe un avance posterior que mantiene Completada. No se admite insertar un avance de ejecución en un intervalo posterior a una finalización y anterior a una reactivación válida. | `[CONFIRMADO]` | RN-77, RN-79, RN-45, RN-66 | Una actividad con un avance En progreso el lunes y Completada el miércoles admite, sin reactivarla, un avance del martes: queda entre ambos, consta en la auditoría y el estado actual sigue siendo Completada. Un avance con fecha laboral del miércoles registrado después de la finalización no se admite sin reactivar. Con dos finalizaciones separadas por una reactivación, un avance que quedaría justo tras la primera finalización no se admite. |
| RF-90 | Las correcciones auditadas de registros existentes se distinguen de la incorporación de nuevos avances de ejecución: una corrección no exige reactivar la actividad ni se registra como un nuevo avance. | `[CONFIRMADO]` | RN-80 | Corregir con auditoría la descripción de un avance anterior a la finalización de una actividad Completada no exige reactivarla ni añade un avance a su secuencia. |
| RF-101 | Toda corrección se valida contra la secuencia completa de avances antes de aplicarse. | `[CONFIRMADO]` | RN-91 | Cada corrección se comprueba con la secuencia completa de la actividad antes de modificar nada. |
| RF-102 | No se admite una corrección que deje avances de ejecución posteriores a una finalización sin una reactivación válida. Eliminar o modificar una finalización exige validar todas las demás reglas aplicables. | `[CONFIRMADO]` | RN-92 | Corregir a Completada un avance anterior a otros avances de ejecución, sin reactivación intermedia, se rechaza; corregir la finalización a otro estado se acepta si la secuencia sigue siendo válida. |
| RF-103 | Una corrección válida queda auditada y recalcula el estado actual cuando corresponde. Una corrección inválida se rechaza sin modificar los datos. No se generan reactivaciones automáticas. | `[CONFIRMADO]` | RN-93, RN-67 | Tras una corrección rechazada, los avances, el estado actual y la auditoría no cambian; ninguna corrección crea una reactivación. |
| RF-110 | Una actividad Completada se reactiva hacia Pendiente, En progreso o Bloqueada. Bloqueada exige motivo. La finalización anterior se conserva. | `[CONFIRMADO]` | RN-100, RN-68 | Reactivar sin motivo hacia Bloqueada se rechaza; reactivar hacia Pendiente conserva la finalización anterior en el historial. |
| RF-113 | Cada operación genera una única entrada de auditoría con los valores anterior y nuevo necesarios para reconstruir el cambio, sin versionar los avances. Los ciclos de cierre y reapertura se reconstruyen desde la auditoría. | `[CONFIRMADO]` | RN-103, RN-49, RN-50 | Una operación que modifica varios campos deja una sola entrada con los valores de cada campo; tras cerrar, reabrir y cerrar de nuevo se reconstruye cada ciclo. |
| RF-118 | Modificar el contenido de una jornada cerrada exige reabrirla antes. Registrar una ejecución nueva en una jornada abierta no obliga a reabrir las jornadas anteriores de la actividad. | `[CONFIRMADO]` | RN-108, RN-19 | Registrar o corregir contenido en una jornada cerrada sin reabrirla se rechaza; una actividad con avances en jornadas cerradas recibe un avance en una jornada abierta posterior sin reabrir las anteriores. |
| RF-119 | Las actividades marcadas como registradas por error no cuentan para las condiciones de cierre. Marcar una actividad se rechaza, sin modificar registros, si dejaría a una jornada cerrada sin cumplir sus condiciones de cierre, considerando todas las actividades válidas creadas o continuadas en esa fecha laboral, incluidas las iniciadas en jornadas anteriores. Marcar y revertir la marca no obligan a reabrir la jornada, se auditan y validan la integridad de los registros relacionados. | `[CONFIRMADO]` | RN-109, RN-21, RN-60 | No se cierra una jornada cuya única actividad está marcada; no se marca la única actividad válida de una jornada cerrada; se marca una actividad si otra válida mantiene el cierre; la reversión consta en la auditoría. |
| RF-120 | La consulta funcional de la auditoría de una bitácora no incluye las entradas de la provisión administrativa. | `[CONFIRMADO]` | RN-110, RN-102 | Quien consulta la auditoría de una bitácora no ve entradas de altas, traslados, bajas ni emisión de códigos. |
| RF-121 | Toda escritura efectiva de contenido sobre una jornada pasada, incluida la primera, genera una entrada de auditoría. Abrir una bitácora vacía no es una escritura efectiva. | `[CONFIRMADO]` | RN-111, RN-45 | Registrar por primera vez contenido en una jornada pasada deja una entrada de auditoría; abrir una bitácora vacía de una fecha pasada no la deja. |
| RF-122 | El título de una actividad es obligatorio y contiene algún carácter distinto de un espacio. | `[CONFIRMADO]` | RN-112 | Planificar o registrar una actividad con el título vacío o de solo espacios se rechaza. |
| RF-123 | No se corrigen los avances de una actividad marcada como registrada por error mientras la marca esté vigente; primero se revierte la marca. | `[CONFIRMADO]` | RN-113, RN-59 | Corregir un avance de una actividad marcada se rechaza; tras revertir la marca se permite según las reglas de corrección. |
| RF-17 | El cierre de una jornada es manual: solo ocurre cuando la persona lo solicita. | `[CONFIRMADO]` | RN-10 | Una jornada con actividades y resumen nunca pasa a cerrada sin una acción explícita. |
| RF-18 | Una jornada puede cerrarse cuando contiene al menos una actividad válida, no marcada como registrada por error (RN-109), creada o continuada en esa jornada y un resumen libre no vacío. "Continuada" significa que tiene al menos un avance de ejecución con esa fecha laboral. "No vacío" significa que contiene algún carácter distinto de un espacio. | `[CONFIRMADO]` | RN-21, RN-109 | El cierre no se permite sin ninguna actividad creada ni continuada; no se permite con el resumen vacío o solo de espacios; se permite cuando se cumplen ambas condiciones. Una continuación planificada, que no es un avance, no cuenta como actividad continuada. |
| RF-19 | Una jornada puede cerrarse con actividades en cualquiera de los cuatro estados. Cerrar no modifica el estado de ninguna actividad. | `[CONFIRMADO]` | RN-22 | Se cierra una jornada con actividades en los cuatro estados; después del cierre cada actividad conserva el mismo estado. |
| RF-44 | Las actividades no completadas permanecen abiertas y disponibles para registrarles avances en jornadas posteriores; no se copian ni se crean automáticamente. | `[CONFIRMADO]` | RN-22, RN-40 | Tras cerrar una jornada con una actividad En progreso, se le puede registrar un avance al día siguiente y no aparece una copia de la actividad. |
| RF-68 | No se puede cerrar una jornada con fecha laboral futura. | `[CONFIRMADO]` | RN-46 | El cierre de una jornada con fecha laboral posterior a la actual no se permite. |
| RF-20 | El propietario de una bitácora puede reabrirla y corregirla. | `[CONFIRMADO]` | RN-01, RN-19 | Una bitácora cerrada, tras reabrirla su propietario, admite correcciones. |
| RF-71 | La reapertura de una bitácora requiere un motivo. | `[CONFIRMADO]` | RN-50 | No se puede reabrir una bitácora sin motivo; el motivo consta en la auditoría. |
| RF-21 | La reapertura, las correcciones posteriores al cierre y las modificaciones de jornadas pasadas, abiertas o cerradas, quedan auditadas. | `[CONFIRMADO]` | RN-01, RN-19, RN-45, RN-49 | Tras reabrir y corregir una bitácora y tras modificar una jornada pasada que no se había cerrado, existe una entrada de auditoría de cada operación. "Pasada" se define en el glosario. Si el primer registro de una jornada pasada se audita está abierto (PA-06). |
| RF-22 | Cada entrada de auditoría registra autor, fecha real, operación, valor anterior y valor nuevo, y conserva suficiente contexto para reconstruir el cambio. | `[CONFIRMADO]` | RN-49, RN-50 | Para una corrección se puede reconstruir qué valor había, cuál se puso, quién lo hizo y cuándo. |
| RF-72 | La auditoría es visible para el propietario del registro y para el supervisor autorizado del equipo correspondiente al registro. | `[CONFIRMADO]` | RN-51, RN-36 | El propietario y el supervisor del equipo al que pertenecía el propietario en la fecha laboral del registro consultan las entradas; otras personas no. |
| RF-73 | La información de las bitácoras y de la auditoría no se borra silenciosamente. | `[CONFIRMADO]` | RN-52 | Ninguna operación elimina un registro sin dejar constancia en la auditoría. La política de retención está abierta (PA-06). |
| RF-77 | El propietario puede marcar una actividad como registrada por error, indicando un motivo, siempre que no tenga avances en jornadas posteriores a su creación. No hay borrado físico. | `[CONFIRMADO]` | RN-59 | Se permite marcar con motivo una actividad sin avances posteriores; se rechaza si tiene avances de jornadas posteriores a su creación o si no se indica motivo. |
| RF-78 | Una actividad registrada por error se excluye de las vistas operativas y de los recuentos ordinarios, y permanece consultable en el historial autorizado y en la auditoría. No es un estado. | `[CONFIRMADO]` | RN-60 | Tras marcarla, la actividad no aparece en las vistas ni en los recuentos ordinarios, sigue consultándose en el historial autorizado y su estado sigue siendo uno de los cuatro. |
| RF-79 | La marca de error puede revertirse y la reversión queda auditada. | `[CONFIRMADO]` | RN-60 | Tras revertir la marca, la actividad vuelve a las vistas y consta una entrada de auditoría. |
| RF-82 | Las correcciones se auditan y, cuando modifican el avance que determina el estado actual, el estado actual se recalcula. | `[CONFIRMADO]` | RN-67 | Al corregir el estado del último avance de una actividad, el estado actual cambia en consecuencia y consta una entrada de auditoría; al corregir un avance que no es el último, el estado actual no cambia. |

### 6.4 M4 — Consulta histórica y supervisión

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RF-23 | Un colaborador puede consultar, solo en modo lectura, los registros de compañeros que pertenecen históricamente a su equipo (RF-66). | `[CONFIRMADO]` | RN-02, RN-12, RN-36 | Un colaborador abre la bitácora de un compañero de su equipo, de una fecha en que ese compañero pertenecía a su equipo, y ve su contenido. |
| RF-66 | Un registro pertenece históricamente al equipo que tenía su propietario en la fecha laboral correspondiente. Los integrantes autorizados de ese equipo pueden consultarlo, aunque el propietario se haya trasladado después a otro equipo, y un integrante activo puede consultar los registros históricos que le corresponden aunque se haya incorporado después. Esto no concede acceso a registros de otros equipos ni de períodos en los que el propietario pertenecía a otro equipo. | `[CONFIRMADO]` | RN-36 | Una persona P estuvo en el equipo T hasta una fecha y después en U: un integrante de T ve las bitácoras de P hasta esa fecha, aunque P ya esté en U y aunque el integrante se haya incorporado a T después; un integrante de U no ve las de P anteriores a esa fecha; un integrante de U ve las de P posteriores y un integrante de T no. |
| RF-24 | Un colaborador no puede consultar los registros que pertenecen históricamente a otro equipo. | `[CONFIRMADO]` | RN-63, RN-36 | Un colaborador no puede abrir un registro de una persona correspondiente a una fecha en la que esa persona pertenecía a otro equipo. |
| RF-25 | Ninguna persona modifica los registros de otra. El supervisor consulta los registros de su equipo sin modificarlos. | `[CONFIRMADO]` | RN-12, RN-23 | Ni un colaborador ni un supervisor pueden cambiar actividades, avances ni resumen de la bitácora de otra persona. |
| RF-26 | La consulta histórica exige un rango de fechas laborales y permite filtrar por colaborador, que es opcional, dentro de lo que la persona está autorizada a consultar. No incluye búsqueda por texto. | `[CONFIRMADO]` | RN-25 | Se filtra por una persona y un rango de fechas y se obtienen sus bitácoras de ese rango. No existe búsqueda por texto. |
| RF-27 | Para el período seleccionado, el supervisor dispone de una vista consolidada de su equipo con las actividades en los cuatro estados. | `[CONFIRMADO]` | RN-13 | El supervisor selecciona un período y ve las actividades de su equipo clasificadas en Pendiente, En progreso, Bloqueada y Completada. |
| RF-69 | La vista del supervisor incluye las actividades del equipo que fueron planificadas o tuvieron avances durante el período, y las no completadas que permanecen pendientes de atención al final del período cuyo propietario pertenece al equipo en la fecha de corte. Incluye las actividades del propio supervisor. Si no existen registros del equipo sobre una actividad iniciada en otro equipo, muestra solo su referencia mínima (RF-94). | `[CONFIRMADO]` | RN-47 | Una actividad sin avances en el período que sigue sin completarse al final aparece en la vista; una actividad completada antes del período y sin avances en él no aparece; las actividades del supervisor aparecen; una actividad de una persona que ya no pertenece al equipo en la fecha de corte no aparece como pendiente. |
| RF-70 | La vista del supervisor muestra el estado correspondiente al corte, que es el último día del período consultado, y lo distingue del estado actual cuando son diferentes, solo para actividades cuyo propietario pertenece al equipo. No muestra el estado al corte cuando deriva exclusivamente de registros protegidos de otro equipo. | `[CONFIRMADO]` | RN-48, RN-88 | Una actividad Bloqueada al corte y Completada hoy, de una persona del equipo, se muestra como Bloqueada al corte con el estado actual Completada indicado aparte; de una persona trasladada no se indica el estado actual; cuando el estado al corte derivaría solo de registros del equipo anterior, no se muestra. |
| RF-28 | El supervisor puede consultar el historial de las actividades de su equipo. | `[CONFIRMADO]` | RN-13 | El supervisor accede a los avances de las actividades de su equipo con su fecha laboral. |
| RF-45 | La vista del supervisor no incluye clasificaciones, rankings ni puntuaciones de personas. | `[CONFIRMADO]` | RN-13, RN-48, PP-09 | Ningún elemento de la vista ordena ni puntúa a las personas por su desempeño. |
| RF-83 | Las consultas, las vistas de supervisión y los informes aplican la pertenencia histórica de los registros de igual manera, según los permisos de cada rol, en las interfaces y en los controles de autorización: el cambio de equipo de una persona no expone automáticamente su historial al equipo nuevo. | `[CONFIRMADO]` | RN-36, RN-86 | Tras el traslado de P de T a U, ni una consulta, ni una vista de supervisión, ni un informe, ni un acceso directo permiten a un integrante de U obtener registros de P anteriores al traslado. |
| RF-91 | Una actividad conserva su identidad y su propietario después del traslado de la persona y puede continuar en el equipo nuevo sin duplicarse. | `[CONFIRMADO]` | RN-81 | Tras el traslado de P, la actividad iniciada en el equipo anterior sigue siendo la misma, con P como propietaria; un nuevo avance de P en el equipo nuevo no crea otra actividad. |
| RF-92 | El equipo nuevo no obtiene acceso automático al título, las descripciones, los motivos de bloqueo ni las bitácoras del equipo anterior. | `[CONFIRMADO]` | RN-82 | Un integrante del equipo nuevo no obtiene el título, las descripciones, los motivos de bloqueo ni las bitácoras de una actividad iniciada en el equipo anterior. |
| RF-93 | La persona propietaria conserva el acceso al historial completo de sus propias actividades, también tras un traslado. | `[CONFIRMADO]` | RN-83 | Tras su traslado, P consulta todos los avances de sus actividades, los del equipo anterior y los del nuevo. |
| RF-94 | El supervisor actual puede consultar una referencia mínima de las actividades pendientes de las personas que supervisa que se iniciaron en otro equipo, sin acceso a los detalles históricos restringidos. La referencia incluye el propietario, la indicación de que se inició en otro equipo y su estado actual sin motivo. Incluye la fecha laboral del último avance solo si ese avance pertenece al equipo del supervisor. No incluye título, descripciones, motivos de bloqueo, contenido de bitácoras, nombre del equipo anterior ni número de avances. | `[CONFIRMADO]` | RN-84 | La referencia de una actividad heredada muestra solo esos elementos; si el último avance es del equipo anterior, no muestra su fecha. |
| RF-95 | El equipo anterior conserva la consulta de sus registros históricos autorizados, pero no presenta como pendiente actual ni muestra el estado actual del trabajo de una persona trasladada. | `[CONFIRMADO]` | RN-85 | El supervisor del equipo anterior ve los registros de P de su período y su estado al corte, pero no figura ninguna actividad de P como pendiente actual en su vista. |
| RF-97 | La visibilidad de una planificación futura se evalúa según la pertenencia del propietario aplicable a su fecha laboral, considerando los traslados registrados. | `[CONFIRMADO]` | RN-87, RN-28 | P planifica en el equipo T algo para el viernes y se traslada a U el miércoles: el viernes esa planificación es visible para U y no para T, y el historial de pertenencias refleja el traslado. |
| RF-98 | El estado al corte de una actividad no se muestra a un equipo cuando deriva exclusivamente de registros protegidos de otro equipo. Si existen avances autorizados del equipo actual, se muestra el estado al corte correspondiente sin revelar información histórica protegida. | `[CONFIRMADO]` | RN-88 | Una actividad heredada sin avances del equipo actual hasta el corte no muestra estado al corte; con un avance del equipo actual anterior o igual al corte, muestra el estado que resulta de ese avance. |
| RF-99 | La referencia mínima de una actividad se distingue claramente del acceso completo a su historial. | `[CONFIRMADO]` | RN-89 | La vista identifica la referencia mínima como tal y no ofrece acceso a los registros protegidos del equipo anterior. |
| RF-100 | La consulta del propietario y los informes respetan la matriz de permisos en el tratamiento de la referencia mínima y del estado al corte. | `[CONFIRMADO]` | RN-90 | El propietario ve su historial completo; un informe del equipo nuevo no incluye un estado al corte derivado exclusivamente de registros del equipo anterior. |
| RF-111 | El título original de una actividad iniciada en otro equipo no se expone al equipo nuevo, aunque existan avances posteriores autorizados; se usa la referencia neutral «Actividad en continuidad», con un identificador opaco que no contiene información del equipo anterior. Los motivos de bloqueo de registros de otro equipo y el motivo de la marca de error no se exponen. Informes, vistas y consultas usan la misma política. | `[CONFIRMADO]` | RN-101, RN-82 | El supervisor del equipo nuevo no ve el título original en la vista, el historial ni los informes; la propietaria sí ve su historial completo. |

### 6.5 M5 — Informes individuales y consolidados con IA

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RF-29 | Un informe individual lo genera su propietario o el supervisor autorizado de su equipo. | `[CONFIRMADO]` | RN-03, RN-53 | El propietario y el supervisor de su equipo generan el informe; un compañero no puede. |
| RF-30 | Un informe consolidado es por equipo y período, y lo genera su supervisor. | `[CONFIRMADO]` | RN-03, RN-54 | El supervisor genera el consolidado de su equipo para un período; un colaborador no puede generarlo. |
| RF-31 | *Retirado en la versión 0.2.* "Los informes se generan con asistencia de IA" no es un comportamiento observable; pasa a las restricciones (sección 8.1). | Retirado | M5 | — |
| RF-32 | Los informes se apoyan en los registros almacenados: todo hecho que afirman consta en ellos. | `[CONFIRMADO]` | RN-06 | Al contrastar un informe con los registros de su período, cada hecho que afirma consta en ellos. |
| RF-46 | Los informes pueden incluir agregaciones calculadas a partir de los registros y las diferencian de los hechos registrados. | `[CONFIRMADO]` | RN-26 | En un informe se distingue qué dato es un hecho registrado y cuál una agregación calculada. |
| RF-47 | Los informes no emiten valoraciones sobre las personas ni incluyen rankings. | `[CONFIRMADO]` | RN-26, RN-55, PP-09 | Un informe no contiene juicios de valor sobre ninguna persona ni ordenaciones por rendimiento. |
| RF-48 | Todo informe indica su período y su fecha de generación. | `[CONFIRMADO]` | RN-29, RN-55 | Todo informe muestra el período que cubre y la fecha en que se generó. |
| RF-49 | La información que se utiliza para generar un informe se limita a la que la persona que lo genera está autorizada a consultar y a la necesaria para ese informe. | `[CONFIRMADO]` | RN-29, RN-30 | Un informe generado por un supervisor no contiene datos de personas fuera de lo que puede consultar; la información usada corresponde al período solicitado. Qué es "necesaria" está abierto (PA-09). |
| RF-50 | Un informe puede generarse nuevamente. | `[CONFIRMADO]` | RN-29, RN-56 | Al generarlo de nuevo se obtiene un informe con su propia fecha de generación. |
| RF-51 | Los indicadores cuantitativos de un informe se calculan de forma determinista a partir de registros autorizados. | `[CONFIRMADO]` | RN-29, RN-55 | Con los mismos registros, el cálculo da siempre el mismo valor y coincide con un recuento manual. |
| RF-74 | Los informes incluyen los bloqueos con sus motivos. | `[CONFIRMADO]` | RN-55 | Un informe de un período con una actividad bloqueada muestra la actividad y su motivo de bloqueo. |
| RF-75 | El informe se consulta en pantalla, no se edita y no se conserva automáticamente como historial de informes. | `[CONFIRMADO]` | RN-56 | El informe no ofrece edición, y al salir no queda guardado en un historial de informes. |
| RF-33 | Cuando no existen registros autorizados en el período, el informe indica explícitamente que no hay datos disponibles. Cuando existen, el informe puede generarse con ellos. No se establecen umbrales de suficiencia ni porcentajes de cobertura. | `[CONFIRMADO]` | RN-57 | Un informe de un período sin ningún registro autorizado indica que no hay datos disponibles; un informe de un período con un único registro autorizado se genera con esa información; en ningún caso contiene actividades, personas, fechas, avances ni bloqueos inventados. |
| RF-87 | Todo informe deja claro que se basa únicamente en los registros disponibles y autorizados del período y que no representa información que nunca fue registrada. | `[CONFIRMADO]` | RN-57 | Todo informe, incluso el de un período con registros de solo algunas jornadas, incluye esa indicación y no afirma que describa todo el trabajo del período. |
| RF-96 | El supervisor de un equipo puede obtener el informe individual de una persona que ya no integra su equipo únicamente respecto de los registros históricos de ese equipo y de los períodos para los que conserva autorización, sin información posterior del equipo nuevo. | `[CONFIRMADO]` | RN-53 | El informe que genera el supervisor del equipo anterior sobre P contiene los registros de su período y nada posterior al traslado. |
| RF-76 | Si falla el servicio de IA, se informa de que el informe no pudo generarse; no se presenta contenido parcial como informe completo. | `[CONFIRMADO]` | RN-58 | Con el servicio de IA no disponible, la persona recibe el aviso de que el informe no pudo generarse y no se muestra un informe parcial como completo. |
| RF-34 | Cada afirmación de un informe enlaza con los registros de origen. | `[PROPUESTO]` | PP-11 | Pendiente de aprobación. |

### 6.6 Requisitos deducidos pendientes de ratificación

Ninguno en esta versión. RF-01, RF-16 y RF-24 se ratificaron y pasan a `[CONFIRMADO]` (RN-61 a RN-63).

### 6.7 Cambios respecto a la versión 0.11

- **Nuevos confirmados:** RF-121 a RF-123 (auditoría de la primera escritura efectiva, título obligatorio y corrección tras revertir la marca).
- **Reescritos:** RF-26 y RF-111.
- **Siguen propuestos:** RF-34.

### 6.8 Trazabilidad de reglas confirmadas a requisitos

| Regla | Requisitos |
|---|---|
| RN-01 | RF-20, RF-21 |
| RN-02 | RF-23 |
| RN-03 | RF-29, RF-30 |
| RN-04 | RF-13 |
| RN-05 | RF-10 |
| RN-06 | RF-32 |
| RN-07 | RF-06, RF-09 |
| RN-08 | RF-07, RF-08, RF-09, RF-39 |
| RN-09 | RF-13, RF-14, RF-15 |
| RN-10 | RF-17 |
| RN-11 | RF-02, RF-04 |
| RN-12 | RF-23, RF-25 |
| RN-13 | RF-27, RF-28, RF-45 |
| RN-14 | RF-10, RF-11 |
| RN-15 | RF-03 |
| RN-16 | RF-04, RF-12 |
| RN-17 | RF-40 |
| RN-18 | RF-10 |
| RN-19 | RF-20, RF-21 |
| RN-20 | RF-38, RF-39 |
| RN-21 | RF-18 |
| RN-22 | RF-19, RF-44 |
| RN-23 | RF-25 |
| RN-24 | RF-41 |
| RN-25 | RF-26 |
| RN-26 | RF-46, RF-47 |
| RN-27 | RF-42, RF-43 |
| RN-28 | RF-35, RF-36, RF-37, RF-53, RF-104 |
| RN-29 | RF-48, RF-49, RF-50, RF-51 |
| RN-30 | RF-49 |
| RN-31 | RNF-12 |
| RN-32 | RF-13 |
| RN-33 | RF-52, RF-57 |
| RN-34 | RF-52, RF-53, RF-54, RF-55 |
| RN-35 | RF-56 |
| RN-36 | RF-66, RF-72, RF-83 |
| RN-37 | RF-67 |
| RN-38 | RF-54, RF-106 |
| RN-39 | RF-64 |
| RN-40 | RF-44, RF-65 |
| RN-41 | RF-59, RF-60 |
| RN-42 | RF-61 |
| RN-43 | RF-63 |
| RN-44 | RF-58 |
| RN-45 | RF-21 |
| RN-46 | RF-42, RF-43, RF-68 |
| RN-47 | RF-69 |
| RN-48 | RF-70, RF-45 |
| RN-49 | RF-21, RF-22 |
| RN-50 | RF-22, RF-71 |
| RN-51 | RF-72 |
| RN-52 | RF-73 |
| RN-53 | RF-29, RF-96 |
| RN-54 | RF-30 |
| RN-55 | RF-46, RF-47, RF-48, RF-51, RF-74 |
| RN-56 | RF-50, RF-75 |
| RN-57 | RF-33, RF-87 |
| RN-58 | RF-76 |
| RN-59 | RF-77 |
| RN-60 | RF-78, RF-79 |
| RN-61 | RF-01 |
| RN-62 | RF-16 |
| RN-63 | RF-24 |
| RN-64 | RNF-08 |
| RN-65 | RF-62 |
| RN-66 | RF-61 |
| RN-67 | RF-82 |
| RN-68 | RF-65 |
| RN-69 | RF-80 |
| RN-70 | RF-59 |
| RN-71 | RF-81 |
| RN-72 | RF-21 |
| RN-73 | RF-86 |
| RN-74 | RF-65 |
| RN-75 | RF-85 |
| RN-76 | RF-84 |
| RN-77 | RF-88 |
| RN-78 | RF-89 |
| RN-79 | RF-88 |
| RN-80 | RF-90 |
| RN-81 | RF-91 |
| RN-82 | RF-92 |
| RN-83 | RF-93 |
| RN-84 | RF-94 |
| RN-85 | RF-95 |
| RN-86 | RF-83 |
| RN-87 | RF-97 |
| RN-88 | RF-98, RF-70 |
| RN-89 | RF-99 |
| RN-90 | RF-100 |
| RN-91 | RF-101 |
| RN-92 | RF-102 |
| RN-93 | RF-103 |
| RN-94 | RF-104 |
| RN-95 | RF-105 |
| RN-96 | RF-106, RF-54, RF-55 |
| RN-97 | RF-107 |
| RN-98 | RF-108 |
| RN-99 | RF-109 |
| RN-100 | RF-110 |
| RN-101 | RF-111 |
| RN-102 | RF-112 |
| RN-103 | RF-113 |
| RN-104 | RF-114 |
| RN-105 | RF-115 |
| RN-106 | RF-116 |
| RN-107 | RF-117 |
| RN-108 | RF-118 |
| RN-109 | RF-119, RF-18 |
| RN-110 | RF-120 |
| RN-111 | RF-121 |
| RN-112 | RF-122 |
| RN-113 | RF-123 |

---

## 7. Requisitos no funcionales

Los umbrales cuantitativos no se fijan porque no hay datos que los respalden. Se registran como punto abierto (PA-13) y no se inventan cifras.

| ID | Requisito | Estado | Origen | Cómo se verifica |
|---|---|---|---|---|
| RNF-01 | **Control de acceso.** Cada consulta, acción o informe se resuelve según el rol de la persona, su equipo en la fecha laboral del registro y sus permisos. Nadie ve ni hace más de lo permitido, tanto en las consultas, las vistas de supervisión y los informes como en los controles de autorización. | `[CONFIRMADO]` | RN-11, RN-12, RN-13, RN-23, RN-29, RN-36, RN-37 | Una matriz de pruebas por rol, acción y equipo no muestra ningún acceso fuera de lo permitido. La matriz está en el anexo B. |
| RNF-02 | **Trazabilidad e integridad.** Ningún cambio sobre una bitácora cerrada ni modificación de una jornada pasada se pierde ni se sobrescribe sin dejar rastro. | `[CONFIRMADO]` | RN-01, RN-17, RN-19, RN-45, RN-52 | Tras varias correcciones sucesivas, la auditoría permite reconstruir cada operación. |
| RNF-03 | **Fidelidad temporal.** La fecha laboral, la fecha real de registro y la fecha de modificación se conservan en todos los registros, y un cambio posterior queda auditado. | `[CONFIRMADO]` | RN-05, RN-14, RN-18 | Tras corregir un registro, las tres fechas siguen siendo consultables y el cambio consta en la auditoría. |
| RNF-04 | **Fiabilidad de la IA.** Los informes no contienen afirmaciones sin respaldo en los registros. | `[CONFIRMADO]` | RN-06, RN-26 | La revisión de una muestra de informes contrastada con los registros no halla afirmaciones sin respaldo. |
| RNF-05 | **Plataforma web.** El producto es accesible mediante navegador web. | `[CONFIRMADO]` | Descripción inicial del producto (registrada en el alcance) | El producto se usa desde un navegador. Los navegadores soportados están por definir (PA-13). |
| RNF-06 | **Privacidad.** No se envían datos de bitácoras a un servicio externo de IA hasta decidir proveedor, datos enviados y conservación. | `[PROPUESTO]` | PP-33 | Pendiente de aprobación. |
| RNF-07 | *Retirado en la versión 0.2.* Lo absorbe RF-49 (información autorizada y necesaria). | Retirado | RN-30 | — |
| RNF-08 | **Protección de credenciales.** Las credenciales de las personas nunca se muestran ni se registran en claro. | `[CONFIRMADO]` | RN-64 | Ninguna pantalla, registro del sistema ni informe contiene credenciales en claro. |
| RNF-09 | **Usabilidad básica.** Un colaborador puede planificar, actualizar y cerrar su jornada sin consultar documentación. | `[PROPUESTO]` | PP-35 | Se comprobaría en una prueba con personas usuarias. Pendiente de aprobación. |
| RNF-10 | **Rendimiento, disponibilidad, volumen, conservación de datos e idioma de la interfaz.** | `[ABIERTO]` | PA-13, PA-06 | Sin valores acordados no son comprobables. |
| RNF-11 | *Retirado en la versión 0.3.* La consistencia de fechas entre zonas horarias la cubre RF-58. | Retirado | RN-44 | — |
| RNF-12 | **Texto libre como datos.** El texto libre de las bitácoras se trata como datos y no como instrucciones. | `[CONFIRMADO]` | RN-31 | Un informe generado a partir de una bitácora cuyo texto contiene órdenes dirigidas al generador no altera su comportamiento ni su contenido por esa causa. |
| RNF-13 | **Confidencialidad de la existencia.** Ante un registro inexistente y ante uno al que la persona no está autorizada, el producto responde de forma indistinguible: ni el mensaje, ni los detalles, ni la estructura de la respuesta revelan que un registro protegido existe. | `[CONFIRMADO]` | RN-36, RN-82, RNF-01 | Dos peticiones, una sobre un registro inexistente y otra sobre uno de otro equipo, reciben respuestas que no se distinguen. |

## 8. Restricciones y supuestos

### 8.1 Restricciones
- **Plataforma web.** El MVP es una aplicación web. `[CONFIRMADO]`
- **Una organización con varios equipos**, una persona por equipo y un supervisor por equipo. `[CONFIRMADO]` (RN-15, RN-28)
- **Alcance limitado a M1–M5**, con las exclusiones PP-06 a PP-10. `[CONFIRMADO]`
- **Provisión administrativa controlada.** Las operaciones administrativas se hacen por provisión; no hay tercer rol funcional ni administración del supervisor. `[CONFIRMADO]` (RN-33)
- **Zona horaria única.** La fecha laboral se interpreta según la zona horaria configurada para la organización. `[CONFIRMADO]` (RN-44)
- **Informes asistidos por IA.** Los informes se generan con asistencia de IA, según la definición del módulo M5. `[CONFIRMADO]`
- **Stack tecnológico.** Flutter Web, FastAPI/Python y PostgreSQL, con monolito modular y autorización centralizada en el backend. `[CONFIRMADO]` (PP-01, ADR-001 aprobado en `docs/arquitectura/adr/ADR-001-stack-tecnologico.md`). El proveedor del servicio de IA, el mecanismo de autenticación y el despliegue no están decididos (PA-09, PA-12).
- **Proveedor, conservación y tratamiento de datos del servicio de IA.** Sin decidir (PA-09). `[ABIERTO]`

### 8.2 Supuestos `[SUPUESTO]`
Se asumen sin evidencia. Si alguno es falso, afecta al MVP.

| ID | Supuesto | Si es falso |
|---|---|---|
| S-01 | Las necesidades de colaboradores y supervisores descritas en la sección 2 reflejan lo que realmente necesitan. | Los módulos pueden no resolver el problema real. |
| S-02 | Los equipos aceptarán sustituir el reporte por mensajería por el registro en SMARTWORK. | No hay adopción y el histórico queda incompleto. |
| S-03 | Las personas pueden dedicar a diario el tiempo necesario para planificar, actualizar y cerrar su jornada. | Las bitácoras se rellenan tarde o no se rellenan. |
| S-04 | Los registros tendrán detalle suficiente para que la IA genere informes útiles. | Los informes serán pobres o repetirán el resumen libre. |
| S-05 | Las bitácoras contienen información laboral de personas identificables y esto conlleva obligaciones de privacidad. El marco legal aplicable no está identificado. | Los requisitos de privacidad pueden ser insuficientes o incorrectos. |

El supuesto S-06 (una sola zona horaria) deja de serlo: lo resuelve RN-44.

## 9. Métricas de éxito propuestas `[PROPUESTO]`

Ninguna está aprobada como métrica. Está aprobada la distinción entre las que se miden dentro del sistema y las que requieren una línea base externa (PP-30). No se fijan objetivos numéricos hasta medir la situación actual (PA-11).

| ID | Métrica | Fuente de la medición | Cómo se mide | Objetivo |
|---|---|---|---|---|
| ME-01 | **Adopción de la bitácora.** Proporción de jornadas laborales de personas activas con bitácora cerrada. | **Mixta** | El numerador sale del sistema. El denominador exige definir "persona activa" y las jornadas esperadas (sin calendario de festivos en el MVP). Mide el cierre, no la calidad del contenido. | Por definir (PA-11) |
| ME-02 | **Abandono del canal anterior.** Reportes de actividad diaria que el equipo sigue haciendo por mensajería. | **Línea base externa** | Observación o encuesta al equipo antes y después. | Por definir (PA-11) |
| ME-03 | **Tiempo de elaboración de un informe.** Tiempo para obtener un informe con SMARTWORK frente al método manual. | **Mixta** | El tiempo en SMARTWORK se mide en el sistema. El tiempo del método manual exige una línea base externa y un protocolo. | Por definir (PA-11) |
| ME-04 | **Respaldo de los informes de IA.** Afirmaciones de una muestra de informes que no constan en los registros. | **Revisión de muestra** | Revisión manual de una muestra de informes frente a los registros. Como los informes no se conservan (RN-56), la muestra se revisa en el momento de generarse. | Cero afirmaciones sin respaldo (consecuencia de RN-06). Tamaño de muestra y tolerancia por definir (PA-11) |
| ME-05 | **Recuperación de antecedentes.** Tiempo y pasos para localizar lo que una persona hizo en un rango de fechas, con el filtro por colaborador y fechas (RN-25). | **Línea base externa** | Prueba cronometrada frente a la búsqueda en el chat. | Por definir (PA-11) |
| ME-06 | **Duplicaciones de actividades.** Actividades creadas que repiten el trabajo de otra existente. La coincidencia de títulos no basta para considerarla duplicación (RN-32). | **Revisión de muestra** | Revisión manual de una muestra de actividades de varias jornadas con un criterio basado en el trabajo descrito. Las actividades registradas por error se excluyen (RN-60). | Por definir (PA-11) |

---

## 10. Puntos abiertos y dependencias

Resueltos por reglas confirmadas: **PA-01** (RN-14, RN-18), **PA-02** (RN-12, RN-36), **PA-03** (RN-10, RN-21, RN-22), **PA-05** (RN-13, RN-47, RN-48), **PA-07** (RN-39 a RN-43, RN-65 a RN-71), **PA-08** (RN-53 a RN-58), **PA-10** (RN-15), **PA-14** (RN-44, RN-45, RN-72), **PA-15** (RN-46), **PA-16** (RN-59, RN-60), **PA-17** (RN-73 a RN-76), **PA-18** (RN-36), **PA-19** (RN-57), **PA-20** (RN-73, RN-77, RN-78), **PA-21** (RN-81 a RN-87), **PA-22** (RN-88 a RN-90), **PA-23** (RN-91 a RN-93) y **PA-26** (RN-101).

| ID | Tema | Resuelto | Pendiente | Depende de | Requisitos afectados |
|---|---|---|---|---|---|
| PA-04 | Roles, permisos y pertenencia | RN-11, RN-23, RN-28, RN-33 a RN-38 | Cómo corregir una bitácora cuyo propietario no puede acceder (por baja o ausencia) | PA-06 | RF-20, RF-54 |
| PA-06 | Auditoría | RN-19, RN-45, RN-49 a RN-52, RN-103, RN-111 | Política de retención; visibilidad y retención de las entradas de provisión | PA-09, PA-13 | RF-21, RF-73, RF-113, RF-121, RNF-10 |
| PA-09 | Privacidad y servicio de IA | RN-30, RN-31 | Proveedor y modalidad; conservación; tratamiento de datos; marco legal; qué es "necesario"; percepción de vigilancia | — | RF-34, RF-49, RNF-06 |
| PA-11 | Métricas de éxito | PP-30 | Objetivos numéricos y líneas base | PA-13 | ME-01 a ME-06 |
| PA-12 | Detalles del acceso inicial, de la recuperación y de la reactivación administrativa | RN-33 a RN-35, RN-64, RN-96, RN-102 | Caducidad del acceso inicial; credencial propia en el primer ingreso; medio de entrega; verificación de la identidad al recuperar el acceso; operación para reactivar un acceso desactivado; identificación de quien opera la provisión | — | RF-55, RF-56, RF-106, RF-112 |
| PA-13 | Objetivos no funcionales cuantitativos e idioma | — | Todos los valores | — | RNF-05, RNF-10 |
| PA-24 | Reincorporación de personas dadas de baja | RN-94, RN-96 | Flujo de reincorporación; reactivación del acceso; planificación conservada dentro del nuevo período | PA-12, PA-25 | RF-104, RF-106 |
| PA-25 | Ajustes históricos excepcionales de pertenencia y altas históricas | RN-95, RN-106 | Si se autorizan y con qué mecanismo | — | RF-105, RF-116 |

**Propuestas pendientes de aprobación:** PP-03 (clientes externos), PP-11 (RF-34), PP-33 (RNF-06), PP-35 (RNF-09), PP-43 (versionado de la planificación), PP-44 (reubicación de avances) y PP-45 (edición del título).

### 10.1 Bloqueos que impiden especificar completamente una funcionalidad

| Funcionalidad | Qué impide especificarla | Punto |
|---|---|---|
| Acceso inicial y recuperación (M1) | Caducidad, credencial propia, medio de entrega, verificación de identidad, reactivación administrativa del acceso e identificación de quien opera la provisión | PA-12 |
| Reincorporación de personas dadas de baja (M1) | No hay flujo definido | PA-24 |
| Retención de la auditoría (M3) | La política no está definida | PA-06 |
| Corrección de la bitácora de una persona dada de baja (M3) | Hoy nadie puede corregirla | PA-04 |
| Informes con el servicio de IA (M5) | Proveedor, conservación, tratamiento de datos y marco legal | PA-09 |
| Verificación del respaldo de los informes (M5) | Los enlaces a los registros de origen no están aprobados | PP-11 |
| Requisitos cuantitativos | Sin umbrales acordados | PA-13 |

Ninguno impide especificar el comportamiento de cierre, reapertura, planificación, visibilidad, vista del supervisor, contenido de los informes ni corrección de errores.

**Orden recomendado para resolver:** PA-12, PA-09, PA-06 y el resto.

---

## Anexo A. Glosario

| Término | Significado |
|---|---|
| **Jornada** | La bitácora de una persona en una fecha laboral (RN-16). |
| **Jornada pasada** | Jornada cuya fecha laboral es anterior a la fecha actual en la zona horaria configurada de la organización (RN-72). |
| **Jornada futura** | Jornada cuya fecha laboral es posterior a la fecha actual en la zona horaria de la organización. |
| **Bitácora** | Registro de la jornada de una persona: actividades y resumen libre. |
| **Propietario** | La persona a la que pertenece una bitácora o una actividad. |
| **Período de actividad** | Tramo continuo de fechas laborales en que una persona tiene pertenencia, sin solapes ni huecos (RN-94). |
| **Desactivación de acceso** | Acción administrativa que impide desde ese momento toda operación autenticada de una persona, sin modificar sus registros (RN-96). |
| **Finalización de pertenencia** | Fin de la pertenencia de una persona a su equipo con fecha efectiva posterior a la actual (RN-96). |
| **Referencia neutral** | Identificación de una actividad iniciada en otro equipo que no revela su título ni otros datos protegidos (RN-101). |
| **Planificación conservada** | Planificación futura que sigue existiendo tras la finalización de la pertenencia de su propietaria y no se muestra como trabajo vigente (RN-105). |
| **Supervisión efectiva** | Situación de un equipo cuyo supervisor asignado conserva el acceso. Si lo pierde, el equipo queda pendiente de supervisión efectiva (RN-98). |
| **Actividad** | Unidad de trabajo con identidad propia y un único propietario, que puede continuar durante varias jornadas y tiene un estado actual (RN-08, RN-09, RN-43). |
| **Registro de avance** | Lo que se informa sobre una actividad en una jornada concreta, con su fecha laboral, su descripción y el estado que tenía la actividad en ese momento (RN-41). |
| **Continuada** | Actividad con al menos un avance de ejecución con la fecha laboral de la jornada. Una continuación únicamente planificada no cuenta (RN-21). |
| **Reactivación** | Acción explícita y auditada del propietario que devuelve a un estado no completado una actividad Completada, sin duplicarla (RN-40). |
| **Estado al corte** | Estado que tenía una actividad en la fecha de corte del período seleccionado. Se distingue del estado actual (RN-48). |
| **Secuencia de avances** | Los avances de una actividad ordenados por fecha laboral, momento real de registro e identificador estable de desempate (RN-65). El estado actual es el del último (RN-66). |
| **No vacío** | Texto que contiene algún carácter distinto de un espacio. Se aplica al resumen libre (RN-21) y a la descripción de un avance (RN-70). |
| **Pertenencia histórica** | Equipo al que pertenecía el propietario de un registro en la fecha laboral de ese registro (RN-36). |
| **Avance de ejecución** | Registro de lo realizado sobre una actividad en una jornada, con su fecha laboral, descripción y estado. Solo los avances de ejecución forman la secuencia y determinan el estado actual (RN-41, RN-65, RN-66, RN-75). |
| **Continuación planificada** | Planificación, para una fecha futura, de la continuación de una actividad existente. No es un avance de ejecución, no modifica el estado actual y no participa en la secuencia (RN-75, RN-76). |
| **Avance de finalización** | Avance que deja una actividad en el estado Completada (RN-77). |
| **Referencia mínima** | Información reducida y filtrada de una actividad pendiente iniciada en otro equipo que ve el supervisor actual: propietario, indicación de que se inició en otro equipo y estado actual, sin detalles históricos protegidos (RN-84). |
| **Pertenencia aplicable** | Equipo al que pertenece el propietario de un registro en la fecha laboral de ese registro, según el historial de pertenencias; para una fecha posterior al último cambio registrado, es la pertenencia vigente (RN-36, RN-87). |
| **Planificación original** | Lo previsto para una actividad cuando se planificó (RN-20). |
| **Actividad no planificada** | Actividad registrada sin planificación previa. Es una identificación, no un estado (RN-20). |
| **Registrada por error** | Marca lógica de corrección de una actividad creada por error. No es un estado y no implica borrado físico (RN-59, RN-60). |
| **Resumen libre** | Texto libre de la bitácora, complementario a las actividades estructuradas. |
| **Fecha laboral** | Día de trabajo al que corresponde un registro, según la zona horaria de la organización (RN-44). |
| **Fecha real de registro** | Momento en que el registro se creó realmente. |
| **Fecha de modificación** | Momento de la última modificación del registro (RN-18). |
| **Registro retroactivo** | Registro cuya fecha laboral es anterior al día en que se registra realmente. |
| **Cierre / reapertura** | Cierre manual de la jornada (RN-10) y posibilidad de reabrirla para corregirla con auditoría (RN-01, RN-19). |
| **Equipo / organización** | Agrupación de personas; la organización contiene varios equipos (RN-15). |
| **Provisión administrativa controlada** | Procedimiento operado fuera de los roles funcionales para crear usuarios y equipos, asignar pertenencias, dar de baja lógicamente y recuperar el acceso (RN-33, RN-34). |
| **Auditoría** | Registro de las reaperturas, correcciones posteriores al cierre y modificaciones retroactivas, y de las reactivaciones y marcas de error (RN-40, RN-49, RN-60). |
| **Agregación** | Dato calculado de forma determinista a partir de los registros, distinto de un hecho registrado (RN-26, RN-55). |

## Anexo B. Matriz de permisos

Solo se marcan como decididas las celdas respaldadas por una regla confirmada.

| Acción | Colaborador | Supervisor |
|---|---|---|
| Registrar y modificar sus propios registros | Sí (RN-11, RN-23) | Sí (RN-11, RN-23) |
| Planificar jornadas futuras (actividades nuevas, solo Pendiente) | Sí (RN-46) | Sí (RN-46) |
| Planificar la continuación de una actividad propia existente | Sí, si no está Completada (RN-76, RN-78) | Sí, si no está Completada (RN-76, RN-78) |
| Cerrar su jornada (no futura) | Propietario (RN-23, RN-46) | Propietario (RN-23, RN-46) |
| Reabrir y corregir su bitácora | Sí (RN-19) | Sí (RN-19) |
| Reabrir o corregir bitácoras ajenas | No (RN-19, RN-23) | No (RN-19, RN-23) |
| Reactivar una actividad Completada | Propietario (RN-40) | Propietario (RN-40) |
| Registrar un avance retroactivo anterior a la finalización de una Completada | Propietario, sin reactivar (RN-77) | Propietario, sin reactivar (RN-77) |
| Marcar una actividad como registrada por error | Propietario (RN-59) | Propietario (RN-59) |
| Consultar bitácoras | Lectura de los registros que pertenecen históricamente a su equipo (RN-12, RN-36) | Lectura de los registros que pertenecen históricamente a su equipo (RN-23, RN-36) |
| Consultar otros equipos | No (RN-63) | No (RN-36, RN-37) |
| Vista consolidada del equipo | No (RN-13) | Sí (RN-13, RN-47) |
| Ver la auditoría | Propietario (RN-51) | Propietario y supervisor autorizado del equipo del registro (RN-51) |
| Ver la referencia mínima de una actividad pendiente iniciada en otro equipo | No | Sí, de las personas que supervisa (RN-84) |
| Consultar el historial completo de las propias actividades tras un traslado | Propietario (RN-83) | Propietario (RN-83) |
| Generar informe individual | Solo el propio (RN-53) | El propio y los de su equipo; el de quien ya no integra su equipo, limitado a los registros históricos de su equipo (RN-53) |
| Generar informe consolidado | No (RN-54) | De su equipo (RN-54) |
| Crear usuarios y equipos; pertenencias, su cancelación o sustitución; desactivar el acceso; finalizar pertenencias; recuperar acceso | No (RN-33, RN-99) | No (RN-33, RN-99). Lo hace la provisión controlada |
| Ver el título original y la marca de error de una actividad iniciada en otro equipo | Solo la propietaria y quienes están autorizados sobre su jornada de origen (RN-101) | Solo la propietaria y quienes están autorizados sobre su jornada de origen (RN-101) |

## Historial de cambios

| Versión | Cambios |
|---|---|
| 0.12 | Alineado con el alcance 0.14. Se incorporan RN-111 a RN-113 y RF-121 a RF-123. Se reescriben RF-26 (rango obligatorio, colaborador opcional) y RF-111 (referencia neutral). Se resuelve PA-26 y se acota PA-06. |
| 0.11 | Alineado con el alcance 0.13. Se incorporan RN-107 a RN-110, RF-117 a RF-120 y RNF-13. Se reescriben RF-18 (actividad válida) y RF-70 (el corte es el último día del período). |
| 0.10 | Alineado con el alcance 0.12. Se reescriben RF-108, RF-109, RF-112 y RF-114 para reflejar RN-98, RN-99, RN-102 y RN-104 con su redacción confirmada. No se añaden requisitos. |
| 0.9 | Alineado con el alcance 0.11. Se incorporan RN-94 a RN-106 y los requisitos RF-104 a RF-116. Se reescriben RF-54 y RF-55 (textos anteriores: RF-54, «La baja de una persona es lógica: deja de poder acceder y su histórico se conserva.»; RF-55, sin la frase sobre el acceso desactivado). Se añaden PA-24 a PA-26 y PP-43 a PP-45; se amplían PA-06 y PA-12. Se amplían el glosario y la matriz de permisos. |
| 0.8 | Alineado con el alcance 0.10. Se incorporan RN-88 a RN-93 y los requisitos RF-98 a RF-103. Se reescribe RF-70. Se resuelven PA-22 y PA-23. La restricción de stack pasa a confirmada mediante ADR-001. |
| 0.7 | Alineado con el alcance 0.9. Se incorporan RN-79 a RN-87 y los requisitos RF-90 a RF-97. Se reescriben RF-69, RF-70, RF-83 y RF-88. Se resuelve PA-21 y se añaden PA-22 y PA-23. Se actualizan el glosario, el anexo de permisos y los bloqueos. Se referencia el ADR-001 en las restricciones. |
| 0.6 | Alineado con el alcance 0.8. Se incorporan RN-77 y RN-78 y los requisitos RF-88 y RF-89. Se reescriben RF-33, RF-84, RF-86 y RF-87. Se resuelve PA-20. PA-21 sigue abierto a la espera de la aprobación final de PP-40. Se actualizan el glosario y el anexo de permisos. |
| 0.5 | Alineado con el alcance 0.7. Se incorporan RN-73 a RN-76 y los requisitos RF-84 a RF-87. Se reescriben RF-18, RF-33, RF-42, RF-43, RF-61, RF-62, RF-65, RF-66, RF-83 y RNF-01. Se resuelven PA-17, PA-18 y PA-19, y se añaden PA-20 y PA-21. Se actualizan el glosario, el anexo de permisos y los bloqueos. |
| 0.4 | Alineado con el alcance 0.6. Se incorporan RN-65 a RN-72. RF-62 y RF-80 pasan a confirmados. Se añaden RF-81, RF-82 y RF-83. Se reescriben RF-07, RF-23, RF-24, RF-59, RF-61, RF-65, RF-66, RF-67 y RNF-01. Se resuelve PA-07 y se añaden PA-17, PA-18 y PA-19. Se armoniza la pertenencia histórica de los registros (RN-12, RN-36, RN-63). Se añaden la definición de jornada pasada y los términos del glosario. |
| 0.3 | Alineado con el alcance 0.5. Se incorporan RN-33 a RN-64 y los requisitos RF-52 a RF-80. RF-01, RF-16, RF-22, RF-24 y RF-33 pasan a confirmados. RNF-08 pasa a confirmado. RNF-11 se retira (absorbido por RF-58). Se reescriben los requisitos afectados por las decisiones D-1 a D-8. Se resuelven PA-05, PA-08, PA-14, PA-15 y PA-16, y se reducen PA-04, PA-06, PA-07 y PA-12. Se actualizan el anexo de permisos, el glosario y los bloqueos. Se propone PP-36 (regla de orden) y PP-37 (estado inicial de lo no planificado). |
| 0.2 | Alineado con el alcance 0.4. Se incorporan RN-16 a RN-32 y los requisitos RF-35 a RF-51 y RNF-12. Se reclasifican RF-01, RF-16 y RF-24. Se retiran RF-31 y RNF-07. |
| 0.1 | Versión inicial. |
