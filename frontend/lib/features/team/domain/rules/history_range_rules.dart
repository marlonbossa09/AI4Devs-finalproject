import '../../../../core/utils/dates.dart';

/// The widest range the history may ask for, in days with both ends included (D-M4-03). It is the server's default
/// (`QUERY_MAX_RANGE_DAYS`); the SERVER decides: if it is configured differently it answers `rango_excede_el_maximo`
/// with its own maximum and the screen shows that one. This constant only avoids sending a request that is certain to
/// be rejected.
const maxHistoryRangeDays = 92;

/// Why a range cannot be sent, if it cannot (pure rule, no framework).
enum HistoryRangeProblem { fromAfterTo, tooWide }

/// Days covered by the range, both ends included.
int rangeDays(DateTime from, DateTime to) => dateOnly(to).difference(dateOnly(from)).inDays + 1;

/// `null` when the range can be sent. Both dates are always required: the screen has no way to leave one empty.
HistoryRangeProblem? historyRangeProblem(DateTime from, DateTime to) {
  if (dateOnly(from).isAfter(dateOnly(to))) return HistoryRangeProblem.fromAfterTo;
  if (rangeDays(from, to) > maxHistoryRangeDays) return HistoryRangeProblem.tooWide;
  return null;
}

String historyRangeMessage(HistoryRangeProblem problem) => switch (problem) {
  HistoryRangeProblem.fromAfterTo => 'La fecha inicial no puede ser posterior a la final.',
  HistoryRangeProblem.tooWide => 'El rango puede abarcar como máximo $maxHistoryRangeDays días.',
};
