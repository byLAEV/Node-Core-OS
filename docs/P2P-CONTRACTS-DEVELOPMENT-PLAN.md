# Node Core OS P2P Contracts — plan de desarrollo, integración e instaladores

Estado: plan de trabajo; no declara que P2P Contracts esté implementada ni que exista un nuevo instalador funcional.

## 1. Objetivo de entrega

Entregar una aplicación pública P2P Contracts integrada en Node Core OS, con un flujo demostrable de tres nodos, más un instalador/actualizador que distribuya la aplicación sin borrar ni reemplazar datos persistentes.

La entrega final tendrá dos caminos diferenciados:

1. **Instalación nueva de Node Core OS:** incluye la nueva aplicación P2P Contracts junto al núcleo y las aplicaciones que oficialmente se empaqueten en esa versión.
2. **Actualización de una instalación existente:** actualiza el código de Node Core OS y agrega/actualiza P2P Contracts, pero preserva configuración, identidad, documentos, almacenamiento local, Kubo/IPFS y su repositorio.

No se debe publicar una nueva versión estable ni dar comandos de instalación definitivos hasta que la aplicación, el instalador y las pruebas hayan pasado.

## 2. Auditoría técnica inicial

Antes de escribir código de aplicación se deben confirmar los contratos de integración y las pruebas existentes.

Archivos e interfaces ya inspeccionados:
- `node_core/storage.py`: `StorageManager`.
- `node_core/content.py`: `ContentManager` y `ContentRegistry`.
- `node_core/network.py`: `NodeNetwork`, que proporciona conectividad básica pero no mensajería de aplicación.
- `installer/install.sh`: instalador de usuario, verifica HashPaper, configura Kubo y verifica la instalación.
- `installer/update.sh`: actualización transaccional del directorio de aplicación con comprobaciones de preservación.
- `docs/DEVELOPMENT.md` y `docs/DEPENDENCIES.md`: contrato de desarrollo oficial GNU/Linux terminal, Python 3.10+ y dependencias de Python estándar.

La auditoría debe continuar leyendo la inicialización real del runtime, el menú principal, el registro de aplicaciones, la configuración, la API Kubo y los tests de instalación. No se debe asumir un mecanismo de registro de aplicaciones sin comprobarlo.

## 3. Fases y entregables

### Fase 0 — Contratos de integración
**Tareas**
- Documentar cómo el runtime construye y entrega `StorageManager`, `ContentManager` y `NodeNetwork`.
- Identificar cómo se registran aplicaciones y cómo el menú principal las descubre.
- Confirmar qué transporte de mensajes de aplicación está disponible. La conectividad de pares no se considera transporte de solicitudes.
- Identificar las pruebas de instalador y actualización que deben extenderse.
- Confirmar política de versiones y empaquetado.

**Entregable:** mapa de llamadas real, puntos de integración y matriz de pruebas. No modificar HashPaper.

### Fase 1 — Esquemas y lógica local
**Tareas**
- Definir los esquemas versionados de anuncio, solicitud, recibo, lote y manifiesto.
- Implementar serialización canónica y hash SHA-256 con vectores de prueba conocidos.
- Implementar validación de formularios y consentimiento de identidad.
- Crear solicitudes y lotes localmente sin red ni Kubo.
- Guardar mediante el almacenamiento existente.

**Entregable:** módulo local con pruebas unitarias deterministas. No se acepta publicación remota en esta fase.

### Fase 2 — Máquina de estados y temporizador
**Tareas**
- Implementar los estados de ventana y las transiciones válidas.
- Configurar el mínimo inicial de 600 segundos.
- Mantener deshabilitado el envío de la solicitud propia antes de `send_enabled_at`.
- Permitir recibir y validar solicitudes mientras el botón de envío propio está bloqueado.
- Persistir el estado y reconstruir la cuenta regresiva después de reiniciar.
- Cerrar el lote sin aceptar solicitudes tardías retroactivamente.

**Entregable:** pruebas de temporizador con reloj simulado; pruebas sin esperas reales de diez minutos.

### Fase 3 — Adaptador de contenido y manifiestos
**Tareas**
- Integrar `ContentManager` para publicar y recuperar solicitudes/manifiestos.
- Verificar bytes recuperados y hash esperado.
- Definir cuándo fijar objetos y qué referencias se conservan en el manifiesto general.
- Manejar errores de Kubo, contenido no disponible, pinning fallido y publicación parcial.
- Nunca declarar éxito si falló una operación.

**Entregable:** pruebas con adaptadores simulados y pruebas de integración local con Kubo cuando el entorno de CI lo permita.

### Fase 4 — Transporte entre nodos
**Tareas**
- Elegir un transporte que funcione con la infraestructura real de Node Core OS y que permita intercambiar mensajes de aplicación acotados.
- Definir ID de mensaje, límite de tamaño, tiempo de espera, confirmación de entrega y reintentos.
- Propagar anuncios pequeños de ventana y consultar el estado anunciado.
- Transmitir solicitudes y recibos durante la ventana.
- Documentar que el Peer ID es un identificador de transporte, no una firma automática del contenido.
- No afirmar que se ha logrado consenso si solo se ha confirmado conectividad o recepción de mensajes.

**Entregable:** prueba de transporte con dos nodos y luego tres nodos, con mensajes de prueba y límites de tamaño.

### Fase 5 — Lote y transición de estado
**Tareas**
- Agrupar solicitudes recibidas y la solicitud propia del receptor en un manifiesto determinista.
- Ordenar las referencias de forma explícita y calcular el hash después de cerrar la lista.
- Verificar el manifiesto desde un nodo que no creó el lote.
- Cambiar al siguiente preestado solo después de validar el cierre.
- Probar solicitudes duplicadas, tardías, mal formadas y referencias ausentes.
- Conservar los recibos para poder comparar lo recibido con lo incluido en el lote.

**Entregable:** flujo local completo y flujo de tres nodos con resultados reproducibles.

### Fase 6 — Integración de interfaz
**Tareas**
- Añadir una entrada de P2P Contracts al punto de integración real del menú.
- Mostrar estado sincronizado, receptor vigente, preestado, cuenta regresiva, solicitudes recibidas, recibos y lote.
- Usar formularios de terminal sencillos y validaciones claras.
- Mostrar consentimiento de identidad antes de publicar campos.
- No agregar opciones privadas/OpenPGP.
- No alterar la navegación o funcionalidad de HashPaper.

**Entregable:** prueba de menú y recorrido manual documentado.

### Fase 7 — Pruebas de regresión y compatibilidad
**Tareas**
- Ejecutar la suite completa del repositorio.
- Añadir pruebas unitarias para todos los esquemas y transiciones.
- Probar instalación limpia y actualización desde la versión estable previa.
- Confirmar que configuración, identidad, documentos, almacenamiento local, Kubo binario y repositorio Kubo sobreviven a la actualización.
- Confirmar que las pruebas de HashPaper siguen pasando sin cambios de comportamiento.
- Probar recuperación ante una descarga interrumpida y un fallo de verificación.
- Validar Bash y Python según el contrato oficial GNU/Linux.

**Entregable:** CI verde y resultados de instalación/actualización documentados.

### Fase 8 — Instaladores y distribución
**Instalación nueva**
- Incluir `applications/p2p_contracts/` en el paquete de aplicación.
- Verificar su `VERSION`, compilar/importar módulos y ejecutar sus pruebas unitarias.
- Crear sus directorios de datos únicamente a través de los mecanismos de almacenamiento del núcleo.
- No crear ni sobrescribir datos de usuario durante instalación si ya existen.
- Verificar que la instalación puede arrancar sin que P2P Contracts esté conectada a la red.

**Actualización**
- Actualizar el árbol de código mediante el actualizador transaccional existente.
- Incorporar la nueva aplicación y ejecutar verificaciones antes de marcar la actualización como completada.
- Preservar todos los datos fuera del árbol de código.
- Mantener la recuperación/rollback si la verificación falla.
- No sustituir Kubo ni inicializar otro repositorio Kubo como efecto colateral de actualizar la aplicación.

**Paquetes de descarga**
- Revisar el flujo de empaquetado existente y el PR de paquetes de instalador antes de modificarlo.
- Generar artefactos versionados para instalación nueva y actualización desde la misma revisión verificada.
- Publicar SHA-512 junto a cada archivo.
- No declarar soporte de Termux/Android sin pruebas reales en dispositivo; el contrato oficial documentado actual es GNU/Linux terminal.

**Entregable:** artefactos reproducibles, checksum y comandos de instalación/actualización publicados solo después de pasar pruebas.

### Fase 9 — Prueba de aceptación con tres nodos
**Escenario**
1. A, B y C comparten el mismo estado inicial.
2. A anuncia una ventana para recibir solicitudes porque también enviará una solicitud.
3. El anuncio pequeño se propaga y los nodos comprueban el estado conocido.
4. El envío propio de A permanece deshabilitado durante 600 segundos.
5. B y C envían formularios a A y reciben sus recibos.
6. Cuando vence el intervalo, A envía su propia solicitud.
7. A crea y publica el manifiesto del lote.
8. B o C recupera el manifiesto y verifica las solicitudes, referencias y hashes.
9. Se cierra la ventana y el siguiente nodo anuncia el próximo preestado.
10. Se reinicia un nodo y se comprueba que recupera el estado de ventana/manifiesto correctamente.

**Criterios de aceptación**
- Los formularios son pequeños y se transmiten por separado del anuncio.
- No se habilita prematuramente el envío propio.
- Las solicitudes de la ventana se agrupan en un manifiesto verificable.
- Los nodos no dependen de un único archivo mutable.
- El contenido se verifica tras recuperarse.
- Los errores de red o almacenamiento se muestran sin falsos mensajes de éxito.
- La suite existente de Node Core OS y HashPaper permanece verde.

## 4. Versiones y límites

La versión de Node Core OS y la versión de P2P Contracts deben identificarse separadamente. El número final se asignará después de revisar la política real de versiones y el estado del lanzamiento existente.

No cambiar la versión ni crear artefactos de lanzamiento antes de que la integración y los tests estén listos. El primer lanzamiento de P2P Contracts debe marcarse como experimental hasta superar las pruebas de tres nodos.

## 5. Reglas de preservación del instalador

- El instalador y actualizador se ejecutan como usuario normal; no usar root ni `sudo`.
- No instalar paquetes del sistema.
- No borrar ni reemplazar `~/.node-core/storage/`, configuración, identidad, documentos, pruebas OTS ni otros datos persistentes.
- No borrar ni recrear `~/.node-core/ipfs/` ni sustituir el binario Kubo por instalar P2P Contracts.
- No guardar solicitudes, manifiestos de usuario ni temporizadores dentro del árbol de código que el actualizador reemplaza.
- Validar el contenido descargado antes de activarlo.
- Si una comprobación falla, conservar la instalación anterior y proporcionar error claro.

## 6. Condiciones para declarar el trabajo terminado

No marcar la aplicación como funcional hasta que:
- la suite de pruebas pase;
- el instalador limpio pase;
- la actualización preserve datos;
- el flujo de tres nodos se complete;
- el manifiesto del lote pueda verificarse desde un nodo distinto;
- la cuenta regresiva y el bloqueo del botón estén probados;
- los documentos de instalación describan exactamente lo que se ha probado.

El modo privado/OpenPGP y los cambios a HashPaper quedan fuera de este trabajo.
