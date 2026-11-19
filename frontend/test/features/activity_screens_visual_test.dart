import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart' hide AuditPage;
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/pages/activities_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/activity_detail_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/audit_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/continuation_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/correction_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/planning_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/progress_page.dart';
import 'package:smartwork/features/logbook/presentation/pages/reactivation_page.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// The activity screens after their visual redesign (UX-T6): the list, the detail, the progress, continuation, correction and
/// reactivation forms, the audit and Planificación. Their rules live in their own test files; this one covers what the redesign
/// promises: nothing overflows on a desktop, a tablet or a phone (also with a larger text), nothing informative is smaller than
/// 12 px or smaller than a 40 px touch target, no clock time, duration or percentage is invented, each screen has ONE main action,
/// and a form that fails keeps what the person typed.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);
final tomorrow = DateTime.utc(2026, 11, 7);

const longTitle = 'Preparar el informe trimestral de resultados con las conclusiones de todas las áreas implicadas en el proyecto';
const longText =
    'Revisar las cifras de cada área, consolidarlas en un solo documento con sus fuentes y dejar constancia de las diferencias '
    'encontradas entre lo previsto y lo realizado durante todo el trimestre.';

class Scene {
  Scene(this.repo, {required this.busy, required this.done, required this.entries});

  final FakeLogbookRepository repo;

  /// Planned, with a long title, two progress entries (the last one blocked) and a planned continuation.
  final Activity busy;

  /// Planned and Completada.
  final Activity done;

  /// The progress entries of [busy], in order.
  final List<Progress> entries;
}

Future<Scene> scene() async {
  final repo = FakeLogbookRepository()
    ..seed(today, longTitle, description: longText)
    ..seed(yesterday, 'Entregar informe', description: 'Enviar el informe final');
  Activity find(String title) => repo.days.values.expand((d) => d.activities).firstWhere((a) => a.title == title);
  final busy = find(longTitle);
  final done = find('Entregar informe');
  await repo.registerProgress(
    activityId: busy.id,
    date: yesterday,
    status: ActivityStatus.inProgress,
    description: longText,
    key: 'k1',
  );
  await repo.registerProgress(
    activityId: busy.id,
    date: today,
    status: ActivityStatus.blocked,
    description: 'Me quedé sin acceso a los datos de dos áreas',
    blockReason: 'Falta el acceso al servidor de datos de cada área, pendiente de la autorización del responsable',
    key: 'k2',
  );
  await repo.registerProgress(
    activityId: done.id,
    date: yesterday,
    status: ActivityStatus.completed,
    description: 'Entregado',
    key: 'k3',
  );
  await repo.registerUnplanned(
    date: today,
    title: 'Atender un incidente urgente',
    status: ActivityStatus.inProgress,
    description: 'Se atiende ahora',
    key: 'k4',
  );
  repo.addContinuation(busy.id, tomorrow, 'Seguir con las cifras pendientes');
  repo.calls.clear();
  repo.progressRequests.clear();
  final fresh = find(longTitle);
  return Scene(repo, busy: fresh, done: find('Entregar informe'), entries: repo.progressStored(busy.id));
}

Future<ProviderContainer> pumpApp(
  WidgetTester tester,
  FakeLogbookRepository repo, {
  Size size = desktop,
  double textScale = 1,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  if (textScale != 1) {
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  }
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
        logbookRepositoryProvider.overrideWithValue(repo),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
  return ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));
}

Future<void> go(WidgetTester tester, ProviderContainer c, AppPage page) async {
  c.read(currentPageProvider.notifier).go(page);
  await tester.pumpAndSettle();
}

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

AuditEntry auditEntry(String id, AuditOperation operation, {String? reason, Map<String, dynamic>? previous, Map<String, dynamic>? next, String type = 'avance', String objectId = 'x'}) =>
    AuditEntry(
      id: id,
      moment: DateTime.utc(2026, 11, 6, 10, 5),
      operationName: operation == AuditOperation.correction ? 'correccion' : 'reapertura',
      operation: operation,
      objectType: type,
      objectId: objectId,
      authorId: 'p1',
      workDate: yesterday,
      reason: reason,
      previous: previous,
      next: next,
    );

/// One screen: how to reach it and which page widget it is.
class Screen {
  const Screen(this.name, this.page, this.open);

  final String name;
  final Type page;
  final Future<void> Function(WidgetTester tester, ProviderContainer c, Scene s) open;
}

final screens = <Screen>[
  Screen('lista de actividades', ActivitiesPage, (tester, c, s) => go(tester, c, AppPage.activities)),
  Screen('detalle (con bloqueo, continuación y marca de planificación)', ActivityDetailPage, (tester, c, s) async {
    c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.activities);
    await go(tester, c, AppPage.activityDetail);
  }),
  Screen('detalle de una actividad completada', ActivityDetailPage, (tester, c, s) async {
    c.read(activityNavProvider.notifier).open(s.done.id, back: AppPage.logbook);
    await go(tester, c, AppPage.activityDetail);
  }),
  Screen('detalle de una actividad marcada por error', ActivityDetailPage, (tester, c, s) async {
    s.repo.markAsError(s.busy.id, reason: 'Se creó dos veces por una confusión al copiar la lista de la semana pasada');
    c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.dashboard);
    await go(tester, c, AppPage.activityDetail);
  }),
  Screen('registrar avance', ProgressPage, (tester, c, s) async {
    c.read(progressTargetProvider.notifier).select(s.busy.summary);
    await go(tester, c, AppPage.progress);
    await tapKey(tester, 'progress-status-blocked');
  }),
  Screen('planificar continuación', ContinuationPage, (tester, c, s) async {
    c.read(continuationTargetProvider.notifier).select(s.busy.summary);
    await go(tester, c, AppPage.continuation);
  }),
  Screen('reactivar actividad', ReactivationPage, (tester, c, s) async {
    c.read(reactivationTargetProvider.notifier).select(s.done.summary);
    await go(tester, c, AppPage.reactivation);
    await tapKey(tester, 'reactivation-status-blocked');
  }),
  Screen('corregir avance', CorrectionPage, (tester, c, s) async {
    c.read(correctionTargetProvider.notifier).select(activityId: s.busy.id, progressId: s.entries.last.id);
    await go(tester, c, AppPage.correction);
  }),
  Screen('auditoría', AuditPage, (tester, c, s) async {
    s.repo.seedAudit(AuditObjectType.activity, s.busy.id, [
      auditEntry(
        'e1',
        AuditOperation.correction,
        objectId: s.busy.id,
        reason: 'Faltaba precisar el alcance de la revisión que se hizo con las áreas',
        previous: {
          'avance': {'descripcion': longText},
        },
        next: {
          'avance': {'descripcion': '$longText Se añadió el detalle de las fuentes consultadas.'},
        },
      ),
      auditEntry('e2', AuditOperation.reopening, type: 'bitacora', reason: 'Corregir', previous: {'estado': 'cerrada'}, next: {'estado': 'abierta'}),
    ]);
    c.read(auditTargetProvider.notifier).select(
      type: AuditObjectType.activity,
      objectId: s.busy.id,
      title: s.busy.title,
      back: AppPage.activityDetail,
    );
    await go(tester, c, AppPage.audit);
  }),
  Screen('planificación', PlanningPage, (tester, c, s) async {
    await go(tester, c, AppPage.planning);
    // Arriving opens the side panel; it is closed to look at the page itself
    final close = find.byKey(const Key('side-panel-close'));
    if (close.evaluate().isNotEmpty) {
      await tester.tap(close);
      await tester.pumpAndSettle();
    }
  }),
];

List<String> textsOf(WidgetTester tester, Type page) => [
  for (final t in tester.widgetList<Text>(find.descendant(of: find.byType(page), matching: find.byType(Text))))
    t.data ?? t.textSpan?.toPlainText() ?? '',
];

void main() {
  setUpAll(loadTestFonts);

  group('no overflow on a desktop, a tablet or a phone, also with a larger text', () {
    for (final screen in screens) {
      for (final (label, size, scale) in [
        ('1400 px', desktop, 1.0),
        ('900 px', tablet, 1.0),
        ('400 px', mobile, 1.0),
        ('400 px con texto al 150 %', mobile, 1.5),
      ]) {
        testWidgets('${screen.name}: $label', (tester) async {
          final s = await scene();
          final c = await pumpApp(tester, s.repo, size: size, textScale: scale);
          await screen.open(tester, c, s);
          expect(find.byType(screen.page), findsOneWidget);
          expect(tester.takeException(), isNull);
          // Scrolling to the end shows everything the screen holds, still without an overflow
          final scrollable = find.byType(Scrollable).first;
          await tester.drag(scrollable, const Offset(0, -3000));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
        });
      }
    }
  });

  group('the type and the touch targets of the redesign', () {
    for (final screen in screens) {
      testWidgets('${screen.name}: nothing informative below 12 px, nothing interactive below 40 px', (tester) async {
        final s = await scene();
        final c = await pumpApp(tester, s.repo, size: mobile);
        await screen.open(tester, c, s);
        final inPage = find.byType(screen.page);
        for (final text in tester.widgetList<Text>(find.descendant(of: inPage, matching: find.byType(Text)))) {
          final size = text.style?.fontSize;
          if (size != null) expect(size, greaterThanOrEqualTo(12), reason: '"${text.data}" is drawn at $size px');
        }
        for (final type in [FilledButton, OutlinedButton, TextButton]) {
          final buttons = find.descendant(of: inPage, matching: find.byType(type));
          for (var i = 0; i < buttons.evaluate().length; i++) {
            expect(tester.getSize(buttons.at(i)).height, greaterThanOrEqualTo(40), reason: '$type #$i');
          }
        }
      });
    }

    testWidgets('the status options are at least 40 px tall and tell the selected one with a check, not only with color', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo, size: mobile);
      c.read(progressTargetProvider.notifier).select(s.busy.summary);
      await go(tester, c, AppPage.progress);
      await tapKey(tester, 'progress-status-inProgress');
      for (final status in ActivityStatus.values) {
        expect(tester.getSize(find.byKey(Key('progress-status-${status.name}'))).height, greaterThanOrEqualTo(40));
      }
      expect(find.descendant(of: find.byKey(const Key('progress-status-inProgress')), matching: find.byIcon(Icons.check)), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('progress-status-pending')), matching: find.byIcon(Icons.check)), findsNothing);
    });

    testWidgets('the status options are announced as buttons with their selected state', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo, size: desktop);
      final handle = tester.ensureSemantics();
      c.read(progressTargetProvider.notifier).select(s.busy.summary);
      await go(tester, c, AppPage.progress);
      await tapKey(tester, 'progress-status-blocked');
      final blocked = tester.getSemantics(find.byKey(const Key('progress-status-blocked')));
      expect(blocked.flagsCollection.isSelected, isTrue);
      expect(blocked.flagsCollection.isButton, isTrue);
      expect(tester.getSemantics(find.byKey(const Key('progress-status-pending'))).flagsCollection.isSelected, isFalse);
      handle.dispose();
    });
  });

  group('nothing is invented', () {
    for (final screen in screens) {
      testWidgets('${screen.name}: no clock time, no duration and no percentage', (tester) async {
        final s = await scene();
        final c = await pumpApp(tester, s.repo);
        await screen.open(tester, c, s);
        // The moment a record was registered is a real datum the server holds; it is the only place a time may appear
        final moment = RegExp(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}');
        for (final text in textsOf(tester, screen.page)) {
          final rest = text.replaceAll(moment, '');
          expect(rest, isNot(matches(RegExp(r'\d{1,2}:\d{2}'))), reason: text);
          expect(text, isNot(matches(RegExp(r'\d\s?%'))), reason: text);
          expect(text, isNot(matches(RegExp(r'\b\d+\s?(min|h|hs|horas|minutos)\b'))), reason: text);
        }
      });
    }
  });

  group('one main action per screen', () {
    // A main action is a filled button, enabled or not
    int mainActions(WidgetTester tester, Type page) =>
        find.descendant(of: find.byType(page), matching: find.byType(FilledButton)).evaluate().length;

    final expected = <String, int>{
      'lista de actividades': 1,
      'detalle (con bloqueo, continuación y marca de planificación)': 1,
      'detalle de una actividad completada': 1,
      'detalle de una actividad marcada por error': 1,
      'registrar avance': 1,
      'planificar continuación': 1,
      'reactivar actividad': 1,
      'corregir avance': 1,
      'auditoría': 0, // read-only: it offers no action at all
      'planificación': 1,
    };
    for (final screen in screens) {
      testWidgets('${screen.name}: ${expected[screen.name]}', (tester) async {
        final s = await scene();
        final c = await pumpApp(tester, s.repo);
        await screen.open(tester, c, s);
        expect(mainActions(tester, screen.page), expected[screen.name]);
      });
    }

    testWidgets('the detail of a Completada activity makes reactivating the main action, and registering progress a secondary one', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(activityNavProvider.notifier).open(s.done.id, back: AppPage.activities);
      await go(tester, c, AppPage.activityDetail);
      expect(find.descendant(of: find.byKey(const Key('detail-reactivate')), matching: find.byType(FilledButton)), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('detail-register-progress')), matching: find.byType(FilledButton)), findsNothing);
      expect(find.byKey(const Key('detail-register-progress')), findsOneWidget);
    });

    testWidgets('the detail of an activity that is not Completada keeps registering progress as the main action', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.activities);
      await go(tester, c, AppPage.activityDetail);
      expect(find.descendant(of: find.byKey(const Key('detail-register-progress')), matching: find.byType(FilledButton)), findsOneWidget);
      expect(find.byKey(const Key('detail-reactivate')), findsNothing);
    });
  });

  group('nothing is said twice', () {
    testWidgets('the list tells how an activity started once per row', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      await go(tester, c, AppPage.activities);
      expect(find.text('Actividad planificada'), findsNWidgets(2));
      expect(find.text('Actividad no planificada'), findsNothing);
      expect(find.text('No planificada'), findsOneWidget);
    });

    testWidgets('the audit page does not repeat what its subtitle already says', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(auditTargetProvider.notifier).select(type: AuditObjectType.activity, objectId: s.busy.id, title: s.busy.title);
      await go(tester, c, AppPage.audit);
      expect(find.textContaining('quién cambió este registro'), findsNothing);
      expect(find.byKey(const Key('audit-explanation')), findsOneWidget);
      expect(find.textContaining('No es el historial de avances'), findsOneWidget);
    });

    testWidgets('the detail keeps its mark of error, its actions and its audit link each in one place', (tester) async {
      final s = await scene();
      s.repo.markAsError(s.busy.id, reason: 'Duplicada');
      final c = await pumpApp(tester, s.repo);
      c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.logbook);
      await go(tester, c, AppPage.activityDetail);
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(find.byKey(const Key('detail-revert-mark')), findsOneWidget);
      expect(find.byKey(const Key('detail-audit')), findsOneWidget);
      expect(find.textContaining('Motivo: Duplicada'), findsOneWidget);
    });
  });

  group('desktop layout of the detail', () {
    testWidgets('1400 px: the status is a column beside the planning and the history; on a phone it comes first', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo, size: desktop);
      c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.activities);
      await go(tester, c, AppPage.activityDetail);
      final status = tester.getTopLeft(find.byKey(const Key('detail-status')));
      final planning = tester.getTopLeft(find.byKey(const Key('detail-planning-original')));
      expect(status.dx, greaterThan(planning.dx));
      expect(status.dy, lessThan(planning.dy + 200));
    });

    testWidgets('400 px: the status comes first, then the planning, then the history', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo, size: mobile);
      c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.activities);
      await go(tester, c, AppPage.activityDetail);
      final status = tester.getTopLeft(find.byKey(const Key('detail-status'))).dy;
      final planning = tester.getTopLeft(find.byKey(const Key('detail-planning-original'))).dy;
      final history = tester.getTopLeft(find.byKey(Key('detail-progress-${s.entries.first.id}'))).dy;
      expect(status, lessThan(planning));
      expect(planning, lessThan(history));
    });
  });

  group('a form that fails keeps what the person typed', () {
    String typed(WidgetTester tester, String key) => tester.widget<TextField>(find.byKey(Key(key))).controller!.text;

    testWidgets('registrar avance: a validation error keeps the description, a server error keeps everything', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(progressTargetProvider.notifier).select(s.busy.summary);
      await go(tester, c, AppPage.progress);
      await tester.enterText(find.byKey(const Key('progress-description')), 'Avancé con las conclusiones');
      await tapKey(tester, 'progress-submit'); // no status chosen
      expect(find.text('Elige un estado.'), findsOneWidget);
      expect(typed(tester, 'progress-description'), 'Avancé con las conclusiones');

      await tapKey(tester, 'progress-status-blocked');
      await tester.enterText(find.byKey(const Key('progress-reason')), 'Sin acceso');
      s.repo.progressErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await tapKey(tester, 'progress-submit');
      expect(find.byKey(const Key('progress-error')), findsOneWidget);
      expect(typed(tester, 'progress-description'), 'Avancé con las conclusiones');
      expect(typed(tester, 'progress-reason'), 'Sin acceso');
      expect(find.descendant(of: find.byKey(const Key('progress-status-blocked')), matching: find.byIcon(Icons.check)), findsOneWidget);
      expect(find.byKey(const Key('progress-submit')), findsOneWidget); // it can be sent again
    });

    testWidgets('planificar continuación: a server error keeps the description and the date', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(continuationTargetProvider.notifier).select(s.busy.summary);
      await go(tester, c, AppPage.continuation);
      await tester.enterText(find.byKey(const Key('continuation-description')), 'Cerrar las cifras');
      s.repo.continuationErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await tapKey(tester, 'continuation-submit');
      expect(find.byKey(const Key('continuation-error')), findsOneWidget);
      expect(typed(tester, 'continuation-description'), 'Cerrar las cifras');
      expect(find.text(formatShortDate(tomorrow)), findsOneWidget);
    });

    testWidgets('reactivar actividad: a server error keeps the description and the chosen status', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(reactivationTargetProvider.notifier).select(s.done.summary);
      await go(tester, c, AppPage.reactivation);
      await tapKey(tester, 'reactivation-status-inProgress');
      await tester.enterText(find.byKey(const Key('reactivation-description')), 'Retomo las cifras');
      s.repo.reactivationErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await tapKey(tester, 'reactivation-submit');
      expect(find.byKey(const Key('reactivation-error')), findsOneWidget);
      expect(typed(tester, 'reactivation-description'), 'Retomo las cifras');
      expect(find.descendant(of: find.byKey(const Key('reactivation-status-inProgress')), matching: find.byIcon(Icons.check)), findsOneWidget);
    });

    testWidgets('corregir avance: nothing changed and a server error both keep the text', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(correctionTargetProvider.notifier).select(activityId: s.busy.id, progressId: s.entries.last.id);
      await go(tester, c, AppPage.correction);
      await tapKey(tester, 'correction-submit');
      expect(find.byKey(const Key('correction-nothing')), findsOneWidget);
      await tester.enterText(find.byKey(const Key('correction-description')), 'Sin acceso a los datos de tres áreas');
      s.repo.correctionErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await tapKey(tester, 'correction-submit');
      expect(find.byKey(const Key('correction-error')), findsOneWidget);
      expect(typed(tester, 'correction-description'), 'Sin acceso a los datos de tres áreas');
      expect(find.byKey(const Key('correction-nothing')), findsNothing);
    });

    testWidgets('cancelar vuelve a la pantalla de origen sin enviar nada', (tester) async {
      final s = await scene();
      final c = await pumpApp(tester, s.repo);
      c.read(activityNavProvider.notifier).open(s.busy.id, back: AppPage.activities);
      await go(tester, c, AppPage.activityDetail);
      await tapKey(tester, 'detail-register-progress');
      expect(find.byType(ProgressPage), findsOneWidget);
      await tester.enterText(find.byKey(const Key('progress-description')), 'Algo');
      await tapKey(tester, 'progress-cancel');
      expect(find.byType(ActivityDetailPage), findsOneWidget);
      expect(s.repo.progressRequests, isEmpty);
    });
  });

  group('the forms keep their actions together in one strip', () {
    for (final (name, key, submit, cancel) in [
      ('registrar avance', 'progress', 'progress-submit', 'progress-cancel'),
      ('planificar continuación', 'continuation', 'continuation-submit', 'continuation-cancel'),
      ('reactivar actividad', 'reactivation', 'reactivation-submit', 'reactivation-cancel'),
      ('corregir avance', 'correction', 'correction-submit', 'correction-cancel'),
    ]) {
      testWidgets('$name: cancel comes before submit, on the same line, at the end of the card (1400 px)', (tester) async {
        final s = await scene();
        final c = await pumpApp(tester, s.repo);
        final screen = screens.firstWhere((x) => x.name == name);
        await screen.open(tester, c, s);
        final cancelBox = tester.getRect(find.byKey(Key(cancel)));
        final submitBox = tester.getRect(find.byKey(Key(submit)));
        expect(cancelBox.right, lessThan(submitBox.left));
        expect((cancelBox.center.dy - submitBox.center.dy).abs(), lessThan(1));
        // under every field of the form
        final lastField = tester.getRect(find.byKey(Key('$key-description'))).bottom;
        expect(cancelBox.top, greaterThan(lastField));
      });

      testWidgets('$name: on a phone the main action comes first and both take the full width', (tester) async {
        final s = await scene();
        final c = await pumpApp(tester, s.repo, size: mobile);
        final screen = screens.firstWhere((x) => x.name == name);
        await screen.open(tester, c, s);
        await tester.ensureVisible(find.byKey(Key(submit)));
        await tester.pumpAndSettle();
        final cancelBox = tester.getRect(find.byKey(Key(cancel)));
        final submitBox = tester.getRect(find.byKey(Key(submit)));
        expect(submitBox.bottom, lessThanOrEqualTo(cancelBox.top));
        expect(submitBox.width, cancelBox.width);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
