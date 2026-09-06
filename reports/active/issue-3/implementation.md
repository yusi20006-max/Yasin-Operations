# Issue #3 — Implementation

## New file (both repos, byte-identical): `telemirror/security.go`
- `forbiddenNets` (explicit CIDRs, fail closed even if stdlib semantics
  shift): `0.0.0.0/8`, `10/8`, `100.64/10`, `127/8`, `169.254/16`,
  `172.16/12`, `192.0.0.0/24`, `192.0.2/24`, `192.168/16`, `198.18/15`,
  `198.51.100/24`, `203.0.113/24`, `224/4`, `240/4`, `255.255.255.255/32`,
  `::/128`, `::1/128`, `64:ff9b::/96`, `100::/64`, `2001::/32` (Teredo),
  `2002::/16` (6to4), `fc00::/7`, `fe80::/10`, `ff00::/8`.
- `isForbiddenIP`: nil → forbidden; `IsUnspecified/IsLoopback/IsMulticast/
  IsLinkLocalUnicast/IsLinkLocalMulticast/IsPrivate` → forbidden; CIDR
  match → forbidden; embedded-IPv4 (`To4`, e.g. `::ffff:127.0.0.1`)
  re-checked → forbidden.
- `lookupIPAddr` var (default `net.DefaultResolver.LookupIPAddr`) for
  deterministic stubbed tests.
- `resolveValidatedIPs(ctx, host)`: trims space/trailing dot; empty →
  error; `net.ParseIP` literal → forbidden-check or single-IP return;
  hostname → `LookupIPAddr`, error/empty → error, **ANY** forbidden answer
  poisons the whole set.
- `validateSafeURL(ctx, rawURL)`: parse, require `https`, non-empty host,
  `resolveValidatedIPs(Hostname())`.
- `safeCheckRedirect`: `len(via) >= 10` → stop; nil req/URL → error;
  else `validateSafeURL(req.URL)`.
- Header comment documents the two synced paths and the threat model.

## Modified (each repo's own fetch shape preserved): `telemirror/client.go`
- `dialTLSFor`: shared `dialAndHandshake(target)` helper; `ap.ip != ""`
  → `JoinHostPort(ap.ip, "443")` exactly as before; `ap.ip == ""` →
  `SplitHostPort(addr)`, `resolveValidatedIPs(dialHost)`, dial each
  validated `ip:port`, first successful handshake wins. Hostname never
  passed to `net.Dialer`. Removed now-unused `neturl` import.
- `do()`: `CheckRedirect: safeCheckRedirect` added.
- `FetchURLLimit()`: old `neturl.Parse` + scheme check replaced by
  `validateSafeURL(ctx, rawURL)` (same `https` enforcement + SSRF gate).
- `fetchOnly()`: `CheckRedirect: safeCheckRedirect` added.
- Only incidental diff: 2-line `gofmt` const-alignment.

## New file (both repos, byte-identical): `telemirror/security_test.go`
10 tests mapping 1:1 to the required regressions (see verification.md).
