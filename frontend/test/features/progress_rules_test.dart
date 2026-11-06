import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/utils/keys.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/progress_rules.dart';

final _today = DateTime.utc(2026, 11, 6);

ProgressErrors _validate({
  String? activityId = 'a-1',
  DateTime? date,
  ActivityStatus? status = ActivityStatus.inProgress,
  String description = 'Trabajo realizado',
  String blockReason = '',
}) => validateProgress(
  activityId: activityId,
  date: date ?? _today,
  today: _today,
  status: status,
  description: description,
  blockReason: blockReason,
);

void main() {
  group('validateProgress', () {
    test('a complete, valid entry has no errors', () {
      expect(_validate().isEmpty, isTrue);
    });

    test('the activity must be chosen', () {
      expect(_validate(activityId: null).activity, isNotNull);
    });

    test('the description is required: empty and only spaces are rejected (CA-68, CA-69)', () {
      for (final text in ['', '   ', '\n\t ']) {
        expect(_validate(description: text).description, 'Describe el trabajo realizado.', reason: '"$text"');
      }
      expect(_validate(description: ' x ').description, isNull);
    });

    test('a future date is rejected, today and the past are accepted (CA-182)', () {
      expect(_validate(date: DateTime.utc(2026, 11, 7)).date, isNotNull);
      expect(_validate(date: _today).date, isNull);
      expect(_validate(date: DateTime.utc(2025, 1, 1)).date, isNull); // a retroactive entry
    });

    test('a status must be chosen', () {
      expect(_validate(status: null).status, 'Elige un estado.');
    });

    test('the four statuses are accepted', () {
      for (final status in ActivityStatus.values) {
        final reason = status == ActivityStatus.blocked ? 'Falta acceso' : '';
        expect(_validate(status: status, blockReason: reason).isEmpty, isTrue, reason: status.name);
      }
    });

    test('blocked requires a reason: empty and only spaces are rejected (CA-49)', () {
      for (final reason in ['', '   ']) {
        final errors = _validate(status: ActivityStatus.blocked, blockReason: reason);
        expect(errors.blockReason, 'Indica el motivo del bloqueo.', reason: '"$reason"');
      }
      expect(_validate(status: ActivityStatus.blocked, blockReason: 'Sin acceso').blockReason, isNull);
    });

    test('the reason is not required, nor validated, for any other status', () {
      for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.completed]) {
        expect(_validate(status: status, blockReason: '').blockReason, isNull, reason: status.name);
      }
    });

    test('every problem is reported at once, each on its own field', () {
      final errors = validateProgress(
        activityId: null,
        date: DateTime.utc(2027, 1, 1),
        today: _today,
        status: ActivityStatus.blocked,
        description: ' ',
        blockReason: '',
      );
      expect(errors.activity, isNotNull);
      expect(errors.date, isNotNull);
      expect(errors.description, isNotNull);
      expect(errors.blockReason, isNotNull);
      expect(errors.status, isNull);
      expect(errors.isEmpty, isFalse);
    });
  });

  group('IntentionKey (T-04)', () {
    test('retrying the same request reuses the key', () {
      final intention = IntentionKey();
      final first = intention.forRequest('a|2026-11-06|inProgress|trabajo|');
      expect(intention.forRequest('a|2026-11-06|inProgress|trabajo|'), first);
      expect(intention.forRequest('a|2026-11-06|inProgress|trabajo|'), first);
    });

    test('changing what is sent is a different intention and gets a new key', () {
      final intention = IntentionKey();
      final first = intention.forRequest('uno');
      final second = intention.forRequest('dos');
      expect(second, isNot(first));
      expect(intention.forRequest('dos'), second);
    });

    test('after the server accepts the request the next one is a new intention', () {
      final intention = IntentionKey();
      final first = intention.forRequest('igual');
      intention.accepted();
      expect(intention.forRequest('igual'), isNot(first));
    });

    test('keys are opaque 128-bit hex values', () {
      final key = IntentionKey().forRequest('x');
      expect(RegExp(r'^[0-9a-f]{32}$').hasMatch(key), isTrue);
    });
  });
}
