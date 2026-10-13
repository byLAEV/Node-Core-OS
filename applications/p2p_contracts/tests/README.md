# Pruebas de P2P Contracts

La primera suite cubre la validación de cantidades, la creación de una solicitud BTC, la creación de manifiestos locales, la incorporación de evidencia y la consulta por ID.

Ejecutar desde la raíz del repositorio:

    python -m unittest applications.p2p_contracts.tests.test_service

Casos cubiertos por los tests añadidos:
- Cantidad BTC decimal válida e inválida.
- Rechazo de BTC como activo a recibir.
- Creación de solicitud y campos de identidad consentidos.
- Registro de evidencia con resultado final y estado derivado.
- Detección de alteraciones al manifiesto local.

Estas pruebas aún requieren ejecución en un entorno de desarrollo real. La integración de red, publicación IPFS e instaladores queda para fases posteriores.
