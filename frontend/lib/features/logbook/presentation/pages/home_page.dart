import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/app_shell.dart';
import '../../../../core/utils/dates.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../providers/navigation.dart';
import 'dashboard_page.dart';
import 'logbook_page.dart';
import 'planning_page.dart';

/// Signed-in area: the app frame with the page chosen in the sidebar.
class HomePage extends ConsumerWidget {
  const HomePage({super.key, required this.session});

  final Session session;

  static const _titles = {
    AppPage.dashboard: 'Panel principal',
    AppPage.logbook: 'Mi bitácora',
    AppPage.planning: 'Planificación',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = ref.watch(currentPageProvider);
    return AppShell(
      items: const [
        NavItem(
          id: AppPage.dashboard,
          label: 'Panel principal',
          icon: Icons.space_dashboard_outlined,
          itemKey: Key('nav-dashboard'),
        ),
        NavItem(
          id: AppPage.logbook,
          label: 'Mi bitácora',
          icon: Icons.menu_book_outlined,
          itemKey: Key('nav-logbook'),
        ),
        NavItem(
          id: AppPage.planning,
          label: 'Planificación',
          icon: Icons.event_note_outlined,
          itemKey: Key('nav-planning'),
        ),
      ],
      selected: page,
      onSelect: (id) => ref.read(currentPageProvider.notifier).go(id as AppPage),
      userName: session.user.name,
      roleLabel: session.role == Role.supervisor ? 'Supervisor' : 'Colaborador',
      breadcrumb: _titles[page]!,
      dateLabel: formatTopDate(session.today),
      onLogout: () => ref.read(authProvider.notifier).logout(),
      child: switch (page) {
        AppPage.dashboard => DashboardPage(session: session),
        AppPage.logbook => const LogbookPage(),
        AppPage.planning => const PlanningPage(),
      },
    );
  }
}
