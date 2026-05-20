"""Eyeball test for the Author node — one real Anthropic call.

Requires ANTHROPIC_API_KEY (loaded from .env). Run from the repo root:

    .venv/bin/python scripts/try_author.py
    .venv/bin/python scripts/try_author.py --persona "high-school senior applying to colleges"
"""

from __future__ import annotations

import argparse
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from phishcoach.agents import DEFAULT_AUTHOR_MODEL, make_author_node
from phishcoach.schemas import PersonaProfile, SessionState


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate one artifact with the Author node.")
    parser.add_argument("--persona", default="CS undergrad at a fictional university")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set — add it to .env and retry.")

    model = os.getenv("AUTHOR_MODEL", DEFAULT_AUTHOR_MODEL)
    node = make_author_node(Anthropic(), model=model)
    state = SessionState(
        student_persona=PersonaProfile(raw_description=args.persona),
        max_rounds=5,
    )

    print(f"Calling Author ({model}) for persona: {args.persona!r}\n")
    artifact = node(state)["current_artifact"]
    assert artifact is not None

    print("=" * 70)
    print("LEARNER-FACING ARTIFACT")
    print("=" * 70)
    print(f"type   : {artifact.artifact_type}")
    print(f"sender : {artifact.sender}")
    if artifact.subject is not None:
        print(f"subject: {artifact.subject}")
    print(f"\n{artifact.body}\n")

    print("=" * 70)
    print(f"REVEAL (hidden from learner)  —  category={artifact.category.value}  "
          f"difficulty={artifact.difficulty}/5")
    print("=" * 70)
    for i, tell in enumerate(artifact.tells, 1):
        print(f"tell {i} [{tell.category.value}]: {tell.marker!r}")
        print(f"        {tell.explanation}")
    print(f"\ntargeting rationale: {artifact.targeting_rationale}")


if __name__ == "__main__":
    main()
