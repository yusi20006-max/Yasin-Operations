# Issue #3 — Investigation

## Scope given
P1 security fix for Telemirror direct dial; autonomous; no redesign of
Openfeed; no unrelated refactor; preserve fetching, fronting/uTLS, API,
runtime behavior; no weakened/skipped tests; fail closed; port to
YasinRelay/fetcher; keep both behaviorally equivalent + document sync.

## Codebase findings (read, not assumed)
- `internal/telemirror/client.go` (626 lines): `dialTLSFor` did
  `target := addr` when `ap.ip == ""`, then `d.DialContext(ctx, network,
  target)` — hostname resolved by the dialer at use-time. No URL/redirect
  validation anywhere (`FetchURLLimit` only checked `scheme == "https"`).
- No `validateSafeURL`, `safeCheckRedirect`, `resolveValidatedIPs`,
  `isForbiddenIP` existed; no `*_test.go` in Openfeed at all.
- `proxyAttempts`: 5 fixed-IP fronted + 2 fixed-IP non-fronted + 1 direct
  (`ip == ""`, Chrome). `FetchURLLimit` in Openfeed rewrites hosts via
  `toTranslateGoogHost` + direct fallback; fetcher copy is simpler
  (`hostHeader := u.Host`, no rewrite) — port had to preserve each side's
  own fetch shape while sharing identical security semantics.
- Fetcher baseline test: `fetcher/main_test.go` (frontURL/cleanHTML/parse
  posts) — untouched and still green.

## Vulnerability confirmed by reading
Check-time vs use-time DNS divergence: even a correct pre-check in
`FetchURLLimit` would not bind the later `DialContext(hostname)`.
Fix must pin at use-time: resolve inside the dial closure, dial IP
literals only. Double gate (early `validateSafeURL` for fast fail before
TCP contact + dial-time pinning) closes the window.
