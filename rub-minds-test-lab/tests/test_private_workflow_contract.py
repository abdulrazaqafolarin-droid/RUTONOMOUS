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

    def test_private_source_runs_only_on_owner_dispatch_or_scoped_workflow_update(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertRegex(
            self.workflow,
            r"(?ms)^  push:\n    branches: \[main\]\n    paths:\n      - \.github/workflows/private-rub-minds-validation\.yml$",
        )
        self.assertNotRegex(self.workflow, r"(?m)^\s{2}pull_request:")
        self.assertIn("required: false", self.workflow)
        self.assertGreaterEqual(
            self.workflow.count("inputs.source_ref || 'feat/device-frame-ai-runtime-contract'"), 6,
        )
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
        self.assertEqual(self.workflow.count("- name: Verify read-only access to the exact private source branch"), 1)
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

    def test_pull_request_and_push_changes_both_run_the_public_safety_gate(self) -> None:
        lab = (ROOT / ".github" / "workflows" / "rub-minds-test-lab.yml").read_text(encoding="utf-8")
        pull_request = lab.split("  pull_request:", 1)[1].split("  workflow_dispatch:", 1)[0]
        for path in (
            "rub-minds-test-lab/**",
            ".github/workflows/rub-minds-test-lab.yml",
            ".github/workflows/private-rub-minds-validation.yml",
            "scripts/check_public_safety.py",
            "docs/PRIVATE_RUB_MINDS_CI.md",
            "README.md",
        ):
            self.assertIn(path, pull_request)

    def test_selected_backroom_and_group_task_migration_matrix_is_complete(self) -> None:
        migrations = [
            "20261029090000_backroom_wake_queue.sql",
            "20261101221132_mcp_bridge_state.sql",
            "20261102221500_backroom_wake_grant_24h_auto_consent.sql",
            "20261102223000_revoke_backroom_wake_on_mcp_leave.sql",
            "20261104111500_backroom_provider_conversation_identity_queue.sql",
            "20261105090000_mcp_session_agent_credential_digest.sql",
            "20261105110000_backroom_android_native_wake_queue_settlement.sql",
            "20261106143000_backroom_android_native_binding_attestation.sql",
            "20261107090000_backroom_android_native_wake_forwarder.sql",
            "20261107110000_backroom_android_native_wake_attested_settlement.sql",
            "20261101040000_group_task_coordination.sql",
            "20261101164016_group_task_fk_indexes.sql",
            "20261101221147_group_task_review_criterion_evidence.sql",
            "20261101221342_restrict_group_task_review_service_role_execute.sql",
        ]
        for migration in migrations:
            self.assertIn(migration, self.workflow, f"missing migration: {migration}")
        for sql_test in (
            "supabase/tests/backroom_wake_queue.sql",
            "supabase/tests/group_task_coordination.sql",
            "supabase/tests/mcp_bridge_state.sql",
        ):
            self.assertIn(sql_test, self.workflow, f"missing SQL regression test: {sql_test}")

    def test_private_source_job_parses_and_lints_its_workflow_definitions(self) -> None:
        block = self._job("web-and-edge")
        self.assertIn("Parse all private Rub Minds GitHub Actions workflow YAML files", block)
        self.assertIn('require "yaml";', block)
        self.assertIn("Lint private Rub Minds workflows with pinned actionlint", block)
        self.assertIn("private-rub-minds/.github/workflows/*.yml", block)
        self.assertIn("sha256sum --check --status", block)

    def test_android_job_runs_provider_identity_probe_regressions_before_gradle(self) -> None:
        block = self._job("android-companion")
        step = "Run synthetic provider-conversation probe regression tests"
        self.assertIn(step, block)
        self.assertIn("python3 -m unittest discover -s android-companion/scripts", block)
        self.assertLess(block.index(step), block.index("Run Android unit tests, merged-manifest gate and compile-only APK"))

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

    def test_frame_binding_schema_and_real_sdk_scenario_are_wired_after_reset(self) -> None:
        block = self._job("local-supabase-e2e")
        sql_test = "supabase/tests/device_frame_bindings.sql"
        sql_step = "Run host-independent device-frame binding SQL contract and lifecycle tests"
        edge_step = "Start all local Supabase Edge Functions (MCP + Backroom device)"
        sdk_step = "Exercise official MCP SDK, two-AI collaboration, realtime, bridge-state and RLS"
        self.assertIn(sql_test, block)
        self.assertIn(sql_step, block)
        self.assertIn(edge_step, block)
        self.assertIn(sdk_step, block)
        self.assertLess(block.index("supabase db reset --local"), block.index(sql_step))
        self.assertLess(block.index(sql_step), block.index(edge_step))
        self.assertLess(block.index(edge_step), block.index(sdk_step))
        self.assertIn("scripts/local-mcp-sdk-e2e.mjs", block)

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
