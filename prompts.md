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
11. [Cierre del MVP: M4, M5 y preparación de la entrega](#11-cierre-del-mvp-m4-m5-y-preparación-de-la-entrega)
12. [Límites del uso de IA generativa en este proyecto](#12-límites-del-uso-de-ia-generativa-en-este-proyecto)

---

## 0. Herramientas, modelos y contexto

### Fuentes y herramientas de apoyo

- **Material del curso AI4Devs:** base de referencia para aplicar las metodologías y los conocimientos utilizados en SMARTWORK (entre ellos el desarrollo guiado por especificación). Es una fuente de conocimiento; no es autor de ningún documento del producto.
- **Claude Code:** herramienta **principal**. Se usó directamente sobre el repositorio para estructurar la documentación y realizar las verificaciones documentales. Todo el contenido de `docs/`, `readme.md` y este registro se produjo con ella y fue revisado y aprobado por la persona responsable.
- **ChatGPT:** herramienta **complementaria**, usada para analizar propuestas, contrastar decisiones y revisar aspectos del proyecto. No es la herramienta principal ni se le atribuye la autoría del proyecto ni del material del curso. Su uso se declara aquí tal como fue; **no se han conservado el modelo ni los prompts concretos**, por lo que no se reproducen ni se inventan.

### Convención de este registro

Los prompts de las secciones 1 a 6, 10 y 11 son **resúmenes** del mensaje original, no transcripciones literales; así se indica en cada uno («resumen fiel»). Ninguno es una transcripción literal. Los mensajes completos y las respuestas están en el historial local de Claude Code, que no forma parte del repositorio.

**Clasificación de cada entrada según la evidencia** (se aplica a las entradas de la sección 11; las de las secciones 1 a 10 son todas «reconstrucción documental»):

- **PROMPT ORIGINAL:** el texto exacto está disponible y se cita entre comillas.
- **RECONSTRUCCIÓN DOCUMENTAL:** resumen fiel del objetivo y de las instrucciones del mensaje, escrito a partir del propio mensaje en el historial local y de los commits y documentos del repositorio. **No es el prompt original** ni una transcripción.
- **NO RECUPERABLE:** no hay texto ni evidencia suficiente para describir el mensaje; se declara la ausencia.

**Fragmentos literales.** En las entradas de la sección 11, la línea «Cita literal» reproduce **solo fragmentos exactos** (el título y la frase de autorización) de un mensaje más largo: **no constituye el prompt completo**. Únicamente dos entradas llevan texto literal más extenso: el Prompt 20 (mensaje íntegro) y el Prompt 22 (párrafo literal incluido en un mensaje mayor; es un fragmento, no un prompt completo).

Cuando una entrada enlaza un commit o un documento, la trazabilidad es la del propio repositorio; no se afirma que un mensaje produjo un cambio si no hay esa trazabilidad.

### Herramientas y modelos

| Herramienta | Modelo | Uso real |
|---|---|---|
| **Claude Code** (extensión para VS Code) | `claude-sonnet-5-5` (la inmensa mayoría de los mensajes de la sesión) y `claude-opus-5-5` (4 mensajes; la transcripción no registra para qué tarea) | Entrega 1: alcance, requisitos, historias, arquitectura, modelo de datos, contratos de la API, tickets, README y este registro. Entrega 2: código del backend y del frontend, migraciones, pruebas y actualización del README. Cierre del MVP (sección 11): M4, M5, auditoría de preparación y actualización del README. Los modelos de cada sesión constan en el historial local; la sesión de M5-T6 a FINAL-T3 usó `claude-sonnet-5-5` |
| Agentes de lectura web de Claude Code y búsqueda web | Los de la propia herramienta | Contrastar datos externos (precios, retención y regiones del proveedor de IA candidato, valores de seguridad de NIST y OWASP) para los ADR |
| Conector de Google Drive de Claude | — | Búsqueda de documentación de apoyo; no aportó contenido utilizable y no se incorporó nada al repositorio |
| Scripts de Python escritos por la IA, ejecutados en la sesión | — | Verificar la documentación (formato de los criterios, trazabilidad, coherencia entre documentos). No forman parte del repositorio |
| Extensión **Claude en Chrome**, dentro de la misma sesión | `claude-sonnet-5-5` | Entrega 2: validar en un Chrome real las cookies, el CSRF, el origen y el flujo completo, y capturar la evidencia de `docs/evidencia/` |
| Subagentes de Claude Code (lectura) | Los de la propia herramienta | Cierre del MVP: en FINAL-T3 dos subagentes de solo lectura recuperaron del repositorio y del historial local la evidencia de los prompts de M4-T5 a M4-T9 y de M5 a FINAL-T2; la redacción de este registro es de una sola sesión principal, revisada por la persona responsable |
| **Ollama** (`qwen2.5:3b-instruct`, `qwen3:8b`) | Modelos locales de terceros | **No son una herramienta de desarrollo**: son el proveedor experimental de generación de narrativa de M5, evaluado con datos ficticios (sección 11, M5-T5 y M5-T7). Sin datos reales |
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

No hay pull requests abiertos ni documentados. El trabajo de la primera entrega está en `feature/entrega-1-eq`, el de la segunda en `feature/entrega-2-eq` y el del cierre del MVP (M4 y M5, auditoría y documentación final) en `final-project-eq`, creada desde el último commit consolidado de la anterior sin modificarla. Ningún commit ni push se hizo sin autorización expresa de la persona responsable; a la fecha de esta revisión, los commits de `final-project-eq` posteriores al 2026-11-17 son locales y no se han publicado.

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

**Decisiones humanas del cierre del MVP (M1, M4 y M5)**

| Decisión | Efecto |
|---|---|
| Provisión por la CLI del servidor, sin endpoints administrativos, y rol de PostgreSQL separado (M1) | No hay superficie HTTP de administración |
| Evaluar la política de contraseña antes que el código (M1-T8.3) | La validez de un código no se revela |
| Elegir Pwned Passwords tras verificar su documentación y no instalar ~81 GB en desarrollo (M1-T8.6) | Mecanismo implementado, comprobación inactiva hasta instalarlo |
| D-M4-10: una referencia neutral no es visibilidad completa para escribir; 404 salvo recurso visible | Criterio uniforme de 403 y 404 |
| Visibilidad efectiva y no «perteneció alguna vez» (P-9, M5-T1); 403 frente a 404 (D-M5-02) | Los informes no revelan relaciones históricas |
| D-M5-06: 31 días, 400 hechos en total por solicitud, 0 reintentos y generación desactivada por defecto; el resto, abierto | Límites confirmados; los demás siguen abiertos |
| Aplazar Amazon Bedrock y AWS Lambda y continuar con Ollama local (M5-T5) | Proveedor local solo para desarrollo, con reservas |
| Detener la evaluación de Ollama y no ampliar la muestra (M5-T7); cerrar M5 técnicamente con reservas (M5-T8) | Evidencia exploratoria declarada como tal |

**Errores de la IA, detectados y corregidos**

- Afirmó que todos los criterios cumplían el formato sin comprobar el `CUANDO` (sección 5).
- Sus propios scripts de verificación tuvieron fallos de implementación (cadenas mal construidas, llaves sin escapar en plantillas, referencias de decisión combinadas en una celda) que se detectaron al ejecutarlos y se corrigieron antes de dar nada por válido.
- No pudo verificar el precio de Bedrock ni algunas cifras de OWASP; lo declaró en los ADR en lugar de estimarlo.
- **Entrega 2.** Propuso instalar la última versión de Riverpod, incompatible con Flutter 3.35.3 y Dart 3.9.2; el resolvedor de dependencias lo detectó y se fijó la familia 3.0.x con su generador.
- **Entrega 2.** Varias pruebas propias estaban mal escritas (un bloque vacío que esperaba un error, una búsqueda de texto que también encontraba el contenido de un campo, dos toques sin refrescar la pantalla). Fallaron al ejecutarse y se corrigieron; no se debilitó ninguna comprobación de la aplicación.
- **Entrega 2.** Al cancelar una tarea en segundo plano se cayó el clúster de PostgreSQL de desarrollo que colgaba de ella. Se retiró un proceso huérfano suyo (sin tocar el servicio de PostgreSQL del equipo) y se relanzó desacoplado de la sesión.
- **Entrega 2.** Un fallo aparente de inicio de sesión en el navegador no era de la aplicación: Chrome autocompletaba la contraseña guardada y la automatización escribía detrás. Se diagnosticó leyendo el campo (48 caracteres en lugar de 24) y comprobando que `curl` y `fetch` entraban.
- **Entrega 2.** Para dar por buenas las pruebas, se rompió el código a propósito en tres puntos y se comprobó que fallaban; no se aceptó que pasaran a la primera sin esa comprobación.
- **Cierre del MVP.** Implementé la visibilidad de M5 con «perteneció alguna vez al equipo» (revelaba relaciones históricas) y la persona la rechazó (M5-T1); tras un 403, tres pantallas de M4 conservaban datos anteriores (M4-T9); la narrativa de M5 no se exponía a las tecnologías de apoyo con `SelectableText` (M5-T6); la prueba de evaluación de Ollama compartía variable con la prueba real (M5-T7). Se corrigieron al verificar.

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
| Implementación | **Realizado (M1 a M5)** | Claude Code con los tickets, los contratos y los criterios como contexto: backend, migraciones, semilla, frontend y su integración, ticket a ticket con aprobación humana. M1 a M4 y el núcleo, la API y la interfaz de M5 están implementados; la generación con un modelo real de M5 es experimental y está desactivada por defecto (secciones 11 y 12) |
| Pruebas | **Realizado** | Pruebas de backend sobre PostgreSQL real desechable y de Flutter, matrices de trazabilidad M1 a M5 y recorridos reales en Chrome (cifras actuales en el [README](readme.md#26-tests)). Pendiente: prueba automatizada de la interfaz en un navegador dentro del repositorio y pruebas de penetración |
| Revisión de código | **Planificado** | Revisión asistida de cada pull request |
| Producto (M5) | **Realizado con reservas** | Núcleo determinista, API e interfaz de informes; generador simulado para pruebas y Ollama local como proveedor experimental de desarrollo. Amazon Bedrock y AWS Lambda siguen como arquitectura futura aplazada y no evaluada; datos laborales reales con un LLM no autorizados (ADR-003 y [matriz de M5](docs/evidencia/matriz-trazabilidad-m5.md)) |

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

### Prompt 13 — Completar M2 y el cierre de jornada por tickets (T1 a T9)

- **Fase:** implementación y validación · **Herramienta:** Claude Code (modelo Sonnet 5.5)
- **Prompt (resumen fiel):** tras un diagnóstico del estado real del repositorio, completar el módulo M2 y solo las operaciones M3-01 y M3-02, siguiendo la especificación aprobada, en una única rama (`feature/entrega-2-eq`), mediante nueve tickets sucesivos (T1 a T9), con un informe al final de cada uno y la aprobación de la persona responsable antes de avanzar. Cada ticket exigía contrato exacto, pruebas de backend sobre `smartwork_test`, pruebas de Flutter, análisis estático y una verificación real con FastAPI, Flutter y PostgreSQL en un clúster desechable; sin commits ni pushes sin autorización, sin tocar `smartwork_app` ni aplicar la migración 0006 sobre ella, sin exponer contraseñas y sin implementar nada que no estuviera especificado.
- **Resultado:** M2-01a a M2-08, M3-01 y M3-02 implementados en backend y Flutter (avances y secuencia, actividades no planificadas, detalle y listado, resumen diario, continuación planificada, cierre y reapertura con auditoría), con idempotencia, serialización por bloqueos de fila y protección del texto sin guardar. T9 añadió una matriz de trazabilidad por criterio, una verificación integral con reinicio de FastAPI y la documentación del estado real. Suites finales: 653 pruebas de backend, 414 de Flutter y análisis limpio.
- **Verificación:** cada ticket se cerró con mutaciones (se rompió el código a propósito y se comprobó que alguna prueba fallaba), un guion HTTP contra el servidor real y un recorrido en Chrome (escritorio y móvil) revisado con capturas; en T9, además, la comprobación de que los datos persisten tras reiniciar FastAPI.
- **Decisiones humanas:** mantener todo el trabajo en una sola rama y no proponer otras; confirmar el contrato v0.5 como base técnica; aprobar el 404 provisional para recursos ajenos hasta que exista M4; mantener que un resumen omitido o nulo equivale a vacío (D-03) en lugar de tratarlo como solicitud inválida; aprobar `bitacora_creada` en M2-04, varias continuaciones por fecha, el formato `{"bitacora": …}`, los instantes de auditoría en UTC y que cerrar o reabrir no modifique `modificada_en`; exigir que la interfaz no ofrezca acciones prohibidas sin quitar las validaciones del backend. Cierre documental posterior (2026-11-09): confirmar que IR-11 y CA-78 se armonizan (una inserción retroactiva se incorpora sin tocar los avances posteriores y el estado actual sale del orden laboral completo, sin ampliar transiciones); conservar de forma provisional la aceptación de avances anteriores al origen de la actividad, sin basarse en `creada_en`; y aprobar el envoltorio `elementos`/`siguiente` del listado.
- **Errores de la IA, corregidos:** (1) la protección contra pérdida de texto no se desregistraba porque comparaba funciones con `identical` en lugar de `==`; (2) al cambiar de fecha durante un cierre en curso, la suscripción que mantenía vivo el proveedor pertenecía al widget y moría con él, así que la respuesta del servidor no podía aplicarse; se detectó con una prueba de cambio de fecha en vuelo y se movió a nivel de contenedor; (3) dos conjuntos de pruebas pasaban sin detectar la regresión que decían cubrir (la recarga del detalle tras planificar y el cierre del diálogo de reapertura mientras guarda): las mutaciones lo demostraron y se reforzaron; (4) tres formularios ofrecían enviar sobre una fecha cerrada y solo fallaban después; (5) una primera versión de la matriz citaba nombres de prueba de memoria: un verificador automático comprobó cada cita y se corrigieron cuatro que no existían. La IA también señaló, sin decidirlas, las diferencias entre IR-11 y CA-78, el 403 frente al 404, y las fechas anteriores al origen de una actividad.

### Prompt 14 — Completar M3 por tickets y cierre técnico (T10 a T14)

- **Fase:** implementación y validación · **Herramienta:** Claude Code (modelo Sonnet 5.5)
- **Prompt (resumen fiel):** continuar en la misma rama (`feature/entrega-2-eq`), sin commits, pushes ni merges, con un ticket por operación de M3 y la aprobación de la persona responsable antes de avanzar: T10 reactivación de actividades completadas (M3-04), T11 marca de error y su reversión (M3-05 y M3-06), T12 corrección auditada de avances (M3-03), T13 consulta del historial de auditoría solo para la persona propietaria (M3-07) y T14 validación integral y cierre técnico de M3. Cada ticket exigía contrato exacto, pruebas de backend sobre `smartwork_test`, pruebas de Flutter, análisis estático y verificación real con FastAPI, Chrome y PostgreSQL en un clúster desechable; pruebas destructivas solo en `smartwork_test`; sin tocar `smartwork_app` salvo orden expresa; sin exponer credenciales; sin implementar nada de M1, M4 ni M5. T14 pedía además, en solo lectura, diagnosticar `smartwork_app` y sus migraciones.
- **Resultado:** M3-01 a M3-07 implementados en backend y Flutter, con migraciones 0006 a 0008 (permisos por columna e inmutabilidad en la base). La auditoría de solo anexado pasó a registrar el reloj real de cada operación, de modo que el orden de la consulta es el de aplicación. M3-07 queda limitado a la propietaria: el acceso del supervisor y la visibilidad histórica dependen de M4. El cierre técnico incorporó M3-04 y sus criterios a la matriz de trazabilidad y dejó el estado de cada criterio (implementado, parcial, bloqueado por M1 o M4). Suites finales: 1031 pruebas de backend (1 omitida a propósito), 619 de Flutter y análisis limpio.
- **Verificación:** mutaciones por ticket (backend 21 de 21 y Flutter 23 de 23 en T13, tras reforzar las pruebas que dejaron sobrevivientes); un guion HTTP contra el servidor real; recorridos en Chrome de escritorio y móvil; y, en T14, una base nueva creada con `alembic upgrade head` desde cero que recorrió los 12 pasos del flujo, la idempotencia, la concurrencia real y la consistencia histórica, y un guion de navegador que ejecutó desde la interfaz la reactivación, la corrección, la marca, la reversión, el cierre y la reapertura y comprobó en la base que constaban exactamente las seis entradas de auditoría esperadas. El diagnóstico de solo lectura de `smartwork_app` confirmó la migración 0008 y un esquema idéntico al de una instalación nueva salvo dos permisos del esquema `public` heredados del aprovisionamiento manual.
- **Decisiones humanas:** la finalización relevante de una actividad es el último avance del orden laboral completo (T10); el origen laboral de una actividad es la fecha de su bitácora de origen, de forma provisional (PA-28); en T12, la regla de PA-29 (una corrección no puede introducir violaciones de secuencia nuevas, comparadas por avance y tipo de violación) y tres interpretaciones menores del contrato; en T13, limitar la consulta de la auditoría a la propietaria y no implementar la supervisión; y la orden expresa de publicar la aplicación sobre la base `smartwork_app` con las migraciones pendientes aplicadas (con respaldo previo), que prevaleció sobre la prohibición general de tocar esa base. La persona responsable consolidó en el repositorio el trabajo de T10 a T13 antes de T14.
- **Errores de la IA, corregidos:** (1) un orden de la auditoría por el inicio de la transacción hacía que correcciones simultáneas quedaran desordenadas y provocó una prueba inestable; se corrigió en origen usando el reloj real; (2) la primera versión de las pruebas de la consulta dejó tres mutaciones vivas (el filtro por propietaria y por tipo de registro, y la comprobación de propiedad del avance), y se reforzaron; (3) se suponía que un método no admitido respondía 405 y respondía 400, y que un resumen de una jornada pasada se auditaba como corrección; se ajustaron las pruebas al comportamiento real y se documentó la diferencia; (4) un cuarto botón de la cabecera desbordaba el ancho en escritorio y se movió el enlace a la tarjeta de estado; (5) el guion de la verificación integral de T14 daba por buenos códigos de error que no eran los del contrato y contaba una entrada de auditoría de más; se comprobó cada caso contra el código y las pruebas existentes antes de tocar nada; (6) un guion auxiliar que comprobaba que no quedaban mutaciones ejecutó, por error, los bucles de mutación de otros guiones y, al detenerse, dejó una mutación aplicada en `secuencia.py`; una comprobación estática la detectó, se restauró el texto original y se confirmó que el árbol de trabajo coincidía con lo consolidado.

### Prompt 15 — Provisión de M1 por tickets (M1-T0 a M1-T7)

- **Fase:** implementación y validación · **Herramienta:** Claude Code (modelo Sonnet 5.5)
- **Prompt (resumen fiel):** tras el diagnóstico de M1 y la aprobación de su plan por tickets, implementar uno a uno, en la misma rama (`feature/entrega-2-eq`), sin commits ni pushes y esperando la aprobación antes de avanzar: M1-T0 (405 con `Allow` para métodos no admitidos), M1-T1 (política interna de visibilidad histórica), M1-T2 (provisión inicial de equipos y personas por la CLI del servidor, con personas operadoras y rol de PostgreSQL propios) M1-T3 (traslado y cambio de rol, con revisión previa del script del rol de provisión) M1-T4 (finalización de pertenencias y cancelación o sustitución de operaciones programadas) y M1-T5 (validación integral de un traslado oficial: CA-212 a CA-214 con las operaciones de M2 y M3, sin simular que una operación futura ya es efectiva modificando pertenencias por SQL) y M1-T6 (desactivación del acceso: sesiones revocadas en la misma transacción, advertencia estructurada de supervisión efectiva y permisos mínimos por columna) y M1-T7 (protección frente a intentos fallidos de autenticación: primero un informe de preparación sin código, con los valores exactos de ADR-002 A9 y A11 y las decisiones por aprobar, y después, con las decisiones aprobadas, la implementación: cinco intentos libres y esperas de 30 s a 1 hora por cuenta y origen, 429 con `Retry-After`, límites por origen, HMAC de los identificadores, eventos técnicos con retención de 30 días, la misma curva para la persona operadora y la cuenta atrás en el login de Flutter, sin implementar todavía el tope agregado de 100).
- **Resultado:** respuesta 405 con `Allow`; función única de «equipo en una fecha» y decisión interna de visibilidad; órdenes `crear-primer-operador`, `crear-equipo`, `crear-persona`, `registrar-traslado`, `finalizar-pertenencia` y `cancelar-operacion-programada` (migraciones 0009 a 0011), con validación de la línea temporal completa, relevo de supervisor atómico, serialización por bloqueos, una entrada de auditoría por orden una protección diferida de IR-32 en la base solo para el rol de provisión y un permiso de borrado acotado en la base a lo que todavía no ha empezado; la desactivación del acceso (M1-T6, migración 0012) y, en M1-T7, la protección frente a intentos fallidos de autenticación (migración 0013 con tablas separadas, 429 con `Retry-After`, esperas progresivas por cuenta y origen con reserva atómica, límites por origen, eventos técnicos con purga, la misma curva para la persona operadora y la cuenta atrás en el login de Flutter).
- **Verificación:** suite completa del backend sobre un clúster PostgreSQL desechable (2619 superadas y 1 omitida a propósito (193 más que al cerrar M1-T6) al cierre de M1-T7; 2426 al cierre de M1-T6) y de Flutter (638 superadas y `flutter analyze` sin incidencias); en M1-T7, mutaciones del backend (71 de 71 muertas tras reforzar las pruebas (56 sobre el código y 15 sobre la migración; en la primera pasada sobrevivieron 7 de 70, que revelaron huecos reales y se corrigieron: el olvido del contador a las 24 horas oculto por la limpieza, la comprobación vacua de «transacción abierta durante Argon2», `Retry-After` sin exponer por CORS, el dominio de la clave de la persona operadora, la actualización de un evento antiguo y una mutación mal planteada)) y de Flutter (23 de 24 muertas; la superviviente es defensiva y equivalente (ninguna acción de la interfaz puede iniciar una espera nueva mientras otra sigue activa: el envío está deshabilitado y protegido); en la primera pasada sobrevivieron 3 y revelaron que faltaba probar el envío con Enter durante la espera y que un `Retry-After` de otro error no debe iniciar una espera), pruebas de concurrencia con hilos y PostgreSQL reales y evidencia real con uvicorn, la CLI como procesos reales y Chrome; mutaciones por ticket (26 de 27 en M1-T2, 38 de 39 en M1-T3 y 44 de 45 en M1-T4, con una equivalente en cada uno; en M1-T5, 5 de 6 sobre código de producción, con la sexta fuera del recorrido); evidencia real con la CLI como procesos reales, incluida una carrera entre dos procesos; comprobación de solo lectura de `smartwork_app`, a la que no se aplicó ninguna migración.
- **Decisiones humanas:** provisión por CLI del servidor sin endpoints administrativos; persona operadora con credencial propia; rol de PostgreSQL separado de privilegios mínimos; protección diferida de IR-32 solo si las pruebas demuestran que admite relevos; nombre de equipo único por organización; confirmación de DM-04; no inventar los parámetros pendientes de ADR-002; revisar el script del rol de provisión antes de M1-T3 (sin contraseñas visibles, solo la base de pruebas, sin tocar `smartwork_app`); en M1-T7: cinco intentos libres y esperas de 30 s a 1 hora por cuenta y origen, límites por origen de 30 en 5 minutos y 200 en 1 hora, HMAC con un secreto nuevo (`AUTH_PEPPER`), sesión de 24 horas y 1 hora de inactividad, proxies de confianza solo si se configuran expresamente (DT-07), retención técnica de eventos de 30 días con purga, la persona operadora con la misma curva y sin deshabilitarla, y **no implementar todavía el tope de 100 fallos** (a revisar con M1-T8); la persona responsable confirmó después las siete interpretaciones adoptadas (la quinta con una corrección: solo una autenticación completa reinicia el contador) y pidió preparar, sin escribir código, el diseño de M1-T8 (primer acceso y recuperación); después aprobó el plan incremental T8.1 a T8.6 con autorización por subpaso, ordenó empezar solo por T8.1 (modelo de códigos con HMAC, generación de 128 bits y política de contraseñas) y cambió la metodología de pruebas hacia verificaciones focalizadas, sin mutaciones rutinarias ni suite completa salvo cierres de módulo.
- **Errores de la IA, corregidos:** (1) la primera versión del script del rol de provisión pasaba la contraseña como argumento y aceptaba cualquier base: se rehízo con `\password` y una lista de bases permitidas; (2) una mutación que dejó la base de pruebas a medio migrar hizo que la tanda siguiente «matara» mutantes por un fallo de preparación y no por las pruebas: se detectó, se restauró la base y se repitió la tanda; (3) una mutación de permisos sobre bitácoras estaba mal planteada (`UPDATE` sin `SELECT` no basta para `set id = id`) y sobrevivió; (4) un bloqueo no previsto de `\password` sin terminal dejó un proceso colgado, que se terminó; (5) la guarda de M1-T1 sobre la definición del intervalo detectó legítimamente el nuevo SQL de cierre y se documentó una excepción acotada en lugar de rodear la guarda; (6) en M1-T4 el primer guion de evidencia real falló por errores del propio guion (una persona con un cambio programado, un traslado que IR-32 rechazaba con razón y una fórmula de invariantes con el máximo de los fines) y no se tocó la aplicación; (7) cuatro mutaciones sobrevivieron al principio y revelaron pruebas que faltaban, y una «muerta» lo era por un error de sintaxis de la propia mutación; (8) en M1-T5 las primeras pruebas de extremo a extremo fallaron por supuestos erróneos míos (una jornada cerrada rechaza avances con `BITACORA_CERRADA`, que es lo correcto, y la forma de una entrada de auditoría) y el primer guion de la evidencia real tenía una comprobación contradictoria; en ningún caso se tocó la aplicación; (9) en M1-T6 una prueba de carrera con inicios de sesión simultáneos descubrió un defecto real (la comprobación del acceso usaba el inicio de la transacción y dejaba pasar a un inicio de sesión que ya había empezado), que se corrigió en la política de acceso con una prueba determinista, y dos pruebas mías fallaron de forma intermitente por suposiciones de temporización; (10) en M1-T7: (a) la primera idea de limpiar filas caducadas con `SELECT … FOR UPDATE SKIP LOCKED` exigía un permiso de actualización que la aplicación no tiene y no se quiso conceder: se cambió por un único limpiador con candado consultivo no bloqueante; (b) mis comprobaciones de «no hay transacción abierta durante Argon2» eran **vacuas** (con un rol sin privilegios `pg_stat_activity.state` es siempre nulo, así que contaban 0): lo descubrió una mutación que sobrevivía, se rehicieron con `pg_locks` y con un control positivo, y al hacerlo salió un **defecto real** (la rama de rechazo mantenía la transacción y el bloqueo de la persona mientras escribía su evento), que se corrigió; (c) otros mutantes que sobrevivían revelaron que la limpieza acotada ocultaba el olvido a las 24 horas, que no había prueba de `Retry-After` expuesto por CORS y que se podía actualizar un evento antiguo; (d) varios guiones míos fallaron por errores propios (la cookie `Secure` no se reenvía por http, el campo de usuario del navegador acumulaba el texto, esperas menores que la duración del recorrido y literales rotos por el uso de heredocs), sin que se tocara la aplicación; (e) el primer diseño de accesibilidad ocultaba la cuenta atrás a los lectores de pantalla para no leerla cada segundo: se cambió a un texto con la cuenta atrás y una región viva aparte con el mensaje fijo.

### Prompt 16 — Primer acceso y recuperación con código, por subpasos (M1-T8.1 a M1-T8.6)

- **Fase:** implementación y validación · **Herramienta:** Claude Code (modelo Sonnet 5.5)
- **Prompt (resumen fiel):** tras el diseño aprobado de M1-T8, implementar uno a uno y en la misma rama (`feature/entrega-2-eq`, sin commits, pushes ni merges, sin tocar `smartwork_app` ni el PostgreSQL local 5432), esperando la aprobación antes de avanzar: T8.1 (modelo de códigos, generación y política de contraseñas), T8.2 (emisión administrativa por la CLI), T8.3 (canje del primer acceso por API), T8.4 (canje de la recuperación por API), T8.5 (pantallas Flutter) y T8.6 (endurecimiento y cierre: contraseñas comprometidas con un listado local de procedencia verificada, purga de códigos a los 30 días, revisión de seguridad focalizada, documentación). Con pruebas focalizadas, sin mutaciones rutinarias ni la suite completa por defecto, sin inventar parámetros no aprobados, sin credenciales en argumentos ni salidas y sin avanzar al siguiente ticket sin aprobación.
- **Resultado:** código de 128 bits con solo su HMAC guardado (secreto propio, `CODE_PEPPER`, distinto de `AUTH_PEPPER`); emisión por CLI con el código mostrado una vez y solo en una terminal; dos funciones de la base `SECURITY DEFINER` blindadas para el canje atómico (primer acceso y recuperación, esta con revocación de todas las sesiones y sin reactivar accesos desactivados); política de contraseña evaluada antes que el código, sin consumirlo; pantallas Flutter que no crean sesión ni guardan nada, con espera por 429; mecanismo de contraseñas comprometidas con procedencia obligatoria y orden `purgar-codigos` (migración 0017, solo `DELETE` para la provisión). **Contraseñas comprometidas:** primero no se incorporó ningún listado porque no se pudo verificar la licencia de los candidatos; la persona responsable verificó la documentación oficial de Have I Been Pwned y eligió Pwned Passwords, y se rehízo la comprobación como consulta local por rangos SHA-1 en el formato oficial (sin enviar contraseñas a servicios externos, sin cargar el conjunto en memoria, sin dependencias nuevas, instalación completa obligatoria). El conjunto (~81 GB) no cabía en el entorno de desarrollo (~77 GB libres, sin .NET): **no se instaló ni se improvisó un subconjunto**; se documentó el tamaño medido y una guía de instalación reproducible para el despliegue.
- **Verificación:** pruebas focalizadas en cada subpaso (por ejemplo, en T8.6: 45 nuevas y 295 de regresión superadas, más un rango real de Pwned Passwords comprobado de forma puntual; en T8.5: 16 nuevas y 85 con las del inicio de sesión, `flutter analyze` sin incidencias), evidencia real con uvicorn y PostgreSQL desechable en T8.3 y T8.4 y recorridos reales en Chrome (escritorio y móvil, 22 comprobaciones por tamaño) en T8.5; sin mutaciones ni suite completa desde T8.1. Privilegios y blindaje de las funciones comprobados en la base.
- **Decisiones humanas:** el diseño por subpasos con aprobación individual; formato y vigencia del código, intentos y verificación de identidad declarada por la persona operadora; entrega directa sin correo ni SMS; que la política de contraseña se evalúe antes que el código; que la recuperación no reactive accesos desactivados; la metodología de pruebas ligera; y no incorporar datos de procedencia desconocida.
- **Errores de la IA, corregidos:** (1) en T8.6 una prueba que escribí para comprobar los registros descubrió un **defecto real**: ante un error de la base durante el canje, SQLAlchemy incluía en el registro el hash Argon2 de la contraseña nueva, el HMAC del código y el identificador; se corrigió con `hide_parameters=True` y la prueba falla sin el cambio; (2) en T8.6 intenté verificar la licencia del listado del NCSC y de Pwned Passwords y no pude desde el agente de lectura (los sitios no resolvían y el archivo web no estaba permitido): en lugar de suponerla, no se incorporó ningún dato hasta que la persona responsable eligió la fuente; ya con Pwned Passwords, mis pruebas con instalaciones sintéticas de 16 rangos fallaban en dos flujos porque la contraseña «válida» elegida caía en un rango que esa instalación no tenía (en una instalación real completa siempre existe): se corrigió el montaje de la prueba y el sistema, que falla cerrado, se mantuvo; y dejé en el código una línea absurda que detecté y limpié al releerlo; (3) en T8.5 mis primeras cifras de pruebas y de comprobaciones de Chrome en la documentación eran incorrectas (24 en lugar de 16; 25 en lugar de 22) y se corrigieron al contarlas; (4) varios guiones míos fallaron por errores propios (un `await` dentro de un generador, el cierre de sesión que en móvil está en el menú, un índice único que mis datos de prueba violaban, literales rotos por el uso de heredocs) sin que se tocara la aplicación; (5) en T8.1 a T8.4 una comprobación mía de «no hay transacción abierta» era vacua (con un rol sin privilegios el estado de la actividad es siempre nulo): se rehízo con los bloqueos de la base y con un control positivo.

### Prompt 17 — Cierre integral del módulo M1 (M1-T9)

- **Fase:** verificación y cierre · **Herramienta:** Claude Code (modelo Sonnet 5.5)
- **Prompt (resumen fiel):** tras aprobar M1-T8.6 (con la integración de Pwned Passwords aprobada como implementación, sin descargar el conjunto de ≈ 81 GB en desarrollo y sin declarar activa la comprobación hasta instalarlo), realizar el cierre técnico y contractual de M1: clasificar los criterios (implementado y probado, parcial, pendiente, fuera de alcance aprobado, bloqueado) sin declarar ninguno completado sin evidencia; revisar diez recorridos principales y las dependencias de M4; comprobar las migraciones 0009 a 0017 sobre una instalación desechable; ejecutar la regresión general del backend y de Flutter y un recorrido real con FastAPI, Flutter Web y PostgreSQL desechable; registrar los pendientes de seguridad y despliegue sin ampliar M1; revisar el estado de Git y preparar una recomendación de consolidación sin commits ni pushes; actualizar la matriz de trazabilidad, los contratos, el ADR-002, el alcance, el README, el plan y este registro.
- **Resultado:** matriz completa de M1 (`docs/evidencia/matriz-trazabilidad-m1.md`): 65 criterios: 48 implementados y probados, 15 parciales, 2 bloqueados por otro módulo (M4 o M5), 0 pendientes y 0 fuera de alcance; 13 contratos implementados y probados y M1-10 fuera de alcance aprobado; las 127 pruebas citadas como evidencia se comprobaron por nombre; migraciones 0001 a 0017 verificadas; recorrido integral real; pendientes y dependencias de M4 registrados.
- **Verificación:** regresión completa del backend (2804 superadas y 1 omitida) y de Flutter (654 superadas, `flutter analyze` sin incidencias) y el recorrido integral real; sin mutaciones.
- **Decisiones humanas:** autorizar el cierre de M1; aprobar la integración con Pwned Passwords como implementación y diferir su instalación al despliegue; proponer una actualización trimestral sujeta a validación operativa; no ampliar M1 para resolver el backlog de producción; consolidar los cambios acumulados solo con su autorización expresa.
- **Errores de la IA, corregidos:** (1) mi primera clasificación de criterios usaba solo las etiquetas «CA-xx» del código de las pruebas, que cubre menos de la mitad: se rehízo leyendo los nombres de las pruebas de M1 y comprobando por nombre las 127 citas; (2) mi guion del recorrido real suponía `rol` en lugar de `rol_vigente` y 401 en lugar de 403 para un acceso desactivado, y una consulta usaba una sintaxis que PostgreSQL no admite con parámetros: se corrigieron sin tocar la aplicación; (3) lancé la regresión completa con `-x` y `--maxfail` a la vez, contradictorios (funcionó como `--maxfail=30`); (4) una prueba de M1-T6 que yo había dejado obsoleta con las rutas de canje de T8.3 solo se descubrió en la regresión completa, no en las ejecuciones focalizadas: es el motivo de ejecutar la suite completa en un cierre de módulo.

### Prompt 18 — Consulta histórica y supervisión por tickets (M4-T0 a M4-T4)

- **Fase:** análisis, implementación y validación · **Herramienta:** Claude Code (modelo Sonnet 5.5) · **Rama:** `final-project-eq` (creada desde el último commit consolidado de la entrega anterior, sin modificarla)
- **Prompt (resumen fiel):** tras analizar M4 con el método de desarrollo guiado por especificación (M4-T0: lectura de contratos, criterios y reglas RA-01 a RA-12, brechas y decisiones D-M4-01 a D-M4-09), implementar un ticket cada vez, con aprobación expresa antes de avanzar: M4-T1 (leer la bitácora de un compañero), M4-T2 (histórico por colaborador y fechas), M4-T3 (núcleo de la vista de supervisión) y M4-T4 (herencia y continuidad de actividades entre equipos). Reglas fijas: reutilizar la política de visibilidad de M1 sin escribir otra, aplicar la autorización al seleccionar los datos, **fallar cerrado** ante cualquier forma no determinable, solo pruebas focalizadas sobre PostgreSQL desechable (nunca `smartwork_app` ni el puerto 5432), evidencia HTTP real en cada ticket, no tocar Flutter, no declarar cerrado ningún criterio sin evidencia, y commits locales solo cuando se autorizan.
- **Resultado:** `GET /api/v1/personas/{id}/bitacoras/{fecha}`, `GET /api/v1/historico` (con paginación por posición propia de M4 y la migración 0018, un índice) y `GET /api/v1/equipo/supervision` (inclusión por planificación, avances y pendiente al corte; estado al corte frente al actual; totales antes de paginar; en M4-T4, formas completa, neutral y referencia mínima, estado al corte solo si el avance que lo determina está autorizado y recuento aparte para lo que no tiene estado al corte). La decisión de herencia vive en la política compartida (`forma_en_supervision`, `estado_al_corte_es_visible`) y el módulo solo reúne hechos. Commits locales de M4-T1 a M4-T4.
- **Verificación:** 16, 34, 25 y 21 pruebas nuevas en T1 a T4 sobre PostgreSQL real; regresiones focalizadas (668 tras T2; 1157 y 998 tras T3) y recorridos HTTP reales con uvicorn en cada ticket; validación de la migración 0018 con 157.191 bitácoras (consulta sin filtro de 338 ms a 2,6 ms; reversible). Sin mutaciones ni suite completa.
- **Decisiones humanas:** aprobar la migración 0018 solo con evidencia y con la condición de detenerse si el peor caso la contradecía; separar el núcleo de la supervisión (T3) de la herencia entre equipos (T4); que el 403 sea por rol y no revele registros; que la referencia mínima no entre en los totales; no avanzar de ticket sin aprobación; y mantener la autoría del repositorio sin trailers añadidos.
- **Errores de la IA, corregidos:** (1) mi primera consulta de supervisión partía de todas las actividades de la organización y tardaba **64 s** con 31 mil actividades; se detectó al medir con datos representativos, se reescribió para partir del equipo (unos 100 ms) y se documentó; (2) el guion de validación del índice dejó una transacción abierta que bloqueó el `DROP INDEX` del downgrade durante 23 minutos: era un fallo del guion, no del producto; (3) varios guiones de evidencia tenían expectativas mal calculadas (por ejemplo, un período sin avances del traslado o el número de elementos por página) y se corrigieron sin cambiar el código; (4) los archivos compartidos mezclaban cambios de T2 y T3 y el commit de T2 se construyó solo con lo suyo, verificándolo sobre el árbol exacto exportado del índice; (5) el comportamiento provisional de T3 ocultaba la actividad entera ante lo no autorizado y T4 lo sustituyó por las formas definitivas.

---

## 11. Cierre del MVP: M4, M5 y preparación de la entrega

Continúa la numeración de la sección 10 y cubre, en orden cronológico, M1 (correspondencia por ticket), M4-T5 a M4-T9, M5-T0 a M5-T8, la auditoría FINAL-T1, la actualización FINAL-T2 y este registro (FINAL-T3). M4 y M5 se desarrollaron en la rama `final-project-eq`; M1 en `feature/entrega-2-eq`. Cada mensaje de la persona responsable aprobaba el ticket anterior, fijaba decisiones y ordenaba **solo** el siguiente; los commits de cada ticket se enlazan por su hash. La clasificación de cada entrada (PROMPT ORIGINAL, RECONSTRUCCIÓN DOCUMENTAL o NO RECUPERABLE) está definida en la sección 0. **Todas las entradas de esta sección son «reconstrucción documental» salvo las dos marcadas como PROMPT ORIGINAL**; en todas, el texto íntegro del mensaje existe en el historial local de Claude Code y aquí solo se cita lo que se indica entre comillas.

### Prompt 19 — M1: trazabilidad por ticket y consolidación en commits

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL para cada mensaje de la tabla (el texto íntegro de todos existe en el historial local; aquí se resume). El mensaje de M1-T8.5 se transcribe **íntegro** más abajo como PROMPT ORIGINAL. **Herramienta:** Claude Code · **Rama:** `feature/entrega-2-eq`
- **Relación con los Prompts 15 a 17:** estos tres ya resumen M1 por grupos de tickets. Esta entrada **no los sustituye**: añade la correspondencia ticket por ticket y la consolidación. Todos los mensajes siguen el mismo patrón: aprobar el ticket anterior, fijar decisiones y ordenar solo el siguiente, con las restricciones repetidas (rama única, sin push ni merge, sin tocar `smartwork_app` ni el PostgreSQL 5432, pruebas solo sobre bases desechables).
- **Commits:** M1 **no tiene commits por ticket**. Se consolidó el 2026-11-17 con autorización expresa en cuatro commits: `870ecf1` (backend y migraciones, M1-T0 a M1-T8.6), `4ab5c96` (pruebas del backend), `55db05e` (pantallas Flutter) y `5b6405d` (cierre técnico, contratos, ADR-002 y evidencias).

| Ticket | Fecha | Qué ordenó el mensaje (resumen fiel) | Resultado documentado |
|---|---|---|---|
| Diagnóstico de M1 | 2026-11-11 | Tras cerrar M3, diagnosticar el estado real de M1 y proponer un plan incremental sin código | [Plan de M1](docs/backlog/tickets/m1-plan-implementacion.md) |
| M1-T0 | 2026-11-11 | Aprobar el plan T0 a T9 con nueve decisiones (provisión por CLI sin endpoints, persona operadora con credencial propia, rol de PostgreSQL separado, IR-32, nombre único de equipo, no inventar parámetros de ADR-002) e implementar solo la respuesta 405 con `Allow` (PA-30) | 405 con `Allow` (`convenciones.md`) |
| M1-T1 | 2026-11-11 | Equipo en una fecha con intervalos semiabiertos y política interna de visibilidad (RA-01 a RA-12), separando la decisión interna de la respuesta HTTP | `compartido/pertenencias.py` y `visibilidad.py`; sin migración |
| M1-T2 | 2026-11-11 | Provisión de equipos y personas por la CLI; nombre de equipo único por organización sin distinguir mayúsculas ni espacios exteriores; sin inventar credenciales | Órdenes `crear-primer-operador`, `crear-equipo` y `crear-persona`; migración 0009 |
| M1-T3 | 2026-11-11 | Traslado y cambio de rol; **antes**, revisar el script del rol de provisión (sin contraseñas en argumentos, sin tocar roles ajenos ni `smartwork_app`) | `registrar-traslado`; migración 0010 |
| M1-T4 | 2026-11-11 | Finalizar pertenencias y cancelar o sustituir operaciones programadas; PA-31 (no ampliar M1-05) | `finalizar-pertenencia` y `cancelar-operacion-programada`; migración 0011 |
| M1-T5 | 2026-11-11 | Validar un traslado real de extremo a extremo y cerrar CA-212 a CA-214 sin simular por SQL | CA-212 a CA-214 probados con uvicorn y Chrome |
| M1-T6 | 2026-11-17 | Desactivación del acceso (M1-08) con la decisión DM-09: advertencia estructurada si el equipo queda sin supervisión efectiva | `desactivar-acceso`; migración 0012 |
| M1-T7 | 2026-11-17 | Primero un informe de preparación y, aprobado el diseño, la protección frente a intentos fallidos (cinco libres, esperas de 30 s a 1 h, límites por origen, HMAC con `AUTH_PEPPER`, sin el tope de 100) | Migración 0013, 429 con `Retry-After` y cuenta atrás en el login |
| M1-T8.1 a T8.6 | 2026-11-17 | Primer acceso y recuperación con código por subpasos con autorización individual (modelo y política de contraseñas, emisión por CLI, canje por API, pantallas Flutter, endurecimiento); aquí nace la **metodología de pruebas ligera** | Migraciones 0014 a 0017; Pwned Passwords local (`docs/operacion/pwned-passwords.md`) |
| M1-T9 | 2026-11-17 | Cierre integral: clasificar los criterios sin declarar ninguno sin evidencia, regresión general y recorrido real | [Matriz de M1](docs/evidencia/matriz-trazabilidad-m1.md): 65 criterios (48 implementados y probados, 15 parciales, 2 bloqueados por otro módulo) |
| Consolidación | 2026-11-17 | Cuatro commits locales por áreas, con staging explícito, sin tocar la configuración de Git | Los cuatro commits citados arriba |

- **Decisiones humanas a destacar:** el cambio de A5 (la verificación de identidad queda fuera de banda y trazable); que la política de contraseña se evalúe **antes** que el código, porque la política es pública y la validez de un código es información sensible; que una contraseña correcta solo reinicie la penalización si el acceso está habilitado y hay pertenencia vigente (corrección de una interpretación mía en M1-T7); la elección de Pwned Passwords como fuente tras verificar la persona responsable su documentación oficial (en M1-T8.6 no pude verificar las licencias y no incorporé ningún dato); y no descargar el conjunto de unos 81 GB en desarrollo.
- **Errores de la IA corregidos:** ver los Prompts 15 a 17, que ya los detallan (script del rol de provisión con la contraseña como argumento, defecto de carrera en M1-T6, comprobaciones vacuas de «transacción abierta», registro del hash Argon2 en un error de base de datos, entre otros).
- **Límite de evidencia:** varias cifras de pruebas y mutaciones de M1-T0 constan solo en el informe que di en la sesión, no en un documento ni en un commit; no se reproducen aquí.

### Prompt 20 — M1-T8.5: pantallas Flutter de primer acceso y recuperación (PROMPT ORIGINAL, íntegro)

- **Clasificación:** PROMPT ORIGINAL (texto íntegro, 1546 caracteres, sin secretos). **Fecha:** 2026-11-17 · **Herramienta:** Claude Code
- **Texto literal:**

  > M1-T8.4 ya fue revisado y aprobado. No repitas su implementación.
  >
  > Continúa exclusivamente con SMARTWORK M1-T8.5: pantallas Flutter de primer acceso y recuperación de contraseña.
  >
  > Utiliza los endpoints existentes:
  > - POST /api/v1/acceso/primer-acceso
  > - POST /api/v1/acceso/recuperacion
  >
  > Implementa formularios para identificador de acceso, código, contraseña nueva y confirmación.
  >
  > Incluye mostrar/ocultar contraseña, validaciones básicas, mensajes uniformes, manejo del 429 y Retry-After, carga, prevención de solicitudes duplicadas y navegación al inicio de sesión después del éxito.
  >
  > No crees sesiones automáticamente ni almacenes códigos o contraseñas de forma persistente.
  >
  > La recuperación sigue siendo administrada por una operadora; no implementes envío automático de códigos, correo ni SMS.
  >
  > Reutiliza componentes y arquitectura existentes. Mantén el diseño responsive y accesible.
  >
  > Realiza únicamente pruebas focalizadas de ambos flujos, ejecuta flutter analyze y comprueba un recorrido representativo en Chrome si el entorno está disponible. No ejecutes mutaciones ni suites completas innecesarias.
  >
  > No modifiques código del backend salvo que exista un defecto contractual que debas reportar primero.
  >
  > Trabaja exclusivamente en feature/entrega-2-eq. No modifiques smartwork_app ni el PostgreSQL local 5432.
  >
  > No hagas commits, pushes ni merges.
  >
  > Actualiza la documentación correspondiente e informa resultados, archivos modificados y riesgos.
  >
  > No avances a M1-T8.6 sin mi aprobación.

- **Resultado:** pantallas de primer acceso y de recuperación enlazadas desde el inicio de sesión, sin cambios de backend, con pruebas focalizadas y `flutter analyze` limpio; el recorrido en Chrome se hizo con el árbol de semántica, no con lectores de pantalla reales. Se consolidó en `55db05e`.

### Prompt 21 — M4-T5: historial de una actividad del equipo (M4-04)

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Autorizo: 1. Consolidar M4-T4 en un commit local. 2. Implementar M4-T5: historial de una actividad del equipo.»
- **Prompt (resumen fiel):** cerrar M4-T4 con precisiones (una actividad heredada con planificaciones o avances autorizados se presenta en forma neutral; el detalle de los avances se consulta en T5; la fecha del último avance y el estado actual solo si están autorizados; `sin_estado_al_corte` como contador separado; no renombrar campos de los contratos) e implementar el historial de una actividad con proyecciones seguras, sin tocar Flutter. El mismo mensaje incluyó la decisión sobre AWS (Prompt 22).
- **Resultado:** `eea40bc` (`feat(m4): historial autorizado de actividades del equipo (M4-T5) - EQ`): `GET /api/v1/equipo/actividades/{actividad_id}`, sin migración y sin cambios en la política de M1; 13 pruebas nuevas y una regresión focalizada de 821 superadas y 1 omitida (plan de M4).
- **Corrección humana a la IA:** el estado actual rellenaba un campo cuando no había estado al corte; se corrigió siguiendo la indicación. En el cierre, la persona pidió revisar `registrado_en`, `modificado_en`, `es_reactivacion` e identificadores antes de exponerlos: los avances solo llevan fecha laboral, estado, descripción y motivo de bloqueo.

### Prompt 22 — Decisión de integración futura con AWS Bedrock y Lambda (PROMPT ORIGINAL, fragmento)

- **Clasificación:** PROMPT ORIGINAL (fragmento literal). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Texto literal** (párrafo incluido en el mensaje de cierre de M4-T4): «Decisión futura para M5: la IA utilizará Amazon Bedrock y AWS Lambda. Registra esta decisión como confirmada para planificación futura, sin implementar ni configurar AWS todavía. No selecciones modelo, región ni servicios adicionales sin la revisión SDD de M5.» Un mensaje posterior (cierre de M4-T5) la ratificó: Amazon Bedrock como servicio de modelos, AWS Lambda para la integración y AWS como plataforma de infraestructura relacionada, con modelo, región, retención y servicios adicionales **abiertos**, y pidió un commit documental independiente.
- **Resultado:** commit `6fbb1fb` (`CLAUDE.md`, ADR-003 y `alcance-mvp.md`). Estado: **CONFIRMADO** solo para planificación futura; **ABIERTO** el resto (PA-09 resuelto en parte).
- **Después:** el 2026-11-18 la persona responsable aplazó esta arquitectura con el ajuste de M5-T5 (Prompt 32); ADR-003, sección 20, lo registra. No se implementó ni configuró nada de AWS.

### Prompt 23 — M4-T6: 403 sobre registros visibles ajenos y auditoría del supervisor

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Apruebo técnicamente M4-T5 según el informe entregado, con las precisiones indicadas.» · «Implementar exclusivamente M4-T6.»
- **Prompt (resumen fiel):** consolidar M4-T5, consolidar por separado las decisiones documentales de M5 (solo `CLAUDE.md`, ADR-003 y `alcance-mvp.md`, sin implementar AWS) e implementar el 403 uniforme sobre registros visibles ajenos en las operaciones de escritura de M2 y M3, y la consulta de auditoría para el supervisor (CA-111), con el mismo 404 para lo no visible o inexistente.
- **Resultado:** `0df881d` (`feat(m4): permisos de escritura y auditoria del supervisor (M4-T6) - EQ`): seis operaciones de M2 y M3 modificadas y M3-07 ampliada; 8 pruebas nuevas, 7 antiguas actualizadas a propósito (fijaban el 404 provisional) sin debilitar aserciones, y una regresión focalizada de 1370 superadas.
- **Alerta de la IA, resuelta por la persona:** los contratos de M3-03 a M3-06 solo decían «Propietaria» pero listaban `OPERACION_NO_PERMITIDA`; apliqué el 403 según las convenciones y lo documenté. La persona pidió distinguir la visibilidad neutral de una referencia de la autorización para identificar un recurso de escritura y no cambiar la respuesta sin fundamento contractual (resuelto en M4-T7 como D-M4-10).

### Prompt 24 — M4-T7: lectura entre compañeros e histórico en Flutter, con el contrato M4-05

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «M4-T6 queda aprobado técnicamente según el informe, sujeto a las comprobaciones contractuales indicadas.»
- **Prompt (resumen fiel):** consolidar M4-T6, completar el contrato y el backend mínimo M4-05 (listado de integrantes vigentes, solo identificador, nombre y rol, reutilizando la política de M1) como prerrequisito, e implementar en Flutter la lectura de la bitácora de un compañero y el histórico por fechas, sin política de permisos en el cliente, con estado solo en memoria y pruebas.
- **Resultado:** `5b703b9` (`feat(m4): listado de integrantes y consultas historicas en Flutter (M4-T7) - EQ`): M4-05 con 5 pruebas, 25 pruebas nuevas de Flutter, `flutter analyze` limpio y un recorrido real en Chrome de 15 comprobaciones (plan de M4).
- **Decisión humana (cierre):** D-M4-10 confirmada: una referencia neutral o mínima no es visibilidad completa del recurso de una escritura, así que se mantiene el 404, y el 403 solo si el recurso es visible según la política; no declarar completo CA-193 sin evidencia y conservar la limitación del selector (no incluye a quienes salieron del equipo).

### Prompt 25 — M4-T8: supervisión del equipo en Flutter

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Implementar exclusivamente M4-T8 — Flutter: supervisión del equipo.»
- **Prompt (resumen fiel):** consolidar M4-05 y M4-T7 y registrar D-M4-10; implementar la vista del supervisor (estado al corte frente al actual, motivo de inclusión, totales y contador aparte, formas completa, neutral y referencia mínima, historial de una actividad y auditoría), sin rankings ni puntuaciones, sin nueva política de permisos en Flutter, sin rutas nuevas de backend y sin ampliar M4-05.
- **Resultado:** `28408e2` (`feat(m4): pantallas de supervision historial y auditoria Flutter (M4-T8) - EQ`): sin cambios de backend ni de contratos; 24 pruebas nuevas de Flutter y un recorrido real en Chrome de 28 comprobaciones con personas trasladadas en ambos sentidos (plan de M4).
- **Decisión humana:** no implementar política de permisos en el cliente; si el servidor omite el estado al corte, la tarjeta muestra «No disponible» y el cliente no lo infiere.

### Prompt 26 — M4-T9: validación integral y cierre técnico de M4

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (dos mensajes: encargo y aprobación). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Ejecutar M4-T9: validación integral y cierre técnico del módulo M4.» · «Apruebo M4-T9 con reservas documentadas.»
- **Prompt (resumen fiel):** consolidar M4-T8; reconciliar la matriz de trazabilidad con los criterios relacionados; una regresión general única (por ser cierre de módulo), un recorrido real integral y revisión de accesibilidad, rendimiento, migraciones y seguridad, sin mutaciones masivas y **sin reescribir requisitos aprobados para que coincidan con la implementación**.
- **Resultado:** `192fe17` (`fix(m4): limpiar datos al perder autorizacion y ampliar evidencia (M4-T9) - EQ`) y `2c45ba5` (`docs(m4): cierre tecnico matriz y evidencias (M4-T9) - EQ`): [matriz de M4](docs/evidencia/matriz-trazabilidad-m4.md) con 61 criterios (59 implementados y probados y 2 parciales, CA-19 y CA-20, por los informes de M5), regresión de backend de 2987 superadas y 1 omitida, 706 de Flutter y recorrido real de 25 comprobaciones. **M4 cerrado con reservas.**
- **Error de la IA, corregido (defecto real):** tras un 403 o un acceso desactivado al repetir una consulta idéntica, tres pantallas conservaban los datos cargados antes; se corrigió con pruebas escritas antes de la corrección. Otros fallos del recorrido eran de mis guiones.
- **Decisión humana:** aprobó el cierre con reservas, confirmó la corrección de pérdida de autorización y ordenó los dos commits con staging explícito.

### Prompt 27 — M5-T0: análisis SDD y planificación del módulo de informes con IA

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (texto íntegro en el historial local; no se reproduce). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal del título y de la autorización:** «# SMARTWORK — Cierre definitivo de M4 e inicio de M5-T0» · «Apruebo M4-T9 con reservas documentadas» · «No autorizo implementar M5-T1 todavía.»
- **Prompt (resumen fiel, no el original):** consolidar M4-T9 en dos commits locales y analizar M5 con el método SDD sin implementar nada: fuentes de verdad, alcance funcional, arquitectura AWS propuesta sin configurarla, seguridad y privacidad, plan de tickets y decisiones para aprobar; sin chatbots, RAG ni rankings, sin convertir en requisito las decisiones abiertas (modelo, región, retención, servicios adicionales) y sin commit del documento de análisis.
- **Resultado:** M4-T9 en `192fe17` y `2c45ba5`. El análisis (38 criterios propios, 11 faltantes de contrato, 13 riesgos, 8 tickets y las decisiones D-M5-01 a D-M5-09) está en el [plan de M5](docs/backlog/tickets/m5-plan-implementacion.md), que entró al repositorio con M5-T1 (`1ad5463`); M5-T0 no tiene commit propio.
- **Decisiones humanas** (plan, sección 12): aprobadas D-M5-01 (entonces, FastAPI → Lambda síncrona → Bedrock), D-M5-02 (403 frente a 404), D-M5-03 (en principio), D-M5-05, D-M5-07, D-M5-08 (datos reales condicionados) y D-M5-09; D-M5-04 y D-M5-06 quedaron pendientes de detalle.

### Prompt 28 — M5-T1: núcleo determinista del informe individual

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (dos mensajes: aprobación de M5-T0 con el encargo, y finalización con la corrección de P-9). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Apruebo el análisis SDD de M5-T0 y autorizo comenzar exclusivamente M5-T1: núcleo determinista del informe individual.»
- **Prompt (resumen fiel):** precisar primero el contrato, implementar un servicio interno sin rutas, sin generador, sin AWS y sin persistencia, con seis agregaciones deterministas y pruebas proporcionadas sobre PostgreSQL desechable; en el segundo mensaje, cerrar las definiciones, corregir lo señalado y, si pasaban las comprobaciones, consolidar T1 y empezar T2.
- **Resultado:** `1ad5463` (`feat(m5): nucleo determinista de informe individual (M5-T1) - EQ`): 16 pruebas del individual y 76 de regresión focalizada, según el plan.
- **Decisiones humanas:** definiciones de las seis métricas; una planificación sin avances no cuenta; P-10 como nueva pregunta.
- **Error de la IA, corregido por la persona responsable:** implementé la visibilidad con «perteneció alguna vez al equipo vigente» (P-9), lo que revelaba relaciones históricas; la persona lo rechazó y se corrigió a visibilidad efectiva en el período, con 404 uniforme y una prueba de equivalencia con la política de M1.

### Prompt 29 — M5-T2: núcleo determinista del informe consolidado

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (el encargo está dentro del mensaje de T1; el cierre y las decisiones, en el siguiente). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Apruebo técnicamente M5-T2 según la evidencia entregada y autorizo consolidarlo en un commit local.»
- **Prompt (resumen fiel):** núcleo determinista del consolidado del equipo reutilizando la autorización histórica, solo con personas con avances autorizados, sin rankings, sin IA ni AWS.
- **Resultado:** `a89e9d2` (`feat(m5): nucleo determinista de informe consolidado (M5-T2) - EQ`): 13 pruebas del consolidado y 71 con las de T1 y visibilidad (plan, sección 15).
- **Decisiones humanas:** P-10 confirmada; C-1 a C-6 (borrador M5-02 0.2, solo personas con avances, orden alfabético con desempate, jornadas del equipo como fechas distintas, trabajo de la supervisora según su pertenencia, rol antes que equipo) y D-M5-04 (catálogo de seis métricas) confirmadas; D-M5-06 sigue abierta.

### Prompt 30 — M5-T3: interfaz interna de generación, validación y fallos

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Después, autorizo comenzar exclusivamente M5-T3: interfaz interna de generación, validación de respuestas y tratamiento de fallos con generador simulado.»
- **Prompt (resumen fiel):** definir la interfaz interna con el generador, una validación determinista de su salida (estructura, referencias, cifras, fechas, alias y contenido no admitido), la clasificación de los fallos y los límites de contexto, con un generador simulado, sin red ni AWS.
- **Resultado:** `ac74c5b` (`feat(m5): interfaz interna de generacion y validacion de informes (M5-T3) - EQ`): 25 pruebas de generación y 96 con las anteriores (plan, sección 17); contrato interno en `docs/api/m5-integracion-ia.md`.
- **Decisiones humanas:** D-M5-06, valores **CONFIRMADOS**: 31 días, 400 hechos como total por solicitud, 0 reintentos de validación y generación desactivada por defecto; tokens, plazo y concurrencia, **ABIERTOS**. P-11 confirmada solo para el contrato interno.
- **Correcciones a mis propuestas:** propuse 400 hechos «por llamada o por persona» y un reintento; la persona fijó 400 en total por solicitud y cero reintentos.

### Prompt 31 — M5-T4: endpoints y respuestas públicas, y resolución contractual

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (tres mensajes). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Autorizo exclusivamente completar M5-T4, cerrar el esquema público y comprobar los endpoints reales con el generador simulado.» · «Apruebo las decisiones pendientes P-6, P-13 y los nombres de los campos del esquema público.»
- **Prompt (resumen fiel):** exponer `POST /api/v1/informes/individuales` y `/consolidados` con la generación desactivada por defecto y solo el generador simulado en pruebas; resolver primero las diferencias contractuales; cerrar el esquema público, registrar las rutas en la aplicación real y comprobar la evidencia HTTP; no declarar T4 cerrado mientras P-6 siguiera pendiente.
- **Resultado:** `f88f6b8` (`feat(m5): endpoints y respuestas publicas de informes (M5-T4) - EQ`): contratos M5-01 y M5-02 versión 0.2 aprobados; pruebas HTTP y recorrido real con uvicorn (plan, secciones 19 a 21).
- **Decisiones humanas:** P-3, P-5, P-11 y P-12 confirmadas; P-6 confirmada como declaración fija de producto («Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.»); P-13 y los nombres del esquema confirmados; P-8 sigue parcial.
- **Hallazgos de la IA:** verifiqué RF-87 y concluí que fija la obligación pero no el texto, por lo que propuse una redacción en lugar de citarlo; en la primera parte detuve la presentación pública en lugar de inventar un esquema provisional, como se pidió.

### Prompt 32 — M5-T5: ajuste a Ollama local (adaptador de generación)

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (mensaje corto cuyo texto íntegro está en el historial local; la parte relevante se cita). **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Debido a las restricciones actuales de Amazon Bedrock Agents Classic, vamos a continuar el desarrollo de SMARTWORK con Ollama local.» · «La decisión de utilizar Amazon Bedrock y AWS Lambda como arquitectura futura se conserva, pero queda aplazada. No implementar ni configurar AWS en este ticket.»
- **Prompt (resumen fiel):** implementar un adaptador de generación con Ollama local detrás de la interfaz existente, con solo destinos locales, parámetros explícitos, sin fallback silencioso, sin registrar prompts ni respuestas, generación desactivada por defecto, pruebas con transporte simulado y una prueba real opcional con datos ficticios.
- **Resultado:** `d411a76` (`feat(m5): adaptador local de generacion con Ollama (M5-T5) - EQ`): 45 pruebas del adaptador y regresión focalizada de 679 superadas y 6 omitidas; Ollama pasa a ser el proveedor confirmado **para el desarrollo local**. Prueba real con datos ficticios: `qwen2.5:3b-instruct`, 1 de 3 individuales aceptado y consolidado rechazado; `qwen3:8b`, 1 intento aceptado en 229 s (plan, sección 22).
- **Decisiones humanas** (mensaje de cierre de T5): aprobado con reservas de calidad, confiabilidad y rendimiento; no cambiar el modelo predeterminado; no autorizar datos reales; no subir los reintentos; el 1 de 3 es evidencia exploratoria, no una tasa generalizable.
- **Hallazgos de la IA:** una prueba de importaciones de red de T3 prohibía `urllib`, que usa el validador de destinos; se afinó para permitir solo `http.client` y se repitió la regresión. El texto aceptado con el modelo pequeño citaba una orden maliciosa sin ejecutarla: riesgo residual declarado.
- **Límite de evidencia:** no hay un mensaje de la persona responsable sobre las restricciones de Bedrock anterior al de este ajuste; el motivo consta solo en su texto y en ADR-003.

### Prompt 33 — M5-T6: interfaz Flutter de informes individuales y consolidados

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-18 · **Herramienta:** Claude Code
- **Cita literal:** «Implementar exclusivamente M5-T6 — Interfaz Flutter de informes individuales y consolidados.» · «No avances a M5-T7 sin aprobación.»
- **Prompt (resumen fiel):** reutilizar la arquitectura Flutter existente; informe individual (propio o de una persona autorizada) y consolidado de supervisión; estados de generación sin progreso inventado, sin datos, límites y fallo, con reintento solo manual; sin política de autorización en Flutter, sin almacenamiento persistente, texto generado como texto plano, sin cambiar timeouts globales; pruebas, recorrido real en Chrome con el simulado y documentación de la incompatibilidad del HTTP síncrono para M5-T7.
- **Resultado:** `827e5dd` (`feat(m5): interfaz Flutter de informes individuales y consolidados (M5-T6) - EQ`): 33 pruebas de informes y 739 en la suite completa de Flutter, `flutter analyze` limpio y recorrido en Chrome con el generador simulado (plan, sección 23).
- **Decisión humana:** no declarar M5 cerrado; no inventar progreso; documentar límites en lugar de resolverlos.
- **Hallazgo de la IA, corregido:** con `SelectableText` la narrativa no se exponía a las tecnologías de apoyo de Flutter Web; se sustituyó por `Text` dentro de `SelectionArea`.

### Prompt 34 — M5-T7: evaluación controlada de Ollama local

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (más tres mensajes breves de la persona responsable durante la ejecución). **Fecha:** 2026-11-18 y 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «Ejecutar M5-T7 como evaluación controlada de Ollama local.» · durante la ejecución: «dejalo asi, con los que sirven esta bien el test, no quiero mas pruebas».
- **Prompt (resumen fiel):** evaluar Ollama con datos ficticios por etapas (una verificación inicial por modelo y una ampliación condicionada), midiendo aceptación del validador, tiempos y calidad, sin cambiar contratos, validador, límites confirmados ni configuración; recomendar valores para los parámetros abiertos sin confirmarlos; documentar y no hacer commit.
- **Resultado:** `638c4a1` (`test(m5): evaluacion parcial de calidad y rendimiento Ollama (M5-T7) - EQ`): solo la etapa A. `qwen2.5:3b-instruct`: 1 de 5 individuales aceptados y consolidado rechazado (14 a 33 s). `qwen3:8b`: 3 de 5 aceptados (155 a 285 s por informe, promedio aproximado de 206 s) y consolidado no ejecutado. Sin etapa B, sin HTTP real con Ollama, sin concurrencia y sin `gpt-oss`. **Muestra exploratoria: no permite extrapolar tasas.** Veredicto: experimental, no apto todavía para uso habitual (plan, sección 24).
- **Decisiones humanas:** detener la evaluación y no completar lo suspendido; los 1024 tokens, 360 s y concurrencia 1 son propuestas de evaluación, no límites; P-14 aprobada como necesidad, pendiente de esquema; la ejecución asíncrona sigue sin autorizar.
- **Hallazgos de la IA:** la prueba de evaluación se habilitaba con la misma variable que la real de T5 (corregido con una variable propia); `qwen2.5:3b-instruct` convirtió órdenes maliciosas en hechos y emitió una valoración, sin que el validador lo detectara; `qwen3:8b` inventó un porcentaje y asumió un año (el validador los rechazó); la corrida se interrumpió una vez por el cierre de la sesión y otra porque el PostgreSQL desechable no estaba levantado.

### Prompt 35 — M5-T8: revisión técnica y contractual final de M5

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL (dos mensajes: encargo y aprobación). **Fecha:** 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «M5-T8 queda aprobado como CIERRE TÉCNICO CON RESERVAS.»
- **Prompt (resumen fiel):** consolidar T7; revisar M5 separando núcleo determinista, API, interfaz, adaptador y calidad real; matriz de los 38 criterios propios con estados reales y evidencia; reconciliar CA-19, CA-20 y CA-05; distinguir el cierre del desarrollo, el cumplimiento de los criterios del MVP y la habilitación para producción; documentar los controles necesarios para un modelo real; sin nuevas inferencias, sin mutaciones y sin commit de T8 sin aprobación.
- **Resultado:** `72ceaad` (`docs(m5): cierre tecnico matriz y reservas (M5-T8) - EQ`) y la [matriz de M5](docs/evidencia/matriz-trazabilidad-m5.md): **M5 cerrado técnicamente con reservas**; 34 criterios implementados y probados y 4 parciales (CA-161, CA-163, CA-166 y CA-224). Regresión completa de backend: 3139 superadas y 13 omitidas.
- **Decisiones humanas:** el veredicto, los estados de los criterios y las reservas; ninguna propuesta se convirtió en confirmada por cerrar el módulo.

### Prompt 36 — FINAL-T1: auditoría de preparación para entrega

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «Objetivo: realizar una auditoría final del repositorio para determinar si SMARTWORK está listo para su entrega académica.»
- **Prompt (resumen fiel):** auditar en solo lectura la documentación, la reproducibilidad, las condiciones de entrega y Git, y proponer una demostración con datos ficticios; clasificar los hallazgos en BLOQUEANTE PARA ENTREGA, NECESARIO ANTES DE ENTREGA y MEJORA POSTERIOR; sin modificar archivos, sin commit ni push.
- **Resultado:** sin commit y sin archivo en el repositorio (el informe se entregó en la sesión). Veredicto: técnicamente listo para demostrarse, pero el repositorio no estaba listo para entregarse: `readme.md` obsoleto, commits locales sin publicar y condiciones oficiales de entrega no verificables.
- **Decisión humana:** aprobó el informe y autorizó solo FINAL-T2.

### Prompt 37 — FINAL-T2: actualización del README y guía de instalación

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «Autorizo exclusivamente FINAL-T2: actualizar el README y las instrucciones de instalación y ejecución.»
- **Prompt (resumen fiel):** reescribir `readme.md` con el estado real de M1 a M5, la instalación verificada por lectura, una sección por módulo, la situación real de la IA (generador simulado, Ollama experimental, AWS aplazado, generación desactivada, datos reales no autorizados) y las cifras documentadas; marcar la plataforma, la rama y la fecha de entrega como pendientes de contraste con el enunciado oficial; sin código, sin ejecutar Ollama y sin instalación limpia.
- **Resultado:** `9852646` (`docs(final): actualizar README y guia de instalacion (FINAL-T2) - EQ`): solo `readme.md`; 0 enlaces relativos rotos y 0 anclas sin encabezado, verificados con un script; instalación limpia **no** ejecutada y limitación de la provisión de roles para `smartwork_dev` declaradas.
- **Decisión humana:** aprobó el informe y autorizó el commit y FINAL-T3, conservando las advertencias de reproducibilidad.

### Prompt 38 — FINAL-T3: completar y organizar este registro

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code y dos subagentes de lectura
- **Cita literal:** «Ejecutar FINAL-T3 para completar y organizar `prompts.md`.» · «Dejar los cambios de FINAL-T3 sin confirmar.»
- **Prompt (resumen fiel):** completar la trazabilidad de M4-T5 a M4-T9, M5-T0 a M5-T8, FINAL-T1 y FINAL-T2 sin reconstruir mensajes inventados, clasificando cada entrada por su evidencia; mantener los estados CONFIRMADO, PROPUESTO y ABIERTO; explicar los límites de la IA generativa; sin tocar código ni otros documentos. Después pidió usar dos agentes distintos para recuperar la evidencia.
- **Resultado:** esta sección. Dos subagentes de solo lectura recuperaron de los commits, los documentos y el historial local la evidencia de M4-T5 a M4-T9 y de M5 a FINAL-T2; yo redacté el documento y lo verifiqué. **Sin commit** (los cambios quedan sin confirmar a la espera de revisión).

### Prompt 39 — Rediseño visual UX-T1 a UX-T4

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «Implementar UX-T3 "panel lateral Nueva actividad" reutilizando `SidePanel`» · «Rediseñar exclusivamente el Panel principal de SMARTWORK.»
- **Prompt (resumen fiel):** unificar el sistema de diseño, reorganizar la navegación y el panel lateral, implementar «Nueva actividad» como panel lateral (planificada y no planificada, una sola pregunta al descartar cambios, idempotencia, refresco tras guardar) y rediseñar el Panel principal con indicadores por estado actual, sin cambiar backend, contratos, reglas, permisos ni estados.
- **Resultado:** commits locales `bcc494d` (UX-T1), `987f148` (UX-T2), `6cef7bc` (UX-T3) y `c7c1327` (UX-T4). Verificación: pruebas de widget, `flutter analyze`, 39 comprobaciones HTTP con FastAPI y PostgreSQL desechable y comprobación visual en Chrome con datos ficticios.
- **Decisión humana:** aprobó cada ticket, resolvió D-UX-11 (el foco permanece en el selector de tipo) y D-UX-12 (la entrada «Planificación» abre el panel en modo planificado).

### Prompt 40 — Rediseño visual UX-T5 a UX-T9

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code y tres subagentes de implementación (uno por bloque de pantallas)
- **Cita literal:** «Autorizo consolidar UX-T4 e implementar UX-T5, UX-T6, UX-T7, UX-T8 y UX-T9 de manera consecutiva.»
- **Prompt (resumen fiel):** rediseñar Mi bitácora, Actividades y planificación, Mi equipo, Supervisión e Informes con el mismo sistema visual y validar de forma integral (una sola regresión completa), conservando contratos, permisos, validaciones, idempotencia, protección de cambios sin guardar y, en M5, las etiquetas CALCULADO, REGISTRADO y REDACTADO CON IA, el informe efímero y la IA desactivada por defecto.
- **Resultado:** commit local `68602ef`; 1062 pruebas de Flutter superadas y 149 focalizadas posteriores. Los subagentes trabajaron en carpetas disjuntas y su informe se verificó contra el código y las pruebas antes de integrarlo; una desviación (Mi equipo no cargaba al elegir a la persona) se corrigió en la integración.
- **Decisión humana:** aprobó el resultado reportado y autorizó el cierre.

### Prompt 41 — Cierre del rediseño y preparación final

- **Clasificación:** RECONSTRUCCIÓN DOCUMENTAL. **Fecha:** 2026-11-19 · **Herramienta:** Claude Code
- **Cita literal:** «Objetivo: consolidar el rediseño, completar la documentación indispensable y preparar SMARTWORK para su publicación final.»
- **Prompt (resumen fiel):** actualizar solo la documentación necesaria (README, `CLAUDE.md`, matrices, referencia obsoleta a `UnplannedPage`), preparar una guía de demostración con el generador simulado, verificar la instalación en una base desechable y conservar capturas finales, sin push ni datos reales.
- **Resultado:** commit del rediseño y commit de documentación local; instalación limpia y recorrido real verificados en un clon con PostgreSQL desechable (ver README, sección 1.4). El generador simulado no se presenta como inteligencia artificial.
- **Decisión humana:** pendiente de revisión; el push y la publicación no están autorizados todavía.

---

## 12. Límites del uso de IA generativa en este proyecto

**Cómo se usó Claude Code.** Para analizar (lectura de contratos, criterios y reglas y detección de brechas), proponer (diseños, decisiones con alternativas y recomendación), implementar ticket a ticket, probar (pruebas focalizadas, recorridos reales en Chrome con bases desechables) y documentar (planes, matrices de trazabilidad, README y este registro). El método fue siempre el mismo: una persona responsable aprobaba o rechazaba cada paso por escrito antes de avanzar, y la IA informaba qué hizo, qué verificó y qué no pudo verificar.

**Lo que la IA no decidió.** Ninguna decisión de producto: alcance, reglas de negocio, estados de actividad, permisos, contratos de la API ni límites operativos se confirmaron sin aprobación expresa. Las propuestas se marcaron `[PROPUESTO]` y las dudas `[ABIERTO]`; solo lo aprobado se escribió como `[CONFIRMADO]` (por ejemplo, los 31 días, los 400 hechos por solicitud y los cero reintentos de validación de M5, o la declaración fija de base de los informes). Cerrar un módulo no convirtió en confirmada ninguna propuesta.

**Errores de la IA que la verificación detectó.** Afirmó un cumplimiento que no había comprobado (el formato de los criterios); escribió pruebas vacuas o mal planteadas; propuso reglas de visibilidad que revelaban relaciones históricas (P-9 en M5-T1); expuso un hash en un registro de error (M1-T8.6); dejó pantallas con datos de una consulta anterior tras perder la autorización (M4-T9); y citó nombres de prueba de memoria que no existían. Todo se corrigió al ejecutar las comprobaciones, y no se debilitó ninguna comprobación para que pasara. Hay un detalle por entrada en la sección 8 y en las secciones 10 y 11.

**Límites de este registro.**

- Los prompts son resúmenes fieles y no transcripciones, salvo los dos marcados como PROMPT ORIGINAL; los textos íntegros están en el historial local de Claude Code, que no forma parte del repositorio. No se reconstruyó ningún texto que no pudiera comprobarse.
- Las cifras de pruebas citadas provienen de los documentos y commits del repositorio; las que constan solo en un informe de la sesión se señalan como tales.
- ChatGPT se usó de forma complementaria sin registro de modelo ni de prompts: no se reconstruyen.

**Límites de la IA del producto (M5).** Un modelo de lenguaje puede afirmar lo que el registro no dice, valorar a una persona, citar o convertir en hechos las instrucciones escritas en un texto libre y redactar con torpeza; el validador determinista (estructura, referencias, cifras, fechas y contenido no admitido) **no** garantiza fidelidad ni ausencia de valoraciones. En la evaluación parcial con datos ficticios, con `qwen2.5:3b-instruct` 1 de 5 informes individuales fue aceptado y con `qwen3:8b`, 3 de 5, tardando de 155 a 285 segundos cada uno: **muestras exploratorias que no permiten extrapolar tasas de éxito**. Por eso la narrativa de IA es experimental, está desactivada por defecto y no se autoriza el uso de datos laborales reales con un modelo de lenguaje (ver [README](readme.md#15-inteligencia-artificial-en-m5) y [matriz de M5](docs/evidencia/matriz-trazabilidad-m5.md)). El generador simulado no es un modelo de lenguaje, y Amazon Bedrock y AWS Lambda son una arquitectura futura aplazada de la que no se ha configurado nada.
