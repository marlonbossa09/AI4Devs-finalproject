import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/app_shell.dart';
import '../../../../core/utils/dates.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../providers/navigation.dart';
import 'activities_page.dart';
import 'activity_detail_page.dart';
import 'dashboard_page.dart';
import 'logbook_page.dart';
import 'planning_page.dart';
import 'progress_page.dart';
import 'unplanned_page.dart';

/// Signed-in area: the app frame with the page chosen in the sidebar.
class HomePage extends ConsumerWidget {
  const HomePage({super.key, required this.session});

  final Session session;

  static const _titles = {
    AppPage.dashboard: 'Panel principal',
    AppPage.logbook: 'Mi bitácora',
    AppPage.planning: 'Planificación',
    AppPage.progress: 'Registrar avance',
    AppPage.activities: 'Mis actividades',
    AppPage.activityDetail: 'Detalle de actividad',
    AppPage.unplanned: 'Actividad no planificada',
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
          id: AppPage.activities,
          label: 'Actividades',
          icon: Icons.checklist_outlined,
          itemKey: Key('nav-activities'),
        ),
        NavItem(
          id: AppPage.planning,
          label: 'Planificación',
          icon: Icons.event_note_outlined,
          itemKey: Key('nav-planning'),
        ),
      ],
      // The detail belongs to the activities area: that item stays highlighted while it is open
      selected: page == AppPage.activityDetail ? AppPage.activities : page,
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
        AppPage.progress => const ProgressPage(),
        AppPage.activities => const ActivitiesPage(),
        AppPage.activityDetail => const ActivityDetailPage(),
        AppPage.unplanned => const UnplannedPage(),
      },
    );
  }
}
