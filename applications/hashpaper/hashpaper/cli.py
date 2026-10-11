"""Initial HashPaper command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import termios
import tty

_SESSION_IDENTITY = None
_SESSION_PEER_ID = None

from .documents import build_transparent_package, write_original, write_package
from .timestamp import OpenTimestampsClient, TimestampError
from .publication import PublicationError
from .identity import IdentityIntegrationError, associate_identity_with_peer, load_identity_and_peer_id


def _expanded_path(value: str | Path) -> Path:
    """Expand home and environment variables in paths supplied by scripts or users."""
    return Path(os.path.expandvars(str(value))).expanduser()


def _data_dir() -> Path:
    return _expanded_path(os.environ.get("NODE_CORE_DATA_DIR", str(Path.home() / ".node-core")))


def _hashpaper_dir() -> Path:
    """Return the private root directory used exclusively by HashPaper."""
    return _data_dir() / "hashpaper"


def _documents_dir() -> Path:
    return _hashpaper_dir() / "documents"


def _ipfs_dir() -> Path:
    return _hashpaper_dir() / "ipfs"


def _records_dir() -> Path:
    return _hashpaper_dir() / "records"


def _has_terminal_control_characters(path: Path) -> bool:
    """Treat unreadable or non-UTF-8 originals as unsuitable for text workflows."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True
    return any(ord(character) < 32 and character not in "\t\n\r" for character in content)


def _default_document_path(
    *,
    for_create: bool = False,
    require_proof: bool = False,
    require_unstamped: bool = False,
) -> Path | None:
    """Choose a document appropriate to the requested operation."""
    directory = _documents_dir()
    directory.mkdir(parents=True, exist_ok=True)
    if not for_create:
        candidates = [
            path for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".markdown"}
            and not path.stem.endswith("-ipfs")
        ]
        if require_proof:
            candidates = [
                path for path in candidates
                if Path(str(path) + ".ots").is_file()
                and Path(str(path) + ".ots").stat().st_size > 0
            ]
        elif require_unstamped:
            candidates = [
                path for path in candidates
                if not Path(str(path) + ".ots").exists()
                and not _has_terminal_control_characters(path)
            ]
        if candidates:
            return max(candidates, key=lambda path: path.stat().st_mtime)
        if require_proof or require_unstamped:
            return None
    base = directory / "Genesis-HashPaper.md"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = directory / f"Genesis-HashPaper-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def _default_package_path() -> Path:
    directory = _data_dir() / "hashpaper" / "packages"
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / "Genesis-HashPaper-package.json"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = directory / f"Genesis-HashPaper-package-{index}.json"
        if not candidate.exists():
            return candidate
        index += 1


def _default_publication_report_path() -> Path:
    directory = _data_dir() / "hashpaper" / "records"
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / "Genesis-HashPaper-publication.json"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = directory / f"Genesis-HashPaper-publication-{index}.json"
        if not candidate.exists():
            return candidate
        index += 1


def _same_path(first: Path, second: Path) -> bool:
    return _expanded_path(first).resolve() == _expanded_path(second).resolve()


def _read_json_object(path: Path, description: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{description} JSON must contain an object.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hashpaper", description="HashPaper for Node Core OS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a local original text/Markdown document")
    create.add_argument("--output", type=Path, help="Optional output path; defaults to the next available Genesis HashPaper document path")
    create.add_argument("--title", required=True, help="Document title")
    create.add_argument("--text", required=True, help="Document body text")

    package = subparsers.add_parser("package", help="Build a transparent JSON package from an existing original")
    package.add_argument("--input", type=Path, help="Optional original document path; defaults to the newest local HashPaper text document")
    package.add_argument("--output", type=Path, help="Optional package output path; defaults to a new local package path")
    identity_group = package.add_mutually_exclusive_group()
    identity_group.add_argument("--identity-json", type=Path, help="Optional local identity profile JSON")
    identity_group.add_argument("--use-node-profile", action="store_true", help="Use the saved Node Core OS profile and current Kubo Peer ID after explicit confirmation")
    package.add_argument("--node-id", help="Actual technical node ID, if known; not used with --use-node-profile")
    package.add_argument("--ots-json", type=Path, help="Optional report produced by an actual OpenTimestamps command")

    for name, help_text in (
        ("stamp", "Submit the exact original document bytes to the official OpenTimestamps client"),
        ("check", "Check/verify an existing OpenTimestamps proof"),
        ("upgrade", "Ask the official client to upgrade a pending proof"),
        ("proof-info", "Show original hash, .ots fingerprint, and timestamp status"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--input", type=Path, help="Optional original document path; defaults to the newest local HashPaper text document")
        command.add_argument("--report", type=Path, help="Optional JSON report output path")

    publish = subparsers.add_parser("publish", help="Publish a transparent package through Node Core Kubo/IPFS after explicit confirmation")
    publish.add_argument("--input", type=Path, help="Optional package path; defaults to the newest local HashPaper package")
    publish.add_argument("--report", type=Path, help="Optional new JSON receipt path; existing reports are never overwritten")

    return parser


def _authorize_identity_session() -> bool:
    """Require explicit identity-data consent each time the app is opened."""
    global _SESSION_IDENTITY, _SESSION_PEER_ID
    _SESSION_IDENTITY = None
    _SESSION_PEER_ID = None
    print("\nIDENTITY DATA USE — REQUIRED TO ENTER HASHPAPER")
    print("HashPaper will read your saved Node Core OS identity profile and live Kubo Peer ID.")
    print("After acceptance, every new Markdown original will embed identity fields and the node identifier.")
    print("These fields are plaintext. OpenTimestamps timestamps the document hash, not the full text.")
    print("Publishing an IPFS copy makes the copy and embedded identity readable to third parties.")
    print("Consent is requested every time HashPaper opens and is not saved as permanent consent.")
    try:
        answer = input('Type "ACCEPT IDENTITY DATA USE" to continue, or anything else to exit: ').strip()
    except (EOFError, KeyboardInterrupt):
        return False
    if answer != "ACCEPT IDENTITY DATA USE":
        print("Access denied: identity-data use was not accepted.")
        return False
    try:
        from node_core.runtime import NodeRuntime
        runtime = NodeRuntime()
        runtime.boot()
        profile, peer_id = load_identity_and_peer_id(runtime)
        _SESSION_IDENTITY = associate_identity_with_peer(runtime, profile, peer_id)
        _SESSION_PEER_ID = peer_id
    except Exception as exc:
        print(f"HashPaper cannot open without the accepted identity and a live node identifier: {exc}", file=sys.stderr)
        return False
    for directory in (_documents_dir(), _ipfs_dir(), _records_dir(), _hashpaper_dir() / "packages"):
        directory.mkdir(parents=True, exist_ok=True)
    print(f"Identity data use accepted for this session. Application directory: {_hashpaper_dir()}")
    return True


def _read_multiline_body() -> str | None:
    """Enter creates a new line; Ctrl-D finishes; ESC cancels."""
    if not sys.stdin.isatty():
        try:
            value = input("Document body text (one line; type CANCEL to abort): ")
        except (EOFError, KeyboardInterrupt):
            return None
        return None if value.strip().lower() in {"cancel", "q", "quit"} else value
    print("Document body text (Enter adds a line; Ctrl-D finishes; ESC cancels):")
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    chars: list[str] = []
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                print("\nText input cancelled.")
                return None
            if ch == "\x04":
                print()
                return "".join(chars).rstrip("\n")
            if ch in ("\r", "\n"):
                chars.append("\n")
                sys.stdout.write("\r\n")
            elif ch in ("\x7f", "\b"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
            else:
                chars.append(ch)
                sys.stdout.write(ch)
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def _document_history() -> list[Path]:
    directory = _documents_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt", ".markdown"}],
        key=lambda p: (p.stat().st_mtime_ns, p.name),
    )


def _select_document_history(*, require_proof: bool = False, require_unstamped: bool = False, page_size: int = 10) -> Path | None:
    docs = _document_history()
    if require_proof:
        docs = [p for p in docs if Path(str(p) + ".ots").is_file() and Path(str(p) + ".ots").stat().st_size > 0]
    elif require_unstamped:
        docs = [p for p in docs if not Path(str(p) + ".ots").exists() and not _has_terminal_control_characters(p)]
    if not docs:
        print("No matching documents in HashPaper history.")
        return None
    page = 0
    while True:
        start = page * page_size
        current = docs[start:start + page_size]
        print(f"\nDocument history — page {page + 1}/{(len(docs) + page_size - 1) // page_size}")
        for number, path in enumerate(current, 1):
            proof = Path(str(path) + ".ots")
            has_proof = proof.is_file() and proof.stat().st_size > 0
            print(f"{number}. {path.name} | OTS: {'PRESENT' if has_proof else 'NOT PRESENT'} | {path.stat().st_size} bytes")
        print("N. Next page | P. Previous page | 0. Cancel")
        choice = input("Select document number: ").strip().lower()
        if choice == "0":
            return None
        if choice == "n" and start + page_size < len(docs):
            page += 1
            continue
        if choice == "p" and page > 0:
            page -= 1
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(current):
            return current[int(choice) - 1]
        print("Choose a listed number, N, P, or 0.")


def _publish_document_copy(source: Path) -> dict:
    """Create a separate OTS-enriched Markdown copy, publish, pin, and save gateway receipt."""
    from datetime import datetime, timezone
    from node_core.runtime import NodeRuntime
    from .publication import HashPaperPublisher

    source = source.resolve()
    raw = source.read_bytes()
    original_text = raw.decode("utf-8")
    proof = Path(str(source) + ".ots")
    proof_exists = proof.is_file() and proof.stat().st_size > 0
    proof_hash = hashlib.sha256(proof.read_bytes()).hexdigest() if proof_exists else None
    ots_status = "NOT_SUBMITTED"
    if proof_exists:
        try:
            ots_status = OpenTimestampsClient().check(source).status
        except TimestampError as exc:
            ots_status = f"CHECK_ERROR: {exc}"
    copy_text = (
        original_text.rstrip() + "\n\n---\n"
        "## HashPaper publication evidence\n"
        f"- Original filename: {source.name}\n"
        f"- Original SHA-256: {hashlib.sha256(raw).hexdigest()}\n"
        f"- OpenTimestamps proof file: {proof.name if proof_exists else 'NOT PRESENT'}\n"
        f"- OpenTimestamps proof SHA-256: {proof_hash or 'NOT AVAILABLE'}\n"
        f"- OpenTimestamps status at copy creation: {ots_status}\n"
        f"- Identity-data consent: ACCEPTED FOR THIS SESSION\n"
        f"- Node Peer ID: {_SESSION_PEER_ID}\n"
    )
    output_dir = _ipfs_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}-ipfs.md"
    index = 2
    while target.exists():
        target = output_dir / f"{source.stem}-ipfs-{index}.md"
        index += 1
    metadata = write_original(target, copy_text)
    runtime = NodeRuntime()
    runtime.boot()
    result = HashPaperPublisher(runtime).publish_package(target, confirmed_publication=True)
    gateways = [
        f"https://ipfs.io/ipfs/{result.cid}",
        f"https://dweb.link/ipfs/{result.cid}",
        f"https://w3s.link/ipfs/{result.cid}",
        f"https://gateway.pinata.cloud/ipfs/{result.cid}",
    ]
    receipt = {
        "application": "HashPaper for Node Core OS",
        "operation": "publish-document-copy",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_path": str(source),
        "published_copy_path": str(target.resolve()),
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "published_copy_sha256": metadata["sha256"],
        "proof_exists": proof_exists,
        "proof_file": str(proof.resolve()) if proof_exists else None,
        "proof_sha256": proof_hash,
        "opentimestamps_status": ots_status,
        "cid": result.cid,
        "pinned": result.pinned,
        "content_verified": result.content_verified,
        "gateways": gateways,
    }
    record_path = _records_dir() / f"{target.stem}-{result.cid}.json"
    write_package(record_path, receipt)
    return receipt


def _show_ipfs_history() -> None:
    records = sorted(_records_dir().glob("*.json"), key=lambda p: p.stat().st_mtime_ns) if _records_dir().is_dir() else []
    for path in records:
        item = _read_json_object(path, "IPFS publication receipt")
        if item.get("operation") != "publish-document-copy":
            continue
        print(f"\n{item.get('original_path')}\nCID: {item.get('cid')} | pinned={item.get('pinned')}")
        for gateway in item.get("gateways", []):
            print(f"  {gateway}")


def run_interactive_menu() -> int:
    """Require identity-data consent, then show HashPaper menu."""
    if not _authorize_identity_session():
        return 3
    actions = {
        "1": ("create", "Create original document"),
        "2": ("stamp", "Send selected document to OpenTimestamps"),
        "3": ("check", "Check an OpenTimestamps proof"),
        "4": ("upgrade", "Upgrade an OpenTimestamps proof"),
        "5": ("send-ipfs", "Create a timestamp-enriched copy and publish it to IPFS"),
        "6": ("ipfs-history", "Show IPFS publication history and gateways"),
        "7": ("proof-info", "Show .ots hashes and processing status"),
        "8": ("package", "Build a transparent JSON package (advanced)"),
        "9": ("publish", "Publish an existing transparent JSON package (advanced)"),
    }
    while True:
        print("\nHashPaper for Node Core OS\n")
        print("1. Create original document")
        print("2. Send selected document to OpenTimestamps")
        print("3. Check an OpenTimestamps proof")
        print("4. Upgrade an OpenTimestamps proof")
        print("5. Send selected document copy to IPFS (pin and show gateways)")
        print("6. IPFS publication history and gateways")
        print("7. Show .ots hashes and processing status")
        print("8. Build transparent JSON package (advanced)")
        print("9. Publish existing transparent package (advanced)")
        print("0. Exit")
        try:
            choice = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHashPaper closed.")
            return 0
        if choice == "0":
            return 0
        if choice not in actions:
            print("Choose an available option.")
            continue
        command, description = actions[choice]
        print(f"\n{description}\n")
        try:
            if command == "create":
                title = input("Document title: ").strip()
                if not title or title.lower() in {"0", "q", "quit", "cancel"}:
                    print("Document creation cancelled.")
                    continue
                if any(ord(character) < 32 and character not in "\t" for character in title):
                    print("Document creation cancelled: title contains terminal control characters.")
                    continue
                body = _read_multiline_body()
                if body is None or not body.strip():
                    print("Document creation cancelled: body is empty or input was cancelled.")
                    continue
                if any(ord(character) < 32 and character not in "\t\n\r" for character in body):
                    print("Document creation cancelled: body contains terminal control characters.")
                    continue
                confirmation = input("Type 1 to CREATE this document, or 0 to cancel: ").strip()
                if confirmation != "1":
                    print("Document creation cancelled.")
                    continue
                if _SESSION_IDENTITY is None or _SESSION_PEER_ID is None:
                    print("Identity session is unavailable. Exiting for safety.")
                    return 3
                arguments = ["create", "--title", title, "--text", body]
            elif command in {"stamp", "check", "upgrade", "proof-info"}:
                source = _select_document_history(require_proof=command in {"check", "upgrade"})
                if source is None:
                    continue
                if command == "stamp" and Path(str(source) + ".ots").exists():
                    print("This document already has an .ots file; select an unstamped original.")
                    continue
                print(f"Selected document: {source.name}")
                arguments = [command, "--input", str(source)]
            elif command == "send-ipfs":
                source = _select_document_history()
                if source is None:
                    continue
                proof = Path(str(source) + ".ots")
                print(f"Selected document: {source.name}")
                print(f"OpenTimestamps proof: {'PRESENT' if proof.is_file() and proof.stat().st_size else 'NOT PRESENT'}")
                print("A separate Markdown copy with timestamp indicators will be created and published.")
                if input('Type "PUBLISH" to publish this copy publicly: ').strip() != "PUBLISH":
                    print("IPFS publication cancelled.")
                    continue
                receipt = _publish_document_copy(source)
                print(json.dumps(receipt, ensure_ascii=False, indent=2))
                print("Public gateway links (availability depends on each gateway):")
                for gateway in receipt["gateways"]:
                    print(gateway)
                status = 0
            elif command == "ipfs-history":
                _show_ipfs_history()
                status = 0
            elif command == "package":
                source = _select_document_history()
                if source is None:
                    continue
                output = _default_package_path()
                arguments = ["package", "--input", str(source), "--output", str(output)]
                if input("Include identity and Peer ID again in this advanced JSON package? [y/N]: ").strip().lower() in {"y", "yes"}:
                    arguments.append("--use-node-profile")
            else:
                packages_dir = _hashpaper_dir() / "packages"
                packages = sorted(packages_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if packages_dir.is_dir() else []
                if not packages:
                    print("No local HashPaper package found. Build one with option 8 first.")
                    continue
                source = packages[0]
                arguments = ["publish", "--input", str(source), "--report", str(_default_publication_report_path())]
            if command not in {"send-ipfs", "ipfs-history"}:
                status = main(arguments)
            if status:
                print(f"Command finished with status {status}.")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
        except (OSError, ValueError, RuntimeError, TimestampError, PublicationError, IdentityIntegrationError) as exc:
            print(f"HashPaper error: {exc}", file=sys.stderr)
        try:
            input("\nPress Enter to return to HashPaper menu...")
        except (EOFError, KeyboardInterrupt):
            return 0

def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        return run_interactive_menu()
    args = build_parser().parse_args(argv)
    try:
        # Resolve paths consistently, including environment variables like $HOME.
        if getattr(args, "input", None) is not None:
            args.input = _expanded_path(args.input)
        if getattr(args, "output", None) is not None:
            args.output = _expanded_path(args.output)
        if getattr(args, "report", None) is not None:
            args.report = _expanded_path(args.report)
        if getattr(args, "ots_json", None) is not None:
            args.ots_json = _expanded_path(args.ots_json)

        if args.command == "create":
            if args.output is None:
                import re
                slug = re.sub(r"[^A-Za-z0-9_-]+", "-", args.title.strip()).strip("-_") or "HashPaper-document"
                candidate = _documents_dir() / f"{slug}.md"
                index = 2
                while candidate.exists() or Path(str(candidate) + ".ots").exists():
                    candidate = _documents_dir() / f"{slug}-{index}.md"
                    index += 1
                args.output = candidate
            if _SESSION_IDENTITY is not None and _SESSION_PEER_ID is not None:
                identity_json = json.dumps(_SESSION_IDENTITY, ensure_ascii=False, indent=2)
                document_text = (
                    f"# {args.title}\n\n{args.text.rstrip()}\n\n"
                    "## Node Core OS Identity Association\n"
                    "Identity fields below were embedded after explicit consent to use identity data.\n"
                    "This is a declared profile, not independent identity verification.\n\n"
                    "~~~json\n" + identity_json + "\n~~~\n\n"
                    f"Node Core OS Peer ID: {_SESSION_PEER_ID}\n"
                )
            else:
                document_text = f"# {args.title}\n\n{args.text}\n"
            metadata = write_original(args.output, document_text)
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
            print(f"Local original created: {args.output.resolve()}")
            print(f"SHA-256: {metadata['sha256']}")
            print(f"Size: {metadata['size_bytes']} bytes")
            print("Identity embedded: " + ("YES" if _SESSION_IDENTITY is not None else "NO (direct CLI mode)"))
            print("Timestamping and IPFS publication are separate steps.")
            return 0

        if args.command == "publish":
            if args.input is None:
                packages_dir = _data_dir() / "hashpaper" / "packages"
                packages = sorted(packages_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if packages_dir.is_dir() else []
                if not packages:
                    raise ValueError("No local HashPaper package found. Build a package first.")
                args.input = packages[0]
            if args.report is None:
                args.report = _default_publication_report_path()
            package_path = args.input
            if not package_path.is_file():
                raise ValueError(f"Package file does not exist: {package_path}")
            package_value = _read_json_object(package_path, "HashPaper package")
            document = package_value.get("document")
            if not isinstance(document, dict) or not isinstance(document.get("original_text"), str):
                raise ValueError("Refusing publication: package must include the complete original document text.")
            original_text = document["original_text"]
            original_bytes = original_text.encode("utf-8")
            if any(ord(character) < 32 and character not in "\t\n\r" for character in original_text):
                raise ValueError("Refusing publication: original text contains terminal control characters.")
            if (
                document.get("hash_algorithm") != "sha256"
                or document.get("sha256") != hashlib.sha256(original_bytes).hexdigest()
                or document.get("size_bytes") != len(original_bytes)
            ):
                raise ValueError("Refusing publication: document size or SHA-256 does not match the exact original text.")
            if args.report and _same_path(args.report, package_path):
                raise ValueError("Publication receipt must be a separate file from the package being published.")
            if args.report and args.report.exists():
                raise FileExistsError(f"Publication report already exists; choose another path: {args.report}")

            print("PUBLIC DISCLOSURE WARNING")
            print("The following complete package will be published through IPFS and may be readable by third parties.")
            print("Encryption is not implemented. The package includes the complete original text and any identity fields present.")
            print("Review the exact package below. No network operation occurs until you type PUBLISH.")
            print(json.dumps(package_value, ensure_ascii=False, indent=2))
            confirmation = input("Type PUBLISH to publish this exact package, or anything else to cancel: ").strip()
            if confirmation != "PUBLISH":
                print("Publication cancelled. No content was sent to Kubo by HashPaper.")
                return 3

            from node_core.runtime import NodeRuntime
            from .publication import HashPaperPublisher

            runtime = NodeRuntime()
            runtime.boot()
            result = HashPaperPublisher(runtime).publish_package(
                package_path,
                confirmed_publication=True,
            )
            receipt = result.to_dict()
            receipt["application"] = "HashPaper for Node Core OS"
            receipt["package_path"] = str(package_path.resolve())
            receipt["publication_status"] = "PUBLISHED_AND_RETRIEVED"
            if args.report:
                write_package(args.report, receipt)
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            print("Publication succeeded: CID retrieval matched the local bytes and pin state was confirmed.")
            print("The CID is recorded in this separate receipt because embedding a file's own CID in itself would change the content and CID.")
            return 0

        if args.command in {"stamp", "check", "upgrade", "proof-info"}:
            if args.input is None:
                if args.command == "stamp":
                    args.input = _default_document_path(require_unstamped=True)
                elif args.command in {"check", "upgrade"}:
                    args.input = _default_document_path(require_proof=True)
                else:
                    args.input = _default_document_path()
            if args.input is None:
                if args.command == "stamp":
                    raise ValueError("No unstamped HashPaper original found. Create a new original first or provide --input.")
                raise ValueError("No non-empty OpenTimestamps .ots proof found. Submit an original first or provide --input.")
            if not args.input.is_file():
                raise ValueError(f"No local original document found: {args.input}. Create one with HashPaper option 1 first.")
            if args.report:
                proof_path = Path(str(args.input.expanduser()) + ".ots")
                if _same_path(args.report, args.input) or _same_path(args.report, proof_path):
                    raise ValueError("OpenTimestamps report must not overwrite the original document or its .ots proof.")
                if args.report.expanduser().exists():
                    raise FileExistsError(
                        f"OpenTimestamps report already exists; choose a new report path: {args.report}"
                    )
            client = OpenTimestampsClient()
            if args.command == "proof-info":
                original = args.input.expanduser()
                proof = Path(str(original) + ".ots")
                if not original.is_file():
                    raise ValueError(f"Original document does not exist: {original}")
                original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
                proof_exists = proof.is_file() and proof.stat().st_size > 0
                if proof_exists:
                    proof_hash = hashlib.sha256(proof.read_bytes()).hexdigest()
                    result = client.check(original)
                    status, verification = result.status, result.proof_verification
                    block_height, return_code = result.bitcoin_block_height, result.return_code
                    stdout, stderr = result.stdout, result.stderr
                    calendar_urls = getattr(result, "calendar_urls", ())
                    bitcoin_transaction_ids = getattr(result, "bitcoin_transaction_ids", ())
                    previous_proof_hash = getattr(result, "previous_proof_sha256", None)
                else:
                    proof_hash = None
                    status, verification = "NOT_SUBMITTED", "NOT_CHECKED"
                    block_height, return_code, stdout, stderr = None, None, "", ""
                    calendar_urls = ()
                    bitcoin_transaction_ids = ()
                    previous_proof_hash = None
                report = {
                    "application": "HashPaper for Node Core OS",
                    "operation": "proof-info",
                    "original_file": str(original.resolve()),
                    "original_sha256": original_hash,
                    "proof_file": str(proof.resolve()),
                    "proof_exists": proof_exists,
                    "proof_file_sha256": proof_hash,
                    "proof_sha256": proof_hash,
                    "previous_proof_sha256": previous_proof_hash,
                    "calendar_urls": calendar_urls,
                    "bitcoin_transaction_ids": bitcoin_transaction_ids,
                    "proof_fingerprint_note": "SHA-256 fingerprint of the local .ots file; not an official OpenTimestamps-issued identifier.",
                    "status": status,
                    "proof_verification": verification,
                    "bitcoin_block_height": block_height,
                    "verification_return_code": return_code,
                    "verification_stdout": stdout,
                    "verification_stderr": stderr,
                }
                if args.report:
                    if _same_path(args.report, original) or _same_path(args.report, proof):
                        raise ValueError("Proof-info report must not overwrite the original document or .ots proof.")
                    if args.report.expanduser().exists():
                        raise FileExistsError(f"Proof-info report already exists; choose another path: {args.report}")
                    write_package(args.report, report)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                if not proof_exists:
                    print("No .ots proof exists for this original. Status: NOT_SUBMITTED.")
                elif status == "WAITING_FOR_BITCOIN":
                    print("Timestamp proof exists and is processing; no Bitcoin attestation is verified yet.")
                elif status == "VERIFIED":
                    print("OpenTimestamps verified the proof against the original document.")
                else:
                    print(f"Proof status is {status}; do not treat it as verified.")
                return 0 if status not in {"NETWORK_ERROR", "PROOF_ERROR"} else 2

            if args.command == "stamp":
                result = client.stamp(args.input)
            else:
                result = client.check(args.input, upgrade=args.command == "upgrade")
            report = result.to_dict()
            if args.report:
                write_package(args.report, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print("\nHashPaper evidence identifiers")
            print(f"Document SHA-256: {result.original_sha256 or 'NOT AVAILABLE'}")
            print(f"OpenTimestamps proof SHA-256: {result.proof_sha256 or 'NOT AVAILABLE'}")
            print(f"OpenTimestamps status: {result.status}")
            print(f"Bitcoin verification: {result.proof_verification}")
            if result.calendar_urls:
                print("Calendar URLs reported by the official client:")
                for calendar_url in result.calendar_urls:
                    print(f"  {calendar_url}")
            if result.bitcoin_transaction_ids:
                print("Bitcoin transaction IDs explicitly reported by the official client:")
                for transaction_id in result.bitcoin_transaction_ids:
                    print(f"  {transaction_id}")
            if args.command == "stamp":
                print("Timestamp submitted. This does not mean a Bitcoin attestation is already verified.")
            elif result.status == "VERIFIED":
                print("OpenTimestamps verification succeeded for the original document.")
            elif result.status == "WAITING_FOR_BITCOIN":
                print("The timestamp is pending Bitcoin confirmation; it is not yet verified.")
            elif result.status == "ANCHOR_AVAILABLE":
                print("Upgrade reported a completed timestamp. Run 'check' to verify against the original document.")
            else:
                print(f"OpenTimestamps result status: {result.status}")
            return 0 if result.status not in {"NETWORK_ERROR", "PROOF_ERROR"} else 2

        if args.input is None:
            args.input = _default_document_path()
        if not args.input.is_file():
            raise ValueError(f"No local original document found: {args.input}. Create one with HashPaper option 1 first.")
        if args.output is None:
            args.output = _default_package_path()
        if args.output.resolve() == args.input.resolve():
            raise ValueError("Package output must be a different file from the immutable original document.")
        if args.use_node_profile and args.node_id:
            raise ValueError("--node-id cannot be combined with --use-node-profile; HashPaper reads the actual Kubo Peer ID.")
        if args.output.expanduser().exists():
            raise FileExistsError(f"Package output already exists; create a new versioned filename: {args.output}")
        identity = _read_json_object(args.identity_json, "Identity profile") if args.identity_json else None
        node_id = args.node_id
        if args.use_node_profile:
            from node_core.runtime import NodeRuntime

            runtime = NodeRuntime()
            identity, peer_id = load_identity_and_peer_id(runtime)
            original_text = args.input.expanduser().read_text(encoding="utf-8")
            print("IDENTITY AND NODE ASSOCIATION REVIEW")
            print("The following full original text and identity fields will be included in the local package.")
            print("No encryption is implemented. Nothing is published by this command.")
            print("Original document text:")
            print(original_text)
            print("Identity profile fields:")
            print(json.dumps(identity, ensure_ascii=False, indent=2))
            print(f"Current Kubo Peer ID: {peer_id}")
            print(f"Previously associated node ID: {identity.get('node_id')}")
            confirmation = input("Type INCLUDE IDENTITY AND NODE to confirm local association and include all shown fields: ").strip()
            if confirmation != "INCLUDE IDENTITY AND NODE":
                print("Identity inclusion cancelled. No package was created and no association was changed.")
                return 3
            identity = associate_identity_with_peer(runtime, identity, peer_id)
            node_id = peer_id
        ots_metadata = _read_json_object(args.ots_json, "OpenTimestamps report") if args.ots_json else None
        trusted_verified_result = False
        if ots_metadata and ots_metadata.get("status") == "VERIFIED":
            # A JSON report can be edited. Never accept its VERIFIED claim without
            # running the official client against the current original and .ots.
            verification_result = OpenTimestampsClient().check(args.input)
            if verification_result.status != "VERIFIED" or verification_result.proof_verification != "SUCCESS":
                raise ValueError(
                    "The supplied report claims VERIFIED, but the official OpenTimestamps client "
                    "did not verify the current original and proof."
                )
            ots_metadata = verification_result.to_dict()
            trusted_verified_result = True
        package = build_transparent_package(
            original_path=args.input,
            identity_profile=identity,
            node_id=node_id,
            ots_metadata=ots_metadata,
            trusted_verified_result=trusted_verified_result,
        )
        write_package(args.output, package)
        print(f"Transparent package written locally: {args.output}")
        print("WARNING: package includes the complete original text and any supplied identity fields; do not publish real personal data unintentionally.")
        print("To publish this package, run the publish command and review the full public-disclosure warning.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, TimestampError, PublicationError, IdentityIntegrationError) as exc:
        print(f"HashPaper error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
