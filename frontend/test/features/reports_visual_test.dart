import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/widgets/kind_tag.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/presentation/pages/home_page.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/reports/presentation/providers/report_repository.dart';
import 'package:smartwork/features/supervision/presentation/providers/supervision_repository.dart';
import 'package:smartwork/features/team/presentation/providers/team_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import '../helpers/report_fakes.dart';
import '../helpers/supervision_fakes.dart';
import '../helpers/team_fakes.dart';

/// The reports (UX-T8): the visual system of the individual and the team report. The rules of what a report says live in
/// `report_pages_test.dart`; this file covers how it is told apart and laid out: the three kinds of content, the layout at
/// 1400, 900 and 400 px (and a large text size on a phone), the states and what the screens never show.
/// The reports always come from the in-memory fake: no model is ever called.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const phone = Size(400, 900);

final sizes = <String, (Size, double)>{
  '1400 px': (desktop, 1),
  '900 px': (tablet, 1),
  '400 px': (phone, 1),
  '400 px with text scale 1.5': (phone, 1.5),
};

class Rig {
  Rig()
    : reports = FakeReportRepository()
        ..individualAnswer = sampleIndividual()
        ..teamAnswer = sampleTeam();

  final FakeReportRepository reports;
  final FakeLogbookRepository logbook = FakeLogbookRepository();
  final FakeTeamRepository team = FakeTeamRepository();
  final FakeSupervisionRepository supervision = FakeSupervisionRepository();
}

Future<void> pumpApp(WidgetTester tester, Rig rig, {required Role role, required Size size, double textScale = 1}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(rig.logbook),
        teamRepositoryProvider.overrideWithValue(rig.team),
        supervisionRepositoryProvider.overrideWithValue(rig.supervision),
        reportRepositoryProvider.overrideWithValue(rig.reports),
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

Future<void> openIndividual(WidgetTester tester, Rig rig, {required Size size, double textScale = 1, Role role = Role.supervisor, bool submit = true}) async {
  await pumpApp(tester, rig, role: role, size: size, textScale: textScale);
  await tapKey(tester, 'nav-report');
  if (submit) await tapKey(tester, 'report-submit');
}

Future<void> openTeam(WidgetTester tester, Rig rig, {required Size size, double textScale = 1, bool submit = true}) async {
  await pumpApp(tester, rig, role: Role.supervisor, size: size, textScale: textScale);
  await tapKey(tester, 'nav-team-report');
  if (submit) await tapKey(tester, 'team-report-submit');
}

/// Every piece of text on screen (plain and rich), to look for what must never appear.
List<String> allTexts(WidgetTester tester) => [
  for (final w in tester.widgetList<Text>(find.byType(Text))) w.data ?? w.textSpan?.toPlainText() ?? '',
];

final _clockTime = RegExp(r'\b\d{1,2}:\d{2}\b');

/// The kinds of content told by name: a tag with its word and its icon, each with its own colors.
void expectThreeKindsDistinct(WidgetTester tester) {
  final tags = {for (final t in tester.widgetList<KindTag>(find.byType(KindTag))) t.text: t};
  expect(tags.keys.toSet(), {'Calculado', 'Registrado', 'Redactado con IA'});
  expect(find.text('CALCULADO'), findsWidgets);
  expect(find.text('REGISTRADO'), findsWidgets);
  expect(find.text('REDACTADO CON IA'), findsWidgets);
  expect({for (final t in tags.values) t.background}.length, 3, reason: 'each kind has its own background');
  expect({for (final t in tags.values) t.color}.length, 3, reason: 'each kind has its own text color');
  expect({for (final t in tags.values) t.icon}.length, 3, reason: 'each kind has its own icon');
  // and the icon is really drawn beside the word
  for (final name in ['CALCULADO', 'REGISTRADO', 'REDACTADO CON IA']) {
    final tag = find.ancestor(of: find.text(name).first, matching: find.byType(KindTag));
    expect(find.descendant(of: tag, matching: find.byType(Icon)), findsOneWidget, reason: name);
  }
}

void expectNothingInvented(WidgetTester tester) {
  for (final text in allTexts(tester)) {
    expect(text.contains('%'), false, reason: 'no percentage: "$text"');
    for (final word in ['ranking', 'Ranking', 'puntuación', 'Puntuación', 'rendimiento', 'Rendimiento', 'mejor', 'peor', 'Exportar', 'Descargar', 'Imprimir', 'PDF']) {
      expect(text.contains(word), false, reason: '"$word" in "$text"');
    }
  }
  // The only moment on screen is the one of generation, inside the period line; nothing else carries a clock time
  for (final w in tester.widgetList<Text>(find.byType(Text))) {
    if (w.key == const Key('report-period')) continue;
    expect(_clockTime.hasMatch(w.data ?? w.textSpan?.toPlainText() ?? ''), false, reason: 'clock time in "${w.data}"');
  }
}

void main() {
  setUpAll(loadTestFonts);

  group('individual report', () {
    for (final entry in sizes.entries) {
      testWidgets('at ${entry.key}: the three kinds are told apart, the narrative is apart and nothing overflows', (tester) async {
        final (size, scale) = entry.value;
        await openIndividual(tester, Rig(), size: size, textScale: scale);
        expect(find.byKey(const Key('report-result')), findsOneWidget);
        expect(tester.takeException(), isNull, reason: 'no overflow');
        expectThreeKindsDistinct(tester);
        // the mandatory base, the figures first, then the records and the blockages, and the narrative last
        expect(find.byKey(const Key('report-base')), findsOneWidget);
        final metrics = tester.getRect(find.byKey(const Key('report-metrics')));
        final facts = tester.getRect(find.byKey(const Key('report-facts')));
        final narrative = tester.getRect(find.byKey(const Key('report-narrative')));
        expect(facts.top, greaterThanOrEqualTo(metrics.bottom), reason: 'the figures come first');
        if (size.width >= 1400) {
          expect(narrative.left, greaterThanOrEqualTo(facts.right), reason: 'the narrative is in its own column');
        } else {
          expect(narrative.top, greaterThanOrEqualTo(tester.getRect(find.byKey(const Key('report-blockages'))).bottom), reason: 'the narrative is last');
        }
        // nothing is cut on the right edge of the screen
        expect(narrative.right, lessThanOrEqualTo(size.width));
        expect(facts.right, lessThanOrEqualTo(size.width));
        expectNothingInvented(tester);
      });
    }

    testWidgets('the narrative holds only generated text and no record; the records hold no generated text', (tester) async {
      await openIndividual(tester, Rig(), size: desktop);
      final narrative = find.byKey(const Key('report-narrative'));
      expect(find.descendant(of: narrative, matching: find.text('REDACTADO CON IA')), findsOneWidget);
      expect(find.descendant(of: narrative, matching: find.text('CALCULADO')), findsNothing);
      expect(find.descendant(of: narrative, matching: find.text('REGISTRADO')), findsNothing);
      expect(find.descendant(of: narrative, matching: find.text('Primer avance del informe')), findsNothing);
      expect(find.descendant(of: narrative, matching: find.byKey(const Key('report-narrative-warning'))), findsOneWidget);
      for (final section in ['report-metrics', 'report-facts', 'report-blockages']) {
        expect(find.descendant(of: find.byKey(Key(section)), matching: find.byKey(const Key('report-narrative-0'))), findsNothing, reason: section);
        expect(find.descendant(of: find.byKey(Key(section)), matching: find.text('REDACTADO CON IA')), findsNothing, reason: section);
      }
      // its own stripe and tint: it is not drawn like the white cards of the records
      final box = tester.widget<Container>(narrative).decoration! as BoxDecoration;
      expect(box.color, isNot(Colors.white));
    });

    testWidgets('the period selection is compact: person, dates and button on one line on a desktop; the button is a real touch target', (tester) async {
      await openIndividual(tester, Rig(), size: desktop, submit: false);
      final person = tester.getRect(find.byKey(const Key('report-person')));
      final from = tester.getRect(find.byKey(const Key('report-from')));
      final to = tester.getRect(find.byKey(const Key('report-to')));
      final submit = tester.getRect(find.byKey(const Key('report-submit')));
      expect((person.center.dy - submit.center.dy).abs(), lessThan(40), reason: 'one line');
      expect(from.right, lessThanOrEqualTo(to.left));
      expect(to.right, lessThanOrEqualTo(submit.left));
      expect(submit.height, greaterThanOrEqualTo(40));
      expect(from.height, greaterThanOrEqualTo(40));
      expect(to.height, greaterThanOrEqualTo(40));
      expect(tester.takeException(), isNull);
    });

    for (final entry in sizes.entries) {
      testWidgets('at ${entry.key}: the form, the empty state and the invalid period fit', (tester) async {
        final (size, scale) = entry.value;
        await openIndividual(tester, Rig(), size: size, textScale: scale, submit: false);
        expect(find.byKey(const Key('report-none')), findsOneWidget);
        expect(find.byKey(const Key('report-hint')), findsOneWidget);
        expect(tester.takeException(), isNull);
        final submit = tester.getRect(find.byKey(const Key('report-submit')));
        expect(submit.right, lessThanOrEqualTo(size.width));
        expect(submit.height, greaterThanOrEqualTo(40));
      });
    }

    for (final entry in sizes.entries) {
      testWidgets('at ${entry.key}: loading and error states fit and show no progress figure and no partial report', (tester) async {
        final (size, scale) = entry.value;
        final rig = Rig()..reports.gate = Completer<void>();
        await openIndividual(tester, rig, size: size, textScale: scale, submit: false);
        await tester.ensureVisible(find.byKey(const Key('report-submit')));
        await tester.tap(find.byKey(const Key('report-submit')));
        await tester.pump();
        expect(find.byKey(const Key('report-generating')), findsOneWidget);
        expect(find.byKey(const Key('report-result')), findsNothing);
        expect(tester.takeException(), isNull);
        expectNothingInvented(tester);
        // it fails: the screen says the report could not be generated and shows nothing of a report
        rig.reports
          ..individualAnswer = notGenerated(retry: true)
          ..gate!.complete();
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('report-error')), findsOneWidget);
        expect(find.text('No se pudo generar el informe'), findsOneWidget);
        expect(find.byKey(const Key('report-retry')), findsOneWidget);
        expect(find.byKey(const Key('report-result')), findsNothing);
        expect(find.byKey(const Key('report-narrative')), findsNothing);
        expect(find.byKey(const Key('report-metrics')), findsNothing);
        expect(find.byKey(const Key('report-facts')), findsNothing);
        expect(find.text('REDACTADO CON IA'), findsNothing);
        expect(tester.takeException(), isNull);
        expectNothingInvented(tester);
      });
    }

    testWidgets('an invalid period is explained with an icon and words, under the form, and nothing is requested', (tester) async {
      final rig = Rig();
      await openIndividual(tester, rig, size: phone, textScale: 1.5, submit: false);
      await tapKey(tester, 'report-from');
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      // from after to
      await tapKey(tester, 'report-to');
      await tester.tap(find.byTooltip('Previous month'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('1').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'report-submit');
      expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(rig.reports.individualRequests, isEmpty);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a period without data keeps the base, shows the empty message and draws no figure, record or narrative', (tester) async {
      final rig = Rig()..reports.individualAnswer = sampleIndividual(noData: true);
      await openIndividual(tester, rig, size: phone, textScale: 1.5);
      expect(find.byKey(const Key('report-base')), findsOneWidget);
      expect(find.byKey(const Key('report-no-data')), findsOneWidget);
      expect(find.byType(KindTag), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });

  group('team report', () {
    for (final entry in sizes.entries) {
      testWidgets('at ${entry.key}: team figures first, each person apart, the three kinds told apart and nothing overflows', (tester) async {
        final (size, scale) = entry.value;
        await openTeam(tester, Rig(), size: size, textScale: scale);
        expect(find.byKey(const Key('team-report-result')), findsOneWidget);
        expect(find.byKey(const Key('team-report-base')), findsOneWidget);
        expect(tester.takeException(), isNull, reason: 'no overflow');
        expectThreeKindsDistinct(tester);
        // team figures before the people, and a person's blocks inside that person's group only
        final team = tester.getRect(find.byKey(const Key('team-metrics')));
        final people = tester.getRect(find.byKey(const Key('team-report-people-title')));
        final first = tester.getRect(find.byKey(const Key('team-report-person-0')));
        final second = tester.getRect(find.byKey(const Key('team-report-person-1')));
        expect(people.top, greaterThanOrEqualTo(team.bottom));
        expect(first.top, greaterThanOrEqualTo(people.bottom));
        expect(second.top, greaterThanOrEqualTo(first.bottom), reason: 'listed in the order given, one after the other');
        expect(first.right, lessThanOrEqualTo(size.width));
        for (var i = 0; i < 2; i++) {
          final person = find.byKey(Key('team-report-person-$i'));
          for (final part in ['metrics', 'facts', 'blockages', 'narrative']) {
            expect(find.descendant(of: person, matching: find.byKey(Key('team-person-$i-$part'))), findsOneWidget, reason: '$part of person $i');
          }
        }
        // the narrative is only per person; the team figures carry no narrative
        expect(find.descendant(of: find.byKey(const Key('team-metrics')), matching: find.text('REDACTADO CON IA')), findsNothing);
        expect(find.text('REDACTADO CON IA'), findsNWidgets(2));
        expect(find.textContaining('no es una clasificación'), findsOneWidget);
        expectNothingInvented(tester);
      });
    }

    for (final entry in sizes.entries) {
      testWidgets('at ${entry.key}: form, empty, loading and error states fit', (tester) async {
        final (size, scale) = entry.value;
        final rig = Rig()..reports.gate = Completer<void>();
        await openTeam(tester, rig, size: size, textScale: scale, submit: false);
        expect(find.byKey(const Key('team-report-none')), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.byKey(const Key('team-report-submit')));
        await tester.tap(find.byKey(const Key('team-report-submit')));
        await tester.pump();
        expect(find.byKey(const Key('report-generating')), findsOneWidget);
        expect(tester.takeException(), isNull);
        rig.reports
          ..teamAnswer = notGenerated(retry: false)
          ..gate!.complete();
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('report-error')), findsOneWidget);
        expect(find.text('No se pudo generar el informe'), findsOneWidget);
        expect(find.byKey(const Key('report-retry')), findsNothing);
        expect(find.byKey(const Key('team-report-result')), findsNothing);
        expect(find.byType(KindTag), findsNothing, reason: 'no part of a report is shown when it could not be generated');
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('a team without entries keeps the base and shows no person', (tester) async {
      final rig = Rig()..reports.teamAnswer = sampleTeam(noData: true);
      await openTeam(tester, rig, size: phone, textScale: 1.5);
      expect(find.byKey(const Key('team-report-base')), findsOneWidget);
      expect(find.byKey(const Key('team-report-no-data')), findsOneWidget);
      expect(find.byKey(const Key('team-report-person-0')), findsNothing);
      expect(find.byType(KindTag), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a collaborator who reaches the page sees it is not available, with nothing to request', (tester) async {
      final rig = Rig();
      await pumpApp(tester, rig, role: Role.collaborator, size: phone, textScale: 1.5);
      ProviderScope.containerOf(tester.element(find.byType(HomePage))).read(currentPageProvider.notifier).go(AppPage.teamReport);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('team-report-not-available')), findsOneWidget);
      expect(find.byKey(const Key('team-report-submit')), findsNothing);
      expect(rig.reports.teamRequests, isEmpty);
      expect(tester.takeException(), isNull);
    });
  });
}
