# Termux / Python 3.14 MCP and cryptography ABI Compatibility

**Related issues:** #152, #153, #164  
**Status:** Enforced native-Termux support boundary

## Problem

On native Android/Termux with Python 3.14.x (aarch64), importing the MCP
Python SDK can fail inside `cryptography.hazmat.bindings._rust.abi3.so` with
missing CPython symbols such as:

- `PyLong_Type`
- `PyModule_Type`

Rebuilding `cryptography` from source does not by itself fix the runtime
linking failure. The extension can be loadable as a file while still lacking
a dynamic dependency on the Termux `libpython3.14.so` that exports the
symbols.

This is a Termux / Bionic / CPython shared-library linking boundary, not a
defect in Yasin-Operations Core. The same class of failure is tracked in
Termux's package issue #30705.

## Supported boundary

**Native Termux Python 3.14+ is currently not an MCP-supported runtime for
Yasin-Operations.** This boundary is intentional and is enforced by
`yasin_operations.mcp_compat` and the MCP tests.

The rule is:

- Core Yasin-Operations remains fully supported on native Termux.
- The `mcp` extra remains optional and does not become a Core dependency.
- Hosted Linux CPython 3.11–3.14 remains supported for the MCP bridge.
- Native Termux Python 3.14+ does not claim MCP support until the underlying
  cryptography/Termux dynamic-linking issue has a supported upstream or
  Termux packaging fix.
- The MCP bridge does not silently preload libraries, monkey-patch CPython
  symbols, or catch and hide a real `ImportError`.

This is a **support boundary**, not a workaround. Installing the optional
extra on an unsupported native-Termux runtime must not turn a known ABI
failure into an apparently healthy MCP service.

## Supported MCP runtime on Android

For MCP testing on an Android device, use the repository's supported Linux
runtime boundary, such as the Debian `proot-distro` environment already used
for hosted-style Yasin-Operations verification. The native Termux runtime
remains the production reference for Core and runit operations, but MCP is
not declared supported there on Python 3.14+ until the dependency/runtime
issue is resolved upstream.

## What Yasin-Operations does and does not do

- MCP is an **optional** extra (`pip install -e ".[mcp]"`).
- Core package, CLI, gateway, Executor and SafetyPolicy install and run
  without MCP or cryptography.
- On supported runtimes, MCP tests perform a real import and do not mask
  `ImportError`.
- On the explicitly unsupported native-Termux/Python 3.14+ boundary, MCP
  functional tests are skipped with the exact compatibility reason and a
  dedicated boundary test verifies that the restriction remains explicit.
- No monkey-patching of missing CPython symbols is performed.
- No `LD_PRELOAD` product workaround is used or documented.
- No pure-Python cryptography fallback is introduced.

## Hosted CI

GitHub Actions runs on Ubuntu with CPython 3.11–3.14. Standard
`cryptography` wheels resolve symbols correctly. The optional MCP extra is
installed by the MCP test job, so the supported MCP path is exercised rather
than merely syntax-checked.

## Verification checklist

- [ ] Core install: `pip install -e .` succeeds without MCP.
- [ ] MCP extra: `pip install -e ".[mcp]"` succeeds on supported Linux.
- [ ] Native Termux Python 3.14+: boundary test reports MCP unsupported.
- [ ] Supported Linux: `python -c "import mcp"` succeeds.
- [ ] Supported Linux: `python -m yasin_operations.mcp_server` starts over stdio.
- [ ] MCP tests pass when the extra is present on a supported runtime.

## References

- Termux/termux-packages #30705 — Python 3.14 cryptography symbol resolution
- Yasin-Operations issues #153 and #164 — P4.1 tracking
- Python packaging environment markers and platform compatibility metadata
