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