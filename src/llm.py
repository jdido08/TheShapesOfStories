import os
import json
import yaml
import tiktoken
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import re
from langchain_groq import ChatGroq

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
        openai_api_key = config.get("openai_key")
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
    elif provider in {"google", "gemini"}:
        # Google Gemini (via Google Generative AI)
        # models gemini-2.5-pro-preview-03-25
        google_api_key = config.get("google_gemini_key")  # or fall back to env var
        if not google_api_key and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("google_api_key must be specified in the config or env")

        # ChatGoogleGenerativeAI uses `max_output_tokens` rather than `max_tokens`
        llm = ChatGoogleGenerativeAI(
          model=model,                    # e.g. "gemini-pro", "gemini-1.5-flash-latest"
            google_api_key=google_api_key,  # optional if env var is set
             model_kwargs={
            "max_output_tokens": max_tokens,           # e.g. 1024
            "response_format": {"type": "json_object"} # force raw JSON
        })   # keeps your current signature unchanged        )
    elif provider == "groq":
        
        groq_api_key = config.get("groq_key")
        if not groq_api_key:
            # You can also allow it to be set as an environment variable
            # groq_api_key = os.getenv("GROQ_API_KEY")
            # if not groq_api_key:
            raise ValueError("groq_api_key must be specified in the config")
        llm = ChatGroq(model_name=model, # Groq uses model_name
                       groq_api_key=groq_api_key,
                       max_tokens=max_tokens) # ChatGroq uses max_tokens
        
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