# SMARTWORK — Contrato interno entre el backend y el generador de narrativa (M5)

| Campo | Valor |
|---|---|
| **Estado** | **`[PROPUESTO]`.** Contrato **interno** (no es público ni lo ve ninguna persona usuaria). Implementado en M5-T3 con un generador **simulado**; no se ha integrado ningún servicio real. **P-11 (2026-11-18): la lista de secciones queda confirmada para este contrato interno.** La estructura **pública** de la narrativa (P-11, confirmada el 2026-11-18) es también una **lista de secciones por persona, cada una solo con `texto`**, sin referencias ni identificadores; está definida en los borradores M5-01 y M5-02 y la ensambla `presentacion.py` desde esta salida validada |
| **Versión** | 0.1 (borrador) |
| **Fecha** | 2026-11-18 |
| **Base** | `docs/backlog/tickets/m5-plan-implementacion.md` (M5-T3); ADR-003 (secciones 6, 8, 9 y 12); contratos M5-01 y M5-02 (borradores 0.2); decisiones D-M5-01, D-M5-03, D-M5-05, D-M5-07, D-M5-08 y D-M5-09 |
| **Qué no define** | **El transporte.** No se diseña ni se asume ninguna ruta, protocolo, formato de invocación de AWS Lambda, firma de peticiones ni llamada a Amazon Bedrock: es de M5-T5. Tampoco define el prompt, el modelo, la región, la retención ni ningún valor de límite (D-M5-06 abierta) |
| **Código** | `backend/app/modulos/informes/{generacion,validacion,narrativa,generador_simulado}.py` |

## 1. Capas

| Capa | Qué es | Dónde |
|---|---|---|
| 1. Datos seleccionados y autorizados | El informe con sus hechos, ya filtrado con la política de M1 | `InformeBase`, `ConsolidadoBase` (M5-T1 y M5-T2) |
| 2. Métricas deterministas | Las seis cifras del catálogo confirmado (D-M5-04) | `Agregaciones` |
| 3. Contexto mínimo de generación | La entrada de campos cerrados de **una persona**, seudonimizada | `EntradaDeGeneracion` |
| 4. Narrativa propuesta | Lo que devuelve el generador: **dato no confiable** hasta validarlo | salida bruta |
| 5. Validación determinista | Comprobaciones mecánicas de estructura y de contenido | `validar_salida` |
| 6. Respuesta de error segura | Una clase y motivos de un vocabulario fijo, sin contenido | `ErrorDeGeneracion` |

Una narrativa **por persona** (D-M5-03). En el informe individual hay una llamada; en el consolidado, una por persona, y la sección de equipo es determinista y **no se envía** al generador.

## 2. La interfaz

```
GeneradorDeTexto.generar(entrada: EntradaDeGeneracion) -> salida bruta
```

Quien la implemente (el simulado; `GeneradorDesactivado`; en M5-T5, el adaptador de Lambda) recibe la entrada y devuelve la salida **bruta**, que el dominio trata como no confiable. El adaptador declara sus fallos con `GeneradorNoDisponible` o `TiempoAgotado`; su mensaje **nunca** se propaga. El dominio no aplica reintentos ni colas (D-M5-06 abierta).

## 3. Entrada (versión 1)

Lista **cerrada** de campos, construida por una función con campos explícitos y no serializando las estructuras del informe.

| Campo | Contenido | Observaciones |
|---|---|---|
| `version` | `"1"` | |
| `tipo` | `individual` o `consolidado` | El informe del que forma parte esta persona |
| `idioma` | `"es"` | `[SUPUESTO]`: la narrativa es en español; confirmar con PA-13 |
| `periodo` | `desde`, `hasta` (fechas laborales ISO) | |
| `persona` | solo `alias` (`"Persona 1"`) | Sin nombre real, sin identificador |
| `actividades[]` | `ref`, `forma`, `texto`, `planificada` | `texto` es el título si la forma es `completa` y «Actividad en continuidad» si es `neutral`. `planificada` puede ser nulo (origen protegido). **Sin identificador de la base de datos** |
| `hechos[]` | `ref`, `fecha_laboral`, `actividad_ref`, `estado`, `descripcion`, `motivo_bloqueo` | Un avance autorizado cada uno. `motivo_bloqueo` solo si Bloqueada |
| `metricas` | Las seis agregaciones de la persona (`avances`, `jornadas_con_registros`, `actividades_con_registros`, `actividades_por_origen`, `actividades_con_bloqueo`, `actividades_por_estado_al_corte`) | **Hechos dados**: el generador no las calcula ni las modifica. Van **separadas** de `hechos` |
| `campos_no_confiables` | `["texto", "descripcion", "motivo_bloqueo"]` | Le dice al adaptador qué valores son texto libre de las personas |

**Nunca viajan:** el nombre real, `persona.id`, el identificador de las actividades, correos, identificadores de acceso, contraseñas, tokens, sesiones, nombres de equipos, el resumen libre de la bitácora (ADR-003, B6), actividades marcadas por error, planificaciones ni la auditoría.

Ejemplo ficticio (abreviado):

```json
{"version": "1", "tipo": "individual", "idioma": "es",
 "periodo": {"desde": "2026-11-01", "hasta": "2026-11-30"},
 "persona": {"alias": "Persona 1"},
 "actividades": [{"ref": "a1", "forma": "completa", "texto": "Preparar informe", "planificada": true}],
 "hechos": [{"ref": "h1", "fecha_laboral": "2026-11-03", "actividad_ref": "a1", "estado": "En progreso",
             "descripcion": "Primer avance", "motivo_bloqueo": null}],
 "metricas": {"avances": 1, "jornadas_con_registros": 1, "actividades_con_registros": 1,
              "actividades_por_origen": {"planificadas": 1, "no_planificadas": 0, "origen_no_disponible": 0},
              "actividades_con_bloqueo": 0,
              "actividades_por_estado_al_corte": {"pendiente": 0, "en_progreso": 1, "bloqueada": 0, "completada": 0, "estado_no_disponible": 0}},
 "campos_no_confiables": ["texto", "descripcion", "motivo_bloqueo"]}
```

## 4. Salida (versión 1)

Esquema **cerrado**: exactamente estos campos.

| Campo | Tipo | Regla |
|---|---|---|
| `version` | cadena | `"1"` |
| `secciones` | lista no vacía | Cada elemento, un objeto con exactamente `texto` y `refs` |
| `secciones[].texto` | cadena no vacía | **Texto plano**. Sin enlaces, marcado, correos ni identificadores |
| `secciones[].refs` | lista no vacía de cadenas | Referencias de hechos de la entrada que respaldan la sección. **Internas**: no se muestran (PP-11 no está aprobada) |
| `uso` | objeto | Exactamente `tokens_entrada` y `tokens_salida`, enteros no negativos. Informativo: sirve para medir el consumo |

La salida no tiene dónde llevar cifras ni hechos propios: **no puede reemplazar ni modificar las cifras verificadas**. No se fija ninguna longitud máxima porque no está definida (D-M5-06).

```json
{"version": "1",
 "secciones": [{"texto": "Persona 1 registró 1 avances en 1 jornadas, sobre 1 actividades.", "refs": ["h1"]}],
 "uso": {"tokens_entrada": 0, "tokens_salida": 0}}
```

## 5. Validación determinista

| Comprobación | Clase del fallo | Motivo (vocabulario fijo) |
|---|---|---|
| La salida es un objeto | `RESPUESTA_MALFORMADA` | `no_es_un_objeto` |
| Campos desconocidos, en cualquier nivel | `RESPUESTA_MALFORMADA` | `campo_desconocido` |
| Campos ausentes | `RESPUESTA_MALFORMADA` | `campo_faltante` |
| Versión, tipos, secciones, textos, refs y `uso` válidos | `RESPUESTA_MALFORMADA` | `version_no_admitida`, `secciones_invalidas`, `seccion_no_es_un_objeto`, `texto_invalido`, `refs_invalidas`, `uso_invalido` |
| Cada `ref` es de un hecho de la entrada | `RECHAZADA_POR_VALIDACION` | `referencia_inexistente` |
| Sin enlaces, marcado, correos ni UUID | `RECHAZADA_POR_VALIDACION` | `contenido_no_admitido` |
| Sin porcentajes (RN-57) | `RECHAZADA_POR_VALIDACION` | `porcentaje` |
| Solo el alias recibido | `RECHAZADA_POR_VALIDACION` | `alias_no_autorizado` |
| Las fechas ISO son las de los hechos o los límites del período | `RECHAZADA_POR_VALIDACION` | `fecha_no_autorizada` |
| Cada número es una métrica, el número de hechos o un número de los propios registros | `RECHAZADA_POR_VALIDACION` | `cifra_no_autorizada` |
| Un número junto a «avances» o «jornadas» coincide con la métrica | `RECHAZADA_POR_VALIDACION` | `cifra_contradictoria` |

El validador **no modifica** la entrada ni la salida bruta, no copia ningún fragmento del texto en el error y no corrige: una narrativa incorrecta se rechaza, y los hechos no se alteran para que coincidan con ella.

**Una validación estricta puede rechazar texto legítimo** (por ejemplo, «2 avances bloqueados» junto a «avances» se compara con el total de avances). Es deliberado: fallar cerrado es preferible a mostrar una cifra errónea (RN-58).

## 6. Clasificación de fallos y respuesta pública

| Clase | Cuándo | Respuesta pública (M5-T4) | ¿Reintentable? |
|---|---|---|---|
| `OK` | Narrativa validada | — | — |
| `SIN_DATOS` | No hay registros autorizados: **el generador no se invoca** (RN-57) | Informe con `sin_datos` | — |
| `ERROR_TECNICO` | El generador no está disponible, no está configurado o está desactivado, o falla de forma inesperada | `INFORME_NO_GENERADO` | **Sí**, salvo integración desactivada o sin generador configurado (no es transitorio) |
| `TIEMPO_AGOTADO` | El adaptador agota su plazo | `INFORME_NO_GENERADO` | Sí |
| `RESPUESTA_MALFORMADA` | No cumple el esquema cerrado | `INFORME_NO_GENERADO` | No |
| `RECHAZADA_POR_VALIDACION` | No supera una comprobación de contenido | `INFORME_NO_GENERADO` | No |
| `CONTEXTO_NO_ADMISIBLE` | Rebasa un límite configurado, **antes** de invocar | `INFORME_EXCEDE_LIMITES` | No |

**Sin contenido parcial** (RN-58, CA-175): si falla la narrativa de una sola persona del consolidado, el informe completo falla. Los fallos no revelan prompts internos ni datos: solo clase y motivos fijos.

## 7. Seudonimización y reconstrucción

**La seudonimización por alias NO es anonimización.** Solo evita enviar el nombre y el identificador de la persona. Los textos libres que sí viajan (descripciones, motivos de bloqueo y títulos) pueden contener nombres propios, datos de terceras personas y otra información personal, y la propia combinación de hechos, fechas y actividades puede permitir identificar a una persona. Los datos siguen siendo **datos personales** a todos los efectos (ADR-003, sección 6) y la base legal sigue abierta (B7). El alias reduce la exposición, no la elimina.

Cada llamada lleva una sola persona con el alias «Persona 1»; el alias y el nombre real viven solo en memoria. Tras validar, el alias del texto se sustituye por el nombre real. **Diferencia con ADR-003, sección 6:** el ADR describe una tabla de alias compartida por petición; aquí cada persona tiene su propia llamada (D-M5-03), de modo que no existe ningún alias que relacione a dos personas.

## 8. Límites

La entrada admite una verificación de contexto con límites configurables (`LimitesDeContexto`: período y número de hechos) **sin ningún valor por defecto**. Los demás límites (tokens, plazo, reintentos, concurrencia) se aplican en el adaptador y en la ruta. Propuesta de valores, para aprobación posterior: plan de M5, sección 17.4. **Ninguno está confirmado.**

## 9. Riesgo residual y evaluación por muestras (D-M5-05)

La validación determinista **no garantiza** que el texto:
- esté libre de **valoraciones subjetivas o juicios sobre personas** (RF-47, CA-163);
- sea **fiel** a los registros que cita (solo se comprueba que las referencias existan, no que digan lo que la frase afirma: CA-161, RNF-04);
- no contenga **nombres propios o hechos plausibles inventados** escritos en letra, ni cifras escritas con letras;
- no **obedezca** una orden escrita en un texto libre cuando lo hace con prosa inocua (la prueba lo demuestra con el generador simulado);
- no reproduzca **datos sensibles** del texto libre citado (puede contener nombres propios u otros datos personales; ADR-003, sección 6).

**Estrategia acotada de evaluación por muestras `[PROPUESTO]`** (se ejecuta en M5-T7, con datos ficticios, y de nuevo ante cualquier cambio de modelo, de región o de instrucciones):

1. Un conjunto de referencia ficticio en español (jornadas de distinto tamaño, registros parciales, bloqueos, actividades heredadas y textos con órdenes), definido y congelado antes de evaluar.
2. Una muestra de informes individuales y consolidados revisada por **al menos una persona hispanohablante ajena al desarrollo**, con una lista de verificación fija: ¿cada afirmación consta en los hechos citados? ¿hay valoraciones de personas? ¿aparece algún dato que no esté en la entrada? ¿se cumple la instrucción del texto libre? Tamaño inicial propuesto: 20 informes individuales y 5 consolidados (a confirmar).
3. Criterio de aceptación: **cero afirmaciones sin respaldo y cero valoraciones** en la muestra (RNF-04). Un solo incumplimiento detiene la habilitación y se corrige antes de repetir la muestra.
4. Resultado documentado con los informes ficticios usados; nunca con datos reales (D-M5-08).

## 10. Compatibilidad con los documentos existentes

No hay **ninguna incompatibilidad bloqueante**. Diferencias que conviene conocer:

| Documento | Lo que dice | Lo que implementa M5-T3 |
|---|---|---|
| Contrato 0.1 (`narrativa`) | Un único campo de texto | Una narrativa por persona (D-M5-03). Forma pública: lista de secciones solo con `texto` (P-11, confirmada) |
| ADR-003, sección 7 (consolidado) | Cifras «por persona y por equipo» como hechos dados | Solo las de la persona: la sección de equipo es determinista y no se envía (D-M5-03) |
| ADR-003, sección 6 | Tabla de alias compartida por petición | Un alias por llamada (más aislamiento) |
| ADR-003, sección 9 | Cada afirmación apunta a registros de origen | Las referencias son **por sección**, no por frase |
| ADR-003, secciones 9 y 12 | «Como máximo un reintento» | Un solo intento; los reintentos se decidirán con D-M5-06 |
| Plan, D-M5-07 | Sin tabla de consumo | Cumple: no se persiste nada |

## 11. Preguntas abiertas

| Id | Pregunta |
|---|---|
| P-11 | **Resuelta (2026-11-18):** lista de secciones por persona, en el contrato interno y en el público (solo `texto`). El adaptador de M5-T5 debe producir esta salida |
| D-M5-06 | Valores de los límites |
| — | Idioma de la narrativa (`[SUPUESTO]`: español) |
| — | Si el adaptador de M5-T5 debe devolver también un código de fin (por ejemplo, salida truncada); hoy no existe en el esquema |

## 12. Cambios de M5-T4

- **Reintento (P-12, confirmada).** `ErrorDeGeneracion.reintentable` es verdadero solo para fallos técnicos transitorios (generador no disponible, plazo agotado, error inesperado). Se añade `GeneradorNoConfigurado`: un generador desactivado o sin configurar es `ERROR_TECNICO` con el motivo `generador_no_configurado` y **no** es reintentable. Una salida malformada o rechazada por la validación tampoco lo es.
- **Límites.** El de hechos es **por solicitud** (400 en total) y lo aplica la canalización de M5-T4; `LimitesDeContexto.max_hechos` (por persona) de M5-T3 queda sin uso. `INFORME_REINTENTOS_VALIDACION` es 0: un solo intento.
- **Presentación.** `presentacion.py` ensambla la respuesta pública con proyecciones cerradas; no expone referencias ni identificadores internos.

## 13. Adaptador de Ollama local (M5-T5)

`GeneradorOllama` (`app/modulos/informes/generador_ollama.py`) implementa `GeneradorDeTexto` para el **desarrollo local** (decisión del 2026-11-18; Bedrock y Lambda quedan aplazados). **El contrato de este documento no cambia**: recibe la misma entrada de campos cerrados y devuelve la salida bruta de la sección 4, que el dominio valida siempre.

| Aspecto | Detalle |
|---|---|
| Transporte | `POST /api/chat` de la API HTTP local de Ollama, sin flujo, con el cliente HTTP de la biblioteca estándar (sin dependencias nuevas, sin redirecciones, sin proxies del entorno) |
| Destino | Solo `127.0.0.1`, `localhost` o `::1`, con puerto explícito, sin credenciales, ruta, parámetros ni fragmento; las rutas de la API las fija el adaptador |
| Mensajes | **Sistema:** instrucciones fijas (nunca textos laborales). **Usuario:** un único objeto JSON delimitado con los datos de la sección 3; `<` y `>` se escapan para que ningún texto laboral cierre el delimitador |
| Respuesta pedida | JSON Schema (`format`): solo `secciones` (`texto` y `refs`), con las `refs` restringidas a las referencias de los hechos recibidos; el adaptador añade `version` y `uso` (los tokens que informa Ollama) |
| Campos de más | No se pulen: el validador los rechaza (`campo_desconocido`), también si el modelo escribe `version` o `uso` |
| Fallos | Sin conexión o error del servidor: `ERROR_TECNICO` (reintentable). Plazo agotado: `TIEMPO_AGOTADO`. Modelo no instalado (404): `ERROR_TECNICO` con `generador_no_configurado` (no reintentable). Contexto que no cabe en `num_ctx`: `CONTEXTO_NO_ADMISIBLE` (`INFORME_EXCEDE_LIMITES`), antes de llamar o descartando la respuesta. Cuerpo o contenido ilegible: respuesta malformada |
| Privacidad | Sin registros en el adaptador: ni prompts, ni textos laborales, ni respuestas. El cuerpo de error del servidor no se propaga |
| Configuración | `INFORME_GENERADOR=ollama` exige `INFORME_OLLAMA_URL`, `INFORME_OLLAMA_MODELO`, `INFORME_OLLAMA_TIMEOUT_SEGUNDOS` e `INFORME_OLLAMA_NUM_CTX`, sin valores por defecto. **Son parámetros de desarrollo y no confirman** los límites abiertos de D-M5-06 (tokens, plazo total, concurrencia) |
