# Issue #3 — P1 Security: Eliminate DNS Rebinding TOCTOU in Telemirror Direct Dial

**Repository:** `yusi20006-max/Openfeed` (work: `~/projects/Openfeed`, branch `main`)
**Mirror port:** `YasinRelay/fetcher` (work: `~/YASIN-REPOS/YasinRelay`, module `fetcher/`)
**Status: DELIVERED — COMMITTED + PUSHED WITH EVIDENCE**
**Updated:** 2026-09-06 UTC

**Commits (pushed):**
- Openfeed `1dff8fe` — "Security: eliminate DNS rebinding TOCTOU in
  Telemirror direct dial (Issue #3)" (rebased onto `29f8dbb`, pushed
  `29f8dbb..1dff8fe` to `origin/main`)
- YasinRelay `6b9b02b` — "fix(security): eliminate DNS rebinding TOCTOU
  in fetcher direct dial (Openfeed Issue #3)" (pushed
  `d977541..6b9b02b` to `origin/main`)
- Only remaining delta found during verification: missing sync section in
  `fetcher/README.md` — fixed (same YasinRelay commit above).

## Threat
`dialTLSFor` with `ap.ip == ""` (direct dial) passed the URL hostname
straight to `net.Dialer`, so DNS was resolved again at use-time, after any
check-time validation. A hostname flipping to loopback/private/link-local/
multicast/unspecified between check and dial could reach internal services
(DNS-rebinding TOCTOU). No `validateSafeURL` / `safeCheckRedirect` existed.

## Fix (fail closed, both copies)
- `resolveValidatedIPs(ctx, host)` — IP literals rejected if forbidden;
  hostnames via `LookupIPAddr`, rejected on lookup error, empty answers, or
  if **ANY** answer is forbidden.
- `validateSafeURL(ctx, rawURL)` uses the helper; requires `https`.
- `dialTLSFor` direct path re-resolves **inside** the dial closure and dials
  only validated IP literals — hostname never reaches `net.Dialer`.
- `safeCheckRedirect` re-validates every redirect (10-cap preserved).
- Fixed-IP fronted attempts (`ap.ip != ""`) preserved: still dial pinned
  `ap.ip:443` with zero resolver contact (proven by test).

## Files
- Openfeed: `M internal/telemirror/client.go`, `?? internal/telemirror/security.go`, `?? internal/telemirror/security_test.go`
- YasinRelay: `M fetcher/telemirror/client.go`, `?? fetcher/telemirror/security.go`, `?? fetcher/telemirror/security_test.go`
- `security.go` / `security_test.go` byte-identical across both (`diff` exit 0).

## Verification (actual runs, 2026-09-06, go1.27.0 android/arm64)
- Openfeed: `gofmt -l .` → only pre-existing `internal/telemirror/types.go`;
  `go vet ./...` exit 0; `go test ./... -count=1` → 10/10 telemirror PASS;
  `go build ./...` exit 0.
- Fetcher: `gofmt -l .` → only pre-existing `telemirror/types.go`;
  `go vet ./...` exit 0; `go test ./... -count=1` → `ok fetcher` +
  `ok fetcher/telemirror`; `go build ./...` exit 0.

## Not done
Nothing. Working trees clean in both repos; report commit pending at the
time of this edit (see latest.md handoff).
