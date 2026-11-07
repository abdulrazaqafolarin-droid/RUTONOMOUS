from __future__ import annotations

import unittest

from contract_model.ack_settlement import (
    Lease,
    Outcome,
    Receipt,
    SettlementError,
)


class AckSettlementContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lease = Lease(
            lease_id="synthetic-lease-001",
            binding_id="synthetic-binding-001",
            provider_digest="a" * 64,
            expires_at=2_000,
        )

    def receipt(
        self,
        handoff: str = "synthetic-handoff-001",
        evidence: str = "synthetic-evidence-001",
        outcome: Outcome = Outcome.CONFIRMED,
    ) -> Receipt:
        return Receipt(handoff, evidence, outcome)

    def settle(self, receipt: Receipt, **kwargs: object) -> str:
        return self.lease.settle(
            receipt=receipt,
            now=int(kwargs.get("now", 1_000)),
            binding_id=str(kwargs.get("binding_id", "synthetic-binding-001")),
            provider_digest=str(kwargs.get("provider_digest", "a" * 64)),
        )

    def test_confirmed_submission_acknowledges_original_lease(self) -> None:
        result = self.settle(self.receipt())
        self.assertEqual(result, "acknowledged")
        self.assertEqual(self.lease.status, "acknowledged")
        self.assertFalse(self.lease.claimed)

    def test_exact_delayed_receipt_replay_is_idempotent(self) -> None:
        receipt = self.receipt()
        self.assertEqual(self.settle(receipt), "acknowledged")
        self.assertEqual(self.settle(receipt, now=5_000), "idempotent-replay")
        self.assertEqual(len(self.lease.receipts), 1)

    def test_reusing_handoff_with_different_evidence_is_rejected(self) -> None:
        self.settle(self.receipt())
        conflict = self.receipt(evidence="different-synthetic-evidence")
        with self.assertRaisesRegex(SettlementError, "different evidence"):
            self.settle(conflict)

    def test_expired_lease_cannot_become_success_from_late_receipt(self) -> None:
        with self.assertRaisesRegex(SettlementError, "expired"):
            self.settle(self.receipt(), now=2_000)
        self.assertEqual(self.lease.status, "claimed")
        self.assertEqual(self.lease.receipts, {})

    def test_revoked_consent_rejects_new_receipt(self) -> None:
        self.lease.consent_active = False
        with self.assertRaisesRegex(SettlementError, "consent is inactive"):
            self.settle(self.receipt())
        self.assertEqual(self.lease.status, "claimed")

    def test_binding_identity_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(SettlementError, "binding ID mismatch"):
            self.settle(self.receipt(), binding_id="another-binding")

    def test_provider_conversation_digest_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(SettlementError, "digest mismatch"):
            self.settle(self.receipt(), provider_digest="b" * 64)

    def test_proven_preflight_denial_is_retryable_within_attempt_limit(self) -> None:
        result = self.settle(self.receipt(outcome=Outcome.PREFLIGHT_DENIED))
        self.assertEqual(result, "retryable")
        self.assertEqual(self.lease.status, "retryable")
        self.assertFalse(self.lease.claimed)

    def test_exhausted_preflight_attempts_become_terminal_failure(self) -> None:
        self.lease.attempt = self.lease.max_attempts
        result = self.settle(self.receipt(outcome=Outcome.PREFLIGHT_DENIED))
        self.assertEqual(result, "failed")
        self.assertEqual(self.lease.status, "failed")

    def test_uncertain_post_effect_result_is_terminal_and_not_success(self) -> None:
        result = self.settle(self.receipt(outcome=Outcome.UNCERTAIN))
        self.assertEqual(result, "failed-result-unconfirmed")
        self.assertEqual(self.lease.status, "failed_result_unconfirmed")
        self.assertNotEqual(self.lease.status, "acknowledged")

    def test_new_receipt_cannot_settle_after_lease_was_already_acknowledged(self) -> None:
        self.settle(self.receipt())
        with self.assertRaisesRegex(SettlementError, "not actively claimed"):
            self.settle(self.receipt(handoff="another-handoff", evidence="another-proof"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
