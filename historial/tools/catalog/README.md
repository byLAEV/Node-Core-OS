# Catálogo de Productos y Servicios de Node Core OS byLAEV

**Estado:** catálogo inicial en definición.  
**Versión del catálogo:** 0.1.0  
**Política económica:** pendiente de consenso; no aprobada.  
**Implementación de pagos:** fuera de alcance de esta etapa.

Este directorio es la fuente documental mantenible para identificar las actividades, productos y servicios que la Red de Nodos de Identidad de Node Core OS byLAEV podría ofrecer y monetizar. El catálogo define alcance, requisitos de participación, trabajo esperado, evidencias y aceptación. **No fija precios, porcentajes, comisiones, recompensas ni fórmulas de distribución económica.** Esas reglas deben ser definidas y aprobadas por el Consenso del Modelo de Negocio.

## Principios

1. Se remunera trabajo solicitado, realizado, verificable y aceptado conforme a reglas aprobadas.
2. La remuneración puede reconocer contribuciones individuales y trabajo coordinado entre varios nodos.
3. Tener una identidad, registrar un nodo, mantenerlo conectado o crear identidades adicionales no genera por sí solo un derecho automático a pago.
4. La prueba de trabajo computacional no demuestra por sí sola la calidad o validez del resultado. Cada servicio define evidencias y criterios adecuados.
5. La política económica permanece separada de la especificación técnica del servicio.
6. No se activarán pagos reales hasta aprobar reglas económicas, contabilidad, seguridad, resolución de disputas y controles legales aplicables.
7. Las entradas del catálogo describen productos potenciales; no afirman que estén implementados o disponibles comercialmente.

## Estructura

```text
tools/
├── README.md
└── catalog/
    ├── README.md
    ├── ECONOMIC-CONSENSUS.md
    ├── SERVICE-TEMPLATE.md
    ├── service.schema.json
    └── services/
        ├── README.md
        ├── identity-and-trust.md
        ├── security-assurance.md
        ├── network-and-consensus.md
        ├── storage-and-content.md
        ├── availability-and-compute.md
        └── monitoring-and-supply-chain.md
```

## Categorías iniciales

| ID | Categoría | Ejemplos de trabajo |
| --- | --- | --- |
| CAT-IDENTITY-TRUST | Identidad y confianza digital | Verificación de credenciales, firmas y afirmaciones con alcance definido |
| CAT-SECURITY | Certificación, auditoría y seguridad | Pruebas reproducibles, auditorías y evaluaciones de controles |
| CAT-NETWORK-CONSENSUS | Redes, validación y consenso | Verificación protocolaria, corroboración y pruebas de resiliencia |
| CAT-STORAGE | Almacenamiento y contenido | Retención, recuperación, replicación e integridad local/IPFS |
| CAT-AVAILABILITY-COMPUTE | Disponibilidad y cómputo | Disponibilidad medida, ejecución de tareas y recursos computacionales |
| CAT-MONITORING-SUPPLY-CHAIN | Monitorización y cadena de suministro | Observabilidad, respuesta autorizada, procedencia y verificación de software |

Las categorías pueden ampliarse por propuesta y consenso. Cada producto concreto debe tener un identificador estable y una ficha basada en [SERVICE-TEMPLATE.md](SERVICE-TEMPLATE.md).

## Estado de las entradas

Usar únicamente estos estados documentales:

- **proposed**: propuesta sin contrato de servicio aprobado.
- **specified**: alcance y criterios documentados; no implica implementación.
- **implemented**: código disponible para la función descrita.
- **tested**: pruebas identificadas ejecutadas y con resultados registrados.
- **security-reviewed**: revisión de seguridad documentada.
- **operational**: operación real respaldada por evidencia y procedimientos vigentes.
- **retired**: producto retirado; conservar historial y razón.

No avanzar de estado sin enlazar evidencias verificables. El estado de una ficha no debe inferirse a partir de la existencia de este documento.

## Cómo actualizar el catálogo

1. Copiar [SERVICE-TEMPLATE.md](SERVICE-TEMPLATE.md) para cada producto nuevo.
2. Asignar un ID estable, propietario documental y estado.
3. Describir elegibilidad, trabajo, evidencias, aceptación, errores y disputas.
4. Mantener la política económica como `pending-consensus` hasta que exista una decisión formal trazable.
5. Actualizar el índice de [services/README.md](services/README.md) y validar la ficha contra [service.schema.json](service.schema.json) cuando sea posible.
6. Proponer cambios mediante pull request y registrar decisión, versión, fecha y referencias al consenso.
7. No registrar credenciales, claves privadas, datos personales innecesarios ni secretos en fichas públicas.

## Documentos

- [Consenso del modelo económico](ECONOMIC-CONSENSUS.md)
- [Plantilla de producto o servicio](SERVICE-TEMPLATE.md)
- [Esquema JSON de ficha](service.schema.json)
- [Índice de categorías](services/README.md)

## Fuera de alcance en esta etapa

Este catálogo no implementa un mercado, contratos de pago, criptomoneda, token, billetera, distribución de ingresos ni consenso ejecutable. Tampoco define aún una fórmula de prueba de trabajo remunerable. Esas funciones requieren especificaciones independientes y aprobación explícita antes de programarlas.
