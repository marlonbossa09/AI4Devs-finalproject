# SMARTWORK — Matriz de trazabilidad y cobertura: M1 (Acceso y equipos)

| Campo | Contenido |
|---|---|
| **Naturaleza** | Evidencia de la implementación. No define requisitos: los requisitos viven en `docs/` (alcance, PRD, historias y contratos) |
| **Fecha** | 2026-11-17 (cierre técnico de M1, M1-T9) |
| **Alcance** | Los 65 criterios de aceptación de las historias HU-1.1 a HU-1.7 y los 14 contratos de M1 (`docs/api/m1-acceso-usuarios-equipos.md`), tal como están implementados en la fecha indicada |
| **Fuente de los criterios** | `docs/backlog/M1-autenticacion-usuarios-equipos/` y los contratos de M1 («Criterios vinculados») |
| **Relación con otras matrices** | `docs/evidencia/matriz-trazabilidad-m2-m3.md` cubre M2 y M3; el anexo parcial de M1-T8 que contiene queda sustituido por esta matriz |
| **Fuera de alcance** | M4 y M5: sus criterios no se evalúan aquí. Se indican las dependencias que M1 deja para ellos (sección 6) |

## 1. Cómo leerla

Cada fila es **criterio → contrato → estado → evidencia**. Un criterio **solo se declara implementado y probado cuando hay una prueba o una verificación real que lo demuestra**; cuando solo se demuestra una parte (la regla, pero no su consulta, que es de otro módulo) se declara parcial y se dice qué falta.

| Estado | Significado |
|---|---|
| **Implementado y probado** | El comportamiento del criterio es observable hoy en el producto y tiene evidencia |
| **Implementado parcialmente** | La regla o parte del criterio está implementada y probada; otra parte depende de algo que no existe todavía |
| **Pendiente** | Sin implementar y sin evidencia |
| **Fuera de alcance aprobado** | Excluido por una decisión aprobada |
| **Bloqueado por otro módulo o por despliegue** | Su comportamiento observable depende de otro módulo (M4, M5) o de la instalación en el despliegue |

**Evidencia.** **B** pruebas del backend (`archivo::prueba`, en `backend/tests/`; todas las pruebas citadas existen: se comprobó por nombre). **F** pruebas de Flutter. **D** garantía en la base de datos. **R85** recorrido real de M1-T8.5 (Chrome, escritorio y móvil). **R9** recorrido integral de M1-T9 (CLI real, HTTP real y Chrome, sobre FastAPI, Flutter Web compilado y PostgreSQL desechable; sección 5). **R-T5** verificación de extremo a extremo con un traslado oficial de M1-T5.

## 2. Resumen

**65 criterios:** 48 implementados y probados, 15 implementados parcialmente, 0 pendientes, 0 fuera de alcance aprobado y 2 bloqueados por otro módulo. **Contratos:** 13 implementados y probados y 1 fuera de alcance aprobado (M1-10).

| Historia | Criterios | Implementado y probado | Parcial | Pendiente | Fuera de alcance | Bloqueado |
|---|---|---|---|---|---|---|
| HU-1.1 Identificarme para acceder | 5 | 1 | 2 | 0 | 0 | 2 |
| HU-1.2 Pertenecer a un único equipo con un único supervisor | 8 | 8 | 0 | 0 | 0 | 0 |
| HU-1.3 Asignar pertenencias y conservar las anteriores | 12 | 12 | 0 | 0 | 0 | 0 |
| HU-1.4 Visibilidad histórica de los registros tras un cambio de equipo | 17 | 6 | 11 | 0 | 0 | 0 |
| HU-1.5 Crear usuarios y equipos y entregar el primer acceso | 9 | 9 | 0 | 0 | 0 | 0 |
| HU-1.6 Recuperar el acceso | 3 | 3 | 0 | 0 | 0 | 0 |
| HU-1.7 Dar de baja lógicamente a una persona | 11 | 9 | 2 | 0 | 0 | 0 |
| **Total** | **65** | **48** | **15** | **0** | **0** | **2** |

Los criterios parciales y bloqueados lo son **por la ausencia de M4** (consulta ajena, vista consolidada, supervisión) **o de M5** (informes), no por un defecto de M1: la regla que M4 necesita (la política de visibilidad histórica) está implementada y probada, pero ninguna ruta la usa todavía.

## 3. Matriz por criterio


### HU-1.1 — Identificarme para acceder

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-01 | Sin identificar no se muestra ningún dato | M1-01a, M1-01c | **Implementado y probado** | B: acceso::sin_sesion_no_se_muestra_ningun_dato; bitacoras_api::sin_sesion_no_se_muestra_ninguna_bitacora · R9: una petición sin sesión recibe 401 |  |
| CA-02 | Sin identificar no se genera un informe | — | **Bloqueado por otro módulo o por despliegue** | Sin evidencia propia: no existen informes | Depende de M5. La sesión es obligatoria en todas las rutas existentes (CA-01). |
| CA-03 | El colaborador no dispone de la vista consolidada del equipo | M1-01c | **Implementado parcialmente** | B: acceso::el_rol_vigente_distingue_colaborador_y_supervisor · R9: la sesión de la colaboradora informa su rol | El rol se distingue y se expone. La vista consolidada no existe todavía (M4): hoy ningún rol la tiene. |
| CA-04 | El supervisor dispone de la vista consolidada de su equipo | M1-01c | **Bloqueado por otro módulo o por despliegue** | B: acceso::el_rol_vigente_distingue_colaborador_y_supervisor (solo el rol) · R9 | La vista consolidada es de M4 (visibilidad histórica y acceso del supervisor). |
| CA-05 | Ninguna pantalla, registro ni informe contiene credenciales en claro | M1-01a, M1-03b, M1-09b | **Implementado parcialmente** | B: acceso::ninguna_respuesta_ni_registro_contiene_la_contrasena; canje_primer_acceso::ni_las_respuestas_ni_los_registros_contienen_el_codigo_el_hash_ni_la_contrasena; contrasenas_comprometidas::ninguna_contrasena_hash_ni_codigo_queda_en_los_registros_ni_en_la_auditoria, un_fallo_de_la_base_durante_el_canje_no_registra_el_hash…; login_intentos_api (tablas y registros) · F: el código y las contraseñas viven solo en los campos de la pantalla (revisión T8.6, sin almacenamiento persistente) · R9: auditoría, eventos y registro del servidor sin secretos | Los informes (M5) no existen. En T8.6 se corrigió un defecto real: un error de la base registraba el hash Argon2 y el HMAC del código. |

### HU-1.2 — Pertenecer a un único equipo con un único supervisor

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-06 | Cada equipo agrupa a sus propias personas | M1-02b | **Implementado y probado** | B: provision::un_equipo_se_crea_en_una_organizacion_existente_y_nace_sin_supervisor, la_persona_se_crea_con_identidad_sin_contrasena_y_pertenencia_desde_la_fecha_indicada; db_pertenencias · R9 | Según el contrato aprobado se verifica con la respuesta de M1-02b y de M1-05; no existe una consulta pública de la composición (sin contrato). |
| CA-07 | Una persona no pertenece a dos equipos a la vez | M1-02b, M1-05 | **Implementado y probado** | B: provision::un_supervisor_solo_supervisa_un_equipo_y_cada_persona_tiene_un_unico_equipo; db_pertenencias::dos_intervalos_solapados_de_una_persona_fallan_en_la_base_de_datos; traslados::ca14_… · D |  |
| CA-08 | Un equipo no tiene dos supervisores | M1-02b, M1-05 | **Implementado y probado** | B: provision::un_segundo_supervisor_no_se_asigna_a_un_equipo_que_ya_tiene_supervisor; db_pertenencias::dos_supervisores_simultaneos_de_un_equipo_fallan; traslados::dos_supervisores_a_la_vez_se_rechazan · R9 |  |
| CA-09 | El supervisor figura como miembro del equipo que supervisa | M1-02b | **Implementado y probado** | B: provision::el_primer_integrante_de_un_equipo_es_su_supervisor_y_un_colaborador_se_une_despues · R9 | Según el contrato aprobado se verifica con la respuesta de M1-02b (pertenencia con equipo y rol). No hay consulta pública de composición; M4 la necesitará. |
| CA-10 | Un supervisor no supervisa otro equipo a la vez | M1-02b, M1-05 | **Implementado y probado** | B: provision::un_supervisor_solo_supervisa_un_equipo_y_cada_persona_tiene_un_unico_equipo; traslados::dos_supervisores_pueden_intercambiar_sus_equipos_en_una_sola_operacion |  |
| CA-240 | No se finaliza al único supervisor de un equipo con colaboradores | M1-06 | **Implementado y probado** | B: programacion::ca240_no_se_finaliza_al_unico_supervisor_de_un_equipo_con_colaboradores; programacion_cli::las_ordenes_rechazadas_devuelven_un_codigo_estable_y_no_dejan_nada · R9 |  |
| CA-241 | No se traslada al único supervisor sin relevo | M1-05 | **Implementado y probado** | B: traslados::ca241_trasladar_al_unico_supervisor_de_un_equipo_con_colaboradores_se_rechaza_sin_cambios, ca241_relevo_que_deja_sin_supervisor_al_equipo_de_origen_del_entrante · R9 |  |
| CA-242 | El relevo de supervisor se acepta sin días sin supervisor | M1-05, M1-06 | **Implementado y probado** | B: traslados::ca242_el_relevo_de_supervisor_acepta_y_el_equipo_no_queda_ningun_dia_sin_supervisor; programacion::el_relevo_de_un_supervisor_que_se_finaliza_es_una_sola_operacion_atomica |  |

### HU-1.3 — Asignar pertenencias y conservar las anteriores

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-11 | Asignar la pertenencia de una persona sin equipo | M1-02b | **Implementado y probado** | B: provision::la_persona_se_crea_con_identidad_sin_contrasena_y_pertenencia_desde_la_fecha_indicada; traslados::ca11_una_persona_recien_creada_en_una_fecha_futura_se_puede_trasladar_despues_de_su_inicio · R9 |  |
| CA-12 | Un cambio de equipo la deja en el nuevo y fuera del anterior | M1-05 | **Implementado y probado** | B: traslados::ca12_la_persona_figura_en_el_equipo_nuevo_y_deja_de_figurar_en_el_anterior; traslado_e2e::el_traslado_oficial_cierra_la_pertenencia_en_t_y_abre_la_de_u_sin_tocar_los_registros_de_m2 |  |
| CA-13 | El historial de pertenencias conserva los equipos anteriores y sus fechas | M1-05 | **Implementado y probado** | B: traslados::ca13_la_respuesta_trae_el_historial_completo_de_cada_persona_afectada, las_pertenencias_anteriores_se_conservan_intactas_y_solo_se_cierra_la_ultima · R9 | Según el contrato aprobado se verifica con la respuesta de M1-05; no existe una consulta pública del historial (sin contrato). |
| CA-14 | Tras el cambio pertenece a un único equipo | M1-05 | **Implementado y probado** | B: traslados::ca14_en_cada_fecha_la_persona_pertenece_a_un_unico_equipo_incluidos_traslados_sucesivos · D |  |
| CA-243 | Un traslado ordinario no admite fecha efectiva de hoy o anterior | M1-05 | **Implementado y probado** | B: traslados::ca243_una_fecha_efectiva_igual_o_anterior_a_hoy_se_rechaza_y_la_posterior_se_acepta; traslados::la_fecha_actual_la_da_un_reloj_inyectable_y_se_mide_en_la_zona_de_la_organizacion · R9 |  |
| CA-244 | Cancelar un traslado programado deja a la persona en su equipo y conserva la auditoría | M1-07 | **Implementado y probado** | B: programacion::ca244_cancelar_un_traslado_programado_deja_a_la_persona_en_su_equipo_y_conserva_la_auditoria; traslado_e2e::el_traslado_cancelado_antes_de_su_fecha_efectiva_deja_a_la_persona_trabajando_en_t_en_esa_fecha · R9 |  |
| CA-245 | Una operación ya efectiva no se cancela ni se sustituye | M1-07 | **Implementado y probado** | B: programacion::ca245_una_operacion_ya_efectiva_no_se_cancela_en_el_limite_exacto_de_hoy, ca245_el_alta_de_hoy_y_las_operaciones_pasadas_ya_son_efectivas; programacion_cli::las_ordenes_rechazadas_devuelven_un_codigo_estable… |  |
| CA-246 | Una cancelación que deja un equipo sin supervisor se rechaza | M1-07 | **Implementado y probado** | B: programacion::ca246_cancelar_solo_una_mitad_de_un_relevo_se_rechaza_sin_cambios |  |
| CA-247 | Sustituir un traslado deja vigente solo el nuevo y conserva ambas operaciones | M1-07 | **Implementado y probado** | B: programacion::ca247_sustituir_un_traslado_deja_vigente_solo_el_nuevo_y_la_auditoria_conserva_ambas_operaciones · R9 |  |
| CA-248 | Cada fecha laboral tiene un único equipo, sin solapes ni huecos | M1-05, M1-06 | **Implementado y probado** | B: traslados::ca248_la_linea_temporal_resultante_no_tiene_solapes_ni_huecos; traslado_e2e::no_hay_ni_huecos_ni_solapes_las_dos_pertenencias_cubren_cada_fecha_desde_el_inicio · D: exclusión de solapes · R9 |  |
| CA-278 | Cancelar un alta futura deja a la persona sin pertenencia | M1-07 | **Implementado y probado** | B: programacion::ca278_cancelar_un_alta_futura_deja_a_la_persona_sin_pertenencia_y_sin_poder_operar |  |
| CA-279 | Cancelar un cambio de rol programado conserva el rol | M1-07 | **Implementado y probado** | B: programacion::ca279_cancelar_un_cambio_de_rol_programado_conserva_el_rol_y_el_cruce_se_cancela_junto |  |

### HU-1.4 — Visibilidad histórica de los registros tras un cambio de equipo

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-15 | El equipo anterior consulta lo anterior al traslado de P | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada, el_supervisor_de_un_equipo_anterior_conserva_lo_de_su_equipo_y_no_lo_ajeno; traslado_e2e::la_politica_de_visibilidad_de_m1_t1_decide_por_el_equipo_de_cada_fecha_antes_y_despues_del_traslado | Política interna implementada y probada (M1-T1). Ninguna ruta de consulta ajena la usa todavía: depende de M4. |
| CA-16 | El equipo nuevo no consulta lo anterior al traslado | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada | Política probada; sin consulta ajena hasta M4. |
| CA-17 | El equipo anterior no consulta lo posterior al traslado | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada, el_supervisor_de_un_equipo_anterior_conserva_lo_de_su_equipo_y_no_lo_ajeno | Política probada; sin consulta ajena hasta M4. |
| CA-18 | El equipo nuevo consulta lo posterior al traslado | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada | Política probada; sin consulta ajena hasta M4. |
| CA-19 | Informes y consultas del equipo nuevo excluyen lo anterior al traslado | — | **Implementado parcialmente** | B: visibilidad_historica::el_predicado_sql_selecciona_exactamente_lo_que_decide_la_politica, propiedad_la_politica_y_el_predicado_coinciden_con_el_modelo_y_no_filtran_entre_organizaciones_ni_periodos | Predicado de lectura probado; sin consultas de equipo (M4) ni informes (M5). |
| CA-20 | Ninguna vía entrega al equipo nuevo un registro anterior al traslado | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura…, quien_no_puede_operar_no_selecciona_nada; traslado_e2e::ninguna_otra_persona_accede_a_la_actividad_ni_antes_ni_despues_del_traslado | Hoy todo recurso ajeno responde 404; la política decidirá cuando M4 y M5 existan. |
| CA-21 | Un colaborador no consulta un registro de otro equipo | — | **Implementado y probado** | B: traslado_e2e::ninguna_otra_persona_accede_a_la_actividad_ni_antes_ni_despues_del_traslado; visibilidad_historica::nadie_cruza_organizaciones · R9: el supervisor recibe 404 de una actividad ajena |  |
| CA-176 | Quien se incorporó después al equipo anterior lee su histórico | — | **Implementado parcialmente** | B: visibilidad_historica::quien_se_incorporo_despues_lee_el_historico_de_su_equipo_pero_no_el_de_otro | Política probada; sin consulta ajena hasta M4. |
| CA-177 | Esa persona no lee el histórico del equipo nuevo | — | **Implementado parcialmente** | B: visibilidad_historica::quien_se_incorporo_despues_lee_el_historico_de_su_equipo_pero_no_el_de_otro | Política probada; sin consulta ajena hasta M4. |
| CA-178 | Un integrante del equipo anterior no modifica registros de P | — | **Implementado parcialmente** | B: visibilidad_historica::la_politica_no_escribe_nada; las rutas de M2 y M3 son solo propias (`/mi/…`) | Toda escritura es de la propietaria; no hay escritura ajena. La política de supervisión de M4 deberá mantenerlo. **M4-T6 (2026-11-18) aporta evidencia:** las escrituras de M2 y M3 sobre un registro de una persona trasladada, desde su equipo anterior, responden 403 y no cambian nada; la clasificación formal se revisa en la matriz de M4-T9. |
| CA-212 | La actividad sigue siendo la misma al cambiar de equipo | M1-05 con M2 | **Implementado y probado** | B: traslado_e2e::ca212_la_actividad_iniciada_en_t_sigue_siendo_la_misma_y_de_su_propietaria_tras_pasar_a_u, ca212_el_equipo_historico_de_la_actividad_sigue_siendo_t_y_el_actual_de_su_propietaria_es_u · R-T5 |  |
| CA-213 | Un avance en el equipo nuevo no crea otra actividad | M1-05 con M2 | **Implementado y probado** | B: traslado_e2e::ca213_un_avance_registrado_en_u_no_crea_otra_actividad, ca213_el_avance_en_u_se_valida_con_las_mismas_reglas_de_la_actividad · R-T5 |  |
| CA-214 | El historial de la actividad muestra los avances de ambos equipos | M1-05 con M2 | **Implementado y probado** | B: traslado_e2e::ca214_la_propietaria_ve_en_u_todos_los_avances_de_la_actividad_los_de_t_y_los_de_u, ca214_la_actividad_aparece_una_sola_vez_en_el_listado_con_su_estado_actual · R-T5 |  |
| CA-215 | El equipo nuevo no obtiene el contenido de una actividad iniciada antes | M1-05 con M2 | **Implementado y probado** | B: traslado_e2e::ninguna_otra_persona_accede_a_la_actividad_ni_antes_ni_despues_del_traslado; visibilidad_historica::forma_de_una_actividad_segun_la_jornada_de_origen | La forma que la política dará a M4 (sin título ni descripciones de la jornada de origen) está probada a nivel de dominio. |
| CA-216 | Una planificación futura ya registrada la consulta el equipo de su fecha | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada | Política probada; sin consulta ajena hasta M4. |
| CA-217 | El equipo anterior no consulta esa planificación | — | **Implementado parcialmente** | B: visibilidad_historica::matriz_de_lectura_de_los_registros_de_una_persona_trasladada | Política probada; sin consulta ajena hasta M4. |
| CA-249 | Antes de la fecha efectiva la bitácora sigue siendo del equipo anterior | M1-05 | **Implementado y probado** | B: traslado_e2e::antes_de_la_fecha_efectiva_la_persona_sigue_en_t_aunque_el_traslado_ya_este_registrado; traslados::la_politica_de_visibilidad_usa_el_equipo_de_cada_fecha_tras_un_traslado_real · R9 |  |

### HU-1.5 — Crear usuarios y equipos y entregar el primer acceso

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-22 | La provisión crea la persona y el equipo y la persona accede con su primer acceso | M1-02a, M1-02b, M1-03a, M1-03b | **Implementado y probado** | B: provision::la_persona_se_crea_con_identidad_sin_contrasena_y_pertenencia_desde_la_fecha_indicada; emision_codigos::el_primer_acceso_se_emite_se_muestra_una_vez_en_la_terminal_y_solo_se_guarda_su_hmac; canje_primer_acceso::el_primer_acceso_establece_la_contrasena_consume_el_codigo_y_no_abre_sesion, despues_del_canje_la_persona_inicia_sesion_con_su_contrasena_y_el_codigo_no_se_reutiliza · F: access_code_test · R85 y R9 (Chrome) |  |
| CA-23 | El primer acceso entregado permite acceder | M1-03b | **Implementado y probado** | B: canje_primer_acceso::despues_del_canje_la_persona_inicia_sesion_con_su_contrasena_y_el_codigo_no_se_reutiliza · F: access_code_test (primer acceso) · R85 y R9 (Chrome) |  |
| CA-24 | Un primer acceso ya utilizado no se puede usar de nuevo | M1-03b | **Implementado y probado** | B: canje_primer_acceso::despues_del_canje…_el_codigo_no_se_reutiliza, todas_las_causas_de_un_codigo_no_valido_dan_exactamente_la_misma_respuesta, dos_o_mas_canjes_simultaneos_del_mismo_codigo_dejan_exactamente_uno_efectivo · D: db_codigo_unico (uso único) · R9 |  |
| CA-25 | El primer acceso identifica solo a esa persona | M1-03b | **Implementado y probado** | B: canje_primer_acceso::ca25_el_codigo_de_una_persona_no_da_acceso_como_otra · R9 |  |
| CA-26 | El supervisor no dispone de funciones de provisión | M1-02a… M1-08 | **Implementado y probado** | B: provision_cli::no_existe_ningun_endpoint_http_de_provision; traslados_cli, programacion_cli, desactivacion_cli::no_existe_ninguna_ruta_http_…; emision_codigos::la_api_no_emite_codigos_ni_tiene_rutas_de_codigos · R9 | La provisión es solo de la CLI del servidor (A2): no hay ninguna ruta HTTP, para ningún rol. |
| CA-250 | Un equipo recién provisionado puede carecer de supervisor | M1-02a | **Implementado y probado** | B: provision::un_equipo_se_crea_en_una_organizacion_existente_y_nace_sin_supervisor; traslados::el_supervisor_de_un_equipo_sin_colaboradores_se_puede_trasladar · R9 |  |
| CA-251 | Toda provisión deja auditoría con autor, operación y valores, sin credenciales ni códigos | Todas las órdenes | **Implementado y probado** | B: provision::crear_un_equipo_deja_una_unica_entrada…, crear_una_persona_deja_una_unica_entrada_de_provision_sin_credenciales_ni_identificadores; traslados::ir35_una_sola_entrada…; emision_codigos::la_auditoria_de_la_emision_reutiliza_entrega_acceso…; desactivacion::una_unica_entrada_de_auditoria_de_provision_con_el_motivo_sin_secretos · R9 |  |
| CA-252 | La primera pertenencia con inicio de hoy o posterior se acepta | M1-02b | **Implementado y probado** | B: provision::la_fecha_de_inicio_igual_o_posterior_a_la_fecha_actual_se_acepta_y_la_anterior_se_rechaza · R9 |  |
| CA-253 | La primera pertenencia con inicio anterior a hoy se rechaza | M1-02b | **Implementado y probado** | B: provision::la_fecha_de_inicio_igual_o_posterior_a_la_fecha_actual_se_acepta_y_la_anterior_se_rechaza · R9 |  |

### HU-1.6 — Recuperar el acceso

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-27 | Recuperar el acceso con el procedimiento | M1-09a, M1-09b | **Implementado y probado** | B: emision_codigos::la_recuperacion_exige_declarar_la_verificacion_y_la_deja_estructurada_en_la_auditoria; canje_recuperacion::la_recuperacion_cambia_la_contrasena_revoca_todas_las_sesiones_y_no_abre_ninguna · F: access_code_test (recuperación) · R85 y R9 (Chrome) |  |
| CA-28 | El supervisor no dispone de la función de recuperar el acceso de otra persona | M1-09a | **Implementado y probado** | B: emision_codigos::la_api_no_emite_codigos_ni_tiene_rutas_de_codigos, ninguna_orden_acepta_un_codigo_ni_una_credencial_como_argumento · R9 | La recuperación se emite solo por la CLI del servidor y se canjea con el código. |
| CA-254 | Un acceso desactivado sigue desactivado tras la recuperación | M1-09a, M1-09b | **Implementado y probado** | B: canje_recuperacion::un_acceso_desactivado_no_se_reactiva_ni_cambia_su_contrasena; emision_codigos::a_un_acceso_desactivado_no_se_le_emite_ningun_codigo · R9 |  |

### HU-1.7 — Dar de baja lógicamente a una persona

| CA | Criterio | Contrato | Estado | Evidencia | Observación |
|---|---|---|---|---|---|
| CA-29 | Con el acceso desactivado o sin pertenencia vigente no se accede | M1-01a, M1-08 | **Implementado y probado** | B: acceso::con_el_acceso_desactivado_no_se_crea_sesion, sin_pertenencia_vigente_no_se_crea_sesion, tras_desactivar_el_acceso_la_siguiente_peticion_con_la_sesion_previa_se_rechaza; login_intentos_api::la_respuesta_con_el_acceso_desactivado_no_cambia… · R9 |  |
| CA-30 | Tras la baja los registros siguen siendo consultables según su pertenencia histórica | M1-06, M1-08 | **Implementado parcialmente** | B: programacion::ca30_tras_la_baja_los_registros_anteriores_siguen_siendo_de_su_equipo_y_la_planificacion_conservada_no_tiene_equipo; traslado_e2e::una_persona_finalizada_no_consulta_sus_registros_tras_la_fecha_efectiva_pero_estos_y_su_propiedad_se_conservan | La conservación y la pertenencia histórica están probadas; la consulta por «persona autorizada» ajena es de M4. |
| CA-31 | La baja no elimina ningún registro | M1-06, M1-08 | **Implementado y probado** | B: programacion::ca31_ninguna_bitacora_actividad_planificacion_ni_avance_se_elimina_ni_se_modifica, finalizar_conserva_el_historial_y_no_borra_nada; db_pertenencias::la_aplicacion_no_escribe_ni_borra_personas_ni_pertenencias · R9: bitácoras y actividades intactas tras desactivar |  |
| CA-255 | Con el acceso desactivado no se permite ninguna operación desde ese momento | M1-08 | **Implementado y probado** | B: desactivacion_api::ca255_las_sesiones_anteriores_a_la_desactivacion_dejan_de_servir_en_todas_las_operaciones, ca255_aunque_la_sesion_siguiera_vigente_el_servidor_rechaza_toda_peticion…, ca255_un_nuevo_inicio_de_sesion… · R9 |  |
| CA-256 | Tras desactivar, los registros anteriores no cambian (contenido, equipo histórico, visibilidad) | M1-08 | **Implementado parcialmente** | B: desactivacion::ca256_los_registros_y_su_visibilidad_no_cambian_con_la_desactivacion; desactivacion_api::ca256_… · R9 (conservación) | La visibilidad se prueba con la política interna; la consulta por «persona autorizada» ajena es de M4. |
| CA-257 | Con finalización desde F no se registra una bitácora de F en adelante | M1-06 | **Implementado y probado** | B: programacion::ca257_la_fecha_efectiva_exacta_ya_no_esta_cubierta_y_el_dia_anterior_si; traslado_e2e::una_persona_finalizada_no_consulta_sus_registros_tras_la_fecha_efectiva… |  |
| CA-258 | Una finalización no admite fecha efectiva de hoy o anterior | M1-06 | **Implementado y probado** | B: programacion::ca258_la_fecha_efectiva_debe_ser_posterior_a_hoy_en_el_limite_exacto; programacion_cli::las_ordenes_rechazadas_devuelven_un_codigo_estable… · R9 |  |
| CA-259 | Sin pertenencia vigente y sin desactivar tampoco se opera | M1-01a | **Implementado y probado** | B: acceso::sin_pertenencia_vigente_no_se_crea_sesion, al_terminar_la_pertenencia_la_sesion_previa_deja_de_operar |  |
| CA-260 | Desactivar al único supervisor se aplica y deja el equipo pendiente de supervisión efectiva | M1-08 | **Implementado y probado** | B: desactivacion::ca260_la_persona_conserva_su_pertenencia_historica_y_sigue_siendo_una_persona_del_equipo; desactivacion_api::ca260_el_unico_supervisor_se_desactiva_con_advertencia_y_su_pertenencia_se_conserva; desactivacion::la_advertencia_queda_en_la_auditoria_y_la_pertenencia_historica_se_conserva · R9 | Clasificación aclarada: «identificado como pendiente de supervisión efectiva» significa, según el contrato aprobado (M1-08, DM-09, RN-98), la **advertencia estructurada** en el resultado de la orden y en la auditoría y la **condición calculada** con las reglas de supervisión efectiva; no es un estado persistente ni hay una consulta de esa condición por API (la consume M4). Se cumple lo que el contrato define; el uso de la condición por la supervisión queda para M4. |
| CA-261 | Un equipo pendiente no concede permisos de supervisión a los colaboradores | M1-08 | **Implementado y probado** | B: desactivacion::ca261_un_equipo_pendiente_no_concede_permisos_de_supervision_a_nadie; desactivacion_api::ca261_los_colaboradores_del_equipo_pendiente_no_reciben_funciones_de_supervision; desactivacion::no_se_asigna_ningun_supervisor_sustituto_ni_se_crea_estado_nuevo · R9: tras desactivar al único supervisor, el rol de la colaboradora sigue siendo colaborador | Clasificación aclarada: se demuestra que ningún colaborador recibe funciones de supervisión (no se transfieren permisos ni se asigna un sustituto: RA-12) y que la supervisión solo deriva de una pertenencia de supervisor con acceso efectivo. Hoy ninguna ruta concede funciones de supervisión a nadie (M4): lo que M4 haga con el equipo pendiente es una dependencia, no una carencia de este criterio. |
| CA-262 | La planificación futura se conserva con su actividad y propietaria tras la finalización | M1-06 | **Implementado y probado** | B: programacion::ca262_la_planificacion_posterior_a_la_finalizacion_se_conserva_con_su_actividad_y_su_propietaria |  |

## 4. Contratos de M1

| Contrato | Operación | Estado | Observaciones |
|---|---|---|---|
| M1-01a | Iniciar sesión | **Implementado y probado** | Esperas y límites de M1-T7 implementados. **Pendiente:** el tope agregado de 100 fallos con deshabilitación de la contraseña (decisión diferida) y la configuración de proxies de confianza en el despliegue (DT-07). |
| M1-01b | Cerrar sesión | **Implementado y probado** |  |
| M1-01c | Consultar mi sesión | **Implementado y probado** |  |
| M1-02a | Crear un equipo (CLI) | **Implementado y probado** | La organización no tiene operación de creación (sin contrato): la crean la semilla de desarrollo o el propietario del esquema. |
| M1-02b | Crear una persona con su primera pertenencia (CLI) | **Implementado y probado** |  |
| M1-03a | Emitir el código de primer acceso (CLI) | **Implementado y probado** | El código se muestra una vez y solo en una terminal interactiva. |
| M1-03b | Completar el primer acceso | **Implementado y probado** | La comprobación de contraseñas comprometidas con Pwned Passwords **no está activa** hasta instalar el conjunto (≈ 81 GB) en el despliegue. |
| M1-05 | Registrar un traslado o un cambio de rol (CLI) | **Implementado y probado** |  |
| M1-06 | Finalizar una pertenencia (CLI) | **Implementado y probado** |  |
| M1-07 | Cancelar o sustituir una operación programada (CLI) | **Implementado y probado** | El enlace histórico entre una cancelación y su operación original es inequívoco salvo una finalización repetida con la misma fecha: se desambigua por el orden; **antes de producción hacen falta identificadores explícitos**. |
| M1-08 | Desactivar el acceso de una persona (CLI) | **Implementado y probado** |  |
| M1-09a | Emitir el código de recuperación (CLI) | **Implementado y probado** | Con la verificación de identidad declarada por la persona operadora (A5): con una sola persona operadora no hay control de dos personas. |
| M1-09b | Completar la recuperación del acceso | **Implementado y probado** | Misma comprobación de contraseñas comprometidas inactiva hasta instalar el conjunto. |
| M1-10 | Reactivar un acceso desactivado | **Fuera de alcance aprobado** | Sin regla ni historia: necesita una RN antes (ADR-002, A10 aprobado). No se implementa ni se prepara salvo lo ya reservado en el modelo. |

Operaciones sin contrato, por decisión: la consulta pública del historial de pertenencias y de la composición de un equipo, la reincorporación (PA-24), las altas y los ajustes históricos (PA-25) y la creación de una organización. Ninguna se ha implementado.

## 5. Recorridos principales validados

**Regresión (2026-11-17).** Backend: 2804 superadas y 1 omitida a propósito (regresión completa sobre `smartwork_test` de un clúster PostgreSQL desechable: 2.803 en la ejecución completa y una prueba obsoleta de M1-T6 corregida y repetida; ver «Defectos» más abajo). Flutter: 654 superadas (suite completa); `flutter analyze` sin incidencias. **Migraciones 0001 a 0017 sobre una base desechable:** 39 comprobaciones correctas: orden lineal 0001 a 0017 con una sola cabeza, `upgrade` revisión a revisión desde 0008 hasta 0017, `downgrade` a 0008 y `upgrade` a head, roles sin atributos de administración, funciones `SECURITY DEFINER` con `search_path` fijo y `EXECUTE` solo para la aplicación, permisos de la aplicación y de la provisión, auditoría solo anexada, sin acceso a contraseñas ni a hashes de códigos, restricción de exclusión de pertenencias y disparadores de integridad. **Recorrido integral (R9):** 65 comprobaciones correctas (CLI real en proceso, HTTP real con FastAPI, Chrome con el cliente Flutter Web compilado y PostgreSQL desechable; primer acceso y recuperación en Chrome, M2 y M3 por HTTP, traslados programados, cancelación y sustitución, finalizaciones, desactivación, único supervisor con advertencia, protección de autenticación y ausencia de secretos en la auditoría, la base y el registro del servidor).

| # | Recorrido | Evidencia automatizada | Evidencia real | Estado |
|---|---|---|---|---|
| 1 | Provisión de equipos y personas | `provision`, `provision_cli`, `db_provision`, `db_pertenencias` | R9: equipos, cuatro personas, rechazo del segundo supervisor y de una fecha anterior a hoy | Implementado y probado |
| 2 | Primer acceso y establecimiento de contraseña | `emision_codigos`, `canje_primer_acceso`, `db_codigo_unico`, `access_code_test` (F) | R85 y R9: primer acceso en Chrome, código de un solo uso, inicio de sesión posterior | Implementado y probado (comprobación de contraseñas comprometidas inactiva hasta instalar el conjunto) |
| 3 | Inicio y cierre de sesión | `acceso`, `login_uniformidad`, `widgets_test` (F), `login_wait_test` (F) | R9: inicio en Chrome y por HTTP, rol y fecha actual, cierre que revoca en el servidor | Implementado y probado |
| 4 | Protección de autenticación | `control_de_intentos*`, `login_intentos_api`, `operador_intentos`, `db_control_de_intentos`, `login_wait_test` (F) | R9: cinco intentos libres y 429 con `Retry-After` aun con la contraseña correcta; eventos técnicos | Implementado y probado; **pendientes:** tope agregado de 100 fallos, ataques distribuidos y proxies de confianza (sección 7) |
| 5 | Traslados y cambios de rol | `traslados`, `traslados_cli`, `traslado_e2e`, `visibilidad_historica` | R9: rechazo de hoy, registro futuro, sin solapes ni huecos, hoy sigue en su equipo; R-T5 | Implementado y probado (el efecto de la fecha efectiva, con reloj inyectable) |
| 6 | Finalización y cancelación de operaciones programadas | `programacion`, `programacion_cli`, `operaciones_programadas`, `enlace_auditoria`, `db_programacion` | R9: cancelar, sustituir, finalizar y cancelar; rechazos de CA-240, CA-241 y CA-258 | Implementado y probado; **pendiente:** identificadores explícitos del enlace histórico |
| 7 | Desactivación de acceso | `desactivacion`, `desactivacion_api`, `desactivacion_cli`, `db_desactivacion` | R9: sesión revocada, inicio rechazado, registros intactos, único supervisor con advertencia | Implementado y probado |
| 8 | Recuperación de contraseña y revocación de sesiones | `emision_codigos`, `canje_recuperacion`, `access_code_test` (F) | R85 y R9: recuperación en Chrome; dos sesiones previas revocadas; la contraseña anterior ya no sirve; no reactiva un acceso desactivado | Implementado y probado |
| 9 | Conservación del historial laboral | `programacion` (CA-31, CA-262), `desactivacion` (CA-256), `traslados`, `db_pertenencias` | R9: bitácoras y actividades de la persona desactivada y de la recuperada intactas | Implementado y probado |
| 10 | Integración con M2 y M3 | `traslado_e2e` (traslado oficial con M2 y M3), `e2e_flujo`, política de acceso en M2 y M3 | R9: bitácora, planificación, avance, resumen, cierre, reapertura y auditoría por HTTP con personas provisionadas y con primer acceso por la vía de M1 | Implementado y probado |

**Alcance del recorrido real R9:** los efectos de una fecha efectiva futura (traslado, finalización) no se pueden observar con el reloj real en una sola ejecución; el recorrido comprueba el registro, la cancelación y la sustitución, y que hoy la persona sigue en su equipo. El efecto de la fecha efectiva está probado con el reloj inyectable (`traslado_e2e`, `programacion`, `traslados`) y con el cliente Flutter en T5. La emisión de códigos usa el servicio de emisión porque la orden de la CLI exige una terminal interactiva.

## 6. Dependencias de M4 y M5

| Dependencia | Criterios o contratos | Estado en M1 |
|---|---|---|
| Vista consolidada y consulta del equipo por el supervisor | CA-03, CA-04 | Parcial / bloqueado: el rol se distingue; la vista es de M4 |
| Consulta ajena que use la política de visibilidad histórica (equipo en cada fecha) | CA-15 a CA-20, CA-176 a CA-178, CA-216, CA-217 | Parcial: la política (M1-T1) y su predicado SQL están probados; `ninguna_operacion_usa_todavia_la_politica_de_visibilidad_historica` deberá cambiarse al empezar M4 |
| Consulta por «persona autorizada» tras una baja o una desactivación | CA-30, CA-256 | Parcial: conservación y pertenencia histórica probadas; la consulta ajena es de M4 |
| Auditoría ajena por el supervisor del equipo y paso del 404 provisional al 403 | CA-111 (M3-07), `OPERACION_NO_PERMITIDA` | **Resuelto en M4-T6 (2026-11-18):** ver la adenda de `matriz-trazabilidad-m2-m3.md` y el plan de M4. Esta matriz es el cierre de M1 y no se reescribe |
| Equipo pendiente de supervisión efectiva | CA-260, CA-261 | M1 lo identifica y no concede permisos de supervisión; M4 debe tratarlo (la persona desactivada no supervisa) |
| Composición del equipo e historial de pertenencias como consultas | CA-06, CA-09, CA-13 | Verificados con las respuestas de M1-02b y M1-05 (contrato aprobado); no hay consulta pública (sin contrato): M4 decidirá si la necesita |
| Planificación conservada tras una baja (DM-08) | CA-262, CA-30 | Conservada y probada; su proyección es de M2 y M4 |
| Informes (M5) | CA-02, CA-05, CA-19, CA-20 | Bloqueado por M5: no existen informes |

## 7. Pendientes de seguridad y despliegue

Registrados para que no se den por resueltos. **M1 no se amplía para resolverlos**: son tareas de preparación del despliegue o decisiones aún abiertas.

| # | Pendiente | Situación y consecuencia |
|---|---|---|
| 1 | **Pwned Passwords no instalado** | La integración está implementada y probada (ADR-002, M1-T8.6), pero el conjunto (≈ 81 GB) **no está instalado**: la comprobación de contraseñas comprometidas está **inactiva** en el entorno de desarrollo y **no debe declararse activa** en ningún despliegue hasta instalarlo. La instalación completa, la verificación de integridad y las mediciones (tiempo de instalación, arranque con el conjunto completo) son tareas de preparación del despliegue (`docs/operacion/pwned-passwords.md`). Actualización propuesta: trimestral, pendiente de validación operativa |
| 2 | **Ataques distribuidos y tope agregado** | Los límites de M1-T7 son por identificador y por origen: un ataque distribuido (muchos orígenes) contra una cuenta no se frena con el tope agregado de 100 fallos y deshabilitación de la contraseña, **decisión diferida y no implementada**. Quien conozca un identificador puede además gastar los 10 intentos de un código pendiente (los límites lo frenan y la operadora emite otro) |
| 3 | **Configuración de proxies de confianza (DT-07)** | Sin `TRUSTED_PROXIES`, el origen es la dirección de la conexión: tras un proxy inverso todas las peticiones parecerían del mismo origen y los límites por origen podrían penalizar a todos (o, mal configurado, aceptar cabeceras falsificadas). Debe configurarse en el despliegue con las direcciones reales del proxy |
| 4 | **Programación de purgas** | `purgar-eventos-autenticacion` y `purgar-codigos` existen (retención de 30 días, la base impide borrar antes) pero **nada las ejecuta**: no hay planificador (DT-07). Hasta programarlas, los eventos y los códigos terminados se acumulan |
| 5 | **Control administrativo de dos personas** | La verificación de identidad de la recuperación (A5) y la emisión de códigos descansan en lo que declara una sola persona operadora; no hay alta de más personas operadoras ni control de dos personas |
| 6 | **Reactivación del acceso (M1-10) sin contrato** | Fuera de alcance aprobado (A10): sin regla ni historia. La recuperación nunca reactiva un acceso desactivado y no hay otra vía en el producto |
| 7 | **Verificación de roles y permisos en el despliegue** | Las migraciones y los permisos se comprobaron en bases desechables. En cada despliegue hay que crear los roles (propietario, aplicación y provisión) con los scripts, aplicar las migraciones y repetir las comprobaciones de permisos (`smartwork_app` no se ha migrado en este trabajo). Las funciones `SECURITY DEFINER` pertenecen al rol propietario de las migraciones, no a un rol propio del canje |
| 8 | **Configuración de secretos** | `AUTH_PEPPER` y `CODE_PEPPER` (≥ 32 caracteres, distintos entre sí, no versionados), las cadenas de conexión de los tres roles y la credencial de la persona operadora (variable de entorno o petición sin eco). Cambiar `AUTH_PEPPER` reinicia las esperas; cambiar `CODE_PEPPER` invalida los códigos pendientes. No hay configuración de producción: `APP_ENV` solo admite `development` y `test` |
| 9 | **Identificadores explícitos para enlaces de auditoría históricos** | El enlace entre una cancelación y su operación original es inequívoco salvo una finalización repetida con la misma fecha en el mismo intervalo, que se desambigua por el orden. Decisión del cierre de M1-T5: **antes de producción hacen falta identificadores explícitos de la operación original** |
| 10 | **Transporte y cookies** | La cookie de sesión es `__Host-` y `Secure`: exige HTTPS en el despliegue (en HTTP no se reenvía). La terminación TLS y los encabezados de seguridad son del despliegue |

## 8. Qué no demuestra esta matriz

- Rendimiento, volumen ni límites de carga (PA-13), ni el comportamiento con el conjunto completo de Pwned Passwords instalado.
- Seguridad de un despliegue real: proxies, TLS, secretos, copias de seguridad y monitorización. La revisión de seguridad de M1-T8.6 fue focalizada, no una auditoría general.
- Los efectos de una fecha efectiva futura con el reloj real en una sola ejecución: se prueban con el reloj inyectable.
- El uso con lectores de pantalla reales: el recorrido en Chrome usó el árbol de semántica de Flutter.
- Que cada persona operadora real siga el procedimiento de verificación de identidad: el sistema registra lo que declara.
- Que M4 y M5 se integren sin cambios: M1 deja la política de visibilidad lista y probada, pero ningún endpoint de M4 la usa todavía.


## Adenda M4-T9 (2026-11-18): reconciliación con la matriz de M4

Esta matriz es el cierre de M1 y **no se reescribe**. La evidencia ejecutada en M4 (matriz completa en [`matriz-trazabilidad-m4.md`](matriz-trazabilidad-m4.md)) resuelve las dependencias que aquí constaban como «sin consulta ajena hasta M4». No hay ninguna contradicción real con lo que M1 declaró «implementado y probado».

| CA | Estado en esta matriz | Con la evidencia de M4 | Evidencia nueva (resumen) |
|---|---|---|---|
| CA-03, CA-04 | Parcial / bloqueado por M4 | **Implementados y probados** | El colaborador no tiene la vista y recibe 403 al pedirla; el supervisor la tiene (pruebas de M4-03, pruebas de Flutter y recorrido en Chrome) |
| CA-15, CA-16, CA-17, CA-18 | Parcial | **Implementados y probados** | `test_consulta_bitacora.py::los_equipos_ven_solo_los_registros_de_su_periodo_tras_un_traslado` con un traslado real |
| CA-19, CA-20 | Parcial | **Siguen parciales** | La parte de consultas está probada (M4-01 a M4-04 y los accesos directos de M2/M3); la de informes es de M5 |
| CA-30, CA-256 | Parcial | **Implementados y probados** | Lectura HTTP por compañeros y supervisor de registros de personas finalizadas o con el acceso desactivado |
| CA-176, CA-177 | Parcial | **Implementados y probados** | `quien_se_incorpora_despues_lee_lo_del_equipo_en_esa_fecha_pero_no_lo_del_otro` |
| CA-178 | Parcial | **Implementado y probado** | Las seis escrituras sobre un registro visible ajeno responden 403 sin cambios en la base y M4 no tiene rutas de escritura (M4-T6) |
| CA-216, CA-217 | Parcial | **Implementados y probados** | `una_planificacion_de_una_fecha_posterior_al_traslado_es_del_equipo_nuevo_aunque_se_registrara_antes` (M4-T9) |
| CA-249 | Implementado y probado | Sin cambios; se añade la consulta ajena | `con_un_traslado_programado_para_manana_la_bitacora_de_hoy_sigue_siendo_del_equipo_anterior` (M4-T9) |
| CA-260, CA-261 | Implementados y probados | Sin cambios | M4 añade que un colaborador de un equipo sin supervisión efectiva recibe 403 en la supervisión y conserva la lectura entre pares |
| CA-05 | Parcial | **Sigue parcial** | Las respuestas de M4 no llevan credenciales; faltan los informes (M5) |

Queda para M5 lo que esta matriz ya dejaba en esa columna (CA-02, CA-05, CA-19, CA-20 en lo que alcanza a los informes).
