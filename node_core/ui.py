"""Terminal interface for Node Core OS."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from node_core.runtime import NodeRuntime

class MainMenu:
    def __init__(self,runtime:"NodeRuntime"): self.runtime=runtime
    def run(self):
        while True:
            print("\nNode Core OS\nbyLAEV\n\n0. Exit\n1. Node Core BIOS\n2. Node Core\n3. Applications")
            choice=input("\n> ").strip()
            if choice=="0": return
            if choice=="1": self.bios()
            elif choice=="2": self.core()
            elif choice=="3": self.applications()
    def bios(self):
        while True:
            print("\nNode Core BIOS\nbyLAEV\n\n0. Back\n1. Storage\n2. IPFS / Kubo\n3. Network\n4. Services\n5. Configuration\n6. Security\n7. Diagnostics\n8. Updates\n9. Lifecycle")
            choice=input("\n> ").strip()
            if choice=="0": return
            if choice=="1": self.storage_bios()
            elif choice=="2": self.kubo_bios()
    def storage_bios(self):
        print(f"\nStorage\nRoot: {self.runtime.config.local_storage_path}\nStatus: {'Ready' if self.runtime.storage.root.exists() else 'Missing'}"); input("\n> ")
    def kubo_bios(self):
        while True:
            status=self.runtime.kubo.status()
            print(f"\nIPFS / Kubo\n0. Back\n1. Status\n2. Initialize\n3. Start\n4. Stop\n5. Show configuration\n\nInstalled: {'Yes' if status.installed else 'No'}\nInitialized: {'Yes' if status.initialized else 'No'}\nRunning: {'Yes' if status.running else 'No'}")
            choice=input("\n> ").strip()
            try:
                if choice=="0": return
                if choice=="1": print(f"Peer ID: {status.peer_id or '-'}\nVersion: {status.version or '-'}"); input("\n> ")
                elif choice=="2": self.runtime.kubo.initialize(); print("Kubo repository initialized."); input("\n> ")
                elif choice=="3": self.runtime.kubo.start(); print("Kubo daemon started."); input("\n> ")
                elif choice=="4": self.runtime.kubo.stop(); print("Kubo daemon stopped."); input("\n> ")
                elif choice=="5": print(f"Repository: {self.runtime.config.ipfs_repo_path}\nRPC API: {self.runtime.config.ipfs_api}\nGateway: {self.runtime.config.ipfs_gateway}\nExecutable: {self.runtime.config.ipfs_executable}\nImport profile: {self.runtime.config.ipfs_profile}"); input("\n> ")
            except Exception as exc: print(f"BIOS error: {exc}"); input("\n> ")
    def core(self):
        while True:
            print("\nNode Core\nbyLAEV\n\n0. Back\n1. Storage\n2. IPFS\n3. Files\n4. CID Registry\n5. Publish\n6. Retrieve\n7. Pin\n8. Unpin\n9. Share\n10. Identity\n11. Reputation\n12. Protocols\n13. Services\n14. Utilities")
            choice=input("\n> ").strip()
            try:
                if choice=="0": return
                if choice=="2": print(f"Kubo: {'Online' if self.runtime.kubo.status().running else 'Offline'}"); input("\n> ")
                elif choice=="4": self.registry()
                elif choice=="5": self.add_content()
                elif choice=="6": self.retrieve_content()
                elif choice=="7": self.pin_content()
                elif choice=="8": self.unpin_content()
                elif choice=="9": print("Share is reserved for the publishing/sharing layer."); input("\n> ")
            except Exception as exc: print(f"Core error: {exc}"); input("\n> ")
    def registry(self):
        print("\nCID Registry")
        records=self.runtime.content.records()
        if not records: print("No content records.")
        for r in records: print(f"\nCID: {r.cid}\nName: {r.name}\nSize: {r.size} bytes\nPinned: {'Yes' if r.pinned else 'No'}\nCreated: {r.created_at}\nOwner: {r.owner_id or '-'}")
        input("\n> ")
    def add_content(self):
        result=self.runtime.content.add(input("\nLocal file path: ").strip(),pin=input("Pin immediately? [y/N]: ").strip().lower()=="y")
        print(f"Name: {result.name}\nSize: {result.size} bytes\nCID: {result.cid}\nRegistry: {self.runtime.content.registry.path}"); input("\n> ")
    def retrieve_content(self):
        target=self.runtime.content.retrieve(input("\nCID: ").strip(),input("Destination file: ").strip()); print(f"Retrieved: {target}"); input("\n> ")
    def pin_content(self):
        cid=input("\nCID to pin: ").strip(); self.runtime.content.pin(cid); print(f"Pinned: {cid}"); input("\n> ")
    def unpin_content(self):
        cid=input("\nCID to unpin: ").strip(); self.runtime.content.unpin(cid); print(f"Unpinned: {cid}"); input("\n> ")
    def applications(self):
        print("\nApplications\nbyLAEV\n\nNo applications installed.\n\n[Future]"); input("\n> ")
