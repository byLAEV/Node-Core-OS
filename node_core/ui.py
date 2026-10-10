"""Terminal interface for Node Core OS."""

from pathlib import Path
from typing import TYPE_CHECKING
import subprocess

from node_core.updates import UpdateStatus, check_for_updates

if TYPE_CHECKING:
    from node_core.runtime import NodeRuntime


class MainMenu:
    def __init__(self, runtime: "NodeRuntime") -> None:
        self.runtime = runtime

    def run(self) -> None:
        update_status = check_for_updates()
        while True:
            print("\nNode Core OS\nbyLAEV\n")
            self._print_update_status(update_status)
            print("0. Exit")
            print("1. Node Core BIOS")
            print("2. Node Core")
            print("3. My Life / Node Blog")
            print("4. Applications")
            print("Type Update to install an available Node Core OS update.")
            choice = input("\n> ").strip()
            if choice.lower() == "update":
                if not update_status.available:
                    print("No confirmed update is available. Check the network and try again.")
                    input("\n> ")
                    update_status = check_for_updates()
                    continue

                updater = self.runtime.config.data_dir / "bin" / "node-core-update"
                if not updater.is_file():
                    print("Update command not found. Reinstall the Node Core launcher first.")
                    input("\n> ")
                    continue

                result = subprocess.run([str(updater)], check=False)
                update_status = check_for_updates()
                if result.returncode != 0:
                    print(f"Update failed with exit code {result.returncode}.")
                elif update_status.checked and not update_status.available:
                    print("\nNode Core OS is updated. Reopen the menu to load the new code.")
                    return
                else:
                    print("The update could not be confirmed. Review the updater output.")
                input("\n> ")
                continue

            if choice == "0":
                return
            if choice == "1":
                self.bios()
            elif choice == "2":
                self.core()
            elif choice == "3":
                self.my_life_blog()
            elif choice == "4":
                self.applications()

    def _print_update_status(self, status: UpdateStatus) -> None:
        if status.available:
            print(f"\033[93mUPDATE AVAILABLE: {status.local_version} -> {status.remote_version}\033[0m")
            print("\033[93mType Update to update Node Core OS.\033[0m\n")
        elif status.checked:
            print(f"\033[92mUPDATED: Node Core OS {status.local_version}\033[0m\n")
        else:
            print(f"\033[90mUpdate status unavailable: {status.message}\033[0m\n")

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

    def my_life_blog(self) -> None:
        while True:
            print("\\nMy Life / Node Blog\\n")
            print("Entries are stored locally by default.")
            print("Publishing an entry adds and pins only that selected entry in IPFS.")
            print("0. Back")
            print("1. New entry")
            print("2. Browse entries")
            print("3. Search entries")
            choice = input("\\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    title = input("Title: ").strip()
                    text = input("Entry: ").strip()
                    entry = self.runtime.my_life.create_entry(title, text)
                    print("\\nEntry saved locally.")
                    print("CID: local-only")
                    print("Use Browse entries to publish this entry later.")
                    input("\\n> ")
                elif choice == "2":
                    self._browse_my_life_entries(self.runtime.my_life.list_entries())
                elif choice == "3":
                    self._search_my_life_entries()
            except Exception as exc:
                print("My Life error: " + str(exc))
                input("\\n> ")

    def _browse_my_life_entries(self, entries: list) -> None:
        page_size = 10
        page = 0
        while True:
            total = len(entries)
            page_count = max(1, (total + page_size - 1) // page_size)
            page = min(page, page_count - 1)
            start = page * page_size
            visible = entries[start:start + page_size]
            print("\\nMy Life / Node Blog — Entries")
            print(f"Entries: {total} | Page: {page + 1} of {page_count}")
            if not entries:
                print("No matching entries.")
            for number, entry in enumerate(visible, start=1):
                print(f"\\n{number}. {entry.title}")
                print(f"   Created: {entry.created_at}")
                print(f"   CID: {entry.cid or 'local-only'}")
            print("\\nEnter an entry number to open it.")
            print("N. Next page | P. Previous page | S. Search | 0. Back")
            choice = input("\\n> ").strip()
            if choice == "0":
                return
            if choice.lower() == "n":
                if page + 1 < page_count:
                    page += 1
                else:
                    print("Already on the last page.")
                    input("\\n> ")
                continue
            if choice.lower() == "p":
                if page > 0:
                    page -= 1
                else:
                    print("Already on the first page.")
                    input("\\n> ")
                continue
            if choice.lower() == "s":
                self._search_my_life_entries()
                continue
            if choice.isdigit():
                number = int(choice)
                if 1 <= number <= len(visible):
                    self._my_life_entry_details(visible[number - 1])
                    refreshed = {
                        item.entry_id: item
                        for item in self.runtime.my_life.list_entries()
                    }
                    entries = [refreshed.get(item.entry_id, item) for item in entries]
                else:
                    print(f"Choose a number from 1 to {len(visible)}.")
                    input("\\n> ")

    def _search_my_life_entries(self) -> None:
        query = input("Search by title, content, or entry ID: ").strip().casefold()
        if not query:
            print("Search query cannot be empty.")
            input("\\n> ")
            return
        matches = []
        for entry in self.runtime.my_life.list_entries():
            searchable = f"{entry.title} {entry.entry_id}".casefold()
            try:
                searchable += " " + Path(entry.text_path).read_text(encoding="utf-8").casefold()
            except OSError:
                pass
            if query in searchable:
                matches.append(entry)
        self._browse_my_life_entries(matches)

    def _my_life_entry_details(self, entry) -> None:
        while True:
            print("\\nMy Life / Node Blog — Selected Entry")
            print("\\nTitle: " + entry.title)
            print("Entry ID: " + entry.entry_id)
            print("Created: " + entry.created_at)
            print("Local file: " + entry.text_path)
            print("CID: " + (entry.cid or "local-only"))
            print("Pinned on this node: " + ("Yes" if entry.pinned else "No"))
            print("\\n1. Publish this entry to IPFS")
            print("2. Open local entry")
            print("0. Back to entries")
            choice = input("\\n> ").strip()
            if choice == "0":
                return
            if choice == "1":
                try:
                    entry = self.runtime.my_life.publish_entry(entry.entry_id)
                    print("\\nEntry publication confirmed.")
                    print("CID: " + (entry.cid or "local-only"))
                    print("Pinned: " + ("Yes" if entry.pinned else "No"))
                except Exception as exc:
                    print("\\nPublication failed: " + str(exc))
                    print("The local entry has been preserved.")
                input("\\n> ")
            elif choice == "2":
                try:
                    print("\\n--- Entry content ---")
                    print(Path(entry.text_path).read_text(encoding="utf-8"))
                except OSError as exc:
                    print("Unable to open local entry: " + str(exc))
                input("\\n> ")

    def applications(self) -> None:
        print("\nApplications\nbyLAEV\n")
        print("No applications installed.")
        print("\n[Future]")
        input("\n> ")
