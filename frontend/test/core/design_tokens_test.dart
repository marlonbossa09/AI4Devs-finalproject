import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/theme/app_colors.dart';
import 'package:smartwork/core/theme/app_tokens.dart';

/// UX-T1: the legibility of the palette is a property of the design system, so it is checked here, with the WCAG 2.x formula,
/// for every text/background pair in its normal, hover, selected and disabled states.
double _channel(double c) => c <= 0.03928 ? c / 12.92 : math.pow((c + 0.055) / 1.055, 2.4).toDouble();

double _luminance(Color c) => 0.2126 * _channel(c.r) + 0.7152 * _channel(c.g) + 0.0722 * _channel(c.b);

double contrast(Color a, Color b) {
  final la = _luminance(a), lb = _luminance(b);
  final hi = math.max(la, lb), lo = math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}

void main() {
  const text = 4.5; // WCAG AA, normal text
  const component = 3.0; // WCAG AA, graphics and focus indicators

  final textPairs = <String, (Color, Color)>{
    // body text on the two surfaces
    'ink on surface': (AppColors.ink, AppColors.surface),
    'secondary text on surface': (AppColors.textSecondary, AppColors.surface),
    'muted text on surface': (AppColors.muted, AppColors.surface),
    'muted text on background': (AppColors.muted, AppColors.background),
    'faint text (hints) on surface': (AppColors.textFaint, AppColors.surface),
    'faint text (hints) on background': (AppColors.textFaint, AppColors.background),
    'soft text on surface': (AppColors.textSoft, AppColors.surface),
    'label on surface': (AppColors.textLabel, AppColors.surface),
    'error on surface': (AppColors.error, AppColors.surface),
    // buttons: normal, hover, disabled
    'primary button text (normal)': (AppColors.white, AppColors.primary),
    'primary button text (hover)': (AppColors.white, AppColors.primaryHover),
    'primary button text (disabled)': (AppColors.disabledText, AppColors.disabledBackground),
    'secondary button text (normal)': (AppColors.textBody, AppColors.white),
    'secondary button text (hover)': (AppColors.textBody, AppColors.hoverSurface),
    'secondary button text (disabled)': (AppColors.disabledText, AppColors.fieldDisabledBackground),
    'link on surface (normal)': (AppColors.primary, AppColors.surface),
    'link on background (normal)': (AppColors.primary, AppColors.background),
    'link on soft teal (hover overlay)': (AppColors.primaryHover, AppColors.primarySoft),
    'eyebrow on surface': (AppColors.teal, AppColors.surface),
    // fields
    'field text': (AppColors.fieldText, AppColors.white),
    'field text (disabled)': (AppColors.textSecondary, AppColors.fieldDisabledBackground),
    // segmented control: idle and selected
    'segmented idle': (AppColors.muted, const Color(0xFFEEF2F7)),
    'segmented selected': (AppColors.ink, AppColors.white),
    // statuses
    'status pending': (AppColors.pendingText, AppColors.pendingBackground),
    'status in progress': (AppColors.progressText, AppColors.progressBackground),
    'status blocked': (AppColors.blockedText, AppColors.blockedBackground),
    'status done': (AppColors.doneText, AppColors.doneBackground),
    // identification and kinds of content
    'tag unplanned': (AppColors.unplannedText, AppColors.unplannedBackground),
    'tag calculated': (AppColors.calculatedText, AppColors.calculatedBackground),
    'tag recorded': (AppColors.recordedText, AppColors.recordedBackground),
    'tag generated': (AppColors.generatedText, AppColors.generatedBackground),
    'notice': (AppColors.infoText, AppColors.infoBackground),
    // sidebar
    'sidebar item': (AppColors.sidebarText, AppColors.navy),
    'sidebar caption': (AppColors.sidebarCaption, AppColors.navy),
    'sidebar role': (AppColors.sidebarRole, AppColors.navy),
    'sidebar active item': (AppColors.white, AppColors.sidebarActive),
    'sidebar item (hover)': (AppColors.sidebarText, AppColors.sidebarHover),
  };

  for (final entry in textPairs.entries) {
    test('legible text: ${entry.key} reaches 4.5:1', () {
      final (foreground, background) = entry.value;
      expect(contrast(foreground, background), greaterThanOrEqualTo(text), reason: '${entry.key}: ${contrast(foreground, background).toStringAsFixed(2)}:1');
    });
  }

  test('the focus ring is visible on every surface it can appear on (3:1)', () {
    for (final surface in [AppColors.surface, AppColors.background, AppColors.fieldDisabledBackground]) {
      expect(contrast(AppColors.focusRing, surface), greaterThanOrEqualTo(component), reason: 'focus ring on $surface');
    }
    // On the teal primary button the blue ring would be invisible (about 1:1), so that button uses a dark ring: it must stand out
    // against the button itself and against the surface around it.
    expect(contrast(AppColors.focusRing, AppColors.primary), lessThan(component), reason: 'documents why the primary button needs its own ring');
    expect(contrast(AppColors.focusRingOnPrimary, AppColors.primary), greaterThanOrEqualTo(component));
    expect(contrast(AppColors.focusRingOnPrimary, AppColors.surface), greaterThanOrEqualTo(component));
    expect(contrast(AppColors.focusRingOnPrimary, AppColors.background), greaterThanOrEqualTo(component));
  });

  test('the four statuses and the kinds of content never share a color pair', () {
    final pairs = <String, (Color, Color)>{
      'pending': (AppColors.pendingText, AppColors.pendingBackground),
      'progress': (AppColors.progressText, AppColors.progressBackground),
      'blocked': (AppColors.blockedText, AppColors.blockedBackground),
      'done': (AppColors.doneText, AppColors.doneBackground),
      'unplanned': (AppColors.unplannedText, AppColors.unplannedBackground),
      'calculated': (AppColors.calculatedText, AppColors.calculatedBackground),
      'recorded': (AppColors.recordedText, AppColors.recordedBackground),
      'generated': (AppColors.generatedText, AppColors.generatedBackground),
    };
    final seen = <String, String>{};
    for (final entry in pairs.entries) {
      final key = '${entry.value.$1.toARGB32()}/${entry.value.$2.toARGB32()}';
      expect(seen.containsKey(key), isFalse, reason: '${entry.key} repeats the pair of ${seen[key]}');
      seen[key] = entry.key;
    }
  });

  test('teal is the interaction color: no status or kind of content uses it', () {
    for (final color in [
      AppColors.pendingText, AppColors.progressText, AppColors.blockedText, AppColors.doneText,
      AppColors.unplannedText, AppColors.calculatedText, AppColors.recordedText, AppColors.generatedText, AppColors.infoText,
    ]) {
      expect(color, isNot(AppColors.primary));
      expect(color, isNot(AppColors.primaryHover));
    }
  });

  test('the type scale never goes below 12 px and the spacing follows 4/8/12/16/20/24', () {
    expect(AppType.caption, 12);
    expect([AppType.body, AppType.bodyLarge, AppType.cardTitle, AppType.pageTitle, AppType.metric], everyElement(greaterThanOrEqualTo(12)));
    expect([AppSpace.xs, AppSpace.sm, AppSpace.md, AppSpace.lg, AppSpace.xl, AppSpace.xxl], [4, 8, 12, 16, 20, 24]);
    expect([AppRadius.control, AppRadius.card, AppRadius.panel], [8, 12, 16]);
    expect(AppSize.minTouch, greaterThanOrEqualTo(40));
  });
}
