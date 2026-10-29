# Interfaz web local (primera etapa)

La interfaz web está conectada al runtime Python existente de Node Core OS. Consulta el estado real devuelto por `NodeRuntime.kubo.status()` y ofrece una acción explícita para iniciar Kubo/IPFS.

## Ejecución sin privilegios

La interfaz web debe ejecutarse como el usuario normal propietario de la instalación de Node Core OS. **No uses `sudo`, `su` ni una sesión root.** El servidor rechaza el inicio si detecta UID efectivo `0`. Esto evita que el proceso web herede privilegios administrativos innecesarios.

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

El servidor escucha exclusivamente en `127.0.0.1`, no en `0.0.0.0`. No lo expongas a una LAN ni a internet público. Ejecutarlo como usuario normal no significa que pueda cambiar permisos o acceder a archivos que ese usuario no tenga autorizados.

## Alcance y seguridad

- La página consulta el endpoint local `/api/status`.
- El endpoint obtiene el estado de Kubo a través de `NodeRuntime.kubo.status()`.
- Iniciar el servidor web no arranca Kubo automáticamente. El botón **Iniciar Kubo / IPFS** envía una solicitud local con confirmación explícita y llama a `NodeRuntime.kubo.start()` como el usuario actual, sin root ni sudo.
- La API RPC de Kubo permanece separada y no se expone ni se reenvía al navegador.
- El endpoint `POST /api/kubo/start` solo acepta solicitudes JSON confirmadas, con Host y Origin locales. Las demás solicitudes POST se rechazan. No se ofrece una acción web para detener Kubo en esta etapa.
- Los elementos del menú permanecen deshabilitados hasta que cada operación esté conectada al runtime con sus validaciones y confirmaciones originales.
- La dirección de la API configurada y la ruta del repositorio se muestran como datos de diagnóstico; no prueban por sí mismas que el servicio responda o que el contenido se pueda recuperar.

## Siguientes pasos

1. Verificar este panel en la instalación Termux de destino.
2. Añadir una ruta de solo lectura para el resumen de red del menú principal usando los métodos existentes del runtime.
3. Implementar cada menú como acciones explícitas y tipadas; no enviar comandos arbitrarios de terminal desde el navegador.
4. Añadir pruebas para cada acción y conservar la interfaz de terminal.

## Incremento de navegación y consulta de red

El menú principal ahora permite abrir secciones en la página. El apartado **Network / Nodes** llama a `GET /api/network/kubo`, que consulta el estado de Kubo y, solo cuando el daemon ya está en ejecución, usa `NodeRuntime.network.status()` para mostrar el ID local y los pares directamente conectados. El botón **Iniciar Kubo / IPFS** llama a `NodeRuntime.kubo.start()` tras confirmación y verifica que la API de Kubo responda.

Las secciones BIOS, Core, Blog y Applications se muestran como pendientes y no ejecutan acciones todavía. La paridad funcional completa requiere conectar y probar cada submenú individualmente.


## Inicio explícito de Kubo desde la web

El botón de inicio solicita confirmación antes de llamar a `KuboManager.start()`. Si el repositorio está sin inicializar, el mensaje de confirmación advierte que Kubo puede inicializarlo con el perfil ya configurado. La operación usa la ruta de ejecutable y `IPFS_PATH` configurados en Node Core OS, con los permisos del usuario que inició el servidor. El endpoint valida Host, Origin, Content-Type, tamaño del cuerpo y el campo `confirm: true`; no permite ejecutar comandos arbitrarios ni expone la API RPC de Kubo al navegador.
