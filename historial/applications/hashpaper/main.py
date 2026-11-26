#!/usr/bin/env python3
"""HashPaper for Node Core OS command-line entry point."""

from pathlib import Path
import sys

# The application lives two levels below the Node Core OS application root.
# Add that root so imports such as node_core.runtime resolve after installation.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from hashpaper.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
