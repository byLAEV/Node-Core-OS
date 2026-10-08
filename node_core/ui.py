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
        while True:
            print("\nNode Core\nbyLAEV\n")
            print("0. Back")
            print("1. Add Evidence")
            print("2. Subir archivo")
            print("3. IPFS")
            print("4. Files")
            print("5. CID Registry")
            print("6. Publish")
            print("7. Retrieve")
            print("8. Pin")
            print("9. Unpin")
            print("10. Share")
            print("11. Identity")
            print("12. Reputation")
            print("13. Protocols")
            print("14. Services")
            print("15. Utilities")
            choice = input("\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    self.add_evidence()
                elif choice == "2":
                    self.add_content()
                elif choice == "3":
                    status = self.runtime.kubo.status()
                    print(f"Kubo: {'Online' if status.running else 'Offline'}")
                    input("\n> ")
                elif choice == "5":
                    self.registry()
                elif choice == "6":
                    self.publish_content()
                elif choice == "7":
                    self.retrieve_content()
                elif choice == "8":
                    self.pin_content()
                elif choice == "9":
                    self.unpin_content()
                elif choice == "10":
                    self.share_content()
            except Exception as exc:
                print(f"Core error: {exc}")
                input("\n> ")

    def add_evidence(self) -> None:
        print("\nAdd Evidence")
        text = input("Evidence: ")
        result = self.runtime.evidence.create_text(text)

        print("\n✓ Evidence created")
        print(f"✓ Local: {result.path}")
        print(f"✓ IPFS CID: {result.content.cid}")
        print("✓ IPFS pin: Yes")
        input("\n> ")

    def add_content(self) -> None:
        print("\nSubir archivo")
        source = input("Archivo: ").strip()
        result = self.runtime.content.add(source)
        print("\n✓ Archivo agregado")
        print("✓ CID generado")
        print("✓ Contenido registrado")
        print(f"\nCID: {result.cid}")
        publish = input("\n¿Desea publicar? [Y/n] ").strip().lower()
        if publish in ("", "y", "yes"):
            published = self.runtime.content.publish(result.cid)
            print("✓ Contenido publicado")
            print(f"✓ Pin: {'Yes' if published.pinned else 'No'}")
        input("\n> ")

    def registry(self) -> None:
        print("\nCID Registry")
        records = self.runtime.content.records()
        if not records:
            print("No content records.")
        for r in records:
            print(f"\nCID: {r.cid}")
            print(f"Name: {r.name}")
            print(f"Size: {r.size} bytes")
            print(f"Pinned: {'Yes' if r.pinned else 'No'}")
            print(f"Published: {'Yes' if r.published_at else 'No'}")
            print(f"Created: {r.created_at}")
            print(f"Owner: {r.owner_id or '-'}")
        input("\n> ")

    def publish_content(self) -> None:
        print("\nPublish")
        cid = input("CID: ").strip()
        result = self.runtime.content.publish(cid)
        print(f"Published by CID: {result.cid}")
        print(f"Pinned: {'Yes' if result.pinned else 'No'}")
        print("Mode: CID")
        input("\n> ")

    def retrieve_content(self) -> None:
        print("\nRetrieve content")
        cid = input("CID: ").strip()
        destination = input("Destination file: ").strip()
        target = self.runtime.content.retrieve(cid, destination)
        print(f"Retrieved: {target}")
        input("\n> ")

    def pin_content(self) -> None:
        cid = input("\nCID to pin: ").strip()
        self.runtime.content.pin(cid)
        print(f"Pinned: {cid}")
        input("\n> ")

    def unpin_content(self) -> None:
        cid = input("\nCID to unpin: ").strip()
        self.runtime.content.unpin(cid)
        print(f"Unpinned: {cid}")
        input("\n> ")

    def share_content(self) -> None:
        print("\nShare")
        reference = self.runtime.content.share(input("CID: ").strip())
        print(f"IPFS URI: {reference.ipfs_uri}")
        print(f"Gateway: {reference.gateway_url}")
        print(f"Path: {reference.path}")
        input("\n> ")

    def applications(self) -> None:
        print("\nApplications\nbyLAEV\n")
        print("No applications installed.")
        print("\n[Future]")
        input("\n> ")
