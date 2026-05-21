"""Main agent using ReAct pattern with manual tool dispatch."""

from __future__ import annotations

import json
import logging
import re

import httpx

from infra_copilot.config import Settings
from infra_copilot.tools.kubectl import kubectl_run
from infra_copilot.tools.shell import shell_run

logging.getLogger("httpx").setLevel(logging.WARNING)

SYSTEM_PROMPT = """You are infra-copilot, a senior SRE and sysadmin assistant.

You have access to these tools:

TOOL: kubectl
  verb: string (get, describe, logs, top, explain, version)
  args: list of strings

TOOL: shell
  binary: string (journalctl, systemctl, ps, ss, df, free, uptime, ip)
  args: list of strings

STRICT OUTPUT RULES:
- If you need a tool, output ONLY the JSON on its own line. No intro, no explanation.
- If you have enough information, respond conversationally in markdown. Adapt your answer to the question:
  - For listing resources: brief intro sentence, then bullet points with status and one-line explanation.
  - For diagnosing problems: explain what you found, why it's happening, and one concrete next step.
  - For system stats (disk, memory, cpu): summarize the key numbers and flag anything concerning.
  - Always end with a one-sentence conclusion or recommendation.
- Keep code blocks and YAML short (under 10 lines). Omit repetitive or irrelevant fields.
- Never mix JSON and text in the same response.

Tool call examples (output exactly like this, nothing else):
{"tool": "kubectl", "verb": "get", "args": ["pods", "-n", "default"]}
{"tool": "shell", "binary": "df", "args": ["-h"]}
"""


async def _call_ollama(messages: list[dict], settings: Settings) -> str:
    async with httpx.AsyncClient(timeout=settings.llm.timeout_seconds) as client:
        response = await client.post(
            f"{settings.llm.base_url}/api/chat",
            json={
                "model": settings.llm.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


def _parse_tool_call(text: str) -> dict | None:
    """Extract a JSON tool call from anywhere in the model response."""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass

    match = re.search(r'(\{[^{}]*"tool"[^{}]*\})', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass

    return None


async def ask(prompt: str, settings: Settings) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    max_iterations = 8
    last_response = ""

    for iteration in range(max_iterations):
        response = await _call_ollama(messages, settings)
        last_response = response
        messages.append({"role": "assistant", "content": response})

        tool_call = _parse_tool_call(response)

        if tool_call is None:
            return response

        tool_name = tool_call.get("tool")

        if tool_name == "kubectl":
            result = await kubectl_run(
                verb=tool_call.get("verb", "get"),
                args=tool_call.get("args", []),
                settings=settings,
            )
            tool_output = result.model_dump_json(indent=2)

        elif tool_name == "shell":
            result = await shell_run(
                binary=tool_call.get("binary", ""),
                args=tool_call.get("args", []),
                settings=settings,
            )
            tool_output = result.model_dump_json(indent=2)

        else:
            tool_output = json.dumps({"error": f"Unknown tool: {tool_name}"})

        if iteration == max_iterations - 2:
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool output:\n{tool_output}\n\nNow write your final answer in markdown bullet points. Do not call any more tools.",
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool output:\n{tool_output}",
                }
            )

    return last_response
