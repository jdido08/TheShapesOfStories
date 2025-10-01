from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from llm import load_config, get_llm, extract_json
import yaml
import tiktoken
import json 
import os 

#HELP FUNCTIONS -- CHECK IF FONT EXISTS


## HELPER FUNCTIONS ###
def get_font_path(font_name):
    """
    Finds the full file path for a given font name using matplotlib's font manager.

    Args:
        font_name (str): The name of the font to find (e.g., "Merriweather").

    Returns:
        str: The full file path to the font. Exits script if font is not found.
    """
    try:
        # findfont will search your system and return the best match.
        # The FontProperties object is needed to properly query the font.
        font_prop = font_manager.FontProperties(family=font_name)
        return font_manager.findfont(font_prop)
    except ValueError:
        # This error is raised if findfont can't find any matching font.
        print(f"--- FONT FINDER ERROR ---", file=sys.stderr)
        print(f"The font '{font_name}' could not be found by the font manager.", file=sys.stderr)
        print("Please ensure it is properly installed and its cache is updated.", file=sys.stderr)
        sys.exit(1)

def pango_font_exists(font_name):
    from gi.repository import Pango, PangoCairo
    """
    Checks whether the given font is available using Pango.
    Returns True if the font is found, False otherwise.
    """
    if not font_name:
        return True  # nothing to check if font_name is empty

    # Get the default font map from PangoCairo.
    font_map = PangoCairo.FontMap.get_default()
    families = font_map.list_families()

    # Iterate through the font families and see if any name matches (case-insensitive).
    for family in families:
        if font_name.lower() in family.get_name().lower():
            return True

    return False


###

def get_story_style(config_path,story_title, author, protagonist, llm_provider, llm_model):


    prompt_template = """
# Story Style Guide Generator

You are a design specialist combining expertise in literary analysis and visual design. Your task is to create a cohesive visual style for a story visualization that captures the essence of the narrative while maintaining aesthetic and technical excellence.

Input:
- Story Title: {story_title}
- Author: {author}
- Protagonist: {protagonist}

Analysis Framework:
1. Story Elements
   - Historical visual traditions e.g. iconic cover designs and established print design elements that audiences would recognize (if applicable)
   - Setting (time period, location, social context)
   - Dominant mood and atmosphere (consider the overall emotional landscape of the work and protagonist)
   - Core themes and the protagonist's journey
   - Key symbols and motifs

2. Design Requirements
   Colors must:
   - Work in both digital and print formats
   - Maintain impact under various lighting
   - Meet accessibility standards (4.5:1 minimum contrast)
   - Connect meaningfully to story elements
   
   Typography must:
   - Reflect story's period and tone
   - Maintain legibility in curved layouts
   - Include appropriate weight variations
   - Be commercially licensable

Process:
1. Analyze story elements
2. Develop color palette considering:
   - Story themes and setting
   - Symbolic significance
   - Technical requirements
3. Select typography that:
   - Captures narrative tone
   - Functions technically
   - Bridges historical and modern needs
4. Output ONLY JSON in the following exact structure and nothing else
{{  
  "design_rationale":"",
  "background_color": "",  
  "font_color": "",       
  "border_color": "",     
  "font": ""            
}}

Example #1:
Story Title: Romeo and Juliet
Author: William Shakespeare
Protagonist: Juliet

Output:
{{  
  "design_rationale":"The passionate romance, tragic fate, and themes of youth and nobility are reflected in rich burgundy tones with gold accents, while the elegant serif typeface echoes both Renaissance Italy and timeless romance.",
  "background_color": "#8C1C13",
  "font_color": "#F4D03F",
  "border_color": "#590D0D",
  "font": "Cormorant Garamond"
}}

Example #2:
Story Title: The Iliad
Author: Homer
Protagonist: Achilles

Output:
{{  
  "design_rationale": "Drawing from ancient Greek aesthetics and the epic's themes of divine warfare and mortal pride, the design pairs a deep bronze background with marble-white text. The classical typeface Trajan Pro evokes both heroic Roman inscriptions and timeless gravitas, while ensuring clarity in the curved narrative of warfare and honor.",
  "background_color": "#704214",
  "font_color": "#F5F5F5",
  "border_color": "#463A2C",
  "font": "Trajan Pro"
}}
"""


    prompt = PromptTemplate(
        input_variables=["story_title", "author", "protagonist"],  # Define the expected inputs
        template=prompt_template
    )


    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1000)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    # Then invoke with the required inputs:
    output = runnable.invoke({
        "story_title": story_title,
        "author": author,
        "protagonist": protagonist
    })

    #print(output)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    #attempt to extact json (if needed)
    story_style = extract_json(output_text)
    print(story_style)
    return story_style


    # story_style = json.loads(output_text)
    # background_color = story_style['background_color'],
    # font_color = story_style['font_color']
    # border_color = story_style['border_color']
    # font = story_style['font']
