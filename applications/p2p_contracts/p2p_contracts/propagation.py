"""Experimental Kubo PubSub request propagation for P2P Contracts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import os
import subprocess
import threading
import time
from typing import Any
from uuid import uuid4

TOPIC = "node-core-os/p2p-contracts/propagation/v1"
MESSAGE_SCHEMA = "node-core-os/p2p-contracts/pubsub-message/1"
WINDOW_SECONDS = 600
ACK_WAIT_SECONDS = 5.0


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


class PubSubUnavailable(RuntimeError):
    """Kubo PubSub is unavailable or disabled."""


class PropagationProtocol:
    """Experimental message protocol; peer claims are not cryptographic consensus."""
    def __init__(self, storage: Any, network: Any, kubo: Any, service: Any = None):
        self.storage, self.network, self.kubo, self.service = storage, network, kubo, service
        self.directory = storage.path("p2p_contracts/propagation")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "state.json"
        self.messages_path = self.directory / "received-messages.json"
        self.pending_path = self.directory / "pending-requests.json"
        self._lock = threading.RLock()
        self._received = []
        self._listener_errors = []
        self._pending_requests = []
        self._listener = None
        if self.messages_path.is_file():
            try:
                items = json.loads(self.messages_path.read_text(encoding="utf-8"))
                self._received = items[-1000:] if isinstance(items, list) else []
            except (OSError, json.JSONDecodeError):
                self._received = []
        if self.pending_path.is_file():
            try:
                items = json.loads(self.pending_path.read_text(encoding="utf-8"))
                self._pending_requests = items if isinstance(items, list) else []
            except (OSError, json.JSONDecodeError):
                self._pending_requests = []

    def _state(self):
        if not self.state_path.is_file():
            return None
        try:
            result = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PubSubUnavailable(f"Cannot read propagation state: {exc}") from exc
        return result if isinstance(result, dict) else None

    @staticmethod
    def _atomic_json(path, value):
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)

    def _save_state(self, state):
        self._atomic_json(self.state_path, state)

    def _save_pending(self):
        self._atomic_json(self.pending_path, self._pending_requests)

    def _new_message(self, kind, **fields):
        return {"schema": MESSAGE_SCHEMA, "message_id": str(uuid4()), "created_at": timestamp(utc_now()),
                "sender_node_id": self.network.identity().peer_id, "type": kind, **fields}

    def _publish(self, kind, **fields):
        message = self._new_message(kind, **fields)
        encoded = json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            publisher = getattr(self.kubo, "pubsub_publish", None)
            if callable(publisher):
                publisher(TOPIC, encoded)
            else:
                subprocess.run(
                    [self.kubo.executable, "pubsub", "pub", TOPIC, "-"],
                    env=self.kubo._environment(), input=encoded, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=True, timeout=15,
                )
        except (subprocess.CalledProcessError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", None) or str(exc)
            detail = detail.strip() if isinstance(detail, str) else str(detail)
            raise PubSubUnavailable(f"Kubo PubSub publish failed: {detail}. Check Pubsub.Enabled and Kubo connectivity.") from exc
        return message

    def start(self):
        if self._listener and self._listener.poll() is None:
            return
        if not self.kubo.status().running:
            raise PubSubUnavailable("Kubo daemon is not running.")
        try:
            self._listener = subprocess.Popen(
                [self.kubo.executable, "--enc=json", "pubsub", "sub", TOPIC],
                env=self.kubo._environment(), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as exc:
            raise PubSubUnavailable(f"Could not start PubSub listener: {exc}") from exc
        threading.Thread(target=self._read_loop, daemon=True, name="p2p-contracts-pubsub").start()
        time.sleep(0.2)
        if self._listener.poll() is not None:
            raise PubSubUnavailable("Kubo PubSub listener exited. Check Pubsub.Enabled and Kubo logs.")

    @staticmethod
    def _decode_pubsub_data(value):
        if not isinstance(value, str):
            raise ValueError("PubSub message has no data field.")
        # Kubo JSON output may use base64, base64url, or a multibase prefix.
        candidates = [value]
        if value.startswith("m"):
            candidates.insert(0, value[1:])
        elif value.startswith("u"):
            candidates.insert(0, value[1:])
        for candidate in candidates:
            padded = candidate + "=" * (-len(candidate) % 4)
            decoded_values = []
            try:
                decoded_values.append(base64.b64decode(padded, validate=True))
            except (ValueError, base64.binascii.Error):
                pass
            try:
                decoded_values.append(base64.urlsafe_b64decode(padded))
            except (ValueError, base64.binascii.Error):
                pass
            for decoded in decoded_values:
                if decoded.lstrip().startswith(b"{"):
                    return decoded
        raise ValueError("PubSub message data is not valid base64-encoded JSON.")

    def _remember(self, message):
        with self._lock:
            if any(old.get("message_id") == message["message_id"] for old in self._received):
                return False
            self._received.append(message)
            self._received = self._received[-1000:]
            self._atomic_json(self.messages_path, self._received)
        return True

    def _queue_request(self, message):
        document = message.get("request_document")
        if not isinstance(document, dict):
            raise ValueError("Request submission has no request document.")
        request_id = document.get("request_id")
        requester = document.get("requester")
        if not isinstance(request_id, str) or not isinstance(requester, dict):
            raise ValueError("Request submission is malformed.")
        # The sender field is only a claim in this prototype, not a signed identity.
        if requester.get("node_id") != message.get("sender_node_id"):
            raise ValueError("Requesting node ID does not match the message's claimed sender.")
        with self._lock:
            existing = next((item for item in self._pending_requests if item.get("request_id") == request_id), None)
            if existing is not None:
                if existing.get("document_hash") != document.get("document_hash"):
                    raise ValueError("A conflicting request document reused an ID already in the pending batch.")
            else:
                self._pending_requests.append(document)
                self._save_pending()
        return request_id

    def _handle_message(self, message):
        kind = message.get("type")
        sender = message.get("sender_node_id")
        if kind == "STATUS_QUERY":
            state = self.current_state()
            active = None
            if state and state.get("status") == "ACCEPTED":
                now = utc_now()
                if now < parse_timestamp(state["send_enabled_at"]) and now < parse_timestamp(state["lease_expires_at"]):
                    active = state
            self._publish("STATUS_RESPONSE", reply_to=message["message_id"],
                          queried_by=sender, active_proposal=active)
        elif kind == "PROPOSAL_ANNOUNCE":
            proposal = message.get("proposal") or {}
            self._publish("PROPOSAL_STATUS", proposal_id=proposal.get("proposal_id"),
                          observed_proposal_hash=(self._state() or {}).get("proposal_hash"),
                          observed_status=((self._state() or {}).get("status") or "NONE"))
        elif kind == "REQUEST_SUBMISSION":
            state = self.current_state()
            proposal_id = message.get("proposal_id")
            proposal_hash = message.get("proposal_hash")
            request_id = None
            accepted = False
            reason = "No active propagation window on this node."
            if state and state.get("status") == "ACCEPTED" and utc_now() < parse_timestamp(state["send_enabled_at"]):
                if proposal_id == state.get("proposal_id") and proposal_hash == state.get("proposal_hash"):
                    try:
                        request_id = self._queue_request(message)
                        accepted = True
                        reason = "Request queued for the active propagation batch."
                    except (ValueError, OSError) as exc:
                        reason = str(exc)
                else:
                    reason = "Propagation ID or hash does not match the active proposal."
            self._publish("REQUEST_ACK", reply_to=message["message_id"], request_id=request_id,
                          proposal_id=proposal_id, accepted=accepted, reason=reason,
                          target_node_id=sender)
        elif kind == "REQUEST_BROADCAST":
            document = message.get("request_document")
            if self.service is not None and isinstance(document, dict):
                try:
                    requester = document.get("requester") or {}
                    if requester.get("node_id") != sender:
                        raise ValueError("Request sender ID does not match the request's claimed node ID.")
                    manifest_document = message.get("manifest_document")
                    if isinstance(manifest_document, dict):
                        result = self.service.import_remote_manifest(manifest_document, request_documents=[document])
                    else:
                        result = self.service.import_remote_requests([document])
                    self._publish("REQUEST_ACK", reply_to=message["message_id"],
                                  request_id=document.get("request_id"), accepted=True,
                                  imported_count=result.get("imported_request_count", result.get("imported_count", 0)),
                                  manifest_hash=result.get("manifest_hash"), reason="Public request imported.")
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("REQUEST_ACK", reply_to=message["message_id"],
                                  request_id=document.get("request_id"), accepted=False, reason=str(exc))
        elif kind == "EVIDENCE_BROADCAST":
            document = message.get("evidence_document")
            if self.service is not None and isinstance(document, dict):
                try:
                    if document.get("reporter_node_id") != sender:
                        raise ValueError("Evidence reporter ID does not match the message's claimed sender ID.")
                    manifest_document = message.get("manifest_document")
                    result = self.service.import_remote_evidence(document, manifest_document=manifest_document)
                    self._publish("EVIDENCE_ACK", reply_to=message["message_id"],
                                  evidence_id=document.get("evidence_id"), accepted=True,
                                  imported=result.get("imported", False), manifest_hash=result.get("manifest_hash"),
                                  reason="Evidence verified and imported.")
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("EVIDENCE_ACK", reply_to=message["message_id"],
                                  evidence_id=document.get("evidence_id"), accepted=False, reason=str(exc))
        elif kind == "REQUEST_BATCH":
            documents = message.get("request_documents")
            if self.service is not None and isinstance(documents, list) and documents:
                try:
                    manifest_document = message.get("manifest_document")
                    if isinstance(manifest_document, dict):
                        result = self.service.import_remote_manifest(manifest_document, request_documents=documents)
                        imported_count = result.get("imported_request_count", 0)
                    else:
                        result = self.service.import_remote_requests(documents)
                        imported_count = result.get("imported_count", 0)
                    self._publish("BATCH_ACK", reply_to=message["message_id"],
                                  imported_count=imported_count, manifest_hash=result.get("manifest_hash"))
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("BATCH_ACK", reply_to=message["message_id"], imported_count=0, error=str(exc))

    def _read_loop(self):
        process = self._listener
        if process is None or process.stdout is None:
            return
        try:
            for line in process.stdout:
                try:
                    envelope = json.loads(line)
                    data = envelope.get("data", envelope.get("Data"))
                    message = json.loads(self._decode_pubsub_data(data).decode("utf-8"))
                    if message.get("schema") != MESSAGE_SCHEMA or not message.get("message_id") or not message.get("sender_node_id"):
                        continue
                    if message.get("sender_node_id") == self.network.identity().peer_id:
                        continue
                    if not self._remember(message):
                        continue
                    self._handle_message(message)
                except Exception as exc:
                    # PubSub data is untrusted. A malformed message or validation bug must
                    # be recorded and skipped, not terminate the long-lived listener thread.
                    with self._lock:
                        self._listener_errors.append(f"{type(exc).__name__}: {exc}; output={line[:240].strip()}")
                        self._listener_errors = self._listener_errors[-20:]
                    continue
        except (ValueError, OSError) as exc:
            # stop() may close stdout while this thread is blocked reading it.
            # Treat that shutdown race as a listener event instead of leaking a traceback.
            if process.poll() is None:
                with self._lock:
                    self._listener_errors.append(f"{type(exc).__name__}: {exc}; listener stdout closed unexpectedly")
                    self._listener_errors = self._listener_errors[-20:]

    def query_status(self, wait_seconds=3.0):
        self.start()
        query = self._publish("STATUS_QUERY", known_proposal_hash=(self._state() or {}).get("proposal_hash"))
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 10.0))
        responses = {}
        while time.monotonic() < deadline:
            with self._lock:
                received = list(self._received)
            for item in received:
                if item.get("type") == "STATUS_RESPONSE" and item.get("reply_to") == query["message_id"]:
                    responses[item.get("sender_node_id", "")] = item
            time.sleep(0.1)
        now = utc_now()
        active = []
        for item in responses.values():
            proposal = item.get("active_proposal")
            if not isinstance(proposal, dict) or proposal.get("status") != "ACCEPTED":
                continue
            try:
                if now < parse_timestamp(proposal["send_enabled_at"]) and now < parse_timestamp(proposal["lease_expires_at"]):
                    active.append(proposal)
            except (KeyError, TypeError, ValueError):
                continue
        local_state = self.current_state()
        if local_state and local_state.get("status") == "ACCEPTED":
            try:
                if now < parse_timestamp(local_state["send_enabled_at"]) and now < parse_timestamp(local_state["lease_expires_at"]):
                    active.append(local_state)
            except (KeyError, TypeError, ValueError):
                pass
        unique = {item.get("proposal_hash"): item for item in active if item.get("proposal_hash")}
        return {"responses": list(responses.values()), "active_proposals": list(unique.values()),
                "status": "UNVERIFIED" if unique else ("NO_ACTIVE_PROPOSAL" if responses else "NO_NODE_RESPONSES")}

    def accept_new_propagation(self, parent_manifest_hash, require_owner_request=False):
        self.start()
        now = utc_now()
        node_id = self.network.identity().peer_id
        proposal_id = str(uuid4())
        candidate = json.dumps({"parent_manifest_hash": parent_manifest_hash or "GENESIS",
                                "proposer_node_id": node_id, "proposal_id": proposal_id},
                               sort_keys=True, separators=(",", ":")).encode("utf-8")
        state = {"proposal_id": proposal_id, "proposal_hash": hashlib.sha256(candidate).hexdigest(),
                 "parent_manifest_hash": parent_manifest_hash, "proposer_node_id": node_id,
                 "accepted_at": timestamp(now), "send_enabled_at": timestamp(now + timedelta(seconds=WINDOW_SECONDS)),
                 "lease_expires_at": timestamp(now + timedelta(seconds=WINDOW_SECONDS + 60)),
                 "window_seconds": WINDOW_SECONDS, "status": "ACCEPTED", "batch_flushed": False,
                 "require_owner_request": bool(require_owner_request), "owner_request_sent": False,
                 "warning": "Local proposal state; not a global consensus certificate."}
        self._save_state(state)
        try:
            self._publish("PROPOSAL_ANNOUNCE", proposal=state)
            self._publish("NODE_HEARTBEAT", proposal_id=proposal_id, proposal_hash=state["proposal_hash"], status="ACCEPTED")
        except Exception:
            state["status"] = "CANCELLED"
            state["cancel_reason"] = "Could not announce proposal."
            self._save_state(state)
            raise
        return state

    def submit_request(self, proposal, request_document, wait_seconds=ACK_WAIT_SECONDS):
        self.start()
        request_id = request_document.get("request_id")
        message = self._publish("REQUEST_SUBMISSION", proposal_id=proposal.get("proposal_id"),
                                proposal_hash=proposal.get("proposal_hash"), request_id=request_id,
                                request_document=request_document)
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 15.0))
        while time.monotonic() < deadline:
            with self._lock:
                replies = [item for item in self._received
                           if item.get("type") == "REQUEST_ACK" and item.get("reply_to") == message["message_id"]
                           and item.get("sender_node_id") == proposal.get("proposer_node_id")]
            if replies:
                return replies[-1]
            time.sleep(0.1)
        return {"accepted": False, "request_id": request_id,
                "reason": "No acknowledgement received before timeout."}

    def publish_request(self, request_document, manifest_document=None, wait_seconds=1.5):
        self.start()
        message = self._publish("REQUEST_BROADCAST", request_document=request_document, manifest_document=manifest_document)
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 5.0))
        while time.monotonic() < deadline:
            time.sleep(0.1)
        with self._lock:
            replies = [item for item in self._received
                       if item.get("type") == "REQUEST_ACK" and item.get("reply_to") == message["message_id"]]
        return {"message_id": message["message_id"], "peer_acknowledgements": replies}

    def publish_evidence(self, evidence_document, manifest_document=None, wait_seconds=1.5):
        self.start()
        message = self._publish("EVIDENCE_BROADCAST", evidence_document=evidence_document, manifest_document=manifest_document)
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 5.0))
        while time.monotonic() < deadline:
            time.sleep(0.1)
        with self._lock:
            replies = [item for item in self._received
                       if item.get("type") == "EVIDENCE_ACK" and item.get("reply_to") == message["message_id"]]
        return {"message_id": message["message_id"], "peer_acknowledgements": replies}

    def finalize_propagation(self, owner_request_document=None):
        """Commit a request batch and keep it retryable until required peers ACK its exact manifest."""
        state = self.current_state()
        if not state or state.get("status") not in {"READY_TO_SUBMIT", "PENDING_ACKS"}:
            raise PubSubUnavailable("The propagation window is not ready to finalize.")
        retryable_batch = (
            state.get("status") == "PENDING_ACKS"
            and isinstance(state.get("final_manifest_document"), dict)
            and isinstance(state.get("finalized_batch_documents"), list)
        )
        if utc_now() >= parse_timestamp(state["lease_expires_at"]) and not retryable_batch:
            state["status"] = "CANCELLED"
            state["cancel_reason"] = "Propagation lease expired before finalization."
            self._save_state(state)
            with self._lock:
                self._pending_requests = []
                self._save_pending()
            raise PubSubUnavailable("The propagation lease expired before finalization.")
        if state.get("batch_flushed"):
            return {
                "imported_count": 0,
                "manifest_hash": state.get("final_manifest_hash"),
                "owner_request_sent": bool(state.get("owner_request_sent")),
                "missing_peer_ids": [],
                "peer_errors": {},
            }

        # Persist the exact batch and manifest before network I/O. If ACKs are missing
        # or the process restarts, a retry must resend the same immutable transition,
        # not create a second manifest or silently lose the queued requests.
        if isinstance(state.get("final_manifest_document"), dict):
            documents = list(state.get("finalized_batch_documents", []))
            manifest_document = state["final_manifest_document"]
            imported = {
                "imported_count": state.get("batch_request_count", len(documents)),
                "manifest_hash": state.get("final_manifest_hash"),
                "manifest_sequence": manifest_document.get("sequence"),
                "manifest_document": manifest_document,
            }
            expected_peer_ids = set(state.get("expected_peer_ids", []))
        else:
            with self._lock:
                pending = list(self._pending_requests)
                expected_peer_ids = {
                    item.get("sender_node_id")
                    for item in self._received
                    if item.get("type") == "PROPOSAL_STATUS"
                    and item.get("proposal_id") == state.get("proposal_id")
                    and isinstance(item.get("sender_node_id"), str)
                    and item.get("sender_node_id") != state.get("proposer_node_id")
                }
            documents = list(pending)
            if owner_request_document is not None:
                documents.append(owner_request_document)
            imported = {"imported_count": 0, "manifest_hash": None}
            if documents:
                if self.service is None:
                    raise PubSubUnavailable("Request service is not connected to the propagation protocol.")
                imported = self.service.import_remote_requests(documents)
                if not isinstance(imported.get("manifest_document"), dict):
                    current_manifest = self.service.current_manifest()
                    if not isinstance(current_manifest, dict) or current_manifest.get("manifest_hash") != imported.get("manifest_hash"):
                        raise PubSubUnavailable("Could not recover the exact manifest for a retryable batch.")
                    imported["manifest_document"] = current_manifest
                state["finalized_batch_documents"] = documents
                state["final_manifest_document"] = imported["manifest_document"]
                state["final_manifest_hash"] = imported.get("manifest_hash")
                state["batch_request_count"] = len(documents)
                state["owner_request_sent"] = owner_request_document is not None
                state["expected_peer_ids"] = sorted(expected_peer_ids)
                state["batch_flushed"] = False
                state["status"] = "PENDING_ACKS"
                self._save_state(state)
            else:
                # Nothing changed, so there is no remote manifest transition to ACK.
                with self._lock:
                    self._pending_requests = []
                    self._save_pending()
                state["batch_flushed"] = True
                state["owner_request_sent"] = False
                state["batch_request_count"] = 0
                state["final_manifest_hash"] = (self.service.current_manifest() or {}).get("manifest_hash") if self.service else None
                state["batch_acknowledgements"] = []
                state["missing_peer_ids"] = []
                state["batch_peer_errors"] = {}
                state["finalized_at"] = timestamp(utc_now())
                self._save_state(state)
                return {
                    "imported_count": 0,
                    "manifest_hash": state.get("final_manifest_hash"),
                    "batch_request_count": 0,
                    "owner_request_sent": False,
                    "peer_acknowledgements": [],
                    "missing_peer_ids": [],
                    "peer_errors": {},
                }

        peer_acknowledgements = {}
        peer_errors = {}
        batch_message_ids = set()
        for attempt in range(3):
            batch_message = self._publish(
                "REQUEST_BATCH",
                proposal_id=state.get("proposal_id"),
                proposal_hash=state.get("proposal_hash"),
                request_documents=documents,
                manifest_document=imported.get("manifest_document"),
                manifest_hash=imported.get("manifest_hash"),
            )
            batch_message_ids.add(batch_message["message_id"])
            if not expected_peer_ids:
                break
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                with self._lock:
                    replies = [
                        item for item in self._received
                        if item.get("type") == "BATCH_ACK"
                        and item.get("reply_to") in batch_message_ids
                    ]
                for reply in replies:
                    sender_id = reply.get("sender_node_id")
                    if sender_id not in expected_peer_ids:
                        continue
                    if reply.get("error"):
                        peer_errors[sender_id] = str(reply["error"])
                    elif reply.get("manifest_hash") == imported.get("manifest_hash"):
                        peer_acknowledgements[sender_id] = reply
                        peer_errors.pop(sender_id, None)
                if expected_peer_ids.issubset(peer_acknowledgements):
                    break
                time.sleep(0.1)
            if expected_peer_ids.issubset(peer_acknowledgements):
                break
            if attempt < 2:
                time.sleep(0.5)

        missing_peer_ids = sorted(expected_peer_ids - set(peer_acknowledgements))
        state["batch_flushed"] = not missing_peer_ids
        state["status"] = "FINALIZED" if not missing_peer_ids else "PENDING_ACKS"
        state["owner_request_sent"] = bool(state.get("owner_request_sent"))
        state["batch_request_count"] = len(documents)
        state["final_manifest_hash"] = imported.get("manifest_hash")
        state["batch_acknowledgements"] = sorted(peer_acknowledgements)
        state["missing_peer_ids"] = missing_peer_ids
        state["batch_peer_errors"] = peer_errors
        state["finalized_at"] = timestamp(utc_now())
        if not missing_peer_ids:
            with self._lock:
                self._pending_requests = []
                self._save_pending()
        self._save_state(state)
        return {
            **imported,
            "batch_request_count": len(documents),
            "owner_request_sent": state["owner_request_sent"],
            "peer_acknowledgements": list(peer_acknowledgements.values()),
            "missing_peer_ids": missing_peer_ids,
            "peer_errors": peer_errors,
            "batch_flushed": state["batch_flushed"],
            "status": state["status"],
        }

    def _flush_pending_requests(self, state):
        if state.get("batch_flushed"):
            return
        self.finalize_propagation()

    def current_state(self):
        state = self._state()
        if not state:
            return None
        now = utc_now()
        if state.get("status") in {"ACCEPTED", "READY_TO_SUBMIT"}:
            if now >= parse_timestamp(state["lease_expires_at"]):
                state["status"] = "CANCELLED"
                state["cancel_reason"] = "Propagation lease expired before the request batch was completed."
                self._save_state(state)
                with self._lock:
                    self._pending_requests = []
                    self._save_pending()
            elif state.get("status") == "ACCEPTED" and now >= parse_timestamp(state["send_enabled_at"]):
                state["status"] = "READY_TO_SUBMIT"
                self._save_state(state)
                if not state.get("require_owner_request"):
                    self._flush_pending_requests(state)
        return state

    def stop(self):
        if self._listener and self._listener.poll() is None:
            self._listener.terminate()
            try:
                self._listener.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._listener.kill()
                self._listener.wait(timeout=2)
        if self._listener and self._listener.stdout:
            self._listener.stdout.close()
        self._listener = None
