# SMARTWORK — Alcance del MVP

| | |
|---|---|
| **Estado** | Vigente; la versión 0.14 está pendiente de revisión |
| **Versión** | 0.14 |
| **Fecha** | 2026-11-06 |
| **Documentos relacionados** | `docs/producto/prd.md` (versión 0.12), `docs/backlog/` (historias de usuario), `docs/modelo-datos/modelo-datos.md` (modelo de datos propuesto) y `docs/api/` (contratos propuestos) |

## Leyenda de estados

| Marca | Significado |
|---|---|
| `[CONFIRMADO]` | Aprobado explícitamente por la persona responsable del producto. Es el único contenido que puede convertirse en requisito. |
| `[PROPUESTO]` | Sugerencia no aprobada. No se implementa ni se trata como requisito. |
| `[ABIERTO]` | Decisión pendiente. Se registra con su argumento y lo necesario para decidirla. |
| `[SUPUESTO]` | Afirmación sin evidencia verificada. |

Identificadores: `RN-XX` (regla de negocio confirmada), `PP-XX` (propuesta), `PA-XX` (punto abierto). Los identificadores son estables: una propuesta o un punto abierto resuelto conserva su identificador y remite a la regla `RN-XX` que lo resuelve. Una regla enmendada conserva su identificador y deja constancia del cambio en el historial.

---

## 1. Problema

Los equipos de trabajo comunican hoy sus actividades diarias mediante mensajería instantánea (WhatsApp). `[CONFIRMADO]`

Consecuencias que SMARTWORK busca resolver: `[CONFIRMADO]`

- **Pérdida de información.** Lo que se reporta queda enterrado en conversaciones.
- **Dificultad para consultar antecedentes.** No hay una forma fiable de saber qué se hizo, cuándo y por qué.
- **Trabajo manual para elaborar informes.** Quien necesita un informe lo reconstruye a mano a partir de mensajes dispersos.

El problema no es solo registrar actividades, sino distinguir **lo planeado de lo realmente hecho**, y conservar **lo que quedó pendiente** y **los bloqueos**.

## 2. Usuarios

### 2.1 Qué hacen hoy
Reportan y consultan actividades mediante mensajes de chat, y elaboran informes manualmente. `[CONFIRMADO]`

### 2.2 Quiénes son
Existen dos roles funcionales y no se añade un tercero: `[CONFIRMADO]` (RN-11, RN-33)

- **Colaborador:** registra y modifica sus propias actividades y consulta, en modo lectura, las bitácoras que le corresponden por su equipo (RN-12, RN-36).
- **Supervisor:** pertenece al equipo que supervisa y supervisa únicamente un equipo (RN-37). Registra su propia bitácora como cualquier otra persona y dispone de una vista consolidada de su equipo (RN-13). Consulta los registros de su equipo sin modificarlos (RN-23). No administra usuarios ni equipos (RN-33).

En el MVP cada persona pertenece a un único equipo y cada equipo tiene un único supervisor (RN-28). La creación de usuarios y equipos, la asignación de pertenencias, la baja lógica y la recuperación de acceso se realizan mediante una provisión administrativa controlada (RN-33, RN-34). `[CONFIRMADO]`

### 2.3 Quién no es el usuario
- Quien busca una herramienta de evaluación del desempeño individual. No se incorporan rankings ni evaluación del desempeño (PP-09). `[CONFIRMADO]`
- Personas externas al equipo, como clientes. `[PROPUESTO]` (PP-03)

## 3. Propuesta de valor

Un único lugar donde cada persona registra qué planea hacer, qué hizo realmente, qué quedó pendiente y qué bloqueos tuvo, de modo que: `[CONFIRMADO]`

- Cada colaborador planifica lo que prevé hacer, incluso con antelación, y después actualiza lo realizado (RN-07, RN-46).
- Lo planificado se conserva aunque después se actualice lo realizado (RN-20).
- La información se conserva y se puede consultar después, conforme al equipo al que pertenecía cada persona (RN-36).
- El trabajo que continúa de una jornada a otra se sigue sin duplicarse (RN-39).
- Cualquier corrección retroactiva queda auditada (RN-45, RN-49).
- Los informes se generan con apoyo de IA a partir de lo realmente registrado, sin valoraciones de desempeño (RN-06, RN-55).

## 4. Alcance del MVP

El MVP está formado por cinco módulos obligatorios, diseñados para una organización con varios equipos (RN-15). `[CONFIRMADO]` El producto es una plataforma web (descripción inicial del producto). `[CONFIRMADO]`

| Módulo | Nombre | Qué agrupa a nivel de producto | Estado |
|---|---|---|---|
| **M1** | Autenticación, usuarios y equipos | Acceso de personas identificadas (RN-61), dos roles funcionales (RN-11), una persona por equipo y un supervisor por equipo (RN-28, RN-37). Provisión administrativa controlada para crear usuarios y equipos, asignar pertenencias, dar de baja lógicamente y recuperar el acceso, con un primer acceso seguro, individual y de un solo uso (RN-33 a RN-35, RN-38). Las pertenencias forman períodos de actividad sin solapes ni huecos, los cambios son futuros y los programados pueden cancelarse o sustituirse; la baja lógica distingue la desactivación inmediata del acceso de la finalización de la pertenencia; un equipo con colaboradores tiene siempre un supervisor válido (RN-94 a RN-99, RN-102, RN-106). | `[CONFIRMADO]`. Pendiente: detalles del acceso inicial, reactivación administrativa del acceso y quién opera la provisión (PA-12); reincorporación (PA-24); ajustes históricos (PA-25) |
| **M2** | Bitácoras laborales híbridas | Una bitácora por persona y fecha laboral (RN-16), con actividades estructuradas y resumen libre. Planificación diaria y anticipada: actividades nuevas en estado Pendiente y continuación de actividades existentes, sin modificar su estado ni su secuencia de avances (RN-07, RN-46, RN-75, RN-76), planificación original conservada (RN-20), cuatro estados (RN-08), avances ordenados de forma estable, con fecha laboral, estado histórico y descripción no vacía (RN-41, RN-65, RN-66, RN-70), motivo obligatorio de bloqueo (RN-24), un propietario por actividad (RN-43), fecha laboral según la zona horaria de la organización (RN-44) y tres fechas diferenciadas (RN-18). La planificación original se conserva sin edición ordinaria y el título no se edita en el flujo ordinario (RN-104). La planificación futura que queda sin pertenencia se conserva sin mostrarse como trabajo vigente (RN-105). La bitácora de una persona y fecha laboral es única y se abre de forma explícita o implícita (RN-107). | `[CONFIRMADO]` |
| **M3** | Seguimiento de actividades y auditoría | Continuidad por selección explícita de una actividad propia, sin duplicarla (RN-04, RN-09, RN-39, RN-40). Reactivación explícita y auditada de una actividad Completada, necesaria para que reciba nuevos avances posteriores a su finalización; los avances retroactivos anteriores a la finalización no la requieren, y no se planifica la continuación de una Completada sin reactivarla (RN-40, RN-73, RN-74, RN-77, RN-78). Cierre manual con actividades en cualquier estado (RN-10, RN-21, RN-22). Reapertura y corrección por el propietario con auditoría de reaperturas, correcciones posteriores al cierre y modificaciones de jornadas pasadas (RN-01, RN-19, RN-45, RN-49 a RN-51). Corrección lógica de actividades registradas por error (RN-59, RN-60). La reactivación admite Pendiente, En progreso o Bloqueada con motivo (RN-100). Cada operación genera una única entrada de auditoría (RN-103). Modificar una jornada cerrada exige reabrirla antes (RN-108). Las actividades marcadas por error no cuentan para el cierre (RN-109). La auditoría de la provisión se separa de la consulta funcional (RN-110). | `[CONFIRMADO]`. Pendiente: política de retención de la auditoría (PA-06) |
| **M4** | Consulta histórica y supervisión | Consulta histórica con filtro por colaborador y rango de fechas (RN-25). Visibilidad conforme al equipo de la persona en la fecha laboral del registro (RN-36). Referencia mínima de las actividades heredadas de otro equipo (RN-84). Vista consolidada del supervisor con criterio de inclusión, estado al corte y estado actual (RN-13, RN-47, RN-48). El título original de una actividad iniciada en otro equipo no se expone: se usa una referencia neutral (RN-101). | `[CONFIRMADO]` |
| **M5** | Informes individuales y consolidados con IA | Informes individuales (por su propietario o su supervisor) y consolidados por equipo y período (por su supervisor), con período, fecha de generación, hechos, agregaciones deterministas y bloqueos con motivo (RN-03, RN-53 a RN-55). Se consultan en pantalla, no se editan ni se conservan como historial (RN-56). Indican explícitamente si faltan registros y si el servicio de IA falla (RN-57, RN-58). Solo usan información autorizada y necesaria, y tratan el texto libre como datos (RN-30, RN-31). Aplican la misma política de referencia neutral que las vistas (RN-101). | `[CONFIRMADO]`. Pendiente: proveedor, conservación y tratamiento de datos (PA-09) |

Límite de alcance: lo que no pertenece a M1–M5 queda fuera del MVP mientras no se apruebe explícitamente lo contrario. `[CONFIRMADO]`

Las historias de cada módulo pueden descomponerse para facilitar implementación y pruebas. Esa descomposición no añade funcionalidades. `[CONFIRMADO]`

## 5. Fuera de alcance

Exclusiones aprobadas para mantener el MVP acotado. `[CONFIRMADO]`

| ID | Exclusión | Justificación |
|---|---|---|
| PP-06 | Notificaciones y recordatorios (correo, push, mensajería). | Ningún módulo confirmado los requiere. Añaden integraciones y canales. |
| PP-07 | Aplicación móvil nativa. | El MVP es una plataforma web. |
| PP-08 | Importación de conversaciones desde WhatsApp u otra mensajería. | El problema se resuelve registrando en SMARTWORK, no migrando chats. |
| PP-09 | Evaluación del desempeño, rankings o métricas de productividad por persona. | No forma parte de ningún módulo y agrava el riesgo de percepción de vigilancia. Reafirmada: no se incorporan rankings ni evaluación de desempeño. |
| PP-10 | Gestión avanzada de proyectos y tareas: sprints, asignaciones complejas, estimaciones y tableros tipo gestor de proyectos. | SMARTWORK registra y da seguimiento a las actividades de la jornada de cada colaborador. |

También quedan fuera del MVP, por decisión expresa: un panel administrativo avanzado (no obligatorio, RN-33), un calendario de días festivos (RN-44), el historial automático de informes y la edición de informes (RN-56) y el borrado físico de actividades (RN-59).

La planificación diaria y anticipada de actividades **no** está excluida: forma parte del MVP (RN-07, RN-46).

Consecuencia de RN-15 `[A CONFIRMAR]`: al diseñarse el MVP para una única organización, no se contempla servir a varias organizaciones aisladas entre sí.

---

## 6. Registro de decisiones

### 6.1 Confirmadas `[CONFIRMADO]`

La redacción de RN-16 a RN-113 se deriva de las decisiones y propuestas que la persona responsable aprobó en las revisiones de las versiones 0.3 a 0.10, y se somete a su revisión final.

| ID | Regla | Módulos | Resuelve | Fuente |
|---|---|---|---|---|
| RN-01 | Las bitácoras cerradas pueden reabrirse y corregirse, con auditoría. | M2, M3 | — | Instrucción del responsable del producto |
| RN-02 | Los colaboradores pueden consultar bitácoras de compañeros. | M4 | Se acota por RN-12 y RN-36 | Ídem |
| RN-03 | Se permiten informes individuales y consolidados. | M5 | Se concreta en RN-53 y RN-54 | Ídem |
| RN-04 | Las actividades pueden continuar durante varias jornadas sin duplicarse. | M2, M3 | Se concreta en RN-09, RN-32 y RN-39 | Ídem |
| RN-05 | Se distingue la fecha laboral de la fecha real de registro. | M2, M3, M4 | Se amplía en RN-18 | Ídem |
| RN-06 | Los resultados de la IA deben apoyarse en los registros almacenados. | M5 | — | Ídem |
| RN-07 | Cada colaborador puede registrar lo que tiene previsto hacer durante su jornada y posteriormente actualizar lo realizado. | M2 | — | Revisión de la versión 0.1 |
| RN-08 | Las actividades tienen uno de cuatro estados: Pendiente, En progreso, Bloqueada o Completada. La planificación inicial no constituye un estado adicional. Una actividad recién planificada comienza en Pendiente. | M2, M3 | PP-05 | Revisión de la versión 0.2 |
| RN-09 | Una actividad conserva su identidad durante varias jornadas y puede tener múltiples registros de avance asociados a diferentes fechas laborales, sin duplicarse. Se distingue conceptualmente entre actividad y registro de avance. | M2, M3 | PA-07 | Ídem |
| RN-10 **[ENMENDADA v0.4]** | El cierre de jornada es manual. Las condiciones para cerrar están en RN-21 y los estados admitidos en RN-22. | M2, M3 | PA-03 | Revisión de la versión 0.2; enmienda de la versión 0.4 |
| RN-11 | Existen dos roles funcionales: colaborador y supervisor. Cada uno puede registrar y modificar sus propias actividades. El supervisor también registra su propia bitácora. | M1, M2, M4 | PP-02, PA-04 (parcial) | Revisión de la versión 0.2 |
| RN-12 **[ENMENDADA v0.6]** | Los colaboradores pueden consultar, únicamente en modo lectura, los registros de compañeros que pertenecen históricamente a su equipo, conforme a RN-36. No pueden modificar registros ajenos. | M4 | PA-02. Se precisa en RN-36 | Ídem; armonización de la versión 0.6 |
| RN-13 **[ENMENDADA v0.4]** | El supervisor tiene acceso a una vista consolidada de su equipo, para el período seleccionado, con las actividades en los cuatro estados definidos en RN-08 y su historial. La vista no incluye clasificaciones ni puntuaciones de personas. | M4 | PP-17. Se precisa en RN-47 y RN-48 | Revisión de la versión 0.2; enmienda de la versión 0.4 |
| RN-14 **[REDACCIÓN ALINEADA v0.4]** | Se permiten registros retroactivos con trazabilidad de la fecha laboral y de la fecha real de registro, sin imponer inicialmente un límite fijo de días. | M2, M3 | PA-01 | Revisión de la versión 0.2 |
| RN-15 | El MVP está diseñado para una organización con varios equipos. | M1, M4 | PA-10 | Ídem |
| RN-16 | Existe una bitácora por usuario y fecha laboral. Esa bitácora es la jornada de la persona en esa fecha. | M2, M3 | PP-04 | Decisión de la versión 0.4 |
| RN-17 | Cada registro de avance conserva el estado histórico de la actividad en ese momento. La actividad mantiene un estado actual. Las correcciones retroactivas no reescriben silenciosamente el historial: quedan auditadas (RN-19). | M2, M3 | PP-13 | Ídem |
| RN-18 | Se distinguen tres fechas: la fecha laboral, la fecha real de registro y la fecha de modificación. | M2, M3, M4 | PP-13 | Ídem |
| RN-19 | El propietario de una bitácora puede reabrirla y corregirla. La reapertura y las correcciones quedan auditadas, incluidas las modificaciones retroactivas correspondientes a jornadas pasadas. | M3 | PP-19 | Ídem |
| RN-20 | La planificación original de una actividad (lo previsto) se conserva aunque posteriormente se actualice lo realizado. Una actividad puede registrarse sin planificación previa y entonces se identifica como no planificada. Esto es una identificación y no un estado adicional. | M2 | PP-14 | Ídem |
| RN-21 **[ENMENDADA v0.13]** | Una jornada puede cerrarse cuando contiene al menos una actividad válida, no marcada como registrada por error (RN-109), creada o continuada en esa jornada y un resumen libre no vacío. "Continuada" significa que tiene al menos un avance de ejecución con esa fecha laboral; una continuación únicamente planificada no cuenta. "No vacío" significa que contiene algún carácter distinto de un espacio. | M2, M3 | PP-15, PA-03 | Ídem; confirmación de la versión 0.8; enmienda de la versión 0.13 |
| RN-22 | Una jornada puede cerrarse con actividades en cualquiera de los cuatro estados. Cerrar no modifica el estado de ninguna actividad. Las actividades no completadas permanecen abiertas y disponibles para registrarles avances en jornadas posteriores; no se copian ni se crean automáticamente. | M2, M3 | PP-16, PA-03 | Ídem |
| RN-23 | Cada persona modifica solo sus propios registros. El supervisor puede consultar los registros de su equipo sin modificarlos. | M1, M2, M4 | PP-18 | Ídem |
| RN-24 | Para marcar una actividad como Bloqueada es obligatorio indicar un motivo, que se conserva en el historial. | M2 | PP-20 | Ídem |
| RN-25 **[ENMENDADA v0.14]** | La consulta histórica exige un rango de fechas laborales y permite filtrar por colaborador, que es opcional según los permisos de quien consulta y la finalidad de la consulta, sin incorporar un motor de búsqueda avanzado. | M4 | PP-21 | Ídem; enmienda de la versión 0.14 |
| RN-26 | Los informes pueden incluir agregaciones calculadas a partir de los registros, diferenciadas de los hechos registrados y sin inventar información. Los informes no emiten valoraciones sobre las personas. | M5 | PP-22 | Ídem |
| RN-27 | Se permite planificar actividades en jornadas futuras. No se puede registrar trabajo futuro como ejecutado. | M2 | PP-24. Se precisa en RN-46 | Ídem |
| RN-28 **[ENMENDADA v0.11]** | En el MVP cada persona pertenece a un único equipo y cada equipo tiene un único supervisor. Cuando una persona cambia de equipo se conserva la trazabilidad de sus pertenencias anteriores. Las pertenencias forman períodos de actividad sin solapes ni huecos (RN-94) y sus cambios se rigen por RN-95 a RN-99. | M1, M4 | PP-26 | Ídem; enmienda de la versión 0.11 |
| RN-29 | Todo informe tiene un período explícito y una fecha de generación, respeta los permisos de la persona que lo genera y puede regenerarse. Los indicadores cuantitativos se calculan de forma determinista a partir de registros autorizados. | M5 | PP-27. Se completa en RN-53 a RN-58 | Ídem |
| RN-30 | Los informes con IA utilizan únicamente información autorizada y necesaria. | M5 | PP-23 | Ídem |
| RN-31 | El texto libre de las bitácoras se trata como datos y no como instrucciones. | M5 | PP-28 | Ídem |
| RN-32 | Continuar una actividad no genera otra actividad. La igualdad o la similitud de títulos no define por sí sola una duplicación. | M3 | PP-29 | Ídem |
| RN-33 | Las operaciones administrativas del MVP se realizan mediante una provisión administrativa controlada. No existe un tercer rol funcional y el supervisor no dispone de administración de usuarios ni de equipos. No se exige un panel administrativo avanzado. | M1 | PP-25 | Decisión de la versión 0.5 |
| RN-34 | M1 contempla procedimientos operables y verificables para crear usuarios y equipos, asignar pertenencias, dar de baja lógicamente y recuperar el acceso. | M1 | PP-25, PA-04, PA-12 (parcial) | Ídem |
| RN-35 | El primer acceso de cada persona se provee de forma segura, individual y de un solo uso. | M1 | PP-25, PA-12 (parcial) | Ídem |
| RN-36 **[ENMENDADA v0.7]** | Un registro pertenece históricamente al equipo que tenía su propietario en la fecha laboral correspondiente. Los integrantes autorizados de ese equipo pueden consultar ese registro histórico, aunque posteriormente el propietario se haya trasladado a otro equipo, y un integrante activo del equipo puede consultar los registros históricos que le corresponden aunque se haya incorporado después. Esto no concede acceso a los registros correspondientes a otros equipos ni a períodos en los que el propietario pertenecía a otro equipo. Las consultas, las vistas de supervisión y los informes respetan esta regla de igual manera, según los permisos de cada rol, tanto en las interfaces como en los controles de autorización. El cambio de equipo no expone automáticamente todo el historial de la persona al equipo nuevo. | M1, M4, M5 | PP-26, PA-04, PA-18 | Decisión de la versión 0.5; armonización de la versión 0.6; enmienda de la versión 0.7 |
| RN-37 | El supervisor pertenece al equipo que supervisa, su bitácora es visible en modo lectura conforme a RN-36 y supervisa únicamente un equipo. | M1, M4 | PA-04 (parcial) | Ídem |
| RN-38 **[ENMENDADA v0.11]** | La baja de una persona es lógica, no elimina su histórico y se compone de la desactivación de acceso y la finalización de la pertenencia (RN-96). | M1, M3 | PA-04 (parcial) | Ídem; enmienda de la versión 0.11 |
| RN-39 | Una actividad se continúa mediante la selección explícita de una actividad propia existente. | M3 | PA-07 | Ídem |
| RN-40 | Las actividades no completadas pueden recibir nuevos avances normalmente. Una actividad Completada puede reactivarse mediante una acción explícita y auditable de su propietario, sin duplicarla. | M2, M3 | PA-07 | Ídem |
| RN-41 | Cada avance conserva su fecha laboral, su estado histórico y la descripción del trabajo realizado. Se permiten varios avances de una actividad en una misma jornada. | M2, M3 | PA-07 | Ídem |
| RN-42 | El estado actual de una actividad se determina de forma consistente con la secuencia de sus avances y con las correcciones retroactivas auditadas. | M2, M3 | PA-07. Se concreta en RN-65 a RN-68 | Ídem |
| RN-43 | Cada actividad tiene un único propietario. | M2, M3 | PA-07 | Ídem |
| RN-44 | La fecha laboral se interpreta según la zona horaria configurada para la organización. En el MVP no se incorpora un calendario de días festivos. | M2, M3 | PA-14 | Ídem |
| RN-45 | Toda modificación de una jornada pasada se audita, esté la jornada abierta o cerrada. | M3 | PA-14, PA-06 (parcial) | Ídem |
| RN-46 **[ENMENDADA v0.7]** | La planificación futura de una actividad nueva se admite únicamente en estado Pendiente. No se registra ejecución futura ni se cierran jornadas futuras. La planificación futura de la continuación de una actividad existente se rige por RN-75 y RN-76. | M2, M3 | PA-15. Se precisa en RN-75 y RN-76 | Ídem; precisión de la versión 0.7 |
| RN-47 **[ENMENDADA v0.9]** | La vista del supervisor incluye las actividades del equipo que fueron planificadas o tuvieron avances durante el período, y las no completadas que permanecen pendientes de atención al final del período cuyo propietario pertenece al equipo en la fecha de corte. Cuando no existen registros del equipo sobre una actividad iniciada en otro equipo, se muestra solo su referencia mínima (RN-84). Incluye las actividades del propio supervisor. | M4 | PA-05, PA-21 | Decisión de la versión 0.5; enmienda de la versión 0.9 |
| RN-48 **[ENMENDADA v0.13]** | La vista del supervisor muestra el estado correspondiente al corte, que es el último día del período consultado, y lo distingue del estado actual cuando son diferentes, solo para actividades cuyo propietario pertenece al equipo. No muestra el estado al corte cuando deriva exclusivamente de registros protegidos de otro equipo (RN-88). No presenta como pendiente actual ni muestra el estado actual del trabajo de una persona que ya no pertenece al equipo (RN-85). No incorpora rankings ni evaluación de personas. | M4 | PA-05, PA-21, PA-22 | Decisión de la versión 0.5; enmiendas de las versiones 0.9, 0.10 y 0.13 |
| RN-49 | La auditoría registra las reaperturas, las correcciones posteriores al cierre y las modificaciones retroactivas. Cada entrada registra autor, fecha real, operación, valor anterior y valor nuevo. | M3 | PP-12, PA-06 (parcial) | Ídem |
| RN-50 | La reapertura requiere un motivo. Las correcciones conservan suficiente contexto para reconstruir el cambio. | M3 | PP-12, PA-06 (parcial) | Ídem |
| RN-51 | La auditoría es visible para el propietario y para el supervisor autorizado del equipo correspondiente al registro. | M3, M4 | PA-06 (parcial) | Ídem |
| RN-52 | La información no se borra silenciosamente. | M3 | PA-06 (parcial) | Ídem |
| RN-53 **[ENMENDADA v0.9]** | Un informe individual lo genera su propietario o el supervisor autorizado de su equipo. El supervisor de un equipo puede obtener el informe individual de una persona que ya no integra su equipo únicamente respecto de los registros históricos de ese equipo y de los períodos para los que conserva autorización; no accede a información posterior del equipo nuevo. | M5 | PA-08, PA-21 | Decisión de la versión 0.5; enmienda de la versión 0.9 |
| RN-54 | Un informe consolidado es por equipo y período, y lo genera su supervisor. | M5 | PA-08 | Ídem |
| RN-55 | Los informes muestran el período y la fecha de generación, los hechos registrados, agregaciones deterministas y los bloqueos con sus motivos, sin valoraciones de desempeño. | M5 | PA-08 | Ídem |
| RN-56 | En el MVP el informe se consulta en pantalla, no se edita y no se conserva automáticamente como historial de informes. Puede generarse nuevamente. | M5 | PA-08 | Ídem |
| RN-57 **[ENMENDADA v0.8]** | Si no existen registros autorizados en el período solicitado, el informe indica explícitamente que no hay datos disponibles. Si existen registros autorizados, el informe puede generarse con ellos y deja claro que se basa únicamente en los registros disponibles y que no representa información que nunca fue registrada. No se establecen umbrales de suficiencia ni porcentajes de cobertura. No se inventan actividades, personas, fechas, avances ni bloqueos. | M5 | PP-32, PA-08, PA-19 | Ídem; enmienda de las versiones 0.7 y 0.8 |
| RN-58 | Si falla el servicio de IA, se informa de que el informe no pudo generarse. No se presenta contenido parcial como informe completo. | M5 | PA-08 | Ídem |
| RN-59 | El propietario puede marcar una actividad como registrada por error, con un motivo, siempre que no tenga avances en jornadas posteriores a su creación. No hay borrado físico. | M3 | PP-31, PA-16 | Ídem |
| RN-60 | Una actividad registrada por error se excluye de las vistas operativas y de los recuentos ordinarios y permanece consultable dentro del historial autorizado y de la auditoría. La marca puede revertirse con auditoría. No constituye un quinto estado. | M3, M4, M5 | PP-31, PA-16 | Ídem |
| RN-61 | Solo las personas identificadas pueden acceder a las bitácoras y al resto de funciones. | M1 | RF-01 (ratificado) | Ratificación de la versión 0.5 |
| RN-62 | Los avances de una actividad se pueden consultar junto con su fecha laboral y su estado. | M3, M4 | RF-16 (ratificado) | Ídem |
| RN-63 **[ENMENDADA v0.6]** | Un colaborador no puede consultar los registros que pertenecen históricamente a otro equipo (RN-36). | M4 | RF-24 (ratificado) | Ratificación de la versión 0.5; armonización de la versión 0.6 |
| RN-64 | Las credenciales de las personas nunca se muestran ni se registran en claro. | M1 | PP-34 | Ídem |
| RN-65 **[ENMENDADA v0.7]** | Los avances de ejecución de una actividad se ordenan por fecha laboral, momento real de registro y un identificador estable de desempate. | M2, M3 | PP-36, PA-07 | Decisión de la versión 0.6; precisión de la versión 0.7 |
| RN-66 **[ENMENDADA v0.7]** | El estado actual de una actividad corresponde al último avance de ejecución de su secuencia. Una actividad planificada sin avances conserva el estado Pendiente. Un avance retroactivo anterior no sustituye el estado correspondiente a un avance con fecha laboral posterior. | M2, M3 | PP-36, PA-07 | Ídem |
| RN-67 | Las correcciones no alteran silenciosamente el historial: se auditan y el estado actual se recalcula cuando corresponde. | M2, M3 | PP-36, PA-07 | Ídem |
| RN-68 **[ENMENDADA v0.7]** | La reactivación de una actividad Completada se registra como un avance de ejecución de la secuencia de la actividad y debe reflejarse coherentemente en ella, incluso cuando existen avances retroactivos. | M3 | PP-36, PA-07, PA-17 | Decisión de la versión 0.6; enmienda de la versión 0.7 |
| RN-69 | Una actividad registrada sin planificación previa inicia con el estado de su primer avance, que es uno de los cuatro estados definidos en RN-08. Si inicia Bloqueada, es obligatorio registrar un motivo. No se incorpora un quinto estado. | M2 | PP-37 | Ídem |
| RN-70 | Todo avance exige una descripción no vacía del trabajo realizado o del cambio relevante. | M2, M3 | PA-07 | Ídem |
| RN-71 | La planificación inicial no constituye por sí misma un avance de ejecución. Se distinguen la planificación original, el registro de avance y el estado actual. | M2, M3 | PA-07 | Ídem |
| RN-72 | Una jornada pasada es aquella cuya fecha laboral es anterior a la fecha actual en la zona horaria configurada de la organización. | M2, M3 | PA-14 | Ídem |
| RN-73 **[ENMENDADA v0.8]** | Una actividad Completada requiere una reactivación explícita y auditada para recibir nuevos avances de ejecución posteriores a su finalización. | M3 | PA-17, PP-38 | Decisión de la versión 0.7; enmienda de la versión 0.8 |
| RN-74 | La reactivación se realiza sobre una jornada no futura y debe respetar la secuencia histórica de la actividad. | M3 | PA-17, PP-38 | Ídem |
| RN-75 | Una planificación futura no modifica el estado actual de una actividad. No constituye un avance de ejecución ni participa en la secuencia de avances ni en el cálculo del estado actual. | M2, M3, M4 | PA-17, PP-38 | Ídem |
| RN-76 **[ENMENDADA v0.8]** | Se permite planificar la continuación de una actividad existente para una fecha futura, sin crear una actividad duplicada. No se aplica a una actividad Completada (RN-78). | M2, M3 | PA-17, PP-38 | Decisión de la versión 0.7; enmienda de la versión 0.8 |
| RN-77 | Se permite registrar un avance retroactivo sobre una actividad Completada, sin reactivarla, cuando su fecha laboral es anterior a la fecha laboral de finalización. Ese avance se inserta en la secuencia histórica, conserva trazabilidad y no modifica el estado actual si existe un avance posterior que mantiene Completada. | M2, M3 | PA-20, PP-39 | Decisión de la versión 0.8 |
| RN-78 | No se permite planificar la continuación futura de una actividad Completada sin reactivarla previamente. | M2, M3 | PA-20, PP-39 | Ídem |
| RN-79 | No se admite insertar un avance de ejecución en un intervalo posterior a una finalización y anterior a una reactivación válida. Los avances retroactivos anteriores a una finalización pueden registrarse con auditoría, conservando la secuencia histórica. | M2, M3 | PA-20, PP-39 | Decisión de la versión 0.9 |
| RN-80 | Las correcciones auditadas de registros existentes se distinguen de la incorporación de nuevos avances de ejecución. | M2, M3 | PA-20, PP-39 | Ídem |
| RN-81 | Una actividad conserva su identidad y su propietario después de un traslado de la persona, y puede continuar en el equipo nuevo sin duplicarse. | M1, M3 | PA-21, PP-40 | Ídem |
| RN-82 | Las bitácoras y los avances conservan su equipo histórico correspondiente. El equipo nuevo no obtiene acceso automático al título, las descripciones, los motivos de bloqueo ni las bitácoras del equipo anterior. | M1, M4 | PA-21, PP-40 | Ídem |
| RN-83 | La persona propietaria conserva el acceso al historial completo de sus propias actividades. | M4 | PA-21, PP-40 | Ídem |
| RN-84 | El supervisor actual puede consultar una referencia mínima a una actividad pendiente de una persona que supervisa, sin recibir acceso a los detalles históricos restringidos. La referencia mínima no utiliza información histórica protegida para revelar detalles del equipo anterior. | M4 | PA-21, PP-40 | Ídem |
| RN-85 | El equipo anterior conserva la consulta de sus registros históricos autorizados, pero no supervisa como pendiente actual el trabajo de una persona trasladada. | M4 | PA-21, PP-40 | Ídem |
| RN-86 | Los informes aplican las mismas restricciones de autorización y alcance histórico que las consultas y las vistas de supervisión. | M5 | PA-21, PP-40 | Ídem |
| RN-87 | La visibilidad de una planificación futura se evalúa según la pertenencia aplicable a su fecha laboral, considerando los traslados registrados y conservando trazabilidad. | M2, M4 | PA-21, PP-40 | Ídem |
| RN-88 | El estado al corte de una actividad no se muestra a un equipo cuando deriva exclusivamente de registros protegidos de otro equipo. Si existen avances autorizados del equipo actual, se puede mostrar el estado al corte correspondiente sin revelar información histórica protegida. | M4, M5 | PA-22, PP-41 | Decisión de la versión 0.10 |
| RN-89 | La referencia mínima de una actividad se distingue claramente del acceso completo a su historial. | M4 | PA-22, PP-41 | Ídem |
| RN-90 | La consulta del propietario y los informes respetan la matriz de permisos en el tratamiento de la referencia mínima y del estado al corte. | M4, M5 | PA-22, PP-41 | Ídem |
| RN-91 | Toda corrección se valida contra la secuencia completa de avances. | M3 | PA-23, PP-42 | Ídem |
| RN-92 | No se permite que una corrección deje avances de ejecución posteriores a una finalización sin una reactivación válida. Eliminar o modificar una finalización también exige validar todas las demás reglas aplicables. | M3 | PA-23, PP-42 | Ídem |
| RN-93 | Una corrección válida queda auditada y recalcula el estado actual cuando corresponde. Una corrección inválida se rechaza sin modificar los datos. No se generan reactivaciones automáticas. | M3 | PA-23, PP-42 | Ídem |
| RN-94 | Las pertenencias de una persona forman períodos de actividad sin solapes ni huecos. No se admite un registro cuya fecha laboral no esté cubierta por una pertenencia de su propietaria, ni anterior a la primera pertenencia. | M1, M2 | Modelo de datos (PV-01) | Decisión de la versión 0.11 |
| RN-95 | Los traslados ordinarios tienen fecha efectiva posterior a la fecha actual en la zona horaria de la organización y no reasignan los registros existentes, incluidos los de la jornada actual. No hay corrección histórica ordinaria de pertenencias. | M1, M4 | Modelo de datos (PV-07, H-1), PA-25 | Ídem |
| RN-96 | La baja lógica comprende dos acciones independientes: la desactivación administrativa del acceso, que puede ser inmediata e impide desde ese momento toda operación autenticada, y la finalización de la pertenencia, con fecha efectiva posterior a la fecha actual. Ninguna elimina ni reasigna registros. La recuperación del acceso no reactiva un acceso desactivado; su reactivación administrativa requiere otra operación, pendiente de especificar. | M1 | Modelo de datos (PV-08, DD-05), PA-12 | Ídem |
| RN-97 | Una persona sin pertenencia vigente no opera, aunque su acceso no se haya desactivado. | M1 | Modelo de datos (PV-08) | Ídem |
| RN-98 | Un equipo puede estar incompleto durante su provisión. Un equipo con colaboradores tiene un supervisor válido en toda fecha: no se finaliza ni se traslada a un supervisor dejando a un equipo con colaboradores sin supervisor. La desactivación inmediata del acceso del único supervisor no se bloquea: el equipo queda identificado como pendiente de supervisión efectiva hasta asignar un reemplazo, sin transferir permisos de supervisión a otra persona y conservando la pertenencia histórica del supervisor. El supervisor con acceso desactivado no ejerce funciones de supervisión y la asignación de un reemplazo no es automática. | M1, M4 | Modelo de datos (PV-12, DD-04) | Ídem |
| RN-99 | Las operaciones administrativas de pertenencia programadas que todavía no han surtido efecto (traslados, cambios de rol, finalizaciones y altas futuras) pueden cancelarse o sustituirse mediante provisión controlada y auditoría. La auditoría conserva la operación original, su cancelación o sustitución, el autor y los valores necesarios para reconstruirla. Una operación que ya surtió efecto no se modifica retroactivamente con este procedimiento. Se respeta la integridad de las pertenencias: la validación impide solapes, huecos y equipos con colaboradores sin supervisor. | M1 | Modelo de datos (DD-02) | Ídem |
| RN-100 | Una actividad Completada se reactiva hacia Pendiente, En progreso o Bloqueada. Bloqueada exige motivo. La finalización anterior se conserva. | M3 | Modelo de datos (PV-04) | Ídem |
| RN-101 **[ENMENDADA v0.14]** | El título original de una actividad iniciada en otro equipo no se expone al equipo nuevo, aunque existan avances posteriores autorizados; la actividad se identifica con la referencia neutral «Actividad en continuidad» y un identificador opaco que no contiene información del equipo anterior. Los motivos de bloqueo de registros de otro equipo y el motivo de la marca de error no se exponen. Informes, vistas y consultas usan la misma política de autorización. La propietaria conserva el acceso a su historial completo. | M4, M5 | Modelo de datos (N8); PA-26 resuelto | Ídem; enmienda de la versión 0.14 |
| RN-102 | Toda operación de provisión administrativa queda auditada con un autor identificable y trazabilidad, sin credenciales ni códigos de acceso y sin crear un tercer rol funcional. El mecanismo concreto para identificar a quien opera la provisión está pendiente (PA-12). | M1, M3 | PA-12, PA-06 | Ídem |
| RN-103 | Cada operación genera una única entrada de auditoría con los valores anterior y nuevo necesarios para reconstruir el cambio, sin versionar los avances. Los ciclos de cierre y reapertura se reconstruyen desde la auditoría. | M3 | Modelo de datos (PV-05, PV-09, PV-11), PA-06 | Ídem |
| RN-104 | En el MVP la planificación original se conserva sin edición ordinaria y el título de una actividad no se edita en el flujo ordinario. Esto no elimina las correcciones auditadas que ya estén permitidas expresamente. | M2 | PP-43, PP-45 | Ídem |
| RN-105 | Cuando finaliza una pertenencia, las planificaciones futuras existentes se conservan con su identidad y trazabilidad, sin perder su relación con su propietaria ni con su actividad de origen. No se muestran como trabajo vigente ni pendiente de un equipo sin autorización, y se distinguen de la planificación vigente y del trabajo ejecutado. | M2, M4 | Modelo de datos (DD-03) | Ídem |
| RN-106 | La primera pertenencia de una persona comienza en una fecha igual o posterior a la fecha actual de la organización. No hay altas históricas excepcionales en el MVP. | M1 | Modelo de datos (OP-06), PA-25 | Ídem |
| RN-107 | Existe una única bitácora por persona y fecha laboral. Se abre de forma explícita o de forma implícita al registrar su primer contenido. Abrir una bitácora que ya existe devuelve la misma sin modificarla. Consultar una fecha sin bitácora no la crea. | M2 | Contratos API (D-01) | Decisión de la versión 0.13 |
| RN-108 | Modificar el contenido de una jornada cerrada exige reabrirla antes (RN-19). Registrar una ejecución nueva en una jornada abierta, incluida la de una actividad con avances en jornadas cerradas anteriores, no obliga a reabrir esas jornadas. | M3 | Contratos API (D-04) | Ídem |
| RN-109 | Las actividades marcadas como registradas por error no cuentan para cumplir las condiciones de cierre de una jornada. La comprobación considera todas las actividades válidas creadas o continuadas en esa fecha laboral, incluidas las iniciadas en jornadas anteriores. Si marcar una actividad hiciera perder a una jornada cerrada sus condiciones de cierre, la operación se rechaza sin modificar registros; si otras actividades válidas las conservan, la marca se permite sin reabrir la jornada. Marcar y revertir una marca se auditan y validan la integridad de los registros relacionados. | M3 | Contratos API (D-04b) | Ídem |
| RN-110 | La consulta funcional de la auditoría de una bitácora no incluye las entradas de la provisión administrativa. Su visibilidad y su retención se definen con PA-12 y PA-06. | M3 | Contratos API (D-11), PA-12, PA-06 | Ídem |
| RN-111 | Toda escritura efectiva de contenido sobre una jornada pasada, incluida la primera, genera una entrada de auditoría (RN-45). Abrir una bitácora vacía no es una escritura efectiva. | M3 | PA-06 (parcial), Contratos API (D-02) | Decisión de la versión 0.14 |
| RN-112 | El título de una actividad es obligatorio y debe contener algún carácter distinto de un espacio. | M2 | Contratos API (D-03) | Ídem |
| RN-113 | No se corrigen los avances de una actividad marcada como registrada por error mientras la marca esté vigente; primero debe revertirse la marca. | M3 | Contratos API (D-05) | Ídem |

Además están confirmados los cinco módulos (sección 4), el carácter de plataforma web, el propósito del producto (secciones 1 y 3), la limitación del alcance a esos módulos, las exclusiones PP-06 a PP-10 (sección 5), la clasificación de las métricas en medibles dentro del sistema y que requieren línea base externa (PP-30) la posibilidad de descomponer historias internas sin añadir funcionalidades y el stack tecnológico aprobado mediante ADR-001 (Flutter Web, FastAPI/Python y PostgreSQL, con monolito modular y autorización centralizada en el backend). El proveedor del servicio de IA, el mecanismo de autenticación y el despliegue no están decididos.

La definición de *jornada pasada* a efectos de RN-45 está confirmada en RN-72.

### 6.2 Propuestas

| ID | Propuesta | Módulos | Estado |
|---|---|---|---|
| PP-01 | Stack: Flutter Web (cliente), FastAPI/Python (servicio) y PostgreSQL (datos), con monolito modular y autorización centralizada en el backend. El proveedor del servicio de IA, el mecanismo de autenticación y el despliegue siguen pendientes. | Todos | Aprobada → ADR-001 (`docs/arquitectura/adr/ADR-001-stack-tecnologico.md`) |
| PP-02 | Dos tipos de persona usuaria: colaborador y supervisor. | M1, M4 | Aprobada → RN-11 |
| PP-03 | Definición de quién no es usuario: personas externas al equipo, como clientes. | Todos | `[PROPUESTO]` |
| PP-04 | Una bitácora por usuario y fecha laboral. | M2 | Aprobada → RN-16 |
| PP-05 | Cuatro estados de actividad. | M2, M3 | Aprobada → RN-08 |
| PP-06 a PP-10 | Exclusiones del MVP (sección 5). | — | Aprobadas |
| PP-11 | Cada afirmación de un informe de IA enlaza con los registros de origen. | M5 | `[PROPUESTO]` |
| PP-12 | Contenido de la auditoría. | M3 | Aprobada en lo compatible → RN-49, RN-50 (el motivo solo es obligatorio en la reapertura) |
| PP-13 | Estado histórico por avance y estado actual; tres fechas. | M2, M3 | Aprobada → RN-17, RN-18, RN-41, RN-42, RN-65 a RN-68 |
| PP-14 | Conservar la planificación original; identificar lo no planificado. | M2 | Aprobada → RN-20 |
| PP-15 | Condiciones de cierre. | M2, M3 | Aprobada → RN-21 |
| PP-16 | Cierre con cualquier estado, sin modificarlos. | M2, M3 | Aprobada → RN-22 |
| PP-17 | Vista del supervisor con cuatro estados, historial y período. | M4 | Aprobada → RN-13, RN-47, RN-48 |
| PP-18 | Cada persona modifica solo lo propio; el supervisor consulta sin modificar. | M1, M4 | Aprobada → RN-23 |
| PP-19 | El propietario reabre y corrige; auditoría incluida la retroactiva. | M3 | Aprobada → RN-19, RN-45, RN-50 |
| PP-20 | Motivo obligatorio para Bloqueada. | M2 | Aprobada → RN-24 |
| PP-21 | Consulta histórica por colaborador y rango de fechas. | M4 | Aprobada → RN-25 |
| PP-22 | Agregaciones diferenciadas, sin inventar y sin valoraciones. | M5 | Aprobada → RN-26 |
| PP-23 | La IA solo usa información autorizada y necesaria. | M5 | Aprobada → RN-30 |
| PP-24 | Retroactivos, jornadas futuras y zona horaria. | M2, M3 | Aprobada → RN-27, RN-44, RN-45, RN-46 |
| PP-25 | Provisión administrativa controlada. | M1 | Aprobada con precisiones → RN-33 a RN-35. Detalles del acceso inicial en PA-12 |
| PP-26 | Un equipo por persona y un supervisor por equipo, con trazabilidad; visibilidad por equipo en la fecha laboral. | M1, M4 | Aprobada → RN-28, RN-36, RN-37 |
| PP-27 | Informes con período, fecha de generación, permisos y regeneración; indicadores deterministas. | M5 | Aprobada → RN-29, RN-53 a RN-58 |
| PP-28 | El texto libre de las bitácoras es dato, no instrucción. | M5 | Aprobada → RN-31 |
| PP-29 | Continuar no genera otra actividad; el título no define la duplicación; selección explícita. | M3 | Aprobada → RN-32, RN-39 |
| PP-30 | Distinguir métricas medibles dentro del sistema de las que requieren línea base externa. | Todos | Aprobada la clasificación. Las métricas siguen siendo propuestas |
| PP-31 | Corrección lógica de actividades registradas por error, sin borrado físico. | M3 | Aprobada → RN-59, RN-60 |
| PP-32 | Cuando faltan registros suficientes, el informe lo indica explícitamente. | M5 | Aprobada → RN-57 |
| PP-33 | No se envían datos a un servicio externo de IA hasta decidir proveedor, datos y conservación. | M5 | `[PROPUESTO]` |
| PP-34 | Las credenciales de las personas nunca se muestran ni se registran en claro. | M1 | Aprobada → RN-64 |
| PP-35 | Un colaborador puede planificar, actualizar y cerrar su jornada sin consultar documentación. | M2 | `[PROPUESTO]` |
| PP-36 | Regla de orden y desempate de los avances. | M2, M3 | Aprobada con precisiones → RN-65 a RN-68 (precisadas en la versión 0.7) |
| PP-37 | Estado inicial de una actividad no planificada. | M2 | Aprobada → RN-69 |
| PP-38 | Reactivación y avances futuros (texto en 6.2.1). | M2, M3 | Aprobada con modificaciones → RN-73 a RN-76. Su punto 2 se sustituye por RN-76 |
| PP-39 | Avance retroactivo anterior a la finalización de una actividad y planificación de la continuación de una Completada. | M2, M3 | Aprobada con condiciones → RN-73, RN-77, RN-78 |
| PP-40 | Actividades entre equipos (texto en 6.2.1). | M4, M5 | Aprobada con precisiones → RN-81 a RN-87 y enmiendas de RN-47, RN-48 y RN-53 |
| PP-41 | Estado al corte de una actividad heredada de otro equipo. | M4 | Aprobada con precisiones → RN-88 a RN-90 y enmienda de RN-48 |
| PP-42 | Correcciones y secuencia de avances. | M3 | Aprobada con ajuste → RN-91 a RN-93 |
| PP-43 | Versionado de la planificación: modificar la planificación vigente conservando la versión inicial y su trazabilidad. | M2 | `[PROPUESTO]` |
| PP-44 | Reubicación auditada de un avance entre fechas laborales, validada contra la secuencia, las bitácoras y los permisos. | M3 | `[PROPUESTO]` |
| PP-45 | Edición ordinaria del título de una actividad. | M2, M3 | `[PROPUESTO]` |

#### 6.2.1 Referencia mínima y estado al corte

**PP-38** a **PP-42** están aprobadas y recogidas en RN-73 a RN-93. **PP-43** a **PP-45** siguen propuestas.

**Referencia mínima de una actividad iniciada en otro equipo (RN-84).** Clasificación de cada elemento por su seguridad:

| Elemento | Clasificación | Tratamiento |
|---|---|---|
| Propietario de la actividad | Seguro | Se muestra: es una persona que el supervisor supervisa. |
| Indicación de que la actividad se inició en otro equipo | Seguro | Se muestra, sin nombrar el equipo. |
| Estado actual (Pendiente, En progreso o Bloqueada) | Seguro con condición | Es un atributo de la actividad, no un detalle histórico. Se muestra sin motivo de bloqueo ni descripción asociada. |
| Fecha laboral del último avance | Requiere filtrado | Se muestra solo si ese avance pertenece al equipo del supervisor. |
| Estado al corte | Requiere filtrado | No se muestra cuando deriva exclusivamente de registros de otro equipo. Se muestra si existen avances autorizados del equipo actual que lo determinan (RN-88). |
| Título; descripciones de la planificación original y de los avances; motivos de bloqueo; resumen y contenido de bitácoras; nombre del equipo anterior; número y detalle de los avances; fecha de creación y planificación original | No seguro | No se muestran. |

La referencia mínima se distingue claramente del acceso completo al historial (RN-89). Cuando el propietario registra en el equipo nuevo un avance o una continuación planificada sobre la actividad, esos registros pertenecen al equipo nuevo y se muestran con el detalle propio de cada registro (su descripción y, en un avance, su motivo de bloqueo). Ese detalle no incluye el título original de la actividad, que no se expone al equipo nuevo (RN-101): la actividad se identifica con la referencia neutral «Actividad en continuidad» y un identificador opaco (RN-101).

**Implicación de seguridad de RN-87.** La planificación futura se evalúa según la pertenencia aplicable a su fecha laboral. Una planificación registrada en el equipo T para una fecha posterior a un traslado al equipo U pasa a pertenecer a U y deja de ser visible para T. El equipo nuevo llega así a ver una planificación redactada antes del traslado. Se acepta por RN-36 y la reevaluación queda trazada en el historial de pertenencias (RN-28).

**Interpretación de "eliminar" en RN-92.** No existe una operación de borrado de avances (RN-52, RN-59). "Eliminar una finalización" se interpreta como una corrección que la deja sin efecto, por ejemplo cambiando su estado.

### 6.3 Puntos abiertos

Todos los puntos abiertos surgieron del análisis funcional del producto. Un punto resuelto parcialmente sigue abierto en lo que no se ha resuelto.

#### 6.3.1 Resueltos

| ID | Decisión | Resuelto por |
|---|---|---|
| PA-01 | Registros retroactivos: se permiten, con trazabilidad y sin límite fijo de días inicialmente. | RN-14, RN-18 |
| PA-02 | Consulta entre equipos: los colaboradores consultan a compañeros del mismo equipo, solo en lectura. | RN-12, RN-36 |
| PA-03 | Cierre de jornada: manual, con condiciones definidas, con actividades en cualquier estado y sin modificar estados. | RN-10, RN-21, RN-22 |
| PA-05 | Vista del supervisor: criterio de inclusión, estado al corte y estado actual. | RN-13, RN-47, RN-48 |
| PA-07 | Continuidad de actividades: selección explícita, estados, orden de los avances, descripción, propietario único y estado inicial de lo no planificado. | RN-39 a RN-43, RN-65 a RN-71 |
| PA-08 | Informes: quién los genera, qué muestran, formato, edición, conservación, datos insuficientes y fallo del servicio. | RN-53 a RN-58 |
| PA-10 | Organización: el MVP se diseña para una organización con varios equipos. | RN-15 |
| PA-14 | Fecha laboral: zona horaria de la organización, sin festivos; las modificaciones de jornadas pasadas se auditan; definición de jornada pasada. | RN-44, RN-45, RN-72 |
| PA-15 | Jornadas futuras: solo planificación en estado Pendiente; no se registra ejecución ni se cierran. | RN-46 |
| PA-16 | Corrección de actividades registradas por error. | RN-59, RN-60 |
| PA-17 | Reactivación y avances futuros: reactivación explícita y auditada, en jornada no futura y respetando la secuencia; la planificación futura no es un avance y permite planificar la continuación de una actividad existente. | RN-73 a RN-76 |
| PA-18 | Visibilidad de un integrante incorporado después de la fecha de un registro: puede consultar los registros históricos de su equipo. | RN-36 |
| PA-19 | Informes con registros escasos: sin número mínimo; aviso de que no hay datos; informe con registros parciales solo con la información disponible. | RN-57 |
| PA-20 | Retroactivos y reactivación: se admite un avance retroactivo anterior a la finalización sin reactivar; los avances posteriores a la finalización requieren reactivación; no se planifica la continuación de una Completada sin reactivarla. | RN-73, RN-77, RN-78 |
| PA-21 | Actividades abiertas que cruzan un cambio de equipo: identidad y propietario, información histórica por equipo, estado actual como atributo de la actividad, referencia mínima segura, informes y planificación futura. | RN-81 a RN-87 |
| PA-22 | Estado al corte de una actividad heredada: no se muestra cuando deriva exclusivamente de registros protegidos de otro equipo; sí cuando existen avances autorizados del equipo actual; la referencia mínima se distingue del acceso completo. | RN-88 a RN-90 |
| PA-23 | Correcciones sobre la secuencia de avances: toda corrección se valida contra la secuencia completa; una corrección inválida se rechaza sin modificar datos; no hay reactivaciones automáticas. | RN-91 a RN-93 |
| PA-26 | Referencia neutral de las actividades heredadas: «Actividad en continuidad», con un identificador opaco que no contiene información del equipo anterior. | RN-101 |

PA-01 queda resuelto con la formulación "inicialmente": introducir un límite en el futuro sería una decisión nueva. Quedan fuera de PA-08 la propuesta PP-11 (enlace a los registros de origen) y la decisión sobre el proveedor de IA (PA-09).

#### 6.3.2 Resueltos parcialmente y abiertos

| ID | Tema | Resuelto | Pendiente | Afecta |
|---|---|---|---|---|
| PA-04 | Roles, permisos y pertenencia | RN-11, RN-23, RN-28, RN-33 a RN-38 | Cómo corregir una bitácora cuyo propietario no puede acceder (por baja o ausencia): hoy nadie puede hacerlo (RN-19, RN-23) | M1, M3 |
| PA-06 | Auditoría | RN-19, RN-45, RN-49 a RN-52, RN-103, RN-111 | Política de retención. Visibilidad y retención de las entradas de la provisión administrativa | M3 |
| PA-09 | Privacidad y servicio de IA | RN-30, RN-31 | Proveedor y modalidad; condiciones de conservación; tratamiento de datos; marco legal aplicable; qué se considera "necesario"; percepción de vigilancia | M4, M5 |
| PA-11 | Métricas de éxito | PP-30 (clasificación) | Objetivos numéricos y líneas base | Todos |
| PA-12 | Detalles del acceso inicial, de la recuperación y de la reactivación administrativa | RN-33 a RN-35, RN-96, RN-102 | Caducidad del acceso inicial; si la persona establece una credencial propia en el primer ingreso; medio de entrega; cómo se verifica la identidad de quien recupera el acceso; operación para reactivar un acceso desactivado administrativamente; cómo se identifica a quien opera la provisión | M1 |
| PA-13 | Objetivos no funcionales cuantitativos e idioma de la interfaz | — | Todo | Todos |
| PA-24 | Reincorporación de personas dadas de baja | RN-94, RN-96 (el modelo admite varios períodos de actividad) | Flujo de reincorporación; reactivación del acceso; tratamiento de la planificación conservada dentro del nuevo período | M1 |
| PA-25 | Ajustes históricos excepcionales de pertenencia y altas históricas | RN-95, RN-106 (no existen en el MVP) | Si se autorizan y con qué mecanismo extraordinario, validación y auditoría | M1 |

### 6.4 Dependencias entre decisiones

- PA-22 y PA-23 están resueltos (RN-88 a RN-93); ya no condicionan a otros puntos.
- PA-06 (retención) depende de PA-09 (marco legal) y de PA-13.
- PA-12 se resuelve junto con RNF-08 (RN-64) y define cómo se verifica la identidad al recuperar el acceso.
- PA-04 (propietario sin acceso) depende de PA-06: una corrección por un tercero exigiría ampliar la auditoría.
- PP-11 depende de PA-09 para la verificación del respaldo de los informes.
- PA-24 depende de PA-12 (reactivación del acceso) y de PA-25.

## 7. Riesgos de alcance

1. **M5 (IA):** dependencia externa, coste, privacidad y verificación del respaldo. Siguen abiertos el proveedor, la conservación y el marco legal (PA-09). El fallo del servicio está cubierto por RN-58.
2. **Visibilidad histórica entre equipos:** la regla funcional está cerrada (RN-81 a RN-90). El riesgo pasa al diseño: filtrar con cuidado referencias, estados al corte e informes de las personas trasladadas, y probarlo con la matriz de permisos.
3. **Propietario sin acceso:** si solo el propietario corrige su bitácora, la de quien causa baja no puede corregirse (PA-04).
4. **Provisión controlada:** M1 no incluye un panel de administración. La operación depende de procedimientos que deben ser operables y verificables (RN-34), y su forma concreta no está decidida.
5. **Registros retroactivos sin límite:** RN-14 favorece corregir olvidos pero debilita la fiabilidad si falla la trazabilidad. Se mitiga con RN-45.
6. **Visibilidad por equipo en la fecha laboral:** RN-36 añade complejidad a cualquier consulta o informe de una persona que cambió de equipo.
7. **Decisiones abiertas resueltas por defecto:** convertirlas en requisitos sin aprobación amplía el alcance.
8. **Percepción de vigilancia:** se mitiga con RN-13, RN-26, RN-48 y PP-09, pero depende de cómo se delimite lo que cada persona ve.
9. **Supervisión efectiva:** la desactivación inmediata del acceso del único supervisor deja al equipo sin supervisión hasta asignar un reemplazo (RN-98). Se acepta para no bloquear una revocación de acceso.

## 8. Siguiente paso

Este alcance se refleja en el PRD (`docs/producto/prd.md`), en las historias de usuario (`docs/backlog/`) y en el modelo de datos propuesto (`docs/modelo-datos/modelo-datos.md`).

## 9. Historial de cambios

| Versión | Cambios |
|---|---|
| 0.14 | Se confirman RN-111 (auditoría de la primera escritura efectiva sobre una jornada pasada), RN-112 (título obligatorio) y RN-113 (revertir la marca antes de corregir avances). Se enmiendan RN-25 (el rango de fechas es obligatorio y el colaborador, opcional) y RN-101 (referencia neutral «Actividad en continuidad»). Se resuelve PA-26 y se acota PA-06 a la retención y a la auditoría de la provisión. Textos anteriores: RN-25, «…permite filtrar por colaborador y rango de fechas laborales…»; RN-101, «…la actividad se identifica con una referencia neutral.» |
| 0.13 | Se confirman RN-107 (apertura única, explícita o implícita, de la bitácora), RN-108 (reapertura previa para modificar una jornada cerrada), RN-109 (las actividades marcadas por error no cuentan para el cierre) y RN-110 (auditoría de provisión separada de la consulta funcional). Se enmiendan RN-21 (actividad válida) y RN-48 (el corte es el último día del período consultado). Textos anteriores: RN-21, «…al menos una actividad creada o continuada en esa jornada…»; RN-48, «…el estado correspondiente al corte seleccionado y lo distingue…». |
| 0.12 | Se confirman con ajuste de redacción RN-99 (cancelación o sustitución de operaciones administrativas programadas, incluidas altas futuras y cambios de rol, sin efecto retroactivo y respetando la integridad de las pertenencias), RN-102 (autor identificable y trazabilidad; el mecanismo concreto sigue en PA-12) y RN-104 (no elimina las correcciones auditadas ya permitidas). RN-98 precisa que el supervisor con acceso desactivado no ejerce funciones de supervisión y que el reemplazo no es automático. No se crean reglas nuevas. Textos anteriores: RN-99, «Los traslados, cambios de rol, finalizaciones y altas con inicio futuro pueden cancelarse o sustituirse antes de su fecha efectiva…»; RN-102, «…La forma de identificar a quien opera la provisión está pendiente.» |
| 0.11 | Se confirman RN-94 a RN-106 a partir de las decisiones sobre el modelo de datos: períodos de actividad y cobertura de las pertenencias (RN-94), traslados con efecto futuro (RN-95), baja lógica en dos acciones y recuperación que no reactiva el acceso (RN-96, RN-97), equipos con supervisor y supervisión efectiva (RN-98), operaciones programadas cancelables (RN-99), estados de la reactivación (RN-100), referencia neutral y protección del título (RN-101), auditoría de la provisión y una entrada por operación (RN-102, RN-103), ausencia de edición ordinaria de la planificación original y del título (RN-104), planificación conservada (RN-105) y primera pertenencia (RN-106). Se enmiendan RN-28 y RN-38. Se reescribe el texto de la sección 6.2.1 que permitía leer «todo su detalle» como permiso para mostrar el título. Se añaden PP-43 a PP-45 (propuestas) y PA-24 a PA-26 (abiertos); se amplían PA-06 y PA-12. Textos anteriores: RN-28, «En el MVP cada persona pertenece a un único equipo y cada equipo tiene un único supervisor. Cuando una persona cambia de equipo se conserva la trazabilidad de sus pertenencias anteriores.»; RN-38, «La baja de una persona es lógica y no elimina su histórico.» |
| 0.10 | Se aprueban PP-41 (RN-88 a RN-90) y PP-42 (RN-91 a RN-93) y se resuelven PA-22 y PA-23. Se enmienda RN-48. PP-01 pasa a aprobada mediante ADR-001 (Flutter Web, FastAPI/Python y PostgreSQL, monolito modular, autorización centralizada en el backend); el proveedor de IA, el mecanismo de autenticación y el despliegue siguen pendientes. Se interpreta "eliminar una finalización" como una corrección que la deja sin efecto. Texto anterior de RN-48: "La vista del supervisor muestra el estado correspondiente al corte seleccionado y lo distingue del estado actual cuando son diferentes, solo para actividades cuyo propietario pertenece al equipo. No presenta como pendiente actual ni muestra el estado actual del trabajo de una persona que ya no pertenece al equipo (RN-85). No incorpora rankings ni evaluación de personas." |
| 0.9 | Se confirman RN-79 a RN-87: se admite como regla la prohibición de insertar un avance entre una finalización y una reactivación válida (antes CA-207), la distinción entre correcciones y nuevos avances, y los principios de PP-40 (identidad y propietario, equipo histórico, propietario con historial completo, referencia mínima, equipo anterior y pertenencia aplicable a una planificación futura). Se enmiendan RN-47, RN-48 y RN-53 para eliminar contradicciones con RN-85 y con la regla de informes. Se resuelve PA-21 y se añaden PA-22 y PA-23, con las propuestas PP-41 y PP-42. Se documenta la clasificación de seguridad de la referencia mínima. Texto anterior de RN-47: "La vista del supervisor incluye las actividades del equipo que fueron planificadas o tuvieron avances durante el período, y las no completadas que permanecen pendientes de atención al final del período. Incluye las actividades del propio supervisor." Texto anterior de RN-48: "La vista del supervisor muestra el estado correspondiente al corte seleccionado y lo distingue del estado actual cuando son diferentes. No incorpora rankings ni evaluación de personas." Texto anterior de RN-53: "Un informe individual lo genera su propietario o el supervisor autorizado de su equipo." |
| 0.8 | Se aprueba PP-39 con condiciones: RN-77 (avance retroactivo anterior a la finalización, sin reactivar) y RN-78 (no se planifica la continuación de una Completada sin reactivarla). Se enmiendan RN-73 (los avances que requieren reactivación son los posteriores a la finalización), RN-76 (excepción de RN-78), RN-21 (una continuación únicamente planificada no cuenta como actividad continuada) y RN-57 (el informe deja claro que no representa información que nunca fue registrada; sin umbrales ni porcentajes). Se resuelve PA-20. PP-40 se ajusta según las indicaciones y queda pendiente de aprobación final; PA-21 sigue abierto. Texto anterior de RN-21: "Una jornada puede cerrarse cuando contiene al menos una actividad creada o continuada en esa jornada y un resumen libre no vacío. «Continuada» significa que tiene al menos un avance con esa fecha laboral. «No vacío» significa que contiene algún carácter distinto de un espacio." Texto anterior de RN-57: "Si no existen registros autorizados en el período solicitado, el informe informa explícitamente de que no hay datos disponibles. Si existen registros parciales, el informe puede generarse únicamente con la información disponible, sin presentarla como si representara todo el trabajo realizado. No se establece un número mínimo de registros. No se inventan actividades, personas, fechas, avances ni bloqueos." Texto anterior de RN-73: "Una actividad Completada requiere una reactivación explícita y auditada para recibir nuevos avances de ejecución." Texto anterior de RN-76: "Se permite planificar la continuación de una actividad existente para una fecha futura, sin crear una actividad duplicada." |
| 0.7 | Se confirman RN-73 a RN-76 (reactivación explícita y auditada, reactivación en jornada no futura que respeta la secuencia, la planificación futura no modifica el estado ni es un avance, y planificación de la continuación de una actividad existente). Se resuelven PA-17, PA-18 (enmienda de RN-36) y PA-19 (enmienda de RN-57). Se precisan RN-46, RN-65, RN-66 y RN-68. PP-38 queda aprobada con modificaciones: su punto sobre avances Pendiente futuros se sustituye por RN-76. Se añaden PA-20 y PA-21 con las propuestas PP-39 y PP-40. Texto anterior de RN-36: "Un registro pertenece históricamente al equipo que tenía su propietario en la fecha laboral correspondiente. Los integrantes autorizados de ese equipo pueden consultar ese registro histórico, aunque posteriormente el propietario se haya trasladado a otro equipo. Esto no concede acceso a los registros correspondientes a otros equipos o períodos. La consulta y los informes respetan esta regla tanto en las interfaces como en los controles de autorización. El cambio de equipo no expone automáticamente todo el historial de la persona al equipo nuevo." Texto anterior de RN-46: "La planificación futura se admite únicamente en estado Pendiente. No se registra ejecución futura ni se cierran jornadas futuras." Texto anterior de RN-57: "Si faltan registros suficientes, el informe lo indica explícitamente sin inventar información." En RN-65 y RN-66 se sustituye "avances" por "avances de ejecución". De RN-68 se elimina la referencia a PA-17. |
| 0.6 | Se confirman RN-65 a RN-72 (orden de los avances, estado actual, correcciones, reactivación en la secuencia, estado inicial de lo no planificado, descripción obligatoria, la planificación no es un avance y definición de jornada pasada). Se enmiendan RN-12, RN-36 y RN-63 para armonizar la pertenencia histórica de los registros. Quedan aprobadas PP-36 (con precisiones) y PP-37, y se resuelve PA-07. Se añaden PA-17 (reactivación y avances futuros), PA-18 (visibilidad de un integrante incorporado después) y PA-19 (criterio de registros suficientes), y la propuesta PP-38. Texto anterior de RN-12: "Los colaboradores pueden consultar las bitácoras de compañeros del mismo equipo, únicamente en modo lectura. No pueden modificar registros ajenos." Texto anterior de RN-36: "La visibilidad histórica de un registro corresponde al equipo al que pertenecía su propietario en la fecha laboral del registro." Texto anterior de RN-63: "Un colaborador no puede consultar las bitácoras de personas de otros equipos." |
| 0.5 | Se confirman RN-33 a RN-64 a partir de las decisiones D-1 a D-8 y de las ratificaciones de RF-01, RF-16 y RF-24. Quedan aprobadas PP-12 (en lo compatible), PP-25, PP-31, PP-32 y PP-34, y completadas PP-24, PP-26 y PP-29. Se resuelven PA-05, PA-08, PA-14, PA-15 y PA-16. Se actualizan PA-04, PA-06, PA-07, PA-09 y PA-12. Se añaden PP-36 (regla de orden) y PP-37 (estado inicial de lo no planificado), formuladas para validar, y la definición derivada de jornada pasada. |
| 0.4 | Se confirman RN-16 a RN-32. Se enmiendan RN-10 y RN-13. Se alinea la redacción de RN-14 ("fecha real de registro"). Se añaden PP-25 reformulada, PP-31 y PP-32 a PP-35. Se resuelve PA-03. Se añaden PA-15 y PA-16. Texto anterior de RN-10: "El cierre de jornada es manual. Para cerrar debe existir al menos una actividad registrada y un resumen libre no vacío. Se permite cerrar con actividades Pendientes o Bloqueadas." Texto anterior de RN-13: "El supervisor tiene acceso a una vista consolidada de su equipo, con actividades pendientes, completadas y bloqueadas, y consulta histórica." |
| 0.3 | Se confirman RN-08 a RN-15. PP-02 y PP-05 quedan aprobadas. Se aprueban las exclusiones PP-06 a PP-10. PA-01, PA-02 y PA-10 quedan resueltos. Se añaden PA-13 y PA-14. |
| 0.2 | Se incorpora la planificación diaria como regla confirmada (RN-07) y se corrige PP-10. PP-05 pasa a cuatro estados propuestos. PA-07 incorpora la distinción entre actividad y registro de avance. |
| 0.1 | Versión inicial. |
