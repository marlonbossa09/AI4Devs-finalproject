import '../entities/report_entities.dart';

/// Generation of reports (M5-01 and M5-02). Both are POST requests that READ: they change nothing and keep nothing on the
/// server (RN-56). Generating can take from tens of seconds to several minutes with a local model, and each call may cost:
/// the app asks once per user action and never repeats a request by itself.
abstract interface class ReportRepository {
  /// The report of one person for the period [from]-[to], both included. [personId] null is the signed-in user.
  Future<IndividualReport> generateIndividual({required DateTime from, required DateTime to, String? personId});

  /// The report of the team the user supervises for the period [from]-[to], both included.
  Future<TeamReport> generateTeam({required DateTime from, required DateTime to});
}
