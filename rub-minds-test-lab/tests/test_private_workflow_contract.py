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

    def _job(self, name: str) -> str:
        match = re.search(
            rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z][a-z-]+:|\Z)",
            self.workflow,
        )
        self.assertIsNotNone(match, f"missing workflow job: {name}")
        return match.group(1)

    def test_only_manual_dispatch_can_start_private_source_jobs(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s{2}(push|pull_request):")
        self.assertIn("github.repository == 'abdulrazaqafolarin-droid/RUTONOMOUS'", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn("github.actor == 'abdulrazaqafolarin-droid'", self.workflow)

    def test_single_preflight_gates_all_five_private_test_jobs(self) -> None:
        jobs = [
            "web-and-edge",
            "durable-queue-sql",
            "android-companion",
            "local-supabase-e2e",
            "windows-companion",
        ]
        self.assertEqual(self.workflow.count("- name: Confirm the private read-only token is configured"), 1)
        self.assertEqual(self.workflow.count("- name: Validate selected private source ref"), 1)
        for job in jobs:
            block = self._job(job)
            self.assertIn("needs: validate", block, f"{job} must wait for preflight")
            self.assertIn("if: needs.validate.result == 'success'", block)

    def test_private_source_is_checked_out_only_from_the_private_repo(self) -> None:
        self.assertEqual(
            self.workflow.count("repository: abdulrazaqafolarin-droid/Rub-minds"),
            5,
        )
        self.assertEqual(
            self.workflow.count("token: ${{ secrets.RUB_MINDS_READ_TOKEN }}"),
            5,
        )
        self.assertEqual(self.workflow.count("persist-credentials: false"), 5)
        self.assertEqual(self.workflow.count("path: private-rub-minds"), 5)

    def test_sql_fixture_includes_supabase_auth_and_realtime_contracts(self) -> None:
        self.assertIn("create schema auth;", self.workflow)
        self.assertIn("create or replace function auth.uid()", self.workflow)
        self.assertIn("create publication supabase_realtime;", self.workflow)
        self.assertIn("create table public.backroom_android_commands", self.workflow)
        self.assertIn("backroom_wake_queue.sql", self.workflow)

    def test_local_supabase_job_is_disposable_and_exercises_real_local_e2e(self) -> None:
        block = self._job("local-supabase-e2e")
        for required in (
            "supabase start",
            "supabase db reset --local",
            "scripts/local-human-invite-e2e.mjs",
            "scripts/local-mcp-sdk-e2e.mjs",
            "scripts/local-backroom-device-e2e.mjs",
            "supabase stop --no-backup",
        ):
            self.assertIn(required, block)
        self.assertIn("LOCAL_SUPABASE_URL=", block)
        self.assertIn("http://127.0.0.1:54321", block)
        self.assertNotIn("SUPABASE_ACCESS_TOKEN", block)

    def test_workflow_never_publishes_private_binaries_or_deploys(self) -> None:
        self.assertNotIn("actions/upload-artifact", self.workflow)
        self.assertNotRegex(self.workflow, r"(?i)\b(supabase db push|supabase functions deploy|vercel --prod)\b")
        self.assertIn('SUPABASE_URL: ""', self.workflow)
        self.assertIn('SUPABASE_PUBLISHABLE_KEY: ""', self.workflow)
        self.assertIn("rm -f \"$apk\"", self.workflow)
        self.assertIn("Remove-Item $exe -Force", self.workflow)
        self.assertIn("supabase stop --no-backup", self.workflow)

    def test_raw_private_build_and_sql_logs_are_not_written_to_public_job_output(self) -> None:
        self.assertIn("Detailed output is withheld on this public run", self.workflow)
        self.assertGreaterEqual(self.workflow.count("> \"$RUNNER_TEMP/"), 12)
        self.assertIn("*> \"$env:RUNNER_TEMP", self.workflow)
        self.assertIn("value not displayed", self.workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
