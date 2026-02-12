from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    seatalk_app_id: str = ""
    seatalk_app_secret: str = ""
    seatalk_auth_url: str = "https://openapi.seatalk.io/auth/app_access_token"
    seatalk_api_base_url: str = "https://openapi.seatalk.io"
    seatalk_group_message_path: str = "/messaging/v2/group_chat"
    seatalk_single_message_path: str = "/messaging/v2/single_chat"
    seatalk_group_typing_path: str = "/messaging/v2/group_chat_typing"

    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_system_prompt: str = "You are a concise and helpful SeaTalk assistant."

    bot_mention_name: str = "@your-bot-name"
    bot_group_welcome_text: str = "Thanks for adding me. Mention me in this group to chat."
    bot_user_welcome_text: str = "Hi, I am online. Ask me anything."
    bot_send_group_welcome: bool = True
    bot_send_user_welcome: bool = True
    bot_send_typing_status: bool = True
    webhook_worker_count: int = 2
    webhook_queue_maxsize: int = 1000
    log_level: str = "INFO"


settings = Settings()
