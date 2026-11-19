import 'package:flutter/painting.dart';

/// Palette of SMARTWORK (UX-T1). Every text/background pair below was checked against WCAG 2.x (4.5:1 for text);
/// the pairs are asserted in `test/core/design_tokens_test.dart`.
///
/// Reading rules of the palette:
/// - **Teal (`primary`) means "you can interact with this"** (buttons, links, focus of the brand). It is NOT used to say
///   "calculated", "planned" or "informative": those have their own tokens below.
/// - A status or a kind of content is never told by color alone: its component always carries a word (and an icon).
class AppColors {
  const AppColors._();

  // Base
  static const ink = Color(0xFF17253C);
  static const navy = Color(0xFF111F38);
  static const navyLogin = Color(0xFF10223B);
  static const border = Color(0xFFE3E9F1);
  static const background = Color(0xFFF5F7FB);
  static const loginBackground = Color(0xFFF8FAFC);
  static const white = Color(0xFFFFFFFF);
  static const surface = Color(0xFFFFFFFF);

  // Text. `muted`/`textSoft` and `textFaint` are the two lowest-emphasis tones and both stay legible (>= 4.5:1 on white and on `background`).
  static const textSecondary = Color(0xFF475569);
  static const muted = Color(0xFF5B6B80);
  static const textSoft = Color(0xFF5B6B80);
  static const textFaint = Color(0xFF5F6F84);

  // Interaction (teal) and focus
  static const teal = Color(0xFF0E7C75);
  static const primary = Color(0xFF0E7C75);
  static const primaryHover = Color(0xFF0A6A64);
  static const primarySoft = Color(0xFFE5F7F3);
  static const tealSoft = primarySoft;
  static const accent = Color(0xFF57D5C4);
  static const focusRing = Color(0xFF2563EB);
  static const focus = focusRing;
  /// The blue ring has almost no contrast against teal (1.02:1), so a focused primary button draws a dark ring instead.
  static const focusRingOnPrimary = ink;

  // Sidebar (on `navy`)
  static const sidebarText = Color(0xFFAEBED1);
  static const sidebarCaption = Color(0xFF8FA2BD);
  static const sidebarHover = Color(0xFF1B324F);
  static const sidebarActive = Color(0xFF203E56);
  static const sidebarActiveIcon = Color(0xFF60D4C2);
  static const sidebarDivider = Color(0xFF293B54);
  static const sidebarRole = Color(0xFF94A4BC);

  // Avatar and logo
  static const avatarBackground = Color(0xFFCDE5E6);
  static const avatarText = Color(0xFF196F70);
  static const logoFrom = Color(0xFF4FD2BE);
  static const logoTo = Color(0xFF16948B);

  // Text on content and fields
  static const textStrong = Color(0xFF25435B);
  static const textBody = Color(0xFF34465D);
  static const textLabel = Color(0xFF45556B);
  static const fieldBorder = Color(0xFFDFE6EE);
  static const fieldText = Color(0xFF24364A);
  static const fieldDisabledBackground = Color(0xFFF1F5F9);
  static const panelFooter = Color(0xFFFBFCFE);
  static const divider = Color(0xFFF0F2F6);

  // Disabled controls (neutral, never a faded brand color)
  static const disabledBackground = Color(0xFFD5DCE6);
  static const disabledText = Color(0xFF4B5A6E);

  // Hover surfaces
  static const hoverSurface = Color(0xFFF1F5F9);

  // Activity status (amber, blue, green and red; always with their word and an icon)
  static const pendingBackground = Color(0xFFFFF4D6);
  static const pendingText = Color(0xFF8A5A00);
  static const progressBackground = Color(0xFFE8F1FC);
  static const progressText = Color(0xFF1D5FA8);
  static const blockedBackground = Color(0xFFFDECEA);
  static const blockedText = Color(0xFFA63D38);
  static const doneBackground = Color(0xFFE2F6EC);
  static const doneText = Color(0xFF11694F);

  // Identification of an activity: "No planificada" (violet). Planned activities carry no tag.
  static const unplannedBackground = Color(0xFFF1ECFB);
  static const unplannedText = Color(0xFF5B3FA6);

  // Kind of content of a report: told apart by NAME and icon, and by these tones (none is teal or a status color)
  static const calculatedBackground = Color(0xFFE4ECF7);
  static const calculatedText = Color(0xFF284B80);
  static const recordedBackground = Color(0xFFEEF1F6);
  static const recordedText = Color(0xFF3D4A5C);
  static const generatedBackground = Color(0xFFECEEFB);
  static const generatedText = Color(0xFF3F4BA8);

  // Informative notice
  static const infoBackground = Color(0xFFEAF2FC);
  static const infoBorder = Color(0xFFD3E3F8);
  static const infoText = Color(0xFF1D4F91);

  static const error = Color(0xFFA63D38);
  static const toast = Color(0xFF132B42);
}
