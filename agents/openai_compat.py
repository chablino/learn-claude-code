"""
openai_compat.py - OpenAI-compatible wrapper that mimics the Anthropic client API.

Translates Anthropic-style calls:
    client.messages.create(model=..., system=..., messages=..., tools=..., max_tokens=...)

into OpenAI chat completions, and wraps the response so existing code using:
    response.content, response.stop_reason,
    block.type, block.id, block.name, block.input, block.text
continues to work without modification.

Configure via environment variables:
    OPENROUTER_API_KEY   API key (also accepts OPENAI_API_KEY as fallback)
    OPENAI_BASE_URL      Base URL override (default: https://openrouter.ai/api/v1)
    MODEL_ID             Model to use
"""

import json
import os

from openai import OpenAI as _OpenAI

# ---------------------------------------------------------------------------
# Synthetic response objects that mirror Anthropic SDK types
# ---------------------------------------------------------------------------


class TextBlock:
    """Mirrors anthropic.types.TextBlock."""

    def __init__(self, text: str):
        self.type = "text"
        self.text = text

    def __repr__(self):
        return f"TextBlock(text={self.text!r})"


class ToolUseBlock:
    """Mirrors anthropic.types.ToolUseBlock."""

    def __init__(self, id: str, name: str, input_dict: dict):
        self.type = "tool_use"
        self.id = id
        self.name = name
        self.input = input_dict

    def __repr__(self):
        return f"ToolUseBlock(name={self.name!r}, id={self.id!r})"


class AnthropicResponse:
    """Mirrors the top-level Anthropic messages.create() response."""

    def __init__(self, content: list, stop_reason: str):
        self.content = content
        self.stop_reason = stop_reason


# ---------------------------------------------------------------------------
# Format converters: Anthropic history <-> OpenAI messages list
# ---------------------------------------------------------------------------


def _to_oai_tools(anthropic_tools: list) -> list:
    """Convert Anthropic tool definitions to OpenAI function-calling format."""
    result = []
    for t in anthropic_tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
        )
    return result


def _to_oai_messages(system: str | None, messages: list) -> list:
    """
    Convert Anthropic-style message history to OpenAI messages format.

    Anthropic uses:
      {"role": "assistant", "content": [TextBlock, ToolUseBlock, ...]}
      {"role": "user",      "content": [{"type": "tool_result", "tool_use_id": ..., "content": ...}]}

    OpenAI uses:
      {"role": "assistant", "content": "...", "tool_calls": [...]}
      {"role": "tool",      "tool_call_id": ..., "content": "..."}  (one per result)
    """
    oai = []
    if system:
        oai.append({"role": "system", "content": system})

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "assistant":
            if isinstance(content, list):
                texts = [
                    b.text
                    for b in content
                    if getattr(b, "type", None) == "text"
                ]
                tool_calls = []
                for b in content:
                    if getattr(b, "type", None) == "tool_use":
                        tool_calls.append(
                            {
                                "id": b.id,
                                "type": "function",
                                "function": {
                                    "name": b.name,
                                    "arguments": json.dumps(b.input),
                                },
                            }
                        )
                oai_msg: dict = {
                    "role": "assistant",
                    "content": "\n".join(texts) if texts else None,
                }
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                oai.append(oai_msg)
            else:
                oai.append({"role": "assistant", "content": content})

        elif role == "user":
            if isinstance(content, list):
                # Tool results
                if (
                    content
                    and isinstance(content[0], dict)
                    and content[0].get("type") == "tool_result"
                ):
                    for tr in content:
                        raw = tr.get("content", "")
                        oai.append(
                            {
                                "role": "tool",
                                "tool_call_id": tr["tool_use_id"],
                                "content": (
                                    raw
                                    if isinstance(raw, str)
                                    else json.dumps(raw)
                                ),
                            }
                        )
                else:
                    texts = []
                    for part in content:
                        if isinstance(part, dict):
                            texts.append(part.get("text", ""))
                        else:
                            texts.append(str(part))
                    oai.append({"role": "user", "content": "\n".join(texts)})
            else:
                oai.append({"role": "user", "content": content})

        else:
            oai.append({"role": role, "content": content})

    return oai


# ---------------------------------------------------------------------------
# The compatibility client
# ---------------------------------------------------------------------------


class _Messages:
    """Drop-in for the Anthropic `client.messages` namespace."""

    def __init__(self, openai_client: _OpenAI):
        self._client = openai_client

    def create(
        self,
        *,
        model: str,
        messages: list,
        max_tokens: int = 8000,
        system: str | None = None,
        tools: list | None = None,
        **kwargs,
    ) -> AnthropicResponse:
        oai_messages = _to_oai_messages(system, messages)
        call_kwargs: dict = {
            "model": model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            call_kwargs["tools"] = _to_oai_tools(tools)

        resp = self._client.chat.completions.create(**call_kwargs)
        choice = resp.choices[0]
        msg = choice.message

        # Build Anthropic-style content block list
        blocks: list = []
        if msg.content:
            blocks.append(TextBlock(msg.content))
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    input_dict = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    input_dict = {}
                blocks.append(
                    ToolUseBlock(tc.id, tc.function.name, input_dict)
                )

        # Map OpenAI finish_reason -> Anthropic stop_reason
        finish = choice.finish_reason
        if finish == "tool_calls":
            stop_reason = "tool_use"
        elif finish == "stop":
            stop_reason = "end_turn"
        else:
            stop_reason = finish or "end_turn"

        return AnthropicResponse(blocks, stop_reason)


class Anthropic:
    """
    Drop-in replacement for `anthropic.Anthropic`.

    Usage (identical to before):
        client = Anthropic()
        response = client.messages.create(model=..., system=..., messages=...,
                                          tools=..., max_tokens=8000)
    """

    def __init__(
        self, base_url: str | None = None, api_key: str | None = None
    ):
        resolved_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or os.getenv("ANTHROPIC_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
        resolved_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "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"
        )
        self._oai = _OpenAI(base_url=resolved_url, api_key=resolved_key)
        self.messages = _Messages(self._oai)
