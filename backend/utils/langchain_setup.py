"""Langchain setup and utilities."""
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from ..config import settings


def setup_langchain_cache():
    """Setup Langchain SQLite cache."""
    cache_path = Path(__file__).parent.parent.parent / "data" / ".langchain_cache.db"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    set_llm_cache(SQLiteCache(database_path=str(cache_path)))


def get_llm(model_type: str = "generation") -> ChatAnthropic:
    """Get configured LLM instance.

    Args:
        model_type: Either 'generation' (Sonnet) or 'summarization' (Haiku)
    """
    if model_type == "summarization":
        model = settings.summarization_model
    else:
        model = settings.generation_model

    return ChatAnthropic(
        model=model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


def convert_history_to_messages(history: list) -> list:
    """Convert conversation history to Langchain messages."""
    messages = []
    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            messages.append(AIMessage(content=item["content"]))
        elif item["role"] == "system":
            messages.append(SystemMessage(content=item["content"]))
    return messages


# Initialize cache on import
setup_langchain_cache()
