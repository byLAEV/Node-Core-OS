# Pruebas de Node Core OS P2P Contracts

## Estado

Este directorio contiene inicialmente la estrategia formal de pruebas. Los archivos de prueba enumerados en la documentación de arquitectura aún no se han creado y no se debe interpretar este README como evidencia de que las pruebas ya pasan.

## Objetivo

Verificar primero la lógica local de manera determinista y, progresivamente, comprobar su integración con el almacenamiento, Kubo/IPFS, el transporte entre nodos, la interfaz y los instaladores. Las pruebas deben poder demostrar resultados observables y reproducibles, no limitarse a comprobar que una función existe.

## Grupos de pruebas previstos

### 1. Esquemas y validación

- Aceptar mensajes válidos de la versión soportada.
- Rechazar campos requeridos ausentes, tipos incorrectos y versiones desconocidas.
- Validar identificadores, referencias, cantidades y estados permitidos.
- Comprobar que los datos recibidos no pueden cambiar silenciosamente de forma durante la validación.

### 2. Serialización y hashes

- Usar vectores de prueba conocidos para SHA-256.
- Comprobar que la serialización canónica es determinista.
- Verificar que un cambio de campo, referencia u orden cambia el hash esperado.
- Asegurar que el hash se calcula sobre los bytes finales exactos, no sobre una representación que luego cambia.

### 3. Temporizador y estados de ventana

- El botón de envío propio está deshabilitado antes del tiempo mínimo.
- La recepción de solicitudes entrantes sigue disponible mientras el envío propio está bloqueado.
- El envío propio se habilita al llegar el instante calculado.
- El estado persiste y se reconstruye correctamente después de reiniciar.
- El reloj se simula para que las pruebas no tengan que esperar 600 segundos reales.
- Una solicitud tardía no se añade a un lote cerrado.

### 4. Solicitudes y recibos

- Cada solicitud tiene un identificador y una referencia de preestado.
- El recibo se vincula a la solicitud correcta.
- Se detectan duplicados según la política documentada.
- Los errores de almacenamiento o transmisión no se presentan como entrega confirmada.

### 5. Lotes y manifiestos

- El lote contiene las referencias esperadas y el orden definido.
- La cantidad declarada coincide con las referencias.
- La solicitud propia del receptor se incorpora solo cuando se cumplen las reglas de cierre.
- Las referencias ausentes o mal formadas se rechazan.
- Un nodo distinto del creador puede recuperar y verificar el manifiesto.
- Los manifiestos anteriores permanecen inmutables.

### 6. Adaptadores

- Probar primero con dobles controlados.
- Probar con las interfaces reales de almacenamiento y contenido.
- Comprobar fallos de Kubo, contenido no disponible y errores de publicación.
- Confirmar que las rutas de escritura permanecen dentro de las ubicaciones permitidas por Node Core OS.
- Confirmar que el transporte transmite mensajes de aplicación y no solo verifica conectividad.

### 7. Flujo de tres nodos

- A anuncia una ventana; B y C verifican el preestado conocido.
- B y C envían solicitudes y reciben recibos.
- A espera el tiempo mínimo para enviar su solicitud propia.
- A cierra el lote y publica el manifiesto.
- B o C recupera el manifiesto y comprueba los hashes y las referencias.
- Los nodos avanzan al siguiente preestado únicamente tras completar las validaciones requeridas.
- Se comprueba recuperación tras desconectar y reiniciar un nodo.

### 8. Instalación y actualización

- Instalación limpia con P2P Contracts incluida.
- Actualización desde la versión estable anterior.
- Preservación de configuración, identidad, documentos, almacenamiento local y repositorio Kubo.
- Fallos de descarga o verificación no destruyen la instalación anterior.
- La integración no cambia el comportamiento de HashPaper.
- El flujo de instalación y actualización se prueba en cada plataforma que se declare compatible.

## Reglas para escribir pruebas

- Cada prueba debe comprobar una condición observable concreta.
- No depender de Internet en pruebas unitarias.
- No usar esperas reales de diez minutos; inyectar un reloj controlado.
- No usar identidades ni datos personales reales en pruebas.
- Usar directorios temporales de prueba solo dentro del entorno de pruebas y limpiarlos al terminar.
- Evitar pruebas que dependan de un orden accidental de ejecución.
- Registrar comandos ejecutados y resultados en la evidencia de CI.
- No omitir una prueba fallida para obtener un resultado verde; corregir el código o documentar una limitación reproducible.

## Criterio de finalización

La aplicación no debe considerarse lista para distribuir hasta que pasen las pruebas unitarias, las pruebas de integración pertinentes, el flujo de tres nodos, la instalación limpia y la actualización con preservación de datos. Los resultados deben asociarse a la revisión exacta del código probado.
