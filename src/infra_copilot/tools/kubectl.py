"""kubectl wrapper exposed as an agent tool."""

from __future__ import annotations

import asyncio
import shutil
import time
from typing import Annotated

from pydantic import BaseModel, Field

from infra_copilot.audit import record
from infra_copilot.config import Settings

MAX_OUTPUT_CHARS = 8000


class KubectlResult(BaseModel):
    command: str
    stdout: str
    stderr: str
    return_code: int
    truncated: bool = False


class KubectlBlocked(BaseModel):
    reason: str
    attempted_command: str


async def kubectl_run(
    verb: Annotated[str, Field(description="kubectl verb e.g. 'get', 'describe', 'logs'")],
    args: Annotated[list[str], Field(description="Remaining args e.g. ['pods', '-n', 'default']")],
    settings: Settings,
) -> KubectlResult | KubectlBlocked:
    """Run a safe allowlisted kubectl command."""
    full_cmd = ["kubectl", verb, *args]
    cmd_str = " ".join(full_cmd)

    if verb not in settings.safety.kubectl_allowed_verbs:
        result = KubectlBlocked(
            reason=f"Verb '{verb}' not in allowlist {settings.safety.kubectl_allowed_verbs}.",
            attempted_command=cmd_str,
        )
        record(
            tool="kubectl",
            inputs={"verb": verb, "args": args},
            outputs=result.model_dump(),
            success=False,
            duration_ms=0,
        )
        return result

    if not shutil.which("kubectl"):
        return KubectlBlocked(reason="kubectl not found in PATH", attempted_command=cmd_str)

    start = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        *full_cmd,
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

    result_ok = KubectlResult(
        command=cmd_str,
        stdout=stdout,
        stderr=stderr,
        return_code=proc.returncode or 0,
        truncated=truncated,
    )
    record(
        tool="kubectl",
        inputs={"verb": verb, "args": args},
        outputs={"return_code": result_ok.return_code},
        success=result_ok.return_code == 0,
        duration_ms=duration_ms,
    )
    return result_ok
