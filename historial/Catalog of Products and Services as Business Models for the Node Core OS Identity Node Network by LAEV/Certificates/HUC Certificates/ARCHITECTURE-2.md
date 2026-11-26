# Arquitectura LAEV HUC Standalone 0.7

```text
TITULAR
  | clave privada permanece en su dispositivo
  | CSR / paquete de credencial
  v
EMISOR HUC
  | firma X.509 con CA
  | firma HUC-CC con Ed25519
  | mantiene ledger UTXO local
  | firma State Attestation
  v
PAQUETE AUTÓNOMO
  | X.509 + HUC-CC + UTXO State Attestation
  | CA pública + clave pública + política + trust anchor
  v
VERIFICADOR / APLICACIÓN
  | verificación offline
  | o challenge-response opcional con titular
  v
VALID / INVALID / INDETERMINATE
```

## Roles

- **Emisor:** crea X.509, HUC-CC, eventos UTXO y atestaciones de estado.
- **Titular:** conserva su clave privada, transporta el paquete y firma desafíos cuando la aplicación solicita prueba de posesión.
- **Verificador:** verifica el pin de confianza, las firmas, las vinculaciones y la frescura del estado.

## Qué evita

No hay un proceso de consenso entre nodos. No existe una red de nodos. No hay líder, comité, quórum distribuido ni sincronización de ledgers entre validadores.

## Comunicación directa

HUC Direct es una interacción opcional a nivel de protocolo entre titular y aplicación. El verificador genera el desafío; el titular firma y devuelve el paquete. Los mensajes son transportables; HUC no impone un medio físico ni levanta servidores. Por ello puede funcionar incluso si el intercambio es por QR o archivo.

## Autoridad de estado

El emisor conserva la fuente de estado UTXO en su workspace. La atestación firmada permite verificar una instantánea del estado sin consultar una red. Esto simplifica la operación, pero centraliza la autoridad del estado en el emisor. La frescura temporal y el proceso de revocación son controles obligatorios.
