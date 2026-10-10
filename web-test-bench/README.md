# Node Core OS Web Test Bench

A static, mobile-friendly public portal for project documentation and recent GitHub Actions status. It does not execute the installer in the browser. Real tests run in GitHub-hosted Ubuntu runners.

## Files

- `index.html`: accessible page structure and direct links to the repository/workflows.
- `assets/styles.css`: responsive styles and reduced-motion support.
- `assets/app.js`: reads public workflow run metadata from the GitHub REST API; no token or secret is embedded in the page.

## Local preview

From the repository root, run:

```bash
python3 -m http.server 8000 --directory web-test-bench
```

Open `http://localhost:8000` in a browser. The live results panel needs network access to the public GitHub API.

## Deployment

The `.github/workflows/pages.yml` workflow validates the site and publishes this directory to GitHub Pages on pushes to `main`. The repository's Pages publishing source must be set to **GitHub Actions** in Settings → Pages. The workflow uses the official Pages actions and minimal deployment permissions.

A deployment can still fail if GitHub Pages is disabled or restricted by repository/organization policy. Confirm Settings → Pages after merging this change.

## Live results and limits

- The dashboard displays recent runs for the terminal CI and installer E2E workflows, linking each row to its GitHub Actions run.
- The GitHub API is public and unauthenticated; rate limits or network restrictions may temporarily prevent loading results. Direct workflow links remain available.
- Timestamps are explicitly displayed in UTC.
- Run state comes from GitHub's API; the site does not claim unrun tests passed.
- This is a status dashboard, not a trigger interface. Start or rerun tests through GitHub Actions, which applies GitHub's own access controls.
- This page intentionally does not display raw logs, secrets, environment variables, or test artifacts.

## Validation

Run `python3 scripts/validate_web_test_bench.py` from the repository root. It checks expected files, key HTML structure, relative asset references, absence of inline scripts, and expected workflow/deployment configuration. It is a structural check, not a full browser test.
