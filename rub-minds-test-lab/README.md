# Rub Minds Test Lab (sanitised starter)

This folder is a **public-safe test harness**, not a copy of the Rub Minds application.

## What this currently tests

The Python tests exercise a small, independent reference model for the expected Android native-wake acknowledgement contract:

- exact-receipt replay is idempotent;
- the same handoff ID cannot be reused with different evidence;
- expired leases cannot become successful from late receipts;
- revoked consent and mismatched binding/provider identities are rejected;
- proven preflight denials may retry only within the attempt limit;
- uncertain post-effect outcomes are never reported as success.

**Important limitation:** these tests verify the reference model in this folder. They do not execute the Rub Minds production implementation. A green run is not proof that the app, Supabase migrations, Edge Functions, Android companion, or physical-device flow works.

## Run locally

```bash
python3 -m compileall -q contract_model tests
python3 -m unittest discover -s tests -v
```

No third-party Python packages are required.

## Public-repository safety rules

- Never copy the private `Rub-minds` application repository into this folder.
- Do not add `.env` files, tokens, service-role keys, database dumps, real user data, APKs, signing keys, or private certificates.
- Use synthetic IDs and synthetic evidence only.
- Do not configure production deployment secrets or production database access.
- The included workflow has read-only repository permissions and does not deploy.

## Next integration steps

1. Add narrowly scoped, sanitised contract fixtures for SQL, Node, and Kotlin boundaries.
2. Add an adapter that consumes synthetic test traces emitted by local runs.
3. Run real project tests only from an authorised private checkout or a suitably isolated local runner. Do not publish private implementation source to make public CI green.
