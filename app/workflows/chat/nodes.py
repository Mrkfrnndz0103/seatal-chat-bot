from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.seatalk.event_types import EVENT_NEW_MENTIONED_MESSAGE
from app.workflows.chat.state import ChatState


_llm = ChatOpenAI(
    api_key=settings.llm_api_key,
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    temperature=0.2,
)


def check_message_node(state: ChatState) -> ChatState:
    text = (state.get("incoming_text") or "").strip()
    should_reply = bool(text)

    mention = settings.bot_mention_name.strip()
    event_type = str(state.get("raw_event", {}).get("event_type", ""))
    requires_mention = event_type == EVENT_NEW_MENTIONED_MESSAGE
    if requires_mention and mention and mention != "@your-bot-name" and mention not in text:
        should_reply = False

    state["should_reply"] = should_reply
    return state


def call_model_node(state: ChatState) -> ChatState:
    history = state.get("messages", [])

    chat_messages = [SystemMessage(content=settings.llm_system_prompt)]
    for m in history:
        role = m.get("role")
        content = m.get("content", "")
        if role == "assistant":
            chat_messages.append(AIMessage(content=content))
        else:
            chat_messages.append(HumanMessage(content=content))

    chat_messages.append(HumanMessage(content=state.get("incoming_text", "")))

    response = _llm.invoke(chat_messages)
    state["reply_text"] = str(response.content)
    return state
