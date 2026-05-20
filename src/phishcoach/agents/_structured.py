"""Shared helper: call Claude with a forced tool and parse the result.

Both the Author and the Coach produce a single Pydantic object per turn via
Anthropic tool use. This module holds the one call path they share — not an
agent base class, just the function that removes the duplication.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from anthropic import Anthropic
from anthropic.types import Message, ToolParam
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def build_tool_schema(model: type[BaseModel], *, exclude: set[str]) -> dict[str, Any]:
    """JSON Schema for ``model`` usable as an Anthropic tool ``input_schema``.

    ``exclude``d top-level fields are dropped — those are filled by the node
    itself, so the model neither sees nor sets them.
    """
    schema = model.model_json_schema()
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for field in exclude:
        properties.pop(field, None)
        if field in required:
            required.remove(field)
    return schema


def _extract_tool_input(response: Message, tool_name: str) -> dict[str, Any]:
    """Pull the forced tool call's input dict out of a response."""
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            if not isinstance(block.input, dict):
                raise RuntimeError(f"tool {tool_name!r} input was not an object")
            return cast(dict[str, Any], block.input)
    raise RuntimeError(
        f"model did not call tool {tool_name!r} (stop_reason={response.stop_reason})"
    )


def generate_structured(
    client: Anthropic,
    *,
    model: str,
    system: str,
    user_content: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict[str, Any],
    build: Callable[[dict[str, Any]], T],
    max_tokens: int,
    max_attempts: int = 2,
) -> T:
    """Call Claude, forcing a single ``tool_name`` call, and build a ``T`` from it.

    ``build`` turns the raw tool input into a validated Pydantic object — it may
    inject node-controlled fields. If ``build`` raises ``ValidationError`` the
    call is retried with the error fed back, up to ``max_attempts`` times.
    """
    tool = cast(
        ToolParam,
        {
            "name": tool_name,
            "description": tool_description,
            "input_schema": input_schema,
        },
    )
    last_error: ValidationError | None = None
    for attempt in range(max_attempts):
        content = user_content
        if attempt > 0 and last_error is not None:
            content = (
                f"{user_content}\n\nYour previous tool call failed validation:\n"
                f"{last_error}\n\nCall {tool_name} again with corrected input."
            )
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )
        tool_input = _extract_tool_input(response, tool_name)
        try:
            return build(tool_input)
        except ValidationError as exc:
            last_error = exc
    raise RuntimeError(
        f"tool {tool_name!r} input failed validation after {max_attempts} attempts"
    ) from last_error
