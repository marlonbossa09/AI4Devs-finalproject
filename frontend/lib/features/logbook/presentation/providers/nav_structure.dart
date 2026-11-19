import 'navigation.dart';

/// The three groups of the sidebar. Pure data: what each page belongs to, and nothing about who may open it (that is the server's call).
enum NavSection {
  work('Mi trabajo'),
  collaboration('Colaboración'),
  reports('Informes');

  const NavSection(this.label);

  final String label;
}

/// Pages that have an item of their own in the sidebar, and the group each one is in.
const topLevelSection = <AppPage, NavSection>{
  AppPage.dashboard: NavSection.work,
  AppPage.logbook: NavSection.work,
  AppPage.activities: NavSection.work,
  AppPage.planning: NavSection.work,
  AppPage.team: NavSection.collaboration,
  AppPage.teamManagement: NavSection.collaboration,
  AppPage.supervision: NavSection.collaboration,
  AppPage.individualReport: NavSection.reports,
  AppPage.teamReport: NavSection.reports,
};

/// Short name of every page, as the sidebar and the breadcrumb call it.
const pageNames = <AppPage, String>{
  AppPage.dashboard: 'Panel principal',
  AppPage.logbook: 'Mi bitácora',
  AppPage.planning: 'Planificación',
  AppPage.progress: 'Registrar avance',
  AppPage.activities: 'Actividades',
  AppPage.activityDetail: 'Detalle de actividad',
  AppPage.continuation: 'Planificar continuación',
  AppPage.reactivation: 'Reactivar actividad',
  AppPage.correction: 'Corregir avance',
  AppPage.audit: 'Historial de auditoría',
  AppPage.team: 'Mi equipo',
  AppPage.teamManagement: 'Gestión del equipo',
  AppPage.supervision: 'Supervisión',
  AppPage.supervisionActivity: 'Historial de la actividad',
  AppPage.individualReport: 'Informe individual',
  AppPage.teamReport: 'Informe del equipo',
};

/// Where a page without an item of its own was opened from (its "back" destination), or null when the page has an item of its own
/// or nothing says where it came from. [back] is what the page's target provider remembered, if anything.
AppPage? parentOf(AppPage page, {AppPage? back}) {
  if (topLevelSection.containsKey(page)) return null;
  return switch (page) {
    // Every detail of a supervised activity belongs to the supervision
    AppPage.supervisionActivity => AppPage.supervision,
    // Everything else about an activity goes back to where the person came from; without a hint, to the activities area
    AppPage.activityDetail => back ?? AppPage.activities,
    _ => back ?? AppPage.activities,
  };
}

/// The page that is "current" in the sidebar for [page]: the page itself when it has an item of its own, otherwise the top-level page its
/// chain of origins ends in. [backOf] says where a page without an item of its own came from.
AppPage navItemFor(AppPage page, AppPage? Function(AppPage page) backOf) {
  var current = page;
  for (var step = 0; step < 8; step++) {
    if (topLevelSection.containsKey(current)) return current;
    final parent = parentOf(current, back: backOf(current));
    if (parent == null || parent == current) break;
    current = parent;
  }
  return topLevelSection.containsKey(current) ? current : AppPage.dashboard;
}
