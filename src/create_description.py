from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import yaml
import tiktoken
import json 
import os 
from llm import load_config, get_llm, extract_json
import base64
import mimetypes
from langchain_core.messages import HumanMessage

config_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml'
llm_provider = 'google'
llm_model = 'gemini-2.5-pro'

# --- New Helper Function for Image Encoding ---

def encode_image(image_path: str) -> str:
    """Encodes an image file into a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """Gets the MIME type of an image file."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        raise ValueError(f"Could not determine MIME type for {image_path}")
    return mime_type

def create_product_description():

    prompt_template = """
    You're a literary and marketing genius. You have a particular expertise in both Kurt Vonnegut's theory on The Shapes of Stories and creating compelling product descriptions for online e-commerce. I need your help to create a product description for the artwork attached. 
    
    The artwork attempts to capture the shape of a particular story. The shape's line is made of words which capture the essence of what's happening in each part of the story.
    
    First, identify the story title, author, and protagonist from the image. Then, please critically analyze the photo and create a product description using the template below. Please respond back with only the product description and nothing else.

    PRODUCT DESCRIPTION TEMPLATE: 

    The Shape of "[STORY TITLE]" -- [PROTAGONIST]'s Journey

    Experience [AUTHOR]'s [masterpiece/classic/beloved novel] in a completely new way. This unique art print transforms the journey of [PROTAGONIST] in "[STORY TITLE]" into a visual [SHAPE DESCRIPTION], where every word contributes to the story's distinctive [emotional arc/narrative journey].

    **The Story Behind the Shape**
    [2-3 sentences about why this particular shape represents this story's emotional journey - connect to plot/themes]

    **Literary Art That Speaks**
    - Every word is carefully chosen to reflect the story's essence
    - Thoughtful typography that honors the literary work
    - A captivating conversation piece for book lovers and literary enthusiasts
    - Timeless design that complements any space

    **Print Details**
    - Premium 8x10" print on archival-quality paper with 0.5" white border
    - [COLOR DESCRIPTION] background with [TEXT COLOR] typography
    - Designed for standard framing (stunning when matted in an 11x14" frame)
    - Museum-quality inks ensure lasting vibrancy and clarity

    Transform your space with this unique intersection of literature and visual art. Whether displayed in your reading nook, office, or living room, this print celebrates the timeless power of storytelling.

    *Part of "The Shapes of Stories" collection - where every story's unique journey becomes beautiful art.*
    """

     # --- 3. Encode the Image and Get MIME type ---
    base64_image = encode_image('/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png')
    #print("base64_image: ", base64_image)
    
    image_mime_type = get_image_mime_type('/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png')
    #print("image_mime_type: ", image_mime_type)

    # --- 4. Construct the Multimodal Message ---
    # This is the key change. We create a HumanMessage with a list of content.
    # The first item is our text prompt, the second is the image.
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt_template,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime_type};base64,{base64_image}"
                }
            },
        ]
    )
    print("message: ", message)

    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    #--- 5. Invoke the LLM with the new message structure ---
    # Instead of a chain with a prompt template, we directly invoke the LLM
    # with our constructed message. We pass it as a list.
    response = llm.invoke([message])
    print("response: ", response)
    
    # The output from the LLM is an AIMessage object, we access its content.
    product_description = response.content
    
    print(product_description)


create_product_description()