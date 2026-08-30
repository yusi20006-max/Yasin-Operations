# Termux / Python 3.14 MCP and cryptography ABI Compatibility

**Related issues:** #152, #153  
**Status:** Documented supported boundary

## Problem

On native Android/Termux with Python 3.14.x (aarch64), importing the MCP
Python SDK fails inside `cryptography.hazmat.bindings._rust.abi3.so` with
missing CPython symbols such as:

- `PyLong_Type`
- `PyModule_Type`

Rebuilding `cryptography` from source produces a wheel that still fails at
`dlopen` time because the extension does not declare a DT_NEEDED dependency
on `libpython3.14.so`. The symbols exist in Termux's shared library but are
not resolved by the dynamic linker for the abi3 extension.

This is a Termux / Bionic / CPython shared-library linking issue, not a
defect in Yasin-Operations Core.

## Supported solutions (in preference order)

### 1. Termux system package (preferred)

Termux's `python-cryptography` package applies `patchelf --add-needed
libpythonX.Y.so` to the Rust extension:

```sh
pkg install python-cryptography
pip install "mcp>=2,<3"
# or
pip install -e ".[mcp]"
```

### 2. LD_PRELOAD workaround

```sh
export LD_PRELOAD=$PREFIX/lib/libpython3.14.so
python -c "import mcp; print('ok')"
# then run the MCP server under the same environment
```

A thin wrapper is acceptable for operator convenience:

```sh
#!/data/data/com.termux/files/usr/bin/sh
export LD_PRELOAD="${PREFIX}/lib/libpython3.14.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec python -m yasin_operations.mcp_server "$@"
```

### 3. proot-distro Debian

Use a Debian proot environment (Python 3.13) where standard Linux wheels
and dynamic linking behave normally. This is the supported path for
hosted-style Linux-side testing of MCP.

## What Yasin-Operations does and does not do

- MCP is an **optional** extra (`pip install -e ".[mcp]"`).
- Core package, CLI, gateway, Executor and SafetyPolicy install and run
  without MCP or cryptography.
- Tests that require the MCP SDK are skipped when the extra is absent.
- When the extra is installed, tests perform a real import; they do not
  catch or mask `ImportError`.
- No monkey-patching of missing CPython symbols is performed.
- No pure-Python cryptography fallback is introduced.

## Hosted CI

GitHub Actions runs on Ubuntu with CPython 3.11–3.14. Standard
`cryptography` wheels resolve symbols correctly. The optional MCP extra is
not installed by default in CI; MCP tests remain skipped unless the extra
is added to a job.

## Verification checklist

- [ ] Core install: `pip install -e .` succeeds without MCP.
- [ ] MCP extra: `pip install -e ".[mcp]"` succeeds on supported Linux.
- [ ] On Termux: follow one of the three paths above; `python -c "import mcp"` succeeds.
- [ ] `python -m yasin_operations.mcp_server` starts (stdio) after a successful import.
- [ ] MCP tests pass when the extra is present.

## References

- termux/termux-packages#30705 (cryptography symbol resolution)
- Yasin-MCP issue tracking the same boundary for the MCP package family
- cryptography Termux packaging uses patchelf to add libpython NEEDED entry
