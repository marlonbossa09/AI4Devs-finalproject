import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/mark_rules.dart';

final _origin = DateTime.utc(2026, 11, 2);

Activity _activity({bool marked = false, DateTime? date, ActivityStatus status = ActivityStatus.pending}) => Activity(
  id: 'a1',
  userId: 'p1',
  title: 'Preparar informe',
  origin: ActivityOrigin.planned,
  status: status,
  date: date ?? _origin,
  createdAt: DateTime.utc(2026, 11, 6, 8),
  marked: marked,
  markReason: marked ? 'Duplicada' : null,
);

Progress _progress(String id, DateTime date, {ActivityStatus status = ActivityStatus.inProgress}) => Progress(
  id: id,
  activityId: 'a1',
  date: date,
  status: status,
  description: 'Avancé',
  createdAt: DateTime.utc(2026, 11, 6, 10),
);

Planning _continuation(DateTime date) => Planning(
  id: 'pc',
  activityId: 'a1',
  date: date,
  type: PlanningType.continuation,
  description: 'Seguir',
  createdAt: DateTime.utc(2026, 11, 2, 10),
);

Logbook _logbook() => Logbook(
  id: 'b1',
  userId: 'p1',
  date: _origin,
  dateType: DateType.past,
  closed: false,
  summary: '',
  createdAt: DateTime.utc(2026, 11, 2, 8),
  updatedAt: DateTime.utc(2026, 11, 2, 9),
);

void main() {
  group('canMarkAsError (RN-59: no progress after the origin day)', () {
    test('an activity without progress can be marked', () {
      expect(canMarkAsError(activity: _activity(), progress: const []), isTrue);
    });

    test('progress on the origin day itself does not prevent it', () {
      expect(canMarkAsError(activity: _activity(), progress: [_progress('p1', _origin), _progress('p2', _origin)]), isTrue);
    });

    test('progress on a LATER day prevents it, whatever its status or kind', () {
      final later = DateTime.utc(2026, 11, 3);
      for (final status in ActivityStatus.values) {
        expect(
          canMarkAsError(activity: _activity(), progress: [_progress('p1', later, status: status)]),
          isFalse,
          reason: status.name,
        );
      }
    });

    test('progress BEFORE the origin day does not prevent it (PA-28: only later days count)', () {
      expect(canMarkAsError(activity: _activity(), progress: [_progress('p1', DateTime.utc(2026, 10, 30))]), isTrue);
    });

    test('the origin is the work date of the origin logbook: one entry on a later date is enough', () {
      final progress = [_progress('p1', _origin), _progress('p2', DateTime.utc(2026, 11, 2, 0, 0, 1))];
      expect(hasProgressAfterOrigin(activity: _activity(), progress: progress), isTrue);
    });

    test('an activity that is already marked cannot be marked again', () {
      expect(canMarkAsError(activity: _activity(marked: true), progress: const []), isFalse);
    });

    test('the status does not matter: a Completada activity without later progress can be marked', () {
      expect(canMarkAsError(activity: _activity(status: ActivityStatus.completed), progress: const []), isTrue);
    });
  });

  group('canRevertMark', () {
    test('only while the mark is in force', () {
      expect(canRevertMark(_activity(marked: true)), isTrue);
      expect(canRevertMark(_activity()), isFalse);
    });
  });

  group('validateMarkReason (CA-116)', () {
    test('an empty or blank reason is not accepted', () {
      for (final reason in ['', '   ', '\n\t']) {
        expect(validateMarkReason(reason), isNotNull, reason: reason.codeUnits.toString());
      }
    });

    test('a reason with text is accepted', () {
      expect(validateMarkReason('Se creó dos veces'), isNull);
    });
  });

  group('the day separates operational activities from marked ones (CA-119, CA-120)', () {
    LogbookDay day(List<Activity> activities, {List<Progress> progress = const []}) =>
        LogbookDay(logbook: _logbook(), plannings: const [], activities: activities, progress: progress);

    test('counts and operational lists leave marked activities out', () {
      final marked = Activity(
        id: 'a2',
        userId: 'p1',
        title: 'Duplicada',
        origin: ActivityOrigin.planned,
        status: ActivityStatus.completed,
        date: _origin,
        createdAt: DateTime.utc(2026, 11, 6, 8),
        marked: true,
        markReason: 'x',
      );
      final d = day([_activity(), marked]);
      expect(d.operationalActivities.map((a) => a.id), ['a1']);
      expect(d.markedActivities.map((a) => a.id), ['a2']);
      expect(d.count(ActivityStatus.completed), 0); // the marked one is Completada, but it does not count
      expect(d.count(ActivityStatus.pending), 1);
      expect(d.activities.length, 2); // nothing was removed from the day
    });

    test('a marked activity keeps its plannings and progress: the history is not hidden', () {
      final marked = _activity(marked: true);
      final d = LogbookDay(
        logbook: _logbook(),
        plannings: [_continuation(DateTime.utc(2026, 11, 9))],
        activities: [marked],
        progress: [_progress('p1', _origin)],
      );
      expect(d.progressOf(marked).length, 1);
      expect(d.continuationsOf(marked).length, 1);
    });

    test('a day with no marked activities has an empty marked list', () {
      expect(day([_activity()]).markedActivities, isEmpty);
    });
  });
}
