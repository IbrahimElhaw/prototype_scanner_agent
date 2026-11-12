from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from optimizer.config import Config


def build_llm(config: Config) -> BaseChatModel:
    """Create the chat model from config. Swap the provider here only."""
    return ChatOllama(
        model=config.model_name,
        base_url=config.ollama_url,
        temperature=config.temperature,
    )