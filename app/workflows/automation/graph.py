from langgraph.graph import END, START, StateGraph

from app.workflows.automation.nodes import (
    noop_node,
    route_event_node,
    send_group_text_node,
    send_single_text_node,
    set_typing_node,
)
from app.workflows.automation.state import AutomationState


def _route_action(state: AutomationState) -> str:
    return str(state.get("action", "noop") or "noop")


def build_automation_graph():
    graph = StateGraph(AutomationState)

    graph.add_node("route_event", route_event_node)
    graph.add_node("noop", noop_node)
    graph.add_node("set_typing", set_typing_node)
    graph.add_node("send_group_text", send_group_text_node)
    graph.add_node("send_single_text", send_single_text_node)

    graph.add_edge(START, "route_event")
    graph.add_conditional_edges(
        "route_event",
        _route_action,
        {
            "noop": "noop",
            "set_typing": "set_typing",
            "send_group_text": "send_group_text",
            "send_single_text": "send_single_text",
        },
    )

    graph.add_edge("noop", END)
    graph.add_edge("set_typing", END)
    graph.add_edge("send_group_text", END)
    graph.add_edge("send_single_text", END)

    return graph.compile()
