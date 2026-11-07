# Rub Minds Test Lab (sanitised public harness)

This folder is a **public-safe reference test harness**, not a copy or mirror of the Rub Minds application.

## What it tests

The Python model exercises selected Backroom durable-wake queue contracts:

- one idempotency key cannot create duplicate jobs or be reused for different request evidence;
- claims are restricted to the expected host, MCP session digest, and input binding;
- a lease is unique, bounded, and tied to a short expiry;
- a valid acknowledgement consumes the lease, while a repeated, stale, expired, or incorrectly scoped ACK is not reported as success;
- expired leases may be reclaimed with a new token, subject to the five-attempt cap;
- retry backoff, TTL expiry, owner cancellation, consent revocation, and host revocation are represented;
- terminal jobs are not claimed again.

## Run locally

    python3 -m compileall -q contract_model tests
    python3 -m unittest discover -s tests -v

No third-party Python packages are required.

## Public-repository safety rules

- Never copy the private Rub Minds application repository into this folder.
- Do not add .env files, tokens, service-role keys, database dumps, real user data, APKs, signing keys, or private certificates.
- Use synthetic IDs, digests, events, and evidence only.
- Do not configure production deployment secrets or production database access.
- The included GitHub Actions workflow has read-only repository permissions, runs a lightweight public-material scan, and does not deploy. The scanner is a guardrail, not a guarantee or substitute for a dedicated secret scanner.

## Evidence boundary

A green workflow verifies only the independent reference model and its test runner. It does **not** prove that the private Rub Minds SQL migration, Supabase Edge Functions, Android companion, desktop host, Playwright adapter, or physical-device workflow passes. The private repository remains the source of truth for implementation tests.

## Next integration steps

1. Keep this public contract model aligned with reviewed behaviour in private implementation changes.
2. Run PostgreSQL migration and trigger tests in an isolated database before treating SQL as verified.
3. Run Node, TypeScript, Deno, and browser suites against an authorised private checkout.
4. Record implementation commit SHA and real test output separately from this synthetic suite.
