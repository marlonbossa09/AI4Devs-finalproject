import 'api_error.dart';

/// User-facing (Spanish) message for each API error code. Messages never reveal protected data:
/// they come from fixed text, not from the server payload.
String errorMessage(ApiError error) {
  final max = error.details.isNotEmpty ? error.details.first['maximo'] : null;
  switch (error.code) {
    case 'CREDENCIALES_INVALIDAS':
      return 'El usuario o la contraseña no son correctos.';
    case ApiError.tooManyRequests:
      // Fixed text: it never says whether the user exists or how many attempts are left.
      return 'Demasiados intentos. Espera un momento antes de volver a intentarlo.';
    case 'CODIGO_NO_VALIDO':
      // One message for every reason (unknown, used, expired, invalidated, someone else's): it never says which.
      return 'El código no es válido o ya no se puede usar. Si lo necesitas, pide uno nuevo a quien administra el servicio.';
    case 'CONTRASENA_NO_VALIDA':
      final reason = error.details.isNotEmpty ? error.details.first['motivo'] : null;
      switch (reason) {
        case 'demasiado_corta':
          return 'La contraseña debe tener al menos 10 caracteres.';
        case 'demasiado_larga':
          return 'La contraseña es demasiado larga.';
        case 'comprometida':
          return 'Esa contraseña no es segura. Elige otra.';
        default:
          return 'La contraseña no cumple los requisitos.';
      }
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
    case 'ACTIVIDAD_NO_COMPLETADA':
      return 'La actividad ya no está Completada, así que no hay nada que reactivar. Se ha actualizado su estado.';
    case 'SECUENCIA_INVALIDA':
      return 'La fecha no puede ser anterior a la de la finalización de la actividad.';
    case 'ACTIVIDAD_MARCADA_POR_ERROR':
      return 'La actividad está marcada como registrada por error.';
    case 'MARCA_NO_PROCEDE':
      return 'No se puede marcar: la actividad tiene avances en jornadas posteriores a la de su origen.';
    case 'MARCA_INVALIDARIA_CIERRE':
      return 'No se puede marcar: una jornada cerrada se quedaría sin ninguna actividad válida. '
          'Reabre esa jornada, marca la actividad y vuelve a cerrarla cuando cumpla las condiciones.';
    case 'MARCA_NO_VIGENTE':
      return 'La actividad ya no tiene una marca de error vigente. Se ha actualizado su estado.';
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
    case 'OPERACION_NO_PERMITIDA':
      return 'Esta operación no está permitida para tu rol.';
    case 'SOLICITUD_INVALIDA':
      // The range of a history query has its own fixed messages; any other invalid request keeps the generic one.
      final reason = error.details.isNotEmpty ? error.details.first['motivo'] : null;
      final maxDays = error.details.isNotEmpty ? error.details.first['maximo_dias'] : null;
      switch (reason) {
        case 'rango_excede_el_maximo':
          return maxDays != null
              ? 'El rango puede abarcar como máximo $maxDays días.'
              : 'El rango de fechas supera el máximo permitido.';
        case 'posterior_a_hasta':
          return 'La fecha inicial no puede ser posterior a la final.';
        case 'obligatorio':
          return 'Indica las fechas desde y hasta.';
        default:
          return 'La solicitud no es válida.';
      }
    case 'INFORME_EXCEDE_LIMITES':
      // Fixed text per limit; the server sends only the maximum (never the real count nor any data of the records).
      final limit = error.details.isNotEmpty ? error.details.first : const <String, dynamic>{};
      switch (limit['motivo']) {
        case 'rango_excede_el_maximo':
          return limit['maximo_dias'] != null
              ? 'El período de un informe puede abarcar como máximo ${limit['maximo_dias']} días. Elige un período más corto.'
              : 'El período supera el máximo permitido. Elige un período más corto.';
        case 'hechos_exceden_el_maximo':
          return limit['maximo_hechos'] != null
              ? 'Ese período tiene más de ${limit['maximo_hechos']} registros, que es el máximo de un informe. Elige un período más corto.'
              : 'Ese período tiene demasiados registros para un informe. Elige un período más corto.';
        default:
          return 'El informe supera un límite. Elige un período más corto.';
      }
    case 'INFORME_NO_GENERADO':
      // The contract distinguishes only whether repeating can help (P-12). It does not say WHY (generation switched off, no
      // provider configured, a technical failure or text that did not pass the checks), so the message does not claim to know.
      return error.retryAllowed == true
          ? 'El informe no pudo generarse en este momento. Puedes intentarlo de nuevo.'
          : 'El informe no pudo generarse y repetir la solicitud con los mismos datos no lo resolverá. '
                'La generación de informes puede no estar disponible, o el texto generado no superó las comprobaciones.';
    case 'CLAVE_IDEMPOTENCIA_OBLIGATORIA':
      return 'La solicitud no es válida.';
    case ApiError.network:
      return 'No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
    default:
      return 'Se produjo un error inesperado. Inténtalo de nuevo.';
  }
}
