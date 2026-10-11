"""Initial local-only HashPaper command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .documents import build_transparent_package, write_original, write_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hashpaper", description="HashPaper for Node Core OS (local prototype)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a local original text/Markdown document")
    create.add_argument("--output", required=True, type=Path, help="New output path; existing files are never overwritten")
    create.add_argument("--title", required=True, help="Document title")
    create.add_argument("--text", required=True, help="Document body text")

    package = subparsers.add_parser("package", help="Build a transparent JSON package from an existing original")
    package.add_argument("--input", required=True, type=Path, help="Existing UTF-8 text/Markdown document")
    package.add_argument("--output", required=True, type=Path, help="Output JSON package path")
    package.add_argument("--identity-json", type=Path, help="Optional local identity profile JSON")
    package.add_argument("--node-id", help="Actual technical node ID, if known")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            metadata = write_original(args.output, f"# {args.title}\n\n{args.text}\n")
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
            print("Local original created. OpenTimestamps submission and IPFS publication are not implemented in this milestone.")
            return 0

        identity = None
        if args.identity_json:
            identity = json.loads(args.identity_json.read_text(encoding="utf-8"))
            if not isinstance(identity, dict):
                raise ValueError("Identity profile JSON must contain an object.")
        package = build_transparent_package(
            original_path=args.input,
            identity_profile=identity,
            node_id=args.node_id,
        )
        write_package(args.output, package)
        print(f"Transparent package written locally: {args.output}")
        print("WARNING: package includes the complete original text and any supplied identity fields; do not publish real personal data unintentionally.")
        print("OpenTimestamps submission, verification, and IPFS publication are not implemented in this milestone.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"HashPaper error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
