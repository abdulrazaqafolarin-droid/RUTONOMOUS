# Test matrix and evidence boundaries

| Contract | Synthetic test in this starter | Real Rub Minds implementation evidence still required |
|---|---|---|
| Confirmed result settles the original lease | Yes | SQL settlement function + authenticated Edge endpoint integration |
| Exact same handoff receipt is idempotent | Yes | Database replay behavior and device ACK outbox integration |
| Same handoff ID with changed evidence is rejected | Yes | SQL constraint/function and endpoint regression |
| Expired lease cannot be marked successful by a late new receipt | Yes | Database clock/lease check under concurrent settlement |
| Revoked binding cannot accept a new receipt | Yes | Consent-revocation race test against SQL locks |
| Binding ID and provider digest must match | Yes | Host binding lookup + SQL null-safe comparison tests |
| Preflight denial may retry only within bounded attempts | Yes | Queue retry counter and lease re-claim integration |
| Uncertain post-effect result is not reported as success | Yes | Device command result mapping and durable job settlement |

This table deliberately separates the reference-model pass from real implementation evidence.
