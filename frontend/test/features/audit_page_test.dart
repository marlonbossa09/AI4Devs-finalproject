import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/buttons.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/audit_history.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/widgets/audit_tag.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

Future<void> pumpApp(WidgetTester tester, {required FakeLogbookRepository logbook, Size size = desktop}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
        logbookRepositoryProvider.overrideWithValue(logbook),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> tapKey(WidgetTester tester, String key) async {
  // On a narrow screen the navigation lives in a menu that has to be opened first
  if (key.startsWith('nav-') && find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

int _n = 0;

AuditEntry entry(
  String operationName,
  AuditOperation operation, {
  String type = 'avance',
  String objectId = 'x',
  String? author = 'p1',
  DateTime? at,
  String? reason,
  Map<String, dynamic>? previous,
  Map<String, dynamic>? next,
}) => AuditEntry(
  id: 'e${++_n}',
  moment: at ?? DateTime.utc(2026, 11, 6, 10, _n),
  operationName: operationName,
  operation: operation,
  objectType: type,
  objectId: objectId,
  authorId: author,
  workDate: DateTime.utc(2026, 11, 5),
  reason: reason,
  previous: previous,
  next: next,
);

AuditEntry correction(String objectId, String from, String to, {String? author = 'p1'}) => entry(
  'correccion',
  AuditOperation.correction,
  objectId: objectId,
  author: author,
  previous: {
    'avance': {'descripcion': from},
  },
  next: {
    'avance': {'descripcion': to},
  },
);

/// An activity planned today with two progress entries. Returns it with the logbook of today.
Future<({FakeLogbookRepository repo, Activity activity, List<Progress> entries, Logbook logbook})> scenario() async {
  final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
  final activity = repo.days[formatDate(today)]!.activities.single;
  var n = 0;
  for (final (status, text) in [(ActivityStatus.inProgress, 'Primero'), (ActivityStatus.inProgress, 'Segundo')]) {
    await repo.registerProgress(activityId: activity.id, date: today, status: status, description: text, key: 'seed-${n++}');
  }
  repo.calls.clear();
  repo.progressRequests.clear();
  return (
    repo: repo,
    activity: activity,
    entries: repo.progressStored(activity.id),
    logbook: repo.days[formatDate(today)]!.logbook,
  );
}

Future<void> openActivityDetail(WidgetTester tester, Activity activity) async {
  await tapKey(tester, 'nav-activities');
  await tapKey(tester, 'activity-row-${activity.id}');
}

void main() {
  setUpAll(loadTestFonts);

  group('how it is reached', () {
    testWidgets('Mi bitácora offers the audit of the day, which asks for the audit of THAT logbook', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.logbook, s.logbook.id, [
        entry('cierre', AuditOperation.closing, type: 'bitacora', previous: {'estado': 'abierta'}, next: {'estado': 'cerrada'}),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'logbook-audit');
      final request = s.repo.auditRequests.single;
      expect(request['type'], AuditObjectType.logbook);
      expect(request['objectId'], s.logbook.id);
      expect(find.text('Historial de auditoría'), findsWidgets);
      expect(find.text('Jornada del ${formatShortDate(today)}'), findsOneWidget);
      expect(find.byKey(const Key('audit-subject')), findsOneWidget);
    });

    testWidgets('the activity detail offers the audit of the activity and of each of its entries', (tester) async {
      final s = await scenario();
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      expect(find.byKey(const Key('detail-audit')), findsOneWidget);
      for (final entry in s.entries) {
        expect(find.byKey(Key('detail-audit-${entry.id}')), findsOneWidget);
      }
      await tapKey(tester, 'detail-audit');
      expect(s.repo.auditRequests.single['type'], AuditObjectType.activity);
      expect(s.repo.auditRequests.single['objectId'], s.activity.id);
      expect(find.text('Preparar informe'), findsWidgets);
    });

    testWidgets('the audit of ONE progress entry is asked by its own identifier', (tester) async {
      final s = await scenario();
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit-${s.entries[1].id}');
      expect(s.repo.auditRequests.single['type'], AuditObjectType.progress);
      expect(s.repo.auditRequests.single['objectId'], s.entries[1].id);
      expect(find.textContaining('Segundo'), findsWidgets);
    });

    testWidgets('a marked activity keeps its audit consultable (CA-120)', (tester) async {
      final s = await scenario();
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-audit')), findsOneWidget);
      await tapKey(tester, 'detail-audit');
      expect(s.repo.auditRequests.single['objectId'], s.activity.id);
    });

    testWidgets('going back returns to the page the audit was opened from', (tester) async {
      final s = await scenario();
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      await tapKey(tester, 'audit-back');
      expect(find.byKey(const Key('detail-status')), findsOneWidget);

      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'logbook-audit');
      await tapKey(tester, 'audit-back');
      expect(find.byKey(const Key('logbook-audit')), findsOneWidget);
    });

    testWidgets('it is loaded again every time it opens: what it shows is what the server holds now', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [correction(s.activity.id, 'a', 'b')]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.byType(AnimatedBuilder), findsWidgets);
      expect(s.repo.auditRequests.length, 1);
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [
        correction(s.activity.id, 'a', 'b'),
        correction(s.activity.id, 'b', 'c'),
      ]);
      await tapKey(tester, 'audit-back');
      await tapKey(tester, 'detail-audit');
      expect(s.repo.auditRequests.length, 2);
      expect(find.byKey(const Key('audit-label')), findsNWidgets(2));
    });
  });

  group('the timeline', () {
    testWidgets('shows the operation, when, who, the day, the reason and the values before and after', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.logbook, s.logbook.id, [
        entry('cierre', AuditOperation.closing, type: 'bitacora', at: DateTime.utc(2026, 11, 6, 18), previous: {'estado': 'abierta', 'cerrada_en': null}, next: {'estado': 'cerrada', 'cerrada_en': '2026-11-06T18:00:00Z'}),
        entry('reapertura', AuditOperation.reopening, type: 'bitacora', at: DateTime.utc(2026, 11, 6, 19), reason: 'Faltaba una cifra', previous: {'estado': 'cerrada'}, next: {'estado': 'abierta'}),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'logbook-audit');
      final ids = s.repo.auditEntries.values.single.map((e) => e.id).toList();
      expect(find.text('Cierre de la jornada'), findsOneWidget);
      expect(find.text('Reapertura de la jornada'), findsOneWidget);
      expect(find.text(formatDateTime(DateTime.utc(2026, 11, 6, 18))), findsWidgets);
      expect(find.byKey(Key('audit-author-${ids[0]}')), findsOneWidget);
      expect(find.text('Autor: Tú'), findsNWidgets(2));
      expect(find.text('Jornada: ${formatShortDate(DateTime.utc(2026, 11, 5))}'), findsNWidgets(2));
      // The reason of a reopening (CA-109)
      expect(find.text('Motivo: Faltaba una cifra'), findsOneWidget);
      expect(find.byKey(Key('audit-reason-${ids[0]}')), findsNothing);
      // The values before and after
      expect(find.text('Estado de la jornada'), findsNWidgets(2));
      expect(find.text('Abierta'), findsWidgets);
      expect(find.text('Cerrada'), findsWidgets);
      expect(find.text('ANTES'), findsWidgets);
      expect(find.text('AHORA'), findsWidgets);
    });

    testWidgets('a cycle of closings and reopenings reads in order (CA-266)', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.logbook, s.logbook.id, [
        entry('cierre', AuditOperation.closing, type: 'bitacora'),
        entry('reapertura', AuditOperation.reopening, type: 'bitacora', reason: 'Corregir'),
        entry('cierre', AuditOperation.closing, type: 'bitacora'),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'logbook-audit');
      final y = [
        for (final e in s.repo.auditEntries.values.single) tester.getTopLeft(find.byKey(Key('audit-entry-${e.id}'))).dy,
      ];
      expect(y[0] < y[1] && y[1] < y[2], isTrue); // oldest first, as the server sends them
      expect(find.text('Cierre de la jornada'), findsNWidgets(2));
      expect(find.byKey(const Key('audit-order')), findsOneWidget);
    });

    testWidgets('a correction shows what the description was and what it became', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.progress, s.entries[0].id, [correction(s.entries[0].id, 'Texto antiguo', 'Texto nuevo')]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit-${s.entries[0].id}');
      expect(find.text('Corrección'), findsOneWidget);
      expect(find.text('Descripción del avance'), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('audit-before'))).data, 'Texto antiguo');
      expect(tester.widget<Text>(find.byKey(const Key('audit-after'))).data, 'Texto nuevo');
    });

    testWidgets('a value that appears or disappears is shown against a dash', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [
        entry('marca_error', AuditOperation.errorMark, type: 'actividad', reason: 'Duplicada', previous: {'marca_error': null}, next: {
          'marca_error': {'motivo': 'Duplicada', 'marcada_en': '2026-11-06T15:30:00Z', 'marcada_por': 'p1'},
        }),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.text('Marca de error'), findsOneWidget);
      expect(find.text('Motivo de la marca'), findsOneWidget);
      expect(find.text('—'), findsWidgets);
      expect(find.text('Duplicada'), findsWidgets);
    });

    testWidgets('only the signed-in user is named; anyone else is "Otra persona" and no id or name appears', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [
        correction(s.activity.id, 'a', 'b'),
        correction(s.activity.id, 'b', 'c', author: 'persona-ajena-123'),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.text('Autor: Tú'), findsOneWidget);
      expect(find.text('Autor: Otra persona'), findsOneWidget);
      expect(find.textContaining('persona-ajena-123'), findsNothing);
      expect(find.textContaining('p1'), findsNothing);
    });

    testWidgets('technical identifiers of the values are never shown', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.progress, s.entries[0].id, [
        entry('correccion', AuditOperation.correction, previous: {'actividad_id': 'ACTIVIDAD-XYZ', 'avance': {'descripcion': 'a'}}, next: {
          'actividad_id': 'ACTIVIDAD-XYZ',
          'bitacora_id': 'BITACORA-XYZ',
          'avance': {'descripcion': 'b'},
        }),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit-${s.entries[0].id}');
      expect(find.textContaining('XYZ'), findsNothing);
    });
  });

  group('the audit is not the work history', () {
    testWidgets('it says so, carries its own tag, and offers no action over the records', (tester) async {
      final s = await scenario();
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [correction(s.activity.id, 'a', 'b')]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.byType(AuditTag), findsOneWidget); // its own tag, apart from EJECUCIÓN and PLANIFICACIÓN
      expect(find.byKey(const Key('audit-explanation')), findsOneWidget);
      expect(find.textContaining('No es el historial de avances'), findsOneWidget);
      // None of the work-history blocks or actions of the detail
      expect(find.text('EJECUCIÓN'), findsNothing);
      expect(find.text('Historial de avances'), findsNothing);
      expect(find.byKey(const Key('detail-register-progress')), findsNothing);
      expect(find.byKey(Key('detail-correct-${s.entries[0].id}')), findsNothing);
      expect(find.byKey(const Key('detail-mark-error')), findsNothing);
      // It is read-only: no field to type in, no way to change anything
      expect(find.byType(TextField), findsNothing);
      expect(s.repo.progressRequests, isEmpty);
    });
  });

  group('the states', () {
    testWidgets('while it loads it shows a spinner and nothing else', (tester) async {
      final s = await scenario();
      s.repo.auditGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tester.tap(find.byKey(const Key('detail-audit')));
      await tester.pump();
      await tester.pump();
      expect(find.byKey(const Key('audit-loading')), findsOneWidget);
      expect(find.byKey(const Key('audit-empty')), findsNothing);
      s.repo.auditGate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('audit-loading')), findsNothing);
    });

    testWidgets('a record with no entries says so and explains when they appear', (tester) async {
      final s = await scenario();
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.byKey(const Key('audit-empty')), findsOneWidget);
      expect(find.textContaining('Todavía no hay entradas de auditoría para la actividad'), findsOneWidget);
      expect(find.byKey(const Key('audit-load-more')), findsNothing);
    });

    testWidgets('a failure shows its message and can be retried', (tester) async {
      final s = await scenario();
      s.repo.auditErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [correction(s.activity.id, 'a', 'b')]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.byKey(const Key('load-error')), findsOneWidget);
      expect(find.byKey(const Key('audit-label')), findsNothing);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('audit-label')), findsOneWidget);
    });

    testWidgets('a record that is not available shows no entries and does not say whether it exists', (tester) async {
      final s = await scenario();
      s.repo.auditUnavailable.add('activity|${s.activity.id}');
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit');
      expect(find.text('Este registro no está disponible.'), findsOneWidget);
      expect(find.byKey(const Key('audit-label')), findsNothing);
      expect(find.byKey(const Key('audit-empty')), findsNothing);
      expect(find.textContaining('existe'), findsNothing);
      expect(find.textContaining('ajena'), findsNothing);
    });
  });

  group('more entries', () {
    Future<FakeLogbookRepository> fiveEntries(WidgetTester tester) async {
      final s = await scenario();
      s.repo.auditPageSize = 2;
      s.repo.seedAudit(AuditObjectType.progress, s.entries[0].id, [
        for (var i = 0; i < 5; i++) correction(s.entries[0].id, 'v$i', 'v${i + 1}'),
      ]);
      await pumpApp(tester, logbook: s.repo);
      await openActivityDetail(tester, s.activity);
      await tapKey(tester, 'detail-audit-${s.entries[0].id}');
      return s.repo;
    }

    testWidgets('shows the first page and a button for more; each tap adds the next page in order, with no repeats', (tester) async {
      final repo = await fiveEntries(tester);
      expect(find.byKey(const Key('audit-label')), findsNWidgets(2));
      expect(find.byKey(const Key('audit-load-more')), findsOneWidget);
      expect(find.text('Ver más entradas'), findsOneWidget);
      await tapKey(tester, 'audit-load-more');
      expect(find.byKey(const Key('audit-label')), findsNWidgets(4));
      expect(repo.auditRequests.last['cursor'], 'c2');
      await tapKey(tester, 'audit-load-more');
      expect(find.byKey(const Key('audit-label')), findsNWidgets(5));
      expect(repo.auditRequests.last['cursor'], 'c4');
      // The last page has no cursor: no more button
      expect(find.byKey(const Key('audit-load-more')), findsNothing);
      // In order, none repeated
      final shown = repo.auditEntries.values.single;
      final y = [for (final e in shown) tester.getTopLeft(find.byKey(Key('audit-entry-${e.id}'))).dy];
      expect(y, [...y]..sort());
      expect(y.toSet().length, 5);
    });

    testWidgets('a failure loading more keeps the pages already shown and offers to retry', (tester) async {
      final repo = await fiveEntries(tester);
      repo.auditErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await tapKey(tester, 'audit-load-more');
      expect(find.byKey(const Key('audit-more-error')), findsOneWidget);
      expect(find.byKey(const Key('audit-label')), findsNWidgets(2)); // nothing lost
      expect(find.text('Reintentar'), findsOneWidget);
      await tapKey(tester, 'audit-load-more');
      expect(find.byKey(const Key('audit-more-error')), findsNothing);
      expect(find.byKey(const Key('audit-label')), findsNWidgets(4));
    });

    testWidgets('a second tap while a page loads asks nothing more', (tester) async {
      final repo = await fiveEntries(tester);
      repo.auditGate = Completer<void>();
      final button = find.byKey(const Key('audit-load-more'));
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pump();
      await tester.tap(button, warnIfMissed: false);
      await tester.pump();
      expect(tester.widget<SecondaryButton>(button).onPressed, isNull);
      expect(find.text('Cargando…'), findsOneWidget);
      expect(repo.auditRequests.where((r) => r['cursor'] != null).length, 1);
      repo.auditGate!.complete();
      await tester.pumpAndSettle();
      expect(repo.auditRequests.where((r) => r['cursor'] != null).length, 1);
    });
  });

  group('the provider', () {
    test('ignores a second "load more" while one is in flight, and loses nothing', () async {
      final repo = FakeLogbookRepository()..auditPageSize = 2;
      repo.seedAudit(AuditObjectType.activity, 'a1', [for (var i = 0; i < 5; i++) correction('a1', 'v$i', 'v${i + 1}')]);
      final container = ProviderContainer(overrides: [logbookRepositoryProvider.overrideWithValue(repo)]);
      addTearDown(container.dispose);
      final provider = auditHistoryProvider(AuditObjectType.activity, 'a1');
      container.listen(provider, (previous, next) {}); // keeps it alive
      expect((await container.read(provider.future)).items.length, 2);

      repo.auditGate = Completer<void>();
      final notifier = container.read(provider.notifier);
      final first = notifier.loadMore();
      final second = notifier.loadMore(); // while the first is still waiting
      await Future<void>.delayed(Duration.zero);
      expect(container.read(provider).value!.loadingMore, isTrue);
      repo.auditGate!.complete();
      await Future.wait([first, second]);
      expect(repo.auditRequests.where((r) => r['cursor'] != null).length, 1);
      expect(container.read(provider).value!.items.length, 4);
      expect(container.read(provider).value!.hasMore, isTrue);
    });
  });

  group('every screen size', () {
    for (final (name, size) in [('mobile', mobile), ('tablet', tablet), ('desktop', desktop)]) {
      testWidgets('$name: the whole flow works without layout errors', (tester) async {
        final s = await scenario();
        s.repo.auditPageSize = 2;
        s.repo.seedAudit(AuditObjectType.activity, s.activity.id, [
          entry('marca_error', AuditOperation.errorMark, type: 'actividad', reason: 'Una explicación bastante larga para comprobar que el texto se ajusta bien en pantallas estrechas', previous: {'marca_error': null}, next: {
            'marca_error': {'motivo': 'Duplicada con un texto largo de ejemplo', 'marcada_en': '2026-11-06T15:30:00Z', 'marcada_por': 'p1'},
          }),
          correction(s.activity.id, 'Un texto anterior largo para ver cómo se parte', 'Un texto nuevo largo para ver cómo se parte'),
          correction(s.activity.id, 'b', 'c'),
        ]);
        await pumpApp(tester, logbook: s.repo, size: size);
        await openActivityDetail(tester, s.activity);
        await tapKey(tester, 'detail-audit');
        expect(tester.takeException(), isNull);
        expect(find.byKey(const Key('audit-load-more')), findsOneWidget);
        await tapKey(tester, 'audit-load-more');
        expect(tester.takeException(), isNull);
        expect(find.byKey(const Key('audit-load-more')), findsNothing);
        await tapKey(tester, 'audit-back');
        expect(find.byKey(const Key('detail-status')), findsOneWidget);
      });
    }
  });
}
