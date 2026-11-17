"""Provisión administrativa de SMARTWORK (M1): órdenes del servidor, no endpoints HTTP (A2, decisión del 2026-11-11).

Los casos de uso (``servicio``) son independientes de cómo se invoquen: la CLI (``scripts/provision.py``) es solo una forma
de llamarlos. Cada orden la ejecuta una persona operadora identificada con credencial propia (``operadores``, opción C del
ADR-002), con un rol de PostgreSQL de privilegios mínimos distinto del propietario y de la aplicación.
"""
