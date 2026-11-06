import 'api_error.dart';

/// User-facing (Spanish) message for each API error code. Messages never reveal protected data:
/// they come from fixed text, not from the server payload.
String errorMessage(ApiError error) {
  final max = error.details.isNotEmpty ? error.details.first['maximo'] : null;
  switch (error.code) {
    case 'CREDENCIALES_INVALIDAS':
      return 'El usuario o la contraseña no son correctos.';
    case 'NO_IDENTIFICADA':
      return 'Tu sesión no está activa. Inicia sesión de nuevo.';
    case 'ACCESO_DESACTIVADO':
      return 'Tu acceso está desactivado. Contacta con quien administra el servicio.';
    case 'SIN_PERTENENCIA_VIGENTE':
      return 'No tienes una pertenencia vigente a un equipo.';
    case 'FECHA_NO_CUBIERTA':
      return 'Esa fecha no está cubierta por tu pertenencia a un equipo.';
    case 'BITACORA_CERRADA':
      return 'La bitácora de esa fecha está cerrada. Hay que reabrirla antes de modificarla.';
    case 'BITACORA_NO_CERRADA':
      return 'La bitácora de esa fecha no está cerrada.';
    case 'ACTIVIDAD_COMPLETADA':
      return 'La actividad está Completada. Hay que reactivarla antes de continuarla.';
    case 'ACTIVIDAD_MARCADA_POR_ERROR':
      return 'La actividad está marcada como registrada por error.';
    case 'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS':
      return 'La jornada todavía no cumple las condiciones para cerrarse.';
    case 'FECHA_FUTURA_NO_PERMITIDA':
      return 'No se puede registrar ejecución ni cerrar una jornada de fecha futura.';
    case 'FECHA_NO_FUTURA':
      return 'La continuación planificada debe ser para una fecha posterior a hoy.';
    case 'ESTADO_INVALIDO':
      return 'El estado elegido no es válido.';
    case 'DESCRIPCION_OBLIGATORIA':
      return 'Describe el trabajo realizado.';
    case 'MOTIVO_BLOQUEO_OBLIGATORIO':
      return 'Indica el motivo del bloqueo.';
    case 'MOTIVO_OBLIGATORIO':
      return 'Indica el motivo.';
    case 'RECURSO_NO_DISPONIBLE':
      return 'El recurso solicitado no está disponible.';
    case 'CAMPO_OBLIGATORIO':
      return 'Falta un campo obligatorio.';
    case 'TEXTO_DEMASIADO_LARGO':
      return max != null
          ? 'El texto supera el máximo permitido ($max caracteres).'
          : 'El texto supera el máximo permitido.';
    case 'CLAVE_IDEMPOTENCIA_REUTILIZADA':
      return 'Esta solicitud ya se envió con otros datos. Vuelve a intentarlo.';
    case 'OPERACION_EN_CURSO':
      return 'La operación sigue en curso. Espera un momento antes de reintentar.';
    case 'SOLICITUD_INVALIDA':
    case 'CLAVE_IDEMPOTENCIA_OBLIGATORIA':
      return 'La solicitud no es válida.';
    case ApiError.network:
      return 'No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
    default:
      return 'Se produjo un error inesperado. Inténtalo de nuevo.';
  }
}
