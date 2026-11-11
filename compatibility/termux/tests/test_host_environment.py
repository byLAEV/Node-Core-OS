#!/usr/bin/env python3
"""Tests for Lobby Linux distribution and terminal detection."""
import sys
import tempfile, unittest
from pathlib import Path

LOBBY_DIRECTORY = Path(__file__).resolve().parents[1] / "lobby"
if str(LOBBY_DIRECTORY) not in sys.path:
 sys.path.insert(0, str(LOBBY_DIRECTORY))

from host_environment import detect_host_environment, create_installation_snapshot, read_installation_snapshot

class DetectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.osr=Path(self.tmp.name)/"os-release"
  self.osr.write_text('NAME="Ubuntu"\nID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04 LTS"\n')
  self.commands={"bash","python3","tar","sha512sum","mkdir","cp","rm","mktemp","uname","awk","realpath","stat","id","find","grep","sed","nohup","curl","apt-get","pkg"}
  self.kw=dict(
   os_release_path=self.osr,
   proc_version_path=Path(self.tmp.name)/"missing-proc-version",
   cgroup_path=Path(self.tmp.name)/"missing-cgroup",
   container_marker_paths=(),
   command_lookup=lambda c:"/usr/bin/"+c if c in self.commands else None,
   python_version=(3,12,1),
  )
 def tearDown(self): self.tmp.cleanup()
 def test_linux_distro_and_terminal(self):
  x=detect_host_environment({"TERM_PROGRAM":"GNOME Terminal","SHELL":"/bin/bash"},system="Linux",machine="x86_64",**self.kw)
  self.assertEqual(x["profile"],"gnu_linux"); self.assertEqual(x["distribution"]["id"],"ubuntu")
  self.assertEqual(x["terminal"]["emulator"],"GNOME Terminal"); self.assertEqual(x["preflight_status"],"ready")
 def test_debian_distribution(self):
  self.osr.write_text('NAME="Debian GNU/Linux"\nID=debian\nVERSION_ID="13"\nPRETTY_NAME="Debian GNU/Linux 13"\n')
  x=detect_host_environment({},system="Linux",machine="x86_64",**self.kw)
  self.assertEqual(x["profile"],"gnu_linux")
  self.assertEqual(x["distribution"]["id"],"debian")
  self.assertEqual(x["installer"]["entry_point"],"bash installer/install.sh")
 def test_termux(self):
  x=detect_host_environment({"TERMUX_VERSION":"0.118","PREFIX":"/data/data/com.termux/files/usr"},system="Linux",machine="aarch64",**self.kw)
  self.assertEqual(x["profile"],"termux"); self.assertEqual(x["package_manager"]["id"],"pkg")
  self.assertEqual(x["installer"]["entry_point"],"bash installer/install.sh")
 def test_termux_rejects_non_arm64(self):
  x=detect_host_environment({"TERMUX_VERSION":"0.118","PREFIX":"/data/data/com.termux/files/usr"},system="Linux",machine="x86_64",**self.kw)
  self.assertEqual(x["profile"],"termux")
  self.assertFalse(x["supported_architecture"])
  self.assertEqual(x["preflight_status"],"unsupported")
 def test_container_environment_variable(self):
  x=detect_host_environment({"container":"docker"},system="Linux",machine="x86_64",**self.kw)
  self.assertEqual(x["environment_type"],"linux_container")
  self.assertEqual(x["container"],"docker")
  self.assertTrue(x["profile_supported"])
 def test_container_cgroup_marker(self):
  cgroup=Path(self.tmp.name)/"cgroup"
  cgroup.write_text("0::/docker/0123456789abcdef\n")
  x=detect_host_environment({},system="Linux",machine="x86_64",cgroup_path=cgroup,**{k:v for k,v in self.kw.items() if k!="cgroup_path"})
  self.assertEqual(x["environment_type"],"linux_container")
  self.assertEqual(x["container"],"docker")
 def test_container_marker_paths_have_string_labels(self):
  marker=Path(self.tmp.name)/".dockerenv"; marker.touch()
  x=detect_host_environment({},system="Linux",machine="x86_64",container_marker_paths=((marker,"docker"),),**{k:v for k,v in self.kw.items() if k!="container_marker_paths"})
  self.assertEqual(x["container"],"docker")
  self.assertIsInstance(x["container"],str)
 def test_wsl(self):
  x=detect_host_environment({"WSL_DISTRO_NAME":"Ubuntu"},system="Linux",machine="x86_64",kernel_release="microsoft WSL2",**self.kw)
  self.assertEqual(x["environment_type"],"wsl")
 def test_unsupported_architecture(self):
  x=detect_host_environment({},system="Linux",machine="riscv64",**self.kw)
  self.assertEqual(x["preflight_status"],"unsupported")
 def test_missing_capabilities(self):
  x=detect_host_environment({},system="Linux",machine="x86_64",command_lookup=lambda c:None,python_version=(3,12,1),os_release_path=self.osr)
  self.assertEqual(x["preflight_status"],"requires_preparation")
 def test_snapshot(self):
  path=Path(self.tmp.name)/"snapshot.json"
  snapshot=create_installation_snapshot({"TERMUX_VERSION":"0.118","PREFIX":"/data/data/com.termux/files/usr"})
  import json
  path.write_text(json.dumps(snapshot))
  self.assertEqual(read_installation_snapshot(path)["host"]["profile"],"termux")
 def test_reject_symlink(self):
  real=Path(self.tmp.name)/"real"; real.write_text('{"schema_version":1,"host":{}}')
  link=Path(self.tmp.name)/"link"
  try: link.symlink_to(real)
  except OSError: self.skipTest("symlinks unavailable")
  self.assertIsNone(read_installation_snapshot(link))

if __name__=="__main__": unittest.main(verbosity=2)
