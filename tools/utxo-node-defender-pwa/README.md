# UTXO NODE DEFENDER — Android PWA (prototipo v0.1)

## Estado honesto
Esta primera entrega es una PWA instalable en Android desde HTTPS o localhost. Implementa:
- generación Ed25519 con Web Crypto;
- clave privada marcada como no exportable;
- persistencia local del objeto CryptoKey en IndexedDB (según soporte del navegador);
- manifiesto JSON firmado y exportable;
- verificación criptográfica de firma, huella SHA-256 y node_id;
- service worker para caché básica.

El manifiesto se marca explícitamente `SELF_SIGNED_UNTRUSTED`. La firma propia demuestra control de la clave, no identidad civil ni confianza de Node Core OS.

## Lo que NO implementa
- no emite X.509 ni NODE-PKI-BINDING;
- no valida un outpoint UTXO ni consume una autorización;
- no crea ledger, transacciones, consenso, doble gasto distribuido ni finality;
- no publica en IPFS;
- no protege contra navegador comprometido, extracción por malware con control de sesión, pérdida de datos del sitio o restauración de fábrica;
- no sincroniza la clave privada entre dispositivos.

No introduzcas secretos ni datos personales reales en este prototipo.

## Instalación en Motorola Android
1. Publica esta carpeta en un servidor HTTPS de confianza (o sirve desde localhost durante desarrollo).
2. Abre la URL en Chrome para Android.
3. Menú ⋮ → **Instalar aplicación** o **Añadir a pantalla principal**.
4. Abre UTXO NODE DEFENDER y crea la identidad.
5. Mantén el dispositivo protegido con bloqueo de pantalla y copias de seguridad del dispositivo.
6. No borres los datos del sitio: la clave local podría perderse.

Abrir `index.html` directamente como archivo (`file://`) no permite instalar la PWA y puede bloquear Service Worker/WebCrypto.

## Pruebas manuales
- Crear identidad y confirmar que muestra node_id y fingerprint.
- Recargar y pulsar Cargar identidad local.
- Firmar manifiesto, exportarlo y verificarlo.
- Cambiar un carácter de `purpose` o `signature` y confirmar que la verificación falla.
- Abrir el manifiesto en otro dispositivo: se podrá verificar la firma, pero no se transfiere la clave privada ni se confiere confianza.

## Siguiente integración
La versión de producción debe consumir los contratos existentes en `node_core/security/node_pki_guard.py`, `node_pki_guard_backend.py`, `node_pki_guard_utxo.py` y el backend `StandaloneSQLiteBackend`. La interfaz web no debe implementar por su cuenta la lógica autoritativa UTXO. Se requiere un servicio local autenticado, autorización explícita, protección CSRF/origin, rate limiting, persistencia y recibos verificables. La integración Network requiere un adaptador real y pruebas multi-nodo; SQLite solo demuestra ACID en un host.
