import '../../../../core/utils/dates.dart';

/// The widest period a report may cover, in calendar days with both ends included (D-M5-06, confirmed). The SERVER decides:
/// if it answers `INFORME_EXCEDE_LIMITES` with its own maximum, the screen shows that one. This constant only avoids sending
/// a request that is certain to be rejected.
const maxReportRangeDays = 31;

/// Why a period cannot be asked for, if it cannot (pure rule, no framework).
enum ReportRangeProblem { fromAfterTo, tooWide }

/// Days covered by the period, both ends included.
int reportRangeDays(DateTime from, DateTime to) => dateOnly(to).difference(dateOnly(from)).inDays + 1;

/// `null` when the period can be asked for. Both dates are always required: the screen has no way to leave one empty.
ReportRangeProblem? reportRangeProblem(DateTime from, DateTime to) {
  if (dateOnly(from).isAfter(dateOnly(to))) return ReportRangeProblem.fromAfterTo;
  if (reportRangeDays(from, to) > maxReportRangeDays) return ReportRangeProblem.tooWide;
  return null;
}

String reportRangeMessage(ReportRangeProblem problem) => switch (problem) {
  ReportRangeProblem.fromAfterTo => 'La fecha inicial no puede ser posterior a la final.',
  ReportRangeProblem.tooWide => 'El período de un informe puede abarcar como máximo $maxReportRangeDays días.',
};
