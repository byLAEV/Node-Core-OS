"""End-to-end P2P Contracts test using three independent local Kubo daemons.

Run with IPFS_BIN=/path/to/ipfs python applications/p2p_contracts/tests/three_node_real_kubo.py.
The test creates three temporary Kubo repositories and never touches the user's installed repo.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from node_core.storage import StorageManager
from applications.p2p_contracts.p2p_contracts.propagation import (
    PropagationProtocol, timestamp, utc_now,
)
from applications.p2p_contracts.p2p_contracts.service import P2PContractsService


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
        for index in range(3):
            repo = cls.root / f"kubo-{index + 1}"
            repo.mkdir()
            env = {**os.environ, "IPFS_PATH": str(repo)}
            subprocess.run([cls.ipfs, "init", "--profile=test"], env=env, check=True,
                           capture_output=True, text=True, timeout=30)
            api_port, gateway_port, swarm_port = free_ports(3)
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
            log_path = cls.root / f"kubo-{index + 1}.log"
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen([cls.ipfs, "daemon"], env=env, stdout=log_handle,
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
            proposal = protocols[0].accept_new_propagation(None, require_owner_request=True)
            status = protocols[1].query_status(wait_seconds=2.0)
            self.assertTrue(status["responses"], "Node B did not receive any peer status responses.")
            self.assertTrue(any(item.get("proposal_hash") == proposal["proposal_hash"]
                                for item in status["active_proposals"]),
                            "Node B did not discover Node A's active proposal.")

            request_b = services[1].create_btc_exchange_request(
                btc_amount="0.015", receive_asset="USDT", receive_amount="1000",
                receive_network="TRON", description="Three-node integration request from B",
                contacts=[{"type": "email", "value": "node-b@example.invalid"}],
                publish_identity=False,
            )
            request_b_doc = json.loads(Path(request_b["request_path"]).read_text(encoding="utf-8"))
            acknowledgement = protocols[1].submit_request(proposal, request_b_doc, wait_seconds=5.0)
            self.assertTrue(acknowledgement.get("accepted"), acknowledgement.get("reason"))

            request_a = services[0].create_btc_exchange_request(
                btc_amount="0.025", receive_asset="EUR", receive_amount="700",
                receive_network="SEPA", description="Three-node integration request from A",
                contacts=[{"type": "email", "value": "node-a@example.invalid"}],
                publish_identity=False, defer_manifest=True,
            )
            request_a_doc = json.loads(Path(request_a["request_path"]).read_text(encoding="utf-8"))
            state = protocols[0]._state()
            from datetime import timedelta
            state["send_enabled_at"] = timestamp(utc_now() - timedelta(seconds=1))
            state["lease_expires_at"] = timestamp(utc_now() + timedelta(seconds=30))
            protocols[0]._save_state(state)
            self.assertEqual(protocols[0].current_state()["status"], "READY_TO_SUBMIT")
            finalized = protocols[0].finalize_propagation(request_a_doc)
            self.assertEqual(finalized["batch_request_count"], 2)
            self.assertTrue(finalized["owner_request_sent"])
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

            evidence = services[2].create_request_evidence(
                request_id=request_a["request_id"], outcome="exchange_completed",
                evidence_type="exchange_result", description="Integration closure evidence.",
                reporter_statement="Node C recorded the test result.", target_node_id=networks[0].identity().peer_id,
                rating=5,
            )
            evidence_path = self.root / "app-storage-3" / "p2p_contracts" / "evidence" / f"{evidence['evidence_id']}.json"
            evidence_doc = json.loads(evidence_path.read_text(encoding="utf-8"))
            protocols[2].publish_evidence(evidence_doc)

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
        finally:
            for protocol in protocols:
                protocol.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
