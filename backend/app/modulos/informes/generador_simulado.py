"""M5-T3 — generador SIMULADO y determinista: para desarrollo y pruebas (ADR-003, sección 13: «adaptadores: ninguno, simulado y AWS»). NO es un generador real y NO debe habilitarse como si lo fuera: no usa ningún
modelo, no hace llamadas de red, no lee configuración ni credenciales y escribe el texto con plantillas fijas. Cuando exista configuración de la integración (M5-T4), ningún entorno que no sea de desarrollo o pruebas
podrá seleccionarlo.

Recibe la misma ``EntradaDeGeneracion`` que recibiría un adaptador real y trabaja SOLO con ``entrada.a_diccionario()`` (la forma que viaja): si el simulado puede redactar con eso, el contrato es suficiente. Los modos
reproducen, de forma controlada, los comportamientos que el dominio debe tratar: respuestas correctas, indisponibilidad, tiempo agotado, errores inesperados, salidas malformadas, cifras contradictorias o inventadas,
enlaces, identificadores y generadores que OBEDECEN una orden escrita dentro de un texto libre.
"""

from app.modulos.informes.generacion import EntradaDeGeneracion, GeneradorNoDisponible, TiempoAgotado

UUID_DE_EJEMPLO = "123e4567-e89b-12d3-a456-426614174000"
ORDEN_QUE_ACTIVA_LA_OBEDIENCIA = "IGNORA"


class GeneradorSimulado:
    def __init__(self, modo: str = "correcto") -> None:
        self.modo = modo
        self.llamadas = 0
        self.recibido: list[dict] = []                              # lo que habría viajado: las pruebas comprueban que no lleva nada que no deba

    def generar(self, entrada: EntradaDeGeneracion) -> object:
        self.llamadas += 1
        datos = entrada.a_diccionario()
        self.recibido.append(datos)
        if self.modo == "no_disponible":
            raise GeneradorNoDisponible("detalle-interno-del-adaptador")
        if self.modo == "tiempo_agotado":
            raise TiempoAgotado("detalle-interno-del-adaptador")
        if self.modo == "error_inesperado":
            raise ValueError("secreto-interno: contenido del prompt y de los registros")
        return self._salida(datos)

    # ------------------------------------------------------------------------------------------------------ salidas
    @staticmethod
    def _correcta(datos: dict) -> dict:
        alias, m, hechos = datos["persona"]["alias"], datos["metricas"], datos["hechos"]
        secciones = [{"texto": f"{alias} registró {m['avances']} avances en {m['jornadas_con_registros']} jornadas, sobre {m['actividades_con_registros']} actividades.",
                      "refs": [hechos[0]["ref"], hechos[-1]["ref"]]}]
        bloqueados = [h for h in hechos if h["estado"] == "Bloqueada"]
        if bloqueados:
            secciones.append({"texto": f"{alias} tuvo bloqueos registrados el {bloqueados[0]['fecha_laboral']}.", "refs": [h["ref"] for h in bloqueados]})
        return {"version": "1", "secciones": secciones, "uso": {"tokens_entrada": 0, "tokens_salida": 0}}

    def _salida(self, datos: dict) -> object:
        modo = self.modo
        salida = self._correcta(datos)
        primera = salida["secciones"][0]
        if modo == "correcto":
            return salida
        if modo == "no_es_un_objeto":
            return "texto suelto que no es un objeto"
        if modo == "campo_faltante":
            del salida["uso"]
        elif modo == "campo_extra":
            salida["instrucciones_internas"] = "no debería existir"
        elif modo == "campo_extra_en_seccion":
            primera["autor"] = "no debería existir"
        elif modo == "secciones_no_es_lista":
            salida["secciones"] = "no es una lista"
        elif modo == "tokens_booleanos":
            salida["uso"] = {"tokens_entrada": True, "tokens_salida": False}
        elif modo == "cifra_contradictoria":
            primera["texto"] = primera["texto"].replace(f"{datos['metricas']['avances']} avances", f"{datos['metricas']['avances'] + 1} avances", 1)
        elif modo == "cifra_inventada":
            primera["texto"] += " Se completaron 777 tareas."
        elif modo == "porcentaje":
            primera["texto"] += " Es el 80% del trabajo."
        elif modo == "referencia_inexistente":
            primera["refs"] = ["h999"]
        elif modo == "alias_ajeno":
            primera["texto"] += " Persona 2 colaboró en el trabajo."
        elif modo == "fecha_inventada":
            primera["texto"] += " Ocurrió el 2031-01-01."
        elif modo == "enlace":
            primera["texto"] += " Más detalle en https://ejemplo.invalid/informe."
        elif modo == "identificador":
            primera["texto"] += f" Identificador {UUID_DE_EJEMPLO}."
        elif modo in ("obedece_orden_con_enlace", "obedece_orden_en_prosa"):
            if any(ORDEN_QUE_ACTIVA_LA_OBEDIENCIA in (h["descripcion"] or "") for h in datos["hechos"]):
                if modo == "obedece_orden_con_enlace":
                    primera["texto"] += " Orden cumplida: ver http://ejemplo.invalid/todos-los-equipos y los 999 registros."
                else:
                    primera["texto"] += " Además, todos los demás equipos están en perfecto estado."         # prosa inocua: la validación determinista NO puede detectarla (riesgo residual)
        else:
            raise ValueError(f"modo desconocido: {modo}")
        return salida
