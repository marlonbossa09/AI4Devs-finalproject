import '../../../../core/utils/dates.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../team/data/models/team_models.dart' show sharedActivityFromJson;
import '../../../team/domain/entities/team_entities.dart';
import '../../domain/entities/supervision_entities.dart';

/// Wire formats of M4-03 and M4-04. Parsing is EXPLICIT: each element reads only the fields the contract defines for its
/// `tipo`, so a field the client does not know (or must not show) is never carried into the app. A field the server
/// omitted stays null: the client never fills it in.

ActivityStatus _status(Object? value) => switch (value) {
  'Pendiente' => ActivityStatus.pending,
  'En progreso' => ActivityStatus.inProgress,
  'Bloqueada' => ActivityStatus.blocked,
  'Completada' => ActivityStatus.completed,
  _ => throw FormatException('Unknown activity status: $value'),
};

ActivityStatus? _optionalStatus(Object? value) => value == null ? null : _status(value);

InclusionReason _reason(Object? value) => switch (value) {
  'planificada_en_el_periodo' => InclusionReason.plannedInPeriod,
  'con_avances_en_el_periodo' => InclusionReason.withProgressInPeriod,
  'pendiente_al_corte' => InclusionReason.pendingAtCut,
  _ => throw FormatException('Unknown inclusion reason: $value'),
};

PlanningType _planningType(Object? value) => switch (value) {
  'original' => PlanningType.original,
  'continuacion' => PlanningType.continuation,
  _ => throw FormatException('Unknown planning type: $value'),
};

List<Map<String, dynamic>> _list(Object? value) => (value as List).cast<Map<String, dynamic>>();

MinimalReference _minimalReference(Map<String, dynamic> json) {
  final activity = sharedActivityFromJson(json['actividad'] as Map<String, dynamic>);
  if (!activity.isNeutral) throw const FormatException('A minimal reference must carry a neutral activity');
  final last = json['fecha_ultimo_avance'] as String?;
  return MinimalReference(
    ownerId: json['propietaria_id'] as String,
    activity: activity,
    currentStatus: _status(json['estado_actual']),
    lastProgressDate: last == null ? null : parseDate(last),
  );
}

SupervisionItem supervisionItemFromJson(Map<String, dynamic> json) {
  switch (json['tipo']) {
    case 'actividad':
      return SupervisedActivity(
        ownerId: json['propietaria_id'] as String,
        activity: sharedActivityFromJson(json['actividad'] as Map<String, dynamic>),
        reasons: [for (final r in json['motivo_inclusion'] as List) _reason(r)],
        statusAtCut: _optionalStatus(json['estado_al_corte']),
        currentStatusIfDiffers: _optionalStatus(json['estado_actual_si_difiere']),
      );
    case 'referencia_minima':
      return _minimalReference(json);
    default:
      throw FormatException('Unknown element type: ${json['tipo']}');
  }
}

class SupervisionPageModel {
  const SupervisionPageModel({required this.page});

  factory SupervisionPageModel.fromJson(Map<String, dynamic> json) {
    final period = json['periodo'] as Map<String, dynamic>;
    final totals = json['totales_por_estado'] as Map<String, dynamic>;
    final without = json['sin_estado_al_corte'] as Map<String, dynamic>;
    return SupervisionPageModel(
      page: SupervisionPage(
        from: parseDate(period['desde'] as String),
        to: parseDate(period['hasta'] as String),
        cut: parseDate(json['corte'] as String),
        totals: {for (final status in ActivityStatus.values) status: (totals[_wire(status)] as num?)?.toInt() ?? 0},
        withoutStatus: WithoutStatusCount(
          minimalReferences: (without['referencias_minimas'] as num).toInt(),
          activities: (without['actividades'] as num).toInt(),
        ),
        items: _list(json['elementos']).map(supervisionItemFromJson).toList(),
        next: json['siguiente'] as String?,
      ),
    );
  }

  final SupervisionPage page;

  static String _wire(ActivityStatus status) => switch (status) {
    ActivityStatus.pending => 'Pendiente',
    ActivityStatus.inProgress => 'En progreso',
    ActivityStatus.blocked => 'Bloqueada',
    ActivityStatus.completed => 'Completada',
  };
}

/// M4-04: `tipo` `actividad` (with its authorized progress and plannings) or `referencia_minima`.
ActivityHistory activityHistoryFromJson(Map<String, dynamic> json) {
  switch (json['tipo']) {
    case 'referencia_minima':
      return ActivityHistoryReference(_minimalReference(json));
    case 'actividad':
      final activity = sharedActivityFromJson(json['actividad'] as Map<String, dynamic>);
      return ActivityHistoryDetail(
        activity: activity,
        // The response carries no id per entry: they all belong to this activity
        progress: [
          for (final a in _list(json['avances']))
            PeerProgress(
              activityId: activity.id,
              date: parseDate(a['fecha_laboral'] as String),
              status: _status(a['estado']),
              description: (a['descripcion'] as String?) ?? '',
              blockReason: a['motivo_bloqueo'] as String?,
            ),
        ],
        plannings: [
          for (final p in _list(json['planificaciones']))
            PeerPlanning(
              activityId: activity.id,
              date: parseDate(p['fecha_laboral'] as String),
              type: _planningType(p['tipo']),
              description: (p['descripcion'] as String?) ?? '',
            ),
        ],
        currentStatus: _optionalStatus(json['estado_actual']),
      );
    default:
      throw FormatException('Unknown history type: ${json['tipo']}');
  }
}
