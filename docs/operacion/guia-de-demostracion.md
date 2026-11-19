# SMARTWORK — Guía breve de demostración

| Campo | Contenido |
|---|---|
| **Naturaleza** | Guía operativa. No define requisitos ni modifica ninguna decisión del producto |
| **Fecha** | 2026-11-19 |
| **Alcance** | Recorrido de unos 15 minutos por M1 a M5 sobre un entorno local **desechable** con datos ficticios |
| **Qué no es** | Una demostración de producción: SMARTWORK **no está habilitado para producción** y no tiene despliegue |

## 1. Preparación

1. Instalar siguiendo el [README, sección 1.4](../../readme.md#14-instrucciones-de-instalación-y-ejecución) (pasos 1 a 7). Para una demostración conviene usar una **base de datos propia y desechable** (puede ser un clúster de PostgreSQL aparte, en otro puerto), nunca una base con datos reales ni una compartida.
2. La semilla del paso 5 crea tres personas ficticias y **muestra sus contraseñas una sola vez**; anotarlas. No se guardan ni se versionan.

   | Usuario | Rol | Nombre que se ve |
   |---|---|---|
   | `supervisor.demo` | Supervisor | Sofía Supervisora (demo) |
   | `colaborador1.demo` | Colaborador | Carlos Colaborador (demo) |
   | `colaborador2.demo` | Colaborador | Camila Colaboradora (demo) |

3. **Informes (M5): generador simulado.** Por defecto la generación está desactivada. Solo para esta demostración, en `backend/.env` (con `APP_ENV=development`) poner `INFORME_HABILITADO=true` e `INFORME_GENERADOR=simulado` y reiniciar FastAPI. Al terminar, volver a `false` y `ninguno`.
4. Abrir <http://localhost:8000> (o el puerto elegido). No hace falta ninguna semilla adicional: los datos se crean durante el recorrido con la propia aplicación.

> **Aviso para quien presente.** El generador simulado **no es un modelo de lenguaje ni inteligencia artificial real**: escribe plantillas fijas a partir de los hechos calculados. La pantalla lo etiqueta como «Redactado con IA» porque ese es el contrato de la sección de narrativa; hay que decirlo en voz alta. La generación real (Ollama local) es experimental, no está validada y no debe usarse con datos laborales reales. Amazon Bedrock y AWS Lambda están aplazados y no se usan.

## 2. Recorrido

### M1 — Acceso, roles y equipos (3 min)

1. Iniciar sesión con una contraseña incorrecta: el mensaje no dice si falló el usuario o la contraseña.
2. Entrar como `colaborador1.demo`. En la barra lateral aparecen Panel principal, Mi bitácora, Actividades, Planificación, Mi equipo e Informe individual. **No** aparecen Supervisión ni Informe del equipo.
3. Cerrar sesión y entrar como `supervisor.demo`: ahora sí aparecen Supervisión e Informe del equipo. Los roles y los equipos se crean por una provisión administrativa por línea de órdenes (no hay panel de administración); la semilla ya los dejó creados.

### M2 — Bitácora, actividades y planificación (4 min)

Como `colaborador1.demo`:

1. En **Panel principal**, pulsar **Nueva actividad**. Se abre un panel lateral con dos tipos.
2. **Planificada:** escribir un título («Revisar la propuesta del cliente») y guardar. Se ve el aviso «Estado inicial: Pendiente. Guardar una planificación no registra avances.» El panel se cierra y se permanece en el Panel principal, que ya cuenta la actividad como Pendiente.
3. **No planificada:** pulsar de nuevo **Nueva actividad**, elegir «No planificada», escribir título, estado y descripción («Atender un incidente», En progreso). El estado y la descripción son obligatorios y no hay estado por defecto.
4. Escribir algo en el panel y pulsar **Cancelar**: pregunta una sola vez si se descartan los cambios.
5. Abrir **Mi bitácora**: la fecha laboral y el estado de la jornada (Abierta) están arriba; las actividades, con su filtro Planificadas / No planificadas; el cierre, el resumen y la auditoría, en la columna lateral.
6. En **Actividades**, ver la lista y abrir **Ver detalle** de una actividad.

### M3 — Avances, bloqueos, cierre, reapertura y auditoría (4 min)

1. En una actividad, **Registrar avance** con el estado **Bloqueada**: sin motivo no se acepta; con motivo («Falta el acceso al servidor») se registra y se ve en la actividad y en el Panel principal.
2. En **Mi bitácora**, pulsar **Cerrar jornada** sin resumen: la pantalla explica qué falta. **Escribir resumen**, guardarlo y cerrar la jornada (pide confirmación).
3. Con la jornada cerrada no se admiten avances ni cambios del resumen. **Reabrir jornada** exige un motivo.
4. **Ver auditoría de la jornada**: aparecen el cierre y la reapertura, con su autor y su fecha real.

### M4 — Mi equipo y Supervisión (2 min)

1. Como `colaborador2.demo`, crear una planificación («Tarea de la compañera») y cerrar sesión.
2. Como `colaborador1.demo`, abrir **Mi equipo**, elegir a Camila en la lista: se lee su bitácora **en solo lectura**.
3. Como `supervisor.demo`, abrir **Supervisión**, pulsar **Ver supervisión**: totales por estado al corte y actividades del equipo, con «Estado al corte» y, aparte, «Estado actual». **Ver historial** abre el historial de una actividad. No hay clasificaciones de personas.

### M5 — Informes con generador simulado (2 min)

1. Como `colaborador1.demo`, **Informe individual**, **Generar informe**: tarjeta de **Cálculo** (cifras que calcula el servidor), **Registros** y **Bloqueos** tal como se registraron y, aparte, la **narrativa** (simulada). Se indica la base del informe: solo registros disponibles y autorizados.
2. Como `supervisor.demo`, **Informe del equipo**: cifras del equipo y, por persona, sus registros autorizados, en orden alfabético y sin clasificaciones.
3. Señalar que el informe es efímero (no se guarda ni se exporta) y que, si el generador falla o está desactivado, la pantalla lo dice y no muestra un informe parcial como completo.

## 3. Qué no se puede demostrar desde la interfaz

- La creación de personas y equipos, los traslados y los códigos de primer acceso o recuperación: son órdenes de provisión del servidor (ver el [contrato de M1](../api/m1-acceso-usuarios-equipos.md)). El medio de entrega de códigos sigue pendiente (PA-12).
- Narrativa con un modelo real: no está validada; no se presenta como funcionalidad.
- Despliegue, HTTPS y observabilidad: no existen todavía.

## 4. Al terminar

Volver `INFORME_HABILITADO=false` e `INFORME_GENERADOR=ninguno`, detener FastAPI y, si se creó un clúster de PostgreSQL desechable para la demostración, detenerlo y borrarlo. No quedan datos reales que eliminar: todo era ficticio.
