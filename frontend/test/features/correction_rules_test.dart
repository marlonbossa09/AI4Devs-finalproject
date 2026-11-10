import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/correction_rules.dart';

final _mon = DateTime.utc(2026, 11, 2);
final _tue = DateTime.utc(2026, 11, 3);
final _wed = DateTime.utc(2026, 11, 4);
final _thu = DateTime.utc(2026, 11, 5);

Progress _p(
  String id,
  DateTime date,
  ActivityStatus status, {
  bool reactivation = false,
  String description = 'Avancé',
  String? reason,
  DateTime? modifiedAt,
}) => Progress(
  id: id,
  activityId: 'a1',
  date: date,
  status: status,
  description: description,
  createdAt: DateTime.utc(2026, 11, 6, 10),
  blockReason: reason,
  isReactivation: reactivation,
  modifiedAt: modifiedAt,
);

Activity _activity({bool marked = false}) => Activity(
  id: 'a1',
  userId: 'p1',
  title: 'Preparar informe',
  origin: ActivityOrigin.planned,
  status: ActivityStatus.pending,
  date: _mon,
  createdAt: DateTime.utc(2026, 11, 6, 8),
  marked: marked,
);

void main() {
  group('what can be corrected', () {
    test('an ordinary entry can be left in any of the four statuses; a reactivation never in Completada', () {
      expect(correctionStatuses(_p('1', _mon, ActivityStatus.inProgress)), ActivityStatus.values);
      expect(
        correctionStatuses(_p('2', _tue, ActivityStatus.inProgress, reactivation: true)),
        [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked],
      );
    });

    test('the entries of a marked activity are not corrected until the mark is reverted (D-05)', () {
      expect(canCorrect(_activity()), isTrue);
      expect(canCorrect(_activity(marked: true)), isFalse);
    });

    test('an entry corrected after it was recorded says so; one never corrected does not (CA-62)', () {
      expect(_p('1', _mon, ActivityStatus.pending).corrected, isFalse);
      expect(_p('1', _mon, ActivityStatus.pending, modifiedAt: DateTime.utc(2026, 11, 6, 10)).corrected, isFalse);
      expect(_p('1', _mon, ActivityStatus.pending, modifiedAt: DateTime.utc(2026, 11, 6, 11)).corrected, isTrue);
    });
  });

  group('the sequence (IR-11, PA-29 option A)', () {
    test('a valid sequence has no breaches, with several cycles', () {
      final progress = [
        _p('1', _mon, ActivityStatus.completed),
        _p('2', _tue, ActivityStatus.pending, reactivation: true),
        _p('3', _wed, ActivityStatus.completed),
        _p('4', _thu, ActivityStatus.blocked, reactivation: true, reason: 'x'),
      ];
      expect(newSequenceViolations(progress, '1', ActivityStatus.completed), isEmpty);
    });

    test('CA-236: correcting the Monday entry to Completada, with entries after it, is rejected', () {
      final progress = [
        _p('1', _mon, ActivityStatus.inProgress),
        _p('2', _tue, ActivityStatus.inProgress),
        _p('3', _wed, ActivityStatus.completed),
        _p('4', _thu, ActivityStatus.inProgress, reactivation: true),
      ];
      final violations = newSequenceViolations(progress, '1', ActivityStatus.completed);
      expect(violations, [const SequenceViolation('2', SequenceProblem.progressAfterCompletion)]);
    });

    test('CA-238: correcting the completion to another status is valid when nothing depends on it', () {
      final progress = [_p('1', _mon, ActivityStatus.inProgress), _p('2', _tue, ActivityStatus.completed)];
      expect(newSequenceViolations(progress, '2', ActivityStatus.inProgress), isEmpty);
    });

    test('correcting the completion when a reactivation follows leaves it without completion: rejected', () {
      final progress = [
        _p('1', _mon, ActivityStatus.completed),
        _p('2', _tue, ActivityStatus.inProgress, reactivation: true),
      ];
      expect(newSequenceViolations(progress, '1', ActivityStatus.inProgress), [
        const SequenceViolation('2', SequenceProblem.reactivationWithoutCompletion),
      ]);
    });

    test('a reactivation cannot be corrected to Completada', () {
      final progress = [
        _p('1', _mon, ActivityStatus.completed),
        _p('2', _tue, ActivityStatus.inProgress, reactivation: true),
      ];
      expect(newSequenceViolations(progress, '2', ActivityStatus.completed), [
        const SequenceViolation('2', SequenceProblem.reactivationCompleted),
      ]);
    });

    test('PA-27: a pair a retroactive entry admitted does not reject a correction that does not worsen it', () {
      // Completada on Tuesday (retroactive) between a Monday entry and a Wednesday one: Wednesday is a breach already
      final progress = [
        _p('1', _mon, ActivityStatus.inProgress),
        _p('2', _tue, ActivityStatus.completed),
        _p('3', _wed, ActivityStatus.inProgress),
      ];
      expect(sequenceViolations(_seq(progress)), {const SequenceViolation('3', SequenceProblem.progressAfterCompletion)});
      expect(newSequenceViolations(progress, '3', ActivityStatus.blocked), isEmpty); // does not touch the pair
      expect(newSequenceViolations(progress, '3', ActivityStatus.completed), isEmpty); // does not worsen it
      expect(newSequenceViolations(progress, '2', ActivityStatus.pending), isEmpty); // even resolves it
    });

    test('PA-29: a correction that worsens the admitted pair is rejected', () {
      final progress = [
        _p('1', _mon, ActivityStatus.inProgress),
        _p('2', _tue, ActivityStatus.completed),
        _p('3', _wed, ActivityStatus.inProgress),
      ];
      expect(newSequenceViolations(progress, '1', ActivityStatus.completed), [
        const SequenceViolation('2', SequenceProblem.progressAfterCompletion),
      ]);
    });

    test('the current status after a correction is the status of the last entry', () {
      final progress = [_p('1', _mon, ActivityStatus.inProgress), _p('2', _tue, ActivityStatus.completed)];
      expect(currentStatusAfter(progress, '2', ActivityStatus.blocked), ActivityStatus.blocked);
      expect(currentStatusAfter(progress, '1', ActivityStatus.pending), ActivityStatus.completed);
      expect(currentStatusAfter(const [], 'x', ActivityStatus.blocked), ActivityStatus.pending);
    });
  });

  group('buildCorrection sends only what changed', () {
    final original = _p('1', _mon, ActivityStatus.inProgress, description: 'Texto');

    test('nothing changed is an empty correction', () {
      final c = buildCorrection(original: original, status: ActivityStatus.inProgress, description: 'Texto', blockReason: '');
      expect(c.isEmpty, isTrue);
    });

    test('text is compared and sent without the spaces at its ends', () {
      expect(
        buildCorrection(original: original, status: ActivityStatus.inProgress, description: '  Texto  ', blockReason: '').isEmpty,
        isTrue,
      );
      final c = buildCorrection(original: original, status: ActivityStatus.inProgress, description: '  Otro  ', blockReason: '');
      expect((c.status, c.description, c.blockReason), (null, 'Otro', null));
    });

    test('a new status goes alone; the reason only goes with Bloqueada', () {
      final toBlocked = buildCorrection(
        original: original,
        status: ActivityStatus.blocked,
        description: 'Texto',
        blockReason: ' Sin acceso ',
      );
      expect((toBlocked.status, toBlocked.description, toBlocked.blockReason), (ActivityStatus.blocked, null, 'Sin acceso'));
      final toPending = buildCorrection(
        original: original,
        status: ActivityStatus.pending,
        description: 'Texto',
        blockReason: 'sobra', // a stale reason is never sent for another status
      );
      expect((toPending.status, toPending.blockReason), (ActivityStatus.pending, null));
    });

    test('correcting only the reason of a blocked entry sends only the reason; an unchanged one sends nothing', () {
      final blocked = _p('1', _mon, ActivityStatus.blocked, reason: 'Motivo');
      final changed = buildCorrection(original: blocked, status: ActivityStatus.blocked, description: 'Avancé', blockReason: 'Otro motivo');
      expect((changed.status, changed.description, changed.blockReason), (null, null, 'Otro motivo'));
      expect(
        buildCorrection(original: blocked, status: ActivityStatus.blocked, description: 'Avancé', blockReason: 'Motivo').isEmpty,
        isTrue,
      );
    });
  });

  group('validateCorrection', () {
    final progress = [
      _p('1', _mon, ActivityStatus.inProgress, description: 'Lunes'),
      _p('2', _tue, ActivityStatus.completed, description: 'Martes'),
    ];

    test('a blank description is not accepted', () {
      final e = validateCorrection(
        original: progress[0],
        progress: progress,
        status: ActivityStatus.inProgress,
        description: '   ',
        blockReason: '',
      );
      expect(e.description, isNotNull);
    });

    test('Bloqueada needs a reason', () {
      final e = validateCorrection(
        original: progress[0],
        progress: progress,
        status: ActivityStatus.blocked,
        description: 'Lunes',
        blockReason: '  ',
      );
      expect(e.blockReason, isNotNull);
    });

    test('a form equal to the entry has nothing to correct', () {
      final e = validateCorrection(
        original: progress[0],
        progress: progress,
        status: ActivityStatus.inProgress,
        description: 'Lunes',
        blockReason: '',
      );
      expect(e.nothingChanged, isTrue);
      expect(e.isEmpty, isFalse);
    });

    test('a correction that breaks the sequence is explained', () {
      final e = validateCorrection(
        original: progress[0],
        progress: progress,
        status: ActivityStatus.completed,
        description: 'Lunes',
        blockReason: '',
      );
      expect(e.sequence, contains('posterior a una finalización'));
    });

    test('a valid correction has no errors', () {
      final e = validateCorrection(
        original: progress[1],
        progress: progress,
        status: ActivityStatus.inProgress,
        description: 'Martes, corregido',
        blockReason: '',
      );
      expect(e.isEmpty, isTrue);
    });
  });
}

List<({String id, ActivityStatus status, bool reactivation})> _seq(List<Progress> progress) => [
  for (final p in progress) (id: p.id, status: p.status, reactivation: p.isReactivation),
];
