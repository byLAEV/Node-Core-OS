"""English terminal interface for Node Core OS P2P Contracts v0.1."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any

from applications.p2p_contracts.p2p_contracts.propagation import (
    PropagationProtocol, PubSubUnavailable, parse_timestamp,
)
from applications.p2p_contracts.p2p_contracts.service import P2PContractsError, P2PContractsService


class P2PContractsCLI:
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.service = P2PContractsService(runtime.storage, runtime.identity_profile, runtime.network)
        self.propagation = PropagationProtocol(runtime.storage, runtime.network, runtime.kubo, service=self.service)
        self._stop_event = threading.Event()
        self._auto_submit_lock = threading.Lock()

    @staticmethod
    def _ask(label: str, optional: bool = False) -> str:
        value = input(f"{label}: ").strip()
        if not optional and not value:
            raise ValueError(f"{label} is required.")
        return value

    @staticmethod
    def _yes(prompt: str) -> bool:
        return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}

    def run(self) -> None:
        print("\nNODE CORE OS — P2P CONTRACTS")
        profile = self.runtime.identity_profile.load()
        node = self.runtime.network.identity()
        print(f"Node ID: {node.peer_id}")
        if not profile:
            print("No local identity profile was found. Create one in Node Core OS first.")
            input("Press Enter to return...")
            return
        print("\nIdentity fields available to this application:")
        for key in ("identity_id", "full_name", "alias"):
            if profile.get(key):
                print(f"  {key}: {profile[key]}")
        if not self._yes("Do you accept that P2P Contracts may use your existing Node Core OS identity locally?"):
            print("Identity consent was not granted. Returning to Node Core OS.")
            return
        try:
            state = self.propagation.current_state()
            if state and state.get("require_owner_request") and not state.get("owner_request_sent") and state.get("status") in {"ACCEPTED", "READY_TO_SUBMIT"}:
                self.propagation.start()
                self._start_owner_auto_submit()
            while True:
                print("\n========================================")
                print("       NODE CORE OS P2P CONTRACTS")
                print("========================================")
                print("1. Create Public Request")
                print("2. Create Private Request (not available yet)")
                print("3. Create Request Closure")
                print("4. Search Request ID")
                print("0. Exit P2P Contracts")
                choice = input("\nSelect an option: ").strip()
                try:
                    if choice == "0":
                        return
                    if choice == "1":
                        self.public_request_menu()
                    elif choice == "2":
                        print("Private requests are disabled until OpenPGP encryption is implemented and tested.")
                    elif choice == "3":
                        self.create_closure_form()
                    elif choice == "4":
                        self.search_request_form()
                    else:
                        print("Choose an available option.")
                except (ValueError, P2PContractsError, PubSubUnavailable, OSError, RuntimeError) as exc:
                    print(f"Operation not completed: {exc}")
                input("\nPress Enter to continue...")
        finally:
            self._stop_event.set()
            self.propagation.stop()


    def public_request_menu(self) -> None:
        while True:
            state = self.propagation.current_state()
            if state and state.get("status") == "READY_TO_SUBMIT" and state.get("require_owner_request") and not state.get("owner_request_sent"):
                self.submit_owner_draft_if_ready(state)
                state = self.propagation.current_state()
            print("\n--- CREATE PUBLIC REQUEST ---")
            print("1. Check Propagation Hash Status")
            print("2. Accept a New Propagation Hash")
            print("3. View Propagation Status")
            enabled = bool(state and state.get("status") == "READY_TO_SUBMIT" and not state.get("require_owner_request") and not state.get("owner_request_sent"))
            own_status = "AUTOMATICALLY SENT" if state and state.get("owner_request_sent") else ("ENABLED" if enabled else "LOCKED")
            print(f"4. Create This Node's BTC Exchange Request ({own_status})")
            print("5. Submit a BTC Exchange Request to the Active Propagation")
            print("0. Back")
            choice = input("\nSelect an option: ").strip()
            if choice == "0":
                return
            if choice == "1":
                self.check_propagation_status()
            elif choice == "2":
                self.accept_propagation()
            elif choice == "3":
                self.show_propagation_status()
            elif choice == "4":
                state = self.propagation.current_state()
                if not state or state.get("status") != "READY_TO_SUBMIT" or state.get("require_owner_request") or state.get("owner_request_sent"):
                    print("This propagation's owner request is prepared and submitted automatically with the peer batch; a second owner request is not enabled in the same propagation.")
                else:
                    self.create_request_form()
            elif choice == "5":
                self.submit_to_active_propagation()
            else:
                print("Choose an available option.")

    def check_propagation_status(self) -> None:
        print("\nChecking local state and requesting status from PubSub peers...")
        result = self.propagation.query_status()
        print(f"Status: {result['status']}")
        print(f"Peer responses: {len(result['responses'])}")
        if result["active_proposals"]:
            for proposal in result["active_proposals"]:
                print(f"Proposal hash: {proposal.get('proposal_hash')}")
                print(f"Proposing node: {proposal.get('proposer_node_id')}")
                print(f"Proposal state: {proposal.get('status')}")
            print("Remote claims are UNVERIFIED. This prototype cannot establish global consensus.")
        elif result["status"] == "NO_NODE_RESPONSES":
            print("No peer responded. Do not treat this as proof that no proposal exists.")
        else:
            print("No active proposal was reported by the responding peers. This is not a global consensus certificate.")

    def accept_propagation(self) -> None:
        result = self.propagation.query_status()
        if result["active_proposals"]:
            print("An active proposal was reported by a peer. It is not safe to create a competing proposal in this prototype.")
            print("Submit to the currently active proposal instead of opening a competing propagation window.")
            return
        if not result["responses"]:
            print("Cannot safely accept a propagation: no peer responded. A local timeout is not proof of network-wide availability.")
            return
        manifest = self.service.current_manifest()
        parent_hash = manifest.get("manifest_hash") if manifest else None
        print("No active proposal was reported by the responding peers.")
        print("WARNING: this experimental version cannot prove global absence or enforce a network-wide exclusive lease.")
        if not self._yes("Accept a local ten-minute propagation window and announce it to Kubo PubSub?"):
            print("Propagation acceptance cancelled.")
            return
        print("Before accepting propagation, prepare this node's own public BTC exchange request.")
        if not self.create_request_form(draft_only=True):
            print("Propagation acceptance cancelled because the owner request draft was not saved.")
            return
        recheck = self.propagation.query_status()
        if recheck["active_proposals"]:
            print("Another active propagation appeared while this node's request was being prepared. This node will not open a competing window.")
            return
        state = self.propagation.accept_new_propagation(parent_hash, require_owner_request=True)
        print("\nPROPAGATION ACCEPTED")
        print(f"Propagation hash: {state['proposal_hash']}")
        print(f"Accepted at: {state['accepted_at']}")
        print(f"Automatic batch submission time: {state['send_enabled_at']}")
        print("Incoming peer requests and this node's prepared request will be included in one manifest transition.")
        print("Keep Node Core OS and Kubo running. This remains an experimental, non-global lease.")
        self._start_owner_auto_submit()

    def show_propagation_status(self) -> None:
        state = self.propagation.current_state()
        if not state:
            print("No local propagation has been accepted.")
            return
        print(f"Propagation hash: {state['proposal_hash']}")
        print(f"Proposer node: {state['proposer_node_id']}")
        print(f"Status: {state['status']}")
        print(f"Accepted at: {state['accepted_at']}")
        print(f"Submission enabled at: {state['send_enabled_at']}")
        if state["status"] == "ACCEPTED":
            remaining = max(0, int((parse_timestamp(state["send_enabled_at"]) - datetime.now(timezone.utc)).total_seconds()))
            print(f"Time remaining: {remaining // 60:02d}:{remaining % 60:02d}")
            print("The request form remains locked until the timestamp.")
        elif state["status"] == "READY_TO_SUBMIT":
            print("The local timer has elapsed.")
            print(f"Queued/owner batch finalized: {bool(state.get('batch_flushed'))}")
            print(f"Owner request automatically submitted: {bool(state.get('owner_request_sent'))}")
            if not state.get("batch_flushed") and state.get("require_owner_request"):
                print("The owner request draft and incoming peer requests are waiting for automatic batch submission.")
        elif state["status"] == "CANCELLED":
            print(f"Cancellation reason: {state.get('cancel_reason', 'Not specified')}")


    def submit_to_active_propagation(self) -> None:
        print("\nChecking for an active propagation proposal from connected peers...")
        result = self.propagation.query_status()
        if not result["responses"]:
            print("No peer responded. A new submission cannot be safely routed.")
            return
        proposals = result["active_proposals"]
        if not proposals:
            print("No active propagation proposal was reported by responding peers.")
            print("If this node needs to create a new propagation, use option 2 only after checking network status.")
            return
        unique = {item.get("proposal_hash"): item for item in proposals if item.get("proposal_hash")}
        if len(unique) != 1:
            print("Conflicting active propagation hashes were reported. Submission is blocked.")
            for item in unique.values():
                print(f"- {item.get('proposal_hash')} from {item.get('proposer_node_id')}")
            return
        proposal = next(iter(unique.values()))
        if proposal.get("proposer_node_id") == self.runtime.network.identity().peer_id:
            print("This node owns the active propagation. Use option 4 after the timer unlocks.")
            return
        print(f"Active propagation hash: {proposal.get('proposal_hash')}")
        print(f"Receiving node ID: {proposal.get('proposer_node_id')}")
        print(f"Submission window closes at: {proposal.get('send_enabled_at')}")
        if not self._yes("Prepare a public BTC exchange request for this propagation node?"):
            print("Request submission cancelled.")
            return
        self.create_request_form(remote_proposal=proposal)

    def create_request_form(self, remote_proposal: dict[str, Any] | None = None, draft_only: bool = False) -> bool:
        profile = self.runtime.identity_profile.load() or {}
        node = self.runtime.network.identity()
        print("\n--- PUBLIC BTC EXCHANGE REQUEST ---")
        print(f"Node ID: {node.peer_id}")
        for address in node.addresses:
            print(f"Node address: {address}")
        available = [key for key in ("identity_id", "full_name", "alias", "nationality", "issuing_country",
                                     "document_type", "document_number") if profile.get(key) not in (None, "")]
        selected = set()
        if available and self._yes("Include selected personal identity fields in this PUBLIC request?"):
            print("Available fields: " + ", ".join(available))
            raw = self._ask("Fields to publish (comma-separated; Enter selects none)", optional=True)
            selected = {item.strip() for item in raw.split(",") if item.strip()}
            unknown = selected - set(available)
            if unknown:
                raise ValueError("Unknown identity fields: " + ", ".join(sorted(unknown)))
        contacts = []
        print("Contact types: email, phone, pgp_public_key, office, external_protocol, other")
        while True:
            kind = self._ask("Contact type (Enter to finish)", optional=True).lower()
            if not kind:
                break
            contacts.append({"type": kind, "value": self._ask("Contact value")})
            if not self._yes("Add another contact method?"):
                break
        if not contacts:
            raise ValueError("At least one contact method is required.")
        btc_amount = self._ask("BTC amount offered")
        asset = self._ask("Asset to receive (e.g. USDT, EUR, ETH)")
        receive_amount = self._ask("Amount of asset requested")
        receive_network = self._ask("Asset network, if applicable", optional=True)
        description = self._ask("Public exchange conditions")
        print("\nSUMMARY")
        print(f"Offer: {btc_amount} BTC")
        print(f"Request: {receive_amount} {asset.upper()}")
        print(f"Contact methods: {len(contacts)}")
        print("Identity fields to publish: " + (", ".join(sorted(selected)) if selected else "none"))
        confirm_text = ("Save this request as a local draft for automatic propagation submission?"
                        if draft_only else "Create this request in the local append-only manifest?")
        if not self._yes(confirm_text):
            print("Request creation cancelled.")
            return False
        if draft_only:
            draft = {
                "btc_amount": btc_amount, "receive_asset": asset, "receive_amount": receive_amount,
                "receive_network": receive_network, "description": description, "contacts": contacts,
                "publish_identity": bool(selected), "identity_fields": sorted(selected),
            }
            draft_path = self.runtime.storage.path("p2p_contracts/propagation/owner-request-draft.json")
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = draft_path.with_suffix(".tmp")
            temporary_path.write_text(json.dumps(draft, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, draft_path)
            print("Owner request draft saved locally. It has not been published or appended to the manifest.")
            return True
        result = self.service.create_btc_exchange_request(
            btc_amount=btc_amount, receive_asset=asset, receive_amount=receive_amount,
            receive_network=receive_network, description=description, contacts=contacts,
            publish_identity=bool(selected), identity_fields=selected,
        )
        print("Request saved locally.")
        print(f"Request ID: {result['request_id']}")
        print(f"Request hash: {result['request_hash']}")
        print(f"Manifest hash: {result['manifest_hash']}")
        request_document = json.loads(Path(result["request_path"]).read_text(encoding="utf-8"))
        if remote_proposal is not None:
            acknowledgement = self.propagation.submit_request(remote_proposal, request_document)
            if acknowledgement.get("accepted"):
                print("Propagation node acknowledged the request for inclusion in its pending batch.")
                print(f"Target node: {remote_proposal.get('proposer_node_id')}")
            else:
                print("Request remains saved locally but was NOT acknowledged by the propagation node.")
                print(f"Reason: {acknowledgement.get('reason', 'No reason provided.')}")
        else:
            broadcast = self.propagation.publish_request(request_document)
            print(f"Network acknowledgements received: {len(broadcast['peer_acknowledgements'])}")
            print("Request broadcast attempted. Peers without acknowledgements may not have imported it.")
        return True

    def _start_owner_auto_submit(self) -> None:
        if self._stop_event.is_set():
            return
        threading.Thread(target=self._owner_auto_submit_loop, daemon=True, name="p2p-contracts-owner-submit").start()

    def _owner_auto_submit_loop(self) -> None:
        while not self._stop_event.wait(1.0):
            try:
                state = self.propagation.current_state()
                if not state:
                    return
                if state.get("status") == "CANCELLED":
                    return
                if state.get("status") == "READY_TO_SUBMIT" and state.get("require_owner_request") and not state.get("owner_request_sent"):
                    self.submit_owner_draft_if_ready(state)
                    return
            except (ValueError, P2PContractsError, PubSubUnavailable, OSError, RuntimeError) as exc:
                print(f"Automatic propagation submission is waiting for recovery: {exc}")
            time.sleep(0.5)

    def submit_owner_draft_if_ready(self, state: dict[str, Any]) -> None:
        if not self._auto_submit_lock.acquire(blocking=False):
            return
        try:
            current = self.propagation.current_state()
            if not current or current.get("status") != "READY_TO_SUBMIT" or current.get("owner_request_sent"):
                return
            draft_path = self.runtime.storage.path("p2p_contracts/propagation/owner-request-draft.json")
            if not draft_path.is_file():
                print("Automatic submission cannot proceed: the local owner request draft is missing.")
                return
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            request_document = draft.get("request_document")
            if not isinstance(request_document, dict):
                result = self.service.create_btc_exchange_request(
                    btc_amount=draft["btc_amount"], receive_asset=draft["receive_asset"],
                    receive_amount=draft["receive_amount"], receive_network=draft["receive_network"],
                    description=draft["description"], contacts=draft["contacts"],
                    publish_identity=bool(draft["publish_identity"]),
                    identity_fields=set(draft["identity_fields"]), defer_manifest=True,
                )
                request_document = json.loads(Path(result["request_path"]).read_text(encoding="utf-8"))
                draft["request_document"] = request_document
                temporary_path = draft_path.with_suffix(".tmp")
                temporary_path.write_text(json.dumps(draft, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
                os.chmod(temporary_path, 0o600)
                os.replace(temporary_path, draft_path)
            result = self.propagation.finalize_propagation(request_document)
            draft_path.unlink(missing_ok=True)
            print("\nPROPAGATION BATCH SUBMITTED")
            print(f"Owner request ID: {request_document['request_id']}")
            print(f"Requests included in the manifest transition: {result.get('batch_request_count', result.get('imported_count', 0))}")
            print(f"Manifest hash: {result.get('manifest_hash')}")
            print("The owner request and queued peer requests were broadcast as one request batch.")
        finally:
            self._auto_submit_lock.release()

    def create_closure_form(self) -> None:
        print("\n--- CREATE REQUEST CLOSURE / REPUTATION EVIDENCE ---")
        request_id = self._ask("Request ID")
        existing = self.service.find_request(request_id)
        if existing is None:
            raise ValueError("Request ID was not found in the local application manifest.")
        target_node = self._ask("Evaluated counterparty node ID")
        rating_text = self._ask("Rating from 1 to 5")
        if not rating_text.isdigit() or not 1 <= int(rating_text) <= 5:
            raise ValueError("Rating must be an integer from 1 to 5.")
        print("Closure states: exchange_completed, not_completed, cancelled, disputed")
        outcome = self._ask("Final request state").lower()
        description = self._ask("Closure description")
        statement = self._ask("Reporter statement")
        print(f"Reporter node ID: {self.runtime.network.identity().peer_id}")
        print(f"Evaluated node ID: {target_node}")
        print(f"Rating: {rating_text}/5")
        print(f"State: {outcome}")
        if not self._yes("Record this self-reported closure evidence?"):
            print("Closure cancelled.")
            return
        result = self.service.create_request_evidence(
            request_id=request_id, outcome=outcome, evidence_type="exchange_result",
            description=description, reporter_statement=statement,
            target_node_id=target_node, rating=int(rating_text),
        )
        print(f"Evidence ID: {result['evidence_id']}")
        print(f"Evidence hash: {result['evidence_hash']}")
        print("Verification status: self_reported_unverified")
        evidence_path = self.runtime.storage.path(f"p2p_contracts/evidence/{result['evidence_id']}.json")
        evidence_document = json.loads(evidence_path.read_text(encoding="utf-8"))
        broadcast = self.propagation.publish_evidence(evidence_document)
        print(f"Evidence broadcast acknowledgements: {len(broadcast['peer_acknowledgements'])}")
        print("Remote nodes verify the evidence hash and import it only if the referenced request is already present.")

    def search_request_form(self) -> None:
        request_id = self._ask("Request ID to search")
        result = self.service.find_request(request_id)
        if result is None:
            print("Request ID was not found in this node's synchronized local manifest.")
            return
        request = result["request"]
        exchange = request.get("exchange", {})
        print("\n--- REQUEST SEARCH RESULT ---")
        print(f"Request ID: {request['request_id']}")
        print(f"Node ID: {request.get('node_id')}")
        print(f"BTC offered: {exchange.get('give_amount')} BTC")
        print(f"Asset requested: {exchange.get('receive_amount')} {exchange.get('receive_asset')}")
        print(f"Derived state: {result['request_status']}")
        print(f"Evidence records: {len(result['evidence'])}")
        for evidence in result["evidence"]:
            print(f"- {evidence['evidence_id']} | state={evidence['outcome']} | reporter={evidence.get('reporter_node_id')} | target={evidence.get('target_node_id')} | rating={evidence.get('rating')} | {evidence['verification_status']}")
        print(f"Manifest hash: {result['manifest_hash']}")
