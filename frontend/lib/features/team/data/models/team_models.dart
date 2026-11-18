import '../../../../core/utils/dates.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../domain/entities/team_entities.dart';

/// Wire formats of M4-01, M4-02 and M4-05. The JSON names are Spanish (the public contract) and are mapped here.
///
/// Parsing is EXPLICIT on purpose: each model reads only the fields the contract defines for it, so a field the
/// client does not know (or must not show) is never carried into the app, even if a server sent it. A neutral
/// activity is read as neutral: its title, origin and mark are not even looked at.

TeamRole _role(Object? value) => switch (value) {
  'colaborador' => TeamRole.collaborator,
  'supervisor' => TeamRole.supervisor,
  _ => throw FormatException('Unknown team role: $value'),
};

ActivityStatus _status(Object? value) => switch (value) {
  'Pendiente' => ActivityStatus.pending,
  'En progreso' => ActivityStatus.inProgress,
  'Bloqueada' => ActivityStatus.blocked,
  'Completada' => ActivityStatus.completed,
  _ => throw FormatException('Unknown activity status: $value'),
};

ActivityOrigin _origin(Object? value) => switch (value) {
  'planificada' => ActivityOrigin.planned,
  'no_planificada' => ActivityOrigin.unplanned,
  _ => throw FormatException('Unknown activity origin: $value'),
};

PlanningType _planningType(Object? value) => switch (value) {
  'original' => PlanningType.original,
  'continuacion' => PlanningType.continuation,
  _ => throw FormatException('Unknown planning type: $value'),
};

bool _closed(Object? value) => switch (value) {
  'cerrada' => true,
  'abierta' => false,
  _ => throw FormatException('Unknown logbook state: $value'),
};

List<Map<String, dynamic>> _list(Object? value) => (value as List).cast<Map<String, dynamic>>();

class TeamMemberModel {
  const TeamMemberModel({required this.id, required this.name, required this.role});

  factory TeamMemberModel.fromJson(Map<String, dynamic> json) =>
      TeamMemberModel(id: json['persona_id'] as String, name: json['nombre'] as String, role: _role(json['rol']));

  final String id;
  final String name;
  final TeamRole role;

  TeamMember toEntity() => TeamMember(id: id, name: name, role: role);
}

class TeamMemberPageModel {
  const TeamMemberPageModel({required this.items, this.next});

  factory TeamMemberPageModel.fromJson(Map<String, dynamic> json) => TeamMemberPageModel(
    items: _list(json['elementos']).map(TeamMemberModel.fromJson).toList(),
    next: json['siguiente'] as String?,
  );

  final List<TeamMemberModel> items;
  final String? next;

  TeamMemberPage toEntity() => TeamMemberPage(items: [for (final item in items) item.toEntity()], next: next);
}

/// `ActividadVisible`: `forma` tells the two shapes apart (`completa` or `neutral`).
SharedActivity sharedActivityFromJson(Map<String, dynamic> json) {
  final id = json['id'] as String;
  final ownerId = json['propietaria_id'] as String;
  switch (json['forma']) {
    case 'neutral':
      return SharedActivity(id: id, ownerId: ownerId, form: ActivityForm.neutral);
    case 'completa':
      final mark = json['marca_error'];
      final status = json['estado_actual'];
      return SharedActivity(
        id: id,
        ownerId: ownerId,
        form: ActivityForm.full,
        title: json['titulo'] as String,
        origin: _origin(json['origen']),
        status: status == null ? null : _status(status),
        markReason: mark is Map<String, dynamic> ? mark['motivo'] as String? : null,
      );
    default:
      throw FormatException('Unknown activity form: ${json['forma']}');
  }
}

class PeerLogbookModel {
  const PeerLogbookModel({
    required this.ownerId,
    required this.date,
    required this.closed,
    required this.summary,
    required this.plannings,
    required this.progress,
    required this.activities,
  });

  factory PeerLogbookModel.fromJson(Map<String, dynamic> json) {
    final logbook = json['bitacora'] as Map<String, dynamic>;
    return PeerLogbookModel(
      ownerId: logbook['persona_id'] as String,
      date: parseDate(logbook['fecha_laboral'] as String),
      closed: _closed(logbook['estado']),
      summary: logbook['resumen'] as String,
      plannings: [
        for (final p in _list(json['planificaciones']))
          PeerPlanning(
            activityId: p['actividad_id'] as String,
            date: parseDate(p['fecha_laboral'] as String),
            type: _planningType(p['tipo']),
            description: (p['descripcion'] as String?) ?? '',
          ),
      ],
      progress: [
        for (final a in _list(json['avances']))
          PeerProgress(
            activityId: a['actividad_id'] as String,
            date: parseDate(a['fecha_laboral'] as String),
            status: _status(a['estado']),
            description: (a['descripcion'] as String?) ?? '',
            blockReason: a['motivo_bloqueo'] as String?,
          ),
      ],
      activities: _list(json['actividades']).map(sharedActivityFromJson).toList(),
    );
  }

  final String ownerId;
  final DateTime date;
  final bool closed;
  final String summary;
  final List<PeerPlanning> plannings;
  final List<PeerProgress> progress;
  final List<SharedActivity> activities;

  PeerLogbook toEntity() => PeerLogbook(
    ownerId: ownerId,
    date: date,
    closed: closed,
    summary: summary,
    plannings: plannings,
    progress: progress,
    activities: activities,
  );
}

class HistoryPageModel {
  const HistoryPageModel({required this.items, this.next});

  factory HistoryPageModel.fromJson(Map<String, dynamic> json) => HistoryPageModel(
    items: [
      for (final e in _list(json['elementos']))
        HistoryEntry(
          ownerId: e['persona_id'] as String,
          date: parseDate(e['fecha_laboral'] as String),
          closed: _closed(e['estado']),
          summary: e['resumen'] as String,
          activities: _list(e['actividades']).map(sharedActivityFromJson).toList(),
        ),
    ],
    next: json['siguiente'] as String?,
  );

  final List<HistoryEntry> items;
  final String? next;

  HistoryPage toEntity() => HistoryPage(items: items, next: next);
}
