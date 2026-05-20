"""Smoke test for the LangGraph wiring — no real LLM calls.

Runs the Author -> await_student -> Coach loop with stub nodes that return
canned data, exercising the interrupt/resume cycle and the loop-back edge.
Run from the repo root:

    python scripts/smoke_graph.py
"""

from __future__ import annotations

from typing import Any

from phishcoach.graph import AWAIT_STUDENT, build_graph, open_memory_checkpointer
from phishcoach.schemas import (
    ArtifactGen,
    AttackCategory,
    CoachAnalysis,
    ConfidenceEntry,
    PersonaProfile,
    RoundResult,
    SessionState,
    StudentResponse,
    Tell,
)

THREAD_ID = "smoke-1"


def stub_author(state: SessionState) -> dict[str, Any]:
    """Canned Author: emit a fixed phishing artifact, no LLM call."""
    next_round = state.round_num + 1
    tell = Tell(
        category=AttackCategory.URGENCY_SCARCITY,
        marker="within 24 hours",
        explanation="A manufactured deadline pressures a fast, unverified click.",
    )
    artifact = ArtifactGen(
        artifact_type="email",
        category=AttackCategory.URGENCY_SCARCITY,
        sender="IT Help Desk <no-reply@it-portal.school-sim.example>",
        subject=f"[Round {next_round}] Account verification required",
        body="Your account will be locked within 24 hours unless you verify now.",
        tells=[tell],
        difficulty=2,
        targeting_rationale="Stub artifact — smoke test only.",
    )
    return {"current_artifact": artifact}


def stub_coach(state: SessionState) -> dict[str, Any]:
    """Canned Coach: deterministic round bookkeeping, no LLM teaching call."""
    artifact = state.current_artifact
    response = state.current_response
    assert artifact is not None and response is not None  # guaranteed by graph order

    correct = (response.verdict == "phish") == artifact.is_phish

    # Minimal inline weakness update — the real reducer arrives in step 6.
    weakness = state.weakness_model.model_copy(deep=True)
    weakness.stats[artifact.category].confidence_log.append(
        ConfidenceEntry(confidence=response.confidence, correct=correct)
    )

    analysis = CoachAnalysis(
        student_correct=correct,
        missed_tells=[] if response.flagged_tells else list(artifact.tells),
        reasoning_strengths=["Stub strength."],
        reasoning_weaknesses=[] if correct else ["Stub weakness."],
        coaching_message="Stub coaching message — smoke test only.",
    )
    completed = state.round_num + 1
    round_result = RoundResult(
        round_num=completed,
        artifact=artifact,
        response=response,
        coach_analysis=analysis,
    )
    return {
        "round_history": [*state.round_history, round_result],
        "weakness_model": weakness,
        "round_num": completed,
        "current_artifact": None,
        "current_response": None,
    }


def main() -> None:
    rounds = 2
    graph = build_graph(
        author_node=stub_author,
        coach_node=stub_coach,
        checkpointer=open_memory_checkpointer(),
    )
    config: dict[str, Any] = {"configurable": {"thread_id": THREAD_ID}}
    initial = SessionState(
        student_persona=PersonaProfile(
            raw_description="CS undergrad at a fictional university"
        ),
        max_rounds=rounds,
    )

    print(f"Compiled graph nodes: {sorted(graph.nodes)}")
    print(f"Running {rounds} stub rounds on thread '{THREAD_ID}'\n")

    # First invoke runs the Author, then pauses before await_student.
    graph.invoke(initial, config)

    for _ in range(rounds):
        snap = graph.get_state(config)
        assert snap.next == (AWAIT_STUDENT,), f"expected interrupt, got next={snap.next}"
        state = SessionState.model_validate(snap.values)
        artifact = state.current_artifact
        assert artifact is not None
        print(f"--- interrupt before round {state.round_num + 1} ---")
        print(f"  artifact: {artifact.subject}")

        # What the CLI does: capture the learner's verdict, write it, resume.
        response = StudentResponse(
            verdict="phish",
            confidence=4,
            reasoning="Manufactured 24-hour deadline; generic sender.",
            flagged_tells=["within 24 hours"],
        )
        graph.update_state(config, {"current_response": response})
        graph.invoke(None, config)

    snap = graph.get_state(config)
    final = SessionState.model_validate(snap.values)
    print(f"\n--- graph finished (next={snap.next or 'END'}) ---")
    print(f"  completed rounds : {final.round_num}")
    print(f"  round_history len: {len(final.round_history)}")
    stat = final.weakness_model.stats[AttackCategory.URGENCY_SCARCITY]
    print(f"  urgency_scarcity : seen={stat.seen} caught={stat.caught} "
          f"catch_rate={stat.catch_rate}")

    assert final.round_num == rounds
    assert len(final.round_history) == rounds
    print("\nOK: interrupt/resume + loop-back wiring works.")


if __name__ == "__main__":
    main()
