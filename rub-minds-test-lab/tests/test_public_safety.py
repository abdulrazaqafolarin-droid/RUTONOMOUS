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

    def test_common_provider_and_workspace_tokens_are_detected(self) -> None:
        cases = {
            "openai-api-key": "sk-proj-" + "x" * 28,
            "google-api-key": "AIza" + "x" * 35,
            "slack-token": "xoxb-" + "x" * 28,
            "vercel-token": "vercel_" + "x" * 28,
        }
        for expected, fake_token in cases.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, inspect_text(fake_token))

    def test_database_archives_and_credential_files_are_rejected(self) -> None:
        self.assertEqual(forbidden_path(Path("backup/data.sqlite3")), "private-binary-or-key-file")
        self.assertEqual(forbidden_path(Path("release/source.zip")), "private-binary-or-key-file")
        self.assertEqual(forbidden_path(Path(".npmrc")), "environment-file")
        self.assertEqual(forbidden_path(Path("secrets/provider.txt")), "private-material-directory")

    def test_scanner_fails_closed_on_binary_and_oversized_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "app.dat").write_bytes(b"\x00\x01\x02")
            (root / "large.txt").write_bytes(b"x" * 1_000_001)
            (root / "invalid.txt").write_bytes(b"\xff\xfe")
            found = set(scan(root))
            self.assertIn(("app.dat", "binary-file"), found)
            self.assertIn(("large.txt", "oversized-file"), found)
            self.assertIn(("invalid.txt", "non-text-file"), found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
