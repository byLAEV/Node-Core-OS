"""End-to-end P2P Contracts test using three independent local Kubo daemons.

Run with IPFS_BIN=/path/to/ipfs python applications/p2p_contracts/tests/three_node_real_kubo.py.
The test creates three temporary Kubo repositories and never touches the user's installed repo.
"""
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

if hasattr(os, "getuid") and os.getuid() == 0:
    raise SystemExit("ERROR: the real Kubo integration test must run as an ordinary user, never UID 0.")
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from node_core.storage import StorageManager
from applications.p2p_contracts.p2p_contracts.propagation import (
    PropagationProtocol, timestamp, utc_now,
)
from applications.p2p_contracts.p2p_contracts.service import P2PContractsService
from applications.p2p_contracts.p2p_contracts.cli import P2PContractsCLI


def free_ports(count):
    sockets = [socket.socket() for _ in range(count)]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


class RealKuboAdapter:
    def __init__(self, executable, repo):
        self.executable = executable
        self.repo = Path(repo)
        self.env = {**os.environ, "IPFS_PATH": str(self.repo)}

    def _environment(self):
        return self.env

    def _run(self, *args):
        return subprocess.run(
            [self.executable, *args], env=self.env, check=True,
            capture_output=True, text=True, timeout=20,
        )

    def pubsub_publish(self, topic, encoded):
        """Publish one immutable payload, retrying transient Kubo PubSub failures."""
        command = [self.executable, "pubsub", "pub", topic, "-"]
        last_error = None
        for attempt in range(3):
            try:
                subprocess.run(
                    command,
                    env=self.env,
                    input=encoded,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=15,
                )
                return
            except subprocess.CalledProcessError as exc:
                last_error = exc
                detail = (exc.stderr or exc.stdout or str(exc)).strip()
                # Kubo can briefly reject a publish while its PubSub mesh is
                # converging. Retrying the identical message is safe because the
                # protocol assigns a stable message_id to this encoded payload.
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Kubo PubSub publish failed after {attempt + 1} attempts: {detail}"
                ) from exc
            except subprocess.TimeoutExpired as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Kubo PubSub publish timed out after {attempt + 1} attempts."
                ) from exc
        if last_error is not None:
            raise RuntimeError(f"Kubo PubSub publish failed: {last_error}") from last_error

    def status(self):
        self._run("swarm", "peers")
        return SimpleNamespace(running=True)


class RealKuboNetwork:
    def __init__(self, kubo):
        self.kubo = kubo

    def identity(self):
        payload = json.loads(self.kubo._run("id").stdout)
        return SimpleNamespace(peer_id=payload["ID"], addresses=tuple(payload.get("Addresses", [])))


class TestThreeNodeRealKubo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ipfs = os.environ.get("IPFS_BIN") or shutil.which("ipfs")
        if not cls.ipfs:
            raise RuntimeError("Kubo CLI not found. Set IPFS_BIN to the installed ipfs executable.")
        cls.temporary = tempfile.TemporaryDirectory(prefix="p2p-contracts-three-node-")
        cls.root = Path(cls.temporary.name)
        cls.nodes = []
        # Reserve one unique set of API, gateway and swarm ports for all three
        # daemons at once. Reserving only one node at a time can reuse a gateway
        # port that a previous daemon has not bound yet.
        reserved_ports = free_ports(9)
        port_sets = [reserved_ports[index:index + 3] for index in range(0, 9, 3)]
        for index in range(3):
            repo = cls.root / f"kubo-{index + 1}"
            repo.mkdir()
            env = {**os.environ, "IPFS_PATH": str(repo)}
            subprocess.run([cls.ipfs, "init", "--profile=test"], env=env, check=True,
                           capture_output=True, text=True, timeout=30)
            api_port, gateway_port, swarm_port = port_sets[index]
            commands = [
                ("config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{api_port}"),
                ("config", "Addresses.Gateway", f"/ip4/127.0.0.1/tcp/{gateway_port}"),
                ("config", "--json", "Addresses.Swarm", json.dumps([f"/ip4/127.0.0.1/tcp/{swarm_port}"])),
                ("config", "--json", "Bootstrap", "[]"),
                ("config", "--json", "Pubsub.Enabled", "true"),
                ("config", "--json", "Discovery.MDNS.Enabled", "false"),
            ]
            for command in commands:
                subprocess.run([cls.ipfs, *command], env=env, check=True,
                               capture_output=True, text=True, timeout=15)
            daemon_help = subprocess.run(
                [cls.ipfs, "daemon", "--help"], env=env, check=False,
                capture_output=True, text=True, timeout=10,
            )
            daemon_command = [cls.ipfs, "daemon"]
            if "--enable-pubsub-experiment" in (daemon_help.stdout or "") + (daemon_help.stderr or ""):
                daemon_command.append("--enable-pubsub-experiment")
            log_path = cls.root / f"kubo-{index + 1}.log"
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(daemon_command, env=env, stdout=log_handle,
                                       stderr=subprocess.STDOUT, text=True)
            cls.nodes.append({"repo": repo, "env": env, "process": process,
                              "log_handle": log_handle, "log_path": log_path,
                              "swarm_port": swarm_port, "api_port": api_port})
        for node in cls.nodes:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if node["process"].poll() is not None:
                    raise RuntimeError(f"Kubo daemon exited. Log: {node['log_path'].read_text(errors='replace')}")
                try:
                    subprocess.run([cls.ipfs, "swarm", "peers"], env=node["env"], check=True,
                                   capture_output=True, text=True, timeout=2)
                    break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    time.sleep(0.25)
            else:
                raise RuntimeError(f"Kubo daemon did not become ready: {node['log_path']}")
        identities = []
        for node in cls.nodes:
            payload = json.loads(subprocess.run([cls.ipfs, "id"], env=node["env"], check=True,
                                                capture_output=True, text=True, timeout=10).stdout)
            identities.append(payload["ID"])
        for source_index, target_index in ((0, 1), (0, 2), (1, 2)):
            target = cls.nodes[target_index]
            address = f"/ip4/127.0.0.1/tcp/{target['swarm_port']}/p2p/{identities[target_index]}"
            subprocess.run([cls.ipfs, "swarm", "connect", address], env=cls.nodes[source_index]["env"],
                           check=True, capture_output=True, text=True, timeout=20)
        for node in cls.nodes:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                result = subprocess.run([cls.ipfs, "swarm", "peers"], env=node["env"], check=True,
                                        capture_output=True, text=True, timeout=5)
                if len([line for line in result.stdout.splitlines() if "/p2p/" in line]) >= 2:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Three Kubo nodes did not establish full peer connectivity.")

    @classmethod
    def tearDownClass(cls):
        for node in reversed(getattr(cls, "nodes", [])):
            process = node["process"]
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            node["log_handle"].close()
        if hasattr(cls, "temporary"):
            cls.temporary.cleanup()

    def test_proposal_request_batch_publication_closure_and_search(self):
        class Profile:
            def load(self):
                return {"identity_id": "integration-test", "alias": "integration-node"}

        adapters = [RealKuboAdapter(self.ipfs, node["repo"]) for node in self.nodes]
        networks = [RealKuboNetwork(adapter) for adapter in adapters]
        storages = []
        services = []
        protocols = []
        for index, (adapter, network) in enumerate(zip(adapters, networks)):
            storage = StorageManager(self.root / f"app-storage-{index + 1}")
            storage.initialize()
            service = P2PContractsService(storage, Profile(), network)
            protocol = PropagationProtocol(storage, network, adapter, service=service)
            storages.append(storage)
            services.append(service)
            protocols.append(protocol)
        try:
            for protocol in protocols:
                protocol.start()
            time.sleep(1.0)
            # Node A acts through the real application menu: it accepts a
            # propagation window and fills the owner BTC request form as a draft.
            runtime_a = SimpleNamespace(
                storage=storages[0], identity_profile=Profile(),
                network=networks[0], kubo=adapters[0],
            )
            cli_a = P2PContractsCLI(runtime_a)
            cli_a.service = services[0]
            cli_a.propagation = protocols[0]
            # Keep the timer-driven worker deterministic; invoke its normal submission
            # function explicitly after advancing the isolated test clock.
            cli_a._start_owner_auto_submit = lambda: None
            owner_answers = iter([
                "y",  # Accept a local propagation window.
                "n",  # Do not publish personal identity fields.
                "email", "node-a@example.invalid", "n",
                "0.025", "EUR", "700", "SEPA",
                "Three-node integration request from A", "y",
            ])
            owner_form_output = io.StringIO()
            with patch("builtins.input", side_effect=owner_answers), redirect_stdout(owner_form_output):
                cli_a.accept_propagation()
            proposal = protocols[0].current_state()
            self.assertIsNotNone(proposal, "Node A's application menu did not create a propagation.")
            self.assertEqual(proposal["status"], "ACCEPTED")
            self.assertTrue((storages[0].path("p2p_contracts/propagation/owner-request-draft.json")).is_file())
            status = protocols[1].query_status(wait_seconds=2.0)
            self.assertTrue(status["responses"], f"Node B received no peer status responses; received types={[item.get('type') for item in protocols[1]._received]}; listener errors={protocols[1]._listener_errors}; peers={adapters[1]._run('swarm', 'peers').stdout}")
            self.assertTrue(any(item.get("proposal_hash") == proposal["proposal_hash"]
                                for item in status["active_proposals"]),
                            "Node B did not discover Node A's active proposal.")

            # Exercise the same status check shown in the application menu.
            runtime_b = SimpleNamespace(
                storage=storages[1], identity_profile=Profile(),
                network=networks[1], kubo=adapters[1],
            )
            cli_b = P2PContractsCLI(runtime_b)
            cli_b.service = services[1]
            cli_b.propagation = protocols[1]
            status_output = io.StringIO()
            with redirect_stdout(status_output):
                cli_b.check_propagation_status()
            self.assertIn(proposal["proposal_hash"], status_output.getvalue())
            self.assertIn("Remote claims are UNVERIFIED", status_output.getvalue())

            # Node B must explicitly accept the genesis reference locally before its first request.
            services[1].accept_initial_genesis_reference(
                accepted_by_node_id=networks[1].identity().peer_id
            )

            # Exercise the real interactive BTC exchange form, not only the service API.
            # The input stream is synthetic, while the request is sent through the real
            # PropagationProtocol and the three real Kubo daemons started by this test.
            created_request = {}
            original_create = services[1].create_btc_exchange_request

            def capture_request_result(*args, **kwargs):
                result = original_create(*args, **kwargs)
                created_request.update(result)
                return result

            services[1].create_btc_exchange_request = capture_request_result
            form_answers = iter([
                "n",  # Do not publish identity fields in this public synthetic request.
                "email", "node-b@example.invalid", "n",
                "0.015", "USDT", "1000", "TRON",
                "Three-node integration request from B", "y",
            ])
            try:
                with patch("builtins.input", side_effect=form_answers), redirect_stdout(io.StringIO()):
                    self.assertTrue(cli_b.create_request_form(remote_proposal=proposal))
            finally:
                services[1].create_btc_exchange_request = original_create

            request_b = created_request
            self.assertTrue(request_b.get("request_id"), "The BTC exchange form did not create a request.")
            request_b_doc = json.loads(Path(request_b["request_path"]).read_text(encoding="utf-8"))
            self.assertEqual(request_b_doc["exchange"]["give_amount"], "0.015")
            self.assertEqual(request_b_doc["exchange"]["receive_asset"], "USDT")
            self.assertEqual(request_b_doc["exchange"]["receive_amount"], "1000")
            self.assertEqual(request_b_doc["exchange"]["receive_network"], "TRON")
            self.assertIsNone(services[1].current_manifest(), "A peer request must remain uncommitted until the proposer publishes the batch.")
            self.assertTrue(
                any(item.get("request_id") == request_b["request_id"] for item in protocols[0]._pending_requests),
                "The form-submitted request was not queued by the proposing node after its network acknowledgement.",
            )

            # Fast-forward the ten-minute timer only inside this isolated test
            # and run the application's normal owner-draft submission function.
            from datetime import timedelta
            state = protocols[0]._state()
            state["send_enabled_at"] = timestamp(utc_now() - timedelta(seconds=1))
            state["lease_expires_at"] = timestamp(utc_now() + timedelta(seconds=30))
            protocols[0]._save_state(state)
            self.assertEqual(protocols[0].current_state()["status"], "READY_TO_SUBMIT")
            owner_submit_output = io.StringIO()
            with redirect_stdout(owner_submit_output):
                cli_a.submit_owner_draft_if_ready(protocols[0].current_state())
            self.assertIn("PROPAGATION BATCH SUBMITTED", owner_submit_output.getvalue())
            self.assertIn("Requests included in the manifest transition: 2", owner_submit_output.getvalue())
            owner_id_line = next(
                line for line in owner_submit_output.getvalue().splitlines()
                if line.startswith("Owner request ID: ")
            )
            request_a = {"request_id": owner_id_line.split(":", 1)[1].strip()}
            request_a_found = services[0].find_request(request_a["request_id"])
            self.assertIsNotNone(request_a_found, "Node A's owner request form was not committed.")
            request_a_doc = request_a_found["request"]
            finalized_state = protocols[0].current_state()
            self.assertEqual(
                finalized_state["status"], "FINALIZED",
                "Batch did not finalize: "
                f"missing_peer_ids={finalized_state.get('missing_peer_ids')}; "
                f"batch_peer_errors={finalized_state.get('batch_peer_errors')}; "
                f"acknowledgements={finalized_state.get('batch_acknowledgements')}; "
                f"node_listener_errors={[protocol._listener_errors for protocol in protocols]}; "
                f"received_types={[[item.get('type') for item in protocol._received[-30:]] for protocol in protocols]}",
            )
            self.assertTrue(finalized_state["owner_request_sent"])
            self.assertEqual(services[0].current_manifest()["sequence"], 1)
            self.assertEqual(len(services[0].current_manifest()["requests"]), 2)
            self.assertIsNotNone(services[0].find_request(request_b["request_id"]))

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if all(services[index].find_request(request_a["request_id"]) is not None for index in (1, 2)):
                    break
                time.sleep(0.2)
            self.assertTrue(all(services[index].find_request(request_a["request_id"]) is not None for index in (1, 2)),
                            "Node A's public request did not synchronize to B and C.")

            self.assertEqual(services[1].current_manifest()["sequence"], 1)
            self.assertEqual(len(services[1].current_manifest()["requests"]), 2)
            self.assertEqual(services[2].current_manifest()["sequence"], 1)
            self.assertEqual(len(services[2].current_manifest()["requests"]), 2)
            shared_hashes = {services[index].current_manifest()["manifest_hash"] for index in range(3)}
            self.assertEqual(len(shared_hashes), 1, "All three nodes must accept the exact same batch manifest hash.")

            # The first BTC-exchange request batch must be logical block 1,
            # anchored to the bundled genesis on every independent node.
            genesis_hash = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
            for index in range(3):
                manifest = services[index].current_manifest()
                self.assertEqual(manifest["sequence"], 1,
                                 f"Node {index + 1} must publish the first request batch as block 1.")
                self.assertEqual(manifest["genesis_hash"], genesis_hash,
                                 f"Node {index + 1} manifest must identify the expected genesis.")
                self.assertEqual(manifest["previous_manifest_hash"], genesis_hash,
                                 f"Node {index + 1} block 1 must reference the genesis as its parent.")
                self.assertTrue(services[index].genesis_path.is_file(),
                                f"Node {index + 1} must store the genesis in its synchronized manifests directory.")
                genesis_document = services[index]._read_json(services[index].genesis_path)
                self.assertEqual(genesis_document["genesis_hash"], genesis_hash,
                                 f"Node {index + 1} synchronized genesis document has the wrong hash.")

            # Verify the actual BTC exchange fields, not only request IDs, on every node.
            expected_exchanges = {
                request_a["request_id"]: {
                    "give_asset": "BTC",
                    "give_amount": "0.025",
                    "receive_asset": "EUR",
                    "receive_amount": "700",
                    "receive_network": "SEPA",
                },
                request_b["request_id"]: {
                    "give_asset": "BTC",
                    "give_amount": "0.015",
                    "receive_asset": "USDT",
                    "receive_amount": "1000",
                    "receive_network": "TRON",
                },
            }
            for index in range(3):
                for request_id, expected_exchange in expected_exchanges.items():
                    found = services[index].find_request(request_id)
                    self.assertIsNotNone(found, f"Node {index + 1} cannot retrieve BTC exchange request {request_id}.")
                    request_doc = found["request"]
                    self.assertEqual(request_doc["request_type"], "btc_exchange")
                    self.assertEqual(request_doc["exchange"], expected_exchange,
                                     f"Node {index + 1} changed or failed to synchronize exchange fields for {request_id}.")
                    self.assertEqual(found["manifest_hash"], next(iter(shared_hashes)))

            # Node C now uses the actual application closure form, just as an identity
            # would. The form writes and broadcasts the evidence through the real protocol.
            runtime_c = SimpleNamespace(
                storage=storages[2], identity_profile=Profile(),
                network=networks[2], kubo=adapters[2],
            )
            cli_c = P2PContractsCLI(runtime_c)
            cli_c.service = services[2]
            cli_c.propagation = protocols[2]
            closure_answers = iter([
                request_a["request_id"], networks[0].identity().peer_id, "5",
                "exchange_completed", "Synthetic integration closure evidence.",
                "Node C recorded the synthetic test result.", "y",
            ])
            closure_output = io.StringIO()
            with patch("builtins.input", side_effect=closure_answers), redirect_stdout(closure_output):
                cli_c.create_closure_form()
            self.assertIn("Verification status: self_reported_unverified", closure_output.getvalue())
            self.assertIn("Evidence ID:", closure_output.getvalue())
            evidence_files = list((self.root / "app-storage-3" / "p2p_contracts" / "evidence").glob("*.json"))
            self.assertEqual(len(evidence_files), 1)
            evidence_doc = json.loads(evidence_files[0].read_text(encoding="utf-8"))
            evidence = {"evidence_id": evidence_doc["evidence_id"]}

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                found_a = services[0].find_request(request_a["request_id"])
                found_b = services[1].find_request(request_a["request_id"])
                if found_a and found_b and found_a["evidence"] and found_b["evidence"]:
                    break
                time.sleep(0.2)
            for index in range(3):
                found = services[index].find_request(request_a["request_id"])
                self.assertIsNotNone(found, f"Node {index + 1} cannot search for request A.")
                self.assertEqual(found["request_status"], "exchange_completed")
                self.assertTrue(found["evidence"], f"Node {index + 1} did not synchronize closure evidence.")
                self.assertEqual(found["evidence"][0]["rating"], 5)

            # Node B uses the actual Search Request ID menu and must display the
            # synchronized BTC offer, final state, evidence, and shared manifest hash.
            search_output = io.StringIO()
            with patch("builtins.input", return_value=request_a["request_id"]), redirect_stdout(search_output):
                cli_b.search_request_form()
            self.assertIn(request_a["request_id"], search_output.getvalue())
            self.assertIn("BTC offered: 0.025 BTC", search_output.getvalue())
            self.assertIn("Asset requested: 700 EUR", search_output.getvalue())
            self.assertIn("Derived state: exchange_completed", search_output.getvalue())
            self.assertIn("Evidence records: 1", search_output.getvalue())

            evidence_hashes = {services[index].current_manifest()["manifest_hash"] for index in range(3)}
            self.assertEqual(len(evidence_hashes), 1, "All three nodes must converge to the same closure-evidence manifest hash.")
        finally:
            for protocol in protocols:
                protocol.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
