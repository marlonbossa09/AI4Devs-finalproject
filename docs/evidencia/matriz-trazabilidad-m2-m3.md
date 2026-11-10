# SMARTWORK — Matriz de trazabilidad y cobertura: M2 y M3-01/M3-02

| Campo | Contenido |
|---|---|
| **Naturaleza** | Evidencia de la implementación. No define requisitos: los requisitos viven en `docs/` (alcance, PRD, historias y contratos) |
| **Fecha** | 2026-11-09 |
| **Alcance** | Contratos M2-01a a M2-08, M3-01 y M3-02, y (T11 a T13) M3-03, M3-05, M3-06 y M3-07, tal como están implementados en la fecha indicada. M3-04 está implementado y verificado, pero su cobertura por criterio se incorpora a esta matriz en el cierre de M3 |
| **Fuente de los criterios** | `docs/api/m2-bitacoras.md` y `docs/api/m3-seguimiento-auditoria.md` («Criterios vinculados») y las historias de `docs/backlog/` |
| **Fuera de alcance** | M4 y M5 (y, de momento, la fila por criterio de M3-04): sus criterios no se evalúan aquí, salvo los que los contratos M2/M3-01/02 citan |

## 1. Cómo leerla

Cada fila es **contrato → criterio → componente → prueba → estado**. El componente (endpoint y pantalla) se indica una vez por contrato.

**Tipos de evidencia**

| Sigla | Qué es | Es flujo real |
|---|---|---|
| **B** | Prueba de backend (`pytest`): HTTP contra la aplicación con **PostgreSQL real** (`smartwork_test`), sin dobles de datos. Se cita `archivo::prueba`, con el nombre abreviado: el prefijo identifica la prueba | Sí (API y base) |
| **F** | Prueba de Flutter (`flutter test`) con un repositorio **en memoria** que imita al servidor. Verifica la pantalla y sus reglas, no la integración | **No**: es simulada |
| **R-INT** | Verificación integral: FastAPI y PostgreSQL reales en una instalación desechable, incluido el reinicio del servidor | Sí |
| **R-UI** | Recorrido en Chrome real (escritorio y móvil) contra FastAPI y PostgreSQL, con capturas revisadas, durante el desarrollo y la verificación | Sí |

**Estados**

- **Implementado y probado:** hay una prueba de backend con PostgreSQL real (B) que cubre el criterio y, si el criterio tiene una parte de interfaz, un recorrido real (R-UI). Una prueba solo de tipo F **nunca** basta.
- **Parcial:** la regla existe y está probada, pero una parte del criterio depende de algo que no existe todavía o solo se probó con datos preparados a mano (por ejemplo, una marca de error escrita por SQL).
- **No implementado:** pertenece a una operación que esta entrega no incluye.
- **Bloqueado por otro módulo:** exige una operación de otro módulo (reactivación, traslado de equipo).
- **Pendiente de decisión:** el contrato o los criterios no fijan el comportamiento y hay que decidirlo.

## 2. Resumen

113 criterios distintos, 142 filas (un criterio aparece en cada contrato que lo cita).

| Estado | Filas |
|---|---|
| Implementado y probado | 124 |
| Parcial | 9 |
| No implementado | 4 |
| Bloqueado por otro módulo | 5 |
| Pendiente de decisión | 0 |

| Contrato | Criterios | Implementado y probado | Parcial | Bloqueado |
|---|---|---|---|---|
| M2-01a — Consultar mi bitácora de una fecha | 7 | 6 | 1 | 0 |
| M2-01b — Abrir mi bitácora de una fecha | 11 | 11 | 0 | 0 |
| M2-02 — Guardar el resumen libre | 9 | 9 | 0 | 0 |
| M2-03 — Planificar una actividad nueva | 9 | 9 | 0 | 0 |
| M2-04 — Planificar la continuación de una actividad | 10 | 9 | 0 | 1 |
| M2-05 — Registrar un avance | 35 | 32 | 2 | 1 |
| M2-06 — Registrar una actividad no planificada | 9 | 9 | 0 | 0 |
| M2-07 — Consultar una actividad propia | 25 | 18 | 4 | 3 |
| M2-08 — Listar mis actividades | 4 | 3 | 1 | 0 |
| M3-01 — Cerrar mi jornada | 13 | 12 | 1 | 0 |
| M3-02 — Reabrir mi bitácora cerrada | 6 | 6 | 0 | 0 |

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
| CA-210 | Una reactivada sí se continúa | — | Bloqueado por otro módulo | Depende de M3-04 (reactivación), no implementada. Hoy una Completada siempre se rechaza. |

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
| CA-207 | Entre una finalización y su reactivación no se admite | B secuencia::no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion | Parcial | Regla de dominio probada con una reactivación representada en los datos; no existe el flujo real de reactivar (M3-04). |
| CA-208 | No es posible sobre una Completada ajena | B avances::un_avance_retroactivo_sobre_una_actividad_completada_ajena_tampoco_es_posible | Implementado y probado |  |
| CA-213 | Registrar en el equipo nuevo no crea otra actividad | — | Bloqueado por otro módulo | Requiere el traslado de equipo de M1 (no implementado). La propietaria es una persona, no un equipo (modelo), y ningún avance consulta el equipo. |
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
| CA-191 | Una reactivada sigue siendo la misma actividad | — | Bloqueado por otro módulo | Requiere M3-04. Toda actividad conserva hoy su identidad, planificación y avances (CA-265, CA-39). |
| CA-265 | El título es el mismo en todas las jornadas | B actividades::la_secuencia_de_tres_jornadas_muestra_tres_avances_y_una_sola_actividad (título inmutable por disparador) | Implementado y probado |  |
| CA-212 | Una actividad sigue siendo de su propietaria al cambiar de equipo | — | Bloqueado por otro módulo | Requiere el cambio de pertenencia de M1. El modelo no liga la actividad al equipo. |
| CA-214 | El historial muestra los avances de ambos equipos | — | Bloqueado por otro módulo | Requiere el cambio de pertenencia de M1; no hay prueba con un traslado real. |

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

### M3-05 — Marcar una actividad como registrada por error

**Componente:** `POST /mi/actividades/{id}/marca-error` · acción «Marcar como registrada por error» del detalle de la actividad (`ActivityMarkActions`, diálogo con motivo)

| Criterio | Qué exige | Prueba | Estado | Nota |
|---|---|---|---|---|
| CA-115 | Sin avances posteriores, con motivo, queda marcada | B marca_error::marca_una_actividad_sin_avances_con_motivo; los_avances_de_la_propia_jornada_de_origen_no_lo_impiden; el_origen_es_la_fecha_de_la_bitacora_de_origen_y_no_creada_en · R-INT · R-UI | Implementado y probado | El origen es la fecha de la bitácora de origen (PA-28). |
| CA-116 | Sin motivo no se permite | B marca_error::sin_motivo_no_se_permite_y_no_cambia_nada · F mark_form (motivo en blanco) · R-UI | Implementado y probado |  |
| CA-117 | Con avances en jornadas posteriores no se permite | B marca_error::con_avances_en_jornadas_posteriores_a_su_origen_no_procede; test_db_marca_error (disparador) · F mark_rules · R-INT · R-UI | Implementado y probado | La interfaz no ofrece la acción; el servidor y la base la rechazan igualmente. |
| CA-118 | La de otra persona no se marca | B marca_error::la_actividad_de_otra_persona_no_se_marca_ni_se_revierte; un_supervisor_del_mismo_equipo… · R-INT | Implementado y probado | 404 indistinguible de una inexistente (T-01). |
| CA-119, CA-120, CA-121 | Fuera de vistas y recuentos; consultable; no se borra | Ver M2-07 y M2-08 | Ver arriba | CA-120 sigue parcial por M3-07. |
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
| CA-112 | Un compañero que no es propietario ni supervisor autorizado no puede | B auditoria::la_auditoria_de_un_registro_ajeno_y_de_uno_inexistente_es_indistinguible; una_persona_solo_ve_sus_propias_entradas | Implementado y probado | Hoy solo consulta la propietaria. |
| CA-113 | El supervisor de otro equipo no puede | B auditoria::un_supervisor_del_mismo_equipo_todavia_no_consulta_la_auditoria_ajena | Implementado y probado | Ningún supervisor consulta aún (M4). |
| CA-286 | La auditoría de un registro inexistente y la de uno ajeno son indistinguibles | B auditoria::la_auditoria_de_un_registro_ajeno_y_de_uno_inexistente…; un_tipo_que_no_corresponde_al_registro…; la_autorizacion_se_aplica_antes_de_leer_las_entradas · R-INT | Implementado y probado | Mismo estado y mismo cuerpo; no se revela si existe. |
| CA-285 | Las entradas de la provisión no aparecen | B auditoria::las_entradas_de_provision_administrativa_no_aparecen | Implementado y probado | D-11. |
| CA-111 | El supervisor autorizado del equipo ve las entradas | — | Bloqueado por otro módulo | Requiere M4: visibilidad histórica y acceso del supervisor (RA-10). |
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
| 2 | **403 frente a 404 según visibilidad** | Todo recurso que no es propio responde 404 `RECURSO_NO_DISPONIBLE`, con el mismo cuerpo que uno inexistente (T-01). `OPERACION_NO_PERMITIDA` (403) no se emite porque aún no hay recursos ajenos visibles | **Provisional, depende de M4**; documentado en `convenciones.md` 3.1 |
| 3 | **CA-62** | La fecha de modificación existe en la bitácora y en cada avance (columna `modificado_en`, migración 0008) | **Implementado** con M3-03 |
| 4 | **CA-210** | Una actividad Completada siempre se rechaza al planificar su continuación | **Bloqueado por M3-04** |
| 5 | **CA-212, CA-213 y CA-214** | Sin prueba con un traslado real. La actividad pertenece a una persona, no a un equipo | **Bloqueado por M1** (cambio de pertenencia) |
| 6 | **Fechas laborales anteriores al origen de la actividad** | Se acepta un avance con una fecha cubierta y no futura aunque sea anterior a la jornada de origen de la actividad. No se valida contra `creada_en`, que es una marca técnica de registro y no el inicio laboral | **Provisional** (2026-11-09, PA-28): vinculado a definir el origen laboral de las actividades en M3. No se cambia el código |
| 7 | **Paginación y formato de respuestas** | El listado devuelve `{"elementos": [...], "siguiente": cursor o null}` con `limite` y `continuar_desde` configurables (convenciones 6.1). Las escrituras devuelven sobres con nombre (`{"bitacora"}`, `{"actividad", "planificacion", "bitacora_creada"}`, `{"avance", "actividad", "bitacora_creada"}`) | **Aprobado** el envoltorio del listado (2026-11-09) y `{"bitacora": …}` y `bitacora_creada`. M2-08 y convenciones 6.1 lo reflejan |
| 8 | **Resumen omitido o nulo** | Equivale a un resumen vacío y se acepta al guardar; solo impide cerrar (D-03) | **Decidido y mantenido**. Documentado en M2-02 |
| 9 | **Varias continuaciones en la misma fecha** | Se registran todas si proceden de operaciones distintas (distinta clave); el mismo reintento no duplica | **Aprobado**. Documentado en M2-04 |
| 10 | **`modificada_en` al cerrar y reabrir** | No cambia: es la fecha de modificación del contenido | **Aprobado**. Documentado en M3-01 |
| 11 | **Marca de error (M3-05 y M3-06)** | Implementadas (T11). Las pruebas anteriores que preparaban la marca por SQL se adaptaron a estados alcanzables: una actividad con avances posteriores a su origen ya no puede marcarse ni siquiera por SQL | **CA-119, CA-121 y CA-283 implementados**; CA-120 sigue parcial hasta M3-07 |
| 12 | **Alcance de la comprobación de cierre de M3-05** | El contrato la describe sobre la jornada de origen. Como PA-28 admite un avance anterior al origen (que cuenta la actividad como continuada en esa jornada anterior), la comprobación se aplica a **toda jornada cerrada en la que la actividad cuenta** | **Aprobado** (2026-11-09): la comprobación abarca todas las jornadas cerradas cuyas condiciones de cierre dependan de la actividad |
| 13 | **Respuesta de M3-05 y M3-06** | `{"actividad": …}`, el sobre con nombre que usan las demás respuestas con una actividad; el contrato dice «la Actividad» | **Aprobado** (2026-11-09), con el esquema completo de la entidad |
| 14 | **Interpretaciones menores de M3-03** | Un `motivo_bloqueo` enviado para un estado distinto de Bloqueada es `SOLICITUD_INVALIDA` (como en M2-05); corregir una reactivación a Completada se rechaza con `SECUENCIA_INVALIDA`; una violación se identifica por el avance y el motivo para compararlas antes y después (PA-29) | **Aprobado** (2026-11-09): identidad estable = avance afectado y tipo de violación; una violación nueva o agravada se rechaza aunque existan otras históricas toleradas |
| 15 | **Corrección y modificación de jornada pasada** | Corregir un avance de una jornada pasada deja UNA sola entrada `correccion` (no una de corrección y otra de modificación de jornada pasada), como indica IR-35 | **Según el contrato** |

## 5. Criterios que dependen de otros módulos (siguen pendientes)

La cobertura propia de M2 y del cierre y la reapertura es la de las secciones anteriores. Esto es lo que **no** se puede dar por cumplido hasta que exista el módulo indicado:

| Módulo | Criterios | Qué falta |
|---|---|---|
| **M1** | CA-212, CA-213, CA-214 | El cambio de pertenencia (traslado de equipo) para probar con un caso real que la actividad sigue siendo de su propietaria y conserva su historial |
| **M3** | CA-210, CA-191 | Reactivación de una actividad Completada (M3-04) |
| **M3** | CA-111 | La consulta de la auditoría por el supervisor autorizado (M3-07, CA-111) y la autorización histórica por equipo (RA-10) |
| **M3** | CA-207 | Reactivación real (M3-04): hoy se prueba la regla de dominio con una reactivación representada en los datos |
| **M3** | PA-28 | Origen laboral de la actividad (hoy: fecha de la bitácora de origen); restricción de avances anteriores, provisional |
| **M4** | Respuesta 403 frente a 404 | Qué registros ajenos son visibles. Hasta entonces todo recurso ajeno responde 404 |

## 6. Qué no demuestra esta matriz

- Que las pantallas se comporten igual en todos los navegadores: el recorrido real fue con Chrome. No hay pruebas automáticas de interfaz en un navegador.
- Rendimiento, volumen ni límites de carga (PA-13).
- Seguridad de un despliegue: ver las limitaciones en el README (sección 2.5).
