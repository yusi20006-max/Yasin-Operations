# Issue #3 — Verification (actual runs, 2026-09-06, go1.27.0 android/arm64)

## Openfeed (`~/projects/Openfeed`)
- `gofmt -l .` → `internal/telemirror/types.go` ONLY (pre-existing
  comment-alignment, untouched by this fix).
- `go vet ./...` → exit 0, no output.
- `go test ./internal/telemirror/ -v -count=1` → 10/10 PASS:
  `TestResolveValidatedIPsPublicIPAccepted`,
  `TestResolveValidatedIPsForbiddenIPRejected`,
  `TestResolveValidatedIPsLocalhostRejected`,
  `TestResolveValidatedIPsPublicHostnameAccepted`,
  `TestResolveValidatedIPsMixedAnswersFailClosed`,
  `TestValidateSafeURL`,
  `TestDirectDialRejectsPrivateBeforeContact`,
  `TestFixedIPFrontedPathUnchanged`,
  `TestSafeCheckRedirectPreserved`,
  `TestFetchURLLimitRejectsPrivateBeforeContact`
  (`ok openfeed/internal/telemirror 0.029s`).
- `go build ./...` → exit 0.

## YasinRelay/fetcher (`~/YASIN-REPOS/YasinRelay/fetcher`)
- `gofmt -l .` → `telemirror/types.go` ONLY (same pre-existing file).
- `go vet ./...` → exit 0.
- `go test ./... -count=1` → `ok fetcher 0.020s` (pre-existing
  `main_test.go` still green) + `ok fetcher/telemirror 0.029s` (10 new
  tests PASS), exit 0.
- `go build ./...` → exit 0.

## Behavioral equivalence (actual runs)
- `diff Openfeed/.../security.go fetcher/.../security.go` → exit 0.
- `diff Openfeed/.../security_test.go fetcher/.../security_test.go` → exit 0.
- Tracked diff in both repos: one file each (`client.go`, 77+/37-,
  dial-gate + redirect wiring + import/gofmt only).

## Requirement checklist (each verified by a named test above)
public IP accepted / loopback-private-link-local-ULA-unspecified-multicast
rejected / localhost rejected / public hostname accepted / direct empty-IP
path rejects private before contact / fixed-IP fronted path unchanged /
mixed answers fail closed / redirect validation preserved / existing SSRF
tests green (none existed; fetcher `main_test.go` green).
