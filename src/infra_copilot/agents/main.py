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

To use a tool, respond ONLY with valid JSON in this exact format:
{"tool": "kubectl", "verb": "get", "args": ["pods", "-n", "kube-system"]}
{"tool": "shell", "binary": "df", "args": ["-h"]}

After receiving tool output, reason about it and give a final answer.
When you have enough information, respond with plain markdown — no JSON.

Rules:
- Always gather evidence with tools before answering.
- Be concise. Explain WHY based on actual output.
- Never fabricate command output.
- Mark any suggested fixes clearly as suggestions.
"""


async def _call_ollama(messages: list[dict], settings: Settings) -> str:
    """Call Ollama chat API and return the assistant message content."""
    async with httpx.AsyncClient(timeout=settings.llm.timeout_seconds) as client:
        response = await client.post(
            f"{settings.llm.base_url}/api/chat",
            json={
                "model": settings.llm.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": settings.llm.temperature},
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


def _parse_tool_call(text: str) -> dict | None:
    """Extract a JSON tool call from the model response if present."""
    text = text.strip()
    # Try direct JSON parse first
    try:
        data = json.loads(text)
        if "tool" in data:
            return data
    except json.JSONDecodeError:
        pass
    # Try extracting JSON from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass
    return None


async def ask(prompt: str, settings: Settings) -> str:
    """Run a ReAct loop: model decides tool → we execute → model reasons → repeat."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    max_iterations = 6
    for _ in range(max_iterations):
        response = await _call_ollama(messages, settings)
        messages.append({"role": "assistant", "content": response})

        tool_call = _parse_tool_call(response)
        if tool_call is None:
            # No tool call — this is the final answer
            return response

        # Execute the tool
        tool_name = tool_call.get("tool")
        tool_output: str

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

        messages.append({"role": "user", "content": f"Tool output:\n{tool_output}"})

    return "Reached maximum iterations without a final answer."
