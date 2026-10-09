# Node Core OS — Plan de evolución del instalador

## Objetivo

Unificar progresivamente la instalación, actualización y reparación en un mismo motor que inspeccione el estado real, planifique cambios y verifique el resultado. Todas las operaciones deben ejecutarse como usuario normal, sin root, sin sudo y sin modificaciones globales del sistema.

Este documento describe el diseño y el orden de implementación. Una capacidad solo se considera terminada cuando existe código y una prueba automatizada que la respalde.

## Reglas de seguridad

1. Rechazar UID 0 antes de modificar archivos.
2. Mantener `NODE_CORE_DATA_DIR` dentro del HOME y comprobar propiedad/rutas seguras.
3. No reinstalar Kubo si el ejecutable existente funciona y no se solicitó expresamente su actualización.
4. No borrar ni reconstruir `storage/` o `ipfs/` durante una actualización normal de la aplicación.
5. No sobrescribir la configuración del usuario sin una migración versionada y validada.
6. Descargar y validar el código objetivo antes de reemplazar la aplicación.
7. Crear respaldos de los componentes que serán modificados y ofrecer recuperación si falla la actualización.
8. No afirmar que está actualizado si no se pudo consultar la versión remota.
9. Actualizar el inventario únicamente después de superar las verificaciones obligatorias.
10. Probar el comportamiento en un entorno temporal antes de declarar una fase terminada.

## Hallazgos de la auditoría inicial

- `installer/lib/python.sh` elimina el directorio de aplicación existente en `install_application()`; esta operación no debe usarse indiscriminadamente en futuras ejecuciones idempotentes.
- `write_config()` genera de nuevo `config.json`; el motor evolutivo debe preservar valores existentes y realizar migraciones explícitas.
- `installer/update.sh` prepara/recrea los lanzadores antes de comprobar la versión remota; el motor futuro debe separar inspección y planificación de aplicación de cambios.
- La lógica de instalación y actualización está repartida en scripts distintos; se conservarán inicialmente los puntos de entrada por compatibilidad, pero deberán delegar al mismo motor.
- `installer/lib/kubo.sh` contempla Termux, mientras que la documentación actual declara que Termux no está soportado. La plataforma admitida debe aclararse y probarse antes de ampliar soporte.
- La actualización de la aplicación no debe copiar ni eliminar el repositorio IPFS como parte de un respaldo normal de código.

## Arquitectura objetivo

1. **Detector**: lectura del estado de archivos, configuración, lanzadores, Kubo, repositorio y almacenamiento.
2. **Manifiesto**: registro versionado de componentes, versiones conocidas y estado de verificación.
3. **Planificador**: determina las operaciones necesarias sin ejecutarlas.
4. **Motor de aplicación**: aplica el plan con respaldos y recuperación.
5. **Verificador**: comprueba código, lanzadores, configuración e integración con Kubo.
6. **Interfaces**: instalación, actualización y reparación delegan al mismo motor.

## Etapas

1. Auditar los efectos de los scripts actuales y establecer pruebas de preservación.
2. Añadir un detector de estado estrictamente de solo lectura.
3. Diseñar e implementar el manifiesto, incluyendo validación y escritura atómica.
4. Implementar el planificador y pruebas de planes sin cambios.
5. Implementar la aplicación transaccional de cambios y recuperación.
6. Integrar `install.sh`, `update.sh` y reparación con el motor compartido.
7. Añadir transición segura entre versiones del instalador.
8. Incorporar el inventario de componentes y sus dependencias.
9. Actualizar la documentación según las plataformas realmente probadas.

## Criterios de aceptación

- La ejecución de detección no crea, elimina ni modifica archivos.
- La segunda ejecución del instalador no reinstala componentes que estén verificados.
- Las actualizaciones conservan almacenamiento local, repositorio IPFS y configuración.
- Los fallos de red se informan como estado desconocido, no como instalación actualizada.
- Una actualización fallida intenta restaurar el código anterior sin tocar los datos persistentes.
- Las pruebas se ejecutan como usuario no root en CI.
- No se usan gestores de paquetes del sistema ni privilegios globales.

## Estado de implementación

- [x] Detector inicial de instalación de solo lectura.
- [x] Validación y escritura atómica del manifiesto de esquema 1.
- [x] Planificador inicial de solo lectura que propone acciones a partir del estado real.
- [x] Pruebas para detector, manifiesto y planificador añadidas a CI.
- [ ] Integrar el motor compartido con los puntos de entrada install/update.
- [ ] Aplicación transaccional con respaldo y recuperación probada.
- [ ] Inventario verificado de versiones y dependencias por componente.

El planificador actual es deliberadamente consultivo: no ejecuta las acciones que enumera. Un componente que falta Kubo o el repositorio IPFS se marca para revisión, no para reemplazo o inicialización automática. La integración con el instalador principal queda pendiente hasta que el plan y el manifiesto estén cubiertos por pruebas adicionales.
