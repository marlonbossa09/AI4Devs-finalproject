# SMARTWORK — Matriz de trazabilidad de M5 (informes individuales y consolidados asistidos por IA)

| Campo | Contenido |
|---|---|
| **Estado** | Evidencia de la revisión técnica y contractual final de M5 (M5-T8), **aprobada por la persona responsable el 2026-11-19 como cierre técnico con reservas**. No modifica ningún requisito ni cambia ninguna decisión: clasifica cada criterio según la evidencia ejecutada |
| **Fecha** | 2026-11-19 |
| **Base** | Rama `final-project-eq`, M5-T1 a M5-T7 consolidados (HEAD `638c4a1`); los documentos de cierre de M5-T8 (este documento, el plan y la nota en la matriz de M4) se consolidan en un único commit documental |
| **Fuentes** | `docs/backlog/M5-…/HU-5.1` a `HU-5.5`, `docs/api/m5-01-informe-individual-v0.2.md`, `m5-02-informe-consolidado-v0.2.md`, `m5-informes.md`, `m5-integracion-ia.md`, `docs/backlog/tickets/m5-plan-implementacion.md` (secciones 22 a 25), ADR-003, `matriz-trazabilidad-m4.md` y el código y las pruebas reales |

## 1. Método, claves y estados

Cada criterio se clasifica con los **cinco estados** del proyecto: **implementado y probado**, **parcial**, **pendiente**, **bloqueado** y **fuera de alcance aprobado**. Un criterio solo es «implementado y probado» si hay una prueba ejecutada que lo comprueba. **Nada se declara cumplido por inferencia ni porque el generador simulado produzca una respuesta válida.**

**Dos tipos de evidencia, que no son equivalentes:**
- **(S) Simulado o determinista:** el núcleo determinista, la API y la interfaz con el **generador simulado** (sin modelo). Demuestra la autorización, las proyecciones, las cifras y la ruta de fallos; **no demuestra calidad de la IA**.
- **(L) LLM real:** el adaptador de Ollama local con un modelo real y datos ficticios (M5-T5 y M5-T7). Solo hay evidencia de **servicio** (sin HTTP) y de **muestras pequeñas**.

| Clave | Evidencia |
|---|---|
| **B-NI** | `backend/tests/test_informe_individual.py` (16 pruebas, M5-T1) |
| **B-NC** | `test_informe_consolidado.py` (13, M5-T2) |
| **B-GEN** | `test_generacion_informes.py` (13, M5-T3: interfaz, validador, narrativa, fallos) |
| **B-HTTP** | `test_informes_http.py` (15, M5-T4: API pública con el simulado) |
| **B-RHTTP** | `test_informes_http_real.py` (3, M5-T4: uvicorn real y PostgreSQL desechable, simulado) |
| **B-OLL** | `test_generador_ollama.py` (45, M5-T5: adaptador con transporte simulado y un servidor local de prueba; **no es Ollama**) |
| **B-OLLR** | `test_generador_ollama_real.py` (M5-T5, **(L)**, omitida por defecto) |
| **B-EVAL** | `test_evaluacion_ollama.py` (M5-T7, **(L)**, omitida por defecto; variable propia `SMARTWORK_EVAL_OLLAMA_MODELO`) |
| **F-D** | `frontend/test/features/report_data_test.dart` (9, análisis del contrato y reglas) |
| **F-P** | `report_pages_test.dart` (24, pantallas, estados, errores, sesión y móvil, con repositorio simulado) |
| **R-UI** | Recorrido real en Chrome de M5-T6 (cliente compilado, FastAPI, PostgreSQL desechable, **generador simulado**) |

## 2. Resumen por estado

| Conjunto | Criterios | Implementado y probado | Parcial | Pendiente | Bloqueado | Fuera de alcance aprobado |
|---|---|---|---|---|---|---|
| Los **38 criterios propios** de HU-5.1 a HU-5.5 | 38 | **34** | **4** (CA-161, CA-163, CA-166, CA-224) | 0 | 0 | 0 |
| — HU-5.1 (15) | 15 | 14 | 1 (CA-224) | 0 | 0 | 0 |
| — HU-5.2 (7) | 7 | 4 | 3 (CA-161, CA-163, CA-166) | 0 | 0 | 0 |
| — HU-5.3 (8) | 8 | 8 | 0 | 0 | 0 | 0 |
| — HU-5.4 (6) | 6 | 6 | 0 | 0 | 0 | 0 |
| — HU-5.5 (2) | 2 | 2 | 0 | 0 | 0 | 0 |
| Reconciliados de M4 (sección 4): CA-19, CA-20, CA-05 | 3 | 3 | 0 | 0 | 0 | 0 |

**Cómo leer estas cifras.** Los 34 «implementado y probado» lo son con evidencia **(S)**: autorización, proyecciones, cifras, límites, declaración de base, ausencia de datos y ruta de fallos. **Ninguno de los 38 criterios tiene evidencia de extremo a extremo (HTTP, interfaz) con un LLM real**; la única evidencia (L) es de servicio, de muestras pequeñas y con datos ficticios. Los criterios CA-152, CA-153 y CA-168 («obtiene el informe») están probados con el simulado; con un generador real, el consolidado no se obtuvo de forma fiable en la evaluación (secciones 6 y 12).

Los cuatro **parciales**: tres dependen de la calidad de la narrativa con un modelo real (fidelidad, ausencia de valoraciones y no obediencia al texto libre) y uno (CA-224) de una limitación de la interfaz.

## 3. Matriz de los 38 criterios propios

Contrato: **M5-01** = informe individual, **M5-02** = informe consolidado. «IyP» = implementado y probado. Las claves de prueba citan funciones por un fragmento de su nombre.

### HU-5.1 — Generar un informe individual

| ID | Requisito / regla | Contrato | Estado | Evidencia concreta | Dependencia y riesgo pendiente |
|---|---|---|---|---|---|
| CA-152 | RF-29 · RN-03, RN-29 | M5-01 | **IyP (S)** | B-HTTP `el_informe_individual_propio_se_devuelve…`; B-NI `el_informe_propio_trae…`; F-P «asks the own report for the default period…»; R-UI (informe propio) | Con un generador real solo hay evidencia de servicio (B-OLLR, B-EVAL); sin recorrido HTTP real |
| CA-153 | RF-29 | M5-01 | **IyP (S)** | B-NI `el_supervisor_obtiene_el_informe_de_una_persona…`; B-HTTP `el_supervisor_obtiene_el_informe_de_su_persona…`; F-P «a supervisor can choose a person of the team…»; R-UI | Igual que CA-152 |
| CA-154 | RF-29 · RN-36 | M5-01 | **IyP (S)** | B-NI `un_companero_que_no_supervisa_recibe_403…`, `403_o_404_dependen_de_la_visibilidad…`; B-HTTP `un_companero_visible_sin_permiso_recibe_403…`; R-UI (403 y 404 por HTTP) | El servidor decide; la interfaz no ofrece la opción |
| CA-155 | RF-48 | M5-01 | **IyP (S)** | B-HTTP (esquema: `periodo`, `generado_en` con la hora actual); F-D «reads every field of the contract…»; F-P (`Período del … Generado el …`); R-UI | — |
| CA-156 | RF-49 · RN-86 | M5-01 | **IyP (S)** | B-NI `el_informe_propio_trae…`, `la_estructura_solo_tiene_los_campos_cerrados…`; B-GEN `lo_que_viajaria_al_generador_tiene_campos_cerrados…`; B-HTTP `el_nombre_y_el_identificador_de_la_persona_no_llegan_al_generador…`; B-EVAL (L): en 7 llamadas reales no salió nada de otro equipo | Solo se envía lo autorizado (probado); su fidelidad en el texto es CA-161 |
| CA-157 | RF-49 · RN-53 | M5-01 | **IyP (S)** | B-NI `el_supervisor_del_equipo_anterior_solo_obtiene_lo_de_su_equipo…`, `…nuevo_no_recibe_titulo_ni_motivos…` | — |
| CA-158 | RF-75 · RN-56 | M5-01/02 | **IyP (S)** | F-P `expectReadOnly` (sin campos ni palabras de edición) en ambas pantallas; B-NI `…el_informe_es_de_solo_lectura`; B-NC `el_consolidado_es_de_solo_lectura`; R-UI | — |
| CA-159 | RF-75 · RN-56 | M5-01/02 | **IyP (S)** | B-GEN `el_paquete_de_informes_no_importa_ningun_cliente_de_red_ni_de_aws_y_no_persiste`; B-HTTP `las_solicitudes_no_escriben_ni_registran_contenido`; F-P «changing the period takes the report away…» y las dos pruebas de sesión; el informe vive en un estado en memoria que se destruye al salir de la pantalla | No hay una prueba que navegue fuera y vuelva dentro de la misma sesión; la propiedad se apoya en el diseño (estado autodestruido, sin almacenamiento) |
| CA-160 | RF-50 | M5-01 | **IyP (S)**, evidencia indirecta | B-HTTP: cada solicitud devuelve `generado_en` con su propio momento actual; B-HTTP sin persistencia | **Sin una prueba específica de dos generaciones consecutivas** (laguna menor) |
| CA-224 | RF-96 · RN-53 | M5-01 | **Parcial** | Backend: B-NI `el_supervisor_del_equipo_anterior_solo_obtiene_lo_de_su_equipo_y_nada_posterior_al_traslado` | **La interfaz solo ofrece a los integrantes actuales (M4-05, H-M5-11)**: en pantalla el supervisor no puede pedir el informe de quien ya no integra el equipo; solo por la API |
| CA-225 | RF-96 | M5-01 | **IyP (S)** | La misma prueba (nada posterior al traslado ni del equipo nuevo) | Alcanzable solo por la API (ver CA-224) |
| CA-226 | RF-94 · RN-88 | M5-01 | **IyP (S)** | B-NI `el_supervisor_del_equipo_nuevo_no_recibe_titulo_ni_motivos_ni_detalles_del_equipo_anterior` | La «referencia mínima» es opcional («puede incluir») |
| CA-227 | RF-93 | M5-01 | **IyP (S)** | B-NI `la_propietaria_trasladada_obtiene_todos_sus_registros_de_ambos_equipos` | — |
| CA-234 | RF-100 | M5-01 | **IyP (S)** | B-NI `el_estado_al_corte_sigue_la_secuencia_y_un_avance_protegido_no_se_sustituye…` | — |
| CA-276 | RF-111 · RN-101 | M5-01 | **IyP (S)** | B-NI `…nuevo_no_recibe_titulo_ni_motivos_ni_detalles…`; B-HTTP `…la_actividad_heredada_sale_neutral_sin_datos_protegidos`; F-P «a neutral activity shows only the fixed label»; R-UI (actividad neutral); B-EVAL (L): el caso de la actividad heredada no envió nada del equipo anterior | — |

### HU-5.2 — Informes apoyados en los registros

| ID | Requisito / regla | Contrato | Estado | Evidencia concreta | Dependencia y riesgo pendiente |
|---|---|---|---|---|---|
| CA-161 | RF-32 · RN-06, RN-26, RN-29 | M5-01/02 | **Parcial** | (S) Los hechos, las cifras y los bloqueos salen del registro (B-NI, B-NC); el validador comprueba referencias, cifras, fechas, alias y contenido no admitido (B-GEN). (L) Lectura manual de B-EVAL: `qwen3:8b` fiel en los 3 aceptados (con omisiones y redacción torpe); `qwen2.5:3b-instruct` afirmó lo contrario del registro | **No hay evaluación semántica por muestras** (D-M5-05); el validador no garantiza fidelidad. RNF-04 no es verificable con esta evidencia. **Bloquea el uso real** |
| CA-162 | RF-46 | M5-01/02 | **IyP (S)** | B-GEN `la_narrativa_y_las_metricas_estan_separadas…`; B-HTTP (narrativa aparte); F-P «…base, figures, records, blockages and narrative apart» (etiquetas CALCULADO, REGISTRADO y REDACTADO CON IA); R-UI | — |
| CA-163 | RF-47 | M5-01/02 | **Parcial** | Rankings y puntuaciones: ausentes de la estructura (B-NC `la_estructura_tiene_campos_cerrados_sin_rankings…`) y de la pantalla (F-P `expectNoRanking`). Valoraciones: el validador **no las detecta**; B-EVAL (L): `qwen2.5:3b` escribió «el mejor de todo el equipo» (rechazado por otra causa); los 3 textos aceptados de `qwen3:8b` no tenían | Sin detector ni evaluación semántica. **Bloquea el uso real** |
| CA-164 | RF-51 · RN-31 | M5-01/02 | **IyP (S)** | B-NI `…las_cifras_coinciden_con_un_recuento_manual`; B-NC `las_agregaciones_por_persona_coinciden_con_las_del_informe_individual…`; B-GEN `la_narrativa_y_las_metricas_estan_separadas…` (la narrativa no cambia las cifras) | — |
| CA-165 | RF-74 | M5-01/02 | **IyP (S)** | B-NI (bloqueo con su motivo); B-HTTP; F-D y F-P (bloqueos como registro histórico); R-UI | — |
| CA-166 | RNF-12 | M5-01/02 | **Parcial** | (S) B-NI `el_texto_libre_se_conserva_como_dato_sin_interpretarlo`; B-GEN `una_orden_escrita_en_una_descripcion_viaja_solo_como_dato_y_su_obediencia_se_rechaza_si_es_detectable`; F-P «markup, links and instructions are shown as plain text». (L) B-EVAL: `qwen3:8b` ignoró las órdenes (un caso); **`qwen2.5:3b` las convirtió en hechos** («reveló los registros de todos los equipos», «el mejor de todo el equipo») y el validador no lo detectó | Riesgo residual **conocido y demostrado**; la validación determinista no cubre la obediencia semántica. **Bloquea el uso real** |
| CA-167 | RF-78 | M5-01/02 | **IyP (S)** | B-NI `las_actividades_marcadas_por_error_y_las_planificaciones_conservadas_quedan_fuera`; B-NC `las_marcadas_por_error…` | — |

### HU-5.3 — Generar un informe consolidado

| ID | Requisito / regla | Contrato | Estado | Evidencia concreta | Dependencia y riesgo pendiente |
|---|---|---|---|---|---|
| CA-168 | RF-30 · RN-54 | M5-02 | **IyP (S)** | B-NC `el_supervisor_obtiene_el_consolidado…`; B-HTTP `el_consolidado_se_devuelve_por_persona…`; B-RHTTP; F-P «a supervisor asks the team report…»; R-UI | **Con un modelo real no se demostró**: `qwen2.5:3b` rechazado y `qwen3:8b` no ejecutado (se estimó de 17 a 35 minutos); el flujo síncrono es inviable en la práctica |
| CA-169 | RF-30 | M5-02 | **IyP (S)** | B-NC `solo_el_supervisor_vigente_con_acceso_efectivo…`; B-HTTP `el_consolidado_rechaza_a_quien_no_supervisa…`; F-P «a collaborator who reaches the team report anyway…»; R-UI (HTTP 403) | — |
| CA-170 | RF-30 | M5-02 | **IyP (S)** | B-NC `un_equipo_ajeno_o_inexistente_es_el_mismo_404`; B-HTTP | — |
| CA-171 | RF-48 | M5-02 | **IyP (S)** | B-HTTP (esquema del consolidado: `periodo`, `generado_en`); F-P; R-UI | — |
| CA-228 | RF-83 | M5-02 | **IyP (S)** | B-NC `una_persona_trasladada_solo_aporta_a_cada_equipo_lo_de_sus_fechas`; R-UI (persona trasladada) | — |
| CA-229 | RF-83 | M5-02 | **IyP (S)** | La misma prueba (nada posterior al traslado para el equipo anterior) | — |
| CA-235 | RF-98 | M5-02 | **IyP (S)** | B-NC `el_estado_al_corte_que_determina_un_avance_de_otro_equipo_no_se_muestra_ni_se_sustituye` | — |
| CA-277 | RF-111 · RN-101 | M5-02 | **IyP (S)** | B-NC; B-GEN; B-HTTP `…el_consolidado_no_expone_titulos_ni_motivos_protegidos`; R-UI | — |

### HU-5.4 — Informe cuando faltan registros

| ID | Requisito / regla | Contrato | Estado | Evidencia concreta | Dependencia y riesgo pendiente |
|---|---|---|---|---|---|
| CA-172 | RF-33 · RN-57 | M5-01/02 | **IyP (S)** | B-NI `un_periodo_sin_avances_es_sin_datos`; B-NC `sin_avances_autorizados_el_consolidado_dice…`; B-HTTP `un_informe_sin_datos_lleva_la_base…`; F-P «a period with no data…»; R-UI (también con la generación desactivada) | — |
| CA-173 | RF-33 · RN-57 | M5-01/02 | **IyP (S)** | B-GEN `un_informe_sin_datos_no_invoca_al_generador`; B-HTTP (sin narrativa y sin cifras); F-P | — |
| CA-199 | RF-33 | M5-01/02 | **IyP (S)** | B-NI `el_periodo_acota_la_seleccion…`; B-NC; solo se seleccionan registros autorizados | La narrativa «únicamente con esos registros» depende de su fidelidad (CA-161) |
| CA-200 | RF-87 · RN-60 | M5-01/02 | **IyP (S)** | B-HTTP (la declaración fija `base` en toda respuesta, también sin datos); F-P `report-base`; R-UI | — |
| CA-201 | RF-33 | M5-01/02 | **IyP (S)** | B-NC (personas con un único avance, incluidas) y B-NI (la supervisora con un solo avance) | Sin prueba dedicada de «un único registro» con la narrativa |
| CA-202 | RF-33 · RN-36 | M5-01/02 | **IyP (S)** | B-NI (prueba que cita CA-202: la persona tiene registros pero ninguno autorizado, se informa sin datos) | — |

### HU-5.5 — Servicio de IA no disponible

| ID | Requisito / regla | Contrato | Estado | Evidencia concreta | Dependencia y riesgo pendiente |
|---|---|---|---|---|---|
| CA-174 | RF-76 · RN-58 | M5-01/02 | **IyP (S)** | B-GEN `un_generador_no_disponible_con_tiempo_agotado_o_roto_se_clasifica_sin_filtrar_nada`; B-HTTP `un_fallo_del_generador_o_una_salida_rechazada_es_503…`; B-RHTTP; F-P «a transient technical failure…» y «generation switched off…»; R-UI (con la generación desactivada); B-OLLR (L) servidor caído y modelo no instalado; B-OLL | **PA-09** (proveedor y condiciones) sigue abierto; **P-14**: la interfaz no distingue la causa |
| CA-175 | RF-76 · RN-58 | M5-01/02 | **IyP (S)** | B-GEN `si_falla_la_narrativa_de_una_persona_no_se_devuelve_un_informe_parcial`; B-HTTP (503 sin contenido); B-RHTTP; F-P; R-UI | — |

## 4. Reconciliación de CA-19, CA-20 y CA-05

Eran parciales al cerrar M4 porque faltaba la parte de informes. Con los informes ya implementados:

| Criterio | Estado al cerrar M4 | Estado ahora | Evidencia de la parte de informes |
|---|---|---|---|
| **CA-19** (RF-83) | Parcial (consultas probadas; informes pendientes de M5) | **Implementado y probado** | B-NC `una_persona_trasladada_solo_aporta_a_cada_equipo_lo_de_sus_fechas` (CA-228 y CA-229); B-NI `el_supervisor_del_equipo_nuevo_no_recibe…` y `…anterior_solo_obtiene…` (CA-225, CA-226); R-UI. Se mantienen las pruebas de consulta de M4 |
| **CA-20** (RF-83) | Parcial | **Implementado y probado** | Quien integra U no obtiene el informe de otra persona (CA-154: 403 o 404 uniforme); el supervisor de U recibe solo lo posterior al traslado y la forma neutral (CA-226, CA-276, CA-277); lo enviado al generador no contiene nada protegido (B-GEN y B-HTTP, B-EVAL en las llamadas reales). Se mantienen el acceso directo (M2-07, M2-08, M3-07, 404) y las consultas de M4 |
| **CA-05** (RNF-08) | Parcial | **Implementado y probado**, con una reserva | Los informes no llevan datos de acceso ni credenciales (B-NI `la_estructura_solo_tiene_los_campos_cerrados_y_ningun_dato_de_acceso_ni_de_equipo`; B-HTTP `la_respuesta_no_lleva_identificadores_internos_ni_datos_de_acceso_ni_de_equipo`); lo que viaja al generador tiene campos cerrados y ninguna credencial (B-GEN `lo_que_viajaria_al_generador…`); ni el cuerpo de la solicitud ni el de la respuesta ni los prompts se registran (B-HTTP `las_solicitudes_no_escriben_ni_registran_contenido`, B-OLL) |
| | | | **Reserva:** si una persona escribe una credencial dentro de un texto libre, el informe la conserva como dato y el generador podría repetirla; no existe detección de información personal ni de credenciales en el texto libre (sección 9, control faltante) |

## 5. Pruebas reutilizadas y ejecutadas en M5-T8

Se **reutilizan** las pruebas de M5-T1 a M5-T7 y se **ejecutó una regresión completa de backend** contra PostgreSQL desechable (porque la última regresión completa era anterior a M5) y `flutter analyze`. No se ejecutó ninguna inferencia real, ninguna mutación ni ninguna prueba que invoque a Ollama. La suite completa de Flutter (739) se ejecutó en M5-T6, después del último cambio de Flutter, y no se repitió.

| Verificación | Resultado |
|---|---|
| `flutter analyze` | Sin incidencias |
| Pruebas de Flutter (suite completa, M5-T6) | 739 superadas, de ellas 33 de informes |
| Regresión completa de backend (M5-T8, PostgreSQL desechable, 16 min) | **3139 superadas, 13 omitidas, 0 fallos**. Las 13 omitidas: 7 de la evaluación de M5-T7 y 5 de la prueba real de M5-T5 (requieren habilitación explícita) y 1 omisión previa conocida |
| Pruebas de Ollama real (B-OLLR, B-EVAL) | **Omitidas** (requieren habilitación explícita) y **no ejecutadas** |

## 6. Evidencia de integración con el simulador

- **B-RHTTP:** servidor uvicorn real y PostgreSQL desechable con el generador simulado habilitado expresamente (individual, consolidado, salida malformada) y con la generación desactivada por defecto.
- **R-UI (M5-T6):** recorrido real en Chrome con el cliente compilado y el simulado (supervisora con ambas pantallas, informe propio sin datos, informe de una persona con cifras, registros, bloqueo y narrativa, actividad neutral, informe del equipo con tres personas, móvil de 400 px, pérdida del rol en plena sesión, colaboradora, generación desactivada, comprobaciones HTTP de 403 y 404). Sin datos laborales reales.
- **Comprobaciones puntuales de M5-T8** (todas cubiertas por pruebas existentes): generación desactivada por defecto (B-HTTP `la_generacion_esta_desactivada_por_defecto…`); selección explícita del proveedor y simulado solo si se pide (B-HTTP `el_simulado_solo_se_usa_si_se_pide_expresamente…`); proyecciones autorizadas y referencias opacas (B-HTTP, R-UI); cifras deterministas y declaración de base; `sin_datos`; 403 y 404 uniformes; límites de 31 días y de 400 hechos sin truncar (B-HTTP `el_rango_maximo_es_de_31_dias…`, `mas_de_400_hechos_autorizados_se_rechazan_sin_truncar…`); manejo de errores sin contenido parcial; prohibición de persistir y de importar clientes de red o de AWS (B-GEN).

**Limitación:** el simulador demuestra los caminos y la seguridad, **no la calidad**: un texto válido del simulador no cuenta como cumplimiento de CA-161, CA-163 ni CA-166.

## 7. Evidencia y limitaciones de la evaluación de Ollama (resumen; detalle en el plan, sección 24)

- **Muestra exploratoria, no extrapolable.** Un solo escenario ficticio, 5 informes individuales con datos por modelo.
- `qwen2.5:3b-instruct`: **1 de 5** individuales aceptados por el validador; consolidado rechazado. `qwen3:8b`: **3 de 5** individuales aceptados; consolidado **no ejecutado**.
- Tiempos: `qwen3:8b` de **155 a 285 s** por informe individual (promedio ≈ **206 s**); `qwen2.5:3b-instruct`, de 14 a 33 s. CPU, sin GPU dedicada.
- **Sin etapa B, sin recorrido HTTP con Ollama real, sin prueba de concurrencia, sin evaluación de `gpt-oss`, sin cambios de prompt ni del validador.**
- Calidad leída a mano: `qwen3:8b` fiel en los aceptados pero con redacción torpe y omisiones; `qwen2.5:3b` con afirmaciones contrarias al registro y órdenes maliciosas convertidas en hechos.
- Veredicto del proveedor: **experimental, no apto todavía para uso habitual.**

## 8. Defectos y limitaciones encontrados

| Id | Hallazgo | Estado |
|---|---|---|
| H-1 | La prueba de evaluación de M5-T7 se habilitaba con la misma variable que la prueba real de M5-T5: habilitar una activaba la otra | **Corregido** antes de consolidar M5-T7 (variable propia); comprobado que ambas se omiten por defecto y que la primera no activa la segunda |
| H-2 | El texto de la narrativa no se exponía a las tecnologías de apoyo de Flutter Web (`SelectableText`) | **Corregido** en M5-T6 (`Text` dentro de `SelectionArea`) |
| H-3 | La interfaz no ofrece el informe de una persona que ya no integra el equipo (H-M5-11); afecta a CA-224 en pantalla | **Limitación abierta** (parcial) |
| H-4 | Un modelo pequeño puede convertir órdenes del texto libre en hechos y el validador no lo detecta | **Riesgo residual demostrado** (CA-166, CA-161, CA-163) |
| H-5 | El validador rechaza fechas escritas con el nombre del mes aunque sean correctas, y cualquier número que no sea una cifra autorizada | Comportamiento seguro previsto; baja la tasa de aceptación |
| H-6 | La interfaz no distingue generación desactivada, modelo no instalado y texto rechazado (P-14) | **Necesidad aprobada; esquema y contrato pendientes** |
| H-7 | No hay una prueba específica de dos generaciones consecutivas (CA-160) ni de navegar fuera y volver (CA-159) | Laguna menor; no se añadió prueba (no es defecto crítico) |
| H-8 | Regresión completa de backend | Sin defectos: 3139 superadas, 0 fallos |

No se encontró ningún defecto que bloquee el núcleo determinista, la API ni la interfaz con el simulador.

## 9. Dependencias, decisiones abiertas y controles para usar un modelo real

**Valores CONFIRMADOS (sin cambios):** rango máximo de 31 días; máximo de 400 hechos por solicitud; reintentos de validación 0; generación desactivada por defecto.

**Siguen ABIERTAS (D-M5-06 parcial):** máximo de tokens de entrada, máximo de tokens de salida, plazo total y concurrencia de generación. Los valores **1024 tokens de salida, 360 s por llamada y concurrencia 1** son **propuestas de evaluación**, no límites operativos definitivos.

**P-14** (motivo del fallo en la interfaz): **aprobada como necesidad funcional; el esquema y el contrato de errores siguen pendientes.** No se implementa sin una decisión contractual adicional. **La ejecución asíncrona sigue sin autorización** (RN-56 y RF-75 la excluyen salvo una decisión de producto nueva). Siguen abiertos D-M5-08 (uso de datos reales), PA-09 (proveedor y tratamiento de datos) y la evaluación previa de Bedrock y Lambda (ADR-003, sección 13).

### Controles que faltan para usar un modelo real con datos laborales

| # | Control | Clasificación |
|---|---|---|
| 1 | Base de tratamiento y privacidad de los textos (decisión de PA-09 y D-M5-08: qué se envía, a quién, con qué conservación) | **Bloqueante para uso real** |
| 2 | Minimización y detección de información personal o credenciales en el texto libre | **Bloqueante** |
| 3 | Evaluación semántica de calidad por muestras con revisión humana y umbral de aceptación definido (D-M5-05) | **Bloqueante** |
| 4 | Protección contra instrucciones maliciosas más allá del validador determinista (detección de citas, de valoraciones y de afirmaciones sin respaldo) | **Bloqueante** |
| 5 | Límites efectivos de tiempo, tokens y concurrencia (cierre de D-M5-06) y decisión sobre el modelo de ejecución frente a la generación larga | **Bloqueante** |
| 6 | Control de consumo y de disponibilidad (cuotas, tiempos de espera efectivos, comportamiento con el generador caído, sin reintentos silenciosos) | **Bloqueante** |
| 7 | Monitoreo operativo seguro (métricas sin contenido, sin prompts ni respuestas) | **Bloqueante** |
| 8 | Evaluación de Bedrock y Lambda (región, retención, modelo, coste) antes de activarlos, con autorización expresa de AWS | **Bloqueante** si se elige ese proveedor |
| 9 | P-14 (motivo del fallo en el contrato y la interfaz) | No bloqueante para el MVP determinista; recomendable |
| 10 | Informe de personas que ya no integran el equipo en la interfaz (H-M5-11) | No bloqueante |
| 11 | Revisión de accesibilidad con lector de pantalla (R-11) | No bloqueante |
| 12 | Pruebas adicionales de CA-159 y CA-160 | No bloqueante |

## 10. Riesgos

**Privacidad:** el texto libre laboral puede contener datos personales o credenciales que un modelo repetiría; un destino local reduce la exposición pero no sustituye el marco de privacidad; la narrativa se trata como contenido no confiable. **Calidad:** el modelo puede afirmar lo que el registro no dice, valorar personas y obedecer o citar órdenes; el validador no lo detecta; muestras pequeñas. **Operación:** de 2,5 a 5 minutos por informe individual con `qwen3:8b` en CPU, consolidado inviable en flujo síncrono; sin límite de concurrencia; consumo de memoria de 2,4 a 6,7 GB por modelo.

## 11. Estado de migraciones

**M5 no añadió ninguna migración ni cambió el esquema** (RN-56: los informes no se persisten; el modelo de datos no contiene entidades de IA). Último estado: `0018_indice_historico_de_bitacoras` (M4-T2). Sin cambios en `migrations/` desde la base de M4. No se tocó la base de datos local `smartwork_app`.

## 12. Veredicto contractual y técnico

Tres situaciones **distintas**, que no deben tomarse por equivalentes:

1. **Cierre del desarrollo de M5: M5 — CERRADO TÉCNICAMENTE CON RESERVAS** (aprobado por la persona responsable). El núcleo determinista, la API y la interfaz con el simulador están implementados, probados y consolidados en siete commits locales (M5-T1 a M5-T7); el adaptador del proveedor local existe como proveedor de desarrollo.
2. **Cumplimiento de los criterios del MVP:** **34 de 38 implementados y probados con evidencia (S); 4 parciales** (CA-161, CA-163, CA-166 por la calidad de la narrativa con un modelo real y CA-224 por la interfaz). **Ningún criterio está demostrado de extremo a extremo con un LLM real**, y con un modelo real el consolidado no se obtuvo de forma fiable. El MVP **determinista** (cifras, registros, bloqueos, autorización, declaración de base y ausencia de datos) cumple; **la parte «asistida por IA» no está demostrada**.
3. **Habilitación para producción: NO.** Faltan los controles bloqueantes de la sección 9. La generación sigue desactivada por defecto y Ollama es **experimental**.

**Funcionalidades que todavía no cumplen sus criterios:** (a) la narrativa generada por un modelo real (fidelidad, ausencia de valoraciones y no obediencia al texto libre: CA-161, CA-163, CA-166); (b) el informe de una persona que ya no integra el equipo desde la interfaz (CA-224); (c) la obtención fiable del consolidado con un modelo real en el flujo síncrono (CA-168 con IA real).

## 13. Recomendaciones para la entrega final del proyecto

1. Presentar M5 como **«núcleo determinista, API e interfaz completos; narrativa de IA en estado experimental y desactivada por defecto»**, sin afirmar que los informes con IA están listos para uso real.
2. Decidir el modelo de ejecución (flujo síncrono acotado u otro) y, con él, cerrar D-M5-06; decidir el esquema de P-14.
3. Si se quiere una narrativa real, elegir proveedor y ejecutar la evaluación previa (ADR-003, sección 13) y una evaluación semántica por muestras con revisión humana, con datos ficticios, antes de cualquier dato real.
4. Mantener los valores confirmados y la generación desactivada por defecto; no autorizar datos laborales reales (D-M5-08).
5. No avanzar a despliegue ni a entrega final sin revisión de la persona responsable.
