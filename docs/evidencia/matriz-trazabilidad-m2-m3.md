# SMARTWORK — Matriz de trazabilidad y cobertura: M2 y M3

| Campo | Contenido |
|---|---|
| **Naturaleza** | Evidencia de la implementación. No define requisitos: los requisitos viven en `docs/` (alcance, PRD, historias y contratos) |
| **Fecha** | 2026-11-11 (cierre técnico de M3, T14; CA-212 a CA-214 con un traslado oficial, M1-T5) |
| **Alcance** | Contratos M2-01a a M2-08 y M3-01 a M3-07, tal como están implementados en la fecha indicada. M3-07 solo para la persona propietaria: el acceso del supervisor y la visibilidad histórica son de M4 |
| **Fuente de los criterios** | `docs/api/m2-bitacoras.md` y `docs/api/m3-seguimiento-auditoria.md` («Criterios vinculados») y las historias de `docs/backlog/` |
| **Fuera de alcance** | M4 y M5: sus criterios no se evalúan aquí, salvo los que los contratos de M2 y M3 citan |

## 1. Cómo leerla

Cada fila es **contrato → criterio → componente → prueba → estado**. El componente (endpoint y pantalla) se indica una vez por contrato.

**Tipos de evidencia**

| Sigla | Qué es | Es flujo real |
|---|---|---|
| **B** | Prueba de backend (`pytest`): HTTP contra la aplicación con **PostgreSQL real** (`smartwork_test`), sin dobles de datos. Se cita `archivo::prueba`, con el nombre abreviado: el prefijo identifica la prueba | Sí (API y base) |
| **F** | Prueba de Flutter (`flutter test`) con un repositorio **en memoria** que imita al servidor. Verifica la pantalla y sus reglas, no la integración | **No**: es simulada |
| **R-INT** | Verificación integral: FastAPI y PostgreSQL reales en una instalación desechable (en T14, una base nueva creada con `alembic upgrade head` desde cero y la semilla de desarrollo), incluidas peticiones simultáneas reales y, en T9, el reinicio del servidor. En M1-T5, además, la provisión oficial por la CLI como procesos reales y un servidor uvicorn en otro proceso con el reloj de la aplicación de prueba (ver «Recorrido de M1-T5») | Sí |
| **R-UI** | Recorrido en Chrome real (escritorio y móvil) contra FastAPI y PostgreSQL, con capturas revisadas, durante el desarrollo y la verificación | Sí |

**Estados**

- **Implementado y probado:** hay una prueba de backend con PostgreSQL real (B) que cubre el criterio y, si el criterio tiene una parte de interfaz, un recorrido real (R-UI). Una prueba solo de tipo F **nunca** basta.
- **Parcial:** la regla existe y está probada, pero una parte del criterio depende de algo que no existe todavía o solo se probó con datos preparados a mano (por ejemplo, una marca de error escrita por SQL).
- **No implementado:** pertenece a una operación que esta entrega no incluye.
- **Bloqueado por otro módulo:** exige una operación de otro módulo (reactivación, traslado de equipo).
- **Pendiente de decisión:** el contrato o los criterios no fijan el comportamiento y hay que decidirlo.

## 2. Resumen

153 criterios distintos, 211 filas (un criterio aparece en cada contrato que lo cita, y las filas sin criterio propio recogen pruebas de validación, idempotencia, atomicidad y concurrencia).

| Estado | Filas |
|---|---|
| Implementado y probado | 208 |
| Parcial | 2 |
| No implementado | 0 |
| Bloqueado por otro módulo | 1 |
| Pendiente de decisión | 0 |

| Contrato | Criterios | Filas | Implementado y probado | Parcial | Bloqueado |
|---|---|---|---|---|---|
| M2-01a — Consultar mi bitácora de una fecha | 7 | 7 | 7 | 0 | 0 |
| M2-01b — Abrir mi bitácora de una fecha | 11 | 11 | 11 | 0 | 0 |
| M2-02 — Guardar el resumen libre | 9 | 9 | 9 | 0 | 0 |
| M2-03 — Planificar una actividad nueva | 9 | 9 | 9 | 0 | 0 |
| M2-04 — Planificar la continuación de una actividad | 10 | 10 | 10 | 0 | 0 |
| M2-05 — Registrar un avance | 35 | 35 | 34 | 1 | 0 |
| M2-06 — Registrar una actividad no planificada | 9 | 9 | 9 | 0 | 0 |
| M2-07 — Consultar una actividad propia | 25 | 25 | 24 | 1 | 0 |
| M2-08 — Listar mis actividades | 4 | 4 | 4 | 0 | 0 |
| M3-01 — Cerrar mi jornada | 13 | 13 | 13 | 0 | 0 |
| M3-02 — Reabrir mi bitácora cerrada | 6 | 6 | 6 | 0 | 0 |
| M3-04 — Reactivar una actividad Completada | 15 | 21 | 21 | 0 | 0 |
| M3-05 — Marcar una actividad como registrada por error | 10 | 11 | 11 | 0 | 0 |
| M3-06 — Revertir la marca de error | 3 | 5 | 5 | 0 | 0 |
| M3-07 — Consultar la auditoría de un registro | 15 | 18 | 17 | 0 | 1 |
| M3-03 — Corregir un avance ya registrado | 18 | 18 | 18 | 0 | 0 |

## 3. Matriz por contrato

### M2-01a — Consultar mi bitácora de una fecha

**Componente:** `GET /mi/bitacoras/{fecha}` · `LogbookPage`, `LogbookSummary`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-32 | Registrar la jornada en la propia bitácora | B bitacoras::cada_persona_dispone_de_su_propia_bitacora_aunque_sea_el_mismo_dia · R-INT | Implementado y probado |  |
| CA-33 | No hay una segunda bitácora de la misma fecha | B bitacoras::abrir_crea_la_bitacora_y_abrir_de_nuevo_devuelve_la_misma_sin_cambios y la apertura concurrente · R-INT | Implementado y probado |  |
| CA-34 | Actividades estructuradas y resumen libre | B resumen::guarda_el_resumen_de_una_bitacora_existente_y_la_consulta_lo_devuelve · R-UI | Implementado y probado |  |
| CA-35 | Cada persona tiene su bitácora el mismo día | B bitacoras::cada_persona_dispone_de_su_propia_bitacora_aunque_sea_el_mismo_dia | Implementado y probado |  |
| CA-61 | Fecha laboral y fecha de registro por separado | B bitacoras::la_bitacora_muestra_por_separado_las_tres_fechas · R-UI | Implementado y probado |  |
| CA-62 | Se muestra la fecha de modificación | B bitacoras::la_bitacora_muestra_por_separado_las_tres_fechas; resumen::la_consulta_muestra_las_tres_fechas_tras_una_correccion…; correccion::el_avance_corregido_muestra_su_fecha_de_modificacion… | Implementado y probado | Bitácora: cambia al guardar el resumen. Avances: `modificado_en` cambia al corregirlos (M3-03) y es el del registro mientras no se corrijan. |
| CA-282 | Consultar una fecha sin bitácora no crea nada | B bitacoras::consultar_una_fecha_sin_bitacora_no_crea_nada · R-INT | Implementado y probado |  |

### M2-01b — Abrir mi bitácora de una fecha

**Componente:** `POST /mi/bitacoras` · `LogbookPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-32 | Abrir en la propia bitácora | B bitacoras::cada_persona_dispone_de_su_propia_bitacora… | Implementado y probado |  |
| CA-33 | Abrir otra vez no duplica | B bitacoras::abrir_crea_la_bitacora_y_abrir_de_nuevo_devuelve_la_misma… · R-INT | Implementado y probado |  |
| CA-35 | Cada persona su bitácora | B bitacoras::cada_persona_dispone_de_su_propia_bitacora… | Implementado y probado |  |
| CA-59 | Jornada pasada sin límite de antigüedad | B bitacoras::una_jornada_de_hace_meses_no_se_rechaza_por_su_antiguedad | Implementado y probado |  |
| CA-60 | Jornada de hace meses no se rechaza | B bitacoras::planificar_en_una_jornada_de_hace_meses_se_acepta | Implementado y probado |  |
| CA-63 | Misma fecha laboral actual con independencia del lugar | B bitacoras::la_fecha_actual_la_calcula_el_servidor_en_la_zona_de_la_organizacion (varias zonas) | Implementado y probado |  |
| CA-64 | Un día festivo no restringe | B bitacoras::se_puede_abrir_una_jornada_futura_y_no_hay_restriccion_por_festivos | Implementado y probado |  |
| CA-264 | Nada anterior a la primera pertenencia | B bitacoras::una_fecha_anterior_a_la_primera_pertenencia_no_se_permite | Implementado y probado |  |
| CA-280 | Abrir una existente devuelve la misma sin cambios | B bitacoras::abrir_crea_la_bitacora_y_abrir_de_nuevo_devuelve_la_misma… | Implementado y probado |  |
| CA-281 | El primer contenido crea la única bitácora | B bitacoras::planificar_crea_actividad_pendiente…; resumen::si_la_bitacora_no_existe_se_crea_en_la_misma_transaccion | Implementado y probado |  |
| CA-294 | Abrir una jornada pasada vacía no se audita | B bitacoras::abrir_una_jornada_pasada_vacia_no_genera_auditoria | Implementado y probado |  |

### M2-02 — Guardar el resumen libre

**Componente:** `PUT /mi/bitacoras/{fecha}/resumen` · `DailySummary` y protección de texto sin guardar

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-34 | Resumen libre dentro de la bitácora | B resumen::guarda_el_resumen_de_una_bitacora_existente… · R-UI · R-INT | Implementado y probado |  |
| CA-36 | No se guarda en la bitácora de otra persona | B resumen::solo_se_guarda_en_la_bitacora_propia_y_nunca_en_la_de_otra_persona | Implementado y probado |  |
| CA-62 | La modificación renueva `modificada_en` | B resumen::modificada_en_se_renueva_en_cada_guardado_y_las_otras_dos_fechas_no_cambian | Implementado y probado |  |
| CA-65 | Las tres fechas siguen consultables tras corregir; consta en la auditoría | B resumen::la_consulta_muestra_las_tres_fechas_tras_una_correccion_en_una_jornada_pasada | Implementado y probado |  |
| CA-105 | Modificar una jornada pasada deja auditoría | B resumen::una_modificacion_en_una_jornada_pasada_deja_una_unica_entrada… · R-INT | Implementado y probado |  |
| CA-107 | Nadie, ni un supervisor, modifica la jornada de otra persona | B resumen::solo_se_guarda_en_la_bitacora_propia…; cierre_reapertura::un_supervisor_no_modifica_la_jornada_pasada_de_su_colaboradora | Implementado y probado |  |
| CA-281 | Si no existe la bitácora, se crea en la misma operación | B resumen::si_la_bitacora_no_existe_se_crea_en_la_misma_transaccion | Implementado y probado |  |
| CA-284 | Una jornada cerrada no admite cambios sin reabrirla | B resumen::una_jornada_cerrada_no_admite_cambios_hasta_reabrirla; cierre_reapertura::en_una_jornada_cerrada_no_se_escribe_contenido_sin_reabrirla · F closure/closed_day_actions · R-INT · R-UI | Implementado y probado |  |
| CA-293 | La primera escritura efectiva en una jornada pasada se audita | B resumen::la_primera_escritura_efectiva_en_una_jornada_pasada_se_audita… | Implementado y probado |  |

### M2-03 — Planificar una actividad nueva

**Componente:** `POST /mi/bitacoras/{fecha}/planificaciones` · `PlanningPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-37 | La actividad planificada aparece en la bitácora | B bitacoras::planificar_crea_actividad_pendiente_y_planificacion_original… · R-UI · R-INT | Implementado y probado |  |
| CA-38 | Una actividad nueva es Pendiente | B bitacoras::planificar_crea_actividad_pendiente… · R-INT | Implementado y probado |  |
| CA-39 | Lo previsto sigue consultable | B actividades::lo_previsto_originalmente_sigue_consultable_tras_actualizar_lo_realizado | Implementado y probado |  |
| CA-40 | La planificación no es un avance | B actividades::el_detalle_distingue_la_planificacion_de_la_ejecucion_y_del_estado · R-UI | Implementado y probado |  |
| CA-41 | Una actividad no admite otro propietario | B bitacoras::el_cuerpo_no_admite_estado_propietaria_ni_avances; disparador de inmutabilidad (test_db_bitacoras) | Implementado y probado |  |
| CA-42 | Planificar una jornada futura se acepta | B bitacoras::planificar_para_una_fecha_futura_es_valido_y_no_se_audita · R-INT | Implementado y probado |  |
| CA-43 | En una jornada futura solo Pendiente | B bitacoras::el_cuerpo_no_admite_estado…; no_planificadas::no_se_registra_ejecucion_con_fecha_futura_en_ningun_estado | Implementado y probado |  |
| CA-263 | La planificación original no cambia | B bitacoras::la_planificacion_original_conserva_su_contenido; test_db_permisos_m2 (sin UPDATE sobre `planificacion`) | Implementado y probado |  |
| CA-295 | Título vacío o de espacios no se permite | B bitacoras::un_titulo_vacio_o_de_solo_espacios_no_se_permite · R-INT | Implementado y probado |  |

### M2-04 — Planificar la continuación de una actividad

**Componente:** `POST /mi/actividades/{id}/continuaciones-planificadas` · `ContinuationPage`, detalle

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-43 | Solo se planifica hacia el futuro | B continuaciones::la_fecha_de_hoy_o_pasada_no_es_una_fecha_futura | Implementado y probado |  |
| CA-179 | Continuar no crea otra actividad | B continuaciones::registra_la_continuacion_sin_crear_otra_actividad_ni_un_avance · R-UI · R-INT | Implementado y probado |  |
| CA-180 | El estado actual no cambia | B continuaciones::el_estado_actual_no_cambia_al_planificar | Implementado y probado |  |
| CA-181 | La continuación no entra en la secuencia | B continuaciones::la_continuacion_no_forma_parte_de_la_secuencia_ni_del_estado | Implementado y probado |  |
| CA-182 | No hay ejecución en jornadas futuras | B avances::no_se_registra_ejecucion_con_fecha_futura · R-INT | Implementado y probado |  |
| CA-183 | No se continúa la actividad de otra persona | B continuaciones::no_se_planifica_la_continuacion_de_la_actividad_de_otra_persona · R-INT | Implementado y probado |  |
| CA-185 | El estado actual es el del último avance | B actividades::las_continuaciones_planificadas_se_listan_aparte_y_no_forman_parte_de_la_secuencia | Implementado y probado |  |
| CA-186 | Sin avances sigue Pendiente | B actividades::las_continuaciones_planificadas_se_listan_aparte…; continuaciones::la_continuacion_no_forma_parte… | Implementado y probado |  |
| CA-209 | Una Completada no se continúa sin reactivarla | B continuaciones::una_actividad_completada_no_se_continua_sin_reactivarla · R-INT | Implementado y probado |  |
| CA-210 | Una reactivada sí se continúa | B reactivacion::despues_de_reactivar_se_puede_planificar_su_continuacion; continuaciones::una_actividad_completada_no_se_continua_sin_reactivarla | Implementado y probado | Con la reactivación real de M3-04: una Completada se rechaza y, reactivada, admite continuación. |

### M2-05 — Registrar un avance

**Componente:** `POST /mi/actividades/{id}/avances` · `ProgressPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-45 | El avance conserva el estado histórico | B avances::registrar_un_avance_actualiza_la_actividad_y_conserva_el_estado_historico | Implementado y probado |  |
| CA-46 | Los avances anteriores no cambian | B secuencia::registrar_un_avance_cambia_la_secuencia_pero_no_reescribe_los_anteriores | Implementado y probado |  |
| CA-47 | El estado es uno de los cuatro | B avances::un_estado_distinto_de_los_cuatro_no_se_acepta; restricción CHECK de la base (migración 0003) · R-INT | Implementado y probado |  |
| CA-48 | Un valor fuera de los cuatro no se acepta | B avances::un_estado_distinto_de_los_cuatro_no_se_acepta · F progress_rules | Implementado y probado |  |
| CA-49 | Bloquear sin motivo no se permite | B avances::bloquear_sin_motivo_no_se_permite · F progress_form (CA-49) · R-INT | Implementado y probado |  |
| CA-50 | Bloquear con motivo se permite | B avances::el_motivo_del_bloqueo_consta_y_sigue_constando_al_cambiar_de_estado · R-UI | Implementado y probado |  |
| CA-51 | El motivo consta en el avance | B avances::el_motivo_del_bloqueo_consta…; actividades::el_motivo_de_un_bloqueo_anterior_sigue_constando_en_el_historial | Implementado y probado |  |
| CA-52 | El motivo anterior sigue en el historial | B actividades::el_motivo_de_un_bloqueo_anterior_sigue_constando_en_el_historial | Implementado y probado |  |
| CA-66 | El avance queda asociado a su fecha laboral | B avances::registrar_un_avance_actualiza_la_actividad… · R-UI · R-INT | Implementado y probado |  |
| CA-67 | El nuevo estado queda en el avance | B avances::se_admite_cualquier_cambio_de_estado_entre_los_cuatro | Implementado y probado |  |
| CA-68 | Sin descripción no se permite | B avances::un_avance_sin_descripcion_o_solo_con_espacios_no_se_permite | Implementado y probado |  |
| CA-69 | Descripción de solo espacios no se permite | B avances::un_avance_sin_descripcion_o_solo_con_espacios_no_se_permite · F progress_form (CA-69) | Implementado y probado |  |
| CA-71 | Dos avances en la misma fecha constan | B avances::dos_avances_en_la_misma_fecha_constan_y_el_segundo_es_el_estado_actual | Implementado y probado |  |
| CA-72 | No se registra en la actividad de otra persona | B avances::no_se_puede_registrar_un_avance_en_la_actividad_de_otra_persona · R-INT | Implementado y probado |  |
| CA-74 | La fecha laboral posterior manda sobre el momento de registro | B secuencia::la_fecha_laboral_posterior_es_posterior_aunque_se_registrara_antes; avances::… | Implementado y probado |  |
| CA-75 | En la misma fecha, el registrado después es posterior | B avances::dos_avances_en_la_misma_fecha…; secuencia (orden por momento) | Implementado y probado |  |
| CA-76 | Con igual fecha y momento decide el identificador | B secuencia::con_igual_fecha_y_momento_decide_el_identificador_siempre_igual | Parcial | Regla pura probada y orden `…, id` en la consulta SQL; un empate real de momentos no se puede forzar por HTTP. |
| CA-77 | El estado actual es el del último avance | B avances::dos_avances_en_la_misma_fecha…; R-INT (8 avances simultáneos) | Implementado y probado |  |
| CA-78 | Un avance retroactivo Completada no pisa a uno posterior | B avances::un_avance_retroactivo_no_sustituye_el_estado_de_uno_posterior; actividades::un_avance_retroactivo_no_sustituye_el_estado_actual · R-INT | Implementado y probado | Interpretación de IR-11 confirmada el 2026-11-09 (PA-27): se mira solo el avance anterior al punto de inserción. M3-03 valida una corrección sin introducir violaciones nuevas y sin rechazarla por estos pares preexistentes (PA-29, opción A). |
| CA-81 | Un avance en una jornada posterior no crea otra actividad | B cierre_reapertura::una_actividad_de_una_jornada_cerrada_sigue_recibiendo_avances_en_una_posterior; actividades (tres jornadas, una sola actividad) · R-INT | Implementado y probado |  |
| CA-86 | Se asocia a la actividad explícitamente elegida | B (la ruta exige `actividad_id`) avances::registrar_un_avance_actualiza_la_actividad… · R-UI | Implementado y probado |  |
| CA-87 | Nunca se asocia por similitud de título | B actividades::dos_actividades_con_el_mismo_titulo_siguen_siendo_distintas; el contrato no admite crear avance sin actividad | Implementado y probado | No hay una prueba negativa propia: es una propiedad del contrato (la ruta exige el identificador). |
| CA-88 | No se continúa la actividad de otra persona | B actividades::la_actividad_de_otra_persona_y_una_inexistente_tienen_la_misma_respuesta; el_listado_solo_incluye_actividades_propias | Implementado y probado |  |
| CA-96 | Solo debe estar abierta la jornada del avance | B avances::solo_debe_estar_abierta_la_bitacora_de_la_fecha_del_avance; cierre_reapertura::…continua_recibiendo_avances… · R-INT | Implementado y probado |  |
| CA-182 | No hay avance con fecha futura | B avances::no_se_registra_ejecucion_con_fecha_futura · F progress_rules · R-INT | Implementado y probado |  |
| CA-190 | Tras completar no se admite otro avance | B avances::una_actividad_completada_no_recibe_avances_posteriores_sin_reactivarla · R-INT | Implementado y probado |  |
| CA-203 | Retroactivo anterior a la finalización se acepta | B avances::un_avance_retroactivo_anterior_a_la_finalizacion_se_acepta_sin_reactivar · R-INT | Implementado y probado |  |
| CA-204 | Se inserta en su posición y se audita | B avances::un_avance_retroactivo_sobre_una_actividad_completada_se_audita | Implementado y probado |  |
| CA-205 | El estado actual sigue Completada | B secuencia::el_retroactivo_anterior_a_la_finalizacion_deja_la_actividad_completada | Implementado y probado |  |
| CA-206 | Misma fecha tras la finalización no se admite | B secuencia::un_avance_de_la_misma_fecha_registrado_despues_de_la_finalizacion…; avances | Implementado y probado |  |
| CA-207 | Entre una finalización y su reactivación no se admite | B secuencia::no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion; reactivacion::sin_reactivar_no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion · R-INT | Implementado y probado | Con el flujo real de reactivar (M3-04). |
| CA-208 | No es posible sobre una Completada ajena | B avances::un_avance_retroactivo_sobre_una_actividad_completada_ajena_tampoco_es_posible | Implementado y probado |  |
| CA-213 | Registrar en el equipo nuevo no crea otra actividad | B: `test_traslado_e2e.py`::ca213_un_avance_registrado_en_u_no_crea_otra_actividad y ca213_el_avance_en_u_se_valida_con_las_mismas_reglas · R-INT M1-T5 (servidor real, CLI real) · R-UI M1-T5 (cliente Flutter real) | Implementado y probado | M1-T5, con un traslado oficial de M1-05: la actividad iniciada en T recibe en U un avance sobre la misma actividad (una sola fila de actividad, una sola en el listado). El avance se valida con las reglas de siempre (estado, motivo, fecha no futura, cobertura). |
| CA-284 | Una jornada cerrada no admite avances | B cierre_reapertura::en_una_jornada_cerrada_no_se_escribe_contenido_sin_reabrirla; test una_escritura_que_esperaba_al_cierre_ve_la_jornada_cerrada · F closed_day_actions · R-INT · R-UI | Implementado y probado |  |
| CA-293 | La primera escritura efectiva en una jornada pasada se audita | B avances::un_avance_en_una_jornada_pasada_deja_una_unica_entrada… | Implementado y probado |  |

### M2-06 — Registrar una actividad no planificada

**Componente:** `POST /mi/actividades-no-planificadas` · `UnplannedPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-43 | No hay ejecución futura | B no_planificadas::no_se_registra_ejecucion_con_fecha_futura_en_ningun_estado | Implementado y probado |  |
| CA-44 | En la jornada actual, cualquier estado | B no_planificadas::la_actividad_empieza_con_el_estado_de_su_primer_avance; se_acepta_la_jornada_actual_y_las_pasadas_sin_limite_de_antiguedad | Implementado y probado |  |
| CA-53 | Se identifica como no planificada | B no_planificadas::crea_la_actividad_no_planificada_y_su_primer_avance; se_distingue_de_las_planificadas… · R-UI · R-INT | Implementado y probado |  |
| CA-54 | Empieza con el estado de su primer avance | B no_planificadas::la_actividad_empieza_con_el_estado_de_su_primer_avance · R-INT | Implementado y probado |  |
| CA-55 | Bloqueada sin motivo no se permite | B no_planificadas::bloqueada_sin_motivo_no_se_permite · F unplanned_data | Implementado y probado |  |
| CA-56 | Bloqueada con motivo se registra | B no_planificadas::bloqueada_con_motivo_se_registra_y_el_motivo_consta | Implementado y probado |  |
| CA-57 | No es un estado adicional | B no_planificadas::se_distingue_de_las_planificadas_sin_ser_un_estado_adicional | Implementado y probado |  |
| CA-58 | Sin descripción no se permite | B no_planificadas::un_primer_avance_sin_descripcion_no_se_permite | Implementado y probado |  |
| CA-296 | Título vacío no se permite | B no_planificadas::un_titulo_vacio_o_de_solo_espacios_no_se_permite | Implementado y probado |  |

### M2-07 — Consultar una actividad propia

**Componente:** `GET /mi/actividades/{id}` · `ActivityDetailPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-39 | Lo previsto sigue consultable | B actividades::lo_previsto_originalmente_sigue_consultable… · R-UI | Implementado y probado |  |
| CA-40 | Planificación y ejecución distinguidas | B actividades::el_detalle_distingue_la_planificacion_de_la_ejecucion_y_del_estado · R-UI | Implementado y probado |  |
| CA-47 | El estado es uno de los cuatro | B actividades (detalle y listado) + restricción CHECK | Implementado y probado |  |
| CA-51 | Consta el motivo del bloqueo | B actividades::el_motivo_de_un_bloqueo_anterior_sigue_constando_en_el_historial | Implementado y probado |  |
| CA-52 | El motivo anterior sigue constando | B actividades::el_motivo_de_un_bloqueo_anterior_sigue_constando_en_el_historial | Implementado y probado |  |
| CA-61 | Fechas laboral y de registro por separado | B actividades::se_muestran_la_fecha_laboral_la_real_de_registro_y_la_de_modificacion | Implementado y probado |  |
| CA-62 | Fecha de modificación | B actividades::se_muestran_la_fecha_laboral_la_real_de_registro_y_la_de_modificacion; correccion::el_avance_corregido_muestra_su_fecha_de_modificacion… | Implementado y probado | `modificado_en` del avance es el del registro hasta que se corrige (M3-03). |
| CA-70 | El avance muestra fecha, estado de entonces y descripción | B actividades::se_muestran_la_fecha_laboral…; avances::la_consulta_de_la_bitacora_muestra_el_avance… · R-UI | Implementado y probado |  |
| CA-73 | Sin avances es Pendiente | B actividades::el_detalle_distingue…; secuencia::una_actividad_sin_avances_esta_pendiente | Implementado y probado |  |
| CA-74 | Orden por fecha laboral | B actividades::los_avances_van_en_el_orden_de_la_secuencia… · R-INT | Implementado y probado |  |
| CA-75 | En la misma fecha, el registrado después va después | B actividades::los_avances_van_en_el_orden_de_la_secuencia… | Implementado y probado |  |
| CA-76 | Desempate por identificador estable | B secuencia::con_igual_fecha_y_momento_decide_el_identificador_siempre_igual | Parcial | Igual que en M2-05. |
| CA-77 | El estado actual es el del último avance | B actividades::los_avances_van_en_el_orden_de_la_secuencia… · R-INT | Implementado y probado |  |
| CA-78 | Un retroactivo no pisa el estado posterior | B actividades::un_avance_retroactivo_no_sustituye_el_estado_actual | Implementado y probado |  |
| CA-82 | Una sola actividad con avances en tres jornadas | B actividades::la_secuencia_de_tres_jornadas_muestra_tres_avances_y_una_sola_actividad | Implementado y probado |  |
| CA-83 | Muestra los tres avances con su fecha | B actividades::la_secuencia_de_tres_jornadas… | Implementado y probado |  |
| CA-84 | Cada avance con su fecha y su estado | B actividades::los_avances_van_en_el_orden_de_la_secuencia_y_cada_uno_con_su_fecha_y_su_estado | Implementado y probado |  |
| CA-120 | Una marcada por error sigue consultable | B actividades::una_actividad_marcada_por_error_sigue_siendo_consultable; marca_error::la_actividad_marcada_sigue_consultable_con_su_historial · R-UI | Implementado y probado | El historial y la auditoría siguen consultables, con la marca real de M3-05 (probado en API, PostgreSQL y Chrome; M3-07 en T13). |
| CA-121 | Una marcada por error no se borra | B actividades::una_actividad_marcada_por_error_sigue_siendo_consultable; marca_error::marcar_no_borra_ni_modifica_ningun_registro; test_db_marca_error (sin permiso de borrado) · R-INT | Implementado y probado | La marca es lógica: el estado no cambia y no se borra ninguna fila. |
| CA-185 | El estado no depende de la continuación | B actividades::las_continuaciones_planificadas_se_listan_aparte… | Implementado y probado |  |
| CA-186 | Con continuación y sin avances: Pendiente | B actividades::las_continuaciones_planificadas_se_listan_aparte…; continuaciones | Implementado y probado |  |
| CA-191 | Una reactivada sigue siendo la misma actividad | B reactivacion::la_actividad_conserva_su_identidad_su_planificacion_y_sus_avances; el_detalle_y_el_listado_reflejan_la_reactivacion · R-INT · R-UI | Implementado y probado | Con la reactivación real (M3-04); además CA-265 y CA-39. |
| CA-265 | El título es el mismo en todas las jornadas | B actividades::la_secuencia_de_tres_jornadas_muestra_tres_avances_y_una_sola_actividad (título inmutable por disparador) | Implementado y probado |  |
| CA-212 | Una actividad sigue siendo de su propietaria al cambiar de equipo | B: `test_traslado_e2e.py`::ca212_la_actividad_iniciada_en_t_sigue_siendo_la_misma y ca212_el_equipo_historico_de_la_actividad_sigue_siendo_t · R-INT M1-T5 (servidor real, CLI real) · R-UI M1-T5 (cliente Flutter real) | Implementado y probado | M1-T5: tras el traslado efectivo la actividad conserva su identidad, su propietaria y su jornada de origen (del equipo T por su fecha); el traslado no reescribió ninguna fila de M2 ni de M3. |
| CA-214 | El historial muestra los avances de ambos equipos | B: `test_traslado_e2e.py`::ca214_la_propietaria_ve_en_u_todos_los_avances y ca214_la_actividad_aparece_una_sola_vez_en_el_listado · R-INT M1-T5 (servidor real, CLI real) · R-UI M1-T5 (cliente Flutter real) | Implementado y probado | M1-T5: la propietaria ve, desde U, los avances de T y los de U en el orden laboral, con su fecha laboral (distinta de la real) y el estado actual derivado; el cliente Flutter lo muestra en «Historial de avances». |

### M2-08 — Listar mis actividades

**Componente:** `GET /mi/actividades` · `ActivitiesPage`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-82 | Cada actividad cuenta una vez | B actividades::una_actividad_con_avances_en_varias_jornadas_cuenta_una_sola_vez · R-INT | Implementado y probado |  |
| CA-85 | Títulos iguales o parecidos son actividades distintas | B actividades::dos_actividades_con_el_mismo_titulo_siguen_siendo_distintas | Implementado y probado |  |
| CA-88 | Solo aparecen mis actividades | B actividades::el_listado_solo_incluye_actividades_propias · R-INT | Implementado y probado |  |
| CA-119 | Las marcadas por error no aparecen | B actividades::las_actividades_marcadas_por_error_no_aparecen_en_el_listado; marca_error::la_actividad_marcada_sale_del_listado_operativo · F mark_form · R-INT · R-UI | Implementado y probado | Con la marca real de M3-05. |

### M3-01 — Cerrar mi jornada

**Componente:** `POST /mi/bitacoras/{fecha}/cierre` · `DayClosure`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-89 | El cierre es solo manual | B cierre_reapertura::cerrar_es_solo_manual_el_paso_del_tiempo_no_cierra | Implementado y probado |  |
| CA-90 | Actividad creada + resumen: se cierra | B cierre_reapertura::cierra_una_jornada_con_una_actividad_creada_y_un_resumen · F closure · R-INT · R-UI | Implementado y probado |  |
| CA-91 | Actividad continuada + resumen: se cierra | B cierre_reapertura::una_actividad_continuada_con_un_avance_de_esa_fecha_cuenta | Implementado y probado |  |
| CA-92 | Sin actividad no se cierra | B cierre_reapertura::sin_actividad_creada_ni_continuada_no_se_cierra · F closure | Implementado y probado |  |
| CA-93 | Resumen vacío no se cierra | B cierre_reapertura::un_resumen_vacio_o_de_solo_espacios_no_permite_cerrar · R-INT · R-UI | Implementado y probado |  |
| CA-94 | Resumen de solo espacios no se cierra | B cierre_reapertura::un_resumen_vacio_o_de_solo_espacios_no_permite_cerrar | Implementado y probado |  |
| CA-95 | Las actividades conservan su estado | B cierre_reapertura::las_actividades_conservan_su_estado_en_los_cuatro_estados | Implementado y probado |  |
| CA-96 | Una actividad de una jornada cerrada recibe avances después | B cierre_reapertura::una_actividad_de_una_jornada_cerrada_sigue_recibiendo_avances_en_una_posterior · R-INT | Implementado y probado |  |
| CA-97 | No se cierra una jornada futura | B cierre_reapertura::una_jornada_futura_no_se_cierra · R-INT | Implementado y probado |  |
| CA-98 | No se cierra la jornada de otra persona | B cierre_reapertura::la_jornada_de_otra_persona_no_se_puede_cerrar; un_supervisor_del_mismo_equipo_no_cierra_ni_reabre… · R-INT | Implementado y probado |  |
| CA-184 | Una continuación planificada no cuenta | B cierre_reapertura::una_continuacion_planificada_no_cuenta_como_actividad_continuada | Implementado y probado | La continuación se prepara por SQL en una jornada ya no futura (el tiempo no avanza en la prueba). |
| CA-266 | Cada ciclo de cierre y reapertura es reconstruible | B cierre_reapertura::los_ciclos_de_cierre_y_reapertura_se_reconstruyen_desde_la_auditoria · R-INT | Implementado y probado |  |
| CA-283 | Una actividad marcada por error no cuenta | B cierre_reapertura::una_actividad_marcada_por_error_no_cuenta; marca_error::la_actividad_marcada_no_cuenta_para_cerrar_la_jornada · F closing_rules · R-INT | Implementado y probado | Con la marca real de M3-05. |

### M3-02 — Reabrir mi bitácora cerrada

**Componente:** `POST /mi/bitacoras/{fecha}/reapertura` · `DayClosure`, `ReopenDialog`

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-99 | Reabierta, se puede corregir | B cierre_reapertura::tras_reabrir_se_admiten_de_nuevo_las_operaciones_sobre_la_jornada · R-INT · R-UI | Implementado y probado |  |
| CA-100 | Sin motivo no se reabre | B cierre_reapertura::sin_motivo_no_se_reabre · F closure · R-INT · R-UI | Implementado y probado |  |
| CA-101 | No se reabre la de otra persona, ni por un supervisor | B cierre_reapertura::la_bitacora_cerrada_de_otra_persona_no_se_reabre; un_supervisor_del_mismo_equipo_no_cierra_ni_reabre_la_jornada_de_su_colaboradora · R-INT | Implementado y probado |  |
| CA-102 | Constancia de la reapertura y de la corrección | B cierre_reapertura::la_correccion_tras_reabrir_deja_constancia_de_la_reapertura_y_de_la_correccion · R-INT | Implementado y probado |  |
| CA-109 | El motivo consta en la auditoría | B cierre_reapertura::reabre_una_bitacora_cerrada_indicando_un_motivo · R-INT | Implementado y probado |  |
| CA-266 | Ciclos reconstruibles | B cierre_reapertura::los_ciclos_de_cierre_y_reapertura_se_reconstruyen_desde_la_auditoria | Implementado y probado |  |

### M3-04 — Reactivar una actividad Completada

**Componente:** `POST /mi/actividades/{id}/reactivacion` · acción «Reactivar» del detalle de la actividad (`ReactivationPage`, formulario con estado, descripción, motivo y fecha laboral)

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-124 | Reactivar una Completada con descripción: la misma actividad pasa a otro estado y no se crea otra | B reactivacion::reactiva_hacia_los_tres_estados_permitidos; la_actividad_conserva_su_identidad_su_planificacion_y_sus_avances · F reactivation_form · R-INT · R-UI | Implementado y probado |  |
| CA-125 | Una reactivación completada consta en la auditoría | B reactivacion::deja_una_unica_entrada_de_auditoria_con_el_autor_el_objeto_y_la_fecha_correctos; una_reactivacion_en_hoy_tambien_se_audita; la_persistencia_es_coherente_en_la_base · R-INT | Implementado y probado | Una entrada `reactivacion` sobre el avance, con el estado actual anterior y nuevo y la finalización anterior. Se consulta con M3-07. |
| CA-126 | La reactivación es un avance de la secuencia, posterior al que completó | B reactivacion::la_reactivacion_es_un_avance_posterior_a_la_finalizacion_y_la_historia_se_conserva; la_finalizacion_relevante_es_la_del_ultimo_avance_del_orden_laboral · R-INT · R-UI | Implementado y probado | La finalización relevante es el último avance del orden laboral completo (decisión aprobada). |
| CA-127 | La actividad Completada de otra persona no se reactiva | B reactivacion::la_actividad_completada_de_otra_persona_no_se_reactiva; un_supervisor_del_mismo_equipo_tampoco_la_reactiva; la_visibilidad_se_evalua_antes_que_el_cuerpo · R-INT | Implementado y probado | 404 indistinguible de una inexistente (T-01). |
| CA-128 | Bloqueada sin motivo no se permite | B reactivacion::bloqueada_sin_motivo_no_se_permite · F reactivation_form, reactivation_rules · R-UI | Implementado y probado |  |
| CA-129 | Sin descripción no vacía no se permite | B reactivacion::sin_descripcion_no_se_permite · F reactivation_form · R-UI | Implementado y probado |  |
| CA-187 | La misma fecha F de la finalización se acepta, con un momento posterior | B reactivacion::la_misma_fecha_de_la_finalizacion_se_acepta_y_queda_despues_de_ella | Implementado y probado |  |
| CA-188 | Una fecha anterior a F no se permite | B reactivacion::una_fecha_anterior_a_la_finalizacion_no_se_permite · F reactivation_rules | Implementado y probado | `SECUENCIA_INVALIDA`. |
| CA-189 | Una fecha futura no se permite | B reactivacion::una_fecha_futura_no_se_permite · F reactivation_rules | Implementado y probado | `FECHA_FUTURA_NO_PERMITIDA`. |
| CA-190 | Sin reactivar no se admite un avance posterior a la finalización | B reactivacion::sin_reactivar_no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion; avances::una_actividad_completada_no_recibe_avances_posteriores_sin_reactivarla · R-INT | Implementado y probado | `ACTIVIDAD_COMPLETADA`. |
| CA-191 | Una reactivada sigue siendo la misma actividad | B reactivacion::la_actividad_conserva_su_identidad_su_planificacion_y_sus_avances; el_detalle_y_el_listado_reflejan_la_reactivacion · R-INT · R-UI | Implementado y probado | Identidad, planificación original y avances anteriores. |
| CA-192 | Reactivar en una jornada pasada posterior a F se acepta y queda auditado | B reactivacion::se_admite_hoy_y_una_jornada_pasada_posterior_a_la_finalizacion_con_una_sola_entrada · R-INT | Implementado y probado | Una sola entrada, con la fecha laboral de la reactivación. |
| CA-269 | Hacia Pendiente o En progreso se acepta y la finalización anterior se conserva | B reactivacion::reactiva_hacia_los_tres_estados_permitidos; la_finalizacion_anterior_se_conserva_sin_cambios · R-INT | Implementado y probado |  |
| CA-270 | Hacia Bloqueada sin motivo se rechaza | B reactivacion::bloqueada_sin_motivo_no_se_permite | Implementado y probado |  |
| CA-271 | Hacia Bloqueada con motivo se acepta y el motivo se conserva | B reactivacion::bloqueada_con_motivo_conserva_el_motivo_en_el_historial · R-UI | Implementado y probado |  |
| — | Estados y textos | B reactivacion::Completada_no_es_un_estado_de_reactivacion; un_estado_fuera_de_los_cuatro_o_ausente_es_estado_invalido; el_motivo_solo_existe_para_bloqueada; el_maximo_de_texto_se_valida_con_su_valor | Implementado y probado | `ESTADO_INVALIDO`, `MOTIVO_BLOQUEO_OBLIGATORIO`, `DESCRIPCION_OBLIGATORIA`, `TEXTO_DEMASIADO_LARGO`. |
| — | Actividad no Completada o marcada | B reactivacion::una_actividad_que_no_esta_completada_no_se_reactiva; una_actividad_marcada_por_error_no_se_reactiva · R-INT | Implementado y probado | `ACTIVIDAD_NO_COMPLETADA`, `ACTIVIDAD_MARCADA_POR_ERROR`. |
| — | Bitácora de la fecha de la reactivación | B reactivacion::si_la_bitacora_de_la_fecha_esta_cerrada_se_rechaza…; no_hace_falta_reabrir_la_jornada_cerrada_de_la_finalizacion; la_bitacora_de_la_fecha_se_crea_en_la_misma_operacion_y_una_sola_vez | Implementado y probado | Solo importa la jornada de la fecha de la reactivación (D-04); se crea si no existe (D-01). |
| — | Tras reactivar | B reactivacion::tras_reactivar_se_pueden_registrar_avances_y_completar_de_nuevo; un_segundo_ciclo_de_reactivacion_es_valido; la_reactivacion_cuenta_como_actividad_continuada_para_cerrar_la_jornada; despues_de_reactivar_se_puede_planificar_su_continuacion | Implementado y probado | |
| — | Idempotencia y atomicidad | B reactivacion::repetir_la_misma_peticion_con_la_misma_clave_no_duplica; reutilizar_la_clave_con_otra_peticion_se_rechaza; si_falla_el_guardado_no_queda_ni_el_avance_ni_la_bitacora_ni_la_clave · R-INT | Implementado y probado | |
| — | Concurrencia | B reactivacion::reactivaciones_simultaneas…; la_misma_reactivacion_simultanea…; una_reactivacion_espera_a_quien_tiene_la_actividad_bloqueada…; una_reactivacion_y_un_avance_simultaneos… · R-INT (8 peticiones simultáneas reales: una sola efectiva) | Implementado y probado | |

### M3-05 — Marcar una actividad como registrada por error

**Componente:** `POST /mi/actividades/{id}/marca-error` · acción «Marcar como registrada por error» del detalle de la actividad (`ActivityMarkActions`, diálogo con motivo)

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-115 | Sin avances posteriores, con motivo, queda marcada | B marca_error::marca_una_actividad_sin_avances_con_motivo; los_avances_de_la_propia_jornada_de_origen_no_lo_impiden; el_origen_es_la_fecha_de_la_bitacora_de_origen_y_no_creada_en · R-INT · R-UI | Implementado y probado | El origen es la fecha de la bitácora de origen (PA-28). |
| CA-116 | Sin motivo no se permite | B marca_error::sin_motivo_no_se_permite_y_no_cambia_nada · F mark_form (motivo en blanco) · R-UI | Implementado y probado |  |
| CA-117 | Con avances en jornadas posteriores no se permite | B marca_error::con_avances_en_jornadas_posteriores_a_su_origen_no_procede; test_db_marca_error (disparador) · F mark_rules · R-INT · R-UI | Implementado y probado | La interfaz no ofrece la acción; el servidor y la base la rechazan igualmente. |
| CA-118 | La de otra persona no se marca | B marca_error::la_actividad_de_otra_persona_no_se_marca_ni_se_revierte; un_supervisor_del_mismo_equipo… · R-INT | Implementado y probado | 404 indistinguible de una inexistente (T-01). |
| CA-119, CA-120, CA-121 | Fuera de vistas y recuentos; consultable; no se borra | Ver M2-07, M2-08 y M3-07 | Implementado y probado | CA-120 se prueba en M3-07: la auditoría de una marcada sigue consultable. |
| CA-287 | Jornada cerrada con dos actividades válidas: se acepta y sigue cerrada | B marca_error::con_otra_actividad_valida_se_marca_sin_reabrir_la_jornada · F mark_form · R-INT | Implementado y probado | No se reabre ni se renueva `modificada_en`. |
| CA-288 | Única actividad válida de una jornada cerrada: se rechaza sin cambiar nada | B marca_error::si_era_la_unica_actividad_valida…; una_actividad_con_avance_anterior_al_origen… · F mark_form · R-INT · R-UI | Implementado y probado | `MARCA_INVALIDARIA_CIERRE`; la comprobación abarca toda jornada cerrada en la que la actividad cuenta (ver diferencia 12). |
| CA-289 | Con otra actividad continuada, se acepta | B marca_error::otra_actividad_iniciada_antes_y_continuada_en_la_jornada_la_mantiene_valida | Implementado y probado |  |
| — | Auditoría de la marca | B marca_error::marcar_deja_una_unica_entrada…; la_entrada_pertenece_a_la_jornada_de_origen… · R-INT | Implementado y probado | Se consulta con M3-07. |
| — | Idempotencia y atomicidad | B marca_error::repetir_la_misma_marca…; si_falla_el_guardado_no_queda_ni_la_marca_ni_la_clave | Implementado y probado |  |
| — | Concurrencia | B marca_error::marcas_simultaneas…; dos_actividades_que_son_las_unicas…; marcar_espera_a_quien_tiene_la_jornada_bloqueada…; cerrar_espera_a_quien_marca…; un_avance_espera_a_quien_marca… · R-INT (peticiones simultáneas reales) | Implementado y probado | Marcar, cerrar y registrar avances se serializan. |

### M3-06 — Revertir la marca de error

**Componente:** `POST /mi/actividades/{id}/marca-error/reversion` · acción «Revertir marca» del detalle (confirmación sin motivo)

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-122 | Vuelve a las vistas y recuentos, con entrada de auditoría | B marca_error::revertir_devuelve_la_actividad_a_las_vistas_operativas; revertir_deja_una_unica_entrada_con_la_marca_anterior · F mark_form · R-INT · R-UI | Implementado y probado |  |
| CA-123 | La de otra persona no se revierte | B marca_error::la_actividad_de_otra_persona_no_se_marca_ni_se_revierte | Implementado y probado |  |
| CA-290 | Jornada cerrada: sigue cerrada, consta en la auditoría y la actividad vuelve a contar | B marca_error::la_jornada_cerrada_sigue_cerrada_y_la_actividad_vuelve_a_contar · R-INT | Implementado y probado |  |
| — | Sin marca vigente | B marca_error::sin_marca_vigente_no_hay_nada_que_revertir · F mark_form | Implementado y probado | `MARCA_NO_VIGENTE`. |
| — | Idempotencia y atomicidad | B marca_error::repetir_la_misma_reversion…; si_falla_la_reversion_la_marca_sigue_vigente | Implementado y probado |  |

**Pruebas de base de datos (migración 0007):** `test_db_marca_error` comprueba con intentos reales los permisos por columna, la restricción de coherencia de la marca y los disparadores (marca no reescribible, sin marcar con avances posteriores, sin avances ni continuaciones sobre una marcada).

### M3-07 — Consultar la auditoría de un registro

**Componente:** `GET /auditoria?tipo_objeto=…&objeto_id=…` · `AuditPage` (línea de tiempo), con entradas desde Mi bitácora («Ver auditoría de la jornada») y desde el detalle de la actividad («Ver historial de auditoría» y «Ver auditoría» de cada avance). Solo para la persona propietaria: el supervisor y M4 quedan fuera.

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-110 | El propietario consulta la auditoría de su registro y ve las entradas | B auditoria::los_ciclos_de_cierre_y_reapertura_se_reconstruyen_en_orden; la_marca_y_su_reversion_constan…; la_reactivacion_y_las_correcciones_de_un_avance_se_reconstruyen · F audit_page · R-INT · R-UI | Implementado y probado | Por tipo: bitácora, actividad, avance y planificación (vacía: no se audita). |
| CA-106, CA-108 | La entrada trae autor, fecha real, operación, valor anterior y nuevo, con contexto para reconstruir | B auditoria::cada_entrada_tiene_los_campos_del_contrato…; una_actividad_creada_en_una_jornada_pasada_deja_su_entrada · F audit_changes, audit_page · R-UI | Implementado y probado | La interfaz muestra «Antes» y «Ahora» por campo, sin identificadores técnicos. |
| CA-109 | La reapertura consta con su motivo | B auditoria::los_ciclos_de_cierre_y_reapertura… · F audit_page · R-UI | Implementado y probado |  |
| CA-65 | Un registro corregido conserva las tres fechas y el cambio consta | B auditoria::la_correccion_del_resumen_tras_reabrir…; guardar_el_resumen_de_una_jornada_pasada… | Implementado y probado |  |
| CA-104 | Varias correcciones sucesivas se reconstruyen | B auditoria::la_reactivacion_y_las_correcciones…; el_orden_refleja_el_orden_en_que_se_aplicaron_las_correcciones_simultaneas | Implementado y probado | El momento es el del reloj real: el orden de la consulta es el de aplicación. |
| CA-266 | Cada ciclo de cierre y reapertura es reconstruible | B auditoria::los_ciclos_de_cierre_y_reapertura_se_reconstruyen_en_orden · F audit_page | Implementado y probado |  |
| CA-267 | Una operación con varios campos es una sola entrada | B auditoria::una_operacion_que_modifica_varios_campos_es_una_sola_entrada | Implementado y probado |  |
| CA-114 | Las entradas no se borran ni se reescriben | B auditoria::el_momento_de_la_entrada_es_el_de_la_operacion_y_no_se_reescribe; la_auditoria_no_admite_ninguna_otra_operacion | Implementado y probado | La consulta es de solo lectura (sin POST, PUT, PATCH ni DELETE). |
| CA-120 | Una marcada por error sigue consultable en el historial y en la auditoría | B auditoria::una_actividad_marcada_sigue_siendo_consultable_en_la_auditoria · F audit_page · R-UI | Implementado y probado | Con CA-119 y CA-121 (M2-07, M2-08, M3-05). |
| CA-112 | Un compañero que no es propietario ni supervisor autorizado no puede | B auditoria::la_auditoria_de_un_registro_ajeno_y_de_uno_inexistente_es_indistinguible; una_persona_solo_ve_sus_propias_entradas; extensiones_m2_m3::el_supervisor_consulta_la_auditoria_del_equipo_de_cada_registro_y_nadie_mas (M4-T6) | Implementado y probado | Consultan la propietaria y el supervisor vigente del equipo del registro (adenda M4-T6). |
| CA-113 | El supervisor de otro equipo no puede | B extensiones_m2_m3::el_supervisor_consulta_la_auditoria_del_equipo_de_cada_registro_y_nadie_mas; el_supervisor_trasladado_o_desactivado_pierde_la_autorizacion (M4-T6) | Implementado y probado | La prueba anterior (`un_supervisor_del_mismo_equipo_todavia_no_consulta…`) se sustituyó por la del supervisor del MISMO equipo (CA-111). |
| CA-286 | La auditoría de un registro inexistente y la de uno ajeno son indistinguibles | B auditoria::la_auditoria_de_un_registro_ajeno_y_de_uno_inexistente…; un_tipo_que_no_corresponde_al_registro…; la_autorizacion_se_aplica_antes_de_leer_las_entradas · R-INT | Implementado y probado | Mismo estado y mismo cuerpo; no se revela si existe. |
| CA-285 | Las entradas de la provisión no aparecen | B auditoria::las_entradas_de_provision_administrativa_no_aparecen | Implementado y probado | D-11. |
| CA-111 | El supervisor autorizado del equipo ve las entradas | B auditoria::un_supervisor_del_mismo_equipo_consulta_la_auditoria_de_su_equipo; extensiones_m2_m3::el_supervisor_consulta_la_auditoria_del_equipo_de_cada_registro_y_nadie_mas; la_paginacion_de_la_auditoria_del_supervisor…; la_consulta_sql_de_la_auditoria_coincide… · HTTP real (M4-T6) | Implementado y probado | Desbloqueado por M4-T6 (RA-10): el supervisor vigente del equipo del registro por su fecha laboral; ver la adenda. |
| — | Paginación y orden (D-10) | B auditoria::la_paginacion_no_repite_ni_omite…; el_orden_es_cronologico_y_estable…; un_cursor_sigue_siendo_valido…; los límites y cursores inválidos · F audit_page (ver más, fallo al cargar más, doble toque) | Implementado y probado | `{elementos, siguiente}`; límite por defecto y máximo configurables. |
| — | Validación de parámetros | B auditoria::no_existe_consulta_sin_objeto…; los tipos, identificadores, operaciones y parámetros inválidos; el_formato_se_evalua_antes_que_la_visibilidad | Implementado y probado | No hay listado global. |
| — | Lo que no produjo cambios no aparece | B auditoria::las_operaciones_rechazadas_o_sin_cambios_no_dejan_entrada | Implementado y probado |  |
| — | Sin sesión | B auditoria::sin_sesion_no_se_consulta; con_el_acceso_desactivado_no_se_consulta | Implementado y probado |  |

### M3-03 — Corregir un avance ya registrado

**Componente:** `PATCH /mi/avances/{id}` · acción «Corregir» de cada avance del detalle de la actividad (`CorrectionPage`, con confirmación si cambia el estado actual)

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-79 | Una corrección que cambia el último avance recalcula el estado y se audita | B correccion::cambiar_el_estado_del_ultimo_avance_recalcula_el_estado_actual · F correction_form · R-INT · R-UI | Implementado y probado | `estado_actual_cambio` verdadero; la entrada incluye el estado actual anterior y nuevo. |
| CA-80 | Corregir uno que no es el último no cambia el estado y se audita | B correccion::cambiar_el_estado_de_un_avance_que_no_es_el_ultimo… · F correction_form · R-INT | Implementado y probado |  |
| CA-62 | Fecha de modificación de actividades y avances | B correccion::el_avance_corregido_muestra_su_fecha_de_modificacion…; test_db_correccion_avance · R-INT · R-UI | Implementado y probado | `modificado_en` es el del registro hasta que se corrige (migración 0008). |
| CA-101, CA-107 | Un avance ajeno no se corrige, tampoco por un supervisor | B correccion::el_avance_de_otra_persona_no_se_corrige; un_supervisor_del_mismo_equipo_tampoco_corrige · R-INT | Implementado y probado | 404 indistinguible de un avance inexistente (T-01). |
| CA-102, CA-284 | Con la jornada cerrada se reabre antes; la reapertura y la corrección constan | B correccion::una_bitacora_cerrada_exige_reabrirla_antes; solo_importa_la_bitacora_del_propio_avance · F correction_form · R-INT | Implementado y probado | D-04: otras jornadas cerradas de la actividad no se reabren. |
| CA-103, CA-104 | Toda corrección queda auditada y se reconstruye | B correccion::una_correccion_deja_una_unica_entrada…; varias_correcciones_sucesivas_se_reconstruyen_en_orden; la_correccion_de_una_jornada_de_hoy_tambien_se_audita · R-INT | Implementado y probado | Se consulta con M3-07. |
| CA-105, CA-106 | Corrección en jornada pasada: una sola entrada con autor, fecha, valor anterior y nuevo | B correccion::una_correccion_deja_una_unica_entrada… | Implementado y probado | Una sola entrada `correccion`, no una de corrección y otra de modificación de jornada pasada (IR-35). |
| CA-211 | Corregir la descripción de un avance anterior a la finalización no reactiva ni crea un avance | B correccion::corregir_con_una_actividad_completada_la_descripcion…; una_correccion_no_crea_borra_ni_reordena_avances · R-INT | Implementado y probado |  |
| CA-236 | Corregir a Completada un avance anterior a otros, sin reactivación, se rechaza | B correccion::corregir_a_completada_un_avance_anterior_a_otros_sin_reactivacion_se_rechaza; test_secuencia (violaciones) · F correction_rules, correction_form · R-INT · R-UI | Implementado y probado | `SECUENCIA_INVALIDA` con el avance y el motivo. |
| CA-237 | Una corrección rechazada no cambia avances, estado actual ni auditoría | B correccion::(instantánea antes y después en cada rechazo) · R-INT | Implementado y probado |  |
| CA-238 | Corregir la finalización a otro estado, si la secuencia sigue siendo válida, se acepta | B correccion::cambiar_el_estado_del_ultimo_avance_recalcula…; corregir_la_finalizacion_cuando_hay_una_reactivacion_posterior_se_rechaza | Implementado y probado |  |
| CA-239 | Ninguna corrección crea una reactivación automática | B correccion::una_correccion_rechazada_no_crea_ninguna_reactivacion; test_secuencia (con_estado_corregido) | Implementado y probado |  |
| CA-297, CA-298 | Con la marca vigente no se corrige; revertida, sí | B correccion::los_avances_de_una_actividad_marcada_no_se_corrigen; revertida_la_marca_se_pueden_corregir; test_db_correccion_avance (disparador) · F correction_form · R-INT | Implementado y probado |  |
| — | PA-27 y PA-29 (opción A) | B correccion::un_par_preexistente_admitido_por_pa27…; una_correccion_que_agrava_el_par_preexistente_se_rechaza; una_correccion_puede_resolver…; test_secuencia (violaciones_nuevas) · F correction_rules | Implementado y probado | Se comparan las violaciones de antes y después. |
| — | Sin cambios | B correccion::una_correccion_con_los_valores_vigentes_no_hace_nada | Implementado y probado | 200 sin entrada y sin renovar `modificado_en` (T-04). |
| — | Reactivaciones | B correccion::se_corrige_el_avance_de_una_reactivacion…; una_reactivacion_no_se_corrige_a_completada | Implementado y probado | Conservan su condición de reactivación. |
| — | Idempotencia y atomicidad | B correccion::repetir_la_misma_correccion…; si_falla_el_guardado_no_queda_ni_el_cambio_ni_el_estado_ni_la_clave | Implementado y probado |  |
| — | Concurrencia | B correccion::correcciones_simultaneas…; una_correccion_espera_a_quien_tiene_la_actividad_bloqueada_y_ve_su_marca; …a_quien_cierra_la_jornada…; …a_un_avance_nuevo… · R-INT (peticiones simultáneas reales) | Implementado y probado | Se serializa con avances nuevos, cierre y marcado por error. |

**Pruebas de base de datos (migración 0008):** `test_db_correccion_avance` comprueba con intentos reales que la aplicación solo corrige estado, descripción, motivo y `modificado_en`, sin borrar nada; que el identificador, la actividad, la bitácora, el momento de registro y la reactivación son inmutables incluso para el propietario del esquema; que `modificado_en` solo avanza con un cambio; y que no se corrige un avance de una actividad marcada.

## 4. Diferencias y decisiones señaladas

Ninguna se ha resuelto cambiando una regla confirmada. Cada una indica qué hace hoy el código.

| # | Tema | Qué hace hoy | Situación |
|---|---|---|---|
| 1 | **IR-11 frente a CA-78** | Una inserción retroactiva se incorpora a la secuencia sin eliminar ni modificar los avances posteriores; al registrar un avance nuevo solo se mira el avance anterior al punto de inserción, y el estado actual sale del orden laboral completo. No amplía las transiciones permitidas | **Decidido y armonizado** (2026-11-09, PA-27) en IR-11, M2-05 y HU-2.9. **PA-29 resuelta** (opción A): una corrección no debe introducir violaciones nuevas; se aplicará en M3-03 |
| 2 | **403 frente a 404 según visibilidad** | Todo recurso que no es propio responde 404 `RECURSO_NO_DISPONIBLE`, con el mismo cuerpo que uno inexistente (T-01). `OPERACION_NO_PERMITIDA` (403) no se emite porque aún no hay recursos ajenos visibles | **Resuelta en M4-T6** (2026-11-18, ver la adenda al final); documentado en `convenciones.md` 3.1 |
| 3 | **CA-62** | La fecha de modificación existe en la bitácora y en cada avance (columna `modificado_en`, migración 0008) | **Implementado** con M3-03 |
| 4 | **CA-210** | Una actividad Completada se rechaza al planificar su continuación y, una vez reactivada con M3-04, la admite | **Resuelto con M3-04** (T10) |
| 5 | **CA-212, CA-213 y CA-214** | Probados con un traslado oficial de M1-05 (M1-T5). La actividad pertenece a una persona, no a un equipo | **Implementado y probado** (B, R-INT y R-UI) |
| 6 | **Fechas laborales anteriores al origen de la actividad** | Se acepta un avance con una fecha cubierta y no futura aunque sea anterior a la jornada de origen de la actividad. No se valida contra `creada_en`, que es una marca técnica de registro y no el inicio laboral | **Provisional** (2026-11-09, PA-28): vinculado a definir el origen laboral de las actividades en M3. No se cambia el código |
| 7 | **Paginación y formato de respuestas** | El listado devuelve `{"elementos": [...], "siguiente": cursor o null}` con `limite` y `continuar_desde` configurables (convenciones 6.1). Las escrituras devuelven sobres con nombre (`{"bitacora"}`, `{"actividad", "planificacion", "bitacora_creada"}`, `{"avance", "actividad", "bitacora_creada"}`) | **Aprobado** el envoltorio del listado (2026-11-09) y `{"bitacora": …}` y `bitacora_creada`. M2-08 y convenciones 6.1 lo reflejan |
| 8 | **Resumen omitido o nulo** | Equivale a un resumen vacío y se acepta al guardar; solo impide cerrar (D-03) | **Decidido y mantenido**. Documentado en M2-02 |
| 9 | **Varias continuaciones en la misma fecha** | Se registran todas si proceden de operaciones distintas (distinta clave); el mismo reintento no duplica | **Aprobado**. Documentado en M2-04 |
| 10 | **`modificada_en` al cerrar y reabrir** | No cambia: es la fecha de modificación del contenido | **Aprobado**. Documentado en M3-01 |
| 11 | **Marca de error (M3-05 y M3-06)** | Implementadas (T11). Las pruebas anteriores que preparaban la marca por SQL se adaptaron a estados alcanzables: una actividad con avances posteriores a su origen ya no puede marcarse ni siquiera por SQL | **CA-119, CA-121 y CA-283 implementados**; CA-120, con M3-07 (T13) |
| 12 | **Alcance de la comprobación de cierre de M3-05** | El contrato la describe sobre la jornada de origen. Como PA-28 admite un avance anterior al origen (que cuenta la actividad como continuada en esa jornada anterior), la comprobación se aplica a **toda jornada cerrada en la que la actividad cuenta** | **Aprobado** (2026-11-09): la comprobación abarca todas las jornadas cerradas cuyas condiciones de cierre dependan de la actividad |
| 13 | **Respuesta de M3-05 y M3-06** | `{"actividad": …}`, el sobre con nombre que usan las demás respuestas con una actividad; el contrato dice «la Actividad» | **Aprobado** (2026-11-09), con el esquema completo de la entidad |
| 14 | **Interpretaciones menores de M3-03** | Un `motivo_bloqueo` enviado para un estado distinto de Bloqueada es `SOLICITUD_INVALIDA` (como en M2-05); corregir una reactivación a Completada se rechaza con `SECUENCIA_INVALIDA`; una violación se identifica por el avance y el motivo para compararlas antes y después (PA-29) | **Aprobado** (2026-11-09): identidad estable = avance afectado y tipo de violación; una violación nueva o agravada se rechaza aunque existan otras históricas toleradas |
| 15 | **Corrección y modificación de jornada pasada** | Corregir un avance de una jornada pasada deja UNA sola entrada `correccion` (no una de corrección y otra de modificación de jornada pasada), como indica IR-35 | **Según el contrato** |
| 16 | **400 frente a 405, y rechazos de CSRF y de origen** | El servidor responde `400 SOLICITUD_INVALIDA` (sin cabecera `Allow`) a todo error HTTP del marco que no sea 404, incluido un método no admitido en una ruta existente (comprobado con `DELETE`, `PUT`, `PATCH` y `POST` sobre rutas que no los admiten). Una petición de escritura sin token CSRF o con un `Origin` no permitido también da 400, con `detalles` (`csrf_invalido`, `origen_no_permitido`), y no cambia nada. Las convenciones definen 400 como «petición mal formada» y no mencionan 405 ni el código de los rechazos de CSRF | **Decidido (PA-30 `[CONFIRMADO]`, 2026-11-11) e implementado en M1-T0**: un método no admitido en una ruta existente responde 405 `METODO_NO_PERMITIDO` con `Allow`; el 400 para solicitudes inválidas y el rechazo provisional de CSRF u origen se mantienen. La descripción de la columna anterior corresponde al comportamiento previo al ticket. Ninguna regla de negocio se ve afectada |
| 17 | **Alcance de la auditoría de una actividad frente a la de sus avances** | La consulta es siempre de UN registro: la de una actividad devuelve su alta en jornada pasada, su marca y su reversión; las correcciones y reactivaciones constan en la de cada avance, y los cierres y reaperturas, en la de la bitácora. La interfaz ofrece el enlace de cada una | **Según el contrato** (M3-07, T13); verificado de extremo a extremo en T14 |
| 18 | **Instante de las entradas de auditoría** | `momento` es el del reloj real al aplicar el cambio (`clock_timestamp()`), no el inicio de la transacción: el orden de la consulta es el de aplicación incluso con operaciones simultáneas. Las entradas anteriores conservan su momento | **Aplicado** en T13; la prueba de seis correcciones simultáneas en T14 las recupera encadenadas |
| 19 | **UTC en los eventos de auditoría** | Todos los instantes de la API (`momento` de la auditoría, `cerrada_en`, `modificado_en`, valores de auditoría) son ISO 8601 en UTC con `Z`; la base los guarda como `timestamptz`. La interfaz los muestra en la hora local | **Comprobado** en T14 (HTTP y base) |
| 20 | **403 frente a 404 según la visibilidad** | Se comprobó en T14 con una colaboradora ajena y con la supervisión: la auditoría, la consulta, la corrección, la reactivación, la marca y su reversión de un registro ajeno responden 404 `RECURSO_NO_DISPONIBLE`, con el mismo cuerpo que un registro inexistente. No se emite 403 `OPERACION_NO_PERMITIDA` porque no hay recursos ajenos visibles | **Resuelta en M4-T6** (igual que la diferencia 2; ver la adenda) |
| 21 | **Esquema de `smartwork_app` frente al historial de migraciones** | El esquema real (migraciones 0001 a 0008) es idéntico al de una instalación nueva creada con `alembic upgrade head`, salvo dos permisos del esquema `public`: tiene `GRANT ALL … TO smartwork_owner` y conserva el `USAGE` de PUBLIC que las bases de pruebas revocan. Ambos proceden del aprovisionamiento manual del servidor 5432, no de ninguna migración | **Sin efecto funcional; no se ha modificado** (inspección solo de lectura). `smartwork_app` está en la migración **0008** (0001 a 0005 aplicadas el 2026-11-06 y 0006 a 0008 el 2026-11-09, esta vez con un respaldo previo) |

## 5. Criterios que dependen de otros módulos o siguen parciales

M3-01 a M3-07 están implementados. Lo que **no** se puede dar por cumplido hasta que exista el módulo indicado, o por una limitación de la prueba:

| Módulo o causa | Criterios | Qué falta |
|---|---|---|
| **M4** | CA-111 (M3-07) | **Resuelto en M4-T6** (ver la adenda): la consulta de la auditoría por el supervisor autorizado del equipo, con la política de visibilidad histórica (RA-10) |
| **M4** | CA-15 a CA-21, CA-176 a CA-178, CA-216, CA-217, CA-249 (visibilidad histórica) | La política interna está implementada y probada (M1-T1) pero **ningún endpoint la usa**: no se declaran cumplidos hasta que M4 los exponga y se pruebe de extremo a extremo. El traslado real ya existe (M1-05, M1-T3) y la política se ha probado con líneas temporales creadas por esa operación |
| **M4** | Respuesta 403 frente a 404 | **Resuelto en M4-T6** (ver la adenda): seis operaciones responden 403 sobre lo visible ajeno y 404 sobre lo demás; M2-07 conserva el 404 |
| **M2 / M4** | DM-08 (clase «planificación conservada») | CA-262 se cumple en los datos (M1-T4: la planificación posterior a una finalización se conserva con su actividad y su propietaria y sigue consultable mientras la persona tiene pertenencia vigente), pero las vistas de M2 siguen presentando toda planificación como vigente (`planificacion_a_dict`): la clasificación «conservada» no existe en la proyección. No se ha modificado M2; la decisión es de M2 y M4 |
| **Decisión** | PA-28 | Origen laboral de la actividad (hoy: la fecha de la bitácora de origen); la restricción de avances anteriores al origen es provisional |
| **Prueba** | CA-76 (M2-05 y M2-07) | Un empate real de fecha y momento no se puede forzar por HTTP: la regla de desempate está probada como regla pura y en el orden de la consulta |

### Recorrido de M1-T5: qué está probado de extremo a extremo y qué no

**Probado de extremo a extremo** (B con PostgreSQL real, la CLI de provisión y la API HTTP; R-INT con un servidor uvicorn en otro proceso; R-UI con el cliente Flutter en Chrome): CA-212, CA-213 y CA-214, y con ellos, desde la nueva pertenencia, la aplicación de FECHA_NO_CUBIERTA y de la fecha no futura, M3-01 (cierre de la jornada de T antes del traslado), M3-02 (reapertura desde U), M3-03 (corrección de un avance de T desde U), M3-07 (auditoría con la fecha laboral de la jornada y a nombre de la propietaria, sin las entradas de provisión, D-11), la autorización antes y después (ninguna otra persona accede: 404 provisional) y el rechazo de operar sin pertenencia vigente (IR-38) con los registros y su propiedad conservados.

**Cómo se vive el día del traslado sin tocar pertenencias por SQL:** el traslado se registra con la orden oficial (`registrar-traslado`, fecha efectiva futura). Las operaciones de M2 y M3 toman «hoy» de una sola función de producción (`politica_acceso.fecha_actual_en`); en las pruebas se sustituye con `monkeypatch` (en el servidor real de R-INT y R-UI, con un arranque de prueba fuera del repositorio que la lee de un archivo). No cambia el reloj del sistema ni el de PostgreSQL (que sigue protegiendo la edición de pertenencias efectivas), ni ningún código de producción. Lo único preparado por SQL es la contraseña de las personas de prueba (el primer acceso, M1-03, no existe).

**Solo a nivel de dominio o de base de datos (no de extremo a extremo):** la política de visibilidad histórica de M1-T1 (quién lee las jornadas de P según el equipo en cada fecha), porque no hay endpoint hasta M4; el enlace de la auditoría con la operación original (`test_enlace_auditoria.py`); y los controles de PostgreSQL sobre la edición de pertenencias (M1-T3 y M1-T4).

**No demostrado** y pendiente de otros módulos: CA-15 a CA-21, CA-176 a CA-178, CA-216, CA-217 y CA-249 como consulta HTTP (M4); el acceso del supervisor (CA-111); y la clase «planificación conservada» de DM-08 en las vistas de M2 y M4 (M2 presenta toda planificación como vigente; no se modificó). Limitación del cliente: el recorrido con el cliente Flutter requiere el servidor de prueba con reloj controlado; el cliente actual no tiene pantalla de provisión ni de visibilidad entre personas, así que no se pudo comprobar la autorización de otras personas desde la interfaz.

### Recorrido de M1-T7: protección frente a intentos fallidos de autenticación

**Fuente:** decisiones de ADR-002 A9 y A11 aprobadas el 2026-11-17 (no hay criterios de aceptación nuevos: no se inventaron) y el contrato M1-01a; CA-05 (ninguna respuesta, registro ni informe contiene credenciales en claro), CA-29, CA-255 y CA-259 (sin sesión con acceso desactivado o sin pertenencia) y el contrato de la persona operadora (M1-02a, M1-08). Pruebas (`B`, PostgreSQL real; `R-INT`, uvicorn real en otro proceso; `R-UI`, Flutter):

| Decisión aprobada | Pruebas |
|---|---|
| Cinco intentos libres; esperas de 30 s, 1, 2, 4, 8, 16 y 32 min y 1 hora de máximo | `test_control_de_intentos.py` (curva, progresión con reloj controlado), `test_login_intentos_api.py` (progresión HTTP) |
| Contador por identificador normalizado y origen; olvido a las 24 h; reinicio solo tras una autenticación COMPLETA (contraseña correcta, acceso habilitado y pertenencia vigente; cierre del 2026-11-17) | `test_control_de_intentos.py`, `test_login_intentos_api.py` (variantes de mayúsculas, espacios y Unicode; otro origen no espera) |
| 429 `DEMASIADAS_SOLICITUDES` y `Retry-After`; credenciales correctas durante la espera; respuestas uniformes | `test_login_intentos_api.py`, `test_login_uniformidad.py` (mismo número de verificaciones y parámetros Argon2; ningún hash durante una espera) |
| Límites por origen de 30 en 5 minutos y 200 en 1 hora; sin penalizar a una red compartida; sin bloqueos permanentes | `test_control_de_intentos.py`, `test_login_intentos_api.py` |
| Reserva atómica y concurrencia | `test_control_de_intentos_concurrencia.py` (20 reservas simultáneas: exactamente 5; 50 cuentas desde un origen: exactamente 30; sin interbloqueos; 20 inicios HTTP simultáneos: 5 × 401 y 15 × 429) |
| HMAC con `AUTH_PEPPER`, sin secretos en contadores, eventos ni registros | `test_login_intentos_api.py` (recorre las tablas y los registros), `test_db_control_de_intentos.py` (restricciones de forma) |
| Origen: dirección de conexión; proxy solo si es de confianza; cabeceras falsificadas | `test_control_de_intentos.py`, `test_login_intentos_api.py` (DT-07) |
| Eventos de A11 (seis tipos), separados de la auditoría; retención de 30 días y purga | `test_login_intentos_api.py`, `test_desactivacion_cli.py` (revocación), `test_operador_intentos.py` (purga), `test_db_control_de_intentos.py` (solo anexado, borrado solo pasados 30 días) |
| Persona operadora: misma curva, contador separado, sin deshabilitarla, sin credenciales | `test_operador_intentos.py` (también como proceso real) |
| Cierre de M1-T7 (2026-11-17): una contraseña válida sin poder operar no reinicia el contador ni devuelve la reserva de origen y no permite sondeo ilimitado; el reinicio va con la sesión; la auditoría de la desactivación es siempre efectiva y el evento de revocación solo cuenta sesiones reales, sin identificadores ni secretos | `test_login_intentos_api.py`, `test_control_de_intentos_concurrencia.py`, `test_desactivacion_cli.py` |
| Sesión de 24 h y 1 h de inactividad | `test_control_de_intentos.py` (valores por defecto sin `.env`), `test_login_intentos_api.py` |
| Migración 0013: privilegios mínimos, instalación desde cero, datos existentes y reversión | `test_db_control_de_intentos.py` |
| CSRF, `Origin`, cookies y sesiones sin cambios; compatibilidad con M1-T6 | `test_login_intentos_api.py`, y las suites de M1-T6 sin cambios |
| Flutter: `Retry-After`, mensaje fijo, cuenta atrás, envío deshabilitado y rehabilitado, nueva espera, móvil y escritorio | `login_wait_test.dart` |

**Resultados:** 2619 superadas y 1 omitida a propósito (193 más que al cerrar M1-T6) en el backend y 638 superadas y `flutter analyze` sin incidencias en Flutter. Mutaciones: backend 71 de 71 muertas tras reforzar las pruebas (56 sobre el código y 15 sobre la migración; en la primera pasada sobrevivieron 7 de 70, que revelaron huecos reales y se corrigieron: el olvido del contador a las 24 horas oculto por la limpieza, la comprobación vacua de «transacción abierta durante Argon2», `Retry-After` sin exponer por CORS, el dominio de la clave de la persona operadora, la actualización de un evento antiguo y una mutación mal planteada); Flutter 23 de 24 muertas; la superviviente es defensiva y equivalente (ninguna acción de la interfaz puede iniciar una espera nueva mientras otra sigue activa: el envío está deshabilitado y protegido); en la primera pasada sobrevivieron 3 y revelaron que faltaba probar el envío con Enter durante la espera y que un `Retry-After` de otro error no debe iniciar una espera. Evidencia real: servidor uvicorn real en otro proceso y la CLI como procesos reales sobre una base desechable creada con `alembic upgrade head`: 47 comprobaciones correctas (fallo cerrado sin `AUTH_PEPPER`; cinco intentos libres y 429 con `Retry-After`; uniformidad entre cuenta existente e inexistente; espera real de 30 s y reinicio; límite por origen de 30 en 5 minutos y red compartida; cabeceras falsificadas y proxy de confianza; eventos y ausencia de secretos; 30 intentos simultáneos contra una cuenta: exactamente 5 × 401 y 25 × 429; carreras con la desactivación del acceso sin sesiones residuales; progresión real de la espera con la curva configurada; persona operadora; purga y retención; privilegios por rol). Chrome: Chrome real (protocolo CDP, sin interfaz) con el cliente compilado, escritorio y móvil emulado: 30 comprobaciones correctas (mensaje uniforme en los cinco intentos libres, 429 con la cuenta atrás visible, envío deshabilitado, nueva espera tras recargar con la restricción aún vigente, rehabilitación al terminar y acceso con la contraseña correcta).

**No demostrado, pendiente o fuera de M1-T7:** el tope agregado de 100 fallos con deshabilitación de la contraseña (decisión diferida: **no se declara resuelto el requisito agregado** por el contador por cuenta y origen); la resistencia a ataques distribuidos y a la rotación de direcciones IPv6; el funcionamiento detrás de un balanceador real de AWS ECS (DT-07); la programación de la purga de eventos (no hay planificador); PA-06 general; la recuperación de contraseña (M1-T8); y la medición de tiempos de respuesta (se comprueba la estructura que los hace comparables, no tiempos de pared).

### Recorrido de M1-T8: primer acceso y recuperación con código (la matriz completa de M1 está en `docs/evidencia/matriz-trazabilidad-m1.md`, M1-T9)

**Fuente:** decisiones de ADR-002 (A3, A4, A5, A6, A8, D1 a D10) aprobadas el 2026-11-17 y los contratos M1-03a, M1-03b, M1-09a y M1-09b; criterios CA-23, CA-24, CA-25, CA-27 y CA-254, y CA-05 (ninguna respuesta, registro ni informe contiene credenciales en claro). No se crearon criterios nuevos. **Desde M1-T9 la matriz completa de M1 es `docs/evidencia/matriz-trazabilidad-m1.md`**; esta sección se conserva como registro de M1-T8.

| Criterio o decisión | Componente | Pruebas | Estado |
|---|---|---|---|
| CA-23: el primer acceso entregado permite acceder | `POST /acceso/primer-acceso` (no abre sesión; la persona inicia sesión después) y pantalla de primer acceso | B: `test_canje_primer_acceso.py`::el_primer_acceso_establece_la_contrasena_consume_el_codigo_y_no_abre_sesion, despues_del_canje_la_persona_inicia_sesion_con_su_contrasena · F: `access_code_test.dart` · R-UI (Chrome, T8.5) | Implementado y probado |
| CA-24: un primer acceso ya utilizado no se permite de nuevo | función `canjear_codigo_primer_acceso` | B: `test_canje_primer_acceso.py`::despues_del_canje_la_persona_inicia_sesion_con_su_contrasena_y_el_codigo_no_se_reutiliza, dos_o_mas_canjes_simultaneos…, todas_las_causas_de_un_codigo_no_valido…; `test_db_codigo_unico.py` (uso único) | Implementado y probado |
| CA-25: el código identifica solo a esa persona | ídem | B: `test_canje_primer_acceso.py`::ca25_el_codigo_de_una_persona_no_da_acceso_como_otra | Implementado y probado |
| CA-27: recuperar el acceso con el procedimiento | `emitir-codigo-recuperacion` (CLI), `POST /acceso/recuperacion` y pantalla | B: `test_canje_recuperacion.py`::la_recuperacion_cambia_la_contrasena_revoca_todas_las_sesiones… · F: `access_code_test.dart` · R-UI | Implementado y probado |
| CA-254: un acceso desactivado sigue desactivado | función `canjear_codigo_recuperacion` | B: `test_canje_recuperacion.py`::un_acceso_desactivado_no_se_reactiva…, la_desactivacion_que_toma_el_bloqueo_primero… | Implementado y probado |
| A8: longitud mínima de 10 sin composición; **contraseñas comprometidas con Pwned Passwords local** (fuente elegida el 2026-11-17) | `app/seguridad/contrasenas_comprometidas.py` y `scripts/lista_contrasenas.py` | B: `test_contrasenas_comprometidas.py` (formato oficial por rangos, instalación completa y procedencia, subconjunto rechazado, rechazo en primer acceso y en recuperación sin consumir el código ni dar un oráculo, contraseña no incluida y cuenta 0 aceptadas, sin comunicación externa), con instalaciones SINTÉTICAS completas de 16 rangos, y un rango real de Pwned Passwords comprobado de forma puntual (no automatizada) | **Implementado y probado; efectivo solo con el conjunto (≈ 81 GB) instalado en el despliegue: NO instalado en desarrollo** (ADR-002, M1-T8.6; `docs/operacion/pwned-passwords.md`) |
| D6: retención de 30 días y purga de códigos terminados | `purgar-codigos` (CLI) y migración 0017 | B: `test_purga_de_codigos.py` (límites de 30 días, pendientes vigentes, reloj de PostgreSQL, repetible, sin tocar la auditoría, sin contenido en la salida, privilegios mínimos, migración reversible); `test_db_codigo_unico.py` (disparador de retención) | Implementado y probado |
| D2, D7, D9: función `SECURITY DEFINER` blindada, política antes del código, límites de M1-T7 | migraciones 0015 y 0016 | B: `test_canje_primer_acceso.py`, `test_canje_recuperacion.py` (blindaje, atomicidad, concurrencia, carrera con la desactivación); `test_control_de_intentos*.py` | Implementado y probado |
| CA-05 (credenciales y códigos no aparecen en respuestas, registros ni auditoría) | API, CLI, base y Flutter | B: `test_canje_primer_acceso.py`::ni_las_respuestas_ni_los_registros…; `test_contrasenas_comprometidas.py` (registros y auditoría; **un fallo interno ya no registra el hash de la contraseña ni el HMAC del código**, M1-T8.6) · F: sin almacenamiento persistente (revisión del código, T8.6) | Implementado y probado |

**No demostrado, pendiente o fuera de M1-T8:** la cobertura real de Pwned Passwords con el conjunto completo instalado (no se instaló en desarrollo) y su frecuencia de actualización; la programación periódica de las purgas (no hay planificador, DT-07); la reactivación del acceso (M1-10); un control de dos personas para la verificación de identidad (A5); la comprobación con lectores de pantalla reales; y la evaluación de seguridad del despliegue.

## 6. Qué no demuestra esta matriz

- Que las pantallas se comporten igual en todos los navegadores: el recorrido real fue con Chrome. No hay pruebas automáticas de interfaz en un navegador.
- Rendimiento, volumen ni límites de carga (PA-13).
- Seguridad de un despliegue: ver las limitaciones en el README (sección 2.5).
- Que la supervisión pueda consultar la auditoría ajena: es de M4.
- Que `smartwork_app` se comporte igual que una instalación nueva con datos reales: se comprobó su esquema y migración (solo lectura), no se ejecutaron pruebas destructivas ni escrituras de verificación sobre ella.

## Adenda M4-T6 (2026-11-18): 403 sobre lo visible ajeno y auditoría del supervisor

Este documento es el cierre técnico de M2 y M3 del 2026-11-11 y no se reescribe; M4-T6 cambió a propósito dos comportamientos que aquí constaban como provisionales. Lo que cambia y la evidencia (pruebas en `backend/tests/test_consulta_extensiones_m2_m3.py`, las pruebas antiguas actualizadas que se enumeran y un recorrido HTTP real con uvicorn y PostgreSQL desechable de 13 comprobaciones):

| Cambio | Criterios afectados | Evidencia | Estado |
|---|---|---|---|
| Seis operaciones (M2-04, M2-05, M3-03, M3-04, M3-05, M3-06) responden `OPERACION_NO_PERMITIDA` (403) si el registro ajeno le es visible a quien opera y 404 indistinguible si no | CA-72, CA-183, CA-208 (M2); CA-101, CA-107 (M3-03); CA-127 (M3-04); CA-118 (M3-05); CA-123 (M3-06) | B extensiones_m2_m3::las_seis_escrituras_…_responden_403_y_no_cambian_nada; lo_que_no_es_visible_y_lo_inexistente_responden_el_mismo_404_en_las_seis; las_operaciones_propias_siguen_funcionando… · actualizadas: correccion, marca_error, reactivacion, cierre_reapertura (un supervisor no modifica la jornada pasada de su colaboradora), traslado_e2e | Siguen **Implementado y probado**; el nuevo código de respuesta es 403 si el registro es visible |
| M2-07 (detalle de actividad ajena) conserva el 404 | — (el contrato remite a M4-04) | B extensiones_m2_m3::…el_detalle_ajeno_de_m2_07_conserva_su_404 | Sin cambio |
| M3-07: consulta la propietaria y el supervisor vigente del equipo del registro por su fecha laboral | CA-111 (nuevo), CA-112, CA-113, CA-286 | B auditoria::un_supervisor_del_mismo_equipo_consulta_la_auditoria_de_su_equipo; extensiones_m2_m3::el_supervisor_consulta…; la_paginacion_…; el_supervisor_trasladado_o_desactivado_pierde_la_autorizacion; la_consulta_sql_… | **CA-111: Implementado y probado**; los demás, sin cambio de estado |
| CA-178 y CA-194 (escritura sobre registros de otra persona, también de una persona trasladada) | CA-178, CA-194, CA-131 | B extensiones_m2_m3::las_seis_escrituras… (el supervisor del equipo de T sobre una actividad de una persona ya trasladada a U); M4 no tiene ninguna ruta de escritura (M4-T1) | Con evidencia; la clasificación formal de M1 (CA-178 «parcial») se revisa en la matriz de M4-T9 |

Pruebas antiguas que se **actualizaron a propósito** (fijaban el 404 provisional): `correccion::un_supervisor_del_mismo_equipo_tampoco_corrige`, `marca_error::un_supervisor_del_mismo_equipo_tampoco_marca_ni_revierte`, `reactivacion::un_supervisor_del_mismo_equipo_tampoco_la_reactiva` y `cierre_reapertura::un_supervisor_no_modifica_la_jornada_pasada_de_su_colaboradora` (de 404 a 403: el supervisor ve el registro de su equipo); `auditoria::un_supervisor_del_mismo_equipo_todavia_no_consulta…` (ahora `…consulta_la_auditoria_de_su_equipo`: CA-111); `traslado_e2e::test_ninguna_otra_persona_accede…` (ahora una tabla por persona: 403 al equipo de la fecha, auditoría para su supervisora) y `visibilidad_historica::test_solo_el_modulo_de_m4_usa…` (ahora una lista cerrada de los archivos que usan la política). En ningún caso se debilitó una aserción: se reemplazó el código esperado por el contractual y se comprobó, como antes, que la base no cambia.
