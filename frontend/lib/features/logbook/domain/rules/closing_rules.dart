import '../entities/logbook_entities.dart';

/// What a day still needs to be closed (M3-01, RN-21). The server applies the same rules and has the
/// last word; this only lets the screen say what is missing without a useless round trip.
class ClosingConditions {
  const ClosingConditions({required this.hasSummary, required this.hasActivity});

  /// The summary has text: not empty and not only spaces (CA-93, CA-94).
  final bool hasSummary;

  /// At least one valid activity created in the day, or continued in it with a progress entry of
  /// that work date (CA-90, CA-91). A planned continuation does not count (CA-184) and neither does an
  /// activity marked as registered by mistake (CA-283, RN-109).
  final bool hasActivity;

  bool get met => hasSummary && hasActivity;

  /// One clear sentence per missing condition.
  List<String> get missing => [
    if (!hasSummary) 'Falta el resumen de la jornada: escribe un texto y guárdalo.',
    if (!hasActivity) 'Falta una actividad creada en la jornada, o continuada en ella con un avance.',
  ];
}

/// The closing conditions of [day] as it was loaded from the server.
ClosingConditions closingConditions(LogbookDay day) {
  bool createdHere(Activity a) =>
      a.date.year == day.logbook.date.year && a.date.month == day.logbook.date.month && a.date.day == day.logbook.date.day;
  bool continuedHere(Activity a) => day.progress.any((p) => p.activityId == a.id);
  return ClosingConditions(
    hasSummary: day.logbook.summary.trim().isNotEmpty,
    hasActivity: day.activities.any((a) => !a.marked && (createdHere(a) || continuedHere(a))),
  );
}

/// Whether the day can be offered for closing at all: not already closed and not in the future
/// (CA-97). Whether it MEETS the conditions is a different question: [closingConditions].
bool canOfferClosing(Logbook logbook) => !logbook.closed && logbook.dateType != DateType.future;

/// What is wrong with a reopening reason (null = fine). The reason is mandatory (RN-50, CA-100).
String? validateReopenReason(String reason) =>
    reason.trim().isEmpty ? 'Indica el motivo de la reapertura.' : null;

/// What the server said is missing (`CONDICIONES_DE_CIERRE_NO_CUMPLIDAS`), as sentences, from its
/// `detalles`. An unknown detail is ignored: the message never repeats server text.
List<String> missingFromDetails(List<Map<String, dynamic>> details) {
  final conditions = ClosingConditions(
    hasSummary: !details.any((d) => d['campo'] == 'resumen'),
    hasActivity: !details.any((d) => d['campo'] == 'actividades'),
  );
  return conditions.missing;
}
