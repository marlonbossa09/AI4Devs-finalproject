"""Errores de las órdenes de provisión (contratos de M1, `docs/api/m1-acceso-usuarios-equipos.md`).

No son errores HTTP (la provisión no tiene endpoints). El mensaje es fijo y nunca incluye credenciales, códigos ni datos
de otras personas.
"""

MENSAJES: dict[str, str] = {
    "OPERADOR_NO_AUTORIZADO": "La persona operadora no está autorizada.",
    "CAMPO_OBLIGATORIO": "Falta un campo obligatorio.",
    "TEXTO_DEMASIADO_LARGO": "El texto supera el máximo permitido.",
    "SOLICITUD_INVALIDA": "La solicitud no es válida.",
    "RECURSO_NO_DISPONIBLE": "El recurso solicitado no existe.",
    "FECHA_EFECTIVA_INVALIDA": "La fecha de inicio debe ser igual o posterior a la fecha actual de la organización.",
    "PERTENENCIA_INVALIDA": "La pertenencia no cumple las reglas del equipo.",
    "IDENTIFICADOR_DUPLICADO": "El identificador de acceso ya existe.",
    "NOMBRE_DE_EQUIPO_DUPLICADO": "Ya existe un equipo con ese nombre en la organización.",
    "ACCESO_YA_DESACTIVADO": "El acceso de la persona ya está desactivado.",
    "CREDENCIAL_NO_VALIDA": "La credencial no cumple la política.",
    "INSTALACION_YA_REALIZADA": "Ya existe al menos una persona operadora: este procedimiento es solo para la primera.",
    "DEMASIADOS_INTENTOS": "Demasiados intentos de autenticación. Vuelva a intentarlo más tarde.",
    "ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE": "El acceso de la persona está desactivado: no se emite ningún código.",
    "TERMINAL_INTERACTIVA_REQUERIDA": "Esta orden muestra un código secreto y solo se ejecuta en una terminal interactiva (entrada y salida).",
    "VERIFICACION_NO_DECLARADA": "La persona operadora no declaró haber verificado la identidad de la persona.",
    "SECRETO_DE_CODIGOS_NO_CONFIGURADO": "Falta CODE_PEPPER: no se pueden emitir códigos.",
    "CODIGO_NO_PRESENTADO": "No se pudo mostrar el código: no se guardó nada. Emita uno nuevo.",
    "CODIGO_NO_CONFIRMADO": "El código mostrado NO es válido: no se pudo confirmar su registro. Emita uno nuevo.",
    "CONEXION_NO_PERMITIDA": "La conexión no es la del rol de provisión con privilegios mínimos.",
}


class ErrorDeProvision(Exception):
    """Una orden rechazada: no modifica datos ni deja entrada de auditoría (la transacción se deshace)."""

    def __init__(self, codigo: str, detalles: list[dict] | None = None) -> None:
        if codigo not in MENSAJES:
            raise ValueError(f"Código de error fuera del catálogo: {codigo}")
        self.codigo = codigo
        self.mensaje = MENSAJES[codigo]
        self.detalles = detalles or []
        super().__init__(codigo)

    def como_dict(self) -> dict:
        return {"error": self.codigo, "mensaje": self.mensaje, "detalles": self.detalles}
