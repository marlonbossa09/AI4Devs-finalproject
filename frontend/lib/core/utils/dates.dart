/// Work dates (`AAAA-MM-DD`) are calendar dates, not instants. They are represented as UTC
/// midnight so they never shift with the browser time zone. "Today" always comes from the
/// server (the session), never from the device clock.
DateTime parseDate(String value) {
  final parts = value.split('-');
  if (parts.length != 3) throw FormatException('Invalid date: $value');
  return DateTime.utc(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
}

String formatDate(DateTime date) {
  final y = date.year.toString().padLeft(4, '0');
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  return '$y-$m-$d';
}

DateTime addDays(DateTime date, int days) => DateTime.utc(date.year, date.month, date.day + days);

DateTime dateOnly(DateTime date) => DateTime.utc(date.year, date.month, date.day);

const _weekdays = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const _months = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

String _capital(String text) => text[0].toUpperCase() + text.substring(1);

/// e.g. "viernes 6 de noviembre de 2026"
String formatLongDate(DateTime date) =>
    '${_weekdays[date.weekday - 1]} ${date.day} de ${_months[date.month - 1]} de ${date.year}';

/// e.g. "Viernes, 6 de noviembre de 2026"
String formatTopDate(DateTime date) =>
    '${_capital(_weekdays[date.weekday - 1])}, ${date.day} de ${_months[date.month - 1]} de ${date.year}';

/// e.g. "Noviembre de 2026"
String formatMonth(DateTime date) => '${_capital(_months[date.month - 1])} de ${date.year}';

/// e.g. "06/11/2026"
String formatShortDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';

/// Real moments arrive as ISO 8601 UTC; they are shown in the browser local time.
String formatDateTime(DateTime moment) {
  final local = moment.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(local.day)}/${two(local.month)}/${local.year} ${two(local.hour)}:${two(local.minute)}';
}

/// e.g. "09:15" in the browser local time.
String formatTime(DateTime moment) {
  final local = moment.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(local.hour)}:${two(local.minute)}';
}
