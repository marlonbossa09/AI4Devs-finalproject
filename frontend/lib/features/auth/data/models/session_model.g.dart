// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'session_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserModel _$UserModelFromJson(Map<String, dynamic> json) =>
    UserModel(id: json['id'] as String, name: json['nombre'] as String);

SessionModel _$SessionModelFromJson(Map<String, dynamic> json) => SessionModel(
  user: UserModel.fromJson(json['persona'] as Map<String, dynamic>),
  role: json['rol_vigente'] as String,
  csrf: json['csrf_token'] as String,
  today: json['fecha_actual'] as String?,
);
