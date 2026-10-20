#!/usr/bin/env python3
"""Structural checks for the static Node Core OS Web Test Bench."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
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
    SITE / "identity.html",
]
errors = []

class LocalLinkParser(HTMLParser):
    """Collect IDs and href/src attributes for static-site link validation."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag.lower() == "a" and values.get("name"):
            self.ids.add(values["name"])
        for attribute in ("href", "src"):
            if values.get(attribute):
                self.references.append((attribute, values[attribute]))

for path in REQUIRED:
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")

if not errors:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "assets" / "styles.css").read_text(encoding="utf-8")
    js = (SITE / "assets" / "app.js").read_text(encoding="utf-8")
    readme = (SITE / "README.md").read_text(encoding="utf-8")
    menus = (SITE / "menus.html").read_text(encoding="utf-8")
    identity = (SITE / "identity.html").read_text(encoding="utf-8")
    pages_workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    e2e_workflow = (ROOT / ".github" / "workflows" / "installer-e2e.yml").read_text(encoding="utf-8")
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for token in ('<html lang="es">', '<meta name="viewport"', 'id="workflow-runs"',
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

    # Validate relative links, assets, and fragments on every HTML page.
    html_pages = sorted(SITE.rglob("*.html"))
    parsed_pages = {}
    for page in html_pages:
        parser = LocalLinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        parsed_pages[page.resolve()] = parser

    site_root = SITE.resolve()
    for page_path, parser in parsed_pages.items():
        for attribute, raw_target in parser.references:
            parts = urlsplit(raw_target)
            if parts.scheme or parts.netloc or raw_target.startswith("//"):
                continue
            if parts.path:
                target_path = (page_path.parent / unquote(parts.path)).resolve()
                if target_path.is_dir():
                    target_path = (target_path / "index.html").resolve()
                if not target_path.is_relative_to(site_root):
                    errors.append(f"Local {attribute} escapes site directory in {page_path.name}: {raw_target}")
                    continue
                if not target_path.is_file():
                    errors.append(f"Broken local {attribute} in {page_path.name}: {raw_target}")
                    continue
            else:
                target_path = page_path
            if parts.fragment:
                target_parser = parsed_pages.get(target_path.resolve())
                if target_parser is not None and unquote(parts.fragment) not in target_parser.ids:
                    errors.append(f"Broken fragment in {page_path.name}: {raw_target}")

    for token in ("External CID Library", "Read Content by CID", "Remove Reference from History", "does not unpin or delete IPFS content"):
        if token.casefold() not in menus.casefold():
            errors.append(f"menus.html is missing External CID Library documentation: {token}")

    for token in ("api.github.com/repos/", "Promise.allSettled", "textContent"):
        if token not in js:
            errors.append(f"app.js is missing expected safe/live-results behavior: {token}")

    for token in ("@media(max-width:560px)", "prefers-reduced-motion"):
        if token not in css:
            errors.append(f"styles.css is missing responsive/accessibility rule: {token}")

    for token in ('<html lang="en">', 'id="model"', 'id="evidence"', 'id="privacy"', 'id="roadmap"', 'ZKP', 'consensus', 'identity-function-proof-consensus-v1/docs/IDENTITY-PERSONHOOD-AND-SELECTIVE-EVIDENCE.md'):
        if token not in identity:
            errors.append(f"identity.html is missing expected architecture content: {token}")
    for target in re.findall(r'(?:src|href)="(\./[^"#?]+)"', identity):
        local = (SITE / target.removeprefix("./")).resolve()
        if not local.is_relative_to(SITE.resolve()):
            errors.append(f"Identity page asset escapes site directory: {target}")
        elif not local.is_file():
            errors.append(f"Identity page references missing local asset: {target}")

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
print("Checked required files, HTML markers, local links and fragments across all pages, responsive CSS, live API logic, and deployment workflow.")
