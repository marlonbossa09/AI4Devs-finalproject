# SMARTWORK — Registro del uso de IA en el desarrollo

Este documento registra cómo se usó la IA para construir SMARTWORK: qué herramientas y modelos, con qué contexto, con qué prompts representativos y, sobre todo, **qué decisiones humanas aprobaron o corrigieron lo que propuso la IA**. Solo contiene lo que ocurrió realmente; lo que no puede verificarse desde este repositorio se marca como pendiente. No se adjunta la conversación completa: se conserva en el historial local de la herramienta.

## Índice

0. [Herramientas, modelos y contexto](#0-herramientas-modelos-y-contexto)
1. [Descripción general del producto](#1-descripción-general-del-producto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Especificación de la API](#4-especificación-de-la-api)
5. [Historias de usuario](#5-historias-de-usuario)
6. [Tickets de trabajo](#6-tickets-de-trabajo)
7. [Pull requests](#7-pull-requests)
8. [Decisiones humanas y errores de la IA](#8-decisiones-humanas-y-errores-de-la-ia)
9. [Uso de IA por fase: realizado y planificado](#9-uso-de-ia-por-fase-realizado-y-planificado)
10. [Entrega 2: implementación asistida por IA](#10-entrega-2-implementación-asistida-por-ia)

---

## 0. Herramientas, modelos y contexto

### Fuentes y herramientas de apoyo

- **Material del curso AI4Devs:** base de referencia para aplicar las metodologías y los conocimientos utilizados en SMARTWORK (entre ellos el desarrollo guiado por especificación). Es una fuente de conocimiento; no es autor de ningún documento del producto.
- **Claude Code:** herramienta **principal**. Se usó directamente sobre el repositorio para estructurar la documentación y realizar las verificaciones documentales. Todo el contenido de `docs/`, `readme.md` y este registro se produjo con ella y fue revisado y aprobado por la persona responsable.
- **ChatGPT:** herramienta **complementaria**, usada para analizar propuestas, contrastar decisiones y revisar aspectos del proyecto. No es la herramienta principal ni se le atribuye la autoría del proyecto ni del material del curso. Su uso se declara aquí tal como fue; **no se han conservado el modelo ni los prompts concretos**, por lo que no se reproducen ni se inventan.

### Convención de este registro

Los prompts de las secciones 1 a 6 y 10 son **resúmenes** del mensaje original, no transcripciones literales; así se indica en cada uno («resumen fiel»). Ninguno es una transcripción literal. Los mensajes completos y las respuestas están en el historial local de Claude Code, que no forma parte del repositorio.

### Herramientas y modelos

| Herramienta | Modelo | Uso real |
|---|---|---|
| **Claude Code** (extensión para VS Code) | `claude-sonnet-5-5` (la inmensa mayoría de los mensajes de la sesión) y `claude-opus-5-5` (4 mensajes; la transcripción no registra para qué tarea) | Entrega 1: alcance, requisitos, historias, arquitectura, modelo de datos, contratos de la API, tickets, README y este registro. Entrega 2: código del backend y del frontend, migraciones, pruebas y actualización del README |
| Agentes de lectura web de Claude Code y búsqueda web | Los de la propia herramienta | Contrastar datos externos (precios, retención y regiones del proveedor de IA candidato, valores de seguridad de NIST y OWASP) para los ADR |
| Conector de Google Drive de Claude | — | Búsqueda de documentación de apoyo; no aportó contenido utilizable y no se incorporó nada al repositorio |
| Scripts de Python escritos por la IA, ejecutados en la sesión | — | Verificar la documentación (formato de los criterios, trazabilidad, coherencia entre documentos). No forman parte del repositorio |
| Extensión **Claude en Chrome**, dentro de la misma sesión | `claude-sonnet-5-5` | Entrega 2: validar en un Chrome real las cookies, el CSRF, el origen y el flujo completo, y capturar la evidencia de `docs/evidencia/` |
| **ChatGPT** (complementaria) | No registrado | Análisis de propuestas, contraste de decisiones y revisión de aspectos del proyecto. Sin registro de modelo ni de prompts; no se reconstruyen |

### Contexto avanzado

- **`CLAUDE.md`** ([CLAUDE.md](CLAUDE.md)): reglas de trabajo cargadas en cada sesión. Fijan la metodología (primero el alcance, luego el PRD, las historias, el backlog y la arquitectura), los estados de toda decisión (`[CONFIRMADO]`, `[PROPUESTO]`, `[ABIERTO]`, `[SUPUESTO]`), la prohibición de implementar lo no especificado, la aprobación previa para cambiar el alcance, la trazabilidad y las reglas de la IA del producto (nada inventado, fallo explícito). Se creó con autorización expresa de la persona responsable.
- **Modo de planificación** de Claude Code: la IA presentó un plan antes de escribir cualquier archivo y la persona responsable lo aprobó o rechazó.
- **Aprobación por pasos:** cada fase terminó con una revisión humana antes de pasar a la siguiente; ninguna decisión se convirtió en requisito sin aprobación expresa.
- **Restricciones repetidas en cada petición:** sin código, sin dependencias, sin commits ni pushes, y la rama de trabajo no se cambia.
- **Entrega 2:** los contratos, el modelo de datos y los tickets de la Entrega 1 sirvieron de especificación; se ejecutaron las pruebas de cada bloque antes de pasar al siguiente y se informó al terminar cada uno.
- **Identificadores y plantillas propios** (`RN`, `RF`, `HU`, `CA`, `PP`, `PA`) y scripts de verificación que la IA debía ejecutar antes de afirmar que algo cumplía.

---

## 1. Descripción general del producto

### Prompt 1 — Inicio con desarrollo guiado por especificación (SDD)

- **Fase:** descubrimiento y alcance · **Herramienta:** Claude Code (modo de planificación)
- **Prompt (resumen fiel del mensaje original):** actuar como arquitecto senior, analista funcional y especialista en SDD. SMARTWORK es el proyecto; el MVP tiene cinco funcionalidades obligatorias; hay decisiones funcionales confirmadas y otras abiertas (límites de los registros retroactivos, alcance de la consulta entre equipos, condiciones para cerrar una jornada) que **no deben convertirse en requisitos**; el stack es una propuesta (Flutter Web, FastAPI, PostgreSQL y un servicio de IA); solo análisis y planificación, sin código, sin dependencias, sin modificar archivos y sin commits; presentar primero un diagnóstico y un plan; el primer objetivo es construir y validar el PRD.
- **Resultado:** un diagnóstico del repositorio y un plan de trabajo por fases.
- **Decisión humana:** se **rechazó el primer plan** porque trataba el proyecto como un ejercicio; se exigió que SMARTWORK fuera un producto profesional e independiente y que su documentación no hiciera referencia a su contexto de elaboración. Tras un segundo plan se aprobaron la metodología, los identificadores y el español como idioma, y se autorizó únicamente un `CLAUDE.md` mínimo.
- **Después:** el alcance (`docs/producto/alcance-mvp.md`) y el PRD se escribieron en pasos, con una **revisión adversarial** de ambos (doce aspectos prioritarios, sin modificar archivos) que alimentó una propuesta consolidada de resoluciones que la persona responsable fue aprobando una a una.

---

## 2. Arquitectura del sistema

### Prompt 2 — Comparación de stack, ADR y arquitectura lógica

- **Fase:** arquitectura · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** comparar opciones de stack, redactar un ADR **propuesto**, describir la arquitectura lógica de los cinco módulos con diagramas de componentes y flujos, y listar riesgos; sin tablas, sin entidad-relación y sin endpoints; dejar los puntos abiertos del mecanismo de acceso y del proveedor de IA **sin elegir ninguno por defecto**.
- **Resultado:** `ADR-001`, `arquitectura-general.md` con seis diagramas, riesgos y decisiones técnicas.
- **Decisión humana:** la persona responsable informó de su experiencia previa (Flutter, FastAPI, PostgreSQL, API REST, Git y Docker) y pidió que el ADR la usara como fundamento sin suponer lo mismo de todo el equipo; aprobó el stack, el monolito modular y la autorización centralizada. Más tarde, AWS Bedrock se mantuvo solo como candidato.
- **Continuación:** [ADR-002](docs/arquitectura/adr/ADR-002-autenticacion-y-acceso.md) (autenticación) y [ADR-003](docs/arquitectura/adr/ADR-003-integracion-de-ia.md) (IA). Para ambos la IA contrastó datos externos con agentes de lectura web y marcó explícitamente lo que **no pudo verificar** (por ejemplo, el precio de Bedrock y las cifras de OWASP sobre sesiones). La persona responsable aprobó la arquitectura técnica de referencia de ADR-002 y exigió no tratar el acceso al servidor como autorización administrativa.

---

## 3. Modelo de datos

El modelo de datos y los contratos de la API se elaboraron en un mismo flujo de trabajo; el **Prompt 3** de la sección siguiente cubre ambos.

## 4. Especificación de la API

### Prompt 3 — Flujo de decisiones por matriz (modelo de datos y contratos)

- **Fase:** modelo de datos y contratos · **Herramienta:** Claude Code
- **Prompt (resumen fiel), modelo:** presentar la matriz completa de decisiones PV-01 a PV-12, sin omitir ninguna, con descripción, opciones, recomendación, consecuencia sobre entidades, relaciones y restricciones, si afecta a seguridad, integridad o alcance, y si debe decidirse antes de aprobar el modelo; «no inventes aprobaciones».
- **Prompt (resumen fiel), contratos:** especificar M2, M3 y M4 desde el catálogo de operaciones, con propósito, reglas, requisitos e historias, método y ruta, entrada, respuesta, validaciones, autorización, errores, auditoría y criterios vinculados; verificar la diferencia entre consultar y crear una bitácora, la corrección según el estado de la jornada, la protección entre equipos y las respuestas ante registros inexistentes; «no inventes reglas de negocio para completar un contrato».
- **Resultado:** [modelo de datos](docs/modelo-datos/modelo-datos.md) con nueve entidades y 39 reglas de integridad, y [35 contratos de la API](docs/api/indice.md). La IA comprobó la trazabilidad con scripts.
- **Decisiones humanas que corrigieron a la IA:**
  - Se aprobó una parte de la matriz y se **rechazaron** el versionado de la planificación, la reubicación de avances y la edición del título.
  - La IA proponía que una baja solo pudiera tener efecto en una fecha futura; la persona responsable lo **rechazó** y exigió separar la desactivación inmediata del acceso de la finalización de la pertenencia.
  - La IA proponía reabrir siempre la jornada para marcar una actividad por error; la persona responsable lo **rechazó** y pidió distinguir una corrección de contenido de un cambio de validez, con una comprobación de integridad del cierre.
  - La persona responsable fijó el corte de la vista de supervisión en el último día del período, en lugar de un segundo parámetro.

---

## 5. Historias de usuario

### Prompt 4 — Historias con criterios verificables y validación

- **Fase:** historias y criterios · **Herramienta:** Claude Code más un script de verificación
- **Prompt (resumen fiel):** crear las historias en `docs/backlog/`, organizadas por módulo, con regla, requisito, dependencias, estado de preparación y criterios DADO / CUANDO / ENTONCES observables, sin rutas de API ni nombres de campos; y validar al final la trazabilidad, los identificadores únicos, las historias incompletas, el inventario y cuántas están listas para el diseño técnico.
- **Resultado:** 33 historias, hoy con 301 criterios y un índice con su estado.
- **Decisión humana y error de la IA:** la IA informó de que todos los criterios cumplían el formato, pero su verificador solo buscaba algunas palabras y no comprobaba que cada criterio tuviera su `CUANDO`. La persona responsable pidió una verificación estricta; la IA reescribió el verificador, detectó 29 criterios de 17 historias que no cumplían y, con autorización expresa, los normalizó solo en su forma. Desde entonces el verificador exige una sola secuencia DADO / CUANDO / ENTONCES con contenido en cada parte.
- **Otras decisiones humanas:** se aprobaron las reglas de continuidad, reactivación y planificación futura con precisiones; **no se aprobó tal como estaba escrita** la propuesta de visibilidad entre equipos tras un traslado, que se reescribió.

---

## 6. Tickets de trabajo

### Prompt 5 — Tickets documentales y README a partir de la especificación

- **Fase:** tickets y documentación · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** elaborar tickets documentales para las cinco funcionalidades, organizados por backend, frontend y base de datos, con identificador, objetivo, historia y criterios, descripción técnica, dependencias, prioridad y condiciones verificables de terminado; sin convertir cada criterio en un ticket y priorizando un flujo principal de extremo a extremo; completar el `readme.md` con enlaces relativos en lugar de copiar los requisitos; y registrar el uso real de la IA sin inventar información.
- **Resultado:** [34 tickets](docs/backlog/tickets/indice.md), el [README](readme.md) y este registro. Los tickets y el README se generaron en parte con scripts que leen los documentos reales para evitar discrepancias, y se verificaron los enlaces y las referencias.
- **Decisión humana:** se limitó la ampliación del diseño («dejemos de ampliar innecesariamente el diseño») y se priorizó completar los entregables.

---

## 7. Pull Requests

Todavía no hay pull requests. El trabajo de la Entrega 1 está en `feature/entrega-1-eq` y el de la Entrega 2 en `feature/entrega-2-eq`, creada desde la anterior sin modificarla. Ningún commit ni push se hizo sin autorización expresa de la persona responsable.

---

## 8. Decisiones humanas y errores de la IA

**Decisiones humanas que aprobaron o corrigieron a la IA**

| Decisión | Efecto |
|---|---|
| Rechazo del primer plan | SMARTWORK pasó a documentarse como producto independiente |
| Aprobación de cada propuesta (`PP-xx`) una a una, con precisiones | Ninguna decisión se convirtió en requisito por inferencia |
| No aprobar la visibilidad entre equipos tal como estaba escrita | Se reescribió con una referencia mínima segura |
| Rechazo de las bajas solo futuras y de la reapertura obligatoria al marcar | Dos modelos de comportamiento más precisos |
| No aprobar versionado de planificación, reubicación de avances ni edición del título | Quedaron fuera del MVP |
| Exigir que el acceso al servidor no equivalga a autorización administrativa | Se rediseñó la autorización de la persona operadora |
| Mantener ADR-002 y ADR-003 como propuestos hasta resolver lo operativo | Sin mecanismo ni proveedor elegidos por defecto |

**Decisiones humanas de la Entrega 2**

| Decisión | Efecto |
|---|---|
| Elegir la autenticación real y mínima (opción A) y prohibir cualquier suplantación o cabecera para saltarse el acceso | Sesiones reales y revocables con usuarios ficticios; ningún código de elusión en el repositorio |
| Aprobar M1-01c, la idempotencia mínima y la auditoría de jornadas pasadas | Entraron en el alcance con su justificación; sin ellas el contrato de planificación no se cumplía |
| Fijar la arquitectura del frontend (Riverpod, Dio, `.g.dart` versionados, nombres en inglés, sin Freezed ni capa de casos de uso) | Estructura limpia por funcionalidad, tomada de otro proyecto de la persona responsable |
| No compartir contraseñas administrativas de PostgreSQL | La IA creó un clúster de desarrollo propio y sin privilegios, y versionó un script SQL sin secretos |
| Retirar solo el archivo accidental sin seguimiento y no hacer limpiezas generales | Árbol limpio sin tocar nada más |
| Mantener la identidad de git configurada sin atribuir los commits a otra persona | Autoría tal cual consta en la configuración |

**Errores de la IA, detectados y corregidos**

- Afirmó que todos los criterios cumplían el formato sin comprobar el `CUANDO` (sección 5).
- Sus propios scripts de verificación tuvieron fallos de implementación (cadenas mal construidas, llaves sin escapar en plantillas, referencias de decisión combinadas en una celda) que se detectaron al ejecutarlos y se corrigieron antes de dar nada por válido.
- No pudo verificar el precio de Bedrock ni algunas cifras de OWASP; lo declaró en los ADR en lugar de estimarlo.
- **Entrega 2.** Propuso instalar la última versión de Riverpod, incompatible con Flutter 3.35.3 y Dart 3.9.2; el resolvedor de dependencias lo detectó y se fijó la familia 3.0.x con su generador.
- **Entrega 2.** Varias pruebas propias estaban mal escritas (un bloque vacío que esperaba un error, una búsqueda de texto que también encontraba el contenido de un campo, dos toques sin refrescar la pantalla). Fallaron al ejecutarse y se corrigieron; no se debilitó ninguna comprobación de la aplicación.
- **Entrega 2.** Al cancelar una tarea en segundo plano se cayó el clúster de PostgreSQL de desarrollo que colgaba de ella. Se retiró un proceso huérfano suyo (sin tocar el servicio de PostgreSQL del equipo) y se relanzó desacoplado de la sesión.
- **Entrega 2.** Un fallo aparente de inicio de sesión en el navegador no era de la aplicación: Chrome autocompletaba la contraseña guardada y la automatización escribía detrás. Se diagnosticó leyendo el campo (48 caracteres en lugar de 24) y comprobando que `curl` y `fetch` entraban.
- **Entrega 2.** Para dar por buenas las pruebas, se rompió el código a propósito en tres puntos y se comprobó que fallaban; no se aceptó que pasaran a la primera sin esa comprobación.

---

## 9. Uso de IA por fase: realizado y planificado

| Fase del ciclo de desarrollo | Estado | Uso de la IA |
|---|---|---|
| Descubrimiento y alcance | **Realizado** | Planes, alcance, registro de decisiones |
| Requisitos | **Realizado** | PRD, revisión adversarial, trazabilidad |
| Historias y criterios | **Realizado** | 33 historias, 301 criterios, verificación automática |
| Arquitectura | **Realizado** | ADR, diagramas, riesgos, contraste de datos externos |
| Modelo de datos y contratos | **Realizado** | Modelo, 35 contratos, comprobaciones de coherencia |
| Tickets y documentación | **Realizado** | 34 tickets, README, este registro |
| Implementación | **Realizado en parte (Entrega 2)** | Claude Code con los tickets, los contratos y los criterios como contexto: backend, migraciones, semilla, frontend y su integración; solo el subconjunto del primer recorrido. El resto, planificado |
| Pruebas | **Realizado en parte (Entrega 2)** | 242 pruebas de backend sobre PostgreSQL real (incluidas 24 de aislamiento, 12 de salud y 28 de creación de cuentas) y 64 de frontend, comprobación del código con fallos provocados y verificación en Chrome real. Planificado: matriz de permisos completa, pruebas de seguridad de ADR-002 y prueba automatizada de la interfaz |
| Revisión de código | **Planificado** | Revisión asistida de cada pull request |
| Producto (M5) | **Planificado, condicionado** | Informes con un servicio de IA, solo tras decidir proveedor, retención, región y marco legal (ADR-003) |

---

## 10. Entrega 2: implementación asistida por IA

### Prompt 6 — Plan de implementación del primer recorrido

- **Fase:** planificación de la implementación · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** la Entrega 2 no es implementar todo SMARTWORK, sino construir los andamios de Flutter Web, FastAPI y PostgreSQL, conectarlos y dejar al menos una funcionalidad real de extremo a extremo (abrir o consultar la bitácora, registrar una actividad planificada para una fecha válida, guardarla en PostgreSQL y verla de nuevo en Flutter), usando el modelo y los contratos ya documentados. Primera tarea solo de análisis: verificar la Entrega 1, crear la rama, revisar los tickets P0, identificar las decisiones de autenticación y autorización, proponer un mecanismo de prueba local seguro que no pueda usarse fuera de desarrollo, definir la estructura, los endpoints, las migraciones y las pruebas, y ordenar la ejecución. Sin código, sin dependencias, sin migraciones, sin commits.
- **Resultado:** un plan concreto con dos opciones de autenticación (una real y mínima, otra solo para desarrollo con sus salvaguardas), la estructura de carpetas, las migraciones, las pruebas mínimas y ocho decisiones pendientes de la persona responsable.
- **Decisión humana:** se eligió la autenticación real y se prohibió expresamente toda suplantación de identidad (sección 8). Además, la IA detectó que el árbol no estaba limpio por un archivo accidental y lo notificó en lugar de ignorarlo.

### Prompt 7 — Arquitectura del frontend a partir de una referencia

- **Fase:** arquitectura del cliente · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** el frontend debe tener una arquitectura limpia como la de otro proyecto de la persona responsable, mostrada con una captura de su árbol de carpetas (`config`, `core`, `features` con `data`, `domain` y `presentation`, y proveedores con código generado).
- **Resultado:** una estructura por funcionalidad (`auth` y `logbook`) con Riverpod y Dio, y el aviso de que solo se veía la captura, no el código del otro proyecto, por lo que se deducían Riverpod con generación de código y Dio.
- **Decisión humana:** se confirmó la deducción y se fijaron los nombres en inglés, los archivos generados versionados, sin Freezed y sin capa de casos de uso. La IA comprobó la compatibilidad de versiones con el Flutter instalado antes de aceptar la lista (sección 8).

### Prompt 8 — Ejecución incremental por tickets con pruebas

- **Fase:** implementación y pruebas · **Herramienta:** Claude Code, con la extensión de Chrome para la validación en navegador
- **Prompt (resumen fiel):** con las decisiones aprobadas, empezar la implementación por tickets en este orden: estructura y configuración, backend y conexión a PostgreSQL, migraciones y datos ficticios, autenticación mínima, contratos de bitácoras y planificación, frontend con Riverpod y Dio, integración real, pruebas automatizadas y comprobación del flujo completo, y actualización del README y de este registro. Ejecutar las pruebas de cada ticket antes de continuar, informar al terminar cada bloque, validar las cookies seguras, el CSRF, el origen y las sesiones en el entorno local antes de dar por completada la autenticación, y no hacer commits ni pushes sin autorización.
- **Resultado:** los bloques se implementaron en ese orden, con las pruebas de cada uno ejecutadas antes de seguir (cifras y alcance en el [README](readme.md#26-tests)). Se declararon como límites lo no implementado, las decisiones técnicas que los contratos no cubrían y la ausencia de una prueba automatizada de la interfaz en un navegador.
- **Decisión humana:** se aprobaron las decisiones técnicas listadas en el README y se mantuvo sin publicar hasta su autorización expresa.

### Prompt 9 — Rediseño visual a partir de un prototipo HTML

- **Fase:** diseño de la interfaz · **Herramienta:** Claude Code, con la extensión de Chrome para verificar
- **Prompt (resumen fiel):** mejorar por completo el diseño del frontend a partir de un prototipo HTML que se entregaría después; mantener la arquitectura por funcionalidades con Riverpod y Dio; usar nombres sencillos en inglés (`user`, `password`, `name`, `status`, `date`, `activity`, `logbook`, `planning`) y conservar los contratos JSON con mapeos; usar solo variables de entorno locales para las credenciales; comprobar el estado de la base `smartwork_app` local antes de cambiar nada y no usar automáticamente el clúster del puerto 5433; no borrar bases, roles ni datos. Después se aprobó el prototipo: reproducirlo con fidelidad y responsive, sin datos simulados y sin funcionalidades que no existen.
- **Resultado:** diagnóstico del servidor del 5432, rediseño completo con componentes reutilizables, 64 pruebas de Flutter y verificación en Chrome en escritorio, tableta y móvil con datos reales.
- **Decisión humana:** se eligió usar `smartwork_app` del 5432 y se facilitó la clave de administrador en el chat. La IA la usó solo para comprobaciones de lectura y para crear dos roles de privilegios mínimos, sin ejecutar nunca la aplicación como superusuario, y borró el archivo temporal donde la guardó.
- **Errores de la IA, corregidos:** (1) dos pantallas con un `Container` con color y decoración a la vez, y un formulario que se desbordaba 144 px en móvil: los detectaron las pruebas de widgets una vez cargada la fuente real, porque con la fuente de prueba por defecto el texto sale el doble de ancho; (2) al verificar en el navegador se veía todavía la versión antigua por la caché del service worker de Flutter, que hubo que eliminar; (3) la automatización escribió una «a» de más con Ctrl+A y la clave salió mal, lo que no era un fallo de la aplicación; (4) el diagnóstico inicial usó el clúster alternativo del 5433 al ejecutar las pruebas de la semilla, contra la indicación de no usarlo automáticamente; solo contiene la base de pruebas, pero se declara aquí.

### Prompt 10 — Cierre de la validación técnica antes de publicar

- **Fase:** validación y cierre · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** conservar el rediseño aprobado; trabajar con `smartwork_app` en el PostgreSQL del puerto 5432 y no usar el clúster del 5433; antes de tocar `listen_addresses`, `pg_hba.conf`, credenciales, roles o el cortafuegos, presentar el impacto y los pasos de respaldo y reversión, sin hacer todavía cambios globales; antes de ejecutar la suite completa del backend, verificar que la base de pruebas sea exactamente `smartwork_test`, que no se use `smartwork_app` en pruebas destructivas y que ninguna otra base del servicio pueda resultar afectada; ejecutar también `flutter analyze` y las 64 pruebas de Flutter; no incluir el prototipo HTML en el commit; comprobar que no haya secretos preparados para Git ni valores reales en `.env.example`; revisar que README y este registro reflejen el estado real; no ampliar el alcance; no hacer commit ni push.
- **Resultado:** diagnóstico de solo lectura del servicio compartido, creación de la base `smartwork_test` (lo único que se creó en el servicio), validación de aislamiento endurecida y probada, suite completa del backend y de Flutter, y documentos al día (cifras en el [README](readme.md#26-tests)).
- **Decisión humana:** limitar los cambios al servicio compartido a lo imprescindible y exigir el impacto y la reversión por escrito antes de cualquier ajuste global.
- **Errores de la IA, corregidos:** (1) la comprobación de aislamiento que había escrito aceptaba cualquier base que terminara en `_test`, es decir, `otra_test` en cualquier servidor local; se sustituyó por una validación exacta del nombre, el servidor y el puerto, comprobada también contra lo que responde PostgreSQL; (2) afirmó que el servicio del 5432 estaba «accesible desde toda la red» por ver `listen_addresses=*`, sin haber leído `pg_hba.conf`, que solo admite conexiones desde `127.0.0.1` y `::1`; lo corrigió al leerlo; (3) las pruebas se apuntaban por defecto a un servidor que el responsable había descartado; ahora se rechaza el puerto 5433 y `.env` ya no lo menciona.

### Prompt 11 — Comprobaciones de salud y cuentas locales de prueba

- **Fase:** operación y datos de prueba · **Herramienta:** Claude Code
- **Prompt (resumen fiel), primera parte:** implementar `GET /health` y `GET /health/ready`: el primero responde 200 mientras el proceso de FastAPI funcione; el segundo hace una consulta ligera a PostgreSQL y responde 503 si no está disponible; JSON, sin credenciales, cadenas de conexión ni datos de personas, sin autenticación y sin depender del negocio; con pruebas de los casos sano y de fallo; documentados en el README y diseñados para poder usarse como comprobaciones en AWS ECS.
- **Prompt (resumen fiel), segunda parte:** crear dos cuentas locales en `smartwork_app` (una supervisora y un colaborador) en el mismo equipo de prueba, con una contraseña inicial entregada por un canal local seguro y sin escribirla en archivos versionados, scripts, pruebas, documentación ni registros; antes de crear, confirmar que la conexión es exactamente `smartwork_app` en el puerto 5432 y revisar las cuentas existentes para no duplicar; guardar con Argon2id; respetar pertenencias y roles; no crear un tercer rol de administrador; hacerlo idempotente; detenerse si hiciera falta un permiso especial. Después, una vez entregada la contraseña: crear las cuentas, comprobar inicio y cierre de sesión, que el colaborador crea y consulta actividades, que ambos están en el equipo con sus roles, que las cuentas demo no cambiaron, que la salud responde, ejecutar las pruebas, actualizar este registro y verificar que no haya secretos en Git, sin modificar la política de contraseñas.
- **Resultado de la salud:** implementada y verificada con servidores reales: 200 y 200 contra `smartwork_app`; con la base inalcanzable, 200 y 503 en 3,2 s, sin filtrar nada. 12 pruebas, incluida una con un servidor inalcanzable real. Para que una base caída responda 503 en vez de colgarse se añadió un tiempo máximo de conexión configurable.
- **Resultado de las cuentas:** el mecanismo (`scripts/crear_cuentas.py`) es genérico: los datos de las cuentas se leen de un archivo local ignorado por Git, la contraseña de un archivo local, una variable de entorno o una petición sin eco, y nunca de la especificación; antes de escribir confirma con el propio servidor la base y el puerto, que el servidor es local y que el rol no es administrador. El primer intento falló: la contraseña entregada tenía menos de los 15 caracteres que exige ADR-002 y el script la rechazó sin escribir nada. La persona responsable decidió crear las cuentas con esa contraseña, así que se añadió una excepción **explícita y por ejecución** (`--permitir-contrasena-corta`, suelo de 8 caracteres) sin cambiar el mínimo por defecto ni lo que la aplicación exige al iniciar sesión. Con ella se crearon en `smartwork_app` (puerto 5432, confirmado por el servidor) las dos cuentas, en un «Equipo de prueba» nuevo: una con rol supervisor y otra con rol colaborador. Una segunda ejecución no cambió nada.
- **Verificación sobre un servidor real:** ambas cuentas inician y cierran sesión (la sesión queda revocada en el servidor); el colaborador abre su bitácora, crea una actividad pendiente y la consulta, y un reintento no la duplica; el supervisor no ve la bitácora del colaborador (404 indistinguible de inexistente); sin sesión, sin token CSRF o desde otro origen se rechaza; no existe ninguna ruta de administración; las pertenencias están vigentes con un único supervisor y ningún rol distinto de colaborador y supervisor; las contraseñas están con Argon2id y no aparecen en claro en ninguna tabla; la auditoría de provisión no contiene credenciales ni identificadores de acceso; `/health` y `/health/ready` responden 200. Las tres cuentas demo conservan exactamente la misma huella (contraseñas, nombres, roles, equipo y fechas). La verificación dejó una actividad de verificación en la bitácora del colaborador.
- **Decisión humana:** la contraseña se entrega por un archivo local ignorado por Git y no se escribe en ningún archivo versionado; ante la contraseña corta, la persona responsable optó primero por una excepción explícita (superada después por la política de 10 caracteres: ver Prompt 12).
- **Errores de la IA, corregidos:** (1) la primera versión de las pruebas del script no ejercía la confirmación que hace el propio servidor, porque la comprobación de configuración que la precede ya rechazaba los casos; se detectó al desactivarla a propósito y se añadieron pruebas con una conexión simulada que contradice a la configuración; (2) una aserción de la prueba de «colaboradores sin supervisor» llevaba un `or` que la hacía casi siempre verdadera; se endureció; (3) tras el rechazo, la IA propuso detenerse y pedir otra contraseña; la persona responsable lo consideró una complicación innecesaria y decidió la excepción; (4) un intento de comprobar la petición de contraseña con `< /dev/null` dejó el script esperando en la consola de Windows, que trata `NUL` como terminal; se detuvo el proceso y se comprobó que no había escrito nada.

### Prompt 12 — Simplificar la política de contraseñas a 10 caracteres

- **Fase:** seguridad · **Herramienta:** Claude Code
- **Prompt (resumen fiel):** simplificar la política de contraseñas con un mínimo de 10 caracteres en lugar de 15; actualizar la política y ADR-002; eliminar el parámetro `--permitir-contrasena-corta`, que ya no hace falta; conservar Argon2id y las demás medidas; actualizar validaciones, pruebas y documentación; no modificar ni restablecer las contraseñas de las cuentas existentes; no introducir contraseñas en código, documentación ni archivos versionados; ejecutar las pruebas afectadas y confirmar que ambas cuentas siguen funcionando; sin funcionalidades nuevas, commit ni push.
- **Resultado:** el mínimo pasa a ser un parámetro de configuración (`PASSWORD_MIN_LENGTH`, 10 por defecto) en lugar de un valor fijo del código, y desaparecen la excepción y su indicador. ADR-002 sube a la versión 0.4: fija los 10 caracteres, los documenta como **desviación consciente** de los 15 de NIST (una referencia, no una obligación de SMARTWORK) y deja constado el riesgo y que la limitación de intentos fallidos aún no está implementada. Se actualizaron también las notas de A8 en los contratos de M1 y en las dependencias, el README y este registro. No se tocó ninguna contraseña existente.
- **Verificación:** 28 pruebas de cuentas (límite exacto de 10 aceptado, 9 rechazado, el mínimo gobernado por la configuración, ausencia del indicador y de la excepción); con el mínimo puesto a 15 a propósito fallan 2 y sin validar el mínimo fallan 3. Suite completa del backend: 242 superadas y 1 omitida; Flutter: análisis limpio y 64 superadas. Ambas cuentas reales inician y cierran sesión con sus contraseñas actuales y la huella de sus hashes no cambió.
- **Decisión humana:** el mínimo de 10 caracteres y su aplicación a la política, no solo a las cuentas de prueba. La IA señaló en el propio ADR que es una desviación de NIST y que la limitación de intentos sigue pendiente, para que la decisión quede informada.
- **Errores de la IA, corregidos:** una prueba incluía una cadena vacía entre los casos «demasiado corta», pero una variable de entorno vacía cuenta como no definida y produce otro mensaje; se retiró ese caso porque ya lo cubre la prueba de contraseña ausente.
