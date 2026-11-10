#!/usr/bin/env python3
"""Tests for Lobby Linux distribution and terminal detection."""
import tempfile, unittest
from pathlib import Path
from host_environment import detect_host_environment, create_installation_snapshot, read_installation_snapshot

class DetectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.osr=Path(self.tmp.name)/"os-release"
  self.osr.write_text('NAME="Ubuntu"\nID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04 LTS"\n')
  self.commands={"bash","python3","tar","sha512sum","mkdir","cp","rm","mktemp","uname","awk","realpath","stat","id","find","grep","sed","nohup","curl","apt-get","pkg"}
  self.kw=dict(os_release_path=self.osr,command_lookup=lambda c:"/usr/bin/"+c if c in self.commands else None,python_version=(3,12,1))
 def tearDown(self): self.tmp.cleanup()
 def test_linux_distro_and_terminal(self):
  x=detect_host_environment({"TERM_PROGRAM":"GNOME Terminal","SHELL":"/bin/bash"},system="Linux",machine="x86_64",**self.kw)
  self.assertEqual(x["profile"],"gnu_linux"); self.assertEqual(x["distribution"]["id"],"ubuntu")
  self.assertEqual(x["terminal"]["emulator"],"GNOME Terminal"); self.assertEqual(x["preflight_status"],"ready")
 def test_termux(self):
  x=detect_host_environment({"TERMUX_VERSION":"0.118","PREFIX":"/data/data/com.termux/files/usr"},system="Linux",machine="aarch64",**self.kw)
  self.assertEqual(x["profile"],"termux"); self.assertEqual(x["package_manager"]["id"],"pkg")
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
