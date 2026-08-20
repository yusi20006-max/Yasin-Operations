# Authorization Model

## One authoritative mutation gate

All registered operations are executed through `Executor`. The executor verifies that the requested safety classification matches the registered tool capability and then evaluates `SafetyPolicy` before invoking the tool.

No transport may directly invoke a mutating tool or substitute its own authorization result.

## Mutation rules

By default:

1. `READ_ONLY` operations are allowed without confirmation.
2. `MUTATING` operations require explicit boolean confirmation.
3. Named `auto_approved_mutations` may omit confirmation according to local policy.
4. Protected targets are denied unless the operation name is in `protected_mutation_allowlist`.
5. A protected mutation still requires explicit confirmation, even when auto-approved.

The policy is deny-by-default for protected mutation targets.

## Confirmation semantics

`confirmation` and `dry_run` are strictly typed booleans at both the external request contract and Executor/SafetyPolicy boundaries. Truthy strings, integers, or other values cannot be interpreted as approval.

This prevents a transport or caller from turning an ambiguous value such as `"true"` or `1` into authorization.

## Dry-run semantics

Dry-run produces a deterministic operation plan and does not call the tool. It is not a mutation authorization bypass and must never be used as a substitute for confirmed execution.

## Identity

`actor`, `source`, and `correlation_id` are validated metadata used for execution context and audit correlation. They do not themselves grant permission. Authenticated transports must establish caller identity separately and pass the verified identity into the execution boundary.

## Safety-class integrity

The requested operation safety class is checked against the registered tool capability before policy evaluation. A caller cannot downgrade a mutating tool to `READ_ONLY` merely by changing request metadata.

## Protected targets

Protected-target checks are performed inside `SafetyPolicy`, after capability classification and before tool execution. Confirmation is evaluated again for protected mutations; transport defaults cannot bypass this check.
