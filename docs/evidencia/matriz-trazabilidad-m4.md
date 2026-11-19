# SMARTWORK — Matriz de trazabilidad de M4 (consulta histórica y supervisión)

| Campo | Contenido |
|---|---|
| **Estado** | Evidencia del cierre técnico de M4 (M4-T9), pendiente de revisión por la persona responsable. No modifica ningún requisito: clasifica cada criterio según la evidencia ejecutada |
| **Fecha** | 2026-11-18 |
| **Base** | Rama `final-project-eq`, M4-T1 a M4-T8 consolidados (HEAD `28408e2`) más los cambios de M4-T9 sin confirmar |
| **Fuentes** | `docs/backlog/M4-…/HU-4.1` a `HU-4.4`, `docs/api/m4-consulta-supervision.md` (M4-01 a M4-05), `docs/backlog/tickets/m4-plan-implementacion.md`, `matriz-trazabilidad-m1.md`, `matriz-trazabilidad-m2-m3.md` y el código y las pruebas reales |

## 1. Método y claves de evidencia

Cada criterio se clasifica en uno de cinco estados: **implementado y probado**, **parcial**, **pendiente**, **bloqueado** y **fuera de alcance aprobado**. Un criterio solo es «implementado y probado» si hay una prueba ejecutada que lo comprueba; lo que solo depende de otro módulo se marca aparte. Nada se declara cumplido por inferencia.

| Clave | Evidencia |
|---|---|
| **B1** | `backend/tests/test_consulta_bitacora.py` (M4-01, 18 pruebas, dos añadidas en M4-T9) |
| **B2** | `test_consulta_historico.py` (M4-02, 18 funciones, 34 casos) |
| **B3** | `test_consulta_supervision.py` (M4-03 núcleo, 17 funciones, 25 casos) |
| **B4** | `test_consulta_supervision_herencia.py` (M4-03 herencia entre equipos, 19 funciones, 21 casos) |
| **B5** | `test_consulta_historial_actividad.py` (M4-04, 13 pruebas) |
| **B6** | `test_consulta_extensiones_m2_m3.py` (403 de M2/M3 y auditoría del supervisor, 7 funciones, 8 casos) |
| **B7** | `test_consulta_integrantes.py` (M4-05, 5 pruebas) |
| **BM1** | Pruebas de M1 que ya cubrían la política: `test_traslados.py`, `test_traslado_e2e.py`, `test_visibilidad_historica.py`, `test_desactivacion*.py`, `test_programacion.py` |
| **F-E** | Flutter: `team_data_test.dart`, `team_page_test.dart` (lectura entre pares) |
| **F-S** | Flutter: `supervision_data_test.dart`, `supervision_page_test.dart` (supervisión) |
| **R-INT** | Recorrido HTTP real del ticket que implementó el contrato (uvicorn y PostgreSQL desechable): T1 M4-01, T2 M4-02, T3 y T4 M4-03, T5 M4-04, T6 las extensiones de M2/M3. Indica que el contrato se ejecutó de extremo a extremo, no una comprobación por criterio |
| **R-UI** | Recorridos reales en Chrome con el cliente compilado: T7 (15 comprobaciones), T8 (28) y **T9 integral (25)** |

Todas las pruebas de backend usan PostgreSQL real (`smartwork_test`, clúster desechable); ninguna toca `smartwork_app`. Ninguna prueba ejecuta mutaciones.

## 2. Resumen por estado

| Conjunto | Criterios | Implementado y probado | Parcial | Pendiente | Bloqueado | Fuera de alcance aprobado |
|---|---|---|---|---|---|---|
| Los 61 criterios vinculados a los cuatro contratos | 61 | **59** | **2** (CA-19, CA-20) | 0 | 0 | 0 |
| — propios de las cuatro historias (47) | 47 | 47 | 0 | 0 | 0 | 0 |
| — de HU-1.4 y HU-3.7 vinculados a M4 (14) | 14 | 12 | 2 | 0 | 0 | 0 |
| Relacionados fuera de esos 61 (sección 4) | 14 | 13 | 1 (CA-05) | 0 | 0 | 0 |

Los dos parciales de los 61 son **CA-19 y CA-20**: la parte de consultas está probada, la de informes es de M5 (sección 7 del informe de cierre y sección 5 de este documento). CA-05 es parcial por la misma razón (informes).

**Actualización posterior (M5-T8, 2026-11-19):** la parte de informes de CA-19, CA-20 y CA-05 se reconcilió en `matriz-trazabilidad-m5.md` (sección 4): los tres pasan a implementados y probados (CA-05 con una reserva sobre el texto libre). Esta matriz conserva el estado de M4 en el momento de su cierre.

## 3. Los 61 criterios

### 3.1 HU-4.1 — Consultar las bitácoras de mi equipo (M4-01), 7 criterios propios

| CA | Regla o requisito | Estado | Backend (B) | Flutter (F) | Integración (R) | Pendiente |
|---|---|---|---|---|---|---|
| CA-130 | RF-23 | Implementado y probado | B1 `un_companero_lee_la_bitacora_de_otro_con_el_detalle_propio…` | F-E «a colleague logbook: is read-only» | R-INT T1; R-UI T7 (lectura de la bitácora de una compañera) y T9 (CA-193) | — |
| CA-131 | RF-25 | Implementado y probado | B1 `ninguna_ruta_de_m4_escribe…`; B6 `las_seis_escrituras…responden_403_y_no_cambian_nada` | F-E: sin campos ni botones de edición | R-INT T6; R-UI T7 («sin ningún botón de edición») | — |
| CA-132 | RF-24 | Implementado y probado | B1 `los_equipos_ven_solo_los_registros_de_su_periodo_tras_un_traslado`, `quien_se_incorpora_despues…_no_lo_del_otro` | F-E «no logbook…is one neutral message» | R-INT T1 | — |
| CA-133 | RF-67 | Implementado y probado | B1 `el_supervisor_lee_a_su_colaboradora_y_el_colaborador_lee_al_supervisor_del_equipo` | F-E «offers the CURRENT colleagues… tells the supervisor apart» | R-UI T7 y T9 (el selector ofrece a la supervisora) | — |
| CA-193 | RF-23, RN-36 | Implementado y probado | B1 `quien_se_incorporo_despues_lee_los_registros_historicos_de_su_equipo` | F-E: la fecha se elige libremente | **R-UI T9**: un colaborador incorporado hace 2 días abre, con el selector de fecha, la bitácora de Ana de hace 4 días | — |
| CA-194 | RF-25 | Implementado y probado | B1 `ninguna_ruta_de_m4_escribe…`; B6 las seis escrituras (403, base sin cambios) | F-E y F-S: ningún control de escritura | R-INT T6 | — |
| CA-291 | RNF-13 | Implementado y probado | B1 `inexistente_y_no_autorizado_son_indistinguibles`, `el_formato_se_valida_antes_que_el_recurso…` | F-E: un único mensaje neutro | R-INT T1 | — |

### 3.2 HU-4.2 — Consultar el histórico por colaborador y fechas (M4-02), 5 criterios propios

| CA | Regla o requisito | Estado | Backend (B) | Flutter (F) | Integración (R) | Pendiente |
|---|---|---|---|---|---|---|
| CA-134 | RF-26 | Implementado y probado | B2 `un_rango_valido_devuelve_solo_lo_autorizado…`, `el_filtro_por_persona_devuelve_solo_lo_autorizado_de_esa_persona` | F-E «the optional person filter is sent only when chosen» | R-UI T9: el filtro devuelve solo lo de Ana | — |
| CA-135 | RF-26, RA-01 | Implementado y probado | B2 `…solo_lo_autorizado…`, `recorrer_todas_las_paginas_no_duplica_ni_omite_y_lo_no_autorizado_no_acorta_ninguna` | F-E: solo lo que el servidor entrega | R-UI T9: 23 registros autorizados en 2 páginas, nada del otro equipo | — |
| CA-136 | RF-26 | Implementado y probado | B2 `no_hay_busqueda_por_texto_ni_otros_filtros` | F-E: no hay campo de búsqueda | — | — |
| CA-299 | RF-26, RN-25 | Implementado y probado | B2 `las_fechas_son_obligatorias_estan_en_orden_y_el_rango_no_supera_el_maximo` | F-E «ALWAYS sends desde and hasta» y «a range that cannot be sent is not sent» | R-UI T7 (no se pide nada hasta consultar) y T9 | — |
| CA-300 | RF-26 | Implementado y probado | B2 `el_historico_propio_incluye_todo_lo_suyo…`, `tras_un_traslado_cada_equipo_ve_su_periodo` | F-E «names people from the current team…» | R-UI T9: sin filtro aparecen las personas autorizadas, también quien ya salió | — |

### 3.3 HU-4.3 — Supervisar mi equipo en un período (M4-03), 29 criterios propios

| CA | Regla o requisito | Estado | Backend (B) | Flutter (F) | Integración (R) | Pendiente |
|---|---|---|---|---|---|---|
| CA-137 | RF-27 | Implementado y probado | B3 `el_supervisor_con_acceso_efectivo_obtiene_la_vista_con_la_forma_del_contrato`, `inclusion_por_planificacion_avances_y_pendiente…_totales_exactos` | F-S «asks only when the supervisor asks… the totals» | R-UI T8 y T9 | — |
| CA-138 | RF-69 | Implementado y probado | B3 `inclusion_por_planificacion_avances_y_pendiente…` | F-S: etiquetas de motivo de inclusión | — | — |
| CA-139 | RF-69 | Implementado y probado | B3 ídem | F-S ídem | — | — |
| CA-140 | RF-69 | Implementado y probado | B3 ídem | F-S ídem | — | — |
| CA-141 | RF-69 | Implementado y probado | B3 `lo_completado_antes_del_periodo_y_lo_marcado_por_error_no_aparecen` | — (lo decide el servidor) | R-INT T3 | — |
| CA-142 | RF-69 | Implementado y probado | B3 `inclusion_por_planificacion…` (aserción «CA-142: las propias») | — | — | — |
| CA-143 | RF-70 | Implementado y probado | B3 `el_estado_al_corte_se_distingue_del_actual_solo_si_difiere_y_la_propietaria_sigue_en_el_equipo` | F-S «the status at the cut and the current status are told apart» | R-UI T8 (estado al corte «No disponible» cuando el servidor lo omite) | — |
| CA-144 | RF-70 | Implementado y probado | B3 ídem | F-S ídem | — | — |
| CA-145 | RF-45 | Implementado y probado | B3 (aserción CA-145: sin ranking, puntuación ni clasificación en el JSON) | F-S: sin rankings ni puntuaciones | R-UI T8 | — |
| CA-146 | RF-27 | Implementado y probado | B3 `cada_supervisor_ve_solo_las_actividades_de_su_equipo`, `lo_de_otros_equipos_no_cambia_ni_los_totales_ni_la_lista` | — | R-UI T9: la vista de T no lleva nada de U | — |
| CA-147 | RF-78 | Implementado y probado | B3 `lo_completado_antes_del_periodo_y_lo_marcado_por_error_no_aparecen`; B4 `una_actividad_marcada_por_error_no_aparece_de_ninguna_forma_en_ningun_equipo` | — | R-INT T4 | — |
| CA-195 | RF-25 | Implementado y probado | B3 `ningun_metodo_de_escritura_existe_en_la_ruta` | F-S: sin controles de escritura | R-INT T3 | — |
| CA-196 | RF-83 | Implementado y probado | B4 `el_supervisor_del_equipo_nuevo_ve_la_actividad_continuada_en_forma_neutral…` | F-S | R-UI T8 (traslados T→U y U→T) y T9 | — |
| CA-197 | RF-83 | Implementado y probado | B4 `el_supervisor_del_equipo_anterior_no_ve_lo_posterior_al_traslado_ni_presenta_pendiente_a_la_persona_trasladada` | F-S | R-UI T8 | — |
| CA-198 | RF-70 | Implementado y probado | B3 `una_continuacion_planificada_posterior_al_corte_no_cambia_el_estado_al_corte` | — | R-INT T3 | — |
| CA-218 | RF-94 | Implementado y probado | B4 `la_actividad_heredada_sin_registros_del_equipo_es_una_referencia_minima_con_la_lista_cerrada_de_campos` | F-S «a full activity, a neutral one and a minimal reference are three different things» | R-UI T8 («Iniciada en otro equipo», sin nada reservado) | — |
| CA-219 | RF-94 | Implementado y probado | B4 ídem y `lo_que_no_se_puede_mostrar_no_cambia_nada_de_la_respuesta` | F-S ídem; F-S datos (modelo con lista cerrada) | R-UI T8 (nada reservado del equipo anterior) | — |
| CA-220 | RF-94 | Implementado y probado | B4 `una_referencia_minima_muestra_la_fecha_del_ultimo_avance_solo_si_ese_avance_esta_autorizado` | F-S: la fecha solo si llega | — | — |
| CA-221 | RF-95 | Implementado y probado | B4 `el_supervisor_del_equipo_anterior_no_ve_lo_posterior…`, `si_el_estado_actual_no_se_puede_informar_la_referencia_minima_no_se_emite` | F-S | — | — |
| CA-222 | RF-95 | Implementado y probado | B4 `el_equipo_anterior_conserva_sus_registros_autorizados_con_su_estado_al_corte_y_sin_estado_actual` | F-S | R-UI T8 | — |
| CA-223 | RF-94 | Implementado y probado | B4 `con_un_avance_del_equipo_nuevo_la_actividad_se_identifica_con_la_referencia_neutral…`; B5 `la_actividad_heredada_con_avances_del_equipo_nuevo_se_muestra_neutral_con_solo_esos_avances` | F-S «a neutral activity stays neutral…» | R-UI T8 y T9 (la actividad de Pablo llega a U como «Actividad en continuidad») | — |
| CA-230 | RF-98 | Implementado y probado | B4 `el_estado_al_corte_determinado_por_un_avance_de_otro_equipo_no_se_muestra_ni_se_sustituye` | F-S «an omitted status at the cut is not inferred» (se muestra «No disponible») | R-UI T8 y T9 | — |
| CA-231 | RF-98 | Implementado y probado | B4 `el_estado_al_corte_cambia_con_el_corte_y_se_muestra_cuando_lo_determina_un_avance_autorizado` | F-S | R-INT T4 | — |
| CA-232 | RF-99 | Implementado y probado | B4 `las_referencias_minimas_tienen_su_recuento_aparte_y_nunca_entran_en_los_totales_por_estado` | F-S: etiqueta «Referencia mínima» y nota fija | R-UI T8 | — |
| CA-233 | RF-99 | Implementado y probado | B5 `la_heredada_sin_registros_del_equipo_es_solo_la_referencia_minima_y_pasa_a_neutral_cuando_el_equipo_registra` | F-S «a minimal reference shows only the reference» | R-UI T8 | — |
| CA-272 | RF-111 | Implementado y probado | B4 `con_un_avance_del_equipo_nuevo_la_actividad_se_identifica_con_la_referencia_neutral…` | F-S | R-UI T8 y T9 | — |
| CA-273 | RF-111 | Implementado y probado | B4 `el_supervisor_del_equipo_nuevo_ve_la_actividad_continuada_en_forma_neutral_sin_nada_del_equipo_anterior`; B5 `el_supervisor_del_equipo_nuevo_no_obtiene_titulo_descripciones_ni_motivos_del_equipo_anterior` | F-S | R-UI T8 (historial de la actividad que continuó en el equipo nuevo, sin nada reservado) y T9 (la vista no lleva motivos protegidos) | — |
| CA-274 | RF-115 | Implementado y probado | B3 `el_periodo_puede_ser_futuro_y_las_planificaciones_conservadas_no_cuentan_como_trabajo_de_nadie` | — | — (no alcanzable por la API: D-M4-07) | La planificación conservada solo existe en datos: no hay ruta que la cree en el MVP actual (PA-24) |
| CA-301 | RF-111 | Implementado y probado | B4 `el_supervisor_del_equipo_nuevo_ve_la_actividad_continuada…` (identificador opaco, sin datos del equipo anterior) | F-E y F-S: «Actividad en continuidad» | R-UI T7, T8 y T9 | — |

### 3.4 HU-4.4 — Consultar el historial de las actividades de mi equipo (M4-04), 6 criterios propios

| CA | Regla o requisito | Estado | Backend (B) | Flutter (F) | Integración (R) | Pendiente |
|---|---|---|---|---|---|---|
| CA-148 | RF-28 | Implementado y probado | B5 `el_supervisor_ve_los_avances_autorizados_con_su_fecha_y_estado_historico_en_el_orden_de_la_secuencia` | F-S «a full activity: authorized plannings and progress in order» | R-UI T8 y T9 | — |
| CA-149 | RF-25 | Implementado y probado | B5 `la_ruta_es_de_solo_lectura_y_leer_no_cambia_nada` | F-S: sin controles de escritura | R-INT T5 | — |
| CA-150 | RF-25 | Implementado y probado | B5 ídem; B6 las seis escrituras (403, sin cambios) | F-S ídem | R-INT T5 y T6 | — |
| CA-151 | RF-45 | Implementado y probado | B5 `ninguna_respuesta_contiene_clasificaciones_ni_campos_fuera_de_la_lista_cerrada` | F-S: sin rankings ni puntuaciones | R-UI T8 | — |
| CA-275 | RF-111 | Implementado y probado | B5 `la_actividad_heredada_con_avances_del_equipo_nuevo_se_muestra_neutral…` | F-S «a neutral activity stays neutral» | R-UI T8 y T9 | — |
| CA-292 | RF-99 | Implementado y probado | B5 `la_heredada_sin_registros_del_equipo_es_solo_la_referencia_minima…` | F-S «a minimal reference shows only the reference» | R-UI T8 | — |

### 3.5 Criterios de HU-1.4 y HU-3.7 vinculados a los contratos (14)

| CA | Regla o requisito | Contrato | Estado | Backend (B) | Flutter (F) | Integración (R) | Pendiente |
|---|---|---|---|---|---|---|---|
| CA-15 | RF-66 | M4-01 | Implementado y probado | B1 `los_equipos_ven_solo_los_registros_de_su_periodo_tras_un_traslado`; BM1 `traslado_e2e`, `visibilidad_historica` | — | R-INT T1 | — |
| CA-16 | RF-66 | M4-01 | Implementado y probado | B1 ídem | — | R-INT T1 | — |
| CA-17 | RF-66 | M4-01 | Implementado y probado | B1 ídem | — | R-INT T1 | — |
| CA-18 | RF-66 | M4-01 | Implementado y probado | B1 ídem | — | R-INT T1 | — |
| CA-19 | RF-83 | M4-02 | **Parcial** | B2 `tras_un_traslado_cada_equipo_ve_su_periodo`, `las_actividades_neutrales_no_filtran_nada_del_equipo_anterior`; B3 y B4 (la vista consolidada) | F-E: el histórico solo muestra lo que el servidor entrega | R-UI T9 | **Informes de M5**: los informes no existen; cuando existan deberán usar la misma política |
| CA-20 | RF-83 | M4-02 | **Parcial** | Consultas (M4-01, M4-02, M4-03, M4-04), acceso directo (M2-07, M2-08, M3-07 devuelven 404 sobre lo ajeno) y auditoría: B1, B2, B4, B5, B6 | — | R-INT T1 a T6 | **Informes de M5** |
| CA-21 | RF-24 | M4-01 | Implementado y probado | B1 `inexistente_y_no_autorizado_son_indistinguibles`; BM1 `traslado_e2e` | F-E | R-INT T1 | — |
| CA-176 | RF-66 | M4-01 | Implementado y probado | B1 `quien_se_incorpora_despues_lee_lo_del_equipo_en_esa_fecha_pero_no_lo_del_otro` | — | R-INT T1 | — |
| CA-177 | RF-66 | M4-01 | Implementado y probado | B1 ídem | — | R-INT T1 | — |
| CA-178 | RF-25 | M4-01 | Implementado y probado | B6 `las_seis_escrituras…` (incluida la supervisora de T sobre una actividad de una persona ya pasada a U); M4 no tiene rutas de escritura | — | R-INT T6 | Reconciliada con M1 (sección 4) |
| CA-215 | RF-92 | M4-04 | Implementado y probado | B5 `el_supervisor_del_equipo_nuevo_no_obtiene_titulo_descripciones_ni_motivos_del_equipo_anterior`; B1 `el_equipo_nuevo_ve_la_actividad_heredada_en_forma_neutral…` | F-S | R-UI T9 | — |
| CA-216 | RF-97 | M4-01 | Implementado y probado | **B1 `una_planificacion_de_una_fecha_posterior_al_traslado_es_del_equipo_nuevo_aunque_se_registrara_antes`** (nueva en M4-T9) | — | — | — |
| CA-217 | RF-97 | M4-01 | Implementado y probado | B1 ídem | — | — | — |
| CA-268 | RF-111 | M4-03 | Implementado y probado | B4 `una_actividad_marcada_por_error_no_aparece_de_ninguna_forma_en_ningun_equipo`; B1 `una_actividad_marcada_por_error_de_otro_equipo_no_aparece_ni_sus_registros`; B5 | — | R-INT T4 | — |

> Nota de recuento: CA-15 a CA-21 son 7, CA-176 a CA-178 son 3, CA-215 a CA-217 son 3 y CA-268 es 1: 14 criterios. Los criterios de esta sección que no son propios de M4 siguen perteneciendo a sus historias; aquí solo se anota su evidencia de M4.

## 4. Criterios relacionados fuera de los 61 y reconciliación con las matrices previas

La matriz de M1 y la de M2/M3 son registros de su fecha de cierre y **no se reescriben**. Este apartado y las adendas que se añaden a cada una dejan constancia de la evidencia nueva. Ninguna clasificación de M1 «implementado y probado» se cambia.

| CA | Estado previo (matriz) | Estado con la evidencia de M4 | Evidencia nueva | Observación |
|---|---|---|---|---|
| CA-03 | Parcial (M1-01c): el rol se distingue | **Implementado y probado** | B3 `un_colaborador_recibe_403…`; F-S «a supervisor is offered "Supervisión"; a collaborator is not»; R-UI T8 y T9 (el colaborador no tiene la opción; la petición directa recibe 403 sin datos) | La limitación anterior («la vista no existe») desaparece |
| CA-04 | Bloqueado por M4 | **Implementado y probado** | B3, B4; F-S; R-UI T8 y T9 | El supervisor dispone de la vista consolidada de su equipo |
| CA-05 | Parcial (M1): sin informes | **Parcial** (sin cambio de estado) | Las respuestas de M4 usan listas cerradas de campos; ninguna lleva credenciales, correo, identificador de acceso ni datos de autenticación (B2, B3, B5, B7; R-UI T9, comprobación de campos del contrato M4-03) | Los informes (M5) siguen sin existir |
| CA-30 | Parcial (M1) | **Implementado y probado** | B1 y B2 `los_registros_de_personas_finalizadas_o_desactivadas_siguen_…`; B3 (la propietaria ya fuera del equipo no tiene estado actual); B7 (quien tiene el acceso desactivado sigue listado) | Vinculado a M4-01 y M4-02 el 2026-11-17 |
| CA-256 | Parcial (M1) | **Implementado y probado** | B1 y B2 ídem; BM1 `desactivacion::ca256…` | La visibilidad por «persona autorizada» ajena es ahora una consulta HTTP real |
| CA-111 | Bloqueado por M4 (M3-07) | **Implementado y probado** | B6 `el_supervisor_consulta_la_auditoria_del_equipo_de_cada_registro_y_nadie_mas`; R-UI T8 y T9 (auditoría desde el historial) | Resuelto en M4-T6 |
| CA-112 | Implementado y probado (propietaria) | Implementado y probado, ampliado | B6 | Un compañero no consulta la auditoría ajena |
| CA-113 | Implementado y probado (propietaria) | Implementado y probado, ampliado | B6 `el_supervisor_trasladado_o_desactivado_pierde_la_autorizacion` | El supervisor de otro equipo recibe 404 (R-UI T9) |
| CA-212, CA-213, CA-214 | Implementado y probado (M1-T5) | Sin cambios | BM1 `traslado_e2e` | M4 no los modifica |
| CA-249 | M1: implementado y probado · M2/M3: «consulta HTTP de M4» (hallazgo H-1) | **Implementado y probado** — **H-1 resuelto** | B1 `con_un_traslado_programado_para_manana_la_bitacora_de_hoy_sigue_siendo_del_equipo_anterior` (nueva en M4-T9); BM1 `traslado_e2e`, `traslados` | No había contradicción: la política ya era correcta; faltaba la prueba de la consulta ajena, ahora ejecutada |
| CA-260, CA-261 | Implementado y probado (M1-08) | Sin cambios; M4 añade: un colaborador de un equipo sin supervisión efectiva recibe 403 en M4-03 y M4-04, y conserva la lectura entre pares | B3 `un_colaborador_recibe_403_y_nadie_mas_supervisa_aunque_el_supervisor_este_desactivado`; B5 `un_supervisor_con_el_acceso_desactivado_no_consulta_y_nadie_hereda_su_permiso`; B1 | La vista no informa del equipo pendiente ni propone sustituto |
| CA-72, CA-183, CA-208, CA-101, CA-107, CA-118, CA-123, CA-127 | Implementado y probado (M2/M3) | Siguen cumpliéndose; el código sobre lo visible ajeno pasa de 404 a 403 | B6; pruebas antiguas actualizadas a propósito (lista cerrada en el plan, M4-T6) | M2-07 conserva su 404 por contrato (D-M4-10) |

**Resultado de la reconciliación.** No hay contradicciones reales con M1 ni con M2/M3. Los desfases eran de dependencia («sin consulta ajena hasta M4») y se resuelven con evidencia nueva. CA-178 se anota **implementado y probado** en esta matriz (en la de M1 consta «parcial»: su nota ya recoge la evidencia de M4-T6).

## 5. Lo que sigue dependiendo de M5

| Criterio | Qué falta |
|---|---|
| CA-19, CA-20 | Que los informes (individuales y consolidados) excluyan los registros anteriores al traslado de la persona. M4 deja la política y las proyecciones listas (RA-09); su uso por la IA es de M5 y requiere la revisión SDD de M5 |
| CA-05 | Que los informes no contengan credenciales en claro |
| Informes (CA-02, CA-05) | Bloqueados por M5, sin cambio |

La integración con Amazon Bedrock y AWS Lambda decidida el 2026-11-18 es solo para planificación futura de M5: M4 no la implementa ni la configura.

## 6. Decisiones de M4 y estado

D-M4-01 a D-M4-09 `[CONFIRMADO]` el 2026-11-17 y D-M4-10 `[CONFIRMADO]` el 2026-11-18 (PA-32, resuelto). Ninguna decisión de M4 queda abierta. Siguen abiertos los puntos transversales que no son de M4: PA-13 (volumen y límites de rendimiento), PA-24 (reincorporación) y los de M5.

## 7. Resultados de las pruebas del cierre (M4-T9)

| Prueba | Resultado |
|---|---|
| Regresión completa del backend (una vez, PostgreSQL desechable) | **2.987 superadas, 1 omitida** (la entrada `ERROR_INTERNO` de `test_errores.py`, que se prueba en el caso de fallo interno) |
| Pruebas añadidas después de esa regresión (`test_consulta_bitacora.py`, CA-216/CA-217 y CA-249) | El archivo completo: **18 superadas** |
| `flutter analyze` | **Sin incidencias** |
| Regresión completa de Flutter (una vez) | **706 superadas** (tras la corrección del defecto de la sección 8; las 3 pruebas nuevas figuran en esa cifra) |
| Revisión de Git | `git diff --check` sin errores (solo avisos de fin de línea del propio Git); sin secretos añadidos |

No se ejecutaron mutaciones.

## 8. Defecto encontrado y corregido en M4-T9

| Campo | Contenido |
|---|---|
| **Defecto** | Tras un rechazo del servidor (403 `OPERACION_NO_PERMITIDA` o `ACCESO_DESACTIVADO`, por pérdida del rol o desactivación) al repetir una consulta idéntica, la pantalla conservaba **los datos cargados antes**, porque el proveedor de Riverpod seguía con valor previo (`hasValue` verdadero junto con el error) y no se volvía a consultar |
| **Riesgo** | Datos de un compañero visibles después de perder la autorización |
| **Corrección** | Las páginas de «Mi equipo» (bitácora, histórico), la supervisión y el historial de la actividad muestran el estado de carga y de error **antes** que el valor previo, e invalidan el proveedor en cada consulta nueva: preguntar es siempre preguntar al servidor. Archivos: `team_page.dart`, `supervision_page.dart`, `supervision_activity_page.dart` |
| **Pruebas** | Escritas antes de la corrección (fallaban con 1 petición en lugar de 2): 3 pruebas de widget en el grupo «losing the authorization while looking at data» de `supervision_page_test.dart` y `team_page_test.dart` |
| **Comprobación real** | R-UI T9: desactivación y pérdida del rol de supervisor en plena sesión: se muestra el texto fijo del rechazo y no queda ningún dato anterior |

No hubo otros defectos de producto: los fallos intermedios del recorrido fueron de los scripts de prueba (parámetro de teclado, clic sobre una etiqueta y no sobre el campo de fecha) y se corrigieron sin cambiar el producto.

## 9. Recorrido integral real (R-UI T9)

FastAPI sirviendo el cliente compilado, Chrome real controlado por CDP y PostgreSQL desechable (`smartwork_m4t9_dev`, ya eliminada, solo en el clúster de pruebas, nunca el puerto 5432). Migraciones 0001 a 0018 aplicadas desde cero. Equipos T y U: Sara supervisa T; Tomás se incorporó a T hace 2 días; Ana, de T; Pablo pasó de T a U hace 3 días; Luis, de U a T hace 3 días; un supervisor de U. 23 bitácoras autorizadas (más de una página).

**25 comprobaciones, todas correctas; «no verificado en Chrome»: nada.**

| # | Comprobación |
|---|---|
| 1–2 | El colaborador tiene «Mi equipo» y no «Supervisión»; el selector ofrece solo a los integrantes vigentes |
| 3 | CA-193: lee la bitácora de Ana de una fecha anterior a su incorporación, eligiéndola en el selector de fecha |
| 4–7 | Histórico: primera página con «Ver más», registros de quien ya salió (sin su nombre), «Ver más» sigue el cursor sin repetir, nada del otro equipo |
| 8 | El filtro por persona devuelve solo lo de esa persona |
| 9–10 | Desactivación en plena sesión: la siguiente consulta se rechaza con su texto fijo y no queda ningún dato; un acceso desactivado no inicia sesión |
| 11–13 | Respuestas HTTP de la supervisión: ningún dato protegido (listas, totales, recuento), campos exactos del contrato, cursor opaco que no da nada protegido |
| 14, 16 | La actividad de otro equipo y una inexistente responden el mismo 404; la auditoría de otro equipo, 404 uniforme |
| 15 | Un colaborador recibe 403 sin datos |
| 17–18 | La supervisora ve la vista consolidada con actividad completa, neutral, referencia mínima y estado al corte «No disponible», sin nada del otro equipo |
| 19–20 | Historial autorizado de una actividad y su auditoría |
| 21–22 | Teclado: con Tab se alcanza «Ver supervisión» y con Enter se acciona |
| 23 | Pérdida del rol de supervisor en plena sesión: 403 con texto fijo y ningún dato anterior |
| 24–25 | La supervisión del equipo nuevo recibe la actividad de la persona trasladada como «Actividad en continuidad», sin título ni registros del equipo anterior |

Los traslados en ambos sentidos, la referencia mínima con y sin estado actual y la actividad completa con auditoría se comprobaron además en el recorrido de M4-T8 (28 comprobaciones); no se repiten aquí porque no aportan evidencia de integración nueva.

## 10. Revisión básica de accesibilidad y experiencia (proporcionada, sin rediseño)

> **Nota posterior (2026-11-19).** Las pantallas de Mi equipo y Supervisión se rediseñaron después de esta revisión (lista de integrantes y detalle, filas densas con «Estado al corte» y «Estado actual» diferenciados), sin cambiar contratos, visibilidad histórica ni permisos. La tabla siguiente describe la revisión original; el diseño adaptable se volvió a comprobar con pruebas de widget a 1400, 900 y 400 px.

| Aspecto | Resultado |
|---|---|
| Teclado | Con Tab se llega a los controles de la supervisión y Enter acciona la consulta (comprobado en Chrome). No se recorrieron con teclado todas las pantallas |
| Etiquetas de los controles | Los campos y botones tienen etiqueta textual (los recorridos los localizan por su etiqueta en el árbol de accesibilidad de Flutter) |
| Mensajes de error | Textos fijos y distintos para acceso desactivado, operación no permitida, rango, conexión y «no disponible»; nunca el mensaje del servidor |
| Estados vacíos | Hay un estado vacío propio en el histórico, la supervisión, la lista de compañeros y el historial |
| Diseño adaptable | Probado en móvil, tableta y escritorio sin desbordes (pruebas de widget); el recorrido móvil de T7 y T8 usó «Abrir menú» |
| Datos tras un rechazo | Corregido (sección 8): no queda nada visible tras perder la autorización |

**Mejoras no bloqueantes** (no incumplen ningún criterio obligatorio): (1) no se probó con lectores de pantalla ni con otros navegadores; (2) el rol se lee al iniciar sesión, así que si se pierde durante la sesión la opción del menú permanece hasta recargar (toda petición recibe 403 y la pantalla lo dice); (3) «Persona que ya no está en tu equipo» no distingue entre varias personas que salieron; (4) al volver del historial se pierden las páginas posteriores a la primera de la supervisión; (5) la navegación entre supervisión, historial y auditoría podría mostrar un rastro de ubicación; (6) la identificación visual de lo histórico frente a lo actual puede reforzarse.

## 11. Migraciones, rendimiento y seguridad

- **Migraciones.** Una sola cabeza, `0018`. M4 solo añadió la 0018 (`bitacora_historico_idx` sobre `bitacora (fecha_laboral, persona_id, id)`, aprobada y aplicada en M4-T2, reversible). Ninguna otra migración es necesaria: no hay tablas ni columnas que falten. El recorrido T9 partió de una base vacía y aplicó 0001 a 0018.
- **Rendimiento.** No hay cambios de consultas ni de código de backend desde las mediciones de M4-T2 y M4-T3, por lo que se reutilizan: histórico con 157.191 bitácoras, 338 ms a 2,6 ms con el índice (peor caso 328 a 71 ms); supervisión con 157.040 bitácoras y 31.408 actividades, 63 s (primera versión descartada) a unos 90–120 ms por consulta de 92 días. Sin evidencia de un riesgo crítico nuevo.
- **Seguridad.** Autorización previa a la selección de datos con la política de M1 (no hay política paralela); filtrado también en recuentos, totales y cursores (R-INT y R-UI T9: ninguna respuesta lleva datos protegidos); 404 indistinguible para lo inexistente y lo no autorizado y 403 solo por rol sobre una función o sobre lo visible; reglas neutral y de referencia mínima con listas cerradas de campos; permisos de supervisión efectivos (el supervisor desactivado o trasladado y los colaboradores de un equipo sin supervisión no supervisan); ningún endpoint de M4 escribe; la auditoría del supervisor no incluye datos administrativos ni técnicos; sin secretos en el código ni en la documentación.

## 12. Riesgos que dependen del despliegue, el volumen o decisiones futuras

1. Límite de tasa de lecturas y canal de temporización entre 403 y 404: no analizados ni implementados (despliegue).
2. El historial de una actividad (M4-04) no está paginado: una actividad con miles de avances devuelve todos (PA-13).
3. La lista de integrantes (M4-05) no incluye a quienes salieron; no hay directorio histórico (limitación aprobada, D-M4-02). Con equipos muy grandes el selector carga hasta 20 páginas de 100.
4. La referencia mínima (200) frente a un 404 revela que la actividad es de una persona del equipo y está pendiente: es lo que D-09 y RN-84 piden.
5. Un supervisor desactivado deja el equipo sin vista de supervisión hasta que se provea otro (M1, CA-260/CA-261): M4 no propone sustituto (DD-04).
6. El estado de Flutter vive en memoria; no se probó con otros navegadores ni lectores de pantalla.

## 13. Veredicto

**M4 cerrado con reservas.** Los 61 criterios vinculados tienen evidencia ejecutada: 59 están implementados y probados y 2 (CA-19 y CA-20) son parciales por su dependencia de los informes de M5. No hay defectos bloqueantes abiertos; el defecto encontrado (datos anteriores visibles tras un rechazo) está corregido y probado. Las reservas son las dependencias de M5, las mejoras no bloqueantes de la sección 10 y los riesgos de despliegue y volumen de la sección 12. Ningún criterio se declara cumplido sin la evidencia citada.
