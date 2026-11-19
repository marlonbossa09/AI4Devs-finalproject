import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/app_shell.dart';
import '../../../../core/layout/side_panel.dart';
import '../../../../core/utils/dates.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../providers/nav_structure.dart';
import '../providers/navigation.dart';
import '../providers/side_panel.dart';
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
import '../../../supervision/presentation/pages/supervision_activity_page.dart';
import '../../../supervision/presentation/pages/supervision_page.dart';
import '../../../team/presentation/pages/team_page.dart';
import '../../../team_admin/presentation/pages/team_management_page.dart';
import '../../../reports/presentation/pages/individual_report_page.dart';
import '../../../reports/presentation/pages/team_report_page.dart';

/// Signed-in area: the app frame with the page chosen in the sidebar.
///
/// The sidebar is organized in groups (MI TRABAJO, COLABORACIÓN, INFORMES). Showing or hiding an entry by role is only a convenience:
/// the server is the authority and answers 403 or 404 on its own. A page opened from another (a detail, a form) keeps the entry it
/// belongs to highlighted and shows where it came from in the breadcrumb.
class HomePage extends ConsumerWidget {
  const HomePage({super.key, required this.session});

  final Session session;

  /// Where the current page was opened from, as the page's own target provider remembers it.
  AppPage? _backOf(WidgetRef ref, AppPage page) => switch (page) {
    AppPage.progress => ref.watch(progressTargetProvider)?.back,
    AppPage.continuation => ref.watch(continuationTargetProvider)?.back,
    AppPage.reactivation => ref.watch(reactivationTargetProvider)?.back,
    AppPage.correction => ref.watch(correctionTargetProvider)?.back,
    AppPage.audit => ref.watch(auditTargetProvider)?.back,
    AppPage.activityDetail => ref.watch(activityNavProvider)?.back,
    _ => null,
  };

  /// "Mi espacio / (group) / ..." The page you are on is the title of the page itself, so a top-level page is not repeated; a page
  /// opened from another shows the whole path, with every step before the current one a link back to it.
  List<BreadcrumbItem> _breadcrumb(WidgetRef ref, AppPage page) {
    final path = <AppPage>[];
    var current = page;
    for (var step = 0; step < 8; step++) {
      path.add(current);
      final parent = parentOf(current, back: _backOf(ref, current));
      if (parent == null || path.contains(parent)) break;
      current = parent;
    }
    final section = topLevelSection[path.last] ?? NavSection.work;
    final steps = path.reversed.toList();
    return [
      const BreadcrumbItem('Mi espacio'),
      BreadcrumbItem(section.label),
      if (steps.length > 1)
        for (var i = 0; i < steps.length; i++)
          BreadcrumbItem(
            pageNames[steps[i]]!,
            onTap: i == steps.length - 1 ? null : () => ref.read(currentPageProvider.notifier).go(steps[i]),
          ),
    ];
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = ref.watch(currentPageProvider);
    final panel = ref.watch(sidePanelProvider);
    final isSupervisor = session.role == Role.supervisor;
    return UnsavedChangesHost(
      child: AppShell(
        groups: [
          NavGroup(
            label: NavSection.work.label.toUpperCase(),
            items: const [
              NavItem(id: AppPage.dashboard, label: 'Panel principal', icon: Icons.space_dashboard_outlined, itemKey: Key('nav-dashboard')),
              NavItem(id: AppPage.logbook, label: 'Mi bitácora', icon: Icons.menu_book_outlined, itemKey: Key('nav-logbook')),
              NavItem(id: AppPage.activities, label: 'Actividades', icon: Icons.checklist_outlined, itemKey: Key('nav-activities')),
              NavItem(id: AppPage.planning, label: 'Planificación', icon: Icons.event_note_outlined, itemKey: Key('nav-planning')),
            ],
          ),
          NavGroup(
            label: NavSection.collaboration.label.toUpperCase(),
            items: [
              const NavItem(id: AppPage.team, label: 'Mi equipo', icon: Icons.groups_outlined, itemKey: Key('nav-team')),
              // Only a supervisor is offered the supervision. The server is the authority: a collaborator who reached the
              // page anyway would get a 403 (and the page itself says it is not available).
              if (isSupervisor)
                const NavItem(id: AppPage.teamManagement, label: 'Gestión del equipo', icon: Icons.person_add_alt_1_outlined, itemKey: Key('nav-team-management')),
              if (isSupervisor)
                const NavItem(id: AppPage.supervision, label: 'Supervisión', icon: Icons.fact_check_outlined, itemKey: Key('nav-supervision')),
            ],
          ),
          NavGroup(
            label: NavSection.reports.label.toUpperCase(),
            items: [
              // Reports (M5): the individual one is offered to everyone (the server decides whose report each person may ask for);
              // the team one only to a supervisor, and the server is the authority here too.
              const NavItem(id: AppPage.individualReport, label: 'Informe individual', icon: Icons.summarize_outlined, itemKey: Key('nav-report')),
              if (isSupervisor)
                const NavItem(id: AppPage.teamReport, label: 'Informe del equipo', icon: Icons.groups_2_outlined, itemKey: Key('nav-team-report')),
            ],
          ),
        ],
        // A page opened from another keeps highlighted the entry it belongs to (the one its chain of origins ends in)
        selected: navItemFor(page, (p) => _backOf(ref, p)),
        onSelect: (id) => ref.read(currentPageProvider.notifier).go(id as AppPage),
        userName: session.user.name,
        roleLabel: isSupervisor ? 'Supervisor' : 'Colaborador',
        breadcrumb: _breadcrumb(ref, page),
        dateLabel: formatTopDate(session.today),
        onLogout: () => ref.read(leaveRequestProvider.notifier).request(() => ref.read(authProvider.notifier).logout()),
        sidePanel: panel == null
            ? null
            : SidePanel(
                title: panel.title,
                subtitle: panel.subtitle,
                icon: panel.icon,
                onClose: ref.read(sidePanelProvider.notifier).requestClose,
                actions: panel.actionsBuilder == null ? null : Builder(builder: panel.actionsBuilder!),
                child: Builder(builder: panel.bodyBuilder),
              ),
        onSidePanelDismiss: ref.read(sidePanelProvider.notifier).requestClose,
        child: switch (page) {
          AppPage.dashboard => DashboardPage(session: session),
          AppPage.logbook => const LogbookPage(),
          AppPage.planning => const PlanningPage(),
          AppPage.progress => const ProgressPage(),
          AppPage.activities => const ActivitiesPage(),
          AppPage.activityDetail => const ActivityDetailPage(),
          AppPage.continuation => const ContinuationPage(),
          AppPage.reactivation => const ReactivationPage(),
          AppPage.correction => const CorrectionPage(),
          AppPage.audit => const AuditPage(),
          AppPage.team => const TeamPage(),
          AppPage.teamManagement => const TeamManagementPage(),
          AppPage.supervision => const SupervisionPage(),
          AppPage.supervisionActivity => const SupervisionActivityPage(),
          AppPage.individualReport => const IndividualReportPage(),
          AppPage.teamReport => const TeamReportPage(),
        },
      ),
    );
  }
}
