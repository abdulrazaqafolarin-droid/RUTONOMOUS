#!/usr/bin/env python3
"""Fail closed if obvious private material is added to this public test lab.

This is a lightweight guardrail, not a replacement for a dedicated secret scanner.
It deliberately prints file paths and rule names only, never matched values.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", "__pycache__", ".venv", "node_modules"}

FORBIDDEN_SUFFIXES = {
    ".jks", ".keystore", ".apk", ".aab", ".pem", ".p12", ".pfx",
    ".mobileprovision", ".dump", ".p8", ".cer", ".der", ".crt", ".key",
    ".db", ".sqlite", ".sqlite3", ".zip", ".tar", ".gz", ".tgz", ".7z",
    ".rar", ".bin", ".exe", ".msi", ".dmg", ".iso", ".jar", ".war", ".class",
}
FORBIDDEN_NAMES = {
    ".env", ".npmrc", ".pypirc", ".netrc", ".git-credentials",
    "id_rsa", "id_ed25519", "credentials.json", "secrets.json",
    "service-account.json", "google-credentials.json",
}
FORBIDDEN_DIR_NAMES = {"secret", "secrets", "credential", "credentials", "private-keys"}

SECRET_PATTERNS = (
    ("private-key-block", re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    )),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("stripe-secret", re.compile(r"\bsk_(?:live|test|proj)-[A-Za-z0-9_-]{16,}\b")),
    ("supabase-secret", re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}\b")),
    ("openai-api-key", re.compile(r"\bsk-(?:proj-|svcacct-)[A-Za-z0-9_-]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    ("vercel-token", re.compile(r"\bvercel_[A-Za-z0-9]{20,}\b")),
    ("jwt-like-token", re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    )),
)

MAX_TEXT_BYTES = 1_000_000


def forbidden_path(path: Path) -> str | None:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if name in FORBIDDEN_NAMES or (name.startswith(".env.") and name != ".env.example"):
        return "environment-file"
    if any(part in FORBIDDEN_DIR_NAMES for part in parts):
        return "private-material-directory"
    if any(name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        return "private-binary-or-key-file"
    if name.endswith(".sql.gz"):
        return "database-dump"
    return None


def inspect_text(data: str) -> list[str]:
    return [label for label, pattern in SECRET_PATTERNS if pattern.search(data)]


def scan(root: Path = ROOT) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        path_rule = forbidden_path(relative)
        if path_rule:
            findings.append((relative.as_posix(), path_rule))
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            findings.append((relative.as_posix(), "unreadable-file"))
            continue
        if len(raw) > MAX_TEXT_BYTES:
            findings.append((relative.as_posix(), "oversized-file"))
            continue
        if b"\x00" in raw:
            findings.append((relative.as_posix(), "binary-file"))
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            findings.append((relative.as_posix(), "non-text-file"))
            continue
        for label in inspect_text(content):
            findings.append((relative.as_posix(), label))
    return findings


if __name__ == "__main__":
    problems = scan()
    if problems:
        print("Public repository safety check failed:")
        for path, rule in problems:
            print(f"- {path}: {rule}")
        sys.exit(1)
    print("Public repository safety check passed.")
