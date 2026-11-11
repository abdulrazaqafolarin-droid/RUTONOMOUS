# Temporary CI validation trigger

This marker exists only to trigger the repository's sanitised Rub Minds Test Lab workflow from a draft pull request. It contains no application source, credentials, private data, or deployment configuration.

The workflow runs the repository safety scan, GitHub Actions YAML parsing and linting, Python syntax checks, and synthetic acceptance contracts. It does not access production services or publish artifacts.
