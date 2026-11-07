from __future__ import annotations

import unittest
from dataclasses import replace

from contract_model.wake_queue import QueueContractError, Request, Scope, WakeQueue


class DurableWakeQueueContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue = WakeQueue()
        self.scope = Scope()
        self.request = Request(
            job_key="a" * 64,
            event_id="event-1",
            prompt_digest="b" * 64,
            scope=self.scope,
        )
        self.enqueued = self.queue.enqueue(self.request, now=100)
        self.job_id = self.enqueued.job_id

    def claim(self, *, now: int = 101):
        jobs = self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=now,
        )
        self.assertEqual(len(jobs), 1)
        return jobs[0]

    def ack(self, job, *, now: int = 102, **overrides):
        args = {
            "job_id": job.job_id,
            "host_id": self.scope.host_id,
            "session_digest": self.scope.session_digest,
            "binding_id": self.scope.binding_id,
            "lease_token": job.lease_token,
            "outcome": "acknowledged",
            "now": now,
        }
        args.update(overrides)
        return self.queue.acknowledge(**args)

    def test_enqueue_creates_one_pending_job(self) -> None:
        self.assertTrue(self.enqueued.created)
        self.assertEqual(self.enqueued.state, "pending")
        self.assertEqual(len(self.queue.jobs_by_id), 1)

    def test_exact_enqueue_replay_returns_existing_job_without_duplicate(self) -> None:
        replay = self.queue.enqueue(self.request, now=110)
        self.assertFalse(replay.created)
        self.assertEqual(replay.job_id, self.job_id)
        self.assertEqual(len(self.queue.jobs_by_id), 1)

    def test_idempotency_key_reuse_with_different_request_is_rejected(self) -> None:
        changed = replace(self.request, event_id="event-2")
        with self.assertRaisesRegex(QueueContractError, "conflicts"):
            self.queue.enqueue(changed, now=110)
        self.assertEqual(len(self.queue.jobs_by_id), 1)

    def test_claim_mints_lease_and_increments_attempt_count(self) -> None:
        job = self.claim()
        self.assertEqual(job.state, "leased")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNotNone(job.lease_token)
        self.assertEqual(job.lease_expires_at, 131)

    def test_claim_rejects_wrong_host_session_or_binding(self) -> None:
        for args in (
            {"host_id": "other-host", "session_digest": self.scope.session_digest, "binding_id": self.scope.binding_id},
            {"host_id": self.scope.host_id, "session_digest": "c" * 64, "binding_id": self.scope.binding_id},
            {"host_id": self.scope.host_id, "session_digest": self.scope.session_digest, "binding_id": "other-binding"},
        ):
            self.assertEqual(self.queue.claim(**args, now=101), [])

    def test_valid_acknowledgement_consumes_the_lease(self) -> None:
        job = self.claim()
        self.assertTrue(self.ack(job))
        self.assertEqual(job.state, "acknowledged")
        self.assertIsNone(job.lease_token)

    def test_acknowledgement_replay_is_not_reported_as_success(self) -> None:
        job = self.claim()
        self.assertTrue(self.ack(job))
        self.assertFalse(self.ack(job))
        self.assertEqual(job.state, "acknowledged")

    def test_wrong_or_stale_lease_token_cannot_acknowledge(self) -> None:
        job = self.claim()
        self.assertFalse(self.ack(job, lease_token="wrong-token"))
        self.assertEqual(job.state, "leased")
        self.assertTrue(self.ack(job))

    def test_acknowledgement_after_lease_expiry_is_rejected(self) -> None:
        job = self.claim()
        self.assertFalse(self.ack(job, now=131))
        self.assertEqual(job.state, "leased")

    def test_expired_lease_can_be_reclaimed_with_a_new_token(self) -> None:
        first = self.claim()
        old_token = first.lease_token
        reclaimed = self.claim(now=132)
        self.assertEqual(reclaimed.job_id, first.job_id)
        self.assertEqual(reclaimed.attempt_count, 2)
        self.assertNotEqual(reclaimed.lease_token, old_token)
        self.assertFalse(self.ack(reclaimed, lease_token=old_token, now=133))
        self.assertTrue(self.ack(reclaimed, now=133))

    def test_retry_respects_backoff_before_another_claim(self) -> None:
        job = self.claim()
        result = self.queue.retry(
            job_id=job.job_id,
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            lease_token=job.lease_token,
            now=102,
            retry_after_seconds=7,
            error_code="provider_busy",
        )
        self.assertEqual(result, "pending")
        self.assertEqual(self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=108,
        ), [])
        self.assertEqual(len(self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=109,
        )), 1)

    def test_fifth_claim_exhausts_attempts_after_lease_expiry(self) -> None:
        for attempt in range(1, 6):
            job = self.claim(now=100 + (attempt - 1) * 31)
            self.assertEqual(job.attempt_count, attempt)
        self.assertEqual(self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=256,
        ), [])
        self.assertEqual(self.queue.jobs_by_id[self.job_id].state, "failed")
        self.assertEqual(self.queue.jobs_by_id[self.job_id].last_error_code, "max_attempts")

    def test_expiration_clears_lease_and_prevents_ack(self) -> None:
        job = self.claim()
        job.expires_at = 120
        self.assertEqual(self.queue.expire(now=120), 1)
        self.assertEqual(job.state, "expired")
        self.assertIsNone(job.lease_token)
        self.assertFalse(self.ack(job, now=121))

    def test_consent_revocation_cancels_queued_and_leased_jobs(self) -> None:
        job = self.claim()
        self.assertEqual(self.queue.revoke_binding(binding_id=self.scope.binding_id), 1)
        self.assertEqual(job.state, "cancelled")
        self.assertFalse(self.ack(job))
        self.assertEqual(self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=103,
        ), [])

    def test_host_revocation_cancels_queued_jobs(self) -> None:
        self.assertEqual(self.queue.revoke_host(host_id=self.scope.host_id), 1)
        self.assertEqual(self.queue.jobs_by_id[self.job_id].state, "cancelled")

    def test_owner_can_cancel_only_their_own_pending_job(self) -> None:
        self.assertFalse(self.queue.cancel(job_id=self.job_id, owner_id="other-owner"))
        self.assertEqual(self.queue.jobs_by_id[self.job_id].state, "pending")
        self.assertTrue(self.queue.cancel(job_id=self.job_id, owner_id=self.scope.owner_id))
        self.assertEqual(self.queue.jobs_by_id[self.job_id].state, "cancelled")

    def test_terminal_jobs_cannot_be_claimed_again(self) -> None:
        job = self.claim()
        self.assertTrue(self.ack(job))
        self.assertEqual(self.queue.claim(
            host_id=self.scope.host_id,
            session_digest=self.scope.session_digest,
            binding_id=self.scope.binding_id,
            now=103,
        ), [])

    def test_ttl_and_claim_bounds_fail_closed(self) -> None:
        with self.assertRaisesRegex(QueueContractError, "TTL"):
            self.queue.enqueue(
                Request("c" * 64, "event-2", "d" * 64, Scope()),
                now=100,
                ttl_seconds=30,
            )
        with self.assertRaisesRegex(QueueContractError, "claim bounds"):
            self.queue.claim(
                host_id=self.scope.host_id,
                session_digest=self.scope.session_digest,
                binding_id=self.scope.binding_id,
                now=100,
                limit=21,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
