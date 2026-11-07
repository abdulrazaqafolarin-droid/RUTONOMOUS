from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "private-rub-minds-validation.yml"


class PrivateWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_only_manual_dispatch_can_start_private_source_jobs(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s{2}(push|pull_request):")
        self.assertIn("github.repository == 'abdulrazaqafolarin-droid/RUTONOMOUS'", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn("github.actor == 'abdulrazaqafolarin-droid'", self.workflow)

    def test_one_preflight_gates_all_four_private_test_jobs(self) -> None:
        jobs = ["web-and-edge", "durable-queue-sql", "android-companion", "windows-companion"]
        self.assertEqual(self.workflow.count("- name: Confirm the private read-only token is configured"), 1)
        for job in jobs:
            block = re.search(
                rf"(?ms)^  {re.escape(job)}:\n(.*?)(?=^  [a-z][a-z-]+:|\Z)",
                self.workflow,
            )
            self.assertIsNotNone(block, f"missing workflow job: {job}")
            self.assertIn("needs: validate", block.group(1), f"{job} must wait for preflight")
            self.assertIn("if: needs.validate.result == 'success'", block.group(1))

    def test_private_source_is_checked_out_only_from_the_private_repo(self) -> None:
        self.assertEqual(
            self.workflow.count("repository: abdulrazaqafolarin-droid/Rub-minds"),
            4,
        )
        self.assertEqual(
            self.workflow.count("token: ${{ secrets.RUB_MINDS_READ_TOKEN }}"),
            4,
        )
        self.assertEqual(self.workflow.count("persist-credentials: false"), 4)
        self.assertIn("path: private-rub-minds", self.workflow)

    def test_sql_fixture_includes_supabase_auth_and_realtime_contracts(self) -> None:
        self.assertIn("create schema auth;", self.workflow)
        self.assertIn("create or replace function auth.uid()", self.workflow)
        self.assertIn("create publication supabase_realtime;", self.workflow)
        self.assertIn("create table public.backroom_android_commands", self.workflow)
        self.assertIn("backroom_wake_queue.sql", self.workflow)

    def test_workflow_never_publishes_private_binaries_or_connects_to_production(self) -> None:
        self.assertNotIn("actions/upload-artifact", self.workflow)
        self.assertNotRegex(self.workflow, r"(?i)\b(supabase db push|supabase functions deploy|vercel --prod)\b")
        self.assertIn('SUPABASE_URL: ""', self.workflow)
        self.assertIn('SUPABASE_PUBLISHABLE_KEY: ""', self.workflow)
        self.assertIn("rm -f \"$apk\"", self.workflow)
        self.assertIn("Remove-Item $exe -Force", self.workflow)

    def test_raw_private_build_and_sql_logs_are_not_written_to_public_job_output(self) -> None:
        self.assertIn("Detailed output is withheld on this public run", self.workflow)
        self.assertGreaterEqual(self.workflow.count("> \"$RUNNER_TEMP/"), 8)
        self.assertIn("*> \"$env:RUNNER_TEMP", self.workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
