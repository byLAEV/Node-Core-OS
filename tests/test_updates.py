import unittest
from unittest.mock import patch

from node_core.updates import check_for_updates


class UpdateCheckTests(unittest.TestCase):
    def test_version_match_is_up_to_date(self):
        with patch("node_core.updates._read_local_version", return_value="1.0.0"), patch(
            "node_core.updates.urlopen"
        ) as open_url:
            response = open_url.return_value.__enter__.return_value
            response.read.return_value = b"1.0.0\n"
            status = check_for_updates()
        self.assertTrue(status.checked)
        self.assertFalse(status.available)
        self.assertEqual(status.local_version, "1.0.0")
        self.assertEqual(status.remote_version, "1.0.0")

    def test_newer_version_marks_update_available(self):
        with patch("node_core.updates._read_local_version", return_value="1.0.0"), patch(
            "node_core.updates.urlopen"
        ) as open_url:
            response = open_url.return_value.__enter__.return_value
            response.read.return_value = b"1.1.0\n"
            status = check_for_updates()
        self.assertTrue(status.checked)
        self.assertTrue(status.available)
        self.assertEqual(status.remote_version, "1.1.0")

    def test_older_version_does_not_offer_downgrade(self):
        with patch("node_core.updates._read_local_version", return_value="1.2.0"), patch(
            "node_core.updates.urlopen"
        ) as open_url:
            response = open_url.return_value.__enter__.return_value
            response.read.return_value = b"1.1.0\n"
            status = check_for_updates()
        self.assertTrue(status.checked)
        self.assertFalse(status.available)

    def test_network_error_does_not_block_menu(self):
        with patch("node_core.updates._read_local_version", return_value="1.0.0"), patch(
            "node_core.updates.urlopen", side_effect=TimeoutError()
        ):
            status = check_for_updates()
        self.assertFalse(status.checked)
        self.assertFalse(status.available)
        self.assertEqual(status.local_version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
