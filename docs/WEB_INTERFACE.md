# Interfaz web local (primera etapa)

La primera etapa ofrece un panel web de **solo lectura**, conectado al runtime Python existente de Node Core OS. Muestra el estado real devuelto por `NodeRuntime.kubo.status()`.

## Ejecución

Desde la raíz del repositorio, con el mismo entorno Python que usa Node Core OS:

```sh
python -m node_core.web_ui
```

Abre en el navegador del mismo dispositivo:

```text
http://127.0.0.1:8765/
```

Detén el servidor con `Ctrl+C`.

Si el puerto 8765 está ocupado, el servidor termina con un error en lugar de cambiar de puerto silenciosamente. Para una prueba, se puede elegir explícitamente otro puerto:

```sh
NODE_CORE_WEB_PORT=8766 python -m node_core.web_ui
```

El servidor escucha exclusivamente en `127.0.0.1`, no en `0.0.0.0`. No lo expongas a una LAN ni a internet público.

## Alcance y seguridad

- La página consulta el endpoint local `/api/status`.
- El endpoint obtiene el estado de Kubo a través de `NodeRuntime.kubo.status()`.
- La primera etapa no llama a `runtime.boot()`; iniciar el servidor web no arranca automáticamente Kubo ni los servicios P2P nativos.
- La API RPC de Kubo permanece separada y no se expone ni se reenvía al navegador.
- Las solicitudes POST se rechazan. Esta etapa no contiene acciones que cambien el estado del sistema.
- Los elementos del menú permanecen deshabilitados hasta que cada operación esté conectada al runtime con sus validaciones y confirmaciones originales.
- La dirección de la API configurada y la ruta del repositorio se muestran como datos de diagnóstico; no prueban por sí mismas que el servicio responda o que el contenido se pueda recuperar.

## Siguientes pasos

1. Verificar este panel en la instalación Termux de destino.
2. Añadir una ruta de solo lectura para el resumen de red del menú principal usando los métodos existentes del runtime.
3. Implementar cada menú como acciones explícitas y tipadas; no enviar comandos arbitrarios de terminal desde el navegador.
4. Añadir pruebas para cada acción y conservar la interfaz de terminal.
