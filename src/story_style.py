from llm import load_config, get_llm, extract_json
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
# from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm import load_config, get_llm, extract_json
import yaml
import tiktoken
import json 
import os 
import sys
import gi
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Pango, PangoCairo

#VISION SUPPORT
from langchain_core.messages import HumanMessage
import base64
import mimetypes
from typing import Optional, Union, Dict, Any, List, Tuple


#HELP FUNCTIONS -- CHECK IF FONT EXISTS

## HELPER FUNCTIONS TO DECODE IMAGE
def _encode_image_to_data_url(image_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return (mime_type, base64_data) or (None, None) if no image."""
    if not image_path:
        return None, None
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return mime_type, b64


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

def get_story_style(config_path, story_title, author, protagonist, llm_provider, llm_model, book_cover_path):


    prompt_template = f"""
# Story Style Guide Generator

You are a design specialist combining expertise in literary analysis and visual design. Your task is to create a cohesive visual style for a story visualization that captures the essence of the narrative while maintaining aesthetic and technical excellence.

Input:
- Story Title: {story_title}
- Author: {author}
- Protagonist: {protagonist}
- Book Cover: You can see the front cover image attached to this prompt. Use it to infer color palette, visual motifs, and overall tone.


Analysis Framework:
1. Story Elements
   - The attached book cover image: its color palette, typography, composition, and any recognizable visual traditions (e.g., classic Penguin paperbacks, modern minimalists, vintage engravings)
   - Setting (time period, location, social context)
   - Dominant mood and atmosphere (consider the overall emotional landscape of the work and protagonist)
   - Core themes and the protagonist's journey
   - Key symbols and motifs

2. Design Requirements
   Colors must:
   - Work in both digital and print formats
   - Connect meaningfully to story elements
   - Maintain impact under various lighting
   - Be returned as hex codes in the form #RRGGBB
   - Meet accessibility standards i.e. 4.5:1 minimum contrast between background_color and font_color


   
   Typography must:
   - Reflect story's period and tone
   - Maintain legibility in curved layouts
   - Include appropriate weight variations
   - Be commercially licensable

Process:
1. Analyze story elements and the attached book cover image
2. Develop color palette considering:
   - The attached book cover image:
    * Infer dominant and secondary colors from the actual cover.
    * Prefer using one of the dominant cover colors for either the background or primary accent.
    * You may slightly lighten, darken, or desaturate cover colors to satisfy readability and print safety.
    * Avoid creating colors that clash strongly with the cover, unless strictly necessary for contrast.
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
  "font": "Trajan Pro"
}}
"""


    # prompt = PromptTemplate(
    #     input_variables=["story_title", "author", "protagonist"],  # Define the expected inputs
    #     template=prompt_template
    # )


    # config = load_config(config_path=config_path)
    # llm = get_llm(llm_provider, llm_model, config, max_tokens=1000)

    # # Instead of building an LLMChain, use the pipe operator:
    # runnable = prompt | llm

    # # Then invoke with the required inputs:
    # output = runnable.invoke({
    #     "story_title": story_title,
    #     "author": author,
    #     "protagonist": protagonist
    # })

    #print(output)

    # If the output is an object with a 'content' attribute, extract it.
    # if hasattr(output, "content"):
    #     output_text = output.content
    # else:
    #     output_text = output
    
    # if output_text == "" or output_text == None or output_text == {}:
    #     print("❌ ERROR: LLM Failed to Create Story Style")
    #     raise ValueError("ERROR: LLM Failed to Create Story Style")

    #attempt to extact json (if needed)
    #story_style = extract_json(output_text)
    #print(story_style)


    #VISIO SUPPORT
    # 1) Load config + model (unchanged)
    config = load_config(config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # 2) Optional image
    image_mime_type, base64_image = _encode_image_to_data_url(book_cover_path)

    human_content = [{"type": "text", "text": prompt_template}]
    if image_mime_type and base64_image:
        human_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{image_mime_type};base64,{base64_image}"}
        })
    
    message = HumanMessage(content=human_content)

    # 6) Invoke the model exactly like you already do
    response = llm.invoke([message])
    response_text = response.content if hasattr(response, "content") else str(response)
    story_style = extract_json(response_text)
    print("STORY STYLE:")
    print(story_style)


    return story_style


    # story_style = json.loads(output_text)
    # background_color = story_style['background_color'],
    # font_color = story_style['font_color']
    # border_color = story_style['border_color']
    # font = story_style['font']


from paths import PATHS
story_style_llm_model = "claude-sonnet-4-5" #claude sonnet good for style
story_style = get_story_style(
    config_path = PATHS['config'],
    story_title = "The Catcher in the Rye", 
    author = "J.D. Salinger",
    protagonist = "Holden Caulfield", 
    llm_provider = "anthropic", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
    llm_model = story_style_llm_model, #"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    book_cover_path="/Users/johnmikedidonato/Downloads/5107.jpg"
)