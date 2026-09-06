# Issue #3 — Evidence (verbatim command outputs, 2026-09-06)

## Worktree state
Openfeed:
```
M internal/telemirror/client.go
?? internal/telemirror/security.go
?? internal/telemirror/security_test.go
```
YasinRelay:
```
M fetcher/telemirror/client.go
?? fetcher/telemirror/security.go
?? fetcher/telemirror/security_test.go
```

## Openfeed validation
```
$ gofmt -l .
internal/telemirror/types.go
$ go vet ./...          -> VET_EXIT:0 (no output)
$ go test ./... -count=1
?   openfeed/cmd/server      [no test files]
?   openfeed/internal/api    [no test files]
?   openfeed/internal/model  [no test files]
?   openfeed/internal/parser [no test files]
?   openfeed/internal/provider [no test files]
ok  openfeed/internal/telemirror 0.029s   (10/10 new tests PASS, -v list in verification.md)
$ go build ./...        -> BUILD_EXIT:0
```

## Fetcher validation
```
$ gofmt -l .
telemirror/types.go
$ go vet ./...          -> VET_EXIT:0
$ go test ./... -count=1
ok  fetcher 0.020s
?   fetcher/api  [no test files]
?   fetcher/cmd/server  [no test files]
?   fetcher/model  [no test files]
?   fetcher/parser  [no test files]
?   fetcher/provider  [no test files]
ok  fetcher/telemirror 0.029s
$ go build ./...        -> BUILD_EXIT:0
```

## Equivalence
```
$ diff <Openfeed>/internal/telemirror/security.go <YasinRelay>/fetcher/telemirror/security.go
-> SEC_DIFF:0 (no output)
$ diff <Openfeed>/internal/telemirror/security_test.go <YasinRelay>/fetcher/telemirror/security_test.go
-> TEST_DIFF:0 (no output)
```

## Delivery (2026-09-06)
```
Openfeed:   29f8dbb..1dff8fe  main -> main   (push OK)
  [main 1dff8fe] Security: eliminate DNS rebinding TOCTOU in Telemirror direct dial (Issue #3)
  3 files changed, 576 insertions(+), 37 deletions(-)
YasinRelay: d977541..6b9b02b  main -> main   (push OK)
  [main 6b9b02b] fix(security): eliminate DNS rebinding TOCTOU in fetcher direct dial (Openfeed Issue #3)
  4 files changed, 596 insertions(+), 37 deletions(-)
```
Remote divergence encountered once (Openfeed `29f8dbb` docs-only README
commit); resolved via `git rebase origin/main` (no conflicts, disjoint
files), then pushed. No force-push used.

## Notes
- No secrets, tokens, or private data in this report.
- Changes uncommitted in both working trees at report time; no PR created.
- `gofmt` findings limited to pre-existing `types.go` files, not introduced here.
