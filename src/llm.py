import os
import json
import yaml
import tiktoken
# from langchain_community.llms import OpenAI
# from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
import re
from langchain_groq import ChatGroq
from langchain_classic.chains import LLMChain


#Models:
# openai - https://platform.openai.com/docs/models
# anthropic - https://docs.anthropic.com/en/docs/about-claude/models 
#   - claude-3-5-sonnet-latest





def load_config(config_path):
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
        
        if model == "claude-sonnet-4-5-nonthinking":
            # print("THINING!")
            llm = ChatAnthropic(model="claude-sonnet-4-5-20250929", 
                            anthropic_api_key=anthropic_api_key,
                            max_tokens=max_tokens,
                            thinking={"type": "disabled"}
                            # model_kwargs={"thinking": {"type": "disabled"}}
                            )


        else:
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
            max_output_tokens=max_tokens,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

    
            #  model_kwargs={
            # "response_format": {"type": "json_object"} # force raw JSON
            # }
        )   # keeps your current signature unchanged        )
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


# def extract_json(text: str) -> str:
#     """
#     Remove markdown code fences (e.g. ```json ... ```) from the text.
#     """
#     # This regex will remove the ```json and ``` markers.
#     # It assumes that the JSON is enclosed in them.
#     pattern = r"```(?:json)?\s*(.*?)\s*```"
#     match = re.search(pattern, text, re.DOTALL)
#     if match:
#         return match.group(1).strip()
#     return text.strip()

import re, json

def extract_json(text: str) -> str:
    """
    Extract a JSON object from model output, repairing common issues:
    - Strips ```json fences
    - Normalizes quotes and removes trailing commas
    - Returns largest balanced JSON prefix
    - If JSON still invalid, truncates a dangling last element in `component_assessments`
    - Finally, appends missing closers as a last resort
    Returns a JSON string (possibly repaired) suitable for json.loads.
    """

    if not isinstance(text, str) or not text.strip():
        return ""

    # --- 1) Strip code fences if present ---
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    s = (fenced.group(1) if fenced else text).strip()

    # --- 2) Heuristic: start at first '{' (ignore any preamble) ---
    start = s.find("{")
    if start != -1:
        s = s[start:]

    # --- 3) Sanitize common issues ---
    def _sanitize_common_issues(t: str) -> str:
        # Smart quotes -> plain
        t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        # Remove trailing commas before } or ]
        t = re.sub(r",(\s*[}\]])", r"\1", t)
        return t

    s = _sanitize_common_issues(s)

    # --- 4) Largest balanced JSON prefix (ignoring content inside strings) ---
    def _last_balanced_index(t: str) -> int:
        in_str = False
        esc = False
        stack = []
        last_ok = -1
        for i, ch in enumerate(t):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            else:
                if ch == '"':
                    in_str = True
                    continue
                if ch in "{[":
                    stack.append(ch)
                elif ch == "}":
                    if stack and stack[-1] == "{":
                        stack.pop()
                    else:
                        break
                elif ch == "]":
                    if stack and stack[-1] == "[":
                        stack.pop()
                    else:
                        break
            if not in_str and not stack:
                last_ok = i
        return last_ok

    idx = _last_balanced_index(s)
    if idx >= 0:
        s = s[: idx + 1].strip()
        s = _sanitize_common_issues(s)

    # Quick success path
    try:
        json.loads(s)
        return s
    except Exception:
        pass

    # --- 5) Targeted repair: trim dangling last element in `component_assessments` ---
    # We locate the array and keep only fully closed object elements.
    def _trim_dangling_last_array_item(json_text: str, array_key: str) -> str:
        # Find the `"array_key": [`
        m = re.search(rf'"{re.escape(array_key)}"\s*:\s*\[', json_text)
        if not m:
            return json_text  # nothing to do

        open_bracket_pos = m.end()  # position after '['
        # Find the matching closing bracket for this array using depth over objects only
        i = open_bracket_pos
        n = len(json_text)
        in_str = False
        esc = False
        obj_depth = 0
        last_complete_item_end = None
        array_close_pos = None

        while i < n:
            ch = json_text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    obj_depth += 1
                elif ch == "}":
                    if obj_depth > 0:
                        obj_depth -= 1
                        # If object just closed and we're at array top-level,
                        # mark a complete item end (might be followed by comma or ])
                        if obj_depth == 0:
                            last_complete_item_end = i + 1
                elif ch == "]":
                    if obj_depth == 0:
                        array_close_pos = i
                        break
            i += 1

        if array_close_pos is None:
            # No closing bracket found; give up
            return json_text

        # If the last complete item end is before the array close, we may have a dangling partial tail.
        if last_complete_item_end and last_complete_item_end < array_close_pos:
            # Build new text: prefix + items up to last_complete_item_end
            prefix = json_text[:open_bracket_pos]
            items = json_text[open_bracket_pos:last_complete_item_end]
            suffix = json_text[array_close_pos+1:]  # after the original ']'
            # Remove any trailing comma from items
            items = re.sub(r",\s*$", "", items)
            repaired = prefix + items + "]" + suffix
            return repaired
        else:
            return json_text

    # Try trimming the `component_assessments` array once (or twice if needed)
    for _ in range(2):
        s_try = _trim_dangling_last_array_item(s, "component_assessments")
        s_try = _sanitize_common_issues(s_try)
        try:
            json.loads(s_try)
            return s_try
        except Exception:
            s = s_try  # keep best effort and try again

    # --- 6) Final fallback: append missing closers based on counts (ignoring strings) ---
    def _count_pairs(t: str):
        in_str = False
        esc = False
        oc = ob = cc = cb = 0
        for ch in t:
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    oc += 1
                elif ch == "[":
                    ob += 1
                elif ch == "}":
                    cc += 1
                elif ch == "]":
                    cb += 1
        return oc, cc, ob, cb

    oc, cc, ob, cb = _count_pairs(s)
    repaired = s + ("}" * max(0, oc - cc)) + ("]" * max(0, ob - cb))
    repaired = _sanitize_common_issues(repaired)
    return repaired.strip()
