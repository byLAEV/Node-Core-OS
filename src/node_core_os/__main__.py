"""Low-memory, keyboard-only user-mode interface."""
import argparse
from pathlib import Path

VERSION = "1.6.1"
DATA_DIR = Path.home() / ".local" / "share" / "node-core-os"

def status():
    print("Node Core OS", VERSION)
    print("Mode: user (no root)")
    print("Data:", DATA_DIR)
    print("Initialized:", "yes" if DATA_DIR.is_dir() else "no")
    print("IPFS/Kubo: optional, not connected")

def initialize():
    for name in ("storage/local", "storage/ipfs", "config", "apps"):
        (DATA_DIR / name).mkdir(parents=True, exist_ok=True)
    print("User storage initialized:", DATA_DIR)

def menu():
    while True:
        print("\nNODE CORE OS")
        print("1. Status")
        print("2. Initialize user storage")
        print("3. Show paths")
        print("0. Exit")
        try:
            choice = input("Option [0-3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExit.")
            return 0
        if choice == "0":
            return 0
        if choice == "1":
            status()
        elif choice == "2":
            initialize()
        elif choice == "3":
            print("Data:", DATA_DIR)
            print("Local:", DATA_DIR / "storage/local")
            print("IPFS:", DATA_DIR / "storage/ipfs")
        else:
            print("Invalid option; enter one of the listed numbers.")

def main():
    parser = argparse.ArgumentParser(prog="node-core-os")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("command", nargs="?", choices=("menu", "status", "init", "paths"), default="menu")
    args = parser.parse_args()
    if args.command == "status": status()
    elif args.command == "init": initialize()
    elif args.command == "paths": print(DATA_DIR)
    else: return menu()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
