# Node Core OS P2P Contracts

## Estado del desarrollo

**Estado: estructura documental inicial; aplicación todavía no implementada.**

P2P Contracts será una aplicación pública de Node Core OS para preparar solicitudes mediante formularios, anunciar ventanas temporales de recepción entre nodos, recibir solicitudes de otros participantes y agruparlas en manifiestos verificables. Este directorio documenta el límite de la aplicación y servirá como punto de entrada para su implementación.

La estructura se prepara antes de añadir módulos ejecutables para que cada componente tenga responsabilidades definidas y pueda implementarse y probarse por etapas. La presencia de este README no significa que la aplicación ya pueda iniciarse, transmitir solicitudes o participar en una red.

## Objetivo de la primera versión

La primera versión se centrará en solicitudes públicas y transparentes. Un nodo anuncia una ventana porque también necesita enviar su propia solicitud. Durante el tiempo mínimo de propagación, otros nodos pueden enviar formularios al receptor anunciado, mientras el envío de la solicitud propia del receptor permanece deshabilitado. Al vencer el intervalo, el receptor podrá enviar su solicitud y cerrar el lote según las reglas del protocolo.

El valor inicial de prueba propuesto para la ventana es de 600 segundos. Debe ser un parámetro versionado y configurable; no debe copiarse como una constante independiente en varios módulos.

## Estructura prevista

- `main.py`: entrada de la aplicación, siguiendo el patrón de integración real de Node Core OS.
- `p2p_contracts/`: lógica de dominio, esquemas, hashes, estados, servicios y adaptadores.
- `tests/`: pruebas unitarias, de integración y del flujo entre tres nodos.

Cada subdirectorio contiene su propio README con el alcance y los criterios para los archivos que se añadirán después.

## Límites de diseño

- Reutilizar el almacenamiento local y las interfaces de contenido existentes de Node Core OS; no crear otra raíz de almacenamiento sin necesidad demostrada.
- Auditar e integrar el transporte real de mensajes entre nodos. La conectividad de pares por sí sola no equivale a mensajería de aplicación.
- Calcular hashes sobre bytes de una representación canónica definida y probada.
- Mantener los manifiestos inmutables y enlazados al estado padre.
- Mostrar al usuario qué campos de identidad se publicarán y solicitar consentimiento expreso antes de publicarlos.
- No interpretar un perfil declarado como identidad criptográficamente verificada.
- No incluir secretos, contraseñas ni material de autenticación en solicitudes.
- No implementar modo privado ni OpenPGP en esta fase.
- No modificar la funcionalidad de HashPaper.

## Dependencias de integración

Antes de escribir adaptadores se debe confirmar el contrato de las interfaces reales de almacenamiento, contenido, red, runtime y menú. Los adaptadores deben reportar los fallos de forma explícita y no declarar una operación exitosa si no se verificó su resultado.

## Documentación de referencia

- [Estructura de la aplicación](../../docs/P2P-CONTRACTS-APPLICATION-STRUCTURE.md)
- [Plan de desarrollo e instaladores](../../docs/P2P-CONTRACTS-DEVELOPMENT-PLAN.md)
- [Protocolo público de manifiestos](../../docs/P2P-CONTRACTS-PUBLIC-MANIFEST-PROTOCOL.md)
- [Auditoría técnica](../../docs/P2P-CONTRACTS-TECHNICAL-AUDIT.md)

## Criterio para añadir código

Cada módulo debe tener una responsabilidad acotada, entradas y salidas documentadas, errores explícitos y pruebas. No añadir archivos ficticios, interfaces improvisadas ni funcionalidad declarada como lista sin haberla implementado y verificado.
