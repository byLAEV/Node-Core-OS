"""Guard the documented repository contract against version/dependency drift."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryCoherenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "docs/REPOSITORY-CONTRACT.json").read_text())
        cls.readme = (ROOT / "README.md").read_text()
        cls.dependencies = (ROOT / "docs/DEPENDENCIES.md").read_text()
        cls.installer_docs = (ROOT / "docs/INSTALLER.md").read_text()
        cls.defaults = (ROOT / "installer/config/defaults").read_text()
        cls.requirements = (ROOT / "requirements.txt").read_text()
        cls.install = (ROOT / "installer/install.sh").read_text()
        cls.verify = (ROOT / "installer/lib/verify.sh").read_text()
        cls.update = (ROOT / "installer/update.sh").read_text()
        cls.ci_workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    def test_version_matches_contract_and_readme(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(version, self.contract["version"])
        self.assertIn(f"Repository version (`VERSION`):** {version}", self.readme)

    def test_one_canonical_installer_and_legacy_alias(self):
        self.assertEqual(self.contract["canonical_installer"], "installer/install.sh")
        self.assertIn("bash installer/install.sh", self.readme)
        alias = (ROOT / self.contract["legacy_installer_alias"]).read_text()
        self.assertIn('exec bash "$INSTALLER_DIR/install.sh" "$@"', alias)

    def test_python_runtime_dependencies_match_requirements(self):
        declared = [line.strip() for line in self.requirements.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(declared, self.contract["python"]["runtime_requirements"])
        self.assertIn("cryptography>=42.0.0", self.dependencies)
        self.assertIn("urllib", self.contract["python"]["http_client"])
        self.assertNotIn("requests", declared)

    def test_kubo_pin_matches_installer_defaults(self):
        expected = self.contract["kubo"]["gnu_linux_pinned"].removeprefix("v")
        self.assertIn(f'NODE_CORE_KUBO_VERSION="${{NODE_CORE_KUBO_VERSION:-{expected}}}"', self.defaults)

    def test_private_runtime_python_is_used_for_verification_and_recovery(self):
        self.assertIn("runtime/node-core-venv/bin/python", self.install)
        self.assertIn('python_environment="$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python"', self.verify)
        self.assertIn('"$python_environment" -m compileall', self.verify)
        self.assertIn('"$python_environment" -m unittest', self.update)

    def test_updater_recovery_obeys_the_installed_release_manifest(self):
        self.assertIn("requirements_declare_cryptography()", self.update)
        self.assertIn('if requirements_declare_cryptography "$requirements_file"; then', self.update)
        self.assertIn('if requirements_declare_cryptography "$NODE_CORE_APP_DIR/requirements.txt"; then', self.update)
        self.assertIn("verify_declared_cryptography", self.update)

    def test_core_ci_uses_node_24_compatible_actions(self):
        self.assertIn("uses: actions/checkout@v5", self.ci_workflow)
        self.assertIn("uses: actions/setup-python@v6", self.ci_workflow)
        self.assertNotIn("actions/checkout@v4", self.ci_workflow)
        self.assertNotIn("actions/setup-python@v5", self.ci_workflow)

    def test_platform_and_crypto_contract_are_documented(self):
        self.assertIn("Termux", self.dependencies)
        self.assertIn("same installer", self.dependencies.lower())
        self.assertIn("cryptography>=42.0.0", self.installer_docs)
        self.assertIn("Python 3.10", self.dependencies)

    def test_crypto_health_is_shared(self):
        self.assertTrue((ROOT / "node_core/security/crypto_health.py").is_file())
        self.assertIn("node_core.security.crypto_health", self.install)
        self.assertIn("node_core.security.crypto_health", self.verify)
        self.assertIn("node_core.security.crypto_health", self.update)
        self.assertIn("--only-binary=:all:", (ROOT / "installer/lib/python.sh").read_text())

    def test_release_tag_snapshot_is_not_misrepresented(self):
        coherence = (ROOT / "docs/REPOSITORY-COHERENCE.md").read_text()
        self.assertIn("41 commits ahead", coherence)
        self.assertIn("Do not claim that tag 1.5.6 contains all changes", coherence)


if __name__ == "__main__":
    unittest.main()
