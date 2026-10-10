#!/usr/bin/env python3
"""Structural checks for the static Node Core OS Web Test Bench."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web-test-bench"
REQUIRED = [
    SITE / "index.html",
    SITE / "assets" / "styles.css",
    SITE / "assets" / "app.js",
    SITE / "README.md",
    SITE / "menus.html",
]
errors = []

for path in REQUIRED:
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")

if not errors:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "assets" / "styles.css").read_text(encoding="utf-8")
    js = (SITE / "assets" / "app.js").read_text(encoding="utf-8")
    readme = (SITE / "README.md").read_text(encoding="utf-8")
    menus = (SITE / "menus.html").read_text(encoding="utf-8")
    pages_workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    e2e_workflow = (ROOT / ".github" / "workflows" / "installer-e2e.yml").read_text(encoding="utf-8")
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for token in ('<html lang="en">', '<meta name="viewport"', 'id="workflow-runs"',
                  'id="run-status"', 'assets/styles.css', 'assets/app.js'):
        if token not in html:
            errors.append(f"index.html is missing required marker: {token}")

    # Detect executable inline script bodies without flagging an external
    # script element whose body is empty, such as <script src="..." defer></script>.
    for script_body in re.findall(r'<script\b[^>]*>(.*?)</script\s*>', html, re.IGNORECASE | re.DOTALL):
        if script_body.strip():
            errors.append("Inline JavaScript is not permitted; use assets/app.js.")
            break

    for target in re.findall(r'(?:src|href)="(\./[^"#?]+)"', html):
        local = (SITE / target.removeprefix("./")).resolve()
        if not local.is_relative_to(SITE.resolve()):
            errors.append(f"Asset escapes site directory: {target}")
        elif not local.is_file():
            errors.append(f"Missing referenced local asset: {target}")

    for token in ("api.github.com/repos/", "Promise.allSettled", "textContent"):
        if token not in js:
            errors.append(f"app.js is missing expected safe/live-results behavior: {token}")

    for token in ("@media(max-width:560px)", "prefers-reduced-motion"):
        if token not in css:
            errors.append(f"styles.css is missing responsive/accessibility rule: {token}")

    if "workflow_dispatch:" not in pages_workflow:
        errors.append("Pages workflow must support manual validation/deployment.")
    if "workflow_dispatch:" not in e2e_workflow:
        errors.append("Installer E2E workflow must support manual runs.")
    if "workflow_dispatch:" not in ci_workflow:
        errors.append("Terminal CI workflow must support manual runs.")
    if "actions/deploy-pages@" not in pages_workflow or "actions/upload-pages-artifact@" not in pages_workflow:
        errors.append("Pages workflow must upload and deploy the static artifact.")

if errors:
    print("Web Test Bench validation: FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Web Test Bench validation: PASSED")
print("Checked required files, HTML markers, local assets, responsive CSS, live API logic, and deployment workflow.")
