# SMARTWORK — Decisiones de seguridad y privacidad pendientes (M1 y M5)

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]` |
| **Versión** | 0.2 |
| **Fecha** | 2026-11-06 |

Este documento sustituye a la versión 0.1, que solo identificaba operaciones. Los contratos de M1 están en [m1-acceso-usuarios-equipos.md](m1-acceso-usuarios-equipos.md) y los de M5 en [m5-informes.md](m5-informes.md). Aquí se reúnen las decisiones de seguridad y privacidad que siguen sin resolverse y qué contratos afectan.

## 1. Autenticación y acceso (ADR-002)

| Id | Decisión pendiente | Contratos que afecta |
|---|---|---|
| A2/P1 | Forma operativa de la provisión y autenticación y autorización de la persona operadora (acceso al servidor no equivale a autorización administrativa) | Todas las órdenes de M1 |
| A4 | Caducidad e intentos de los códigos | M1-01a, M1-03a, M1-03b, M1-09a, M1-09b |
| A5 | Procedimiento de verificación de identidad al recuperar | M1-09a |
| A6 | Medio de entrega de los códigos | M1-03a, M1-09a |
| A7 | Quién es la persona operadora y cómo se identifica | Todas las órdenes |
| A8 | Lista de contraseñas conocidas (la longitud mínima está decidida: 10 caracteres, ADR-002 versión 0.4) | M1-03b, M1-09b |
| A9 | Duración de la sesión y límites de intentos de inicio | M1-01a |
| A10 | Regla (RN) de la reactivación administrativa | M1-10 |
| A11 | Registro técnico de eventos de autenticación | M1-01a |
| A12 | Estructuras técnicas `IDENTIDAD`, `SESION`, `CODIGO_UNICO` y `OPERADOR` | Todas las de M1 |
| P5 | Aprobar M1-01c | M1-01c |

## 2. Inteligencia artificial (ADR-003)

| Id | Decisión pendiente | Contratos que afecta |
|---|---|---|
| B1 | Proveedor | Ninguno público; la integración interna |
| B2 | Modelo | Ninguno público |
| B3 | Región y perfil de inferencia | Ninguno público |
| B4 | Modo de retención verificado | Ninguno público; condiciona poder usar el servicio externo (RNF-06) |
| B6 | Exclusión del resumen libre | Confirmada por defecto |
| B7 | País y marco legal | Ninguno público; condiciona el uso del servicio |
| B8, B9 | Límites de consumo, tiempos máximos y reintentos | M5-01, M5-02 (parámetros configurables) |
| P-M5-1 | Catálogo de agregaciones | M5-01, M5-02 |
| P-M5-2 | Registro técnico de generación para el consumo | M5-01, M5-02 |

## 3. Privacidad

- **Existencia de los registros:** respuestas indistinguibles ante registros inexistentes y no autorizados (RNF-13). Queda como riesgo residual una diferencia de tiempos de respuesta.
- **Datos enviados a un servicio externo de IA:** solo registros autorizados y necesarios, con personas seudonimizadas, sin el resumen libre por defecto. Todo envío es una decisión explícita y documentada (CLAUDE.md, sección 6).
- **Credenciales y códigos:** nunca se muestran, se registran ni se guardan en claro (RN-64, RNF-08).
- **Auditoría de provisión:** separada de la consulta funcional; su visibilidad y retención dependen de PA-12 y PA-06 (RN-110).

## 4. Abiertos del alcance que afectan a M1 y M5

PA-04, PA-06, PA-09, PA-12, PA-13, PA-24 y PA-25. PA-26 está resuelto (RN-101). PP-11 (enlace de cada afirmación con sus registros) sigue sin aprobar.
