""""Experimental Kubo PubSub propagation window for P2P Contracts."""
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
    """Prototype PubSub protocol; messages are untrusted claims, not consensus."""
    def __init__(self, storage: Any, network: Any, kubo: Any):
        self.storage, self.network, self.kubo = storage, network, kubo
        self.directory = storage.path("p2p_contracts/propagation")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "state.json"
        self.messages_path = self.directory / "received-messages.json"
        self._lock = threading.Lock()
        self._received = []
        self._listener = None
        if self.messages_path.is_file():
            try:
                items = json.loads(self.messages_path.read_text(encoding="utf-8"))
                self._received = items[-1000:] if isinstance(items, list) else []
            except (OSError, json.JSONDecodeError):
                self._received = []

    def _state(self):
        if not self.state_path.is_file():
            return None
        try:
            result = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PubSubUnavailable(f"Cannot read propagation state: {exc}") from exc
        return result if isinstance(result, dict) else None

    def _save_state(self, state):
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.state_path)

    def _new_message(self, kind, **fields):
        return {"schema": MESSAGE_SCHEMA, "message_id": str(uuid4()), "created_at": timestamp(utc_now()),
                "sender_node_id": self.network.identity().peer_id, "type": kind, **fields}

    def _publish(self, kind, **fields):
        message = self._new_message(kind, **fields)
        encoded = json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            self.kubo._run("pubsub", "pub", TOPIC, encoded)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            raise PubSubUnavailable("Kubo PubSub is unavailable. Enable Pubsub.Enabled and restart Kubo.") from exc
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
        time.sleep(0.15)
        if self._listener.poll() is not None:
            raise PubSubUnavailable("Kubo PubSub listener exited. Check Pubsub.Enabled and Kubo logs.")

    def _read_loop(self):
        process = self._listener
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            try:
                envelope = json.loads(line)
                data = envelope.get("Data")
                if not isinstance(data, str):
                    continue
                if data.startswith("m"):
                    raw = base64.b64decode(data[1:] + "=" * (-len(data[1:]) % 4))
                elif data.startswith("u"):
                    raw = base64.urlsafe_b64decode(data[1:] + "=" * (-len(data[1:]) % 4))
                else:
                    raw = base64.b64decode(data + "=" * (-len(data) % 4))
                message = json.loads(raw.decode("utf-8"))
                if message.get("schema") != MESSAGE_SCHEMA or not message.get("message_id") or not message.get("sender_node_id"):
                    continue
                if message.get("sender_node_id") == self.network.identity().peer_id:
                    continue
                with self._lock:
                    if any(old.get("message_id") == message["message_id"] for old in self._received):
                        continue
                    self._received.append(message)
                    temp = self.messages_path.with_suffix(".tmp")
                    temp.write_text(json.dumps(self._received[-1000:], ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
                    os.replace(temp, self.messages_path)
                if message.get("type") == "STATUS_QUERY":
                    state = self.current_state()
                    self._publish("STATUS_RESPONSE", reply_to=message["message_id"],
                                  queried_by=message["sender_node_id"],
                                  active_proposal=state if state and state["status"] in {"ACCEPTED", "READY_TO_SUBMIT"} else None)
                elif message.get("type") == "PROPOSAL_ANNOUNCE":
                    state = self._state()
                    proposal = message.get("proposal") or {}
                    self._publish("PROPOSAL_STATUS", proposal_id=proposal.get("proposal_id"),
                                  observed_proposal_hash=state.get("proposal_hash") if state else None,
                                  observed_status=state.get("status") if state else "NONE")
            except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, OSError):
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
        active = [item["active_proposal"] for item in responses.values()
                  if isinstance(item.get("active_proposal"), dict)
                  and item["active_proposal"].get("status") in {"ACCEPTED", "READY_TO_SUBMIT"}]
        return {"responses": list(responses.values()), "active_proposals": active,
                "status": "UNVERIFIED" if active else ("NO_ACTIVE_PROPOSAL" if responses else "NO_NODE_RESPONSES")}

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
                 "window_seconds": WINDOW_SECONDS, "status": "ACCEPTED",
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

    def current_state(self):
        state = self._state()
        if not state:
            return None
        now = utc_now()
        if state.get("status") == "ACCEPTED":
            if now >= parse_timestamp(state["lease_expires_at"]):
                state["status"] = "CANCELLED"
                state["cancel_reason"] = "Propagation lease expired before submission was completed."
                self._save_state(state)
            elif now >= parse_timestamp(state["send_enabled_at"]):
                state["status"] = "READY_TO_SUBMIT"
                self._save_state(state)
        return state

    def stop(self):
        if self._listener and self._listener.poll() is None:
            self._listener.terminate()
            try:
                self._listener.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._listener.kill()
        self._listener = None
