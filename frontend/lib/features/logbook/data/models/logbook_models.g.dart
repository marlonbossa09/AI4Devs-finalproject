// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'logbook_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LogbookModel _$LogbookModelFromJson(Map<String, dynamic> json) => LogbookModel(
  id: json['id'] as String,
  userId: json['persona_id'] as String,
  date: json['fecha_laboral'] as String,
  dateType: json['clase_jornada'] as String,
  status: json['estado'] as String,
  summary: json['resumen'] as String,
  createdAt: DateTime.parse(json['creada_en'] as String),
  updatedAt: DateTime.parse(json['modificada_en'] as String),
  closedAt: json['cerrada_en'] == null
      ? null
      : DateTime.parse(json['cerrada_en'] as String),
);

ActivityModel _$ActivityModelFromJson(Map<String, dynamic> json) =>
    ActivityModel(
      id: json['id'] as String,
      userId: json['propietaria_id'] as String,
      title: json['titulo'] as String,
      origin: json['origen'] as String,
      status: json['estado_actual'] as String,
      date: json['fecha_laboral_origen'] as String,
      createdAt: DateTime.parse(json['creada_en'] as String),
      mark: json['marca_error'] as Map<String, dynamic>?,
    );

PlanningModel _$PlanningModelFromJson(Map<String, dynamic> json) =>
    PlanningModel(
      id: json['id'] as String,
      activityId: json['actividad_id'] as String,
      date: json['fecha_laboral'] as String,
      type: json['tipo'] as String,
      description: json['descripcion'] as String,
      createdAt: DateTime.parse(json['registrada_en'] as String),
    );

ProgressModel _$ProgressModelFromJson(Map<String, dynamic> json) =>
    ProgressModel(
      id: json['id'] as String,
      activityId: json['actividad_id'] as String,
      date: json['fecha_laboral'] as String,
      status: json['estado'] as String,
      description: json['descripcion'] as String,
      createdAt: DateTime.parse(json['registrado_en'] as String),
      blockReason: json['motivo_bloqueo'] as String?,
      isReactivation: json['es_reactivacion'] as bool? ?? false,
      modifiedAt: json['modificado_en'] == null
          ? null
          : DateTime.parse(json['modificado_en'] as String),
    );

CorrectionResultModel _$CorrectionResultModelFromJson(
  Map<String, dynamic> json,
) => CorrectionResultModel(
  progress: ProgressModel.fromJson(json['avance'] as Map<String, dynamic>),
  activity: ActivityModel.fromJson(json['actividad'] as Map<String, dynamic>),
  currentStatusChanged: json['estado_actual_cambio'] as bool,
);

LogbookDayModel _$LogbookDayModelFromJson(Map<String, dynamic> json) =>
    LogbookDayModel(
      logbook: LogbookModel.fromJson(json['bitacora'] as Map<String, dynamic>),
      plannings: (json['planificaciones'] as List<dynamic>)
          .map((e) => PlanningModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      activities: (json['actividades'] as List<dynamic>)
          .map((e) => ActivityModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      progress:
          (json['avances'] as List<dynamic>?)
              ?.map((e) => ProgressModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );

OpenResultModel _$OpenResultModelFromJson(Map<String, dynamic> json) =>
    OpenResultModel(
      created: json['creada'] as bool,
      logbook: LogbookModel.fromJson(json['bitacora'] as Map<String, dynamic>),
    );

PlanResultModel _$PlanResultModelFromJson(Map<String, dynamic> json) =>
    PlanResultModel(
      activity: ActivityModel.fromJson(
        json['actividad'] as Map<String, dynamic>,
      ),
      planning: PlanningModel.fromJson(
        json['planificacion'] as Map<String, dynamic>,
      ),
      logbookCreated: json['bitacora_creada'] as bool,
    );

LogbookResultModel _$LogbookResultModelFromJson(Map<String, dynamic> json) =>
    LogbookResultModel(
      logbook: LogbookModel.fromJson(json['bitacora'] as Map<String, dynamic>),
    );

ContinuationResultModel _$ContinuationResultModelFromJson(
  Map<String, dynamic> json,
) => ContinuationResultModel(
  planning: PlanningModel.fromJson(
    json['planificacion'] as Map<String, dynamic>,
  ),
  activity: ActivityModel.fromJson(json['actividad'] as Map<String, dynamic>),
  logbookCreated: json['bitacora_creada'] as bool,
);

ProgressResultModel _$ProgressResultModelFromJson(Map<String, dynamic> json) =>
    ProgressResultModel(
      progress: ProgressModel.fromJson(json['avance'] as Map<String, dynamic>),
      activity: ActivityModel.fromJson(
        json['actividad'] as Map<String, dynamic>,
      ),
      logbookCreated: json['bitacora_creada'] as bool,
    );

MarkResultModel _$MarkResultModelFromJson(Map<String, dynamic> json) =>
    MarkResultModel(
      activity: ActivityModel.fromJson(
        json['actividad'] as Map<String, dynamic>,
      ),
    );

ActivitySummaryModel _$ActivitySummaryModelFromJson(
  Map<String, dynamic> json,
) => ActivitySummaryModel(
  id: json['id'] as String,
  title: json['titulo'] as String,
  origin: json['origen'] as String,
  status: json['estado_actual'] as String,
);

ActivityListModel _$ActivityListModelFromJson(Map<String, dynamic> json) =>
    ActivityListModel(
      items: (json['elementos'] as List<dynamic>)
          .map((e) => ActivitySummaryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      next: json['siguiente'] as String?,
    );

ActivityDetailModel _$ActivityDetailModelFromJson(
  Map<String, dynamic> json,
) => ActivityDetailModel(
  activity: ActivityModel.fromJson(json['actividad'] as Map<String, dynamic>),
  progress: (json['avances'] as List<dynamic>)
      .map((e) => ProgressModel.fromJson(e as Map<String, dynamic>))
      .toList(),
  plannedContinuations: (json['continuaciones_planificadas'] as List<dynamic>)
      .map((e) => PlanningModel.fromJson(e as Map<String, dynamic>))
      .toList(),
  status: json['estado_actual'] as String,
  originalPlanning: json['planificacion_original'] == null
      ? null
      : PlanningModel.fromJson(
          json['planificacion_original'] as Map<String, dynamic>,
        ),
);

SummaryResultModel _$SummaryResultModelFromJson(Map<String, dynamic> json) =>
    SummaryResultModel(
      logbook: LogbookModel.fromJson(json['bitacora'] as Map<String, dynamic>),
      logbookCreated: json['bitacora_creada'] as bool,
    );

AuditEntryModel _$AuditEntryModelFromJson(Map<String, dynamic> json) =>
    AuditEntryModel(
      id: json['id'] as String,
      moment: DateTime.parse(json['momento'] as String),
      operation: json['operacion'] as String,
      objectType: json['tipo_objeto'] as String,
      objectId: json['objeto_id'] as String,
      authorId: json['autor_persona_id'] as String?,
      workDate: json['fecha_laboral_registro'] as String?,
      reason: json['motivo'] as String?,
      previous: json['valor_anterior'] as Map<String, dynamic>?,
      next: json['valor_nuevo'] as Map<String, dynamic>?,
    );

AuditPageModel _$AuditPageModelFromJson(Map<String, dynamic> json) =>
    AuditPageModel(
      items: (json['elementos'] as List<dynamic>)
          .map((e) => AuditEntryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      next: json['siguiente'] as String?,
    );
