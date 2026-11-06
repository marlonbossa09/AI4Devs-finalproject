import 'package:json_annotation/json_annotation.dart';

import '../../../../core/utils/dates.dart';
import '../../domain/entities/logbook_entities.dart';

part 'logbook_models.g.dart';

DateType _dateType(String value) => switch (value) {
  'pasada' => DateType.past,
  'actual' => DateType.today,
  'futura' => DateType.future,
  _ => throw FormatException('Unknown date type: $value'),
};

ActivityStatus _status(String value) => switch (value) {
  'Pendiente' => ActivityStatus.pending,
  'En progreso' => ActivityStatus.inProgress,
  'Bloqueada' => ActivityStatus.blocked,
  'Completada' => ActivityStatus.completed,
  _ => throw FormatException('Unknown activity status: $value'),
};

ActivityOrigin _origin(String value) => switch (value) {
  'planificada' => ActivityOrigin.planned,
  'no_planificada' => ActivityOrigin.unplanned,
  _ => throw FormatException('Unknown activity origin: $value'),
};

PlanningType _planningType(String value) => switch (value) {
  'original' => PlanningType.original,
  'continuacion' => PlanningType.continuation,
  _ => throw FormatException('Unknown planning type: $value'),
};

/// Wire formats of the API. The JSON field names are Spanish (the public contract) and are
/// mapped here, so the rest of the app only sees simple English names.
@JsonSerializable(createToJson: false)
class LogbookModel {
  const LogbookModel({
    required this.id,
    required this.userId,
    required this.date,
    required this.dateType,
    required this.status,
    required this.summary,
    required this.createdAt,
    required this.updatedAt,
    this.closedAt,
  });

  factory LogbookModel.fromJson(Map<String, dynamic> json) => _$LogbookModelFromJson(json);

  final String id;
  @JsonKey(name: 'persona_id')
  final String userId;
  @JsonKey(name: 'fecha_laboral')
  final String date;
  @JsonKey(name: 'clase_jornada')
  final String dateType;
  @JsonKey(name: 'estado')
  final String status;
  @JsonKey(name: 'resumen')
  final String summary;
  @JsonKey(name: 'creada_en')
  final DateTime createdAt;
  @JsonKey(name: 'modificada_en')
  final DateTime updatedAt;
  @JsonKey(name: 'cerrada_en')
  final DateTime? closedAt;

  Logbook toEntity() => Logbook(
    id: id,
    userId: userId,
    date: parseDate(date),
    dateType: _dateType(dateType),
    closed: status == 'cerrada',
    summary: summary,
    createdAt: createdAt,
    updatedAt: updatedAt,
    closedAt: closedAt,
  );
}

@JsonSerializable(createToJson: false)
class ActivityModel {
  const ActivityModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.origin,
    required this.status,
    required this.date,
    required this.createdAt,
    this.mark,
  });

  factory ActivityModel.fromJson(Map<String, dynamic> json) => _$ActivityModelFromJson(json);

  final String id;
  @JsonKey(name: 'propietaria_id')
  final String userId;
  @JsonKey(name: 'titulo')
  final String title;
  @JsonKey(name: 'origen')
  final String origin;
  @JsonKey(name: 'estado_actual')
  final String status;
  @JsonKey(name: 'fecha_laboral_origen')
  final String date;
  @JsonKey(name: 'creada_en')
  final DateTime createdAt;
  @JsonKey(name: 'marca_error')
  final Map<String, dynamic>? mark;

  Activity toEntity() => Activity(
    id: id,
    userId: userId,
    title: title,
    origin: _origin(origin),
    status: _status(status),
    date: parseDate(date),
    createdAt: createdAt,
    marked: mark != null,
  );
}

@JsonSerializable(createToJson: false)
class PlanningModel {
  const PlanningModel({
    required this.id,
    required this.activityId,
    required this.date,
    required this.type,
    required this.description,
    required this.createdAt,
  });

  factory PlanningModel.fromJson(Map<String, dynamic> json) => _$PlanningModelFromJson(json);

  final String id;
  @JsonKey(name: 'actividad_id')
  final String activityId;
  @JsonKey(name: 'fecha_laboral')
  final String date;
  @JsonKey(name: 'tipo')
  final String type;
  @JsonKey(name: 'descripcion')
  final String description;
  @JsonKey(name: 'registrada_en')
  final DateTime createdAt;

  Planning toEntity() => Planning(
    id: id,
    activityId: activityId,
    date: parseDate(date),
    type: _planningType(type),
    description: description,
    createdAt: createdAt,
  );
}

/// Response of M2-01a. The `avances` list is not read in this stage (no operation writes
/// progress entries yet).
@JsonSerializable(createToJson: false)
class LogbookDayModel {
  const LogbookDayModel({required this.logbook, required this.plannings, required this.activities});

  factory LogbookDayModel.fromJson(Map<String, dynamic> json) => _$LogbookDayModelFromJson(json);

  @JsonKey(name: 'bitacora')
  final LogbookModel logbook;
  @JsonKey(name: 'planificaciones')
  final List<PlanningModel> plannings;
  @JsonKey(name: 'actividades')
  final List<ActivityModel> activities;

  LogbookDay toEntity() => LogbookDay(
    logbook: logbook.toEntity(),
    plannings: plannings.map((p) => p.toEntity()).toList(),
    activities: activities.map((a) => a.toEntity()).toList(),
  );
}

/// Response of M2-01b.
@JsonSerializable(createToJson: false)
class OpenResultModel {
  const OpenResultModel({required this.created, required this.logbook});

  factory OpenResultModel.fromJson(Map<String, dynamic> json) => _$OpenResultModelFromJson(json);

  @JsonKey(name: 'creada')
  final bool created;
  @JsonKey(name: 'bitacora')
  final LogbookModel logbook;

  OpenResult toEntity() => OpenResult(created: created, logbook: logbook.toEntity());
}

/// Response of M2-03.
@JsonSerializable(createToJson: false)
class PlanResultModel {
  const PlanResultModel({
    required this.activity,
    required this.planning,
    required this.logbookCreated,
  });

  factory PlanResultModel.fromJson(Map<String, dynamic> json) => _$PlanResultModelFromJson(json);

  @JsonKey(name: 'actividad')
  final ActivityModel activity;
  @JsonKey(name: 'planificacion')
  final PlanningModel planning;
  @JsonKey(name: 'bitacora_creada')
  final bool logbookCreated;

  PlanResult toEntity() => PlanResult(
    activity: activity.toEntity(),
    planning: planning.toEntity(),
    logbookCreated: logbookCreated,
  );
}
