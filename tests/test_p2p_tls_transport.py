import socket
import tempfile
import threading
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


class NodeTLSTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.node_a = NodeIdentityStore(root / "a")
        self.node_b = NodeIdentityStore(root / "b")
        self.meta_a = self.node_a.initialize()
        self.meta_b = self.node_b.initialize()
        self.tls_a = NodeTLSTransport(self.node_a)
        self.tls_b = NodeTLSTransport(self.node_b)
        self.cert_a = self.tls_a.ensure_certificate()
        self.cert_b = self.tls_b.ensure_certificate()

    def test_certificate_is_persistent_and_bound_to_node_key(self):
        self.assertEqual(self.tls_a.ensure_certificate(), self.cert_a)
        self.assertEqual(self.tls_b.ensure_certificate(), self.cert_b)
        self.assertTrue(self.tls_a.certificate_path.exists())

    def test_pinned_peer_certificates_have_unique_subjects(self):
        subject_a = x509.load_pem_x509_certificate(self.cert_a).subject.get_attributes_for_oid(
            NameOID.COMMON_NAME
        )[0].value
        subject_b = x509.load_pem_x509_certificate(self.cert_b).subject.get_attributes_for_oid(
            NameOID.COMMON_NAME
        )[0].value
        self.assertNotEqual(subject_a, subject_b)
        self.assertTrue(subject_a.startswith("NCP2P-"))
        self.assertTrue(subject_b.startswith("NCP2P-"))
        self.assertLessEqual(len(subject_a), 64)
        self.assertLessEqual(len(subject_b), 64)

    def test_mutual_tls_13_handshake_and_identity_pinning(self):
        left, right = socket.socketpair()
        results = {}
        errors = []

        def server():
            try:
                with self.tls_b.server_context([self.cert_a]).wrap_socket(
                    right, server_side=True
                ) as tls_socket:
                    results["server_peer"] = self.tls_b.verify_peer_identity(
                        tls_socket, self.meta_a["node_id"]
                    )
                    tls_socket.sendall(b"secure-p2p-test")
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        try:
            with self.tls_a.client_context([self.cert_b]).wrap_socket(
                left, server_hostname=None
            ) as tls_socket:
                results["client_peer"] = self.tls_a.verify_peer_identity(
                    tls_socket, self.meta_b["node_id"]
                )
                results["version"] = tls_socket.version()
                results["payload"] = tls_socket.recv(64)
        finally:
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "TLS server thread did not finish")
        self.assertEqual(errors, [])
        self.assertEqual(results["version"], "TLSv1.3")
        self.assertEqual(results["payload"], b"secure-p2p-test")
        self.assertEqual(results["client_peer"]["node_id"], self.meta_b["node_id"])
        self.assertEqual(results["server_peer"]["node_id"], self.meta_a["node_id"])

    def test_expected_node_id_mismatch_is_rejected(self):
        left, right = socket.socketpair()
        errors = []

        def server():
            try:
                with self.tls_b.server_context([self.cert_a]).wrap_socket(
                    right, server_side=True
                ) as tls_socket:
                    self.tls_b.verify_peer_identity(tls_socket, "sha256:" + "0" * 64)
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        try:
            with self.tls_a.client_context([self.cert_b]).wrap_socket(
                left, server_hostname=None
            ) as tls_socket:
                tls_socket.sendall(b"x")
        except OSError:
            pass
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(any(isinstance(exc, TLSTransportError) for exc in errors))

    def test_untrusted_peer_certificate_is_rejected(self):
        unknown = NodeIdentityStore(Path(self.temp.name) / "unknown")
        unknown.initialize()
        unknown_tls = NodeTLSTransport(unknown)
        unknown_cert = unknown_tls.ensure_certificate()
        left, right = socket.socketpair()
        errors = []

        def server():
            try:
                with self.tls_b.server_context([self.cert_a]).wrap_socket(
                    right, server_side=True
                ):
                    pass
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        try:
            with unknown_tls.client_context([self.cert_b]).wrap_socket(
                left, server_hostname=None
            ):
                pass
        except OSError:
            pass
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
