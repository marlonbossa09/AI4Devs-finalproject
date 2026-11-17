# SMARTWORK — Pwned Passwords en local: instalación, verificación y actualización

| Campo | Contenido |
|---|---|
| **Naturaleza** | Guía de operación. No define requisitos: la política de contraseñas está en ADR-002 (sección 7, A8) y en los contratos M1-03b y M1-09b |
| **Fecha** | 2026-11-17 (M1-T8.6) |
| **Fuente** | Pwned Passwords de Have I Been Pwned, elegida por la persona responsable del producto el 2026-11-17 `[CONFIRMADO]` |
| **Frecuencia de actualización** | trimestral `[PROPUESTO]`, pendiente de validación operativa (ver la sección 7) |

## 1. Fuente y términos de uso

- Servicio: <https://haveibeenpwned.com/Passwords>. Documentación de la API: <https://haveibeenpwned.com/API/v3>. Términos: <https://haveibeenpwned.com/termsofuse> (última actualización indicada en ellos: 27 de octubre de 2026; consultados el 2026-11-17).
- Según esos términos, **Pwned Passwords, incluidos sus conjuntos de hashes descargables, puede usarse para cualquier fin lícito, también en productos comerciales**, y **no exige atribución**. No se puede revender ni usar para construir un servicio sustancialmente similar.
- Por eso el conjunto **no se incluye en el repositorio ni se redistribuye con el producto**: cada despliegue lo obtiene de la fuente. El directorio de instalación está en `.gitignore` por defecto solo en la ruta de ejemplo `backend/data/`; si se elige otra ruta fuera del repositorio no hace falta nada.
- La API pública de Pwned Passwords se usa **únicamente al instalar o actualizar**. Durante un canje (primer acceso o recuperación) **no se envía nada a ningún servicio externo**: la comprobación es local.

## 2. Qué se instala y en qué formato

Se instala la versión **SHA-1** en **modo directorio** (el predeterminado de la herramienta oficial):

- Un archivo `<PREFIJO>.txt` por cada uno de los **1.048.576** prefijos hexadecimales de 5 caracteres (`00000` a `FFFFF`, en mayúsculas).
- Cada archivo contiene líneas `<SUFIJO>:<CUENTA>`: el sufijo de 35 caracteres hexadecimales del SHA-1 y las veces que apareció, ordenadas por sufijo y terminadas en CRLF (formato descrito en la documentación de la API y escrito por la herramienta, comprobado con 10 rangos reales).
- La herramienta crea además `sha1.index` (prefijo y ETag de cada rango) para poder actualizar solo lo que cambió. SMARTWORK lo usa solo como huella de la versión instalada.
- **No** se usa el modo de archivo único (`--single`) ni NTLM (`--ntlm`).

Para comprobar una contraseña, SMARTWORK calcula su SHA-1 (UTF-8 tal como llega, sin normalizar), abre el archivo de su prefijo (unos 77 KB) y busca el sufijo con una cuenta mayor que cero. No carga el conjunto en memoria: la lectura y la búsqueda de un rango tardaron unos 0,09 ms con la caché del sistema caliente (medido con un archivo del tamaño real).

## 3. Tamaño y requisitos de operación

Medidos el 2026-11-17 con una muestra aleatoria de 10 rangos reales (77.261 bytes de media por rango, entre 75.644 y 81.286; 1.967 hashes por rango de media):

| Concepto | Valor |
|---|---|
| Tamaño total estimado | **≈ 81 GB** (77.261 B × 1.048.576 rangos) |
| Hashes en el conjunto | ≈ 2.060 millones |
| Archivos | 1.048.576 (más `sha1.index` y `procedencia.json`) |
| Espacio en disco recomendado | al menos 90 GB libres (el sistema de archivos redondea cada archivo a su tamaño de bloque; en bloques de 4 KB suma del orden de 2 GB) |
| Peticiones HTTPS durante la instalación | 1.048.576 (una por rango) |
| Herramienta | `haveibeenpwned-downloader` (herramienta .NET oficial, <https://github.com/HaveIBeenPwned/PwnedPasswordsDownloader>); su documentación pide el SDK de .NET 11 o posterior, o los paquetes autocontenidos que publica |
| Memoria al comprobar | despreciable: se lee un archivo de unos 77 KB por comprobación |
| Tiempo de instalación | **no medido**: depende de la red y del paralelismo (`-p`) |
| Arranque de la API | recorre el directorio para comprobar que están los 1.048.576 rangos (**no medido**; con un disco lento puede tardar) |

**No se instaló en el entorno de desarrollo**: tenía unos 77 GB libres (menos que el conjunto) y no tenía instalado .NET. Allí la comprobación está **inactiva** y se verificó con instalaciones sintéticas completas de 16 rangos en el formato oficial y con un rango real descargado, sin conservarlo.

## 4. Instalación en un despliegue

1. Elegir un directorio fuera del repositorio con 90 GB libres y escribible por quien ejecuta la herramienta. Debe ser legible por el usuario del servicio de la API.
2. Instalar la herramienta: `dotnet tool install --global haveibeenpwned-downloader`.
3. Descargar el conjunto SHA-1 en modo directorio. El primer ciclo es largo; la herramienta verifica cada rango contra la cabecera `Content-MD5` antes de aceptarlo:

   ```
   haveibeenpwned-downloader /ruta/a/pwned-passwords -p 64
   ```

   (Si una descarga inicial se interrumpe, un directorio no vacío sin índice exige `-o` para continuar.)
4. Registrar la procedencia (desde `backend/`). La fuente, la URL y los términos están fijados por SMARTWORK; solo se indica la herramienta con su versión (`dotnet tool list --global`) y la fecha en que se obtuvo:

   ```
   uv run python -m scripts.lista_contrasenas procedencia --dir /ruta/a/pwned-passwords \
       --herramienta "haveibeenpwned-downloader <versión>" --fecha-obtencion AAAA-MM-DD
   ```

5. Verificar (comprueba los 1.048.576 rangos, la procedencia, la huella del índice y el formato de una muestra aleatoria de rangos; no imprime contraseñas):

   ```
   uv run python -m scripts.lista_contrasenas verificar --dir /ruta/a/pwned-passwords --muestra 500
   ```

6. Activar: `COMPROMISED_PASSWORDS_DIR=/ruta/a/pwned-passwords` en la configuración del servicio y reiniciar la API.

## 5. Comportamiento en la API

- **Sin `COMPROMISED_PASSWORDS_DIR`:** la comprobación está **inactiva** (solo rige la longitud mínima de 10) y la API lo avisa al arrancar. No se presenta como protección.
- **Con él:** la API **solo arranca con una instalación completa y válida**: los 1.048.576 rangos presentes, `procedencia.json` completa y, si existe `sha1.index`, con la misma huella que declara la procedencia. **Un subconjunto no se acepta**, tampoco regenerando la procedencia.
- **Primer acceso y recuperación** aplican el mismo control: una contraseña presente en el conjunto da `CONTRASENA_NO_VALIDA` con el motivo `comprometida`, igual con un código válido que con uno inventado, **sin consumir el código** ni revocar sesiones. Los mensajes existentes no cambian.
- Si, ya en marcha, falta o no se puede leer un rango, la comprobación **falla cerrada** (error interno): nunca se da por buena una contraseña que no se pudo comprobar.

## 6. Integridad

- La herramienta oficial verifica cada rango contra `Content-MD5` y lo reemplaza de forma atómica; si no se puede verificar, falla en lugar de aceptar un rango dañado.
- SMARTWORK comprueba la presencia de todos los rangos, la huella de `sha1.index` y, con `verificar`, el formato de una muestra. **No hay una verificación criptográfica de todo el contenido**: en la documentación consultada no se encontró una huella publicada del conjunto completo. Quien necesite más garantías puede repetir `verificar` con una muestra mayor o volver a ejecutar la herramienta (que revalida con ETag).

## 7. Actualización

1. Volver a ejecutar la herramienta sobre el **mismo directorio**: usa los ETag de `sha1.index` y solo descarga los rangos que cambiaron (`--force` los descarga todos).
2. Regenerar la procedencia con la nueva fecha (paso 4 de la instalación), verificar (paso 5) y reiniciar la API (paso 6): el conjunto se lee una sola vez por proceso.
3. **Frecuencia propuesta: trimestral `[PROPUESTO]`, pendiente de validación operativa.** Sin actualizaciones, la cobertura queda fijada en la fecha de obtención. Quien administra el servidor debe lanzar la actualización a mano o con el planificador que elija el despliegue (DT-07); SMARTWORK no programa nada.

## 8. Cobertura y limitaciones

- La cobertura es **la del conjunto a la fecha de obtención** (`procedencia.json`): no incluye filtraciones posteriores hasta actualizar. Que una contraseña no figure no significa que sea buena.
- La búsqueda es **exacta** sobre el SHA-1 de la contraseña tal como se escribió: no detecta variantes, sustituciones ni contraseñas parecidas, y distingue mayúsculas de minúsculas, como el conjunto.
- Una cadena que no es UTF-8 válido no puede estar en el conjunto y no se rechaza por esta vía.
- Solo se comprueba una contraseña nueva en el primer acceso y en la recuperación; no se revisan contraseñas ya establecidas.
- El servicio de Have I Been Pwned no se consulta en tiempo de canje: si el conjunto local no se actualiza, SMARTWORK no se entera de contraseñas nuevas.
- Un fallo de la instalación (un rango dañado o faltante) se detecta al arrancar si falta el archivo, y falla cerrado si desaparece después; un **rango dañado pero presente** solo se detecta con `verificar` (muestra) o al consultarlo.
