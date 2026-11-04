"""CLI for the Node Core OS terminal compatibility preflight."""
from __future__ import annotations
import argparse
import json
from .detection import detect_environment
from .policy import evaluate_environment, load_manifest, render_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Detecta y evalúa compatibilidad de terminales Linux con Node Core OS.")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--mode", choices=("diagnose", "install", "update", "runtime"), default="diagnose")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = evaluate_environment(detect_environment(), load_manifest(args.manifest), mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) if args.json else render_report(result))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
