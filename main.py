#!/usr/bin/env python3
"""Node Core OS entry point."""

from node_core.runtime import NodeRuntime


def main() -> None:
    runtime = NodeRuntime()
    runtime.boot()
    runtime.menu()


if __name__ == "__main__":
    main()
