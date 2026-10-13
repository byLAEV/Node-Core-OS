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
            self.kubo._run("pubsub", "pub", TOPIC, encoded)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as exc:
            raise PubSubUnavailable("Kubo PubSub publish failed. Enable Pubsub.Enabled and check Kubo connectivity.") from exc
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
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
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
        # Kubo CLI JSON encodes the raw PubSub data as ordinary base64.
        candidates = [value]
        # Also accept multibase-prefixed payloads for compatible CLI variants.
        if value.startswith("m"):
            candidates.append(value[1:])
        if value.startswith("u"):
            candidates.append(value[1:])
        for candidate in candidates:
            try:
                return base64.b64decode(candidate + "=" * (-len(candidate) % 4), validate=True)
            except (ValueError, base64.binascii.Error):
                continue
        raise ValueError("PubSub message data is not valid base64.")

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
            if not any(item.get("request_id") == request_id for item in self._pending_requests):
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
                    result = self.service.import_remote_requests([document])
                    self._publish("REQUEST_ACK", reply_to=message["message_id"],
                                  request_id=document.get("request_id"), accepted=True,
                                  imported_count=result["imported_count"], reason="Public request imported.")
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("REQUEST_ACK", reply_to=message["message_id"],
                                  request_id=document.get("request_id"), accepted=False, reason=str(exc))
        elif kind == "EVIDENCE_BROADCAST":
            document = message.get("evidence_document")
            if self.service is not None and isinstance(document, dict):
                try:
                    result = self.service.import_remote_evidence(document)
                    self._publish("EVIDENCE_ACK", reply_to=message["message_id"],
                                  evidence_id=document.get("evidence_id"), accepted=True,
                                  imported=result.get("imported", False), reason="Evidence verified and imported.")
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("EVIDENCE_ACK", reply_to=message["message_id"],
                                  evidence_id=document.get("evidence_id"), accepted=False, reason=str(exc))
        elif kind == "REQUEST_BATCH":
            documents = message.get("request_documents")
            if self.service is not None and isinstance(documents, list) and documents:
                try:
                    result = self.service.import_remote_requests(documents)
                    self._publish("BATCH_ACK", reply_to=message["message_id"],
                                  imported_count=result["imported_count"],
                                  manifest_hash=result["manifest_hash"])
                except (ValueError, RuntimeError, OSError) as exc:
                    self._publish("BATCH_ACK", reply_to=message["message_id"], imported_count=0, error=str(exc))

    def _read_loop(self):
        process = self._listener
        if process is None or process.stdout is None:
            return
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
            except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, OSError, KeyError, RuntimeError):
                continue

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

    def accept_new_propagation(self, parent_manifest_hash):
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

    def publish_request(self, request_document, wait_seconds=1.5):
        self.start()
        message = self._publish("REQUEST_BROADCAST", request_document=request_document)
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 5.0))
        while time.monotonic() < deadline:
            with self._lock:
                replies = [item for item in self._received
                           if item.get("type") == "REQUEST_ACK" and item.get("reply_to") == message["message_id"]]
            if replies:
                return {"message_id": message["message_id"], "peer_acknowledgements": replies}
            time.sleep(0.1)
        return {"message_id": message["message_id"], "peer_acknowledgements": []}

    def publish_evidence(self, evidence_document, wait_seconds=1.5):
        self.start()
        message = self._publish("EVIDENCE_BROADCAST", evidence_document=evidence_document)
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 5.0))
        while time.monotonic() < deadline:
            with self._lock:
                replies = [item for item in self._received
                           if item.get("type") == "EVIDENCE_ACK" and item.get("reply_to") == message["message_id"]]
            if replies:
                return {"message_id": message["message_id"], "peer_acknowledgements": replies}
            time.sleep(0.1)
        return {"message_id": message["message_id"], "peer_acknowledgements": []}

    def _flush_pending_requests(self, state):
        if state.get("batch_flushed"):
            return
        with self._lock:
            pending = list(self._pending_requests)
        if pending and self.service is not None:
            self.service.import_remote_requests(pending)
            self._publish("REQUEST_BATCH", proposal_id=state.get("proposal_id"),
                          proposal_hash=state.get("proposal_hash"), request_documents=pending)
            with self._lock:
                self._pending_requests = []
                self._save_pending()
        state["batch_flushed"] = True
        self._save_state(state)

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
            elif state.get("status") == "ACCEPTED" and now >= parse_timestamp(state["send_enabled_at"]):
                state["status"] = "READY_TO_SUBMIT"
                self._save_state(state)
                self._flush_pending_requests(state)
        return state

    def stop(self):
        if self._listener and self._listener.poll() is None:
            self._listener.terminate()
            try:
                self._listener.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._listener.kill()
        self._listener = None
