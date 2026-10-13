"""Experimental Kubo PubSub transport and ten-minute propagation leases.

Received PubSub messages are claims, not global consensus certificates.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import base64, json, os, subprocess, threading, time
from typing import Any, Callable
from uuid import uuid4

TOPIC = "node-core-os/p2p-contracts/propagation/v1"
WINDOW_SECONDS = 600
MESSAGE_SCHEMA = "node-core-os/p2p-contracts/pubsub-message/1"

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

class KuboPubSub:
    def __init__(self, kubo: Any):
        self.kubo = kubo
    def publish(self, payload):
        self._validate_message(payload)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            self.kubo._run("pubsub", "pub", TOPIC, encoded)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            raise PubSubUnavailable("Kubo PubSub is unavailable. Enable Pubsub.Enabled and restart Kubo.") from exc
    def start_listener(self, on_message):
        listener = PubSubListener(self.kubo, on_message)
        listener.start()
        return listener
    @staticmethod
    def _validate_message(payload):
        if payload.get("schema") != MESSAGE_SCHEMA:
            raise ValueError("Unsupported P2P Contracts PubSub message schema.")
        if not isinstance(payload.get("message_id"), str) or not payload["message_id"]:
            raise ValueError("PubSub message_id is required.")
        if not isinstance(payload.get("sender_node_id"), str) or not payload["sender_node_id"]:
            raise ValueError("PubSub sender_node_id is required.")
        if not isinstance(payload.get("type"), str):
            raise ValueError("PubSub message type is required.")

class PubSubListener:
    def __init__(self, kubo: Any, on_message: Callable[[dict[str, Any]], None]):
        self.kubo, self.on_message = kubo, on_message
        self.process = None
        self.thread = None
        self.stop_event = threading.Event()
        self.error = None
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        if not self.kubo.status().running:
            raise PubSubUnavailable("Kubo daemon is not running.")
        try:
            self.process = subprocess.Popen(
                [self.kubo.executable, "--enc=json", "pubsub", "sub", TOPIC],
                env=self.kubo._environment(), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
            )
        except OSError as exc:
            raise PubSubUnavailable(f"Could not start Kubo PubSub listener: {exc}") from exc
        self.thread = threading.Thread(target=self._read_loop, name="p2p-contracts-pubsub", daemon=True)
        self.thread.start()
        time.sleep(0.15)
        if self.process.poll() is not None:
            detail = self.process.stderr.read(2000).strip() if self.process.stderr else ""
            raise PubSubUnavailable("Kubo PubSub listener stopped. Check Pubsub.Enabled. " + detail)
    def _read_loop(self):
        assert self.process is not None and self.process.stdout is not None
        try:
            for line in self.process.stdout:
                if self.stop_event.is_set():
                    break
                try:
                    envelope = json.loads(line)
                    data = envelope.get("Data")
                    if not isinstance(data, str):
                        continue
                    payload = json.loads(self._decode_data(data).decode("utf-8"))
                    KuboPubSub._validate_message(payload)
                    if payload.get("sender_node_id") == self._local_peer_id():
                        continue
                    self.on_message(payload)
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    continue
        except (OSError, RuntimeError) as exc:
            self.error = str(exc)
    def _local_peer_id(self):
        try:
            return self.kubo._rpc_json("/api/v0/id", timeout=1.5).get("ID")
        except Exception:
            return None
    @staticmethod
    def _decode_data(value):
        if value.startswith("m"):
            return base64.b64decode(value[1:] + "=" * (-len(value[1:]) % 4))
        if value.startswith("u"):
            return base64.urlsafe_b64decode(value[1:] + "=" * (-len(value[1:]) % 4))
        return base64.b64decode(value + "=" * (-len(value) % 4))
    def close(self):
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

class PropagationProtocol:
    """Local proposal state and experimental PubSub exchange."""
    def __init__(self, storage: Any, network: Any, kubo: Any):
        self.storage, self.network = storage, network
        self.transport = KuboPubSub(kubo)
        self.state_path = storage.path("p2p_contracts/propagation/state.json")
        self.messages_path = storage.path("p2p_contracts/propagation/received-messages.json")
        self._lock = threading.Lock()
        self._listener = None
        self._received = []
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if self.messages_path.is_file():
            try:
                loaded = json.loads(self.messages_path.read_text(encoding="utf-8"))
                self._received = loaded[-1000:] if isinstance(loaded, list) else []
            except (OSError, json.JSONDecodeError):
                self._received = []
    def _save_received(self):
        tmp = self.messages_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._received[-1000:], ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        os.replace(tmp, self.messages_path)
    def _load_state(self):
        if not self.state_path.is_file():
            return None
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PubSubUnavailable(f"Propagation state cannot be read: {exc}") from exc
        return state if isinstance(state, dict) else None
    def _save_state(self, state):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        os.replace(tmp, self.state_path)
    def start(self):
        if self._listener and self._listener.thread and self._listener.thread.is_alive():
            return
        self._listener = self.transport.start_listener(self._on_message)
    def stop(self):
        if self._listener:
            self._listener.close()
            self._listener = None
    def _new_message(self, message_type, **fields):
        return {"schema": MESSAGE_SCHEMA, "message_id": str(uuid4()), "created_at": timestamp(utc_now()),
                "sender_node_id": self.network.identity().peer_id, "type": message_type, **fields}
    def _publish(self, message_type, **fields):
        message = self._new_message(message_type, **fields)
        self.transport.publish(message)
        return message
    def _on_message(self, message):
        with self._lock:
            if any(item.get("message_id") == message.get("message_id") for item in self._received):
                return
            self._received.append(message)
            self._save_received()
        if message.get("type") == "STATUS_QUERY":
            self._answer_status_query(message)
        elif message.get("type") == "PROPOSAL_ANNOUNCE":
            self._answer_proposal(message)
    def _answer_status_query(self, message):
        state = self.current_state()
        self._publish("STATUS_RESPONSE", reply_to=message.get("message_id"),
                      queried_by=message.get("sender_node_id"),
                      active_proposal=state if state and state.get("status") in {"ACCEPTED", "READY_TO_SUBMIT"} else None)
    def _answer_proposal(self, message):
        proposal = message.get("proposal")
        if not isinstance(proposal, dict):
            return
        state = self._load_state()
        self._publish("PROPOSAL_STATUS", proposal_id=proposal.get("proposal_id"),
                      observed_proposal_hash=state.get("proposal_hash") if state else None,
                      observed_status=state.get("status") if state else "NONE",
                      observed_sender=message.get("sender_node_id"))
    def query_status(self, wait_seconds=3.0):
        self.start()
        query = self._publish("STATUS_QUERY", known_proposal_hash=(self._load_state() or {}).get("proposal_hash"))
        deadline = time.monotonic() + max(0.5, min(wait_seconds, 10.0))
        responses = {}
        while time.monotonic() < deadline:
            with self._lock:
                messages = list(self._received)
            for item in messages:
                if item.get("type") == "STATUS_RESPONSE" and item.get("reply_to") == query["message_id"]:
                    responses[item.get("sender_node_id", "")] = item
            time.sleep(0.1)
        active = [m["active_proposal"] for m in responses.values()
                  if isinstance(m.get("active_proposal"), dict)
                  and m["active_proposal"].get("status") in {"ACCEPTED", "READY_TO_SUBMIT"}]
        return {"responses": list(responses.values()), "active_proposals": active,
                "status": "UNVERIFIED" if active else ("NO_ACTIVE_PROPOSAL" if responses else "NO_NODE_RESPONSES")}
    def accept_new_propagation(self, manifest_hash):
        self.start()
        node_id = self.network.identity().peer_id
        now = utc_now()
        proposal_id = str(uuid4())
        parent_hash = manifest_hash or "GENESIS"
        candidate = json.dumps({"parent_hash": parent_hash, "proposer_node_id": node_id, "proposal_id": proposal_id},
                               sort_keys=True, separators=(",", ":")).encode("utf-8")
        import hashlib
        state = {"proposal_id": proposal_id, "proposal_hash": hashlib.sha256(candidate).hexdigest(),
                 "parent_manifest_hash": manifest_hash, "proposer_node_id": node_id,
                 "accepted_at": timestamp(now), "send_enabled_at": timestamp(now + timedelta(seconds=WINDOW_SECONDS)),
                 "lease_expires_at": timestamp(now + timedelta(seconds=WINDOW_SECONDS + 60)),
                 "status": "ACCEPTED", "window_seconds": WINDOW_SECONDS, "request_ids_received": [],
                 "warning": "Local proposal state; not a global consensus certificate."}
        self._save_state(state)
        try:
            self._publish("PROPOSAL_ANNOUNCE", proposal=state)
            self._publish("NODE_HEARTBEAT", proposal_id=proposal_id, proposal_hash=state["proposal_hash"], status="ACCEPTED")
        except Exception:
            state["status"] = "CANCELLED"
            state["cancel_reason"] = "Could not announce proposal to Kubo PubSub."
            self._save_state(state)
            raise
        return state
    def current_state(self):
        state = self._load_state()
        if not state:
            return None
        now = utc_now()
        if state.get("status") == "ACCEPTED":
            if now >= parse_timestamp(state["send_enabled_at"]):
                state["status"] = "READY_TO_SUBMIT"
                self._save_state(state)
            elif now >= parse_timestamp(state["lease_expires_at"]):
                state["status"] = "CANCELLED"
                state["cancel_reason"] = "Lease expired."
                self._save_state(state)
        return state
