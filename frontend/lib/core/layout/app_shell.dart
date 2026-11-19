import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';
import '../widgets/brand.dart';
import '../widgets/buttons.dart';
import '../widgets/focus_ring.dart';
import 'screen_size.dart';
import 'side_panel.dart';

/// One entry of the sidebar navigation.
class NavItem {
  const NavItem({required this.id, required this.label, required this.icon, this.itemKey});

  final Object id;
  final String label;
  final IconData icon;
  final Key? itemKey;
}

/// A titled group of sidebar entries (MI TRABAJO, COLABORACIÓN, INFORMES). A group without entries is not drawn.
class NavGroup {
  const NavGroup({required this.label, required this.items});

  final String label;
  final List<NavItem> items;
}

/// One step of the breadcrumb. Without [onTap] it is plain text (where you are, or a group); with it, a link to that place.
class BreadcrumbItem {
  const BreadcrumbItem(this.label, {this.onTap});

  final String label;
  final VoidCallback? onTap;
}

/// Page frame of the signed-in area: sidebar, top bar and content (`.app`, `.sidebar`, `.topbar`).
///
/// Generic on purpose: it knows nothing about the features. On desktop (232 px) and tablet (208 px) the sidebar is fixed; on a phone it
/// becomes a drawer opened from the top bar. The top bar is 56 px and shows the breadcrumb and, on a desktop or tablet, the date of the
/// server. A right-hand [sidePanel] can be shown over the content (see [SidePanel]); while it is open the page behind it is out of
/// reach of the keyboard and of assistive technology, and the sidebar stays usable (changing page goes through the same
/// unsaved-text question as always).
class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.groups,
    required this.selected,
    required this.onSelect,
    required this.userName,
    required this.roleLabel,
    required this.breadcrumb,
    required this.dateLabel,
    required this.onLogout,
    required this.child,
    this.sidePanel,
    this.onSidePanelDismiss,
  });

  final List<NavGroup> groups;
  final Object selected;
  final ValueChanged<Object> onSelect;
  final String userName;
  final String roleLabel;
  final List<BreadcrumbItem> breadcrumb;
  final String dateLabel;
  final VoidCallback onLogout;
  final Widget child;

  /// A [SidePanel] to show over the content, or null.
  final Widget? sidePanel;

  /// The user tapped the dimmed area outside the panel.
  final VoidCallback? onSidePanelDismiss;

  static const double desktopSidebarWidth = 232;
  static const double tabletSidebarWidth = 208;
  static const double drawerWidth = 256;
  static const double topBarHeight = 56;
  static const double contentMaxWidth = 1440;

  EdgeInsets _contentPadding(ScreenSize size) => switch (size) {
    ScreenSize.desktop => const EdgeInsets.fromLTRB(32, 24, 32, 56),
    ScreenSize.tablet => const EdgeInsets.fromLTRB(24, 20, 24, 56),
    ScreenSize.mobile => const EdgeInsets.fromLTRB(16, 16, 16, 40),
  };

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final panelOpen = sidePanel != null;
    final page = SingleChildScrollView(
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: contentMaxWidth),
          child: Padding(padding: _contentPadding(size), child: child),
        ),
      ),
    );
    final content = Column(
      children: [
        _TopBar(size: size, breadcrumb: breadcrumb, dateLabel: dateLabel),
        Expanded(
          child: Stack(
            children: [
              // While a panel is open the page behind it cannot be reached with the keyboard or announced.
              Positioned.fill(child: ExcludeFocus(excluding: panelOpen, child: ExcludeSemantics(excluding: panelOpen, child: page))),
              if (panelOpen) ...[
                Positioned.fill(
                  child: ExcludeSemantics(
                    child: GestureDetector(
                      key: const Key('side-panel-scrim'),
                      behavior: HitTestBehavior.opaque,
                      onTap: onSidePanelDismiss,
                      child: const ColoredBox(color: Color(0x4D111F38)),
                    ),
                  ),
                ),
                Positioned(
                  top: 0,
                  bottom: 0,
                  right: 0,
                  width: size.isMobile ? null : SidePanel.maxWidth,
                  left: size.isMobile ? 0 : null,
                  child: _SlideIn(child: sidePanel!),
                ),
              ],
            ],
          ),
        ),
      ],
    );

    Widget sidebar({required VoidCallback? closeDrawer}) => _Sidebar(
      groups: groups,
      selected: selected,
      userName: userName,
      roleLabel: roleLabel,
      onSelect: (id) {
        closeDrawer?.call();
        onSelect(id);
      },
      onLogout: () {
        closeDrawer?.call();
        onLogout();
      },
    );

    if (size.isMobile) {
      return Scaffold(
        drawer: Drawer(
          width: drawerWidth,
          backgroundColor: AppColors.navy,
          shape: const RoundedRectangleBorder(),
          child: Builder(builder: (drawerContext) => sidebar(closeDrawer: () => Navigator.of(drawerContext).pop())),
        ),
        body: content,
      );
    }

    return Scaffold(
      body: Row(
        children: [
          // Two traversal groups so that Tab walks the whole sidebar first and then the top bar and the page (the default reading order
          // would interleave a sidebar entry with every page button that sits at the same height).
          FocusTraversalGroup(child: SizedBox(width: size.isDesktop ? desktopSidebarWidth : tabletSidebarWidth, child: sidebar(closeDrawer: null))),
          Expanded(child: FocusTraversalGroup(child: content)),
        ],
      ),
    );
  }
}

/// Slides its child in from the right (and fades it in) in 180 ms; with reduced motion it just appears.
class _SlideIn extends StatelessWidget {
  const _SlideIn({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) => Opacity(opacity: t, child: Transform.translate(offset: Offset((1 - t) * 32, 0), child: child)),
      child: child,
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.groups,
    required this.selected,
    required this.userName,
    required this.roleLabel,
    required this.onSelect,
    required this.onLogout,
  });

  final List<NavGroup> groups;
  final Object selected;
  final String userName;
  final String roleLabel;
  final ValueChanged<Object> onSelect;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: 'Navegación principal',
      child: Container(
        color: AppColors.navy,
        padding: const EdgeInsets.fromLTRB(AppSpace.md, AppSpace.xl, AppSpace.md, AppSpace.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpace.sm, 0, AppSpace.sm, AppSpace.lg),
              child: Row(
                children: [
                  const LogoMark(size: 34),
                  const SizedBox(width: AppSpace.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('SMARTWORK', style: context.heading(AppType.cardTitle, color: AppColors.white, letterSpacing: 0.3, height: 1.2)),
                        Text(
                          'WORKSPACE',
                          style: TextStyle(fontSize: AppType.caption, letterSpacing: 1.0, color: AppColors.white.withValues(alpha: 0.64)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  for (final group in groups)
                    if (group.items.isNotEmpty) ...[
                      _Caption(group.label),
                      for (final item in group.items)
                        _NavButton(
                          key: item.itemKey,
                          label: item.label,
                          icon: item.icon,
                          active: item.id == selected,
                          onTap: () => onSelect(item.id),
                        ),
                    ],
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.only(top: AppSpace.md),
              decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.sidebarDivider))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm),
                    child: Row(
                      children: [
                        Avatar(name: userName, size: 34),
                        const SizedBox(width: AppSpace.sm + 2),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                userName,
                                key: const Key('who'),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.white),
                              ),
                              Text(roleLabel, key: const Key('role'), style: const TextStyle(fontSize: AppType.caption, color: AppColors.sidebarRole)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _NavButton(key: const Key('logout'), label: 'Cerrar sesión', icon: Icons.logout, active: false, onTap: onLogout),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Caption extends StatelessWidget {
  const _Caption(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    header: true,
    child: Padding(
      padding: const EdgeInsets.fromLTRB(AppSpace.md, AppSpace.lg, AppSpace.md, AppSpace.xs + 2),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: AppColors.sidebarCaption),
      ),
    ),
  );
}

/// One sidebar entry: 40 px tall, announced as a button that is selected when it is the current one, with a light focus ring on the
/// dark background. The current one is told by its background AND its bold, white text, not by color alone.
class _NavButton extends StatelessWidget {
  const _NavButton({super.key, required this.label, required this.icon, required this.active, required this.onTap});

  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Semantics(
        button: true,
        selected: active,
        child: Material(
          color: active ? AppColors.sidebarActive : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.control),
          child: FocusRingInk(
            ringColor: AppColors.accent,
            hoverColor: AppColors.sidebarHover,
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: AppSize.minTouch),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm + 1),
                child: Row(
                  children: [
                    Icon(icon, size: 18, color: active ? AppColors.sidebarActiveIcon : AppColors.sidebarText),
                    const SizedBox(width: AppSpace.md),
                    Expanded(
                      child: Text(
                        label,
                        style: TextStyle(
                          fontSize: AppType.body,
                          fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                          color: active ? AppColors.white : AppColors.sidebarText,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.size, required this.breadcrumb, required this.dateLabel});

  final ScreenSize size;
  final List<BreadcrumbItem> breadcrumb;
  final String dateLabel;

  @override
  Widget build(BuildContext context) {
    final horizontal = switch (size) {
      ScreenSize.desktop => 32.0,
      ScreenSize.tablet => 24.0,
      ScreenSize.mobile => 12.0,
    };
    return Container(
      key: const Key('topbar'),
      height: AppShell.topBarHeight,
      padding: EdgeInsets.symmetric(horizontal: horizontal),
      decoration: const BoxDecoration(color: AppColors.white, border: Border(bottom: BorderSide(color: AppColors.border))),
      child: Row(
        children: [
          if (size.isMobile) ...[
            Builder(
              builder: (scaffoldContext) => CircleIconButton(
                key: const Key('menu-toggle'),
                icon: Icons.menu,
                tooltip: 'Abrir menú',
                onPressed: () => Scaffold.of(scaffoldContext).openDrawer(),
              ),
            ),
            const SizedBox(width: AppSpace.sm),
          ],
          Expanded(child: _Breadcrumb(items: breadcrumb)),
          if (!size.isMobile) ...[
            const SizedBox(width: AppSpace.lg),
            // The date of the SERVER (the working day), not the device's clock
            Container(
              padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(AppRadius.control),
                border: Border.all(color: AppColors.border),
              ),
              child: Text(dateLabel, key: const Key('top-date'), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSecondary)),
            ),
          ],
        ],
      ),
    );
  }
}

/// "Mi espacio / Mi trabajo / Actividades / Detalle de actividad": where you are. The steps with an action are links to that place;
/// the last one is where you are and is not a link. Long names are cut with an ellipsis, never wrapped.
class _Breadcrumb extends StatelessWidget {
  const _Breadcrumb({required this.items});

  final List<BreadcrumbItem> items;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: 'Ruta de navegación',
      child: Row(
        key: const Key('breadcrumb'),
        children: [
          for (var i = 0; i < items.length; i++) ...[
            if (i > 0)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: AppSpace.xs),
                child: Icon(Icons.chevron_right, size: 16, color: AppColors.muted),
              ),
            Flexible(child: _Crumb(item: items[i], isLast: i == items.length - 1)),
          ],
        ],
      ),
    );
  }
}

class _Crumb extends StatelessWidget {
  const _Crumb({required this.item, required this.isLast});

  final BreadcrumbItem item;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final linked = item.onTap != null;
    final text = Text(
      item.label,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(
        fontSize: AppType.caption,
        fontWeight: isLast || linked ? FontWeight.w700 : FontWeight.w400,
        color: linked ? AppColors.primary : (isLast ? AppColors.ink : AppColors.muted),
      ),
    );
    if (!linked) return Semantics(label: isLast ? '${item.label}, página actual' : item.label, excludeSemantics: true, child: text);
    return Semantics(
      button: true,
      child: FocusRingInk(
        onTap: item.onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: AppSize.minTouch),
          child: Center(widthFactor: 1, child: Padding(padding: const EdgeInsets.symmetric(horizontal: AppSpace.xs), child: text)),
        ),
      ),
    );
  }
}
