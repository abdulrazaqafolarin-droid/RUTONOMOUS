"""Synthetic reference model for durable native-wake ACK settlement.

This is deliberately independent of Rub Minds production source. It defines expected
safety properties for tests and must not be treated as the production implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Outcome(str, Enum):
    CONFIRMED = "confirmed"
    PREFLIGHT_DENIED = "preflight_denied"
    UNCERTAIN = "uncertain"


class SettlementError(ValueError):
    """The supplied receipt cannot safely settle the original lease."""


@dataclass(frozen=True)
class Receipt:
    handoff_id: str
    evidence: str
    outcome: Outcome


@dataclass
class Lease:
    lease_id: str
    binding_id: str
    provider_digest: str
    expires_at: int
    claimed: bool = True
    consent_active: bool = True
    status: str = "claimed"
    attempt: int = 1
    max_attempts: int = 5
    receipts: dict[str, Receipt] = field(default_factory=dict)
    latest_result: Receipt | None = None

    def settle(
        self,
        *,
        receipt: Receipt,
        now: int,
        binding_id: str,
        provider_digest: str,
    ) -> str:
        """Apply a receipt once; exact duplicate receipts are idempotent.

        The replay lookup occurs before active-lease checks so an exact delayed retry
        can be acknowledged without repeating the original side effect. New evidence
        cannot turn an expired or revoked lease into a success.
        """
        previous = self.receipts.get(receipt.handoff_id)
        if previous is not None:
            if previous != receipt:
                raise SettlementError("handoff ID reused with different evidence")
            return "idempotent-replay"

        if self.status != "claimed" or not self.claimed:
            raise SettlementError("lease is not actively claimed")
        if now >= self.expires_at:
            raise SettlementError("lease has expired")
        if not self.consent_active:
            raise SettlementError("binding consent is inactive")
        if binding_id != self.binding_id:
            raise SettlementError("binding ID mismatch")
        if provider_digest != self.provider_digest:
            raise SettlementError("provider conversation digest mismatch")
        if len(self.receipts) >= self.max_attempts:
            raise SettlementError("receipt retention limit reached")

        self.receipts[receipt.handoff_id] = receipt
        self.latest_result = receipt

        if receipt.outcome is Outcome.CONFIRMED:
            self.status = "acknowledged"
            self.claimed = False
            return "acknowledged"

        if receipt.outcome is Outcome.PREFLIGHT_DENIED:
            self.claimed = False
            if self.attempt < self.max_attempts:
                self.status = "retryable"
                return "retryable"
            self.status = "failed"
            return "failed"

        self.status = "failed_result_unconfirmed"
        self.claimed = False
        return "failed-result-unconfirmed"
