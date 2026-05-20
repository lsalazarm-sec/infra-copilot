"""JSONL audit log for every tool invocation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from infra_copilot.config import AUDIT_LOG


def record(
    *,
    tool: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any] | str | None,
    success: bool,
    duration_ms: float,
    audit_path: Path = AUDIT_LOG,
) -> None:
    """Append a single tool invocation to the audit log (JSONL)."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "tool": tool,
        "inputs": inputs,
        "outputs": outputs,
        "success": success,
        "duration_ms": round(duration_ms, 2),
    }
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
