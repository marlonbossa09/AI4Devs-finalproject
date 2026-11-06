# HU-1.5 — Crear usuarios y equipos y entregar el primer acceso

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-33, RN-34, RN-35, RN-11, RN-98, RN-102, RN-106 |
| **Requisitos** | RF-52, RF-56, RF-57, RF-108, RF-112, RF-116 |
| **Dependencias** | Ninguna |
| **Decisiones pendientes** | PA-12 (caducidad del acceso inicial, credencial propia en el primer ingreso, medio de entrega) |

## Historia

Como persona de la organización, quiero recibir un primer acceso seguro a un entorno con mi equipo y mi supervisor ya definidos, para empezar a registrar mi jornada.

## Criterios de aceptación

- **CA-22** · positivo · RF-52 — DADO el procedimiento de provisión CUANDO se ejecuta para crear una persona con su rol y un equipo ENTONCES existen la persona y el equipo y la persona puede acceder con su primer acceso.
- **CA-23** · positivo · RF-56 — DADO el primer acceso entregado a una persona CUANDO la persona lo utiliza ENTONCES accede al producto.
- **CA-24** · negativo · RF-56 — DADO un primer acceso ya utilizado CUANDO se intenta utilizar de nuevo ENTONCES no se permite.
- **CA-25** · límite · RF-56 — DADO el primer acceso de una persona CUANDO se utiliza ENTONCES identifica únicamente a esa persona y no da acceso como ninguna otra.
- **CA-26** · permisos · RF-57 — DADO un supervisor CUANDO intenta crear usuarios o equipos, o modificar pertenencias ENTONCES no dispone de esa función.
- **CA-250** · positivo · RF-108 — DADO un equipo recién provisionado sin colaboradores CUANDO se consulta su situación ENTONCES puede carecer de supervisor.
- **CA-251** · positivo · RF-112 — DADO una operación de provisión administrativa CUANDO se ejecuta ENTONCES queda una entrada de auditoría con un autor identificable, la operación y los valores anterior y nuevo, sin credenciales ni códigos de acceso.
- **CA-252** · positivo · RF-116 — DADO una persona nueva CUANDO se registra su primera pertenencia con una fecha de inicio igual o posterior a la fecha actual de la organización ENTONCES se acepta.
- **CA-253** · negativo · RF-116 — DADO una persona nueva CUANDO se intenta registrar su primera pertenencia con una fecha de inicio anterior a la fecha actual de la organización ENTONCES se rechaza.

## Notas

- La provisión es un procedimiento administrativo controlado, no un rol funcional ni un panel avanzado (RN-33).
- La dependencia técnica es el diseño del procedimiento y del primer acceso. No se definen criterios sobre caducidad, credencial propia ni medio de entrega (PA-12).
- La forma de identificar a quien opera la provisión está pendiente (PA-12). No se definen criterios sobre ella.
