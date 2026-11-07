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
        cls.bootstrap = (ROOT / "update.sh").read_text()
        cls.package_init = (ROOT / "node_core/__init__.py").read_text()
        cls.ci_workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        cls.compatibility_manifest = json.loads((ROOT / "compatibility/manifest.json").read_text())
        cls.compatibility_docs = (ROOT / "docs/TERMINAL-COMPATIBILITY.md").read_text()

    def test_version_matches_contract_and_readme(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(version, self.contract["version"])
        self.assertIn(f"Repository version (`VERSION`):** {version}", self.readme)

    def test_one_canonical_installer_and_legacy_alias(self):
        self.assertEqual(self.contract["canonical_installer"], "update.sh")
        self.assertIn("bash update.sh", self.readme)
        self.assertIn('bash "$SOURCE_DIR/installer/install.sh"', self.bootstrap)
        self.assertIn("installer/update.sh", self.bootstrap)
        alias = (ROOT / self.contract["legacy_installer_alias"]).read_text()
        self.assertIn('exec bash "$INSTALLER_DIR/install.sh" "$@"', alias)

    def test_python_runtime_dependencies_match_requirements(self):
        declared = [line.strip() for line in self.requirements.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(declared, self.contract["python"]["runtime_requirements"])
        # The dependency contract presents the package name and minimum version
        # in separate Markdown table cells; assert the canonical row rather than
        # expecting the pip requirements token to appear verbatim.
        self.assertIn("| `cryptography` | Core runtime | `>=42.0.0` |", self.dependencies)
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

    def test_terminal_compatibility_contract_is_integrated(self):
        self.assertEqual(self.compatibility_manifest["contract_id"], "NCTCL-1")
        self.assertEqual(self.compatibility_manifest["supported_environments"]["gnu_linux"]["architectures"], ["x86_64", "aarch64"])
        self.assertIn("capability_based", self.compatibility_manifest["supported_environments"]["gnu_linux"]["distribution_policy"])
        self.assertIn("node_core_compatibility_preflight", self.install)
        self.assertIn("node_core_compatibility_preflight", self.update)
        self.assertIn("node_core.compatibility", self.compatibility_docs)
        self.assertTrue((ROOT / "schemas/compatibility-manifest.schema.json").is_file())

    def test_1_5_7_version_and_bootstrap_are_coherent(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(version, "1.5.7")
        self.assertEqual(self.contract["version"], "1.5.7")
        self.assertIn('__version__ = "1.5.7"', self.package_init)
        self.assertIn("TERMUX_VERSION", self.bootstrap)
        self.assertIn("tar -tzf", self.bootstrap)

    def test_termux_android_kernel_detection_does_not_reference_undefined_package_variable(self):
        detection = (ROOT / "node_core/compatibility/detection.py").read_text()
        self.assertIn('active_kernel_system == "Linux" and termux_marker', detection)
        self.assertIn('"pkg": bool(lookup("pkg"))', detection)
        self.assertNotIn("termux_pkg", detection)


if __name__ == "__main__":
    unittest.main()
