"""Test doubles — a fake Anthropic client that returns canned tool calls.

``FakeAnthropic`` stands in for ``anthropic.Anthropic`` so the real Author and
Coach nodes can be exercised — tool schema, parsing, validation, retry — with
no network and no API key. Pass it where an ``Anthropic`` client is expected
via ``cast(Anthropic, fake)``.
"""

from __future__ import annotations

from typing import Any

from anthropic.types import Message, ToolUseBlock, Usage


class FakeAnthropic:
    """A canned-response stand-in for ``anthropic.Anthropic``.

    Programmed with a queue of tool-input dicts; each ``messages.create`` call
    pops the next one and returns it as a forced ``tool_use`` response. Every
    request is recorded on ``.requests`` for assertions.
    """

    def __init__(self, tool_inputs: list[dict[str, Any]]) -> None:
        self._queue: list[dict[str, Any]] = list(tool_inputs)
        self.requests: list[dict[str, Any]] = []
        self.messages = _FakeMessages(self)


class _FakeMessages:
    """The ``.messages`` resource — just enough surface for ``generate_structured``."""

    def __init__(self, parent: FakeAnthropic) -> None:
        self._parent = parent

    def create(self, **kwargs: Any) -> Message:
        self._parent.requests.append(kwargs)
        if not self._parent._queue:
            raise AssertionError("FakeAnthropic queue exhausted — not enough canned inputs")
        tool_input = self._parent._queue.pop(0)
        tool_name = kwargs["tool_choice"]["name"]
        block = ToolUseBlock(
            type="tool_use", id="fake-tool-use", name=tool_name, input=tool_input
        )
        return Message(
            id="msg_fake",
            type="message",
            role="assistant",
            model=kwargs.get("model", "fake-model"),
            content=[block],
            stop_reason="tool_use",
            stop_sequence=None,
            usage=Usage(input_tokens=0, output_tokens=0),
        )
