# RoadMap Index — Node Core OS byLAEV

> Registro maestro de trabajo pendiente, necesidades identificadas, propuestas, investigaciones, decisiones y capacidades que todavía deben diseñarse, implementarse, probarse o validarse en Node Core OS.

## Propósito

Este directorio es el espacio oficial para documentar todo lo que se considera necesario hacer en el proyecto y que todavía no está terminado. No es una descripción de funcionalidades existentes ni una promesa de que una propuesta ya esté implementada.

El RoadMap Index debe conservar la trazabilidad entre:
- Lo que se necesita o desea construir y por qué.
- Qué existe actualmente y qué falta.
- Qué decisiones están pendientes.
- Qué dependencias, permisos o integraciones externas requiere.
- Cómo se demostrará que funciona y cuándo se considera terminado.

## Reglas de registro

1. No presentar propuestas como funcionalidades existentes. Usar estados explícitos y evidencia enlazada.
2. No borrar el historial de decisiones. Las modificaciones importantes deben dejar registro.
3. No convertir una idea en implementación sin especificación y criterios de aceptación.
4. Separar investigación, diseño, implementación, pruebas y validación externa.
5. Registrar dependencias y bloqueos, incluyendo permisos, acuerdos institucionales, APIs externas, hardware y conectividad.
6. Priorizar la funcionalidad comprobable, con pruebas reproducibles y compatibilidad con conexiones lentas y entornos Linux.
7. Proteger datos personales desde el diseño. Los ejemplos y pruebas iniciales deben utilizar datos ficticios.
8. Actualizar el índice maestro cuando se agregue, cambie, complete o descarte un trabajo.

## Estados oficiales

| Estado | Significado |
|---|---|
| IDEA | Necesidad o posibilidad identificada, aún sin investigar. |
| PENDING_RESEARCH | Requiere investigación y fuentes. |
| RESEARCHED | Investigación documentada; falta decidir o diseñar. |
| PROPOSED | Propuesta formulada; no aprobada como diseño definitivo. |
| APPROVED | Alcance y enfoque aprobados para desarrollo. |
| IN_PROGRESS | Trabajo en curso. |
| BLOCKED | No puede avanzar por una dependencia identificada. |
| IMPLEMENTED | Código o documentación implementados; aún requiere validación. |
| TESTING | En pruebas. |
| VERIFIED | Criterios de aceptación y pruebas satisfechos con evidencia. |
| DEFERRED | Pospuesto deliberadamente. |
| CANCELLED | Descartado con motivo documentado. |

IMPLEMENTED no equivale a VERIFIED. Una integración externa tampoco se considera funcional hasta probarla con autorización y un entorno real o sandbox válido.

## Estructura

- [00 — Master Roadmap](00-MASTER-ROADMAP.md): índice de todas las líneas de trabajo pendientes.
- [01 — NCIP: Identity and Institutional Verification](01-NCIP-IDENTITY-INSTITUTIONAL-VERIFICATION/README.md): primera línea estratégica, dedicada a identidad documental y verificación institucional.

Las nuevas líneas de trabajo deben incorporarse aquí antes de crear documentación dispersa.

## Formato mínimo de cada iniciativa

Cada iniciativa debe declarar ID único, nombre y objetivo, problema que resuelve, estado actual, alcance incluido y excluido, capacidades existentes verificadas, trabajo pendiente, dependencias y riesgos, criterios de aceptación, pruebas y evidencias, fuentes y fecha de última revisión.

## Alcance

RoadMap Index es un registro de planificación y control de trabajo pendiente. No modifica por sí mismo el comportamiento del sistema, no concede permisos a terceros y no afirma que existan acuerdos o integraciones institucionales.