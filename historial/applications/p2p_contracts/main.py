#!/usr/bin/env python3
"""Entry point for the initial local P2P Contracts BTC exchange prototype."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from node_core.runtime import NodeRuntime
from applications.p2p_contracts.p2p_contracts.cli import P2PContractsCLI


def main() -> None:
    runtime = NodeRuntime()
    runtime.boot()
    P2PContractsCLI(runtime).run()


if __name__ == "__main__":
    main()
