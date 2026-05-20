"""Agent system prompts.

Prompts live in sibling ``.md`` files and are loaded here as strings. Keeping
the prose out of Python makes it cheap to iterate on wording without touching
code or re-reading diffs full of escaped newlines.
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def _load(filename: str) -> str:
    """Read a prompt file from this package directory as a stripped string."""
    return (_PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


AUTHOR_SYSTEM_PROMPT: str = _load("author_system.md")
COACH_SYSTEM_PROMPT: str = _load("coach_system.md")

__all__ = ["AUTHOR_SYSTEM_PROMPT", "COACH_SYSTEM_PROMPT"]
