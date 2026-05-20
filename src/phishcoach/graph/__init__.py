"""LangGraph StateGraph — the Author -> Student -> Coach training loop.

The graph compiles with ``interrupt_before=[AWAIT_STUDENT]``: execution pauses
before the student node so the CLI can collect the learner's verdict out of
band, then resumes. State is a Pydantic ``SessionState`` persisted by a
checkpointer, so the pause survives across separate ``invoke()`` calls.
"""

from __future__ import annotations

import inspect
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from phishcoach import schemas
from phishcoach.schemas import SessionState

# Node names — exported so the CLI can recognise the interrupt boundary.
AUTHOR = "author"
AWAIT_STUDENT = "await_student"
COACH = "coach"

class Node(Protocol):
    """A graph node: receives the session state, returns a partial-state update.

    Defined as a Protocol rather than a ``Callable`` alias because LangGraph's
    ``add_node`` overloads resolve their input TypeVar from a Protocol's named
    ``__call__`` but not from a bare ``Callable`` across that union of node
    protocols.
    """

    def __call__(self, state: SessionState) -> dict[str, Any]: ...

__all__ = [
    "AUTHOR",
    "AWAIT_STUDENT",
    "COACH",
    "Node",
    "await_student_node",
    "build_graph",
    "open_memory_checkpointer",
    "open_sqlite_checkpointer",
]


def _schema_serde() -> JsonPlusSerializer:
    """Build a checkpoint serializer that explicitly allows PhishCoach's types.

    LangGraph 1.x gates msgpack checkpoint deserialization behind an allowlist:
    unregistered types warn now and will be blocked in a future release. We
    register every Pydantic model and enum defined in ``phishcoach.schemas`` so
    new schemas are picked up automatically — but note an unlisted type is
    *blocked*, so all checkpointed types must live in that module.
    """
    allowed: list[type] = [
        obj
        for obj in vars(schemas).values()
        if inspect.isclass(obj)
        and obj.__module__ == schemas.__name__
        and issubclass(obj, (BaseModel, Enum))
    ]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed)


def await_student_node(state: SessionState) -> dict[str, Any]:
    """No-op boundary node for the human-in-the-loop interrupt.

    The graph is compiled with ``interrupt_before=[AWAIT_STUDENT]``, so it
    pauses *before* this node runs. The CLI writes the learner's response into
    state with ``graph.update_state(...)`` and resumes; this node then executes
    and simply hands control to the Coach. It exists only to give the interrupt
    a stable, named place to stop.
    """
    return {}


def _route_after_coach(state: SessionState) -> str:
    """Loop back to the Author until ``max_rounds`` rounds have completed."""
    return AUTHOR if state.round_num < state.max_rounds else END


def build_graph(
    *,
    author_node: Node,
    coach_node: Node,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Wire and compile the training-loop graph.

    The Author and Coach nodes are injected so the real (LLM-backed) nodes and
    the test stubs share identical wiring. ``checkpointer`` is required — the
    human-in-the-loop interrupt cannot work without persisted state.
    """
    builder = StateGraph(SessionState)
    builder.add_node(AUTHOR, author_node)
    builder.add_node(AWAIT_STUDENT, await_student_node)
    builder.add_node(COACH, coach_node)

    builder.set_entry_point(AUTHOR)
    builder.add_edge(AUTHOR, AWAIT_STUDENT)
    builder.add_edge(AWAIT_STUDENT, COACH)
    builder.add_conditional_edges(COACH, _route_after_coach, {AUTHOR: AUTHOR, END: END})

    return builder.compile(checkpointer=checkpointer, interrupt_before=[AWAIT_STUDENT])


def open_sqlite_checkpointer(db_path: str | Path) -> SqliteSaver:
    """Open a ``SqliteSaver`` on a long-lived connection.

    ``SqliteSaver.from_conn_string`` is a context manager whose connection
    closes on block exit. The CLI resumes the graph across multiple
    ``invoke()`` calls — one per human turn — so the connection must outlive
    any single call. We therefore own the connection directly, and create the
    parent directory and checkpoint tables up front.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    saver = SqliteSaver(conn, serde=_schema_serde())
    saver.setup()
    return saver


def open_memory_checkpointer() -> MemorySaver:
    """In-memory checkpointer with the schema allowlist — for tests and smoke runs."""
    return MemorySaver(serde=_schema_serde())
