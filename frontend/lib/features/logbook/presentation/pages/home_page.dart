import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/app_shell.dart';
import '../../../../core/utils/dates.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../providers/navigation.dart';
import '../providers/unsaved_changes.dart';
import '../widgets/unsaved_changes_host.dart';
import 'activities_page.dart';
import 'activity_detail_page.dart';
import 'continuation_page.dart';
import 'dashboard_page.dart';
import 'logbook_page.dart';
import 'planning_page.dart';
import 'progress_page.dart';
import 'audit_page.dart';
import 'correction_page.dart';
import 'reactivation_page.dart';
import 'unplanned_page.dart';
import '../../../supervision/presentation/pages/supervision_activity_page.dart';
import '../../../supervision/presentation/pages/supervision_page.dart';
import '../../../team/presentation/pages/team_page.dart';
import '../../../reports/presentation/pages/individual_report_page.dart';
import '../../../reports/presentation/pages/team_report_page.dart';

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
    AppPage.continuation: 'Planificar continuación',
    AppPage.reactivation: 'Reactivar actividad',
    AppPage.correction: 'Corregir avance',
    AppPage.audit: 'Historial de auditoría',
    AppPage.team: 'Mi equipo',
    AppPage.supervision: 'Supervisión del equipo',
    AppPage.supervisionActivity: 'Historial de la actividad',
    AppPage.individualReport: 'Informe individual',
    AppPage.teamReport: 'Informe del equipo',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = ref.watch(currentPageProvider);
    return UnsavedChangesHost(
      child: AppShell(
        items: [
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
          NavItem(
            id: AppPage.team,
            label: 'Mi equipo',
            icon: Icons.groups_outlined,
            itemKey: Key('nav-team'),
          ),
          // Only a supervisor is offered the supervision. The server is the authority: a collaborator who reached the
          // page anyway would get a 403 (and the page itself says it is not available).
          if (session.role == Role.supervisor)
            const NavItem(
              id: AppPage.supervision,
              label: 'Supervisión',
              icon: Icons.fact_check_outlined,
              itemKey: Key('nav-supervision'),
            ),
          // Reports (M5): the individual one is offered to everyone (the server decides whose report each person may ask for);
          // the team one only to a supervisor, and the server is the authority here too.
          const NavItem(
            id: AppPage.individualReport,
            label: 'Informe individual',
            icon: Icons.summarize_outlined,
            itemKey: Key('nav-report'),
          ),
          if (session.role == Role.supervisor)
            const NavItem(
              id: AppPage.teamReport,
              label: 'Informe del equipo',
              icon: Icons.groups_2_outlined,
              itemKey: Key('nav-team-report'),
            ),
        ],
        // The detail belongs to the activities area: that item stays highlighted while it is open
        selected: switch (page) {
          AppPage.activityDetail => AppPage.activities,
          AppPage.supervisionActivity => AppPage.supervision,
          _ => page,
        },
        onSelect: (id) =>
            ref.read(currentPageProvider.notifier).go(id as AppPage),
        userName: session.user.name,
        roleLabel: session.role == Role.supervisor
            ? 'Supervisor'
            : 'Colaborador',
        breadcrumb: _titles[page]!,
        dateLabel: formatTopDate(session.today),
        onLogout: () => ref
            .read(leaveRequestProvider.notifier)
            .request(() => ref.read(authProvider.notifier).logout()),
        child: switch (page) {
          AppPage.dashboard => DashboardPage(session: session),
          AppPage.logbook => const LogbookPage(),
          AppPage.planning => const PlanningPage(),
          AppPage.progress => const ProgressPage(),
          AppPage.activities => const ActivitiesPage(),
          AppPage.activityDetail => const ActivityDetailPage(),
          AppPage.unplanned => const UnplannedPage(),
          AppPage.continuation => const ContinuationPage(),
          AppPage.reactivation => const ReactivationPage(),
          AppPage.correction => const CorrectionPage(),
          AppPage.audit => const AuditPage(),
          AppPage.team => const TeamPage(),
          AppPage.supervision => const SupervisionPage(),
          AppPage.supervisionActivity => const SupervisionActivityPage(),
          AppPage.individualReport => const IndividualReportPage(),
          AppPage.teamReport => const TeamReportPage(),
        },
      ),
    );
  }
}
