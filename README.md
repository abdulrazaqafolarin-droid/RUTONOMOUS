# RUTONOMOUS

Autonomous AI Engineering System that can:
- understand your codebase
- understand your product vision
- plan strategically
- execute tasks autonomously
- learn continuously
- evolve the project over time

## Isolated Rub Minds test lab

The `rub-minds-test-lab/` folder contains a standalone, sanitised synthetic acceptance harness for selected Rub Minds safety contracts.

It is intentionally separate from the Rub Minds application. It contains no production application source, credentials, Supabase configuration, user data, database dumps, APKs, signing keys, or deployment secrets.

The GitHub Actions workflow for this test lab has read-only repository permissions. It runs only the synthetic Python contract tests and does not deploy or connect to production services.

**Evidence boundary:** a passing test-lab run verifies only the independent reference model. It does not prove that the real Rub Minds SQL migrations, Edge Functions, Android companion, or device workflow pass.


## Private Rub Minds validation from this public test harness

See [docs/PRIVATE_RUB_MINDS_CI.md](docs/PRIVATE_RUB_MINDS_CI.md) for the manual-only workflow, least-privilege read-token setup, and run instructions. The private source is checked out only on temporary runners; it is never committed to this repository.
