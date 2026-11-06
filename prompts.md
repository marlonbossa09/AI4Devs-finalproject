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

---

## 0. Herramientas, modelos y contexto

### Fuentes y herramientas de apoyo

- **Material del curso AI4Devs:** base de referencia para aplicar las metodologías y los conocimientos utilizados en SMARTWORK (entre ellos el desarrollo guiado por especificación). Es una fuente de conocimiento; no es autor de ningún documento del producto.
- **Claude Code:** herramienta **principal**. Se usó directamente sobre el repositorio para estructurar la documentación y realizar las verificaciones documentales. Todo el contenido de `docs/`, `readme.md` y este registro se produjo con ella y fue revisado y aprobado por la persona responsable.
- **ChatGPT:** herramienta **complementaria**, usada para analizar propuestas, contrastar decisiones y revisar aspectos del proyecto. No es la herramienta principal ni se le atribuye la autoría del proyecto ni del material del curso. Su uso se declara aquí tal como fue; **no se han conservado el modelo ni los prompts concretos**, por lo que no se reproducen ni se inventan.

### Convención de este registro

Los prompts de las secciones 1 a 6 son **resúmenes** del mensaje original, no transcripciones literales; así se indica en cada uno («resumen fiel»). Ninguno es una transcripción literal. Los mensajes completos y las respuestas están en el historial local de Claude Code, que no forma parte del repositorio.

### Herramientas y modelos

| Herramienta | Modelo | Uso real |
|---|---|---|
| **Claude Code** (extensión para VS Code) | `claude-sonnet-5-5` (la inmensa mayoría de los mensajes de la sesión) y `claude-opus-5-5` (4 mensajes; la transcripción no registra para qué tarea) | Alcance, requisitos, historias, arquitectura, modelo de datos, contratos de la API, tickets, README y este registro |
| Agentes de lectura web de Claude Code y búsqueda web | Los de la propia herramienta | Contrastar datos externos (precios, retención y regiones del proveedor de IA candidato, valores de seguridad de NIST y OWASP) para los ADR |
| Conector de Google Drive de Claude | — | Búsqueda de documentación de apoyo; no aportó contenido utilizable y no se incorporó nada al repositorio |
| Scripts de Python escritos por la IA, ejecutados en la sesión | — | Verificar la documentación (formato de los criterios, trazabilidad, coherencia entre documentos). No forman parte del repositorio |
| **ChatGPT** (complementaria) | No registrado | Análisis de propuestas, contraste de decisiones y revisión de aspectos del proyecto. Sin registro de modelo ni de prompts; no se reconstruyen |

### Contexto avanzado

- **`CLAUDE.md`** ([CLAUDE.md](CLAUDE.md)): reglas de trabajo cargadas en cada sesión. Fijan la metodología (primero el alcance, luego el PRD, las historias, el backlog y la arquitectura), los estados de toda decisión (`[CONFIRMADO]`, `[PROPUESTO]`, `[ABIERTO]`, `[SUPUESTO]`), la prohibición de implementar lo no especificado, la aprobación previa para cambiar el alcance, la trazabilidad y las reglas de la IA del producto (nada inventado, fallo explícito). Se creó con autorización expresa de la persona responsable.
- **Modo de planificación** de Claude Code: la IA presentó un plan antes de escribir cualquier archivo y la persona responsable lo aprobó o rechazó.
- **Aprobación por pasos:** cada fase terminó con una revisión humana antes de pasar a la siguiente; ninguna decisión se convirtió en requisito sin aprobación expresa.
- **Restricciones repetidas en cada petición:** sin código, sin dependencias, sin commits ni pushes, y la rama de trabajo no se cambia.
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

Todavía no hay pull requests ni commits de esta fase: el trabajo vive en la rama `feature/entrega-1-eq`. Se documentarán al implementar el flujo principal.

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

**Errores de la IA, detectados y corregidos**

- Afirmó que todos los criterios cumplían el formato sin comprobar el `CUANDO` (sección 5).
- Sus propios scripts de verificación tuvieron fallos de implementación (cadenas mal construidas, llaves sin escapar en plantillas, referencias de decisión combinadas en una celda) que se detectaron al ejecutarlos y se corrigieron antes de dar nada por válido.
- No pudo verificar el precio de Bedrock ni algunas cifras de OWASP; lo declaró en los ADR en lugar de estimarlo.

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
| Implementación | **Planificado** | Claude Code con los tickets, los contratos y los criterios como contexto; implementación guiada por los criterios de aceptación |
| Pruebas | **Planificado** | Pruebas de aceptación derivadas de los criterios, matriz de permisos y pruebas de seguridad de ADR-002 |
| Revisión de código | **Planificado** | Revisión asistida de cada pull request |
| Producto (M5) | **Planificado, condicionado** | Informes con un servicio de IA, solo tras decidir proveedor, retención, región y marco legal (ADR-003) |
