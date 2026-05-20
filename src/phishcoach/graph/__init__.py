"""LangGraph StateGraph — Author → Student → Coach loop with human-in-the-loop interrupt.

Stub file. Wire up during Weekend 1.
"""

from __future__ import annotations

# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.sqlite import SqliteSaver

# from phishcoach.schemas import SessionState


# def build_graph(checkpoint_path: str = "./state/checkpoints.db"):
#     graph = StateGraph(SessionState)
#     graph.add_node("author", phishing_author_node)
#     graph.add_node("await_student", student_input_node)
#     graph.add_node("coach", coach_node)
#
#     graph.add_edge("author", "await_student")
#     graph.add_edge("await_student", "coach")
#     graph.add_conditional_edges(
#         "coach",
#         lambda s: "author" if s.round_num < s.max_rounds else END,
#     )
#     graph.set_entry_point("author")
#
#     saver = SqliteSaver.from_conn_string(checkpoint_path)
#     return graph.compile(checkpointer=saver, interrupt_before=["await_student"])


# Author / Coach / Student nodes go in phishcoach.agents
