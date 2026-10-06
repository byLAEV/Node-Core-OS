"""Initial terminal interface matching the Node Core OS architecture."""

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
        if choice == "2":
            print(f"Kubo API: {self.runtime.config.ipfs_api}")
            print("Status:", "Online" if self.runtime.ipfs.status() else "Offline")

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
