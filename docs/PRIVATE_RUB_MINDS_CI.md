# Running private Rub Minds tests from RUTONOMOUS

RUTONOMOUS remains a public, sanitised test harness. The workflow in this repository can run selected tests against the **private Rub Minds source** without copying that source into RUTONOMOUS.

## What the private validation workflow does

The workflow is manual-only. It runs only when dispatched from RUTONOMOUS main by the repository owner, and it checks out the selected private Rub Minds branch onto temporary GitHub-hosted runners. A shared preflight validates the selected ref and confirms that the read-only token exists before any test job starts.

It covers five independent validation groups:

1. Web build, registered Node test suites, Vitest, Deno helper/type checks, and browser regression tests.
2. PostgreSQL 17 migration and SQL regression tests for the durable wake queue, provider identity, Android native settlement, and group-task coordination.
3. Android protocol tests, Gradle unit tests, merged-manifest audit, and a compile-only debug APK/signature check.
4. A complete disposable local Supabase stack: full migration reset, real React human signup and invitation flows, invite revocation, Vault and bridge-state checks, official MCP SDK interoperability, two independent AI sessions, human↔AI group messaging, realtime, RLS isolation, and Backroom device pairing/authorization.
5. Windows web/companion build, Rust tests, protocol tests, and Windows executable link/fingerprint check.

The workflow does not connect to production Supabase: all Supabase integration tests run against a disposable local stack on the temporary runner. It does not deploy or upload APK/EXE artifacts. It intentionally suppresses raw command output because the runner's logs are visible from the public RUTONOMOUS repository. It reports pass/fail for each test group and prints only non-sensitive build fingerprints. If a command fails, detailed diagnostics must be reproduced locally in the private checkout.

## One-time access setup

The workflow needs a narrowly scoped fine-grained personal access token so the public RUTONOMOUS workflow can read the private Rub Minds repository.

1. Open [GitHub fine-grained personal access tokens](https://github.com/settings/personal-access-tokens/new).
2. Choose your account as the resource owner.
3. Under repository access, select **Only select repositories**, then select **Rub-minds** only.
4. Grant **Contents: Read-only**. Leave write permissions disabled. GitHub's required metadata access is automatic.
5. Create the token with a short expiry that suits the test window. Do not paste the token into this chat or commit it to any file.
6. Open [RUTONOMOUS repository settings](https://github.com/abdulrazaqafolarin-droid/RUTONOMOUS/settings/secrets/actions).
7. Select **New repository secret** and set:
   - Name: RUB_MINDS_READ_TOKEN
   - Secret: the fine-grained token you just created.
8. Save the secret. Do not create any other secrets for this workflow.

The token is passed only to the checkout action. It is not exported to build or test commands. The checked-out private source remains on the temporary runner, and no source archive or binary artifact is uploaded.

## Run a test

1. Open [RUTONOMOUS Actions](https://github.com/abdulrazaqafolarin-droid/RUTONOMOUS/actions).
2. Select **Private Rub Minds validation on free runners**.
3. Choose **Run workflow** on the main branch.
4. Keep the source ref as feat/native-provider-digest-queue for the current native provider/queue regression branch, or enter another existing Rub Minds branch.
5. Start the workflow and inspect the five job summaries.

Standard GitHub-hosted runners are free for public repositories. This workflow is deliberately manual-only so it does not run private-source tests for outside pull requests. See [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage).

## Security and evidence limits

- Never put the private Rub Minds source, SQL migrations, user data, signing keys, APKs, EXEs, or environment files in the public RUTONOMOUS repository.
- The fine-grained token is read-only and restricted to the single private Rub Minds repository.
- Do not widen the token to all repositories or grant write access.
- The workflow uses no production credentials, no production database, and no deployment steps.
- No build artifacts are uploaded from the public workflow. The APK and EXE are removed after fingerprinting, local Supabase credentials and logs remain on the temporary runner, and the runner is discarded.
- Public logs contain pass/fail summaries only; raw test/build output is intentionally withheld.
- A green result validates the selected private branch at the reported checkout commit. It is not a production deployment or a real-device/provider-session acceptance result.
- Revoke the token when you no longer need this workflow.

