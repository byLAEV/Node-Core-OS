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
            print("0. Exit")
            print("1. Node Core BIOS")
            print("2. Node Core")
            print("3. Applications")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice == "1":
                self.bios()
            elif choice == "2":
                self.core()
            elif choice == "3":
                self.applications()

    def bios(self) -> None:
        while True:
            print("\nNode Core BIOS\nbyLAEV\n")
            print("0. Back")
            print("1. Storage")
            print("2. IPFS / Kubo")
            print("3. Network")
            print("4. Services")
            print("5. Configuration")
            print("6. Security")
            print("7. Diagnostics")
            print("8. Updates")
            print("9. Lifecycle")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice == "1":
                self.storage_bios()
            elif choice == "2":
                self.kubo_bios()

    def storage_bios(self) -> None:
        print("\nStorage")
        print(f"Root: {self.runtime.config.local_storage_path}")
        print("Status: Ready" if self.runtime.storage.root.exists() else "Missing")
        input("\n> ")

    def kubo_bios(self) -> None:
        while True:
            status = self.runtime.kubo.status()
            print("\nIPFS / Kubo")
            print("0. Back")
            print("1. Status")
            print("2. Initialize")
            print("3. Start")
            print("4. Stop")
            print("5. Show configuration")
            print(f"\nInstalled: {'Yes' if status.installed else 'No'}")
            print(f"Initialized: {'Yes' if status.initialized else 'No'}")
            print(f"Running: {'Yes' if status.running else 'No'}")
            choice = input("\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    print(f"Peer ID: {status.peer_id or '-'}")
                    print(f"Version: {status.version or '-'}")
                    input("\n> ")
                elif choice == "2":
                    self.runtime.kubo.initialize()
                    print("Kubo repository initialized.")
                    input("\n> ")
                elif choice == "3":
                    self.runtime.kubo.start()
                    print("Kubo daemon started.")
                    input("\n> ")
                elif choice == "4":
                    self.runtime.kubo.stop()
                    print("Kubo daemon stopped.")
                    input("\n> ")
                elif choice == "5":
                    print(f"Repository: {self.runtime.config.ipfs_repo_path}")
                    print(f"RPC API: {self.runtime.config.ipfs_api}")
                    print(f"Gateway: {self.runtime.config.ipfs_gateway}")
                    print(f"Executable: {self.runtime.config.ipfs_executable}")
                    print(f"Import profile: {self.runtime.config.ipfs_profile}")
                    input("\n> ")
            except Exception as exc:
                print(f"BIOS error: {exc}")
                input("\n> ")

    def core(self) -> None:
        print("\nNode Core\nbyLAEV\n")
        for item in (
            "0. Back", "1. Storage", "2. IPFS", "3. Files", "4. CID",
            "5. Publish", "6. Retrieve", "7. Pin", "8. Unpin", "9. Share",
            "10. Identity", "11. Reputation", "12. Protocols", "13. Services",
            "14. Utilities",
        ):
            print(item)
        input("\n> ")

    def applications(self) -> None:
        print("\nApplications\nbyLAEV\n")
        print("No applications installed.")
        print("\n[Future]")
        input("\n> ")
