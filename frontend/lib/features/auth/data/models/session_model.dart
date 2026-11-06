import 'package:json_annotation/json_annotation.dart';

import '../../../../core/utils/dates.dart';
import '../../domain/entities/session.dart';

part 'session_model.g.dart';

/// Wire format of the API. The JSON field names are Spanish (the public contract) and are
/// mapped here, so the rest of the app only sees simple English names.
@JsonSerializable(createToJson: false)
class UserModel {
  const UserModel({required this.id, required this.name});

  factory UserModel.fromJson(Map<String, dynamic> json) => _$UserModelFromJson(json);

  final String id;
  @JsonKey(name: 'nombre')
  final String name;

  User toEntity() => User(id: id, name: name);
}

/// Response of M1-01a (login) and M1-01c (current session). `fecha_actual` only comes in the
/// latter.
@JsonSerializable(createToJson: false)
class SessionModel {
  const SessionModel({required this.user, required this.role, required this.csrf, this.today});

  factory SessionModel.fromJson(Map<String, dynamic> json) => _$SessionModelFromJson(json);

  @JsonKey(name: 'persona')
  final UserModel user;
  @JsonKey(name: 'rol_vigente')
  final String role;
  @JsonKey(name: 'csrf_token')
  final String csrf;
  @JsonKey(name: 'fecha_actual')
  final String? today;

  Session toEntity() {
    final date = today;
    if (date == null) {
      throw const FormatException('The session response has no current date');
    }
    return Session(
      user: user.toEntity(),
      role: role == 'supervisor' ? Role.supervisor : Role.collaborator,
      csrf: csrf,
      today: parseDate(date),
    );
  }
}
