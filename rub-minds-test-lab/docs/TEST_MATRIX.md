# Backroom durable wake contract matrix

| Contract | Public reference-model test | Private implementation evidence still required |
|---|---|---|
| Idempotent enqueue returns the original job | Yes | SQL uniqueness/advisory-lock regression |
| Reusing an idempotency key for different request data is rejected | Yes | SQL conflict-path regression |
| Claim is scoped to host, session digest, and binding | Yes | Authenticated Edge + SQL claim integration |
| Claim increments attempt count and issues a lease token | Yes | SQL lease token hash and concurrent worker test |
| ACK consumes only the current, unexpired lease | Yes | SQL ACK regression against wrong, stale, and expired tokens |
| Repeated ACK is not treated as successful replay | Yes | SQL ACK after terminal-state regression |
| Expired lease can be reclaimed with a new token | Yes | SQL lease-expiry integration and concurrent worker test |
| Retry backoff prevents premature re-claim | Yes | SQL available-at and retry counter integration |
| Maximum five claims lead to terminal failure after lease expiry | Yes | SQL attempt exhaustion integration |
| TTL expiry clears pending/leased work | Yes | SQL expiry function and worker interaction |
| Consent or host revocation cancels pending/leased work | Yes | SQL transaction + live host revocation test |
| Owner cancellation is owner-scoped | Yes | SQL ownership and privilege tests |
| Terminal jobs cannot be claimed again | Yes | SQL state-transition regression |

## Evidence boundary

This table records test coverage in a standalone reference model only. No private implementation is imported into this public repository. A green workflow is not a production, migration, Edge Function, device, or end-to-end acceptance result.
