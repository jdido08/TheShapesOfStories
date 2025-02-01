import os
import json
import yaml
import tiktoken
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
import re

#Models:
# openai - https://platform.openai.com/docs/models
# anthropic - https://docs.anthropic.com/en/docs/about-claude/models 
#   - claude-3-5-sonnet-latest





def load_config(config_path="config.yaml"):
    with open(config_path, "r") as stream:
        return yaml.safe_load(stream)

def get_llm(provider: str, model: str, config: dict, max_tokens: int = 1024):
    provider = provider.lower()
    if provider == "openai":
        # Import the chat model from the community chat models module.
        #from langchain_community.chat_models import ChatOpenAI
        from langchain_openai import ChatOpenAI
        openai_api_key = config.get("openai_key_vonnegutgraphs")
        if not openai_api_key:
            raise ValueError("openai_key_vonnegutgraphs must be specified in the config")
        # Pass the API key as a parameter.
        llm = ChatOpenAI(model_name=model, 
                        openai_api_key=openai_api_key,
                        max_tokens=max_tokens)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        anthropic_api_key = config.get("anthropic_key")
        if not anthropic_api_key:
            raise ValueError("anthropic_key must be specified in the config")
        llm = ChatAnthropic(model=model, 
                            anthropic_api_key=anthropic_api_key,
                            max_tokens=max_tokens)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    return llm


def extract_json(text: str) -> str:
    """
    Remove markdown code fences (e.g. ```json ... ```) from the text.
    """
    # This regex will remove the ```json and ``` markers.
    # It assumes that the JSON is enclosed in them.
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()