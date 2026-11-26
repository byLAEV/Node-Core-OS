"""Small text-only, keyboard-driven Node Core OS CLI."""
import argparse
import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("NODE_CORE_OS_HOME", Path.home() / ".local/share/node-core-os"))


def status() -> int:
    print("NODE CORE OS")
    print("Version: 1.6.0")
    print("User data: " + str(APP_DIR))
    print("Initialized: " + ("yes" if APP_DIR.is_dir() else "no"))
    print("Kubo/IPFS: optional; not configured")
    return 0


def initialize() -> int:
    for name in ("storage/local", "storage/ipfs", "config", "apps"):
        (APP_DIR / name).mkdir(parents=True, exist_ok=True)
    print("Initialized user data at: " + str(APP_DIR))
    return 0


def menu() -> int:
    # Deliberately line-oriented: no GUI, images, mouse, touch, or web server.
    while True:
        print("\nNODE CORE OS - USER MENU")
        print("1. Status")
        print("2. Initialize local directories")
        print("0. Exit")
        try:
            choice = input("Select option [0-2]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExit.")
            return 0
        if choice == "0":
            return 0
        if choice == "1":
            status()
        elif choice == "2":
            initialize()
        else:
            print("Invalid option. Enter a number from the menu.")


def main() -> int:
    parser = argparse.ArgumentParser(prog="node-core-os", description="Node Core OS text interface")
    parser.add_argument("command", nargs="?", choices=("menu", "status", "init"), default="menu")
    args = parser.parse_args()
    if args.command == "status":
        return status()
    if args.command == "init":
        return initialize()
    return menu()


if __name__ == "__main__":
    raise SystemExit(main())
