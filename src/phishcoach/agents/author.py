"""The Phishing Author node — generates one targeted artifact per round."""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from phishcoach.agents._structured import build_tool_schema, generate_structured
from phishcoach.graph import Node
from phishcoach.prompts import AUTHOR_SYSTEM_PROMPT
from phishcoach.schemas import (
    WEEKEND_1_CATEGORIES,
    ArtifactGen,
    AttackCategory,
    SessionState,
    WeaknessModel,
)

DEFAULT_AUTHOR_MODEL = "claude-sonnet-4-6"

_MAX_TOKENS = 4096
_TOOL_NAME = "emit_artifact"
_TOOL_DESCRIPTION = (
    "Return the simulated phishing artifact for this round, with its planted "
    "tells and targeting rationale."
)
# ArtifactGen fields the node fills itself — kept out of the tool schema so the
# model cannot drift the round's category or flip the ground-truth label.
_NODE_CONTROLLED = {"category", "is_phish"}
# In-scope categories in canonical (enum) order, for stable rendering.
_IN_SCOPE = tuple(c for c in AttackCategory if c in WEEKEND_1_CATEGORIES)


def make_author_node(client: Anthropic, *, model: str = DEFAULT_AUTHOR_MODEL) -> Node:
    """Build the Author graph node, bound to an Anthropic client.

    The node picks the learner's weakest in-scope category, briefs the model on
    the persona and weakness map, and returns a validated ``ArtifactGen`` in
    that category as ``current_artifact``.
    """
    input_schema = build_tool_schema(ArtifactGen, exclude=_NODE_CONTROLLED)

    def author_node(state: SessionState) -> dict[str, Any]:
        target = state.weakness_model.weakest_category(WEEKEND_1_CATEGORIES)

        def build(tool_input: dict[str, Any]) -> ArtifactGen:
            # Stamp the node-controlled fields ourselves; drop any echoed back.
            for field in _NODE_CONTROLLED:
                tool_input.pop(field, None)
            return ArtifactGen(**tool_input, category=target, is_phish=True)

        artifact = generate_structured(
            client,
            model=model,
            system=AUTHOR_SYSTEM_PROMPT,
            user_content=_render_brief(state, target),
            tool_name=_TOOL_NAME,
            tool_description=_TOOL_DESCRIPTION,
            input_schema=input_schema,
            build=build,
            max_tokens=_MAX_TOKENS,
        )
        return {"current_artifact": artifact}

    return author_node


def _render_brief(state: SessionState, target: AttackCategory) -> str:
    """The per-round user message: persona + weakness map + target category."""
    return "\n".join(
        [
            f"ROUND {state.round_num + 1} of {state.max_rounds}",
            "",
            "LEARNER PERSONA",
            state.student_persona.raw_description,
            "",
            "WEAKNESS MODEL — what this learner catches vs. misses so far",
            _render_weakness(state.weakness_model),
            "",
            f"TARGET CATEGORY: {target.value}",
            "Generate one phishing artifact in the target category, tuned to the "
            "persona and the weakness model above.",
        ]
    )


def _render_weakness(model: WeaknessModel) -> str:
    """One line per in-scope category — the Author's view of learner skill."""
    rows: list[str] = []
    for category in _IN_SCOPE:
        stat = model.stats[category]
        if stat.seen == 0:
            rows.append(f"- {category.value}: not yet seen")
            continue
        mcw = stat.mean_confidence_when_wrong
        calibration = "" if mcw is None else f"; mean confidence when wrong {mcw:.1f}/5"
        rows.append(
            f"- {category.value}: seen {stat.seen}, "
            f"caught {stat.caught} ({stat.catch_rate:.0%}){calibration}"
        )
    return "\n".join(rows)
