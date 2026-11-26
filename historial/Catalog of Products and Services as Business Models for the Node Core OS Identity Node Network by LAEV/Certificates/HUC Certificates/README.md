# LAEV HUC Standalone 0.7.0

**Certificate-native validation — sin nodos, sin blockchain y sin moneda.**

HUC Standalone conserva tres componentes que trabajan en paralelo:

1. **X.509:** certificado digital estándar que vincula un sujeto con una clave pública.
2. **HUC-CC:** certificado complementario firmado por el emisor. Vincula el hash DER de X.509, la política HUC y la salida UTXO inicial.
3. **HUC-UTXO:** estado lógico firmado por el emisor. Registra si el certificado está `ACTIVE`, `SUPERSEDED` o `REVOKED`.

El titular presenta un paquete autónomo. El verificador valida las firmas y el estado usando una huella de confianza entregada por un canal independiente. No hay validadores, red de nodos, blockchain, minería, tokens ni comisiones de protocolo.

## ¿Hay comunicación entre el certificado y el lugar donde se utiliza?

No es obligatoria. La verificación básica funciona offline con el paquete de evidencia. Para aplicaciones que requieren comprobar que el presentador controla la clave privada, HUC incorpora **HUC Direct Exchange**, un desafío-respuesta entre el verificador y el titular:

1. La aplicación genera un desafío con nonce aleatorio, audiencia y vencimiento.
2. El titular firma el desafío con la clave privada correspondiente al X.509.
3. El titular devuelve la respuesta junto con el paquete de certificado.
4. La aplicación comprueba el desafío, la firma del titular, el X.509, HUC-CC y la atestación de estado del emisor.
5. El verificador consume el nonce para impedir reutilización.

Los mensajes son JSON transportables por QR, NFC, Bluetooth, Nearby Share, correo o cualquier canal seguro. HUC no abre sockets, no requiere servidor de relay y no mantiene nodos. El intercambio es directo a nivel de protocolo; el transporte lo elige la aplicación.

## Importante: qué significa HUC-CC en esta versión

En Standalone 0.7 el HUC-CC es una **atestación protocolaria firmada por el emisor**, no un consenso BFT ni una votación entre instituciones independientes. La política fija al emisor como autoridad de emisión y de estado. Esta es la decisión que permite eliminar los nodos. La validez del documento se acredita con firmas; no se afirma que exista consenso distribuido.

## Instalación

Python 3.10 o posterior. En Termux:

```bash
pkg update
pkg install python
python -m pip install -r requirements.txt
```

## Flujo completo

### 1. Inicializar el emisor

```bash
python huc_standalone.py init \
  --workspace ./huc-workspace \
  --issuer-id LAEV-ISSUER \
  --state-ttl-seconds 300
```

El comando muestra `trust_anchor_sha256`. Guarda esa huella y entrégala al verificador por un canal independiente del paquete. No confíes en una huella obtenida exclusivamente del mismo ZIP que se verifica.

### 2. El titular genera su clave y CSR

```bash
python huc_standalone.py request \
  --out-dir ./holder \
  --name "Nombre del titular"
```

El resultado incluye el CSR y una clave privada del titular. La clave privada no se envía al emisor ni se incluye en el paquete del certificado.

### 3. Emitir X.509 + HUC-CC + UTXO

```bash
python huc_standalone.py issue \
  --workspace ./huc-workspace \
  --csr ./holder/RUTA_SOLICITUD.csr.pem \
  --days 365
```

El emisor produce el certificado X.509, el certificado complementario HUC-CC, un evento UTXO firmado y una atestación actual de estado.

### 4. Crear el paquete portátil

```bash
python huc_standalone.py bundle \
  --workspace ./huc-workspace \
  --certificate ./huc-workspace/certificates/certificate-HASH.pem \
  --output ./credential-package.zip
```

El ZIP contiene únicamente material público: CA, clave pública del emisor, política, ancla, X.509, HUC-CC y atestación UTXO firmada. Nunca contiene claves privadas.

### 5. Verificar offline

```bash
python huc_standalone.py verify-bundle \
  --bundle ./credential-package.zip \
  --trust-anchor-sha256 HUELLA_EXTERNA_DEL_ANCLA
```

Resultados:

- `VALID`: X.509, HUC-CC, firmas y estado activo con evidencia suficientemente reciente.
- `INVALID`: certificado expirado, revocado o sustituido.
- `INDETERMINATE`: evidencia de estado vencida o demasiado antigua para garantizar vigencia.

La antigüedad máxima por defecto es 300 segundos. Se puede ajustar con `--max-state-age-seconds`, respetando la política y el riesgo de la aplicación.

### 6. Comunicación directa opcional — challenge/response

La aplicación/verificador genera un desafío:

```bash
python huc_standalone.py challenge \
  --certificate-sha256 HASH_DER_DEL_X509 \
  --audience "rrhh.empresa.example" \
  --ttl-seconds 120 \
  --output ./challenge.json
```

El verificador entrega `challenge.json` al titular. El titular crea una respuesta con el paquete y su clave privada:

```bash
python huc_standalone.py respond \
  --challenge ./challenge.json \
  --bundle ./credential-package.zip \
  --private-key ./holder/CLAVE_PRIVADA.pem \
  --output ./response.json
```

El titular devuelve `response.json`. El verificador comprueba la respuesta:

```bash
python huc_standalone.py verify-response \
  --challenge ./challenge.json \
  --response ./response.json \
  --trust-anchor-sha256 HUELLA_EXTERNA_DEL_ANCLA \
  --audience "rrhh.empresa.example" \
  --replay-store ./used-nonces.json
```

El replay store conserva los nonces consumidos en el dispositivo verificador. En una aplicación real debe guardarse en almacenamiento persistente y protegido.

### 7. Renovar

El titular genera un CSR nuevo con el mismo sujeto; luego el emisor ejecuta:

```bash
python huc_standalone.py renew \
  --workspace ./huc-workspace \
  --certificate ./RUTA_CERTIFICADO_ANTERIOR.pem \
  --csr ./RUTA_CSR_NUEVO.csr.pem \
  --days 365
```

El UTXO anterior se consume, el certificado anterior pasa a `SUPERSEDED` y se crea un certificado nuevo con una salida distinta.

### 8. Revocar

```bash
python huc_standalone.py revoke \
  --workspace ./huc-workspace \
  --certificate ./RUTA_CERTIFICADO_ACTIVO.pem \
  --reason "key-compromise"
```

La revocación consume el UTXO activo y produce una nueva atestación firmada con estado `REVOKED`.

Para generar un nuevo estado firmado sin cambiar el estado:

```bash
python huc_standalone.py refresh-status \
  --workspace ./huc-workspace \
  --certificate ./RUTA_CERTIFICADO.pem
```

Luego se crea y distribuye un nuevo paquete con `bundle`.

## Ejecutar demostración y pruebas

```bash
python demo/build_demo.py
python -m unittest discover -s tests -v
```

`demo/standalone/` contiene paquetes públicos de ejemplo: activo, renovado activo, anterior sustituido, revocado, challenge y respuesta directa. La demostración no incluye claves privadas.

## Qué se elimina frente a HUC Network

- No se crean validadores ni nodos.
- No hay membresía de red, quórum 3-de-4 ni view-change.
- No hay replicación entre libros de varios nodos.
- No hay protocolo P2P de nodos ni servidor de relay.

El estado UTXO se mantiene en el workspace del emisor y se acredita mediante una atestación digital firmada. El paquete transporta esa atestación al verificador.

## Límites de seguridad

- La autoridad emisora es la fuente de confianza del estado UTXO. Esta versión cambia descentralización de validadores por simplicidad operativa y verificabilidad criptográfica.
- La evidencia offline tiene una ventana de frescura limitada. Un certificado revocado después de emitirse una atestación `ACTIVE` podría parecer vigente hasta que caduque esa atestación. El verificador debe exigir evidencia reciente o recibir un paquete actualizado.
- HUC Direct demuestra posesión de la clave privada del titular y evita replay local; no revela por sí solo una revocación que no esté reflejada en el paquete.
- El transporte QR/Bluetooth/NFC no cifra ni autentica por sí mismo el canal. La aplicación debe aplicar sus controles de privacidad y transporte.
- Las claves privadas demo se guardan sin contraseña para facilitar pruebas. No usar en producción; hace falta HSM/KMS o almacén seguro.
- El nombre del CSR no prueba identidad civil. Se requiere un proceso de verificación de identidad del emisor.
- No hay OCSP/CRL, timestamp de tercero, HSM/KMS, API pública ni auditoría externa.
- La canonicalización JSON es un perfil restringido propio; antes de interoperabilidad multi-lenguaje de producción debe completarse RFC 8785/JCS y sus vectores de prueba.
- HUC-CC 0.7 utiliza una firma del emisor. No equivale a consenso multiinstitucional ni BFT. Si se requieren aprobaciones de varias entidades, se puede añadir firma múltiple offline sin crear una red de nodos.

**No usar esta versión de laboratorio para TLS público, identidad legal, pagos, acceso crítico o cumplimiento regulatorio.**
