"""Pydantic schemas — graph state, agent I/O, scenarios.

Stub file. Fill in during Weekend 1. Locked schemas before any agent code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- Persona & weakness model ---------------------------------------------


class PersonaProfile(BaseModel):
    """Learner's role-played persona. Session-scoped fiction, no real PII."""

    # TODO Weekend 1
    ...


class WeaknessModel(BaseModel):
    """Per-learner detection-skill map, updated by Coach each round."""

    # TODO Weekend 1: category -> {seen, caught, missed, confidence_calibration}
    ...


# --- Artifact generation --------------------------------------------------


class Tell(BaseModel):
    """A specific red flag inside an artifact. Hidden from learner until reveal."""

    # TODO Weekend 1
    ...


class ArtifactGen(BaseModel):
    """What the Phishing Author produces each round."""

    artifact_type: Literal["email", "sms", "dm", "oauth_screen"]
    # TODO Weekend 1
    ...


# --- Student response & coach analysis ------------------------------------


class StudentResponse(BaseModel):
    verdict: Literal["phish", "legit"]
    confidence: int = Field(ge=1, le=5)
    reasoning: str
    flagged_tells: list[str] = Field(default_factory=list)


class CoachAnalysis(BaseModel):
    student_correct: bool
    missed_tells: list[Tell] = Field(default_factory=list)
    reasoning_strengths: list[str] = Field(default_factory=list)
    reasoning_weaknesses: list[str] = Field(default_factory=list)
    # TODO Weekend 1: updated_weakness_model: WeaknessModel


# --- Round + session ------------------------------------------------------


class RoundResult(BaseModel):
    round_num: int
    artifact: ArtifactGen
    response: StudentResponse | None = None
    coach_analysis: CoachAnalysis | None = None


class SessionState(BaseModel):
    """LangGraph state. Lives in the SQLite checkpointer between rounds."""

    student_persona: PersonaProfile
    weakness_model: WeaknessModel
    round_history: list[RoundResult] = Field(default_factory=list)
    current_artifact: ArtifactGen | None = None
    current_response: StudentResponse | None = None
    round_num: int = 0
    max_rounds: int = 8
