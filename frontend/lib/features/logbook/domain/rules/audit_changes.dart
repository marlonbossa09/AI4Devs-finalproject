import '../../../../core/utils/dates.dart';
import '../entities/audit_entities.dart';

/// How an audit entry is shown: the operation, who did it, and which values changed (CA-106, CA-108). These are
/// presentation rules only: the server decides what an entry contains.

String auditOperationLabel(AuditEntry entry) => switch (entry.operation) {
  AuditOperation.closing => 'Cierre de la jornada',
  AuditOperation.reopening => 'Reapertura de la jornada',
  AuditOperation.correction => 'Corrección',
  AuditOperation.pastDayChange => 'Modificación de una jornada pasada',
  AuditOperation.reactivation => 'Reactivación',
  AuditOperation.errorMark => 'Marca de error',
  AuditOperation.markReversal => 'Reversión de la marca',
  AuditOperation.other => entry.operationName,
};

/// Who did it. The audit of a record shows the owner's own operations, so it is "Tú"; anyone else is never named
/// (no data of other people is shown).
String auditAuthorLabel(AuditEntry entry, String? currentUserId) {
  if (entry.authorId == null) return 'Sin autor';
  return entry.authorId == currentUserId ? 'Tú' : 'Otra persona';
}

/// One changed value: what it was and what it became. A null side means "no value".
class AuditChange {
  const AuditChange({required this.label, this.before, this.after});

  final String label;
  final String? before;
  final String? after;
}

/// Technical identifiers and bookkeeping flags that say nothing to the person who reads the audit.
const _hidden = {
  'actividad_id',
  'bitacora_id',
  'bitacora_existia',
  'bitacora_creada',
  'avance_id',
  'marcada_por',
  'id',
};

bool _isHidden(String path) {
  final last = path.split('.').last;
  return _hidden.contains(last);
}

/// Every leaf of a nested map as `a.b.c -> value`.
Map<String, Object?> _flatten(Map<String, dynamic>? map, [String prefix = '']) {
  final result = <String, Object?>{};
  if (map == null) return result;
  map.forEach((key, value) {
    final path = prefix.isEmpty ? key : '$prefix.$key';
    if (value is Map<String, dynamic> && value.isNotEmpty) {
      result.addAll(_flatten(value, path));
    } else {
      result[path] = value;
    }
  });
  return result;
}

/// The values that CHANGED in the entry, in the order they were recorded. Unchanged values (for example a current
/// status that did not vary) are left out. A value that appears or disappears has a null side.
List<AuditChange> auditChanges(AuditEntry entry) {
  final before = _flatten(entry.previous);
  final after = _flatten(entry.next);
  // A null that becomes a whole record (a mark) is not a value of its own: only the record's fields are shown
  for (final side in [before, after]) {
    final other = identical(side, before) ? after : before;
    side.removeWhere(
      (path, value) => value == null && other.keys.any((key) => key.startsWith('$path.')),
    );
  }
  final paths = <String>[...after.keys, ...before.keys.where((k) => !after.containsKey(k))];
  final changes = <AuditChange>[];
  for (final path in paths) {
    if (_isHidden(path)) continue;
    final b = before[path];
    final a = after[path];
    if (before.containsKey(path) && after.containsKey(path) && _same(b, a)) continue;
    // No value before and none after says nothing: it is not a change
    if (b == null && a == null) continue;
    changes.add(
      AuditChange(
        label: _label(entry.objectType, path),
        before: _show(path, b),
        after: _show(path, a),
      ),
    );
  }
  return changes;
}

bool _same(Object? a, Object? b) => a == b;

const _labels = {
  'estado': 'Estado',
  'descripcion': 'Descripción',
  'motivo_bloqueo': 'Motivo del bloqueo',
  'estado_actual': 'Estado actual de la actividad',
  'resumen': 'Resumen',
  'cerrada_en': 'Momento del cierre',
  'avance.estado': 'Estado del avance',
  'avance.descripcion': 'Descripción del avance',
  'avance.motivo_bloqueo': 'Motivo del bloqueo',
  'avance.es_reactivacion': 'Es una reactivación',
  'actividad.titulo': 'Título de la actividad',
  'actividad.origen': 'Origen de la actividad',
  'actividad.estado_actual': 'Estado de la actividad',
  'planificacion.tipo': 'Tipo de planificación',
  'planificacion.descripcion': 'Descripción de lo planificado',
  'marca_error.motivo': 'Motivo de la marca',
  'marca_error.marcada_en': 'Marcada el',
  'marca_error': 'Marca de error',
  'finalizacion_anterior.fecha_laboral': 'Finalización anterior (fecha laboral)',
};

String _label(String objectType, String path) {
  if (objectType == 'bitacora' && path == 'estado') return 'Estado de la jornada';
  final known = _labels[path];
  if (known != null) return known;
  // Unknown field: its last name, readable
  final last = path.split('.').last.replaceAll('_', ' ');
  return last.isEmpty ? path : '${last[0].toUpperCase()}${last.substring(1)}';
}

const _words = {
  'cerrada': 'Cerrada',
  'abierta': 'Abierta',
  'planificada': 'Planificada',
  'no_planificada': 'No planificada',
  'original': 'Original',
  'continuacion': 'Continuación',
};

final _isoMoment = RegExp(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}');

/// A value as a person reads it; null = no value (the screen shows a dash).
String? _show(String path, Object? value) {
  if (value == null) return null;
  if (value is bool) return value ? 'Sí' : 'No';
  if (value is String) {
    if (_isoMoment.hasMatch(value)) {
      final moment = DateTime.tryParse(value);
      if (moment != null) return formatDateTime(moment);
    }
    return _words[value] ?? value;
  }
  return value.toString();
}
