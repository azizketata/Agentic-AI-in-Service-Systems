import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

# Load .env from prototype root
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def _load_settings() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_llm() -> BaseChatModel:
    settings = _load_settings()
    llm_cfg = settings["llm"]
    provider = llm_cfg["provider"]
    temperature = llm_cfg.get("temperature", 0.0)
    max_tokens = llm_cfg.get("max_tokens", 2048)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=llm_cfg["anthropic_model"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=llm_cfg["openai_model"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'anthropic' or 'openai'.")
