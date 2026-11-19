import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';
import '../widgets/buttons.dart';

/// Right-hand panel (UX-T2 infrastructure): a header with a title and a close button, a body that scrolls on its own and an optional
/// strip of actions pinned at the bottom. It holds no form and talks to no endpoint: a feature puts its content in [child].
///
/// Behaviour:
/// - **Focus.** When it opens, focus goes to its title (so a screen reader announces it) and Tab then reaches the close button and the
///   content, in that order. When it closes, focus goes back to what had it before (normally the button that opened it).
/// - **Keyboard.** Escape asks to close it. The request goes to [onClose], which decides (it may ask before discarding typed text).
/// - **Semantics.** It is announced as a named region; the page behind it is hidden from assistive technology by [AppShell].
/// - **Phone.** It takes the whole width.
class SidePanel extends StatefulWidget {
  const SidePanel({
    super.key,
    required this.title,
    required this.child,
    required this.onClose,
    this.subtitle,
    this.icon = Icons.add,
    this.actions,
  });

  final String title;
  final String? subtitle;
  final IconData icon;

  /// Content of the body. It scrolls independently of the page.
  final Widget child;

  /// Strip pinned under the body (for example Cancel and Save).
  final Widget? actions;

  /// Called when the user asks to close the panel (the X, Escape or a tap on the scrim).
  final VoidCallback onClose;

  /// Widest the panel gets on a desktop or a tablet.
  static const double maxWidth = 480;

  @override
  State<SidePanel> createState() => _SidePanelState();
}

class _SidePanelState extends State<SidePanel> {
  FocusNode? _opener;
  final _titleFocus = FocusNode(debugLabel: 'side-panel-title');

  @override
  void initState() {
    super.initState();
    // What had the focus when the panel opened gets it back when the panel closes.
    _opener = FocusManager.instance.primaryFocus;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _titleFocus.requestFocus();
    });
  }

  @override
  void dispose() {
    final opener = _opener;
    _titleFocus.dispose();
    if (opener != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (opener.context?.mounted ?? false) opener.requestFocus();
      });
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final mobile = MediaQuery.sizeOf(context).width <= 700;
    return CallbackShortcuts(
      bindings: {const SingleActivator(LogicalKeyboardKey.escape): widget.onClose},
      child: FocusScope(
        child: Semantics(
          container: true,
          explicitChildNodes: true,
          scopesRoute: true,
          namesRoute: true,
          label: widget.title,
          child: Material(
            key: const Key('side-panel'),
            color: AppColors.surface,
            elevation: 8,
            shadowColor: const Color(0x331A3450),
            shape: mobile
                ? const RoundedRectangleBorder()
                : const RoundedRectangleBorder(
                    borderRadius: BorderRadius.only(topLeft: Radius.circular(AppRadius.panel), bottomLeft: Radius.circular(AppRadius.panel)),
                  ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                _Header(
                  title: widget.title,
                  subtitle: widget.subtitle,
                  icon: widget.icon,
                  titleFocus: _titleFocus,
                  onClose: widget.onClose,
                ),
                const Divider(height: 1, thickness: 1, color: AppColors.border),
                Expanded(
                  child: SingleChildScrollView(
                    key: const Key('side-panel-body'),
                    padding: const EdgeInsets.all(AppSpace.xl),
                    child: widget.child,
                  ),
                ),
                if (widget.actions != null)
                  Container(
                    key: const Key('side-panel-actions'),
                    width: double.infinity,
                    padding: const EdgeInsets.all(AppSpace.lg),
                    decoration: const BoxDecoration(
                      color: AppColors.panelFooter,
                      border: Border(top: BorderSide(color: AppColors.border)),
                    ),
                    child: widget.actions,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.title, required this.subtitle, required this.icon, required this.titleFocus, required this.onClose});

  final String title;
  final String? subtitle;
  final IconData icon;
  final FocusNode titleFocus;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpace.xl, AppSpace.lg, AppSpace.lg, AppSpace.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: AppSize.minTouch,
            height: AppSize.minTouch,
            decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(AppRadius.card)),
            child: Icon(icon, size: 20, color: AppColors.primary),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Focus(
              focusNode: titleFocus,
              child: Semantics(
                header: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, key: const Key('side-panel-title'), style: context.heading(AppType.pageTitle, height: 1.25)),
                    if (subtitle != null) ...[
                      const SizedBox(height: AppSpace.xs),
                      Text(subtitle!, style: const TextStyle(fontSize: AppType.body, color: AppColors.muted)),
                    ],
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          CircleIconButton(key: const Key('side-panel-close'), icon: Icons.close, tooltip: 'Cerrar panel', onPressed: onClose),
        ],
      ),
    );
  }
}
