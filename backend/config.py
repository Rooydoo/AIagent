"""Configuration management for the application."""
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    database_path: str = "data/paper_agent.db"
    papers_directory: str = "papers"
    outputs_directory: str = "outputs"
    default_citation_style: str = "Vancouver"
    default_language: str = "ja"
    max_projects: int = 5
    max_conversation_history: int = 300
    max_paper_pages: int = 30

    # LLM Settings
    summarization_model: str = "claude-3-5-haiku-20241022"
    generation_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096

    class Config:
        env_file = ".env"


def load_config() -> Settings:
    """Load configuration from config.json and environment."""
    config_path = Path(__file__).parent.parent / "config.json"

    settings_dict = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            settings_dict = {
                "anthropic_api_key": config.get("anthropic_api_key", ""),
                "telegram_bot_token": config.get("telegram_bot_token", ""),
                "database_path": config.get("database_path", "data/paper_agent.db"),
                "papers_directory": config.get("papers_directory", "papers"),
                "outputs_directory": config.get("outputs_directory", "outputs"),
                "default_citation_style": config.get("default_citation_style", "Vancouver"),
                "default_language": config.get("default_language", "ja"),
                "max_projects": config.get("max_projects", 5),
                "max_conversation_history": config.get("max_conversation_history", 300),
                "max_paper_pages": config.get("max_paper_pages", 30),
            }
            llm_settings = config.get("llm_settings", {})
            settings_dict["summarization_model"] = llm_settings.get("summarization_model", "claude-3-5-haiku-20241022")
            settings_dict["generation_model"] = llm_settings.get("generation_model", "claude-sonnet-4-20250514")
            settings_dict["temperature"] = llm_settings.get("temperature", 0.7)
            settings_dict["max_tokens"] = llm_settings.get("max_tokens", 4096)

    return Settings(**settings_dict)


settings = load_config()
