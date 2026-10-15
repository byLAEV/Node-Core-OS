"""Terminal interface for Node Core OS."""

from pathlib import Path
from typing import TYPE_CHECKING
import subprocess
import sys

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
            self._print_identity_summary()
            self._print_update_status(update_status)
            print("0. Exit")
            print("1. Node Core BIOS")
            print("2. Node Core")
            print("3. My Life / Node Blog")
            print("4. Applications")
            print("5. Network / Nodes")
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
            elif choice == "5":
                self.network_nodes()

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
            print("10. Identity Profile")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice == "1":
                self.storage_bios()
            elif choice == "2":
                self.kubo_bios()
            elif choice == "10":
                self.identity_bios()

    def identity_presence_menu(self) -> None:
        """Create and exchange public identity-presence claims and shared reports."""
        service = self.runtime.identity_presence
        while True:
            print("\nIdentity Presence / Shared Report")
            print("0. Back")
            print("1. Publish my association declaration (get CID)")
            print("2. Import another node's declaration by CID")
            print("3. Create report from declarations received")
            print("4. Publish and pin current report (get CID)")
            print("5. Import and pin a shared report by CID")
            print("6. Show local evidence and report status")
            choice = input("\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    result = service.publish_announcement()
                    print("\nDeclaration published and pinned locally.")
                    print(f"Public node ID: {result['node_id']}")
                    print(f"Announcement CID: {result['cid']}")
                    print("Share this CID with the other nodes.")
                    input("\n> ")
                elif choice == "2":
                    cid = input("Announcement CID: ").strip()
                    result = service.import_announcement(cid)
                    print(f"Declaration received for node: {result['node_id']}")
                    print(f"Association announced: {result['identity_associated']}")
                    print("Status: announced, not verified.")
                    input("\n> ")
                elif choice == "3":
                    report = service.create_report()
                    print("Report saved locally.")
                    print(f"Reference: {report['report_reference_id']}")
                    print(f"Known nodes: {report['known_nodes']}")
                    print(f"Associations announced: {report['identity_associations_announced']}")
                    print("Personal identity fields transmitted: 0")
                    input("\n> ")
                elif choice == "4":
                    result = service.publish_report()
                    print("Report published and pinned on this node.")
                    print(f"Report reference: {result['report_reference_id']}")
                    print(f"Report CID: {result['report_cid']}")
                    print("Share this CID with the other nodes.")
                    input("\n> ")
                elif choice == "5":
                    cid = input("Shared report CID: ").strip()
                    result = service.import_report(cid)
                    print("Exact report content saved locally and pinned.")
                    print(f"Report reference: {result['report_reference_id']}")
                    print(f"Report CID: {result['report_cid']}")
                    input("\n> ")
                elif choice == "6":
                    status = service.status()
                    print(f"Local declarations known: {status['announcement_count']}")
                    if status["report"]:
                        report = status["report"]
                        print(f"Report reference: {report.get('report_reference_id')}")
                        print(f"Known nodes: {report.get('known_nodes')}")
                        print(f"Associations announced: {report.get('identity_associations_announced')}")
                    else:
                        print("No shared report saved yet.")
                    if status["state"]:
                        print(f"Report CID: {status['state'].get('report_cid')}")
                        print(f"Pinned locally: {status['state'].get('pinned_locally')}")
                    input("\n> ")
            except Exception as exc:
                print(f"Identity presence error: {exc}")
                input("\n> ")

    def _print_identity_summary(self) -> None:
        """Show the saved identity fields and their verification status."""
        try:
            profile = self.runtime.identity_profile.load()
        except (OSError, ValueError) as exc:
            print(f"Identity profile unavailable: {exc}")
            return
        if profile is None:
            print("Identity: Not configured (Node Core BIOS > Identity Profile).")
            return

        print(f"Name: {profile['full_name']}")
        print(f"Alias: {profile.get('alias') or '-'}")
        print(f"Nationality: {profile.get('nationality') or '-'}")
        print(f"Issuing country: {profile['issuing_country']}")
        print(f"Document type: {profile['document_type']}")
        print(f"Document number: {profile['document_number']}")
        print(f"Date of birth: {profile.get('birth_date') or '-'}")
        print(f"Height: {str(profile.get('height_cm')) + ' cm' if profile.get('height_cm') else '-'}")
        print(f"Gender: {profile.get('gender') or '-'}")
        print(f"Identity data first entered (UTC): {profile.get('created_at') or '-'}")
        print(f"Identity data last updated (UTC): {profile.get('updated_at') or '-'}")
        print(f"Logical identity ID: {profile['identity_id']}")
        print(f"Node ID: {profile.get('node_id') or 'Not associated'}")
        print(f"Identity data status: {profile['identity_status'].capitalize()}")
        print("Node Core OS network consensus verification: Not verified")

    def identity_bios(self) -> None:
        """Manage the user's declared identity profile and node association."""
        store = self.runtime.identity_profile
        while True:
            print("\nIdentity Profile")
            try:
                profile = store.load()
            except (OSError, ValueError) as exc:
                print(f"Could not read identity profile: {exc}")
                input("\n> ")
                return

            if profile:
                print(f"Name: {profile['full_name']}")
                print(f"Alias: {profile.get('alias') or '-'}")
                print(f"Nationality: {profile.get('nationality') or '-'}")
                print(f"Date of birth: {profile.get('birth_date') or '-'}")
                print(f"Height: {str(profile.get('height_cm')) + ' cm' if profile.get('height_cm') else '-'}")
                print(f"Gender: {profile.get('gender') or '-'}")
                print(f"Identity data first entered (UTC): {profile.get('created_at') or '-'}")
                print(f"Identity data last updated (UTC): {profile.get('updated_at') or '-'}")
                print(f"Identity status: {profile['identity_status']}")
                print(f"Node ID: {profile.get('node_id') or 'Not associated'}")
            else:
                print("No identity profile has been saved.")

            print("\n0. Back")
            print("1. Enter or edit identity document data")
            print("2. Associate profile with this node")
            print("3. View profile details (document number masked)")
            choice = input("\n> ").strip()

            if choice == "0":
                return
            if choice == "1":
                previous = profile or {}
                full_name = input(
                    f"Full name [{previous.get('full_name', '')}]: "
                ).strip() or previous.get("full_name", "")
                alias = input(
                    f"Alias [{previous.get('alias', '')}]: "
                ).strip() or previous.get("alias", "")
                nationality = input(
                    f"Nationality [{previous.get('nationality', '')}]: "
                ).strip() or previous.get("nationality", "")
                issuing_country = input(
                    f"Issuing country [{previous.get('issuing_country', 'Costa Rica')}]: "
                ).strip() or previous.get("issuing_country", "Costa Rica")
                document_type = input(
                    f"Document type [{previous.get('document_type', 'National identity document')}]: "
                ).strip() or previous.get("document_type", "National identity document")
                document_number = input(
                    "Document number (leave blank to keep the saved value): "
                ).strip() or previous.get("document_number", "")
                birth_date = input(
                    f"Date of birth YYYY-MM-DD [{previous.get('birth_date', '')}]: "
                ).strip() or previous.get("birth_date", "")
                previous_height = previous.get("height_cm")
                height_default = str(previous_height) if previous_height else ""
                height_cm = input(
                    f"Height in centimeters (optional) [{height_default}]: "
                ).strip() or height_default
                gender = input(
                    f"Gender (optional, self-described) [{previous.get('gender', '')}]: "
                ).strip() or previous.get("gender", "")
                try:
                    saved = store.save_declared_profile(
                        full_name=full_name,
                        alias=alias,
                        nationality=nationality,
                        issuing_country=issuing_country,
                        document_type=document_type,
                        document_number=document_number,
                        birth_date=birth_date,
                        height_cm=height_cm,
                        gender=gender,
                    )
                    print("Identity profile saved locally as declared data.")
                    print("No document photo or video was requested.")
                    print(f"Logical identity ID: {saved['identity_id']}")
                    print("No identity verification has been performed.")
                except (OSError, ValueError) as exc:
                    print(f"Could not save identity profile: {exc}")
                input("\n> ")
            elif choice == "2":
                if profile is None:
                    print("Enter identity data before associating a node.")
                    input("\n> ")
                    continue
                try:
                    status = self.runtime.kubo.status()
                    node_id = status.peer_id
                    if not node_id:
                        print("No Kubo Peer ID is currently available.")
                        if status.initialized:
                            print("Start Kubo and ensure its API is available, then retry.")
                        else:
                            print("Initialize and start Kubo, then return here to associate the profile.")
                    else:
                        store.associate_node(node_id)
                        print("Identity profile associated with the current node.")
                        print(f"Node ID: {node_id}")
                except Exception as exc:
                    print(f"Could not associate identity with this node: {exc}")
                input("\n> ")
            elif choice == "3":
                if profile is None:
                    print("No identity profile has been saved.")
                else:
                    number = profile.get("document_number", "")
                    masked_number = (
                        ("*" * max(0, len(number) - 4) + number[-4:])
                        if number
                        else "-"
                    )
                    print(f"Logical identity ID: {profile['identity_id']}")
                    print(f"Name: {profile['full_name']}")
                    print(f"Alias: {profile.get('alias') or '-'}")
                    print(f"Nationality: {profile.get('nationality') or '-'}")
                    print(f"Issuing country: {profile['issuing_country']}")
                    print(f"Document type: {profile['document_type']}")
                    print(f"Document number: {masked_number}")
                    print(f"Date of birth: {profile.get('birth_date') or '-'}")
                    print(f"Height: {str(profile.get('height_cm')) + ' cm' if profile.get('height_cm') else '-'}")
                    print(f"Gender: {profile.get('gender') or '-'}")
                    print(f"Identity data first entered (UTC): {profile.get('created_at') or '-'}")
                    print(f"Identity data last updated (UTC): {profile.get('updated_at') or '-'}")
                    print(f"Identity status: {profile['identity_status']}")
                    print(f"Node ID: {profile.get('node_id') or 'Not associated'}")
                    print("Storage: Local only; not published to IPFS.")
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
            print("0. Back")
            print("1. Status")
            print("2. Initialize")
            print("3. Start")
            print("4. Stop")
            print("5. Show configuration")
            print(f"\nInstalled: {'Yes' if status.installed else 'No'}")
            print(f"Initialized: {'Yes' if status.initialized else 'No'}")
            print(f"Running: {'Yes' if status.running else 'No'}")
            print("Daemon mode: detached background process")
            print(f"Daemon log: {self.runtime.kubo.log_path}")
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
            print("16. External CID Library")
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
                elif choice == "16":
                    self.external_cid_library()
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

    def external_cid_library(self) -> None:
        library = self.runtime.external_cids
        while True:
            print("\nEXTERNAL CID LIBRARY")
            print("0. Back")
            print("1. Add External CID")
            print("2. Browse CID History")
            print("3. Search Saved References")
            print("4. View Reference Details")
            print("5. Read Content by CID")
            print("6. Pin Content on This Node")
            print("7. Check Local Pin Status")
            print("8. Unpin Content from This Node")
            print("9. Edit Reference")
            print("10. Remove Reference from History")
            choice = input("\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    cid = input("CID: ").strip()
                    description = input("Description: ").strip()
                    source_node = input("Source node (optional): ").strip()
                    notes = input("Notes (optional): ").strip()
                    reference = library.add(
                        cid, description, source_node=source_node, notes=notes
                    )
                    print("Reference saved locally.")
                    print(f"Reference ID: {reference.reference_id}")
                    input("\n> ")
                elif choice == "2":
                    self._browse_external_cids(library.list())
                elif choice == "3":
                    query = input("Search: ").strip()
                    self._browse_external_cids(library.search(query))
                elif choice == "4":
                    reference = library.get(input("Reference ID: ").strip())
                    if reference is None:
                        print("Reference not found.")
                    else:
                        self._show_external_cid_details(reference)
                    input("\n> ")
                elif choice == "5":
                    cid = input("CID to retrieve: ").strip()
                    destination = input("Destination file: ").strip()
                    target = library.retrieve(cid, destination)
                    print(f"Retrieved to: {target}")
                    input("\n> ")
                elif choice == "6":
                    cid = input("CID to pin: ").strip()
                    library.pin(cid)
                    print("Kubo accepted the pin request.")
                    input("\n> ")
                elif choice == "7":
                    cid = input("CID to check: ").strip()
                    print(
                        "Pinned on this node."
                        if library.is_pinned_locally(cid)
                        else "Not pinned on this node."
                    )
                    input("\n> ")
                elif choice == "8":
                    cid = input("CID to unpin: ").strip()
                    library.unpin(cid)
                    print("Kubo accepted the unpin request.")
                    input("\n> ")
                elif choice == "9":
                    reference_id = input("Reference ID: ").strip()
                    reference = library.get(reference_id)
                    if reference is None:
                        print("Reference not found.")
                        input("\n> ")
                        continue
                    description = input(f"Description [{reference.description}]: ")
                    source_node = input(f"Source node [{reference.source_node}]: ")
                    notes = input(f"Notes [{reference.notes}]: ")
                    library.update(
                        reference_id,
                        description=description if description.strip() else None,
                        source_node=source_node if source_node.strip() else None,
                        notes=notes if notes.strip() else None,
                    )
                    print("Reference updated.")
                    input("\n> ")
                elif choice == "10":
                    reference_id = input("Reference ID to remove: ").strip()
                    if library.remove(reference_id):
                        print("Reference removed from the local history.")
                        print("No content was unpinned or deleted.")
                    else:
                        print("Reference not found.")
                    input("\n> ")
            except Exception as exc:
                print(f"External CID Library error: {exc}")
                input("\n> ")

    def _browse_external_cids(self, references: list) -> None:
        if not references:
            print("No matching external CID references.")
            input("\n> ")
            return
        for number, reference in enumerate(references, start=1):
            print(f"\n{number}. {reference.description}")
            print(f"   CID: {reference.cid}")
            print(f"   Reference ID: {reference.reference_id}")
            print(f"   Added: {reference.added_at}")
        input("\n> ")

    @staticmethod
    def _show_external_cid_details(reference) -> None:
        print("\nExternal CID Reference")
        print(f"Reference ID: {reference.reference_id}")
        print(f"CID: {reference.cid}")
        print(f"Description: {reference.description}")
        print(f"Source node: {reference.source_node or '-'}")
        print(f"Added: {reference.added_at}")
        print(f"Notes: {reference.notes or '-'}")

    def my_life_blog(self) -> None:
        while True:
            print("\nMy Life / Node Blog\n")
            print("Entries are stored locally by default.")
            print("Publishing an entry adds and pins only that selected entry in IPFS.")
            print("0. Back")
            print("1. New entry")
            print("2. Browse entries")
            print("3. Search entries")
            choice = input("\n> ").strip()
            try:
                if choice == "0":
                    return
                if choice == "1":
                    title = input("Title: ").strip()
                    text = input("Entry: ").strip()
                    entry = self.runtime.my_life.create_entry(title, text)
                    print("\nEntry saved locally.")
                    print("CID: local-only")
                    print("Use Browse entries to publish this entry later.")
                    input("\n> ")
                elif choice == "2":
                    self._browse_my_life_entries(self.runtime.my_life.list_entries())
                elif choice == "3":
                    self._search_my_life_entries()
            except Exception as exc:
                print("My Life error: " + str(exc))
                input("\n> ")

    def _browse_my_life_entries(self, entries: list) -> None:
        page_size = 10
        page = 0
        while True:
            total = len(entries)
            page_count = max(1, (total + page_size - 1) // page_size)
            page = min(page, page_count - 1)
            start = page * page_size
            visible = entries[start:start + page_size]
            print("\nMy Life / Node Blog — Entries")
            print(f"Entries: {total} | Page: {page + 1} of {page_count}")
            if not entries:
                print("No matching entries.")
            for number, entry in enumerate(visible, start=1):
                print(f"\n{number}. {entry.title}")
                print(f"   Created: {entry.created_at}")
                print(f"   CID: {entry.cid or 'local-only'}")
            print("\nEnter an entry number to open it.")
            print("N. Next page | P. Previous page | S. Search | 0. Back")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice.lower() == "n":
                if page + 1 < page_count:
                    page += 1
                else:
                    print("Already on the last page.")
                    input("\n> ")
                continue
            if choice.lower() == "p":
                if page > 0:
                    page -= 1
                else:
                    print("Already on the first page.")
                    input("\n> ")
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
                    input("\n> ")

    def _search_my_life_entries(self) -> None:
        query = input("Search by title, content, or entry ID: ").strip().casefold()
        if not query:
            print("Search query cannot be empty.")
            input("\n> ")
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
            print("\nMy Life / Node Blog — Selected Entry")
            print("\nTitle: " + entry.title)
            print("Entry ID: " + entry.entry_id)
            print("Created: " + entry.created_at)
            print("Local file: " + entry.text_path)
            print("CID: " + (entry.cid or "local-only"))
            print("Pinned on this node: " + ("Yes" if entry.pinned else "No"))
            print("\n1. Publish this entry to IPFS")
            print("2. Open local entry")
            print("0. Back to entries")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice == "1":
                pin_choice = input("Pin this entry on this node? [Y/n] ").strip().lower()
                pin = pin_choice not in ("n", "no")
                try:
                    entry = self.runtime.my_life.publish_entry(entry.entry_id, pin=pin)
                    print("\nEntry publication confirmed.")
                    print("CID: " + (entry.cid or "local-only"))
                    print("Pinned on this node: " + ("Yes" if entry.pinned else "No"))
                except Exception as exc:
                    print("\nPublication failed: " + str(exc))
                    print("The local entry has been preserved.")
                input("\n> ")
            elif choice == "2":
                try:
                    print("\n--- Entry content ---")
                    print(Path(entry.text_path).read_text(encoding="utf-8"))
                except OSError as exc:
                    print("Unable to open local entry: " + str(exc))
                input("\n> ")

    def applications(self) -> None:
        """Launch applications shipped with the current Node Core OS code tree."""
        application_root = Path(__file__).resolve().parents[1]
        hashpaper_entry = application_root / "applications" / "hashpaper" / "main.py"
        p2p_contracts_entry = application_root / "applications" / "p2p_contracts" / "main.py"
        while True:
            print("\nApplications\nbyLAEV\n")
            print("0. Back")
            print("1. HashPaper for Node Core OS")
            print("2. P2P Contracts — BTC Exchange and Reputation (development prototype)")
            choice = input("\n> ").strip()
            if choice == "0":
                return
            if choice not in {"1", "2"}:
                print("Choose an available application.")
                continue
            entry = hashpaper_entry if choice == "1" else p2p_contracts_entry
            application_name = "HashPaper" if choice == "1" else "P2P Contracts"
            if not entry.is_file():
                print(f"{application_name} is not installed in this Node Core OS application tree.")
                input("\n> ")
                continue
            result = subprocess.run(
                [sys.executable, str(entry)],
                cwd=str(application_root),
                check=False,
            )
            if result.returncode != 0:
                print(f"{application_name} exited with status {result.returncode}.")
                input("\n> ")

    def network_nodes(self) -> None:
        """Manage native authenticated P2P and the separate Kubo/IPFS network."""
        while True:
            print("\nNode Core OS — Network / Nodes")
            print("0. Back")
            print("1. Native P2P status")
            print("2. List trusted native peers")
            print("3. Trust peer certificate")
            print("4. Revoke trusted peer")
            print("5. Start native P2P listener")
            print("6. Stop native P2P listener")
            print("7. Refresh Kubo/IPFS network status")
            print("8. Connect to Kubo/IPFS peer")
            print("9. Ping Kubo/IPFS peer")
            print("10. Identity Presence / Shared Report")
            print("11. Query trusted native peer status")
            choice = input("\n> ").strip()

            if choice == "0":
                return

            try:
                if choice == "1":
                    status = self.runtime.native_p2p_status()
                    print("\nNative Node Core OS P2P")
                    print(f"Local node ID: {status['node_id']}")
                    print(f"Service: {'RUNNING' if status['service_running'] else 'STOPPED'}")
                    address = status["listen_address"]
                    print(f"Listen address: {address[0]}:{address[1]}" if address else "Listen address: -")
                    print(f"Trusted peers: {status['trusted_count']}")
                    print(f"Revoked peers: {status['revoked_count']}")
                    active_peers = status["active_peers"]
                    print(f"Authenticated inbound sessions: {len(active_peers)}")
                    for peer in active_peers:
                        print(f"- {peer['node_id']}")
                        print(f"  Connected at (UTC): {peer['connected_at']}")
                        print(f"  Last seen (UTC): {peer['last_seen']}")
                    print(f"Local certificate: {status['certificate_path']}")
                    if status["last_error"]:
                        print(f"Last service error: {status['last_error']}")
                    print("This is native P2P status; it is separate from Kubo/IPFS.")
                    input("\n> ")
                elif choice == "2":
                    peers = self.runtime.p2p_trust.list_peers()
                    print("\nTrusted native peers")
                    if not peers:
                        print("No peers registered.")
                    for peer in peers:
                        print(f"- {peer['node_id']} [{peer['status']}]")
                        print(f"  Label: {peer['label'] or '-'}")
                        print(f"  Certificate SHA-256: {peer['fingerprint_sha256']}")
                        print(f"  Added: {peer['added_at']}")
                        if peer["revoked_at"]:
                            print(f"  Revoked: {peer['revoked_at']}")
                    input("\n> ")
                elif choice == "3":
                    print("Verify the certificate fingerprint with the peer operator through a separate trusted channel.")
                    node_id = input("Peer node ID (sha256:...): ").strip()
                    certificate_path = input("Path to peer certificate PEM: ").strip()
                    label = input("Optional peer label: ").strip()
                    result = self.runtime.trust_peer_certificate(
                        node_id, Path(certificate_path), label
                    )
                    print("Peer certificate trusted.")
                    print(f"Node ID: {result['node_id']}")
                    print(f"Certificate SHA-256: {result['fingerprint_sha256']}")
                    print("Keep the peer certificate file public; never copy a private key.")
                    input("\n> ")
                elif choice == "4":
                    node_id = input("Node ID to revoke (sha256:...): ").strip()
                    confirm = input(f"Type REVOKE to revoke {node_id}: ").strip()
                    if confirm != "REVOKE":
                        print("Revocation cancelled.")
                    else:
                        result = self.runtime.revoke_trusted_peer(node_id)
                        print(f"Peer revoked: {result['node_id']}")
                        print("Native P2P listener stopped; restart only after reviewing its trust list.")
                    input("\n> ")
                elif choice == "5":
                    host = input("Listen host [127.0.0.1; use 0.0.0.0 only when intentionally exposing the service]: ").strip() or "127.0.0.1"
                    raw_port = input("Listen port [0 for OS-assigned]: ").strip() or "0"
                    address = self.runtime.start_native_p2p(host, int(raw_port))
                    print(f"Native P2P listener running at {address[0]}:{address[1]}")
                    print("Only explicitly trusted peer certificates are accepted.")
                    input("\n> ")
                elif choice == "6":
                    self.runtime.stop_native_p2p()
                    print("Native P2P listener stopped.")
                    input("\n> ")
                elif choice == "7":
                    status = self.runtime.network.status()
                    print("\nKubo / IPFS network")
                    print(f"Local peer ID: {status.identity.peer_id}")
                    print(f"Directly connected peers: {len(status.connected_peers)}")
                    print(f"Nodes observed (local + direct peers): {len(status.connected_peers) + 1}")
                    for peer_id in status.connected_peers:
                        print(f"- {peer_id}")
                    if not status.connected_peers:
                        print("No directly connected Kubo peers were reported.")
                    print("This is not a count of every node on the IPFS network.")
                    input("\n> ")
                elif choice == "8":
                    address = input("Complete Kubo peer multiaddress: ").strip()
                    result = self.runtime.network.connect(address)
                    print("Kubo connection request completed.")
                    print(result)
                    input("\n> ")
                elif choice == "9":
                    peer_id = input("Kubo peer ID: ").strip()
                    print(self.runtime.network.ping(peer_id))
                    input("\n> ")
                elif choice == "10":
                    self.identity_presence_menu()
                elif choice == "11":
                    node_id = input("Trusted peer node ID (sha256:...): ").strip()
                    host = input("Peer host/IP: ").strip()
                    port = int(input("Peer TCP port: ").strip())
                    result = self.runtime.query_native_peer_status(host, port, node_id)
                    print("\nAuthenticated native peer status")
                    print(f"Node ID: {result['node_id']}")
                    print(f"State: {result['state']}")
                    print(f"Observed at (UTC): {result['observed_at']}")
                    print(f"Request ID: {result['request_id']}")
                    input("\n> ")
            except (ValueError, OSError, RuntimeError) as exc:
                print(f"Network error: {exc}")
                input("\n> ")

