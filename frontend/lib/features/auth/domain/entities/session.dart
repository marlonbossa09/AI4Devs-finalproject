/// Role of the user in the current period (RN-11).
enum Role { collaborator, supervisor }

class User {
  const User({required this.id, required this.name});

  final String id;
  final String name;
}

/// An authenticated session as the UI needs it.
class Session {
  const Session({
    required this.user,
    required this.role,
    required this.csrf,
    required this.today,
  });

  final User user;
  final Role role;

  /// Token for requests that modify. Kept in memory only.
  final String csrf;

  /// "Today" according to the server, in the organization time zone (UTC midnight).
  final DateTime today;
}
