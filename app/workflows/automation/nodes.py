from app.config import settings
from app.seatalk.event_types import (
    EVENT_BOT_ADDED_TO_GROUP,
    EVENT_INTERACTIVE_CLICK,
    EVENT_USER_ENTER_CHATROOM,
    MESSAGE_EVENT_TYPES,
)
from app.workflows.automation.state import AutomationState


def route_event_node(state: AutomationState) -> AutomationState:
    payload = state.get("payload", {})
    event = payload.get("event", {})
    event_type = state.get("event_type", "")

    state["action"] = "noop"
    state["group_id"] = ""
    state["employee_code"] = ""
    state["thread_id"] = ""
    state["response_text"] = ""

    if event_type in MESSAGE_EVENT_TYPES and settings.bot_send_typing_status:
        group_id = str(event.get("group_id", "") or "")
        thread_id = str(event.get("message", {}).get("thread_id", "") or "")
        if group_id:
            state["action"] = "set_typing"
            state["group_id"] = group_id
            state["thread_id"] = thread_id
            return state

    if event_type == EVENT_BOT_ADDED_TO_GROUP and settings.bot_send_group_welcome:
        group_id = str(event.get("group", {}).get("group_id", "") or "")
        if group_id:
            state["action"] = "send_group_text"
            state["group_id"] = group_id
            state["response_text"] = settings.bot_group_welcome_text
            return state

    if event_type == EVENT_USER_ENTER_CHATROOM and settings.bot_send_user_welcome:
        employee_code = str(event.get("employee_code", "") or "")
        if employee_code:
            state["action"] = "send_single_text"
            state["employee_code"] = employee_code
            state["response_text"] = settings.bot_user_welcome_text
            return state

    if event_type == EVENT_INTERACTIVE_CLICK:
        callback_value = str(event.get("value", "") or "").strip()
        if not callback_value:
            return state

        group_id = str(event.get("group_id", "") or "")
        thread_id = str(event.get("thread_id", "") or "")
        employee_code = str(event.get("employee_code", "") or "")
        message = f"Action received: {callback_value}"

        if group_id:
            state["action"] = "send_group_text"
            state["group_id"] = group_id
            state["thread_id"] = thread_id
            state["response_text"] = message
            return state

        if employee_code:
            state["action"] = "send_single_text"
            state["employee_code"] = employee_code
            state["thread_id"] = thread_id
            state["response_text"] = message

    return state


def noop_node(state: AutomationState) -> AutomationState:
    return state


def set_typing_node(state: AutomationState) -> AutomationState:
    seatalk_client = state["seatalk_client"]
    group_id = state.get("group_id", "")
    thread_id = state.get("thread_id", "")
    if group_id:
        seatalk_client.set_group_typing_status(group_id=group_id, thread_id=thread_id)
    return state


def send_group_text_node(state: AutomationState) -> AutomationState:
    seatalk_client = state["seatalk_client"]
    group_id = state.get("group_id", "")
    text = state.get("response_text", "")
    thread_id = state.get("thread_id", "")
    if group_id and text:
        seatalk_client.send_group_text(group_id=group_id, content=text, thread_id=thread_id)
    return state


def send_single_text_node(state: AutomationState) -> AutomationState:
    seatalk_client = state["seatalk_client"]
    employee_code = state.get("employee_code", "")
    text = state.get("response_text", "")
    thread_id = state.get("thread_id", "")
    if employee_code and text:
        seatalk_client.send_single_text(employee_code=employee_code, content=text, thread_id=thread_id)
    return state
