# SMARTWORK: cliente web (Flutter)

Cliente de SMARTWORK en Flutter Web, con Riverpod (estado) y Dio (HTTP). Instalación, arranque y
pruebas: ver el [README principal](../readme.md#14-instrucciones-de-instalación).

## Arquitectura

Arquitectura limpia por funcionalidad. Código e identificadores en inglés y con nombres simples
(`user`, `password`, `name`, `status`, `date`, `activity`, `logbook`, `planning`); los campos JSON
conservan los nombres en español de los contratos de la API, con su mapeo en `data/models`.

```text
lib/
├── config/          Configuración (URL de la API por --dart-define=API_BASE_URL)
├── core/
│   ├── network/     Cliente HTTP (Dio)
│   ├── errors/      Errores de la API y sus mensajes
│   ├── utils/       Fechas y claves
│   ├── theme/       Colores y tema (DM Sans y Manrope)
│   ├── layout/      Barra lateral y superior responsive, breakpoints y rejilla
│   └── widgets/     Componentes reutilizables (tarjetas, botones, campos, indicadores...)
└── features/
    ├── auth/        Sesión: iniciar, cerrar y consultar (M1-01a/b/c)
    └── logbook/     Bitácora: consultar, abrir y crear una actividad planificada (M2-01a/b, M2-03)
        ├── data/          models, remote, repository (implementa el contrato del dominio)
        ├── domain/        entities y repository (contrato); sin Flutter ni Dio
        └── presentation/  providers (Riverpod), pages (dashboard, logbook, planning) y widgets
```

El diseño sigue el prototipo `smartwork_design_proposal.html`. Los componentes de `core/widgets`
no conocen las funcionalidades; la barra lateral (`core/layout/app_shell.dart`) tampoco.

## Código generado

Los archivos `*.g.dart` (Riverpod y JSON) **están versionados**. Tras cambiar un modelo o un
proveedor, regenerarlos:

```bash
dart run build_runner build --delete-conflicting-outputs
```

## Comandos

```bash
flutter pub get
flutter analyze
flutter test
flutter build web --release   # lo sirve FastAPI en el mismo origen que la API
```
