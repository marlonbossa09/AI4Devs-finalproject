# ADR-003 — Integración del servicio de IA en SMARTWORK

| | |
|---|---|
| **Estado** | **PROPUESTO**. No están aprobados el proveedor, el modelo, la región ni la retención |
| **Versión** | 0.3 |
| **Fecha** | 2026-11-06 |
| **Relacionado con** | PA-09, RNF-06 (PP-33), RN-26, RN-29, RN-30, RN-31, RN-53 a RN-58, RN-86, RN-101, RNF-04, RNF-12, PP-11, ADR-001 |
| **Documentos complementarios** | `docs/api/m1-m5-dependencias.md`, `docs/api/convenciones.md`, `docs/modelo-datos/modelo-datos.md` |

AWS Bedrock es el candidato prioritario de evaluación y la API directa de Anthropic, la alternativa. Este ADR no elige proveedor. Compara ambas opciones con datos consultados el 2026-11-06 y marca lo que **no se pudo verificar**. No contiene credenciales y no modifica el alcance, el PRD, las historias ni el modelo de datos.

**Cautela sobre los datos.** Las fichas y los precios proceden de páginas oficiales leídas con una herramienta de lectura automática; algunas páginas se truncaron y las condiciones cambian con frecuencia. Antes de aprobar, cada dato debe contrastarse con la cuenta real y con el contrato del proveedor. Este ADR distingue entre «literal en la fuente» y «no encontrado».

## 1. Comparación de las opciones

| Aspecto | Amazon Bedrock | API directa de Anthropic |
|---|---|---|
| Modelo | `anthropic.claude-sonnet-5-5`; perfiles `us.`, `eu.`, `au.` y `global.` | Claude Sonnet 5.5 (y Haiku 5.5) |
| Región de procesamiento | Sin soporte en región para Sonnet 5.5 en el punto de acceso de ejecución: solo mediante perfiles de inferencia entre regiones. Desde `sa-east-1` solo el perfil global. Los perfiles geográficos limitan el procesamiento a su geografía | `inference_geo`: `global` (por defecto) o `us`. `us` cuesta 1,1 veces el precio |
| Retención | Modos `none`, `default`, `aws_review` y `provider_data_share`. Qué modos admite **Sonnet 5.5 no está declarado** en las páginas leídas | No se retiene el contenido por defecto, salvo los «Covered Models» (30 días). Retención cero por organización, previa solicitud a ventas. Sonnet 5.5 y Haiku 5.5 no figuran como excluidos |
| Entrenamiento | «Los datos nunca se usan para entrenar» (AWS, según búsqueda; no literal en las páginas leídas) | «Los datos retenidos no se usan para entrenar sin permiso expreso» |
| Precio | **No verificado** (ver sección 1.1) | Verificado en la página oficial (ver sección 1.1) |
| Operación | Cuenta AWS, IAM, cifrado con claves propias, registro de llamadas | Clave de API, gestión de secretos, facturación directa |
| Encaje con ADR-001 | Detrás de la interfaz propia de IA | Igual |

Ninguna de las dos opciones queda descartada.

### 1.1 Evidencia de precios

Los precios de las dos opciones **no son equivalentes ni intercambiables**: son de proveedores distintos, con facturación distinta. No se comparan entre sí hasta tener el precio de Bedrock.

| Opción | Precio de Claude Sonnet 5.5 | Evidencia | Estado |
|---|---|---|---|
| **API directa de Anthropic** | 2 USD de entrada y 10 USD de salida por millón de tokens. Haiku 5.5: 0,10 y 0,50 USD con prompts de hasta 100.000 tokens, y 0,50 y 2,50 por encima. Lotes: 50 % de descuento. `inference_geo` igual a `us`: multiplicador de 1,1 | Página oficial de precios de la API de Claude, tabla literal, leída el 2026-11-06 (sin fecha de publicación en la página) | **Verificado en la fuente** |
| **Amazon Bedrock** | **No encontrado.** La página de precios de Bedrock leída el 2026-11-06 solo contiene una nota sobre una rebaja del 50 % en la lectura de caché de Sonnet 5.5 desde el 7 de octubre de 2026; la tabla de precios de Anthropic no apareció en el texto leído, y la ficha del modelo indica que se factura «a través de AWS Marketplace» | Página de precios de Bedrock (truncada en la lectura) y ficha del modelo | **No verificado.** No se estima ni se infiere del precio de la API directa |

Cualquier cifra de coste de este ADR se calcula solo con los precios de la API directa y se indica como tal.

### 1.2 Criterios para seleccionar proveedor y modelo

La selección se condiciona a todos estos puntos, comprobados en la cuenta real y no en la documentación general:

1. **Disponibilidad real:** el modelo está habilitado en la cuenta y en la región o perfil elegidos, con la cuota necesaria.
2. **Protección de datos:** modo de retención sin almacenamiento verificado con una llamada de prueba, región de procesamiento aceptable y contrato de tratamiento de datos.
3. **Coste:** precio oficial verificado del proveedor elegido y estimación con volúmenes reales.
4. **Calidad de los informes en español:** resultado de la evaluación de la sección 13.

Hasta que se cumplan los cuatro, no se aprueba ninguna opción.

## 2. Modelo concreto candidato

- **Candidato principal: Claude Sonnet 5.5.** La tarea (resumir y estructurar hechos dados, con fidelidad y sin inventar) no exige el nivel superior, y la ventana de contexto (1 millón de tokens) y la salida máxima (128.000 tokens) de la ficha de Bedrock sobran para un informe.
- **Candidato de coste: Claude Haiku 5.5**, a evaluar con el mismo conjunto de pruebas.
- La elección se confirma con la evaluación de la sección 13, no por reputación. La ficha de Sonnet 5.5 en Bedrock indica restricciones sobre los parámetros de razonamiento que deben revisarse al diseñar la llamada.

## 3. Regiones y perfiles de inferencia

| Perfil | Procesamiento | Observaciones |
|---|---|---|
| Sin perfil (en región) | No disponible para Sonnet 5.5 en el punto de acceso de ejecución | Solo aparece un punto de acceso en GovCloud |
| Geográfico `us.` | Regiones de EE. UU. (y, desde las canadienses, EE. UU. y la región de origen) | Se limita a esa geografía |
| Geográfico `eu.` | Regiones de la UE (la lista exacta depende de la región de origen) | Se limita a esa geografía |
| Geográfico `au.` | Dos regiones de Australia | — |
| Global `global.` | «Cualquier lugar del mundo» si no hay restricciones de residencia; la página no lista los destinos | Se consulta con la API de perfiles |

**La región de origen no determina por sí sola la región de procesamiento.** Con un perfil entre regiones, la solicitud se registra en la región de origen pero puede ejecutarse en otra, y los datos de entrada y salida pueden salir de ella. La región efectiva de cada llamada consta en el registro de CloudTrail. Desde São Paulo, Sonnet 5.5 solo está disponible con el perfil global, por lo que el procesamiento puede ocurrir fuera de Brasil.

Con la API de Anthropic, el procesamiento está limitado a `global` o `us`.

## 4. Modos de retención admitidos por el modelo

| Hecho | Estado de la verificación |
|---|---|
| Los modos existentes en Bedrock son `none`, `default`, `aws_review` y `provider_data_share`; `none` garantiza que no se escribe nada en almacenamiento duradero ni se comparte con el proveedor | Literal en la documentación de AWS |
| `default`: AWS puede retener datos con fines de seguridad y prevención de abuso | Literal |
| `aws_review` (retención hasta 30 días con posible revisión humana) se exige hoy a Claude Fable 5 y 5.1 | Literal; **no aplica a Sonnet 5.5** según las páginas leídas |
| «No hay cambio de retención para los modelos Claude anteriores a Claude Fable 5» | Literal. No queda claro si Sonnet 5.5 (lanzado el 28 de septiembre de 2026) es anterior |
| **Qué modos admite Sonnet 5.5** | **No declarado.** Se consulta con la API de modelos de la cuenta (`allowed_modes`); no se ejecutó |
| Detección de abuso: la ficha de Sonnet 5.5 la lista como compatible, pero la página de detección de abuso solo describe retención para otros modelos | Literal; sin información sobre Sonnet 5.5 |

**Consecuencia:** no se presupone retención cero en Bedrock. Antes de aprobar hay que ejecutar la consulta de `allowed_modes` para el modelo candidato, establecer el modo `none` y comprobar con una llamada de prueba que se acepta y que no deja rastro. Si el modelo no admite `none`, las salidas son: otro modelo que sí lo admita, la API de Anthropic con retención cero, o no usar el servicio externo (RNF-06).

Con la API de Anthropic, la retención cero no es automática: se solicita por organización y excluye algunas funciones.

## 5. Evitar el almacenamiento de prompts y respuestas

| Capa | Control |
|---|---|
| Proveedor | Modo de retención `none`, verificado para el modelo (sección 4), y aplicado por cuenta o proyecto y, en Bedrock, reforzado con políticas de organización (la documentación describe el mecanismo, pero su detalle no pudo leerse completo) |
| Registro de invocaciones del proveedor | Desactivado. En Bedrock es opcional y, si se activa, escribe prompts y respuestas en almacenamiento propio |
| Aplicación | Los registros nunca incluyen prompts, respuestas ni registros de bitácora. El informe no se persiste (RN-56). No hay caché de prompts |
| Verificación | Prueba con una cadena marcadora: tras la llamada no debe aparecer en ningún registro ni almacenamiento propio |

## 6. Datos personales y seudonimización

- Se consideran **datos personales** los nombres de las personas, sus identificadores, la información laboral que los vincula y el texto libre, que puede nombrar a terceras personas.
- **Seudonimización por petición:** cada persona se sustituye por un alias (por ejemplo, «Persona 1»). La tabla de alias vive solo en memoria durante la generación y se descarta; el informe final se reconstruye localmente. Nunca se envían correos, identificadores de acceso ni identificadores internos.
- **Límite:** el texto libre puede contener nombres propios u otros datos. No hay un filtro fiable; por eso se trata el texto libre como dato personal potencial y se minimiza lo enviado (sección 7).
- La seudonimización reduce la exposición, no elimina el carácter de dato personal. La base legal queda pendiente (sección 11).

## 7. Campos mínimos por tipo de informe

Solo los registros que la política de autorización permite a quien genera el informe (RA-09, RN-86): las mismas proyecciones, la misma referencia neutral y las mismas exclusiones que en M4.

| Campo | Informe individual (HU-5.1) | Informe consolidado (HU-5.3) |
|---|---|---|
| Período (desde y hasta) | Sí | Sí |
| Alias de la persona | Sí (una) | Sí (varias) |
| Por actividad: título (o «Actividad en continuidad» si no está autorizado) | Sí | Sí |
| Fecha laboral, estado histórico y descripción de cada avance | Sí | Sí |
| Motivo de bloqueo, en los avances Bloqueada | Sí (RN-55) | Sí |
| Planificada o no planificada | Sí | Sí |
| Cifras calculadas de forma determinista (sección 9) | Sí, como hechos dados | Sí, por persona y por equipo |
| Nombre del equipo | No | No. Basta «el equipo» |
| Resumen libre de la bitácora | **Excluido del envío por defecto** (decisión de la persona responsable). Incluirlo exigiría una decisión expresa | Ídem |
| Identificadores, correos, nombres reales | No | No |
| Actividades marcadas por error, planificación conservada, auditoría, datos de otros equipos | No | No |

## 8. Prevención de inyección de instrucciones (RN-31)

El texto libre de las bitácoras es dato, no instrucción. Defensas en capas:

1. **Separación estructural:** instrucciones fijas del sistema, y los registros entregados como datos estructurados y delimitados, con un escape coherente. Nunca se concatenan en las instrucciones.
2. **Instrucción explícita** de tratar cualquier orden contenida en los datos como texto que resumir.
3. **Sin herramientas ni acceso a la red** para el modelo, y sin ejecución de nada de lo que devuelva.
4. **Salida estructurada** con un esquema fijo; todo lo que no cumpla se rechaza.
5. **Presentación como texto plano**: la salida no se interpreta como HTML ni como enlaces ni imágenes, para impedir la exfiltración por contenido enlazado.
6. **Validación posterior** (sección 9), que detecta afirmaciones sin respaldo aunque la inyección haya influido.
7. **Pruebas adversariales:** un conjunto de registros con instrucciones maliciosas, con criterios de aceptación de que el informe no obedece.

## 9. Validación de hechos y métricas deterministas

Canal propuesto:

1. **Selección y filtrado autorizados** (sin IA).
2. **Cálculos deterministas** (sin IA): recuentos por estado, número de actividades iniciadas y completadas, días con registro, listado de bloqueos con motivo. Se entregan al modelo como hechos y se insertan en el informe directamente, no se piden al modelo (RN-26, RN-55).
3. **Generación** del texto narrativo con el modelo, usando solo los datos dados.
4. **Validación determinista de la salida:** cada afirmación apunta a registros de origen que existen y están autorizados; cada número del texto coincide con los calculados; no aparecen personas, fechas ni actividades que no estén en la entrada (CLAUDE.md, sección 9); los alias son los entregados.
5. **Si la validación falla**, el resultado se trata como fallo de generación: no se muestra contenido parcial (RN-58). Se permite como máximo un reintento de generación.
6. **Mostrar enlaces a los registros de origen en el informe** es la propuesta PP-11, no aprobada. La referencia interna de la validación no implica mostrarla.

## 10. Estimación de costes y límites de consumo

Precios leídos el 2026-11-06 en la página oficial de Anthropic (dólares por millón de tokens): Sonnet 5.5, 2 de entrada y 10 de salida; Haiku 5.5, 0,10 y 0,50 con prompts de hasta 100.000 tokens (0,50 y 2,50 por encima). Con `inference_geo` igual a `us`, multiplicar por 1,1. **El precio de Bedrock para Sonnet 5.5 no se encontró**: la estimación en Bedrock queda pendiente de la tarifa oficial del modelo, la región y el perfil.

**Todas las cifras de este apartado usan el precio de la API directa; no hay estimación para Bedrock.**

**Fórmula:** coste por informe = tokens de entrada × precio de entrada + tokens de salida × precio de salida.

**Escenario ilustrativo, con supuestos `[SUPUESTO]` que no son datos del producto:** 22 jornadas por mes, 4 avances por jornada, 150 tokens por avance, 1.500 tokens de instrucciones, 800 tokens de salida (individual) y 1.500 (consolidado de 10 personas, con 2.000 de instrucciones). Y 50 informes individuales y 5 consolidados al mes.

| Informe | Entrada | Salida | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|---|
| Individual mensual | 14.700 tokens | 800 tokens | ≈ 0,037 USD | ≈ 0,002 USD |
| Consolidado mensual (10 personas) | 134.000 tokens | 1.500 tokens | ≈ 0,28 USD | ≈ 0,07 USD (tramo de más de 100.000 tokens) |
| **Mes completo del escenario** | — | — | **≈ 3,3 USD** | **≈ 0,45 USD** |

Cálculo: 14.700 × 2 / 1.000.000 + 800 × 10 / 1.000.000 = 0,0374 (Sonnet, individual); 134.000 × 2 / 1.000.000 + 1.500 × 10 / 1.000.000 = 0,283 (Sonnet, consolidado). Los totales de Haiku se calculan igual con sus precios.

El orden de magnitud del escenario es bajo. Lo que lo cambia es el volumen, la longitud de las descripciones, los reintentos y la elección del modelo; no se debe tomar como presupuesto.

**Límites de consumo propuestos (todos configurables; valores por decidir con PA-13):**

- Amplitud máxima del período del informe.
- Número máximo de registros y de tokens de entrada por informe, y de tokens de salida.
- Número máximo de generaciones simultáneas y por equipo y día.
- Presupuesto mensual global con aviso y, al superarlo, rechazo.

Al rebasar un límite, la petición se rechaza **antes** de llamar al proveedor y se informa de por qué; no se genera un informe parcial.

## 11. Requisitos legales pendientes de confirmar

Este ADR no afirma que ninguna opción cumpla una norma. Hay que confirmar con asesoría legal, según el país donde opere la organización (pendiente):

- Base legal para tratar datos laborales de personas con un servicio externo y finalidad concreta.
- Transferencia internacional de datos si el procesamiento sale del país (relevante con perfiles globales).
- Contrato o anexo de tratamiento de datos con el proveedor elegido y sus subencargados.
- Información a las personas cuyos registros se tratan, y límites de la vigilancia laboral.
- Evaluación de impacto cuando la norma lo exija.
- Plazo máximo de conservación en el proveedor.

## 12. Manejo de errores, tiempos de espera y ausencia de datos

| Situación | Tratamiento |
|---|---|
| No hay registros autorizados en el período | El informe indica que no hay datos (RN-57). **No se llama al proveedor**: no se envían datos ni se gasta |
| Hay registros, pero pocos | Se informa y se presenta lo existente sin presentarlo como total (PA-19, RN-57) |
| El proveedor no responde en el tiempo máximo | Se informa de que el informe no pudo generarse, sin contenido parcial (RN-58) |
| Errores transitorios o limitación de peticiones | Reintentos acotados con espera creciente, dentro de un plazo global |
| La salida no cumple el esquema o la validación | Fallo de generación; como máximo un reintento (sección 9) |
| El proveedor rechaza o bloquea el contenido | Fallo de generación, sin detalles del contenido |
| Se rebasa un límite de consumo | Rechazo previo y aviso (sección 10) |
| Respuesta en flujo | No se muestra nada hasta que la validación termina |

Los tiempos máximos, el número de reintentos y el plazo global son parámetros configurables (PA-13). Los mensajes de error nunca incluyen contenido de los registros.

## 13. Evaluación previa a su uso

Condición para aprobar el proveedor y el modelo:

- **Conjunto de referencia en español** con registros ficticios: jornadas de distinto tamaño, registros parciales, vacíos, bloqueos y actividades heredadas.
- **Fidelidad:** cero afirmaciones sin respaldo en los registros (revisión de una muestra por una persona y comprobación determinista de la sección 9).
- **Calidad en español:** claridad, concisión, terminología laboral correcta y ausencia de valoraciones de personas. Criterios y escala definidos antes de evaluar, y revisión por al menos una persona hispanohablante ajena al desarrollo.
- **Cumplimiento del esquema** de salida y resistencia a las inyecciones de la sección 8.
- **Medición** de tokens reales, latencia y coste con los precios verificados.
- **Verificación en la cuenta:** modo de retención admitido por el modelo, región efectiva de procesamiento y ausencia de rastro con una cadena marcadora.
- Se comparan Sonnet 5.5 y Haiku 5.5 con el mismo conjunto, y las dos opciones de proveedor si ambas están disponibles.

## 14. Interfaz y credenciales

El servicio queda detrás de una interfaz propia con un adaptador por proveedor (ADR-001). Las credenciales del proveedor se gestionan como secretos de despliegue con permisos mínimos (en Bedrock, una identidad con permiso solo para invocar el modelo o perfil elegido) y nunca se guardan en el repositorio ni en documentos.

## 15. Decisiones para aprobación

| Id | Decisión | Recomendación |
|---|---|---|
| B1 | Proveedor | Decidir tras verificar la retención y la región reales del modelo (secciones 4 y 3) |
| B2 | Modelo | Evaluar Sonnet 5.5 y Haiku 5.5 (sección 13) |
| B3 | Región y perfil de inferencia | Depende del país de la organización y de B7. Evitar el perfil global si hay restricciones de residencia |
| B4 | Retención | Exigir `none` (o retención cero) y verificarlo con una llamada de prueba; si no es posible, no usar el servicio |
| B5 | Seudonimización con alias en memoria | Sí |
| B6 | Incluir o no el resumen libre en lo enviado | **Decidido: queda excluido por defecto** |
| B7 | País y marco legal aplicable | Necesito esta respuesta (sección 11) |
| B8 | Límites de consumo y presupuesto | Parámetros por decidir con PA-13 |
| B9 | Tiempos máximos y reintentos | Parámetros por decidir |
| B10 | Evaluación previa (sección 13) como condición de aprobación | Sí |

## 16. Impacto estructural (presentado, no aplicado)

- Ninguna entidad de IA en el modelo: el informe no se persiste (RN-56).
- Posible estructura técnica de control de consumo (contadores y presupuesto), si se aprueba B8. No almacena contenido.
- El registro de llamadas al proveedor, si se decide (PA-09), no debe contener contenido.
- Sin cambios en las nueve entidades.

### 16.1 Riesgos, parámetros y dependencias para la implementación

En la fase de documentación no se contrata ningún servicio, no se abre ninguna cuenta en un proveedor, no se envía ningún dato y no se comprueba ninguna integración.

| Tipo | Elemento | Cuándo se resuelve |
|---|---|---|
| Riesgo | La documentación no declara qué modos de retención admite el modelo candidato (sección 4) | Al consultar la cuenta del proveedor elegido |
| Riesgo | El procesamiento puede salir del país con perfiles entre regiones (sección 3) | Al elegir región y perfil, con el marco legal |
| Riesgo | Sin precio verificado de Bedrock (sección 1.1) no hay comparación de costes | Al consultar la tarifa oficial |
| Riesgo | Inyección de instrucciones por el texto libre (sección 8) | Con las pruebas adversariales de la sección 13 |
| Riesgo | Datos personales en el texto libre pese a la seudonimización (sección 6) | Con el marco legal y la minimización |
| Parámetro | Límites de período, registros, tokens y presupuesto; tiempos máximos y reintentos (sección 10 y 12) | Aprobación (B8, B9) con PA-13 |
| Parámetro | Catálogo de agregaciones | Aprobación funcional |
| Dependencia | País y marco legal (B7) | Asesoría legal |
| Dependencia | Cuenta del proveedor con el modelo habilitado | Selección del proveedor |
| Dependencia | Evaluación previa en español (sección 13) | Antes de aprobar el proveedor |

## 17. Lo que este ADR no decide

El proveedor, el modelo, la región, los valores de límites y tiempos, la base legal, el despliegue ni la presentación de enlaces a los registros de origen (PP-11).

## 18. Fuentes

- Ficha del modelo Claude Sonnet 5.5 en Amazon Bedrock: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html>
- Retención de datos en Amazon Bedrock: <https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html>
- Protección de datos en Amazon Bedrock: <https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html>
- Inferencia entre regiones geográfica: <https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html>
- Disponibilidad regional por modelo: <https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html>
- Cómo exigir retención cero en Bedrock: <https://aws.amazon.com/blogs/security/enforce-zero-data-retention-on-amazon-bedrock-with-bedrock-projects-and-service-control-policies/> (leída parcialmente)
- Precios de Amazon Bedrock: <https://aws.amazon.com/bedrock/pricing/> (sin precio de Sonnet 5.5 en el texto leído)
- API y retención de datos de Claude: <https://platform.claude.com/docs/en/manage-claude/api-and-data-retention>
- Precios de la API de Claude: <https://platform.claude.com/docs/en/about-claude/pricing>
- Residencia de datos de la API de Claude: <https://platform.claude.com/docs/en/manage-claude/data-residency>

## 19. Historial

| Versión | Cambios |
|---|---|
| 0.3 | Se añade la sección 16.1 con riesgos, parámetros y dependencias para la implementación. El proveedor, el modelo, la región y la retención siguen sin aprobar; AWS Bedrock sigue como candidato prioritario |
| 0.2 | Se separa la evidencia de precios de la API directa y de Bedrock (sección 1.1), se explicitan los criterios de selección (sección 1.2) y se detalla la evaluación previa, incluida la calidad en español (sección 13). El resumen libre queda excluido del envío por defecto. El proveedor, el modelo, la región y la retención siguen sin aprobar |
| 0.1 | Primera propuesta |
