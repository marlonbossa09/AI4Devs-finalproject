# SMARTWORK

Reglas de trabajo para cualquier asistente que colabore en este repositorio. Este archivo no define requisitos del producto: los requisitos viven en `docs/`.

## 1. Visión general del producto

SMARTWORK es una plataforma web para registrar y consultar bitácoras laborales. Sustituye la comunicación informal de actividades diarias por mensajería, que provoca pérdida de información, dificultad para consultar antecedentes y trabajo manual al elaborar informes.

La plataforma permite registrar qué se planea hacer, qué se hizo realmente, qué quedó pendiente y qué bloqueos se presentaron.

SMARTWORK es un producto profesional e independiente. Su documentación describe únicamente el producto, su dominio y su construcción técnica.

Stack: Flutter Web, FastAPI (Python) y PostgreSQL, con monolito modular y autorización centralizada en el backend. `[CONFIRMADO]` mediante el ADR-001 (`docs/arquitectura/adr/ADR-001-stack-tecnologico.md`). La arquitectura técnica de referencia de la autenticación está aprobada (ADR-002, que sigue `[PROPUESTO]` en lo operativo); el mecanismo operativo de la provisión de accesos, el proveedor del servicio de IA (ADR-003, `[PROPUESTO]`) y el despliegue siguen sin decidir.

## 2. Módulos funcionales

El MVP tiene cinco módulos obligatorios:

- **M1** — Autenticación, usuarios y equipos.
- **M2** — Bitácoras laborales híbridas (actividades estructuradas y resumen libre).
- **M3** — Seguimiento de actividades, continuidad entre jornadas y auditoría.
- **M4** — Consulta histórica y supervisión del equipo.
- **M5** — Informes individuales y consolidados asistidos por IA.

Las historias internas pueden descomponerse para facilitar la implementación y las pruebas. Esa descomposición no añade funcionalidades al alcance.

## 3. Metodología: Spec-Driven Development (SDD)

La especificación precede a la implementación. El orden es:

1. Alcance del MVP.
2. Documento de requisitos del producto (PRD).
3. Historias y criterios de aceptación.
4. Backlog y tickets.
5. Arquitectura y decisiones técnicas (ADR).
6. Implementación, verificada contra los criterios de aceptación.

No se pasa a un paso sin que el anterior esté validado por la persona responsable del producto.

## 4. Decisiones: confirmadas, propuestas y abiertas

Todo contenido que afecte al alcance o al comportamiento del producto debe quedar clasificado en uno de tres estados:

- `[CONFIRMADO]`: lo ha aprobado explícitamente la persona responsable del producto. Solo esto puede escribirse como requisito.
- `[PROPUESTO]`: es una sugerencia no aprobada. Se documenta como tal y no se implementa.
- `[ABIERTO]`: es una decisión pendiente. Se registra con el argumento disponible y lo necesario para decidirla.

Los supuestos sin evidencia se marcan `[SUPUESTO]`.

Reglas:
- Una decisión abierta no se convierte en requisito por inferencia, por comodidad ni por defecto.
- Los puntos abiertos vigentes se registran en `docs/producto/alcance-mvp.md` (sección 6.3). Un punto resuelto parcialmente sigue abierto en lo que no se ha resuelto. Permanecen así hasta que se resuelvan por escrito.
- Una propuesta pasa a confirmada solo cuando la persona responsable la aprueba de forma explícita.

## 5. Convenciones de documentación e identificadores

- Idioma: español.
- Se conservan `readme.md` y `prompts.md` con sus secciones relevantes.
- Identificadores:
  - `M1`–`M5`: módulos funcionales.
  - `RF-XX`: requisitos funcionales.
  - `HU-M.N`: historias de usuario (módulo `M`, número `N`; por ejemplo `HU-2.3`).
  - `RN-XX`: reglas de negocio.
  - `RNF-XX`: requisitos no funcionales.
  - `ME-XX`: métricas de éxito.
  - `CA-XX`: criterios de aceptación.
  - `PP-XX`: propuestas pendientes de aprobación.
  - `PA-XX`: puntos abiertos (decisiones pendientes).
- Los criterios de aceptación se redactan como reglas de negocio observables, en formato DADO / CUANDO / ENTONCES. No incluyen rutas de API, códigos de estado ni nombres internos de campos.
- Los requisitos deben ser comprobables. Una frase que no pueda responderse con "se cumple" o "no se cumple" se reescribe.
- No se inventan cifras ni datos de mercado.
- SMARTWORK se describe siempre como un producto de software profesional. Los documentos del producto (alcance, PRD, historias, arquitectura, modelo de datos, API y tickets) no incluyen lenguaje de ejercicio ni proyecto académico, ni condicionan requisitos a factores externos al producto.
- Las referencias a AI4Devs son legítimas solo como fuente real de las plantillas oficiales, del material formativo y del contexto y procedimiento de entrega. Se ubican en `readme.md`, `prompts.md` y este archivo, y no definen ni modifican requisitos.
- El autor indicado en `readme.md` es Edwin Quintana (EQ). En configuraciones, títulos y commits la referencia de autoría es siempre Edwin Quintana.
- No se realizan operaciones Git (rama, commit, push) sin autorización expresa.

## 6. Principios de trazabilidad y seguridad

Trazabilidad:
- Cada requisito, historia, criterio y ticket se rastrea hasta una fuente: una decisión confirmada o un requisito previo.
- Cada ticket indica la historia de la que deriva.
- La auditoría conserva autor, fecha real, operación, valor anterior y valor nuevo. Nunca se sobrescribe ni se borra un registro sin dejar rastro.
- Se distinguen la fecha laboral, la fecha real de registro y la fecha de modificación.

Seguridad y privacidad:
- Las bitácoras contienen información laboral de personas. Se aplica el mínimo privilegio y se evita exponer más datos de los necesarios.
- No se almacenan ni se escriben en documentos credenciales, claves ni datos personales reales.
- Todo envío de registros a un servicio externo (incluido el LLM) es una decisión explícita y documentada. No se asume.

## 7. Prohibición de implementar funcionalidades no especificadas

- No se escribe código, esquema, endpoint ni interfaz para algo que no esté especificado y confirmado.
- No se añaden funcionalidades "por si acaso", ni infraestructura, dependencias, automatizaciones ni configuraciones que ningún requisito confirmado justifique.
- Si algo parece necesario y no está especificado, se registra como `[PROPUESTO]` o `[ABIERTO]` y se consulta.

## 8. Aprobación antes de modificar el alcance

Cualquier cambio al alcance del MVP, a los cinco módulos o a una decisión confirmada requiere aprobación explícita de la persona responsable del producto antes de reflejarse en cualquier documento o código. Se presenta primero el cambio propuesto y su impacto.

## 9. Reglas para la IA del producto (informes asistidos)

- Todo resultado generado por IA debe apoyarse en los registros almacenados.
- Ningún informe afirma hechos que no consten en los registros.
- Si faltan registros suficientes, el informe lo indica explícitamente sin inventar información. Si el servicio de IA falla, se informa de que el informe no pudo generarse y no se presenta contenido parcial como informe completo.
- No se inventan actividades, fechas, personas ni bloqueos.
- Los límites del comportamiento de la IA se documentan solo cuando están decididos. No se describe como existente un comportamiento que no se haya especificado ni verificado.
- Lo mismo aplica al asistente de desarrollo: no se declaran resultados de pruebas, validaciones ni comportamientos que no se hayan ejecutado y comprobado.
