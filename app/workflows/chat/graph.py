from langgraph.graph import END, START, StateGraph

from app.workflows.chat.nodes import call_model_node, check_message_node
from app.workflows.chat.state import ChatState


def _route_after_check(state: ChatState) -> str:
    return "call_model" if state.get("should_reply") else "end"


def build_chat_graph():
    graph = StateGraph(ChatState)

    graph.add_node("check_message", check_message_node)
    graph.add_node("call_model", call_model_node)

    graph.add_edge(START, "check_message")
    graph.add_conditional_edges(
        "check_message",
        _route_after_check,
        {
            "call_model": "call_model",
            "end": END,
        },
    )
    graph.add_edge("call_model", END)

    return graph.compile()
