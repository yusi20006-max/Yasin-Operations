# Audit Policy

## Purpose

The audit layer records operation attribution and outcomes for operational forensics. It is observational evidence; it is not an authorization source.

## Recorded attribution

Each `AuditRecord` carries operation ID/name, target, lifecycle status, timestamp, actor, source, correlation ID, duration, dry-run state, and structured error information when present.

## Redaction

Audit metadata and error details are sanitized before being retained by the reference recorder. Common credential-bearing fields such as passwords, tokens, API keys, authorization values, cookies, credentials, and private keys are replaced with `<redacted>`. Long strings are bounded and unknown object types are represented without serializing their internals.

This is a defensive application-level redaction layer, not a substitute for avoiding secrets in operation parameters or logs.

## Integrity and failure behavior

`AuditRecord` validates required attribution and lifecycle types. The in-memory recorder is thread-safe and returns snapshots rather than its mutable internal list.

An audit sink failure must never grant authorization or bypass `SafetyPolicy`. The Executor treats the audit sink as observational: an operation's authorization and tool execution are decided independently. A sink failure therefore does not cause the caller to retry a mutation merely because an audit write failed.

Persistent production sinks remain deployment-specific and must provide their own durability, retention, access control, and tamper-evidence guarantees.

## Retention

The reference in-memory recorder has process lifetime retention and is not a durable incident archive. This repository does not claim persistent retention, centralized storage, or tamper-proof audit history without a configured persistent sink.
