# ADR-001 — Stack tecnológico de SMARTWORK

| | |
|---|---|
| **Estado** | **APROBADO** en D1 a D5 y D7 por la persona responsable del producto. D6 sigue **PROPUESTO**. |
| **Versión** | 0.2 |
| **Fecha** | 2026-11-05 |
| **Relacionado con** | PP-01 (stack propuesto), RNF-05, PA-09, PA-12, PA-13 |
| **Documento complementario** | `docs/arquitectura/arquitectura-general.md` |

Este ADR no decide el mecanismo de acceso (PA-12) ni el proveedor del servicio de IA (PA-09). Tampoco decide el entorno de despliegue.

## 1. Contexto

SMARTWORK es una plataforma web para registrar y consultar bitácoras laborales, con cinco módulos (M1 a M5). Los requisitos que más condicionan la elección técnica son:

| Requisito | Qué exige a la tecnología |
|---|---|
| RNF-05, PP-07 | Plataforma web; aplicación móvil nativa fuera del MVP. |
| RN-15, RN-33 | Una organización con varios equipos, dos roles y provisión administrativa controlada, sin panel avanzado. |
| RN-36, RN-81 a RN-87 | Autorización por registro, según el equipo al que pertenecía el propietario en la fecha laboral. Se aplica por igual a consultas, vistas de supervisión e informes. |
| RN-65, RN-66, RN-44 | Orden determinista de avances, estado actual calculado y fecha laboral según la zona horaria de la organización. |
| RN-45, RN-49 a RN-52, RNF-02 | Auditoría de reaperturas, correcciones y modificaciones de jornadas pasadas; nada se borra silenciosamente. |
| RN-29 a RN-31, RN-55 a RN-58, RNF-12 | Informes con IA: indicadores deterministas, información autorizada y necesaria, texto libre tratado como datos, fallo del servicio sin contenido parcial. |

**Capacidades disponibles.** La persona responsable del producto tiene experiencia práctica desarrollando con Flutter y Dart, FastAPI y Python, PostgreSQL, interfaces REST, Git y entornos de desarrollo con Docker. Esa experiencia es un fundamento de la decisión. **No se asume** que todas las personas que participen en el proyecto tengan las mismas capacidades.

**Lo que sigue sin saberse y este ADR no inventa:** las capacidades de otras personas que se incorporen, el presupuesto, el entorno de despliegue (la experiencia con Docker en desarrollo no lo determina), el volumen esperado (PA-13), el proveedor de IA (PA-09) y el mecanismo de acceso (PA-12).

## 2. Criterios de decisión

| ID | Criterio |
|---|---|
| C1 | Encaje con los requisitos críticos: autorización histórica, auditoría y orden determinista. |
| C2 | Integridad y consistencia transaccional. |
| C3 | Facilidad de pruebas automatizadas, en especial la matriz de permisos y el determinismo. |
| C4 | Integración desacoplada con un servicio de IA. |
| C5 | Mantenibilidad y curva de aprendizaje. |
| C6 | Madurez del ecosistema y disponibilidad de perfiles. |
| C7 | Coste de operación en un MVP. |
| C8 | Seguridad de serie y capacidad de endurecimiento. |
| C9 | Posibilidad de evolución, por ejemplo hacia móvil. |
| C10 | Accesibilidad y experiencia en navegador. |
| C11 | Experiencia práctica de la persona responsable del producto con la tecnología. |

## 3. Opciones consideradas

### 3.1 Cliente web

| Opción | Ventajas | Inconvenientes | Encaje |
|---|---|---|---|
| **Flutter Web** (elegida) | Un solo código con vía abierta a móvil en el futuro (C9). Control total de la interfaz. Tipado fuerte con Dart. La persona responsable tiene experiencia práctica (C11). | Dibuja la interfaz sin usar los elementos nativos del navegador, lo que complica la accesibilidad (C10) y la inspección. Carga inicial mayor. Ecosistema web de componentes y de pruebas de extremo a extremo menos maduro. Menos perfiles disponibles (C6). | Elegida. Los inconvenientes se conservan como riesgos (sección 5). |
| React con TypeScript (SPA) | Ecosistema muy amplio, accesibilidad nativa del navegador, muchas herramientas de prueba y abundancia de perfiles (C6, C10). | No comparte código con una futura app móvil nativa. Sin experiencia práctica declarada. | Alternativa si Flutter Web no supera las verificaciones de la sección 5. |
| Otros SPA (Angular, Vue) | Maduros; Angular aporta estructura. | Sin ventaja decisiva sobre React para este caso. | No se desarrollan. |
| Next.js u otro renderizado en servidor | Útil para páginas públicas y posicionamiento. | SMARTWORK es una aplicación autenticada: no necesita posicionamiento y añade un segundo servidor. | Descartada por innecesaria. |

### 3.2 Backend

| Opción | Ventajas | Inconvenientes | Encaje |
|---|---|---|---|
| **FastAPI (Python)** (elegida) | Ligero y tipado. Genera la documentación OpenAPI de la interfaz. Python es el ecosistema más natural para integrar IA (C4). Buenas pruebas automatizadas (C3). Experiencia práctica de la persona responsable (C11). | Aporta pocos componentes de serie: la estructura, las migraciones y el control de acceso se construyen o se eligen aparte. Exige disciplina para mantener los límites de módulo. | Elegida, con arquitectura por capas. |
| Django con DRF | Incluye identidad, migraciones y consola de administración. | Más pesado. Su consola podría tentar a convertirse en un panel administrativo, que RN-33 no exige. | Alternativa válida; no elegida. |
| NestJS (TypeScript) | Estructura modular. | Python facilita más la integración con IA. | No elegida. |
| Spring Boot (Java) | Muy maduro y robusto. | Mayor coste de arranque para un MVP. | Excesivo para el alcance actual. |

### 3.3 Persistencia

| Opción | Ventajas | Inconvenientes | Encaje |
|---|---|---|---|
| **PostgreSQL** (elegida) | Modelo relacional con restricciones de integridad, transacciones y soporte sólido de fechas e intervalos de tiempo, necesario para la pertenencia por fecha y el orden de avances (C1, C2). Permite añadir controles de acceso en la propia base como segunda capa de defensa. Experiencia práctica de la persona responsable (C11). | Requiere modelar el esquema con cuidado (se hará en el paso siguiente). | Elegida. |
| MySQL o MariaDB | Maduros y extendidos. | Menor expresividad para intervalos de tiempo y restricciones avanzadas. | Alternativa aceptable; no elegida. |
| MongoDB (documentos) | Flexible para contenido libre. | Las reglas de unicidad por persona y fecha, la pertenencia única a un equipo y las consultas históricas favorecen un modelo relacional. | Descartada. |
| SQLite | Sin servidor. | No apta para varios usuarios concurrentes. | Descartada. |

### 3.4 Estilo arquitectónico

| Opción | Ventajas | Inconvenientes | Encaje |
|---|---|---|---|
| **Monolito modular organizado por responsabilidades** (elegido) | Una sola unidad de despliegue y de transacción: la auditoría y el cálculo del estado actual se hacen de forma atómica. Menor coste de operación (C7). Los módulos M1 a M5 se separan por responsabilidad. | Exige disciplina para que los módulos no se acoplen. | Mejor encaje para un MVP con una organización. |
| Microservicios | Escalado independiente. | Transacciones distribuidas para la auditoría y la consistencia; complejidad de operación sin necesidad demostrada. | Prematuro. |
| Funciones sin servidor | Pago por uso. | Autorización y transacciones repartidas; difícil de probar de forma integral. | No recomendado. |

### 3.5 Servicio de IA (modalidades, sin elegir proveedor)

| Modalidad | Qué aporta | Qué obliga a decidir |
|---|---|---|
| Servicio gestionado externo | Rapidez y calidad sin operar modelos. | Qué datos salen, si el proveedor los conserva y qué marco legal aplica (PA-09). |
| Servicio gestionado con garantías contractuales de retención y de región | Reduce la exposición de datos. | Condiciones contractuales y coste. |
| Modelo alojado por la organización | Máximo control de los datos. | Operación, capacidad, coste y calidad en español. |

**Candidato indicado por la persona responsable:** AWS, mediante Amazon Bedrock, que encaja en la segunda modalidad (servicio gestionado). Se registra como candidato y **no está decidido**; puede haber otros. Su evaluación en PA-09 debe responder: qué datos recibe, qué retención y qué región se aplican, qué marco legal rige, cómo responde en español, qué coste y disponibilidad tiene y si condiciona el entorno de despliegue (DT-07). Sus características concretas se verificarán entonces con su documentación contractual; este ADR no las da por supuestas.

La elección entre estas modalidades y entre candidatos **no se toma aquí**: depende de PA-09.

## 4. Decisiones

| ID | Decisión | Fundamento | Estado |
|---|---|---|---|
| D1 | Cliente web con **Flutter Web**. | Experiencia práctica de la persona responsable con Flutter y Dart (C11); vía abierta a móvil; control de la interfaz. | **APROBADO** (DT-01) |
| D2 | Backend con **FastAPI (Python)** organizado como **monolito modular por responsabilidades**: un módulo por cada M1 a M5 y componentes transversales de autorización, auditoría y reloj. | Experiencia práctica con FastAPI y Python (C11); documentación OpenAPI; integración con IA; auditoría y estado actual en una sola transacción. | **APROBADO** (DT-01, DT-02) |
| D3 | **PostgreSQL** como única fuente de verdad. | Experiencia práctica (C11); integridad, transacciones e intervalos de tiempo. | **APROBADO** (DT-01) |
| D4 | El servicio de IA se integra **detrás de una interfaz propia**, de modo que el producto no dependa de un proveedor concreto. No se elige proveedor. | Desacoplar un componente con decisión abierta (PA-09). | **APROBADO** (DT-03). El proveedor sigue **PENDIENTE** (PA-09). |
| D5 | La identificación de personas se integra **detrás de una interfaz propia**. No se elige mecanismo. | Desacoplar un componente con decisión abierta (PA-12). | **APROBADO** (DT-03). El mecanismo sigue **PENDIENTE** (PA-12). |
| D6 | La comunicación entre cliente y servidor usa HTTP con intercambio estructurado. Su contrato se documentará en un paso posterior. | Experiencia con interfaces REST; OpenAPI generado por el servidor. | PROPUESTO |
| D7 | Una **política única de autorización en el backend**, aplicada a consultas, vistas de supervisión e informes. | RN-36 y RN-86: la visibilidad histórica no puede depender del cliente. | **APROBADO** (DT-04) |

## 5. Consecuencias

**Positivas**
- Una sola transacción puede guardar un avance, recalcular el estado actual y registrar la auditoría.
- La política de autorización histórica vive en un único lugar del servidor y se aplica a consultas, vistas e informes (RN-86).
- La experiencia práctica con las tres piezas del stack reduce el riesgo de arranque.
- Python y la interfaz de IA desacoplada facilitan cambiar de proveedor.
- La documentación OpenAPI se obtiene del propio servicio.

**Negativas y riesgos que se conservan**

Aprobar Flutter Web no elimina sus riesgos. Se mantienen y deben verificarse:

| Riesgo | Qué puede ocurrir | Verificación propuesta (a decidir en DT-08 y PA-13) |
|---|---|---|
| **Accesibilidad** | La interfaz dibujada no expone la estructura del navegador; el soporte de lectores de pantalla y de navegación por teclado puede ser insuficiente. | Prueba de concepto con las pantallas más complejas (bitácora y vista del supervisor), con lector de pantalla y teclado, antes de consolidar la interfaz. |
| **Rendimiento** | Carga inicial elevada y primer pintado lento, sobre todo en equipos modestos. | Medir el tamaño de carga y el tiempo hasta la primera interacción con la misma prueba de concepto; fijar un presupuesto de carga cuando se definan los umbrales (PA-13). |
| **Pruebas** | Las pruebas de extremo a extremo en navegador son menos maduras que en otros ecosistemas. | Definir la estrategia de pruebas (DT-08): pruebas de widgets y de integración del cliente, y pruebas de la matriz de permisos y del determinismo en el backend. |

Otros riesgos:
- **Conocimiento concentrado.** La experiencia con el stack recae hoy en una persona. Se mitiga con documentación y con no asumir que otras personas tengan las mismas capacidades.
- FastAPI exige construir o elegir la estructura de módulos y de migraciones.
- El monolito exige vigilar que los módulos no se acoplen.
- Python con control de acceso propio exige una batería de pruebas de permisos amplia.

## 6. Lo que este ADR no decide

- Mecanismo de identificación y de recuperación de acceso (PA-12).
- Proveedor, modalidad, retención y tratamiento de datos del servicio de IA (PA-09).
- Política de retención de la auditoría (PA-06).
- Umbrales de rendimiento, disponibilidad y volumen (PA-13).
- Entorno de despliegue, observabilidad y estrategia de copias de seguridad (DT-07).
- Estrategia de pruebas (DT-08).
- Esquema de datos y contratos de la interfaz.

## 7. Condiciones que obligarían a revisar este ADR

- La prueba de concepto de accesibilidad o de rendimiento de Flutter Web no supera los umbrales acordados: se evalúa React con TypeScript.
- El proyecto se amplía con personas que no pueden asumir Dart o Flutter y el coste de mantenimiento lo desaconseja.
- El volumen esperado (PA-13) exige escalar de forma independiente algún módulo.
- PA-09 obliga a alojar el modelo de IA por la organización.
- PA-12 exige una integración de identidad que condiciona el framework del servidor.

## 8. Trazabilidad

| Decisión | Requisitos que la sostienen |
|---|---|
| D2, D3 | RN-36, RN-45, RN-49 a RN-52, RN-65, RN-66, RNF-02 |
| D4 | RN-30, RN-31, RN-58, RNF-06, RNF-12 |
| D5 | RN-35, RN-61, RN-64, RNF-08 |
| D1 | RNF-05, PP-07 |
| D7 | RN-36, RN-82 a RN-87, RNF-01 |

## 9. Historial

| Versión | Cambios |
|---|---|
| 0.2 | Se incorpora la experiencia práctica de la persona responsable como fundamento (criterio C11). Se aprueban D1 a D5 y D7. D6 sigue propuesto. Se conservan y detallan los riesgos de accesibilidad, rendimiento y pruebas de Flutter Web, con su verificación propuesta. Se añade el riesgo de conocimiento concentrado. Se registra AWS Bedrock como candidato de IA, sin decidir (PA-09). |
| 0.1 | Versión inicial, propuesta. |
