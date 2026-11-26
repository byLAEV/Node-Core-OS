"""Tests for the Kubo/IPFS publication adapter with a fake Node Core runtime."""

from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hashpaper.publication import HashPaperPublisher, PublicationError


class FakeContent:
    def __init__(self, data, *, wrong_retrieval=False):
        self.data = data
        self.wrong_retrieval = wrong_retrieval
        self.added = False
        self.published = False

    def add(self, source, pin=False):
        self.added = True
        return SimpleNamespace(cid="bafy-test-cid", name=Path(source).name, size=len(self.data))

    def publish(self, cid, pin=True):
        self.published = True


class FakeKubo:
    def __init__(self, data, *, running=True, wrong_retrieval=False, pinned=True):
        self.data = data
        self.running = running
        self.wrong_retrieval = wrong_retrieval
        self.pinned = pinned

    def status(self):
        return SimpleNamespace(running=self.running)

    def cat(self, cid):
        return self.data + (b"changed" if self.wrong_retrieval else b"")

    def pin_list(self):
        return {"bafy-test-cid": {"Type": "recursive"}} if self.pinned else {}


class HashPaperPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "package.json"
        self.data = b'{"application":"HashPaper","document":{"original_text":"synthetic"}}\n'
        self.path.write_bytes(self.data)

    def tearDown(self):
        self.temporary.cleanup()

    def runtime(self, *, running=True, wrong_retrieval=False, pinned=True):
        content = FakeContent(self.data, wrong_retrieval=wrong_retrieval)
        kubo = FakeKubo(self.data, running=running, wrong_retrieval=wrong_retrieval, pinned=pinned)
        return SimpleNamespace(kubo=kubo, content=content)

    def test_requires_explicit_publication_confirmation(self):
        runtime = self.runtime()
        with self.assertRaises(PublicationError):
            HashPaperPublisher(runtime).publish_package(self.path, confirmed_publication=False)
        self.assertFalse(runtime.content.added)

    def test_publishes_only_after_retrieval_and_pin_checks(self):
        runtime = self.runtime()
        result = HashPaperPublisher(runtime).publish_package(self.path, confirmed_publication=True)
        self.assertEqual(result.cid, "bafy-test-cid")
        self.assertTrue(result.content_verified)
        self.assertTrue(result.pinned)
        self.assertTrue(result.published)
        self.assertEqual(result.sha256, __import__("hashlib").sha256(self.data).hexdigest())

    def test_refuses_when_kubo_is_not_running(self):
        with self.assertRaises(PublicationError):
            HashPaperPublisher(self.runtime(running=False)).publish_package(self.path, confirmed_publication=True)

    def test_refuses_when_retrieved_bytes_differ(self):
        runtime = self.runtime(wrong_retrieval=True)
        with self.assertRaises(PublicationError):
            HashPaperPublisher(runtime).publish_package(self.path, confirmed_publication=True)
        self.assertFalse(runtime.content.published)

    def test_refuses_when_pin_is_not_confirmed(self):
        runtime = self.runtime(pinned=False)
        with self.assertRaises(PublicationError):
            HashPaperPublisher(runtime).publish_package(self.path, confirmed_publication=True)


if __name__ == "__main__":
    unittest.main()
