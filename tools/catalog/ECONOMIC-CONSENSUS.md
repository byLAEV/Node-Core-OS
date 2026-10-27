# Consenso del Modelo de Negocio y Distribución de Beneficios

**Estado:** `pending-consensus`  
**Versión:** 0.1.0  
**Decisión económica aprobada:** ninguna registrada en esta versión.

## 1. Propósito

Este documento establece el proceso y las preguntas que deberán resolver los participantes autorizados antes de definir cómo se valoran y distribuyen los ingresos derivados de los productos y servicios del catálogo de Node Core OS byLAEV.

No constituye una fórmula de pagos. No establece porcentajes, tarifas, recompensas, comisiones, emisiones monetarias ni garantías de ingresos.

## 2. Principio base

La red podrá reconocer trabajo individual y colectivo que sea solicitado, ejecutado, verificable y aceptado conforme a un contrato de servicio y a las reglas aprobadas. La mera inscripción de identidades o nodos no constituye trabajo remunerable.

El mecanismo concreto de reconocimiento debe diferenciar entre:
- prueba de esfuerzo computacional;
- evidencia de ejecución del servicio;
- validez y calidad del resultado;
- aceptación por el solicitante o por el proceso de verificación;
- liquidación económica efectivamente realizada.

Estos conceptos no son equivalentes y no deben colapsarse en una única métrica sin justificación.

## 3. Temas que el consenso debe resolver

1. **Participación y elegibilidad:** quién puede proponer, ejecutar, verificar y aceptar cada tipo de trabajo.
2. **Demanda comercial:** cómo se registra el solicitante, la tarea y el presupuesto disponible.
3. **Unidad de trabajo:** cómo se mide cada servicio sin premiar actividad artificial.
4. **Evidencias:** qué datos firmados, registros, resultados o pruebas reproducibles son suficientes.
5. **Aceptación:** quién decide, cómo se evita la colusión y cómo se apela un rechazo.
6. **Contribución conjunta:** cómo se atribuyen funciones dependientes, paralelas o de coordinación.
7. **Valoración:** cómo se proponen y aprueban precios o reglas de recompensa.
8. **Costes y reservas:** cómo se contabilizan operación, infraestructura, comisiones y contingencias.
9. **Liquidación:** moneda o medio de pago, plazos, idempotencia, reintentos y conciliación.
10. **Fraude y abuso:** tareas duplicadas, identidades Sybil, evidencias falsificadas, autoconsumo y colusión.
11. **Disputas y correcciones:** revisión, suspensión de liquidación y reparación de errores.
12. **Gobernanza:** quórum, elegibilidad, conflictos de interés, publicación de votos y cambios de reglas.
13. **Cumplimiento:** obligaciones fiscales, contractuales, de protección de datos y demás requisitos aplicables.
14. **Transición:** cómo se versionan las reglas y cómo se tratan trabajos iniciados bajo una versión anterior.

## 4. Requisitos mínimos para una propuesta económica

Toda propuesta debe incluir:
- identificador y versión;
- problema y servicios a los que aplica;
- actores elegibles y posibles conflictos de interés;
- unidad de trabajo y ejemplo calculable;
- evidencias requeridas y método de validación;
- tratamiento de fallos, fraude y disputas;
- efectos sobre operadores individuales y trabajos colectivos;
- análisis de incentivos Sybil y colusión;
- costes, supuestos y riesgos;
- plan de simulación y criterios de aprobación;
- procedimiento de activación, reversión y actualización.

## 5. Registro de decisiones

Hasta que una decisión sea aprobada y registrada, su estado seguirá siendo `pending-consensus`.

| Campo | Valor inicial |
| --- | --- |
| Estado | `pending-consensus` |
| Versión de política económica | No asignada |
| Propuesta aprobada | Ninguna |
| Fecha de aprobación | Ninguna |
| Referencia al acta o decisión | Ninguna |
| Activación de pagos reales | No autorizada por este documento |

Cuando exista consenso, registrar una decisión versionada en un documento separado o en el registro de gobernanza acordado. No sobrescribir el historial de decisiones: enlazar la versión anterior, la nueva, su fecha de vigencia y el mecanismo de aprobación.

## 6. Puerta de seguridad antes de pagos reales

No activar liquidaciones reales hasta que se hayan diseñado, implementado y probado, al menos:
- registro de órdenes y presupuesto;
- evidencias autenticadas y verificables;
- aceptación y apelación;
- protección contra pago duplicado;
- registro contable auditable;
- control de acceso y custodia de credenciales;
- manejo de fallos y conciliación;
- simulaciones de fraude, Sybil y colusión;
- revisión de seguridad y obligaciones legales aplicables.

La aprobación de una política económica no demuestra que el código de pagos sea seguro. La implementación debe pasar pruebas independientes de su documento de gobernanza.
