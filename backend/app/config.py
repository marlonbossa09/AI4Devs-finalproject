"""Configuración del backend.

Todos los parámetros configurables (límites de texto, duración de sesión, ventana de
idempotencia, costes de Argon2) se leen del entorno. Ningún valor está fijado en el código
(BE-01). Los valores por defecto son de desarrollo y no son reglas del producto.
"""

import ipaddress
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # ``hide_input_in_errors``: un error de configuración no repite el valor recibido (podría ser una URL con credenciales).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    # Solo existen entornos de desarrollo y de pruebas; no hay configuración de producción.
    app_env: Literal["development", "test"] = "development"

    # Nombre del rol de la aplicación: lo usan las migraciones para conceder permisos por tabla
    app_db_role: str = "smartwork_app"
    # Nombre del rol de PROVISIÓN (M1-T2): distinto del propietario y de la aplicación, con los privilegios mínimos de las
    # órdenes de provisión. Las migraciones le conceden permisos por tabla; el rol lo crea quien administra el servidor.
    provision_db_role: str = "smartwork_provision"

    # Segundos máximos para conectar con PostgreSQL y para esperar una conexión libre del pool.
    # Acota también la comprobación /health/ready: una base caída responde 503 en vez de colgarse.
    db_connect_timeout_seconds: int = Field(default=3, gt=0)

    database_url: str
    migrations_database_url: str
    # Conexión del rol de provisión (solo la usa la CLI de provisión, nunca la API). Sin valor por defecto.
    provision_database_url: str | None = None
    test_database_url: str | None = None
    test_migrations_database_url: str | None = None
    test_provision_database_url: str | None = None

    # Carpeta del cliente web compilado (flutter build web). Si se indica y existe, FastAPI la sirve
    # en el mismo origen que la API (ADR-002); si no, solo se publica la API.
    web_client_dir: str | None = None

    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Sesión (ADR-002, A9; decisión del 2026-11-17): 1 hora de inactividad y 24 horas de duración total. Configurables.
    session_idle_minutes: int = Field(default=60, gt=0)
    session_absolute_minutes: int = Field(default=1440, gt=0)

    # Cada cuántos segundos se actualiza el último uso de la sesión (para no escribir en cada petición)
    session_touch_seconds: int = Field(default=60, gt=0)
    # Longitudes máximas de entrada del inicio de sesión (evita costes abusivos de hash)
    login_identifier_max_length: int = Field(default=200, gt=0)
    login_password_max_length: int = Field(default=1024, gt=0)
    # Longitud mínima de una contraseña nueva (ADR-002, sección 7). Parámetro configurable.
    password_min_length: int = Field(default=10, gt=0)
    # Pwned Passwords instalado en LOCAL (M1-T8.6; ver app/seguridad/contrasenas_comprometidas.py): directorio con los 1.048.576 archivos de rango SHA-1 que escribe la
    # herramienta oficial de Have I Been Pwned (unos 81 GB) y su ``procedencia.json``. El proyecto no lo incluye; sin directorio, la comprobación está inactiva. Si se indica
    # y la instalación no es completa y válida, la API no arranca.
    compromised_passwords_dir: str | None = None

    # Protección frente a intentos fallidos de autenticación (M1-T7; ADR-002, A9 y A11; decisiones del 2026-11-17).
    # Secreto NUEVO e independiente (no versionado) con el que se calcula el HMAC de los identificadores de control: ni el
    # identificador ni el origen se guardan en claro en los contadores ni en los eventos. Sin él, el inicio de sesión y la CLI se
    # niegan a funcionar (fallo cerrado). Mínimo de 32 caracteres.
    auth_pepper: SecretStr | None = None
    # Códigos de un solo uso de primer acceso y recuperación (M1-T8; ADR-002, A4 y D1 del 2026-11-17). Secreto con el que se calcula el HMAC
    # con el que SOLO se guardan los códigos: INDEPENDIENTE de AUTH_PEPPER (no puede ser el mismo valor), no versionado, mínimo 32 caracteres.
    # No hace falta para arrancar la API; sin él, la generación y la comprobación de códigos se niegan (fallo cerrado).
    code_pepper: SecretStr | None = None
    # Vigencia de un código: 10 minutos con la entrega directa (A4). Máximo 1440 (24 horas, la referencia de ADR-002 para un canal asíncrono).
    code_validity_minutes: int = Field(default=10, gt=0, le=1440)
    # Intentos sin espera, y curva de espera: a partir del intento restringido la espera es ``base * 2 ** (n - 1)`` segundos
    # (30 s, 1, 2, 4, 8, 16, 32 min...) con un máximo de ``login_wait_max_seconds`` (1 hora).
    login_free_attempts: int = Field(default=5, ge=0)
    login_wait_base_seconds: int = Field(default=30, gt=0)
    login_wait_max_seconds: int = Field(default=3600, gt=0)
    # Un contador se olvida tras estas horas sin nuevos intentos.
    login_counter_forget_hours: int = Field(default=24, gt=0)
    # Límites por origen (red): intentos fallidos admitidos en cada ventana. Se descuentan solos al salir de la ventana.
    login_origin_short_attempts: int = Field(default=30, gt=0)
    login_origin_short_window_seconds: int = Field(default=300, gt=0)
    login_origin_long_attempts: int = Field(default=200, gt=0)
    login_origin_long_window_seconds: int = Field(default=3600, gt=0)
    # Proxies de confianza (DT-07): direcciones o redes CIDR cuyas cabeceras ``X-Forwarded-For`` se aceptan. Vacío = ninguna.
    trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Retención técnica de los eventos de autenticación (A11): 30 días iniciales. La base impide borrar antes de 30 días.
    auth_event_retention_days: int = Field(default=30, ge=30)

    text_max_title: int = Field(default=200, gt=0)
    text_max_description: int = Field(default=4000, gt=0)
    text_max_summary: int = Field(default=8000, gt=0)

    idempotency_window_hours: int = Field(default=24, gt=0)

    # Listados (convenciones 6.1 y 9, D-10): valor por defecto y máximo de ``limite``. Valores locales
    # configurables; no son reglas del producto (PA-13).
    pagination_default_limit: int = Field(default=20, gt=0)
    pagination_max_limit: int = Field(default=100, gt=0)
    # Amplitud máxima, en días (extremos incluidos), del rango de fechas laborales de las consultas de M4 (M4-02 y M4-03; convenciones 6.1 y 9; PA-13).
    # 92 días, valor confirmado el 2026-11-17 (D-M4-03): cubre un trimestre y acota el coste y el sondeo. Superarlo es SOLICITUD_INVALIDA con el máximo en ``detalles``.
    query_max_range_days: int = Field(default=92, gt=0)

    # Informes (M5-T4; D-M5-06, valores confirmados el 2026-11-18). Los demás parámetros de D-M5-06 (tokens, plazo, concurrencia) siguen ABIERTOS y NO existen aquí.
    # ``INFORME_HABILITADO`` es falso por defecto: con él desactivado ninguna solicitud ejecuta un generador (RNF-06, D-M5-08).
    informe_habilitado: bool = False
    # Qué generador se usa cuando está habilitado. ``ninguno`` (por defecto): no hay generador. ``simulado``: SOLO desarrollo y pruebas (se rechaza fuera de ellos); nunca se elige solo ni como alternativa
    # silenciosa a un proveedor real no configurado. M5-T5 añadirá la integración real; hoy no existe ningún proveedor.
    informe_generador: Literal["ninguno", "simulado", "ollama", "openrouter"] = "ninguno"
    # Amplitud máxima del período de un informe, en días con AMBOS extremos incluidos: 31. Superarla es INFORME_EXCEDE_LIMITES.
    informe_max_range_days: int = Field(default=31, gt=0)
    # Máximo de hechos (avances autorizados) de UNA SOLICITUD: en el consolidado, de TODAS las personas juntas (no por persona): 400. Superarlo es INFORME_EXCEDE_LIMITES; nada se trunca.
    informe_max_hechos: int = Field(default=400, gt=0)
    # Ollama LOCAL (M5-T5; proveedor confirmado para el desarrollo local el 2026-11-18). Con ``INFORME_GENERADOR=ollama`` los cuatro son OBLIGATORIOS y EXPLÍCITOS (sin valores por defecto): URL (solo la propia máquina:
    # 127.0.0.1, localhost o ::1, con puerto y sin ruta), modelo instalado, tiempo de espera en segundos y ventana de contexto en tokens. NO confirman los parámetros abiertos de D-M5-06 (tokens, plazo total, concurrencia).
    informe_ollama_url: str | None = None
    informe_ollama_modelo: str | None = None
    informe_ollama_timeout_segundos: float | None = Field(default=None, gt=0)
    informe_ollama_num_ctx: int | None = Field(default=None, gt=0)
    # OpenRouter (decisión de la persona responsable, 2026-11-19: modelo gratuito para ver una narrativa real en DESARROLLO, solo con datos FICTICIOS). Con ``INFORME_GENERADOR=openrouter`` los tres son OBLIGATORIOS y
    # EXPLÍCITOS: clave (secreto del entorno, nunca versionado), modelo y plazo en segundos. El destino es fijo (openrouter.ai) y solo se admite en desarrollo y pruebas. NO confirma los parámetros abiertos de D-M5-06.
    informe_openrouter_api_key: SecretStr | None = None
    informe_openrouter_modelo: str | None = None
    informe_openrouter_timeout_segundos: float | None = Field(default=None, gt=0)
    # Reintentos de la generación tras una validación fallida: 0 inicialmente. Hasta que se implementen (M5-T5) solo se admite 0.
    informe_reintentos_validacion: int = Field(default=0, ge=0, le=0)

    argon2_memory_kib: int = Field(default=19456, gt=0)
    argon2_iterations: int = Field(default=2, gt=0)
    argon2_parallelism: int = Field(default=1, gt=0)

    @field_validator("cors_allowed_origins", "trusted_proxies", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("auth_pepper", "code_pepper", mode="before")
    @classmethod
    def _pepper_vacio_es_ausente(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("informe_ollama_url", "informe_ollama_modelo", "informe_ollama_timeout_segundos", "informe_ollama_num_ctx", "informe_openrouter_api_key", "informe_openrouter_modelo", "informe_openrouter_timeout_segundos", mode="before")
    @classmethod
    def _ollama_en_blanco_es_ausente(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _validar_generador_de_informes(self) -> "Settings":
        if self.informe_generador == "simulado" and self.app_env not in ("development", "test"):
            raise ValueError("INFORME_GENERADOR=simulado solo se admite en desarrollo y pruebas")
        if self.informe_generador == "openrouter":
            if self.app_env not in ("development", "test"):
                raise ValueError("INFORME_GENERADOR=openrouter solo se admite en desarrollo y pruebas (datos laborales reales con un LLM: no autorizados)")
            faltan = [nombre for nombre, valor in (("INFORME_OPENROUTER_API_KEY", self.informe_openrouter_api_key), ("INFORME_OPENROUTER_MODELO", self.informe_openrouter_modelo),
                                                   ("INFORME_OPENROUTER_TIMEOUT_SEGUNDOS", self.informe_openrouter_timeout_segundos)) if valor is None]
            if faltan:
                raise ValueError("INFORME_GENERADOR=openrouter exige configurar explícitamente: " + ", ".join(faltan))
        if self.informe_generador == "ollama":
            from app.modulos.informes.destino_local import validar_destino_local
            faltan = [nombre for nombre, valor in (("INFORME_OLLAMA_URL", self.informe_ollama_url), ("INFORME_OLLAMA_MODELO", self.informe_ollama_modelo),
                                                   ("INFORME_OLLAMA_TIMEOUT_SEGUNDOS", self.informe_ollama_timeout_segundos), ("INFORME_OLLAMA_NUM_CTX", self.informe_ollama_num_ctx)) if valor is None]
            if faltan:
                raise ValueError("INFORME_GENERADOR=ollama exige configurar explícitamente: " + ", ".join(faltan))
            validar_destino_local(self.informe_ollama_url)           # solo la propia máquina; el mensaje de error no repite la URL
        return self

    @model_validator(mode="after")
    def _validar_proteccion_de_intentos(self) -> "Settings":
        if self.auth_pepper is not None and len(self.auth_pepper.get_secret_value()) < 32:
            raise ValueError("AUTH_PEPPER debe tener al menos 32 caracteres")
        if self.code_pepper is not None:
            if len(self.code_pepper.get_secret_value()) < 32:
                raise ValueError("CODE_PEPPER debe tener al menos 32 caracteres")
            if self.auth_pepper is not None and self.code_pepper.get_secret_value() == self.auth_pepper.get_secret_value():
                raise ValueError("CODE_PEPPER debe ser un secreto distinto de AUTH_PEPPER")
        if self.login_wait_max_seconds < self.login_wait_base_seconds:
            raise ValueError("LOGIN_WAIT_MAX_SECONDS no puede ser menor que LOGIN_WAIT_BASE_SECONDS")
        if self.login_origin_long_window_seconds < self.login_origin_short_window_seconds:
            raise ValueError("La ventana larga por origen no puede ser menor que la corta")
        for red in self.trusted_proxies:
            try:
                ipaddress.ip_network(red, strict=False)
            except ValueError as error:
                raise ValueError("TRUSTED_PROXIES solo admite direcciones IP o redes CIDR") from error
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
