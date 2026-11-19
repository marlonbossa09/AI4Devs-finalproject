# SMARTWORK — Resumen del proyecto

| Campo | Contenido |
|---|---|
| **Naturaleza** | Resumen informativo del estado real. No define requisitos: los requisitos viven en `docs/producto/`, `docs/backlog/` y `docs/api/` |
| **Fecha** | 2026-11-19 |
| **Autoría** | Edwin Quintana |
| **Estado** | MVP completo en lo funcional (M1 a M5), **no habilitado para producción** y sin despliegue |

## 1. Objetivo

SMARTWORK es una plataforma web para registrar y consultar bitácoras laborales. Sustituye la comunicación informal de actividades diarias por mensajería, que pierde información, dificulta consultar antecedentes y obliga a elaborar los informes a mano. Permite registrar qué se planea, qué se hizo realmente, qué quedó pendiente y qué bloqueos hubo, con auditoría de toda corrección y con informes que se apoyan solo en los registros almacenados. No es una herramienta de evaluación del desempeño: no tiene rankings ni valoraciones de personas.

## 2. Arquitectura

- **Cliente:** Flutter Web, en español, responsive (escritorio, tableta y móvil), con un sistema visual unificado (tokens de diseño, barra lateral, panel lateral «Nueva actividad» y componentes compartidos).
- **API:** FastAPI (Python 3.13) como monolito modular, con la autorización centralizada en el backend. Sirve también el cliente compilado, en el mismo origen.
- **Datos:** PostgreSQL con 18 migraciones (0001 a 0018) escritas a mano; dos roles con privilegios mínimos (propietario para migraciones y aplicación sin DDL).
- **Sesión:** cookie de servidor con protección CSRF y de origen, y control de intentos de acceso.
- **Informes:** núcleo determinista que calcula las cifras y valida cualquier texto; un generador opcional de narrativa detrás de una interfaz propia.

Decisiones y alternativas: [ADR-001](../arquitectura/adr/ADR-001-stack-tecnologico.md), [ADR-002](../arquitectura/adr/ADR-002-autenticacion-y-acceso.md), [ADR-003](../arquitectura/adr/ADR-003-integracion-de-ia.md) y [arquitectura general](../arquitectura/arquitectura-general.md).

## 3. Los cinco módulos y lo implementado

| Módulo | Funcionalidades implementadas |
|---|---|
| **M1** Acceso y equipos | Inicio y cierre de sesión, roles Colaborador y Supervisor, pertenencias a equipos con historial, visibilidad histórica, provisión por línea de órdenes, desactivación de acceso, códigos de primer acceso y recuperación |
| **M2** Registro diario | Bitácora por fecha laboral, resumen libre, planificación de actividades y de sus continuaciones, actividades no planificadas, avances con estado (Pendiente, En progreso, Bloqueada, Completada), detalle y lista de actividades, panel lateral «Nueva actividad» |
| **M3** Seguimiento y auditoría | Cierre y reapertura de la jornada con motivo, corrección de avances, reactivación, marca de actividad registrada por error, auditoría con autor, fecha real, valor anterior y valor nuevo |
| **M4** Consulta histórica y supervisión | Lectura en solo lectura de la bitácora de un compañero, histórico por fechas, vista de supervisión con estado al corte y estado actual diferenciados, historial de actividad y auditoría para el supervisor |
| **M5** Informes | Informe individual y consolidado: cifras calculadas, registros y bloqueos tal como se registraron y narrativa aparte; efímeros (no se guardan ni se exportan); generación desactivada por defecto |

## 4. Estado de las pruebas (ejecuciones documentadas)

| Verificación | Resultado | Fecha |
|---|---|---|
| Backend (`pytest`, suite completa, PostgreSQL desechable) | 3139 superadas, 13 omitidas (pruebas de Ollama real, que requieren una variable explícita), 0 fallos | 2026-11-19, cierre de M5 |
| Frontend (`flutter test`, repositorios en memoria) | 1062 superadas | 2026-11-19, validación del rediseño |
| Frontend, ejecución focalizada posterior | 149 superadas | 2026-11-19 |
| `flutter analyze` | Sin incidencias | 2026-11-19 |
| Instalación limpia y recorrido real (clon limpio, PostgreSQL desechable, FastAPI sirviendo el cliente compilado) | Migraciones hasta 0018, semilla y 35 comprobaciones HTTP de M1 a M5 superadas; recorrido real en Chrome de ambos roles | 2026-11-19, ver [README](../../readme.md#14-instrucciones-de-instalación-y-ejecución) |

Las pruebas de Flutter usan repositorios en memoria y **no sustituyen** a la integración real; por eso se añadió el recorrido real indicado en la última fila.

## 5. Limitaciones y reservas

- **Producción:** no habilitada. No hay despliegue, HTTPS, gestión de secretos ni observabilidad definida (DT-07).
- **M1:** medio de entrega de códigos y verificación de identidad pendientes (PA-12); sin regla para reactivar un acceso desactivado.
- **M4:** cerrado con reservas: mejoras no bloqueantes y riesgos de volumen y despliegue ([matriz de M4](../evidencia/matriz-trazabilidad-m4.md), secciones 12 y 13). Los criterios CA-19 y CA-20 dependían de M5 y se reconciliaron en la matriz de M5.
- **M5:** cerrado técnicamente con reservas: 34 de 38 criterios implementados y probados y 4 parciales (CA-161, CA-163 y CA-166, calidad de la narrativa real; CA-224, el informe de quien ya no integra el equipo). Decisiones abiertas: D-M5-06 (límites de tokens, plazo y concurrencia), P-14 (esquema del motivo del fallo) y PA-09 (proveedor, modelo, región y retención, resuelta en parte). La ejecución asíncrona no está autorizada.
- **Datos reales con un modelo de lenguaje:** no autorizados (D-M5-08).
- **Accesibilidad y navegador:** Flutter Web conserva riesgos conocidos de accesibilidad, carga inicial y pruebas en navegador. No se verificó el teclado virtual en móvil ni lectores de pantalla reales.
- **Tipografías:** se cargan desde Google Fonts al abrir la aplicación (petición externa solo de fuentes).

## 6. Generación de narrativa

| Generador | Estado |
|---|---|
| Ninguno (por defecto) | Un informe sin datos se muestra; uno con datos avisa de que no pudo generarse |
| **Simulado** | Solo desarrollo y pruebas. **No es inteligencia artificial**: escribe plantillas fijas a partir de los hechos. Sirve para demostrar la interfaz de informes |
| **Ollama** local | **Experimental**, solo desarrollo local con datos ficticios. Calidad insuficiente para uso habitual (muestras exploratorias pequeñas que no permiten extrapolar tasas de éxito) |
| **Amazon Bedrock y AWS Lambda** | **Aplazados**: previstos como infraestructura futura, no implementados ni evaluados |

La generación real no debe presentarse como confiable. Un texto aceptado por el validador determinista no es por ello un informe de calidad satisfactoria.

## 7. Requisitos para ejecutar el proyecto

Git, PostgreSQL 16 o superior (probado con 18.4), [uv](https://docs.astral.sh/uv/) (descarga Python 3.13), Flutter 3.35.3 con Dart 3.9.2 y un navegador moderno. Probado en Windows 11 con Git Bash. Instalación paso a paso en el [README](../../readme.md#14-instrucciones-de-instalación-y-ejecución) y recorrido en la [guía de demostración](guia-de-demostracion.md).
