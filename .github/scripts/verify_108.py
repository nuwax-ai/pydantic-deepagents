"""Manual verification for issue #108 — Windows execute crash.

Runs on a Windows GitHub Actions runner to confirm that `LocalBackend.execute()`
and `LocalBackend.async_execute()` work after bumping the `pydantic-ai-backend`
floor to `>=0.2.7`. Exercises the exact failure mode from the issue:
deleting a folder via `powershell -Command "Remove-Item ..."`.

Delete this file (and `.github/workflows/verify-108.yml`) after the issue is
confirmed fixed on Windows.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

from pydantic_ai_backends import LocalBackend


def _section(title: str) -> None:
    print(f"\n--- {title} ---", flush=True)


def main() -> int:
    print(f"platform: {sys.platform}", flush=True)
    print(f"python: {sys.version}", flush=True)

    tmp = tempfile.mkdtemp(prefix="verify_108_")
    backend = LocalBackend(root_dir=tmp)
    print(f"tmp root: {tmp}", flush=True)

    # 1) Smoke test: plain `dir` via the wrapper. If this fails with WinError 2,
    #    the shell wrapper itself isn't spawning — the original #108 symptom.
    _section("backend.execute('dir')")
    r = backend.execute("dir")
    print(f"exit_code: {r.exit_code}")
    print(f"output (first 200): {r.output[:200]!r}")
    assert r.exit_code == 0, f"plain dir failed with exit_code={r.exit_code}"

    # 2) The exact #108 scenario: PowerShell folder deletion via execute().
    target = os.path.join(tmp, "bozo")
    os.makedirs(target)
    assert os.path.exists(target)

    _section(f"backend.execute(powershell Remove-Item on {target})")
    # Single quotes around the path are literal in PowerShell — no escaping
    # headaches across the cmd /c → powershell boundary.
    cmd = f"powershell -Command \"Remove-Item -Recurse -Force '{target}'\""
    r = backend.execute(cmd)
    print(f"exit_code: {r.exit_code}")
    print(f"output: {r.output!r}")
    assert not os.path.exists(target), f"folder still exists after execute: {target}"

    # 3) Same scenario but through the new async path added in 0.2.7.
    target2 = os.path.join(tmp, "bozo2")
    os.makedirs(target2)

    _section(f"backend.async_execute(powershell Remove-Item on {target2})")
    cmd2 = f"powershell -Command \"Remove-Item -Recurse -Force '{target2}'\""
    r = asyncio.run(backend.async_execute(cmd2))
    print(f"exit_code: {r.exit_code}")
    print(f"output: {r.output!r}")
    assert not os.path.exists(target2), f"folder still exists after async_execute: {target2}"

    print("\nAll Windows execute checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
