"""Terminal forms for the initial local BTC exchange request prototype."""
from typing import Any

from applications.p2p_contracts.p2p_contracts.service import P2PContractsError, P2PContractsService


class P2PContractsCLI:
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.service = P2PContractsService(runtime.storage, runtime.identity_profile, runtime.network)

    @staticmethod
    def _ask(label: str, optional: bool = False) -> str:
        value = input(f"{label}: ").strip()
        if not optional and not value:
            raise ValueError(f"{label} is required.")
        return value

    def run(self) -> None:
        while True:
            print("\nNode Core OS — P2P Contracts (prototipo local)\n")
            print("1. Crear solicitud pública de intercambio BTC")
            print("2. Añadir evidencia o resultado a una solicitud")
            print("3. Buscar solicitud por ID")
            print("4. Ver manifiesto local actual")
            print("0. Volver")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            try:
                if choice == "1":
                    self.create_request_form()
                elif choice == "2":
                    self.create_evidence_form()
                elif choice == "3":
                    self.search_request_form()
                elif choice == "4":
                    self.show_manifest()
                else:
                    print("Elige una opción disponible.")
                    continue
            except (ValueError, P2PContractsError, OSError, RuntimeError) as exc:
                print(f"Operación no completada: {exc}")
            input("\nPulsa Enter para continuar...")

    def create_request_form(self) -> None:
        profile = self.runtime.identity_profile.load()
        node = self.runtime.network.identity()
        print("\nSOLICITUD PÚBLICA: INTERCAMBIO BTC")
        print(f"ID técnico del nodo: {node.peer_id}")
        available_keys = []
        if profile:
            print("Perfil de identidad local encontrado. Campos disponibles para publicar:")
            for key in ("identity_id", "full_name", "alias", "nationality", "issuing_country",
                        "document_type", "document_number", "birth_date", "height_cm", "gender"):
                if profile.get(key) not in (None, ""):
                    available_keys.append(key)
                    print(f"  {key}: {profile[key]}")
        else:
            print("No hay perfil de identidad local; se usará únicamente el ID técnico del nodo.")

        publish_identity = False
        identity_fields = set()
        if profile and available_keys:
            consent = input(
                "¿Autorizas incluir en la solicitud los campos de identidad que selecciones? [s/N]: "
            ).strip().lower()
            publish_identity = consent in {"s", "si", "sí", "y", "yes"}
            if publish_identity:
                selected = input("Campos a publicar separados por coma (Enter = todos los mostrados): ").strip()
                identity_fields = set(available_keys) if not selected else {
                    item.strip() for item in selected.split(",") if item.strip()
                }
                unknown = identity_fields - set(available_keys)
                if unknown:
                    raise ValueError(f"Campos de identidad no disponibles: {', '.join(sorted(unknown))}")

        print("\nContacto público: añade al menos un método. Estos valores se guardarán en la solicitud.")
        contacts = []
        while True:
            print("Tipos: email, phone, pgp_public_key, office, external_protocol, other")
            kind = self._ask("Tipo de contacto (Enter para terminar)", optional=True).lower()
            if not kind:
                break
            contacts.append({"type": kind, "value": self._ask("Dato de contacto")})
            more = input("¿Añadir otro método de contacto? [s/N]: ").strip().lower()
            if more not in {"s", "si", "sí", "y", "yes"}:
                break
        if not contacts:
            raise ValueError("Debes añadir al menos un método de contacto.")
        btc_amount = self._ask("Cantidad de BTC que ofreces")
        receive_asset = self._ask("Moneda o activo que deseas recibir (por ejemplo USDT, EUR, ETH)")
        receive_amount = self._ask("Cantidad del activo que solicitas")
        receive_network = self._ask("Red del activo, si corresponde (Enter si no aplica)", optional=True)
        description = self._ask("Condiciones y descripción de la solicitud")
        print("\nRESUMEN")
        print(f"BTC ofrecido: {btc_amount}")
        print(f"Activo solicitado: {receive_amount} {receive_asset.upper()}")
        print(f"Red: {receive_network or 'No especificada'}")
        print(f"Métodos de contacto: {len(contacts)}")
        print(f"Campos de identidad a incluir: {', '.join(sorted(identity_fields)) if publish_identity else 'ninguno'}")
        print("La solicitud se guardará localmente. Esta versión aún no la propaga a otros nodos.")
        confirm = input("¿Crear la solicitud y actualizar el manifiesto local? [s/N]: ").strip().lower()
        if confirm not in {"s", "si", "sí", "y", "yes"}:
            print("Operación cancelada; no se creó la solicitud.")
            return
        result = self.service.create_btc_exchange_request(
            btc_amount=btc_amount, receive_asset=receive_asset, receive_amount=receive_amount,
            receive_network=receive_network, description=description, contacts=contacts,
            publish_identity=publish_identity, identity_fields=identity_fields,
        )
        print("\nSolicitud creada y guardada localmente.")
        print(f"ID de solicitud: {result['request_id']}")
        print(f"Hash de la solicitud: {result['request_hash']}")
        print(f"Hash del manifiesto: {result['manifest_hash']}")
        print(f"Secuencia del manifiesto: {result['manifest_sequence']}")
        print(f"Ruta del manifiesto: {result['manifest_path']}")
        print("Estado: LOCAL_ONLY — todavía no visible para otros nodos.")

    def create_evidence_form(self) -> None:
        print("\nEVIDENCIA / RESULTADO DE SOLICITUD")
        request_id = self._ask("ID de la solicitud")
        print("Tipos: response, exchange_result, follow_up")
        evidence_type = self._ask("Tipo de evidencia").lower()
        print("Resultados: response_received, offer_received, no_response, exchange_completed, not_completed, cancelled, disputed")
        outcome = self._ask("Resultado").lower()
        description = self._ask("Descripción de lo ocurrido")
        statement = self._ask("Declaración del informante")
        reference = self._ask("Referencia externa opcional (CID, identificador o URL)", optional=True)
        print("La evidencia se guardará como declaración propia no verificada.")
        confirm = input("¿Añadir evidencia y actualizar el manifiesto local? [s/N]: ").strip().lower()
        if confirm not in {"s", "si", "sí", "y", "yes"}:
            print("Operación cancelada.")
            return
        result = self.service.create_request_evidence(
            request_id=request_id, outcome=outcome, evidence_type=evidence_type,
            description=description, reporter_statement=statement, external_reference=reference,
        )
        print(f"Evidencia creada: {result['evidence_id']}")
        print(f"Hash de evidencia: {result['evidence_hash']}")
        print(f"Hash de manifiesto: {result['manifest_hash']}")
        print(f"Resultado registrado: {result['outcome']} (no verificado)")

    def search_request_form(self) -> None:
        request_id = self._ask("ID de la solicitud que deseas consultar")
        result = self.service.find_request(request_id)
        if result is None:
            print("No se encontró ese ID en el manifiesto local.")
            print("Esta consulta todavía no busca en otros nodos.")
            return
        request = result["request"]
        exchange = request.get("exchange", {})
        print("\nRESULTADO DE CONSULTA")
        print(f"ID: {request['request_id']}")
        print(f"Creada: {request.get('created_at')}")
        print(f"BTC ofrecido: {exchange.get('give_amount')} BTC")
        print(f"Activo solicitado: {exchange.get('receive_amount')} {exchange.get('receive_asset')}")
        print(f"Estado derivado: {result['request_status']}")
        print(f"Registros de evidencia: {len(result['evidence'])}")
        for item in result["evidence"]:
            print(f"- {item['evidence_id']}: {item['outcome']} | {item['verification_status']} | {item['created_at']}")
        print(f"Hash del manifiesto: {result['manifest_hash']}")

    def show_manifest(self) -> None:
        manifest = self.service.current_manifest()
        if manifest is None:
            print("Todavía no existe un manifiesto local de P2P Contracts.")
            return
        print(f"Secuencia: {manifest['sequence']}")
        print(f"Hash: {manifest['manifest_hash']}")
        print(f"Hash anterior: {manifest['previous_manifest_hash']}")
        print(f"Solicitudes: {len(manifest['requests'])}")
        print(f"Registros de evidencia: {len(manifest['evidence'])}")
        print("Este es el manifiesto local; no se ha sincronizado con la red.")
