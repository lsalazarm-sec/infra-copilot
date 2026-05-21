"""Generic shell command runner with strict allowlist."""

from __future__ import annotations

import asyncio
import shutil
import time
from typing import Annotated

from pydantic import BaseModel, Field

from infra_copilot.audit import record
from infra_copilot.config import Settings

MAX_OUTPUT_CHARS = 8000


class ShellResult(BaseModel):
    command: str
    stdout: str
    stderr: str
    return_code: int
    truncated: bool = False


class ShellBlocked(BaseModel):
    reason: str
    attempted_command: str


async def shell_run(
    binary: Annotated[
        str, Field(description="Binary name e.g. 'journalctl'. Must be in allowlist.")
    ],
    args: Annotated[list[str], Field(description="Arguments to pass to the binary.")],
    settings: Settings,
) -> ShellResult | ShellBlocked:
    """Run a safe allowlisted shell binary."""
    cmd_str = " ".join([binary, *args])

    if binary not in settings.safety.shell_allowed_cmds:
        return ShellBlocked(
            reason=f"Binary '{binary}' not in allowlist {settings.safety.shell_allowed_cmds}.",
            attempted_command=cmd_str,
        )

    if not shutil.which(binary):
        return ShellBlocked(
            reason=f"Binary '{binary}' not found in PATH", attempted_command=cmd_str
        )

    start = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        binary,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    duration_ms = (time.perf_counter() - start) * 1000

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    truncated = False

    if len(stdout) > MAX_OUTPUT_CHARS:
        stdout = stdout[:MAX_OUTPUT_CHARS] + "\n... [TRUNCATED]"
        truncated = True

    result = ShellResult(
        command=cmd_str,
        stdout=stdout,
        stderr=stderr,
        return_code=proc.returncode or 0,
        truncated=truncated,
    )
    record(
        tool="shell",
        inputs={"binary": binary, "args": args},
        outputs={"return_code": result.return_code},
        success=result.return_code == 0,
        duration_ms=duration_ms,
    )
    return result
