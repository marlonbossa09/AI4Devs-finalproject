import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/brand.dart';
import '../widgets/buttons.dart';
import 'screen_size.dart';

/// One entry of the sidebar navigation.
class NavItem {
  const NavItem({required this.id, required this.label, required this.icon, this.itemKey});

  final Object id;
  final String label;
  final IconData icon;
  final Key? itemKey;
}

/// Page frame of the signed-in area: sidebar, top bar and content (`.app`, `.sidebar`, `.topbar`).
///
/// Generic on purpose: it knows nothing about the features. On desktop and tablet the sidebar is
/// fixed; on mobile it becomes a drawer opened from the top bar.
class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.items,
    required this.selected,
    required this.onSelect,
    required this.userName,
    required this.roleLabel,
    required this.breadcrumb,
    required this.dateLabel,
    required this.onLogout,
    required this.child,
  });

  final List<NavItem> items;
  final Object selected;
  final ValueChanged<Object> onSelect;
  final String userName;
  final String roleLabel;
  final String breadcrumb;
  final String dateLabel;
  final VoidCallback onLogout;
  final Widget child;

  EdgeInsets _contentPadding(ScreenSize size) => switch (size) {
    ScreenSize.desktop => const EdgeInsets.fromLTRB(42, 34, 42, 70),
    ScreenSize.tablet => const EdgeInsets.fromLTRB(24, 26, 24, 70),
    ScreenSize.mobile => const EdgeInsets.fromLTRB(16, 22, 16, 70),
  };

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final content = Column(
      children: [
        _TopBar(size: size, breadcrumb: breadcrumb, dateLabel: dateLabel, userName: userName),
        Expanded(
          child: SingleChildScrollView(
            child: Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1350),
                child: Padding(padding: _contentPadding(size), child: child),
              ),
            ),
          ),
        ),
      ],
    );

    if (size.isMobile) {
      return Scaffold(
        drawer: Drawer(
          width: 246,
          backgroundColor: AppColors.navy,
          shape: const RoundedRectangleBorder(),
          child: Builder(
            builder: (drawerContext) => _Sidebar(
              items: items,
              selected: selected,
              userName: userName,
              roleLabel: roleLabel,
              onSelect: (id) {
                Navigator.of(drawerContext).pop();
                onSelect(id);
              },
              onLogout: () {
                Navigator.of(drawerContext).pop();
                onLogout();
              },
            ),
          ),
        ),
        body: content,
      );
    }

    return Scaffold(
      body: Row(
        children: [
          SizedBox(
            width: size.isDesktop ? 246 : 215,
            child: _Sidebar(
              items: items,
              selected: selected,
              userName: userName,
              roleLabel: roleLabel,
              onSelect: onSelect,
              onLogout: onLogout,
            ),
          ),
          Expanded(child: content),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.items,
    required this.selected,
    required this.userName,
    required this.roleLabel,
    required this.onSelect,
    required this.onLogout,
  });

  final List<NavItem> items;
  final Object selected;
  final String userName;
  final String roleLabel;
  final ValueChanged<Object> onSelect;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.navy,
      padding: const EdgeInsets.fromLTRB(16, 27, 16, 27),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 31),
            child: Row(
              children: [
                const LogoMark(),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'SMARTWORK',
                      style: context.heading(16, color: AppColors.white, letterSpacing: 0.3),
                    ),
                    Text(
                      'WORKSPACE',
                      style: TextStyle(
                        fontSize: 10,
                        letterSpacing: 1.2,
                        color: AppColors.white.withValues(alpha: 0.56),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                const _Caption('ESPACIO DE TRABAJO', top: 15),
                for (final item in items)
                  _NavButton(
                    key: item.itemKey,
                    label: item.label,
                    icon: item.icon,
                    active: item.id == selected,
                    onTap: () => onSelect(item.id),
                  ),
                const _Caption('MI CUENTA', top: 15),
                _NavButton(
                  key: const Key('logout'),
                  label: 'Cerrar sesión',
                  icon: Icons.logout,
                  active: false,
                  onTap: onLogout,
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(11, 19, 11, 0),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.sidebarDivider)),
            ),
            child: Row(
              children: [
                Avatar(name: userName),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        userName,
                        key: const Key('who'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: AppColors.white,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        roleLabel,
                        key: const Key('role'),
                        style: const TextStyle(fontSize: 11, color: AppColors.sidebarRole),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Caption extends StatelessWidget {
  const _Caption(this.text, {required this.top});

  final String text;
  final double top;

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(15, top, 15, 12),
    child: Text(
      text,
      style: const TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.7,
        color: AppColors.sidebarCaption,
      ),
    ),
  );
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    super.key,
    required this.label,
    required this.icon,
    required this.active,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Material(
        color: active ? AppColors.sidebarActive : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          hoverColor: AppColors.sidebarHover,
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 18,
                  color: active ? AppColors.sidebarActiveIcon : AppColors.sidebarText,
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: active ? AppColors.white : AppColors.sidebarText,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.size,
    required this.breadcrumb,
    required this.dateLabel,
    required this.userName,
  });

  final ScreenSize size;
  final String breadcrumb;
  final String dateLabel;
  final String userName;

  @override
  Widget build(BuildContext context) {
    final horizontal = switch (size) {
      ScreenSize.desktop => 42.0,
      ScreenSize.tablet => 24.0,
      ScreenSize.mobile => 17.0,
    };
    return Container(
      constraints: const BoxConstraints(minHeight: 77),
      padding: EdgeInsets.symmetric(horizontal: horizontal, vertical: 16),
      decoration: const BoxDecoration(
        color: AppColors.white,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
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
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Text.rich(
              TextSpan(
                style: const TextStyle(fontSize: 12, color: Color(0xFF8592A4)),
                children: [
                  const TextSpan(text: 'Mi espacio'),
                  const TextSpan(
                    text: '  /  ',
                    style: TextStyle(color: Color(0xFFC2CAD5)),
                  ),
                  TextSpan(
                    text: breadcrumb,
                    style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF46546A)),
                  ),
                ],
              ),
              key: const Key('breadcrumb'),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (!size.isMobile) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(9),
                border: Border.all(color: AppColors.border),
              ),
              child: Text(
                dateLabel,
                key: const Key('top-date'),
                style: const TextStyle(fontSize: 12, color: Color(0xFF57697E)),
              ),
            ),
            const SizedBox(width: 16),
          ],
          const CircleIconButton(
            icon: Icons.notifications_none_outlined,
            tooltip: 'Notificaciones no disponibles',
          ),
          const SizedBox(width: 16),
          Avatar(name: userName, size: 35),
        ],
      ),
    );
  }
}
