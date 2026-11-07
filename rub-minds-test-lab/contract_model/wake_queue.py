"""Sanitised reference model for the Rub Minds durable wake queue.

This deliberately does not import or reproduce Rub Minds production code. Its
contract is based on the state transitions documented in the public test lab.
A passing test validates this model only, not the private SQL implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


class QueueContractError(ValueError):
    """A queue operation violates the expected contract."""


@dataclass
class Scope:
    owner_id: str = "owner-1"
    room_id: str = "room-1"
    participant_id: str = "participant-1"
    host_id: str = "host-1"
    session_digest: str = "a" * 64
    binding_id: str = "binding-1"
    space_id: str = "space-1"
    session_id: str = "session-1"
    target_id: str = "target-1"
    target_fingerprint: str = "fingerprint-1"
    target_revision: int = 1
    host_active: bool = True
    consent_active: bool = True
    session_active: bool = True


@dataclass(frozen=True)
class Request:
    job_key: str
    event_id: str
    prompt_digest: str
    scope: Scope


@dataclass
class Job:
    job_id: str
    request: Request
    expires_at: int
    state: str = "pending"
    available_at: int = 0
    attempt_count: int = 0
    lease_token: Optional[str] = None
    lease_expires_at: Optional[int] = None
    last_error_code: Optional[str] = None


@dataclass(frozen=True)
class EnqueueResult:
    job_id: str
    created: bool
    state: str


class WakeQueue:
    """In-memory model of enqueue, claim, ACK, retry, expiry, and revocation."""

    MAX_ATTEMPTS = 5
    ERROR_CODES = {
        "target_unavailable", "approval_required", "provider_busy",
        "transport_error", "result_unconfirmed", "authorization_denied", "other",
    }

    def __init__(self) -> None:
        self.jobs_by_key: dict[str, Job] = {}
        self.jobs_by_id: dict[str, Job] = {}
        self._job_counter = 0
        self._lease_counter = 0

    @staticmethod
    def _same_request(left: Request, right: Request) -> bool:
        a, b = left.scope, right.scope
        identity_fields = (
            "owner_id", "room_id", "participant_id", "host_id",
            "session_digest", "binding_id", "space_id", "session_id",
            "target_id", "target_fingerprint", "target_revision",
        )
        return (
            left.job_key == right.job_key
            and left.event_id == right.event_id
            and left.prompt_digest == right.prompt_digest
            and all(getattr(a, key) == getattr(b, key) for key in identity_fields)
        )

    @staticmethod
    def _scope_active(scope: Scope) -> bool:
        return scope.host_active and scope.consent_active and scope.session_active

    def enqueue(self, request: Request, *, now: int, ttl_seconds: int = 3600) -> EnqueueResult:
        if (
            not re.fullmatch(r"[0-9a-f]{64}", request.job_key)
            or not re.fullmatch(r"[0-9a-f]{64}", request.scope.session_digest)
            or not re.fullmatch(r"[0-9a-f]{64}", request.prompt_digest)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", request.event_id)
        ):
            raise QueueContractError("invalid request identity or digest")
        if not 60 <= ttl_seconds <= 86_400:
            raise QueueContractError("TTL outside allowed range")
        if not self._scope_active(request.scope):
            raise QueueContractError("host, binding consent, or session is inactive")

        existing = self.jobs_by_key.get(request.job_key)
        if existing is not None:
            if not self._same_request(existing.request, request):
                raise QueueContractError("idempotency key conflicts with a different request")
            return EnqueueResult(existing.job_id, False, existing.state)

        self._job_counter += 1
        job = Job(
            job_id=f"job-{self._job_counter}",
            request=request,
            expires_at=now + ttl_seconds,
        )
        self.jobs_by_key[request.job_key] = job
        self.jobs_by_id[job.job_id] = job
        return EnqueueResult(job.job_id, True, job.state)

    def claim(
        self, *, host_id: str, session_digest: str, binding_id: str,
        now: int, limit: int = 5, lease_seconds: int = 30,
    ) -> list[Job]:
        if not 1 <= limit <= 20 or not 10 <= lease_seconds <= 120:
            raise QueueContractError("invalid claim bounds")

        scoped = [
            job for job in self.jobs_by_id.values()
            if job.request.scope.host_id == host_id
            and job.request.scope.session_digest == session_digest
            and job.request.scope.binding_id == binding_id
        ]
        if not scoped or not self._scope_active(scoped[0].request.scope):
            return []

        for job in scoped:
            if job.state in {"pending", "leased"} and job.expires_at <= now:
                self._clear_lease(job)
                job.state = "expired"
            elif (
                job.state == "leased"
                and job.lease_expires_at is not None
                and job.lease_expires_at <= now
                and job.attempt_count >= self.MAX_ATTEMPTS
            ):
                self._clear_lease(job)
                job.state = "failed"
                job.last_error_code = "max_attempts"

        eligible = [
            job for job in scoped
            if job.expires_at > now
            and job.attempt_count < self.MAX_ATTEMPTS
            and (
                (job.state == "pending" and job.available_at <= now)
                or (
                    job.state == "leased"
                    and job.lease_expires_at is not None
                    and job.lease_expires_at <= now
                )
            )
        ]
        eligible.sort(key=lambda job: job.job_id)
        claimed: list[Job] = []
        for job in eligible[:limit]:
            self._lease_counter += 1
            job.state = "leased"
            job.lease_token = f"lease-{self._lease_counter}"
            job.lease_expires_at = min(now + lease_seconds, job.expires_at)
            job.attempt_count += 1
            claimed.append(job)
        return claimed

    def acknowledge(
        self, *, job_id: str, host_id: str, session_digest: str,
        binding_id: str, lease_token: str, outcome: str, now: int,
    ) -> bool:
        if outcome not in {"acknowledged", "ignored"}:
            raise QueueContractError("invalid ACK outcome")
        job = self.jobs_by_id.get(job_id)
        if job is None or job.state != "leased":
            return False
        scope = job.request.scope
        if not self._scope_active(scope):
            return False
        if (
            scope.host_id != host_id
            or scope.session_digest != session_digest
            or scope.binding_id != binding_id
            or job.lease_token != lease_token
            or job.lease_expires_at is None
            or job.lease_expires_at <= now
            or job.expires_at <= now
        ):
            return False

        job.state = outcome
        self._clear_lease(job)
        return True

    def retry(
        self, *, job_id: str, host_id: str, session_digest: str,
        binding_id: str, lease_token: str, now: int,
        retry_after_seconds: int = 5, error_code: str = "other",
    ) -> Optional[str]:
        if not 1 <= retry_after_seconds <= 300 or error_code not in self.ERROR_CODES:
            raise QueueContractError("invalid retry parameters")
        job = self.jobs_by_id.get(job_id)
        if job is None or job.state != "leased":
            return None
        scope = job.request.scope
        if (
            not self._scope_active(scope)
            or scope.host_id != host_id
            or scope.session_digest != session_digest
            or scope.binding_id != binding_id
            or job.lease_token != lease_token
            or job.lease_expires_at is None
            or job.lease_expires_at <= now
            or job.expires_at <= now
        ):
            return None

        if job.attempt_count >= self.MAX_ATTEMPTS:
            job.state = "failed"
            job.last_error_code = "max_attempts"
        else:
            job.state = "pending"
            job.available_at = now + retry_after_seconds
            job.last_error_code = error_code
        self._clear_lease(job)
        return job.state

    def cancel(self, *, job_id: str, owner_id: str) -> bool:
        job = self.jobs_by_id.get(job_id)
        if (
            job is None
            or job.request.scope.owner_id != owner_id
            or job.state not in {"pending", "leased"}
        ):
            return False
        job.state = "cancelled"
        self._clear_lease(job)
        return True

    def expire(self, *, now: int) -> int:
        changed = 0
        for job in self.jobs_by_id.values():
            if job.state in {"pending", "leased"} and job.expires_at <= now:
                job.state = "expired"
                self._clear_lease(job)
                changed += 1
        return changed

    def revoke_binding(self, *, binding_id: str, owner_id: str) -> bool:
        matching = [
            job for job in self.jobs_by_id.values()
            if job.request.scope.binding_id == binding_id
        ]
        if not matching or matching[0].request.scope.owner_id != owner_id:
            return False
        for job in matching:
            scope = job.request.scope
            scope.consent_active = False
            if job.state in {"pending", "leased"}:
                job.state = "cancelled"
                self._clear_lease(job)
        return True

    def revoke_host(self, *, host_id: str, owner_id: str) -> bool:
        matching = [
            job for job in self.jobs_by_id.values()
            if job.request.scope.host_id == host_id
        ]
        if not matching or matching[0].request.scope.owner_id != owner_id:
            return False
        for job in matching:
            scope = job.request.scope
            scope.host_active = False
            scope.consent_active = False
            if job.state in {"pending", "leased"}:
                job.state = "cancelled"
                self._clear_lease(job)
        return True

    @staticmethod
    def _clear_lease(job: Job) -> None:
        job.lease_token = None
        job.lease_expires_at = None
