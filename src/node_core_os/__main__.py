"""Command-line entry point for Node Core OS."""
import argparse
import json
from pathlib import Path

APP_DIR = Path.home() / ".local" / "share" / "node-core-os"


def main() -> int:
    parser = argparse.ArgumentParser(prog="node-core-os", description="Node Core OS local-first runtime")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show runtime and storage locations")
    sub.add_parser("init", help="Create the local data directory")
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps({
            "name": "Node Core OS",
            "version": "1.6.0",
            "data_dir": str(APP_DIR),
            "initialized": APP_DIR.is_dir(),
            "ipfs": "optional external Kubo service; not configured",
        }, indent=2))
        return 0
    if args.command == "init":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        (APP_DIR / "storage").mkdir(exist_ok=True)
        (APP_DIR / "config").mkdir(exist_ok=True)
        print(f"Initialized local data directory: {APP_DIR}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
