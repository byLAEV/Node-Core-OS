"""Terminal interface for Node Core OS."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from node_core.runtime import NodeRuntime


class MainMenu:
    def __init__(self, runtime: "NodeRuntime") -> None:
        self.runtime = runtime

    def run(self) -> None:
        while True:
            print("\nNode Core OS\nbyLAEV\n")
            print("0. Exit\n1. Node Core BIOS\n2. Node Core\n3. Applications")
            choice = input("\n> ").strip()
            if choice == "0": return
            if choice == "1": self.bios()
            elif choice == "2": self.core()
            elif choice == "3": self.applications()

    def bios(self) -> None:
        while True:
            print("\nNode Core BIOS\nbyLAEV\n")
            print("0. Back\n1. Storage\n2. IPFS / Kubo\n3. Network\n4. Services")
            print("5. Configuration\n6. Security\n7. Diagnostics\n8. Updates\n9. Lifecycle")
            choice = input("\n> ").strip()
            if choice == "0": return
            if choice == "1": self.storage_bios()
            elif choice == "2": self.kubo_bios()
            elif choice == "6": self.security_bios()

    def security_bios(self) -> None:
        while True:
            print("\nSecurity\nbyLAEV\n")
            print("0. Back\n1. Node Identity\n2. Keys\n3. Backup\n4. Providers\n5. Verify Backup")
            choice = input("\n> ").strip()
            if choice == "0": return
            if choice == "1": self.node_identity()
            elif choice == "2": self.key_status()
            elif choice == "3": self.backup_bios()
            elif choice == "4": self.providers_bios()

    def node_identity(self) -> None:
        try:
            status = self.runtime.backup.status()
            print("\nNode Identity")
            print(f"Peer ID: {status['peer_id'] or '-'}")
            print(f"Kubo: {status['kubo_version'] or '-'}")
        except Exception as exc:
            print(f"Security error: {exc}")
        input("\n> ")

    def key_status(self) -> None:
        try:
            keys = self.runtime.backup.kubo.list_keys()
            print("\nKeys")
            if not keys: print("No Kubo-managed keys found.")
            for key in keys: print(f"- {key}")
        except Exception as exc:
            print(f"Security error: {exc}")
        input("\n> ")

    def backup_bios(self) -> None:
        while True:
            print("\nBackup")
            print("0. Back\n1. Inspect backup metadata\n2. Create encrypted backup [V1]")
            print("3. Export to file [V1]\n4. Upload to Pinata [V1]\n5. Backup History")
            choice = input("\n> ").strip()
            if choice == "0": return
            if choice == "1":
                try:
                    result = self.runtime.backup.inspect()
                    print(result["manifest"])
                    print(f"Keys: {', '.join(result['keys']) or '-'}")
                except Exception as exc:
                    print(f"Backup error: {exc}")
                input("\n> ")
            elif choice in {"2", "3", "4", "5"}:
                print("\n[Foundation ready — operation is implemented in the next V1 phase.]")
                input("\n> ")

    def providers_bios(self) -> None:
        print("\nProviders\n")
        print("1. Pinata [V1]")
        print("\nAuthentication: configure a Pinata API credential, not a Google/GitHub login.")
        input("\n> ")

    def storage_bios(self) -> None:
        print("\nStorage")
        print(f"Root: {self.runtime.config.local_storage_path}")
        print("Status: Ready" if self.runtime.storage.root.exists() else "Missing")
        input("\n> ")

    def kubo_bios(self) -> None:
        while True:
            status = self.runtime.kubo.status()
            print("\nIPFS / Kubo")
            print("0. Back\n1. Status\n2. Initialize\n3. Start\n4. Stop\n5. Show configuration")
            print(f"\nInstalled: {'Yes' if status.installed else 'No'}")
            print(f"Initialized: {'Yes' if status.initialized else 'No'}")
            print(f"Running: {'Yes' if status.running else 'No'}")
            choice = input("\n> ").strip()
            try:
                if choice == "0": return
                if choice == "1":
                    print(f"Peer ID: {status.peer_id or '-'}\nVersion: {status.version or '-'}"); input("\n> ")
                elif choice == "2": self.runtime.kubo.initialize(); input("\nKubo repository initialized.\n> ")
                elif choice == "3": self.runtime.kubo.start(); input("\nKubo daemon started.\n> ")
                elif choice == "4": self.runtime.kubo.stop(); input("\nKubo daemon stopped.\n> ")
                elif choice == "5":
                    print(f"Repository: {self.runtime.config.ipfs_repo_path}")
                    print(f"RPC API: {self.runtime.config.ipfs_api}")
                    print(f"Gateway: {self.runtime.config.ipfs_gateway}")
                    input("\n> ")
            except Exception as exc:
                print(f"BIOS error: {exc}"); input("\n> ")

    def core(self) -> None:
        print("\nNode Core\nbyLAEV\n")
        print("Existing Core functions remain available.")
        input("\n> ")

    def applications(self) -> None:
        print("\nApplications\nbyLAEV\n")
        print("No applications installed.\n[Future]")
        input("\n> ")
