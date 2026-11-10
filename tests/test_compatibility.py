"""Unit tests for capability-driven terminal compatibility."""
import json
import tempfile
import unittest
from pathlib import Path
from node_core.compatibility.detection import detect_environment, normalize_architecture, parse_os_release
from node_core.compatibility.policy import CompatibilityManifestError, evaluate_environment, load_manifest

BASE_COMMANDS={"bash","python3","tar","sha512sum","mkdir","cp","rm","mktemp","uname","awk","realpath","stat","id","find","grep","sed","nohup","curl","wget","pkg","ipfs","systemctl"}
def lookup_from(names):
    return lambda name: f"/mock/bin/{name}" if name in names else None
def linux_environment(**kwargs):
    params={"env":{"PATH":"/mock/bin","TERM":"xterm-256color","TERM_PROGRAM":"Foot","BASH_VERSION":"5.2"},
        "system":"Linux","machine":"x86_64","python_version":(3,12,4),"terminal_isatty":True,
        "os_release_text":'NAME="Example Linux"\nID=example\nVERSION_ID="1"\n',
        "command_lookup":lookup_from(BASE_COMMANDS),"current_uid":1000,"libc_info":("glibc","2.39")}
    params.update(kwargs)
    return detect_environment(**params)

class TerminalCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load_manifest()
    def test_os_release_parser_never_executes_values(self):
        parsed=parse_os_release('NAME="Test Linux"\nID=test\nVALUE="$(touch /tmp/unsafe)"\n# ignored\n')
        self.assertEqual(parsed["NAME"],"Test Linux")
        self.assertEqual(parsed["VALUE"],"$(touch /tmp/unsafe)")
    def test_architecture_aliases(self):
        self.assertEqual(normalize_architecture("AMD64"),"x86_64")
        self.assertEqual(normalize_architecture("arm64"),"aarch64")
    def test_unknown_distribution_is_capability_based(self):
        result=evaluate_environment(linux_environment(),self.manifest,mode="install")
        self.assertEqual(result["environment"]["os"]["id"],"example")
        self.assertEqual(result["status"],"ready")
    def test_unknown_terminal_emulator_is_not_rejected(self):
        env=linux_environment()
        self.assertEqual(env["terminal"]["program"],"Foot")
        self.assertEqual(evaluate_environment(env,self.manifest)["status"],"ready")
    def test_gnu_linux_x86_and_arm64_profiles(self):
        self.assertEqual(evaluate_environment(linux_environment(),self.manifest)["status"],"ready")
        self.assertEqual(evaluate_environment(linux_environment(machine="aarch64"),self.manifest)["status"],"ready")
    def test_missing_command_requires_preparation(self):
        env=linux_environment(command_lookup=lookup_from(BASE_COMMANDS-{"sha512sum"}))
        result=evaluate_environment(env,self.manifest)
        self.assertEqual(result["status"],"requires_preparation")
        self.assertIn("sha512sum",result["missing_requirements"])
    def test_old_python_requires_preparation(self):
        result=evaluate_environment(linux_environment(python_version=(3,9,19)),self.manifest)
        self.assertEqual(result["status"],"requires_preparation")
        self.assertTrue(any("Python" in item for item in result["missing_requirements"]))
    def test_unsupported_architecture_fails_closed(self):
        result=evaluate_environment(linux_environment(machine="armv7l"),self.manifest)
        self.assertEqual(result["status"],"unsupported")
        self.assertEqual(result["exit_code"],3)
    def test_non_linux_fails_closed(self):
        self.assertEqual(evaluate_environment(linux_environment(system="Darwin"),self.manifest)["status"],"unsupported")
    def test_native_termux_arm64_profile(self):
        names=BASE_COMMANDS|{"pkg","ipfs"}
        env=detect_environment(env={"PATH":"/mock/termux/bin","TERMUX_VERSION":"0.118","PREFIX":"/mock/termux","TERM":"screen-256color"},
            system="Linux",machine="aarch64",python_version=(3,12,4),terminal_isatty=True,os_release_text="",
            command_lookup=lookup_from(names),current_uid=10000,libc_info=("bionic","unknown"))
        self.assertEqual(env["target"]["family"],"termux")
        self.assertEqual(evaluate_environment(env,self.manifest)["status"],"ready")
    def test_termux_markers_without_pkg_are_not_misclassified_as_gnu_linux(self):
        env=detect_environment(env={"PATH":"/mock/termux/bin","TERMUX_VERSION":"0.118","PREFIX":"/mock/termux"},
            system="Linux",machine="aarch64",python_version=(3,12,4),terminal_isatty=True,os_release_text="",
            command_lookup=lookup_from(BASE_COMMANDS-{"pkg"}),current_uid=10000)
        self.assertEqual(env["target"]["family"],"termux")
        result=evaluate_environment(env,self.manifest,mode="prepare")
        self.assertEqual(result["status"],"requires_preparation")
        self.assertIn("pkg",result["missing_requirements"])
    def test_android_termux_arm64_profile(self):
        names=BASE_COMMANDS|{"pkg","ipfs"}
        env=detect_environment(env={"PATH":"/mock/termux/bin","TERMUX_VERSION":"googleplay.2026.10.09","PREFIX":"/mock/termux","TERM":"xterm-256color"},
            system="Android",machine="aarch64",python_version=(3,13,13),terminal_isatty=True,os_release_text="",
            command_lookup=lookup_from(names),current_uid=10292,libc_info=("", ""))
        self.assertEqual(env["os"]["system"],"Android")
        self.assertEqual(env["target"]["family"],"termux")
        self.assertEqual(env["target"]["libc"]["name"],"bionic")
        self.assertEqual(evaluate_environment(env,self.manifest,mode="install")["status"],"ready")
    def test_android_without_termux_markers_remains_unsupported(self):
        env=detect_environment(env={"PATH":"/mock/bin","TERM":"xterm-256color"},
            system="Android",machine="aarch64",python_version=(3,13,13),terminal_isatty=True,
            command_lookup=lookup_from(BASE_COMMANDS|{"ipfs"}),current_uid=10292)
        self.assertEqual(env["target"]["family"],"unsupported")
        result=evaluate_environment(env,self.manifest,mode="install")
        self.assertEqual(result["status"],"unsupported")
        self.assertEqual(result["exit_code"],3)
    def test_android_termux_markers_without_pkg_remain_unsupported(self):
        env=detect_environment(env={"PATH":"/mock/termux/bin","TERMUX_VERSION":"0.118","PREFIX":"/mock/termux"},
            system="Android",machine="aarch64",python_version=(3,13,13),terminal_isatty=True,
            command_lookup=lookup_from(BASE_COMMANDS-{"pkg"}),current_uid=10292)
        self.assertEqual(env["target"]["family"],"unsupported")
    def test_termux_x86_64_is_unsupported(self):
        names=BASE_COMMANDS|{"pkg","ipfs"}
        env=detect_environment(env={"PATH":"/mock/termux/bin","TERMUX_VERSION":"0.118","PREFIX":"/mock/termux"},
            system="Linux",machine="x86_64",python_version=(3,12,4),terminal_isatty=True,os_release_text="",
            command_lookup=lookup_from(names),current_uid=10000)
        self.assertEqual(evaluate_environment(env,self.manifest)["status"],"unsupported")
    def test_term_dumb_disables_ansi_without_blocking(self):
        env=linux_environment(env={"PATH":"/mock/bin","TERM":"dumb"},terminal_isatty=True)
        result=evaluate_environment(env,self.manifest)
        self.assertFalse(env["terminal"]["ansi_color"])
        self.assertEqual(result["status"],"ready")
        self.assertTrue(result["warnings"])
    def test_non_tty_is_a_warning_not_platform_rejection(self):
        result=evaluate_environment(linux_environment(terminal_isatty=False),self.manifest)
        self.assertEqual(result["status"],"ready")
        self.assertFalse(result["interactive_menu_available"])
        self.assertTrue(any("TTY" in item for item in result["warnings"]))
    def test_manifest_loader_rejects_missing_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"manifest.json"
            path.write_text(json.dumps({"manifest_version":1,"minimum_python":"3.10"}))
            with self.assertRaises(CompatibilityManifestError):
                load_manifest(path)

if __name__=="__main__":
    unittest.main()
