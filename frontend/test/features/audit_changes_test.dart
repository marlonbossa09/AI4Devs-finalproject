import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/audit_changes.dart';

AuditEntry _entry({
  String operation = 'correccion',
  AuditOperation kind = AuditOperation.correction,
  String type = 'avance',
  String? author = 'p1',
  Map<String, dynamic>? previous,
  Map<String, dynamic>? next,
  String? reason,
}) => AuditEntry(
  id: 'e1',
  moment: DateTime.utc(2026, 11, 6, 15, 30),
  operationName: operation,
  operation: kind,
  objectType: type,
  objectId: 'o1',
  authorId: author,
  workDate: DateTime.utc(2026, 11, 5),
  reason: reason,
  previous: previous,
  next: next,
);

void main() {
  group('the operation', () {
    test('every known operation has its own name in Spanish', () {
      final labels = {
        AuditOperation.closing: 'Cierre de la jornada',
        AuditOperation.reopening: 'Reapertura de la jornada',
        AuditOperation.correction: 'Corrección',
        AuditOperation.pastDayChange: 'Modificación de una jornada pasada',
        AuditOperation.reactivation: 'Reactivación',
        AuditOperation.errorMark: 'Marca de error',
        AuditOperation.markReversal: 'Reversión de la marca',
      };
      for (final entry in labels.entries) {
        expect(auditOperationLabel(_entry(kind: entry.key)), entry.value, reason: entry.key.name);
      }
    });

    test('an operation this version does not know is still shown, with its own name', () {
      expect(auditOperationLabel(_entry(operation: 'operacion_nueva', kind: AuditOperation.other)), 'operacion_nueva');
    });
  });

  group('the author', () {
    test('the signed-in user is "Tú"; anyone else is never named', () {
      expect(auditAuthorLabel(_entry(author: 'p1'), 'p1'), 'Tú');
      expect(auditAuthorLabel(_entry(author: 'p2'), 'p1'), 'Otra persona');
      expect(auditAuthorLabel(_entry(author: null), 'p1'), 'Sin autor');
    });
  });

  group('the changes', () {
    test('a correction shows what each field was and what it became', () {
      final changes = auditChanges(
        _entry(
          previous: {
            'actividad_id': 'a1',
            'avance': {'estado': 'En progreso', 'descripcion': 'Texto', 'motivo_bloqueo': null},
          },
          next: {
            'actividad_id': 'a1',
            'bitacora_id': 'b1',
            'avance': {'estado': 'Bloqueada', 'descripcion': 'Otro texto', 'motivo_bloqueo': 'Sin acceso'},
          },
        ),
      );
      expect(changes.map((c) => (c.label, c.before, c.after)), [
        ('Estado del avance', 'En progreso', 'Bloqueada'),
        ('Descripción del avance', 'Texto', 'Otro texto'),
        ('Motivo del bloqueo', null, 'Sin acceso'), // a missing value is null, shown as a dash
      ]);
    });

    test('technical identifiers never reach the screen', () {
      final changes = auditChanges(
        _entry(
          previous: {'actividad_id': 'a1', 'bitacora_existia': true},
          next: {'actividad_id': 'a1', 'bitacora_id': 'b1', 'bitacora_creada': false, 'marcada_por': 'p1', 'avance_id': 'x'},
        ),
      );
      expect(changes, isEmpty);
    });

    test('an identifier that appears on only one side is still hidden', () {
      final changes = auditChanges(
        _entry(previous: {}, next: {'actividad_id': 'ACTIVIDAD-XYZ', 'bitacora_id': 'BITACORA-XYZ', 'avance_id': 'AVANCE-XYZ', 'id': 'ID-XYZ'}),
      );
      expect(changes, isEmpty);
    });

    test('a value that did not change is left out (the current status of an activity that stayed the same)', () {
      final changes = auditChanges(
        _entry(
          previous: {'avance': {'descripcion': 'Texto'}, 'estado_actual': 'Completada'},
          next: {'avance': {'descripcion': 'Otro'}, 'estado_actual': 'Completada'},
        ),
      );
      expect(changes.map((c) => c.label), ['Descripción del avance']);
    });

    test('the current status before and after appears when it varied', () {
      final changes = auditChanges(
        _entry(
          previous: {'avance': {'estado': 'Completada'}, 'estado_actual': 'Completada'},
          next: {'avance': {'estado': 'En progreso'}, 'estado_actual': 'En progreso'},
        ),
      );
      expect(changes.map((c) => (c.label, c.before, c.after)), [
        ('Estado del avance', 'Completada', 'En progreso'),
        ('Estado actual de la actividad', 'Completada', 'En progreso'),
      ]);
    });

    test('a mark: nothing before, the reason and the moment after; the reversal goes the other way', () {
      final mark = auditChanges(
        _entry(
          type: 'actividad',
          kind: AuditOperation.errorMark,
          previous: {'marca_error': null, 'estado_actual': 'Pendiente'},
          next: {
            'marca_error': {'motivo': 'Duplicada', 'marcada_en': '2026-11-06T15:30:00Z', 'marcada_por': 'p1'},
            'estado_actual': 'Pendiente',
          },
        ),
      );
      expect(mark.map((c) => c.label), ['Motivo de la marca', 'Marcada el']);
      expect(mark[0].before, isNull);
      expect(mark[0].after, 'Duplicada');
      expect(mark[1].after, formatDateTime(DateTime.utc(2026, 11, 6, 15, 30)));

      final reversal = auditChanges(
        _entry(
          type: 'actividad',
          kind: AuditOperation.markReversal,
          previous: {'marca_error': {'motivo': 'Duplicada', 'marcada_en': '2026-11-06T15:30:00Z', 'marcada_por': 'p1'}},
          next: {'marca_error': null},
        ),
      );
      expect(reversal.map((c) => (c.label, c.before, c.after)), [
        ('Motivo de la marca', 'Duplicada', null),
        ('Marcada el', formatDateTime(DateTime.utc(2026, 11, 6, 15, 30)), null),
      ]);
    });

    test('a closing and a reopening of a day show its state and the moment of the closing', () {
      final closing = auditChanges(
        _entry(
          type: 'bitacora',
          kind: AuditOperation.closing,
          previous: {'estado': 'abierta', 'cerrada_en': null},
          next: {'estado': 'cerrada', 'cerrada_en': '2026-11-06T18:00:00Z'},
        ),
      );
      expect(closing.map((c) => (c.label, c.before, c.after)), [
        ('Estado de la jornada', 'Abierta', 'Cerrada'),
        ('Momento del cierre', null, formatDateTime(DateTime.utc(2026, 11, 6, 18))),
      ]);
      final reopening = auditChanges(
        _entry(
          type: 'bitacora',
          kind: AuditOperation.reopening,
          previous: {'estado': 'cerrada', 'cerrada_en': '2026-11-06T18:00:00Z'},
          next: {'estado': 'abierta', 'cerrada_en': null},
        ),
      );
      expect(reopening.map((c) => (c.before, c.after)), [
        ('Cerrada', 'Abierta'),
        (formatDateTime(DateTime.utc(2026, 11, 6, 18)), null),
      ]);
    });

    test('the correction of a summary shows the old and the new text', () {
      final changes = auditChanges(
        _entry(type: 'bitacora', previous: {'resumen': 'Primero', 'bitacora_existia': true}, next: {'resumen': 'Segundo', 'bitacora_id': 'b'}),
      );
      expect(changes.map((c) => (c.label, c.before, c.after)), [('Resumen', 'Primero', 'Segundo')]);
    });

    test('the creation of a record in a past day lists what was created', () {
      final changes = auditChanges(
        _entry(
          type: 'actividad',
          kind: AuditOperation.pastDayChange,
          previous: {'bitacora_existia': false},
          next: {
            'bitacora_id': 'b',
            'bitacora_creada': true,
            'actividad': {'id': 'a', 'titulo': 'Preparar informe', 'origen': 'planificada', 'estado_actual': 'Pendiente'},
            'planificacion': {'id': 'p', 'tipo': 'original', 'descripcion': 'Revisar cifras'},
          },
        ),
      );
      expect(changes.map((c) => (c.label, c.after)), [
        ('Título de la actividad', 'Preparar informe'),
        ('Origen de la actividad', 'Planificada'),
        ('Estado de la actividad', 'Pendiente'),
        ('Tipo de planificación', 'Original'),
        ('Descripción de lo planificado', 'Revisar cifras'),
      ]);
      expect(changes.every((c) => c.before == null), isTrue);
    });

    test('a reactivation is shown as such, and the flag as Sí', () {
      final changes = auditChanges(
        _entry(
          kind: AuditOperation.reactivation,
          previous: {'actividad_id': 'a', 'estado_actual': 'Completada'},
          next: {
            'actividad_id': 'a',
            'estado_actual': 'En progreso',
            'finalizacion_anterior': {'avance_id': 'x', 'fecha_laboral': '2026-11-04'},
            'avance': {'id': 'v', 'estado': 'En progreso', 'descripcion': 'Retomo', 'motivo_bloqueo': null, 'es_reactivacion': true},
          },
        ),
      );
      final byLabel = {for (final c in changes) c.label: c};
      expect(byLabel['Es una reactivación']!.after, 'Sí');
      expect(byLabel['Estado actual de la actividad']!.before, 'Completada');
      expect(byLabel['Finalización anterior (fecha laboral)']!.after, '2026-11-04');
      expect(byLabel.containsKey('Id'), isFalse);
    });

    test('an unknown field is still shown, readable', () {
      final changes = auditChanges(_entry(previous: {'color_favorito': 'azul'}, next: {'color_favorito': 'verde'}));
      expect(changes.single.label, 'Color favorito');
      expect((changes.single.before, changes.single.after), ('azul', 'verde'));
    });

    test('a field with no value before and none after is not shown as a change', () {
      final changes = auditChanges(
        _entry(
          previous: {'avance': {'descripcion': 'a'}},
          next: {'avance': {'descripcion': 'b', 'motivo_bloqueo': null}},
        ),
      );
      expect(changes.map((c) => c.label), ['Descripción del avance']);
    });

    test('an entry with no values at all has no changes', () {
      expect(auditChanges(_entry()), isEmpty);
    });
  });
}
