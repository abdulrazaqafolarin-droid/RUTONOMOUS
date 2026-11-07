from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.check_public_safety import forbidden_path, inspect_text


class PublicSafetyScannerTests(unittest.TestCase):
    def test_env_files_are_flagged_but_example_template_is_allowed(self) -> None:
        self.assertEqual(forbidden_path(Path(".env")), "environment-file")
        self.assertEqual(forbidden_path(Path(".env.local")), "environment-file")
        self.assertEqual(forbidden_path(Path(".env.production")), "environment-file")
        self.assertIsNone(forbidden_path(Path(".env.example")))

    def test_private_material_directories_and_signing_files_are_flagged(self) -> None:
        self.assertEqual(
            forbidden_path(Path("credentials/provider.txt")),
            "private-material-directory",
        )
        self.assertEqual(forbidden_path(Path("android/release.jks")), "private-binary-or-key-file")
        self.assertEqual(forbidden_path(Path("certs/upload.key")), "private-binary-or-key-file")
        self.assertEqual(forbidden_path(Path("exports/users.sql.gz")), "database-dump")

    def test_common_secret_shapes_are_detected_without_returning_secret_values(self) -> None:
        findings = inspect_text("ghp_" + "x" * 30)
        self.assertIn("github-token", findings)
        self.assertNotIn("x" * 30, findings)

    def test_private_key_block_is_detected(self) -> None:
        findings = inspect_text("-----BEGIN " + "PRIVATE KEY-----")
        self.assertIn("private-key-block", findings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
