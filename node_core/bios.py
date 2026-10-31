"""Functional Node Core BIOS menus with safe defaults and explicit operations.

The BIOS is an operator interface: it never elevates privileges, never silently
changes trust, and clearly separates observed status from configured intent.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class BIOSMenu:
    """Run all BIOS sections against the existing NodeRuntime services."""

    def __init__(self, runtime: Any, ui: Any | None = None) -> None:
        self.runtime = runtime
        self.ui = ui

    @staticmethod
    def _pause() -> None:
        input("\\nPress Enter to return...")

    @staticmethod
    def _confirm(prompt: str) -> bool:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
        return answer in {"y", "yes"}

    @staticmethod
    def _show(title: str, values: dict[str, Any]) -> None:
        print(f"\\n{title}")
        for key, value in values.items():
            print(f"{key}: {value}")

    def run(self) -> None:
        # Never create or mutate Node Core state from an elevated account.
        geteuid = getattr(os, "geteuid", None)
        if geteuid is not None and geteuid() == 0:
            raise RuntimeError(
                "Node Core BIOS is user-only. Exit this root shell and run it "
                "from your normal Termux/Linux user without sudo or su."
            )
        actions = {
            "1": self.storage,
            "2": self.kubo,
            "3": self.network,
            "4": self.services,
            "5": self.configuration,
            "6": self.security,
            "7": self.diagnostics,
            "8": self.updates,
            "9": self.lifecycle,
            "10": self.identity,
            "11": self.domain_verification,
            "12": self.github_identity_pool,
        }
        descriptions = {
            "1": "Local private/shared storage; directories are created automatically.",
            "2": "Kubo daemon, repository, Peer ID, API and gateway.",
            "3": "LAN discovery, authenticated peers and network reachability.",
            "4": "Native P2P listener and background peer monitor.",
            "5": "Persistent paths and local API settings with safe defaults.",
            "6": "Node key, trusted peers, certificate fingerprints and revocation.",
            "7": "Read-only system, storage, Kubo and runtime checks.",
            "8": "Check available versions and run the protected updater.",
            "9": "Start, stop and restart Node Core-managed runtime services.",
            "10": "User-declared identity profile; private data remains local.",
            "11": "Independent verification of local P2P, mesh and IPFS domains.",
            "12": "Administer GitHub-only identity pool, export a lightweight Pages client, and synchronize encrypted records.",
        }
        while True:
            print("\\nNode Core BIOS\\nbyLAEV\\n")
            print("0. Back")
            for number in range(1, 13):
                key = str(number)
                print(f"{key}. {key_name(key)} — {descriptions[key]}")
            choice = input("\\n> ").strip()
            if choice == "0":
                return
            action = actions.get(choice)
            if action is None:
                print("Unknown BIOS option.")
                continue
            try:
                action()
            except (OSError, RuntimeError, ValueError, ImportError) as exc:
                print(f"BIOS operation unavailable: {exc}")
                self._pause()

    def storage(self) -> None:
        self.runtime.storage.initialize()
        if self.ui is not None:
            self.ui.storage_bios()
            return
        print("Private:", self.runtime.storage.private_path)
        print("Shared:", self.runtime.storage.shared_path)
        self._pause()

    def kubo(self) -> None:
        manager = self.runtime.kubo
        while True:
            status = manager.status()
            self._show("IPFS / Kubo", {
                "Installed": status.installed, "Initialized": status.initialized,
                "Running": status.running, "Peer ID": status.peer_id or "not available",
                "Version": status.version or "not available",
                "Repository": self.runtime.config.ipfs_repo_path,
                "RPC API": self.runtime.config.ipfs_api,
                "Gateway": self.runtime.config.ipfs_gateway,
                "Daemon log": manager.log_path,
            })
            print("\\n0. Back\\n1. Refresh status\\n2. Initialize repository\\n3. Start daemon\\n4. Stop daemon\\n5. Show complete configuration")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "1":
                continue
            if choice == "2":
                manager.initialize()
                print("Kubo repository initialized; existing repository was preserved.")
            elif choice == "3":
                manager.start()
                print("Kubo daemon is running.")
            elif choice == "4":
                if self._confirm("Stop the Kubo daemon? This interrupts IPFS requests"):
                    manager.stop()
                    print("Kubo daemon stopped.")
            elif choice == "5":
                self._show("Kubo configuration", {
                    "Executable": self.runtime.config.ipfs_executable,
                    "Repository": self.runtime.config.ipfs_repo_path,
                    "Profile": self.runtime.config.ipfs_profile,
                    "RPC API": self.runtime.config.ipfs_api,
                    "Gateway": self.runtime.config.ipfs_gateway,
                    "Auto-start": self.runtime.config.auto_start_kubo,
                })
                self._pause()

    def network(self) -> None:
        while True:
            print("\\nNetwork")
            print("1. Refresh network status (read-only probes)")
            print("2. Show local native P2P status")
            print("3. Show Kubo peers and bootstrap entries")
            print("4. Show network domain explanation")
            print("0. Back")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "1":
                result = self.runtime.refresh_network_status()
                native = result.get("native_p2p") or {}
                kubo = result.get("kubo")
                print("LAN discovery:", "RUNNING" if native.get("discovery_running") else "NOT VERIFIED")
                print("Native listener:", "RUNNING" if native.get("service_running") else "NOT RUNNING")
                print("Authenticated peers:", len(native.get("active_peers", [])) + len(native.get("recently_authenticated_peers", [])))
                print("Kubo daemon:", "RUNNING" if kubo and kubo.running else "NOT RUNNING")
                for warning in result.get("errors", []):
                    print("WARNING:", warning)
                self._pause()
            elif choice == "2":
                self._show("Native P2P", self.runtime.native_p2p_status())
                self._pause()
            elif choice == "3":
                status = self.runtime.kubo.status()
                if not status.running:
                    print("Kubo is not running; start it from option 2 first.")
                else:
                    print("Connected peers:")
                    result = self.runtime.network.connected_peers()
                    for peer in result:
                        print(peer)
                    print("Bootstrap:")
                    result = self.runtime.kubo._run("bootstrap", "list")
                    print(result.stdout.strip() or "(none)")
                self._pause()
            elif choice == "4":
                if self.ui is not None:
                    self.ui.network_domain_verification_menu()
                else:
                    print("P2P reachability, mesh convergence and IPFS retrieval are independent proofs.")
                    self._pause()

    def services(self) -> None:
        while True:
            try:
                status = self.runtime.native_p2p_status()
            except Exception as exc:
                status = {"error": str(exc)}
            self._show("Services", {
                "LAN discovery": "RUNNING" if status.get("discovery_running") else "NOT RUNNING",
                "Authenticated listener": "RUNNING" if status.get("service_running") else "NOT RUNNING",
                "Peer monitor": "RUNNING" if status.get("peer_monitor_running") else "NOT RUNNING",
                "Trusted peers": status.get("trusted_count", "unavailable"),
                "Listener address": status.get("listen_address", "unavailable"),
                "Note": "Listener requires at least one explicitly trusted peer certificate.",
            })
            print("\\n0. Back\\n1. Start LAN discovery\\n2. Start authenticated listener\\n3. Stop authenticated listener\\n4. Stop LAN discovery")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "1":
                if not self.runtime.start_native_discovery():
                    raise RuntimeError("LAN discovery could not start; inspect diagnostics.")
                print("LAN discovery started.")
            elif choice == "2":
                address = self.runtime.start_native_p2p(host="0.0.0.0", port=0)
                print("Authenticated listener started:", address)
            elif choice == "3":
                if self._confirm("Stop the native P2P listener?"):
                    self.runtime.stop_native_p2p()
                    self.runtime.stop_native_peer_monitor()
                    print("Native P2P listener stopped.")
            elif choice == "4":
                if self._confirm("Stop LAN discovery?"):
                    self.runtime.stop_native_discovery()
                    print("LAN discovery stopped.")

    def configuration(self) -> None:
        config = self.runtime.config
        while True:
            print("\\nConfiguration — defaults are active unless a saved config overrides them.")
            fields = {
                "1": ("auto_start_kubo", "Auto-start Kubo", "true/false"),
                "2": ("ipfs_api", "Kubo RPC API", "http://127.0.0.1:5001"),
                "3": ("ipfs_gateway", "Kubo HTTP Gateway", "http://127.0.0.1:8080"),
                "4": ("ipfs_executable", "Kubo executable", "ipfs (PATH)"),
                "5": ("ipfs_profile", "Kubo init profile", "unixfs-v1-2025"),
                "6": ("local_storage_path", "Local storage path", str(config.data_dir / "storage")),
                "7": ("ipfs_repo_path", "Kubo repository path", str(config.data_dir / "ipfs")),
            }
            for key, (attr, label, _) in fields.items():
                print(f"{key}. {label}: {getattr(config, attr)}")
            print("8. Save current settings\\n0. Back")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "8":
                config.save()
                self.runtime.storage.root = config.local_storage_path
                self.runtime.storage.initialize()
                print("Configuration saved. Kubo API/path changes apply after restarting Node Core.")
                self._pause()
                continue
            field = fields.get(choice)
            if field is None:
                print("Unknown configuration field.")
                continue
            attr, label, example = field
            print(f"Purpose: {label}. Enter a value or press Enter to keep the current value.")
            print(f"Expected format / default: {example}")
            current = getattr(config, attr)
            value = input(f"New value [{current}]: ").strip()
            if not value:
                continue
            if attr == "auto_start_kubo":
                if value.lower() not in {"true", "false", "yes", "no", "1", "0"}:
                    print("Enter true or false.")
                    continue
                setattr(config, attr, value.lower() in {"true", "yes", "1"})
            elif attr in {"local_storage_path", "ipfs_repo_path"}:
                path = Path(value).expanduser()
                if not path.is_absolute():
                    print("Enter an absolute path; relative paths are not accepted.")
                    continue
                setattr(config, attr, path)
            elif attr in {"ipfs_api", "ipfs_gateway"}:
                from urllib.parse import urlparse
                parsed = urlparse(value)
                if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or not parsed.port:
                    print("Only an explicit local HTTP endpoint with a port is accepted.")
                    continue
                setattr(config, attr, value.rstrip("/"))
            else:
                if any(ch.isspace() for ch in value):
                    print("Executable/profile values cannot contain whitespace.")
                    continue
                setattr(config, attr, value)

    def security(self) -> None:
        while True:
            print("\\nSecurity")
            print("1. Show technical node identity and key file permissions")
            print("2. List trusted/revoked peers")
            print("3. Trust peer certificate (verify fingerprint out of band first)")
            print("4. Revoke a trusted peer")
            print("0. Back")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "1":
                identity = self.runtime.p2p_identity.initialize()
                key_path = self.runtime.p2p_identity.private_key_path
                mode = oct(key_path.stat().st_mode & 0o777) if key_path.exists() else "missing"
                self._show("Technical node identity", {
                    "Algorithm": "Ed25519", "Node ID": identity["node_id"],
                    "Public key": identity["public_key"], "Private key path": key_path,
                    "Private key mode": mode,
                    "Warning": "Private key is local and unencrypted; filesystem permissions are not protection from same-user malware.",
                })
                self._pause()
            elif choice == "2":
                for peer in self.runtime.p2p_trust.list_peers():
                    print(peer)
                self._pause()
            elif choice == "3":
                node_id = input("Peer Node ID (sha256:<64 lowercase hex>): ").strip()
                cert_path = input("PEM certificate file path (example: ~/peer-node.pem): ").strip()
                label = input("Human-readable label (optional): ").strip()
                if not node_id or not cert_path:
                    print("Node ID and certificate path are required.")
                    continue
                if self._confirm("Trust only after independently comparing the certificate SHA-256 fingerprint"):
                    record = self.runtime.trust_peer_certificate(node_id, Path(cert_path).expanduser(), label)
                    print("Trusted peer:", record)
            elif choice == "4":
                node_id = input("Node ID to revoke: ").strip()
                if node_id and self._confirm("Revoke this peer and close its sessions"):
                    print(self.runtime.revoke_trusted_peer(node_id))

    def diagnostics(self) -> None:
        from node_core.network_diagnostics import collect_network_diagnostics
        result = collect_network_diagnostics()
        self._show("System network diagnostics", result)
        storage = self.runtime.storage
        storage.initialize()
        print("\\nStorage:")
        for path in (storage.root, storage.private_path, storage.shared_path):
            print(path, "exists" if path.is_dir() else "MISSING")
        status = self.runtime.kubo.status()
        print("\\nKubo:", status)
        print("Node Core version:", (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip())
        self._pause()

    def updates(self) -> None:
        from node_core.updates import check_for_updates
        status = check_for_updates()
        self._show("Updates", {
            "Installed version": status.local_version,
            "Available version": status.remote_version,
            "Update available": status.available,
            "Check completed": status.checked,
            "Detail": status.message,
        })
        if not status.checked:
            self._pause()
            return
        if not status.available:
            print("This installation is already current.")
            self._pause()
            return
        updater = self.runtime.config.data_dir / "bin" / "node-core-update"
        if not updater.is_file():
            print("Updater launcher is missing:", updater)
            self._pause()
            return
        if self._confirm("Run the protected updater? Existing storage, Kubo repo and config are preserved"):
            result = subprocess.run([str(updater)], check=False)
            print("Updater exit code:", result.returncode)
        self._pause()

    def lifecycle(self) -> None:
        while True:
            kubo = self.runtime.kubo.status()
            print("\\nLifecycle")
            print("Kubo:", "RUNNING" if kubo.running else "STOPPED")
            print("1. Start Kubo")
            print("2. Stop Kubo")
            print("3. Restart Kubo")
            print("4. Start native LAN discovery")
            print("5. Stop all Node Core runtime services")
            print("0. Back")
            choice = input("> ").strip()
            if choice == "0":
                return
            if choice == "1":
                self.runtime.kubo.start()
                print("Kubo started.")
            elif choice == "2":
                if self._confirm("Stop Kubo?"):
                    self.runtime.kubo.stop()
                    print("Kubo stopped.")
            elif choice == "3":
                if self._confirm("Restart Kubo? Active IPFS requests will be interrupted"):
                    self.runtime.kubo.stop()
                    self.runtime.kubo.start()
                    print("Kubo restarted.")
            elif choice == "4":
                print("LAN discovery:", self.runtime.start_native_discovery())
            elif choice == "5":
                if self._confirm("Stop native P2P listener, peer monitor, LAN discovery and Kubo?"):
                    self.runtime.shutdown()
                    if self.runtime.kubo.status().running:
                        self.runtime.kubo.stop()
                    print("Node Core managed runtime services stopped.")

    def identity(self) -> None:
        if self.ui is not None:
            self.ui.identity_bios()
            return
        print("Identity profile is available through the main UI.")
        self._pause()

    def github_identity_pool(self) -> None:
        """Administer the GitHub-only identity pool and encrypted Pages client."""
        from node_core.identity.github_pool import GitHubIdentityPool, GitHubIdentityPoolError

        pool = GitHubIdentityPool(self.runtime.config.data_dir)
        while True:
            print("\nGitHub Identity Pool")
            print("This pool admits GitHub accounts and their own Node Core client repositories only.")
            print("Personal records are encrypted in the Pages browser before GitHub receives them.")
            print("0. Back")
            print("1. Initialize / inspect administrator pool")
            print("2. Configure this node's GitHub client repository")
            print("3. Add a GitHub node to the administrator pool (pending)")
            print("4. List pool members")
            print("5. Revoke a pool member")
            print("6. Export lightweight GitHub Pages client")
            print("7. Synchronize encrypted records from this node's GitHub repository")
            print("8. Show public encryption key")
            choice = input("> ").strip()
            if choice == "0":
                return
            try:
                if choice == "1":
                    identity = self.runtime.p2p_identity.initialize()
                    result = pool.initialize(identity["node_id"])
                    self._show("GitHub Identity Pool", result)
                elif choice == "2":
                    login = input("Your GitHub username (example: octocat): ").strip()
                    repository = input("Repository you own (owner/node-core-client): ").strip()
                    branch = input("Default branch [main]: ").strip() or "main"
                    result = pool.configure_local_client(login, repository, default_branch=branch)
                    self._show("Local GitHub client", result)
                    print("Next: create the empty repository under this GitHub account and export the Pages client.")
                elif choice == "3":
                    login = input("GitHub username to admit: ").strip()
                    repository = input("Their Node Core client repository (owner/repository): ").strip()
                    page = input("GitHub Pages URL (Enter for the standard URL): ").strip() or None
                    record = pool.add_node(login, repository, page)
                    self._show("Pool admission", record)
                    print("Status is pending_admin_verification. Adding an account is not proof of ownership or personhood.")
                elif choice == "4":
                    for member in pool.list_nodes():
                        print(json.dumps(member, ensure_ascii=False, indent=2))
                    self._pause()
                elif choice == "5":
                    member_id = input("Pool member ID to revoke: ").strip()
                    if member_id and self._confirm("Revoke this GitHub account's pool membership?"):
                        self._show("Revoked pool member", pool.revoke_node(member_id))
                elif choice == "6":
                    print("0. Export client for this node's own GitHub repository")
                    print("1. Export client for an admitted pool member (encrypted to this administrator node)")
                    export_choice = input("> ").strip()
                    target = input("Export path (example: ~/node-core-client): ").strip()
                    if not target:
                        print("An export path is required.")
                        continue
                    if export_choice == "0":
                        path = pool.export_client_package(Path(target).expanduser())
                    elif export_choice == "1":
                        member_id = input("Pool member ID: ").strip()
                        path = pool.export_member_client_package(member_id, Path(target).expanduser())
                    else:
                        print("Unknown export type.")
                        continue
                    print("Lightweight client exported:", path)
                    print("Copy the exported files into the empty repository owned by that GitHub account, commit, and enable GitHub Pages.")
                elif choice == "7":
                    print("Public member repositories can be synchronized without a token. Private repositories require an owner-authorized credential.")
                    member_id = input("Pool member ID (leave blank for this node's own repository): ").strip()
                    if self._confirm("Read encrypted records from the selected GitHub repository?"):
                        if member_id:
                            result = pool.sync_repository(member_id=member_id, kubo=self.runtime.kubo)
                        else:
                            result = pool.sync_local_repository(kubo=self.runtime.kubo)
                        self._show("GitHub record synchronization", result)
                elif choice == "8":
                    self._show("Public record-encryption key", pool.public_encryption_key())
                else:
                    print("Unknown GitHub Identity Pool option.")
            except (GitHubIdentityPoolError, OSError, RuntimeError, ValueError) as exc:
                print(f"GitHub Identity Pool operation failed: {exc}")
            self._pause()

    def domain_verification(self) -> None:
        if self.ui is not None:
            self.ui.network_domain_verification_menu()
            return
        print("Local P2P, mesh synchronization and IPFS are separate verification domains.")
        self._pause()


def key_name(key: str) -> str:
    return {
        "1": "Storage", "2": "IPFS / Kubo", "3": "Network",
        "4": "Services", "5": "Configuration", "6": "Security",
        "7": "Diagnostics", "8": "Updates", "9": "Lifecycle",
        "10": "Identity Profile", "11": "Network Domain Verification",
        "12": "GitHub Identity Pool",
    }[key]
