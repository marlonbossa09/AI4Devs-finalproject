import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/reactivation_rules.dart';

final _today = DateTime.utc(2026, 11, 6);
final _completedOn = DateTime.utc(2026, 11, 4);

ReactivationErrors _validate({
  DateTime? date,
  DateTime? completedOn,
  ActivityStatus? status = ActivityStatus.inProgress,
  String description = 'Retomo la tarea',
  String blockReason = '',
}) => validateReactivation(
  date: date ?? _today,
  today: _today,
  completedOn: completedOn ?? _completedOn,
  status: status,
  description: description,
  blockReason: blockReason,
);

void main() {
  group('canReactivate (M3-04)', () {
    test('only a Completada activity that is not marked as an error can be reactivated', () {
      expect(canReactivate(status: ActivityStatus.completed, marked: false), isTrue);
      for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]) {
        expect(canReactivate(status: status, marked: false), isFalse, reason: status.name);
      }
    });

    test('a marked activity never can, whatever its status', () {
      for (final status in ActivityStatus.values) {
        expect(canReactivate(status: status, marked: true), isFalse, reason: status.name);
      }
    });
  });

  group('the states a reactivation can leave the activity in', () {
    test('are Pendiente, En progreso and Bloqueada, never Completada', () {
      expect(reactivationStatuses, [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]);
      expect(reactivationStatuses, isNot(contains(ActivityStatus.completed)));
    });
  });

  group('validateReactivation', () {
    test('a complete, valid reactivation has no errors', () {
      expect(_validate().isEmpty, isTrue);
    });

    test('the same date as the completion is valid (CA-187)', () {
      expect(_validate(date: _completedOn).date, isNull);
    });

    test('a later date is valid, up to today (CA-189)', () {
      expect(_validate(date: DateTime.utc(2026, 11, 5)).date, isNull);
      expect(_validate(date: _today).date, isNull);
    });

    test('a date before the completion is rejected (CA-188)', () {
      expect(_validate(date: DateTime.utc(2026, 11, 3)).date, 'La fecha no puede ser anterior a la de la finalización.');
    });

    test('a future date is rejected, not as "before the completion"', () {
      expect(
        _validate(date: DateTime.utc(2026, 11, 7)).date,
        'La fecha no puede ser futura: reactivar es registrar trabajo ya realizado.',
      );
    });

    test('without a known completion only the future is rejected', () {
      final errors = validateReactivation(
        date: DateTime.utc(2000, 1, 1),
        today: _today,
        completedOn: null,
        status: ActivityStatus.pending,
        description: 'x',
        blockReason: '',
      );
      expect(errors.date, isNull);
    });

    test('a status must be chosen, and Completada is not one of the options', () {
      expect(_validate(status: null).status, 'Elige uno de los tres estados.');
      expect(_validate(status: ActivityStatus.completed).status, 'Elige uno de los tres estados.');
      for (final status in reactivationStatuses) {
        expect(_validate(status: status, blockReason: 'x').status, isNull, reason: status.name);
      }
    });

    test('the description is required: empty and only spaces are rejected (CA-270)', () {
      for (final text in ['', '   ', '\n\t ']) {
        expect(_validate(description: text).description, 'Describe cómo retomas la actividad.', reason: '"$text"');
      }
      expect(_validate(description: ' x ').description, isNull);
    });

    test('the block reason is required only when the status is Bloqueada', () {
      expect(_validate(status: ActivityStatus.blocked).blockReason, 'Indica el motivo del bloqueo.');
      expect(_validate(status: ActivityStatus.blocked, blockReason: '   ').blockReason, 'Indica el motivo del bloqueo.');
      expect(_validate(status: ActivityStatus.blocked, blockReason: 'Falta acceso').blockReason, isNull);
      expect(_validate(status: ActivityStatus.pending).blockReason, isNull);
      expect(_validate(status: ActivityStatus.inProgress).blockReason, isNull);
    });

    test('every wrong field is reported at once', () {
      final errors = validateReactivation(
        date: DateTime.utc(2026, 11, 3),
        today: _today,
        completedOn: _completedOn,
        status: ActivityStatus.blocked,
        description: '',
        blockReason: '',
      );
      expect(errors.isEmpty, isFalse);
      expect([errors.date, errors.description, errors.blockReason].every((e) => e != null), isTrue);
    });
  });
}
