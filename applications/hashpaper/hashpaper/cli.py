"""Initial HashPaper command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .documents import build_transparent_package, write_original, write_package
from .timestamp import OpenTimestampsClient, TimestampError
from .publication import PublicationError
from .identity import IdentityIntegrationError, associate_identity_with_peer, load_identity_and_peer_id


def _same_path(first: Path, second: Path) -> bool:
    return first.expanduser().resolve() == second.expanduser().resolve()


def _read_json_object(path: Path, description: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{description} JSON must contain an object.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hashpaper", description="HashPaper for Node Core OS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a local original text/Markdown document")
    create.add_argument("--output", required=True, type=Path, help="New output path; existing files are never overwritten")
    create.add_argument("--title", required=True, help="Document title")
    create.add_argument("--text", required=True, help="Document body text")

    package = subparsers.add_parser("package", help="Build a transparent JSON package from an existing original")
    package.add_argument("--input", required=True, type=Path, help="Existing UTF-8 text/Markdown document")
    package.add_argument("--output", required=True, type=Path, help="Output JSON package path")
    identity_group = package.add_mutually_exclusive_group()
    identity_group.add_argument("--identity-json", type=Path, help="Optional local identity profile JSON")
    identity_group.add_argument("--use-node-profile", action="store_true", help="Use the saved Node Core OS profile and current Kubo Peer ID after explicit confirmation")
    package.add_argument("--node-id", help="Actual technical node ID, if known; not used with --use-node-profile")
    package.add_argument("--ots-json", type=Path, help="Optional report produced by an actual OpenTimestamps command")

    for name, help_text in (
        ("stamp", "Submit the exact original document bytes to the official OpenTimestamps client"),
        ("check", "Check/verify an existing OpenTimestamps proof"),
        ("upgrade", "Ask the official client to upgrade a pending proof"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--input", required=True, type=Path, help="Original UTF-8 text/Markdown document")
        command.add_argument("--report", type=Path, help="Optional JSON report output path")

    publish = subparsers.add_parser("publish", help="Publish a transparent package through Node Core Kubo/IPFS after explicit confirmation")
    publish.add_argument("--input", required=True, type=Path, help="Transparent JSON package containing the complete original text")
    publish.add_argument("--report", type=Path, help="Optional new JSON receipt path; existing reports are never overwritten")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            metadata = write_original(args.output, f"# {args.title}\n\n{args.text}\n")
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
            print("Local original created. Timestamping and IPFS publication are separate steps.")
            return 0

        if args.command == "publish":
            package_path = args.input.expanduser()
            if not package_path.is_file():
                raise ValueError(f"Package file does not exist: {package_path}")
            package_value = _read_json_object(package_path, "HashPaper package")
            document = package_value.get("document")
            if not isinstance(document, dict) or not isinstance(document.get("original_text"), str):
                raise ValueError("Refusing publication: package must include the complete original document text.")
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

        if args.command in {"stamp", "check", "upgrade"}:
            if args.report:
                proof_path = Path(str(args.input.expanduser()) + ".ots")
                if _same_path(args.report, args.input) or _same_path(args.report, proof_path):
                    raise ValueError("OpenTimestamps report must not overwrite the original document or its .ots proof.")
            client = OpenTimestampsClient()
            if args.command == "stamp":
                result = client.stamp(args.input)
            else:
                result = client.check(args.input, upgrade=args.command == "upgrade")
            report = result.to_dict()
            if args.report:
                write_package(args.report, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
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

        if args.output.expanduser().resolve() == args.input.expanduser().resolve():
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
        package = build_transparent_package(
            original_path=args.input,
            identity_profile=identity,
            node_id=node_id,
            ots_metadata=ots_metadata,
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
