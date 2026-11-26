import unittest
from node_core.security.crypto_health import run_self_test, _version_tuple, CryptoHealthError
class CryptoHealthTests(unittest.TestCase):
    def test_full_runtime_self_test(self):
        result=run_self_test()
        self.assertEqual(result["status"],"success")
        self.assertIn("tamper-rejection",result["checks"])
        self.assertIn("pkcs8-pem-roundtrip",result["checks"])
        self.assertIn("sha256-known-answer",result["checks"])
    def test_invalid_version_fails_closed(self):
        with self.assertRaises(CryptoHealthError): _version_tuple("development")
    def test_version_parser(self):
        self.assertEqual(_version_tuple("42.0.0"),(42,0,0))
if __name__=="__main__": unittest.main()
