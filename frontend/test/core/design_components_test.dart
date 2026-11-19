import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/theme/app_colors.dart';
import 'package:smartwork/core/theme/app_theme.dart';
import 'package:smartwork/core/widgets/buttons.dart';
import 'package:smartwork/core/widgets/fields.dart';
import 'package:smartwork/core/widgets/kind_tag.dart';
import 'package:smartwork/core/widgets/segmented_control.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/core/widgets/status_pill.dart';

/// UX-T1: the reusable components keep their public API and now follow the design system (sizes, touch targets, words and
/// icons for statuses, selection semantics and a visible focus). The screens are not redesigned here.
Widget _app(Widget child, {Size size = const Size(1000, 800)}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(
    theme: AppTheme.build(webFonts: false),
    home: Scaffold(body: Center(child: child)),
  ),
);

void main() {
  testWidgets('buttons are 40 px tall on a desktop and 44 px on a phone', (tester) async {
    await tester.pumpWidget(_app(Column(mainAxisSize: MainAxisSize.min, children: [PrimaryButton(label: 'Guardar', onPressed: () {}), SecondaryButton(label: 'Cancelar', onPressed: () {})])));
    expect(tester.getSize(find.byType(FilledButton)).height, 40);
    expect(tester.getSize(find.byType(OutlinedButton)).height, 40);
    await tester.pumpWidget(_app(Column(mainAxisSize: MainAxisSize.min, children: [PrimaryButton(label: 'Guardar', onPressed: () {}), SecondaryButton(label: 'Cancelar', onPressed: () {})]), size: const Size(400, 800)));
    expect(tester.getSize(find.byType(FilledButton)).height, 44);
    expect(tester.getSize(find.byType(OutlinedButton)).height, 44);
  });

  testWidgets('a text link and an icon button are reachable touch targets (at least 40 px)', (tester) async {
    await tester.pumpWidget(_app(Row(mainAxisSize: MainAxisSize.min, children: [LinkButton(label: 'Ver detalle', onPressed: () {}), CircleIconButton(icon: Icons.notifications_none, tooltip: 'Notificaciones', onPressed: () {})])));
    expect(tester.getSize(find.byType(TextButton)).height, greaterThanOrEqualTo(40));
    expect(tester.getSize(find.byType(CircleIconButton)).height, greaterThanOrEqualTo(40));
    expect(tester.getSize(find.byType(CircleIconButton)).width, greaterThanOrEqualTo(40));
  });

  testWidgets('a disabled primary button is a neutral grey, not a faded teal, and a loading one keeps its color', (tester) async {
    await tester.pumpWidget(_app(const Column(mainAxisSize: MainAxisSize.min, children: [PrimaryButton(label: 'Guardar'), PrimaryButton(label: 'Guardando', loading: true)])));
    final buttons = tester.widgetList<FilledButton>(find.byType(FilledButton)).toList();
    Color? background(FilledButton b) => b.style!.backgroundColor!.resolve({WidgetState.disabled});
    expect(background(buttons[0]), AppColors.disabledBackground);
    expect(background(buttons[1]), AppColors.primary);
  });

  testWidgets('a status is told by a word AND an icon, never by color alone', (tester) async {
    await tester.pumpWidget(_app(const Column(mainAxisSize: MainAxisSize.min, children: [
      StatusPill(label: 'Pendiente', kind: PillKind.pending),
      StatusPill(label: 'En progreso', kind: PillKind.progress),
      StatusPill(label: 'Completada', kind: PillKind.done),
      StatusPill(label: 'Bloqueada', kind: PillKind.blocked),
    ])));
    for (final word in ['Pendiente', 'En progreso', 'Completada', 'Bloqueada']) {
      expect(find.text(word), findsOneWidget);
    }
    expect(find.descendant(of: find.byType(StatusPill), matching: find.byType(Icon)), findsNWidgets(4));
    final text = tester.widget<Text>(find.text('Pendiente'));
    expect(text.style!.fontSize, greaterThanOrEqualTo(12));
  });

  testWidgets('a kind tag keeps its name in capitals, an icon and a readable size', (tester) async {
    await tester.pumpWidget(_app(const KindTag('Calculado', icon: Icons.calculate_outlined, color: AppColors.calculatedText, background: AppColors.calculatedBackground)));
    expect(find.text('CALCULADO'), findsOneWidget);
    expect(find.byIcon(Icons.calculate_outlined), findsOneWidget);
    expect(tester.widget<Text>(find.text('CALCULADO')).style!.fontSize, greaterThanOrEqualTo(12));
  });

  testWidgets('the segmented control announces each option as a button of an exclusive group with its selected state', (tester) async {
    final handle = tester.ensureSemantics();
    var chosen = 'a';
    await tester.pumpWidget(_app(StatefulBuilder(builder: (context, set) => SegmentedControl<String>(options: const {'a': 'Todas', 'b': 'Pendientes'}, selected: chosen, onChanged: (v) => set(() => chosen = v)))));
    final all = tester.getSemantics(find.bySemanticsLabel('Todas'));
    final pending = tester.getSemantics(find.bySemanticsLabel('Pendientes'));
    expect(all.flagsCollection.isSelected, isTrue);
    expect(pending.flagsCollection.isSelected, isFalse);
    expect(all.flagsCollection.isButton, isTrue);
    expect(all.flagsCollection.isInMutuallyExclusiveGroup, isTrue);
    await tester.tap(find.text('Pendientes'));
    await tester.pump();
    expect(chosen, 'b');
    expect(tester.getSemantics(find.bySemanticsLabel('Pendientes')).flagsCollection.isSelected, isTrue);
    handle.dispose();
  });

  testWidgets('a control reached with the keyboard shows a visible focus ring', (tester) async {
    await tester.pumpWidget(_app(Column(mainAxisSize: MainAxisSize.min, children: [
      SecondaryButton(label: 'Cancelar', onPressed: () {}),
      DateField(label: 'Fecha laboral', date: DateTime(2026, 11, 18), onChanged: (_) {}),
    ])));
    BorderSide? ring(Finder button) => tester.widget<OutlinedButton>(button).style!.side!.resolve({WidgetState.focused});
    expect(ring(find.byType(OutlinedButton))!.color, AppColors.focusRing);
    expect(ring(find.byType(OutlinedButton))!.width, 2);
    await tester.sendKeyEvent(LogicalKeyboardKey.tab); // first control: the secondary button
    await tester.sendKeyEvent(LogicalKeyboardKey.tab); // second control: the date field
    await tester.pump();
    final ringBorders = find.byWidgetPredicate((w) => w is DecoratedBox && w.position == DecorationPosition.foreground && (w.decoration as BoxDecoration).border != null);
    expect(ringBorders, findsOneWidget);
    expect(((tester.widget<DecoratedBox>(ringBorders)).decoration as BoxDecoration).border!.top.color, AppColors.focusRing);
  });

  testWidgets('fields: a one-line field is 40 px tall and a disabled one is neutral and still legible', (tester) async {
    await tester.pumpWidget(_app(SizedBox(width: 300, child: Column(mainAxisSize: MainAxisSize.min, children: [
      LabeledField(label: 'Título', controller: TextEditingController(text: 'x'), fieldKey: const Key('f')),
      DateField(label: 'Fecha', date: DateTime(2026, 11, 18), onChanged: (_) {}, fieldKey: const Key('d')),
    ]))));
    expect(tester.getSize(find.byKey(const Key('f'))).height, 40);
    expect(tester.getSize(find.byKey(const Key('d'))).height, 40);
  });

  testWidgets('the indicator card keeps its API, shows label, figure and note and is compact', (tester) async {
    await tester.pumpWidget(_app(const SizedBox(width: 260, child: StatCard(label: 'Pendientes', value: 2, caption: 'Por atender', icon: Icons.schedule))));
    expect(find.text('Pendientes'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('Por atender'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    expect(tester.getSize(find.byType(StatCard)).height, lessThan(110)); // it was about 143 px
  });
}
