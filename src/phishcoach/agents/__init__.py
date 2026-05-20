"""Agent nodes — the LLM-backed Author and Coach LangGraph nodes."""

from __future__ import annotations

from phishcoach.agents.author import DEFAULT_AUTHOR_MODEL, make_author_node

__all__ = ["DEFAULT_AUTHOR_MODEL", "make_author_node"]
