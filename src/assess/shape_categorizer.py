

# shape_categorizer.py

from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate
import json

def categorize_shape(config_path: str, emotional_scores: list, llm_provider: str, llm_model: str) -> dict:
    # Docstring and function start are perfect, no changes needed
    # ...
    scores_str = str(emotional_scores)

    # FIX: Refined the prompt to be cleaner and less redundant.
    prompt_template = """
You are a highly logical data processor. Your task is to convert a sequence of emotional scores into a "Shape Signature" and then assign a "Shape Category" based on a fixed set of rules.

**Rules for Shape Signature:**
1.  Compare each score to the previous one.
2.  A significant increase (change of +3 or more) is a Rise (↑).
3.  A significant decrease (change of -3 or more) is a Fall (↓).
4.  A small change (between -2 and +2) is Stasis (→).
5.  Ignore the first score as it is the starting point.

**Rules for Shape Category:**
- "↑": "Rags to Riches"
- "↓": "From Bad to Worse"
- "↓↑": "Man in Hole"
- "↑↓": "Icarus"
- "↑↓↑": "Boy Meets Girl"
- "→↑↓↑": "Cinderella"
- If the signature does not match any of the above, the category is "Custom".

**Input Scores:**
{emotional_scores}

---
## OUTPUT

Provide your final assessment in the following JSON format ONLY. Do not include any other text or explanation outside of this JSON structure.

**Example:**
Input Scores: [3, 7, -10]
Output:
```json
{{
  "shape_signature": "↑↓",
  "shape_category": "Icarus"
}}
"""

    prompt = PromptTemplate(
    input_variables=["emotional_scores"],
    template=prompt_template
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=200)
    runnable = prompt | llm
    output = runnable.invoke({
        "emotional_scores": scores_str
    })
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
    category_data = extract_json(output_text)
    print("--- Shape Categorizer Output ---")
    print(json.dumps(category_data, indent=2))
    print("------------------------------")
    return category_data

if __name__ == 'main':
# --- Example Usage ---
    # 1. Define example emotional scores from the Gatsby analysis
    gatsby_scores = [1, 8, 4, -3, -6, -10]

    # 2. Set configuration parameters
    CONFIG_PATH = 'config.yaml' 
    LLM_PROVIDER = 'openai'
    # Recommended model for simple, fast tasks
    LLM_MODEL = 'gpt-3.5-turbo' 

    # 3. Call the function
    try:
        final_category = categorize_shape(
            config_path=CONFIG_PATH,
            emotional_scores=gatsby_scores,
            llm_provider=LLM_PROVIDER,
            llm_model=LLM_MODEL
        )
        print("\nCategorization successful.")

    except FileNotFoundError:
        print(f"Error: The configuration file '{CONFIG_PATH}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")