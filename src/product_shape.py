# Import necessary libraries
import cairo
import gi
import numpy as np
import math
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity
from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import yaml
import copy
from scipy.interpolate import CubicSpline
import json
import os
import random 
import os
import json
import matplotlib.font_manager as fm
from product_color import map_hex_to_simple_color

# Ensure the correct versions of Pango and PangoCairo are used
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

import anthropic
import yaml

CURRENT_DPI = 300
MAX_SPACING_ADJUSTMENT_ATTEMPTS = 1000


def maybe_save(surface, path, output_format, save: bool):
    if not save:
        return
    if output_format == "svg":
        surface.flush()
    else:
        surface.write_to_png(path)

def create_shape(
                config_path,
                output_dir, # <-- NEW ARGUMENT
                story_data_dir, # <-- NEW ARGUMENT for data files
                story_data_path,
                product = "canvas",
                x_delta = 0.015,
                step_k = 15,
                max_num_steps = 3, #for step by step function; set to 2 for 8x10 and 3 for 12x12
                font_style="",
                font_size=72,
                font_color = (0, 0, 0), #default to black
                line_type = 'char',
                line_thickness = 2,
                line_color = (0,0,0),
                background_type='solid', 
                background_value=(1, 1, 1), 
                has_title = "NO", #values YES or NO
                title_text = "", #optionl if left blank then title used 
                title_font_style = "",
                title_font_size=96,
                title_font_color = (0, 0, 0),#default to black
                title_font_bold = False, #can be True or False
                title_font_underline = False,
                title_padding = 20,
                gap_above_title = 20,
                protagonist_text = "",
                protagonist_font_style = "Cormorant Garamond",
                protagonist_font_size= 12, 
                protagonist_font_color= (0, 0 , 0),
                protagonist_font_bold = False,
                protagonist_font_underline = False,
                author_text="", # Optional, defaults to story_data['author']
                author_font_style="Cormorant Garamond", # Defaults to title font style if empty
                author_font_size=12, # Suggest smaller than title
                author_font_color='#000000', # Use hex, defaults to title color
                author_font_bold=False,
                author_font_underline=False,
                author_padding=5, # Vertical space BETWEEN title and author
                top_text = "", #only applies when wrapped > 0; if "" will default to author, year
                top_text_font_style = "Cormorant Garamond",
                top_text_font_size = "24",
                top_text_font_color = "#1F4534",
                bottom_text = "", #only applies when wrapped > 0; if "" will default to "Shapes of Stories"
                bottom_text_font_style = "Sans",
                bottom_text_font_size = "12",
                bottom_text_font_color = "#000000",
                top_and_bottom_text_band = 1.5,
                border = False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
                wrap_background_color = (0,0,0),
                fixed_margin_in_inches=0.625,
                recursive_mode = True,
                recursive_loops = 500,
                llm_provider = "anthropic",
                llm_model = "claude-3-5-sonnet-latest",
                output_format="png"):
    

    fonts_to_check = {
        "Body Font": font_style,
        "Title Font": title_font_style,
        "Protagonist Font": protagonist_font_style,
        "Author Font":author_font_style,
        "Top Text Font": top_text_font_style,
        "Bottom Text Font": bottom_text_font_style,
    }
    # for desc, font in fonts_to_check.items():
    #     if font and not pango_font_exists(font):
    #         raise ValueError(f"{desc} '{font}' not found on this system.")
    

    #CONVERT BORDER THICKENSS IN INCHES TO PIXELS
    border_thickness = (border_thickness * 2) * CURRENT_DPI

    #save hex values 
    font_color_hex = font_color
    background_value_hex = background_value
    border_color_hex = border_color

    #convert hex colors to (x,y,z) foramt
    font_color = hex_to_rgb(font_color)
    line_color = hex_to_rgb(line_color)
    title_font_color = hex_to_rgb(title_font_color)
    protagonist_font_color = hex_to_rgb(protagonist_font_color)
    author_font_color = hex_to_rgb(author_font_color)
    top_text_font_color = hex_to_rgb(top_text_font_color)
    bottom_text_font_color = hex_to_rgb(bottom_text_font_color)
    border_color = hex_to_rgb(border_color)
    background_value = hex_to_rgb(background_value)
    wrap_background_color = hex_to_rgb(wrap_background_color)

    #open story data
    with open(story_data_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        if 'story_plot_data' in story_data:
            story_data = story_data['story_plot_data']

    background_color_name = map_hex_to_simple_color(background_value_hex)['name']
    font_color_name = map_hex_to_simple_color(font_color_hex)['name']

    #get title 
    if line_type == "char" or line_type == "text" or line_type == "text":
        line_style_name = "storybeats"
    else:
        line_style_name = "classic"
    
    path_name = story_data['title'].lower().replace(' ', '-') + "-" + story_data['protagonist'].lower().replace(' ', '-') + "-" + product.lower().replace(' ', '-') + "-" + str(width_in_inches) + "x" + str(height_in_inches) + "-" + background_color_name.lower().replace(' ', '-') + "-" + font_color_name.lower().replace(' ', '-')
    path_name = path_name.replace("’", "'")   # Normalize the path to replace curly apostrophes with straight ones
    path_name = path_name.replace(",", "")    # Normalize the path to replace commas
    product_data_path_name = path_name

    #check_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{path_title}_{path_protagonist}_{path_size}.json'
    # Use os.path.join with the new story_data_dir argument
    check_path = os.path.join(story_data_dir, f'{product_data_path_name}.json')
    #print(check_path)
    if os.path.exists(check_path):
        story_data_path = check_path
        print("Story Data for " , story_data_path ," exists")
        with open(story_data_path, 'r', encoding='utf-8') as file:
            story_data = json.load(file)
            if 'story_plot_data' in story_data:
                story_data = story_data['story_plot_data']


    #COME BACK TO
    product_design_path_name = path_name + "-" + line_style_name.lower().replace(' ', '-')
    unique_filename = f"{product_design_path_name}.{output_format}"
    

    story_data['font_color_details'] = map_hex_to_simple_color(font_color_hex)
    story_data['background_color_details'] = map_hex_to_simple_color(background_value_hex)
    story_data['border_color_details'] = map_hex_to_simple_color(border_color_hex) #NOT USING THIS 
    story_data['font_color_name'] = story_data['font_color_details']['name']
    story_data['background_color_name'] = story_data['background_color_details']['name']
    story_data['border_color_name'] = story_data['border_color_details']['name']
    story_data['product_slug'] = path_name


    #story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_protagonist}_{story_shape_product}_{story_shape_size}_{story_shape_line_type}_{line_type}_{story_shape_background_color}_{story_shape_font_color}_{story_shape_border_color}_{story_shape_font}_{story_shape_title_display}.{output_format}'
    story_shape_path = os.path.join(output_dir, unique_filename)
    #print("story_shape_path: ", story_shape_path)

   
    status = "processing"
    story_data['status'] = status
    count = 1
    print("starting...")
    # while status == "processing":
    for i in range(recursive_loops):
        # print(story_data['story_components'][1]['modified_end_time'])
        print("loop #", i)
        if story_data is None:
            print("STORY DATA NONE")

        story_data = transform_story_data(story_data, x_delta, step_k, max_num_steps)

        story_data, status = create_shape_single_pass(
                    config_path=config_path,
                    story_data=story_data, 
                    font_style=font_style,
                    font_size=font_size,
                    font_color = font_color,
                    line_type=line_type,
                    line_thickness = line_thickness,
                    line_color = line_color,
                    background_type=background_type, 
                    background_value=background_value, 
                    has_title = has_title,
                    title_text=title_text,
                    title_font_style=title_font_style,
                    title_font_size=title_font_size,
                    title_font_color = title_font_color,
                    title_font_bold = title_font_bold, 
                    title_font_underline = title_font_underline,
                    title_padding = title_padding,
                    gap_above_title = gap_above_title,
                    protagonist_text = protagonist_text,
                    protagonist_font_style = protagonist_font_style,
                    protagonist_font_size= protagonist_font_size, 
                    protagonist_font_color= protagonist_font_color,
                    protagonist_font_bold = protagonist_font_bold,
                    protagonist_font_underline = protagonist_font_underline,
                    author_text=author_text, # Optional, defaults to story_data['author']
                    author_font_style=author_font_style, # Defaults to title font style if empty
                    author_font_size=author_font_size, # Suggest smaller than title
                    author_font_color=author_font_color, # Use hex, defaults to title color
                    author_font_bold=author_font_bold,
                    author_font_underline=author_font_underline,
                    author_padding=author_padding, 
                    top_text = top_text, #only applies when wrapped > 0; if "" will default to author, year
                    top_text_font_style = top_text_font_style,
                    top_text_font_size = top_text_font_size,
                    top_text_font_color = top_text_font_color,
                    bottom_text = bottom_text, #only applies when wrapped > 0; if "" will default to "Shapes of Stories"
                    bottom_text_font_style = bottom_text_font_style,
                    bottom_text_font_size = bottom_text_font_size,
                    bottom_text_font_color = bottom_text_font_color,
                    top_and_bottom_text_band = top_and_bottom_text_band,
                    border = border,
                    border_thickness=border_thickness,
                    border_color=border_color,
                    width_in_inches=width_in_inches,
                    height_in_inches=height_in_inches,
                    wrap_in_inches=wrap_in_inches,
                    wrap_background_color = wrap_background_color,
                    fixed_margin_in_inches=fixed_margin_in_inches,
                    story_shape_path=story_shape_path,
                    recursive_mode=recursive_mode,
                    llm_provider = llm_provider,
                    llm_model = llm_model,
                    output_format = output_format)
        
        #print(count, " .) ", status)
        if(count % 50 == 0):
            print(count)

        count = count + 1
        if status == "completed" or status == "error":
            story_data['status'] = status
            break
        #print(story_data['story_components'][1]['modified_end_time'])



    #clean up story_data for saving 10/5/2025 -- testing out commenting out 
    del story_data['x_values']
    del story_data['y_values']
    for component in story_data['story_components']:

        if 'arc_x_values' in component:
            del component['arc_x_values']

        if 'arc_y_values' in component:
            del component['arc_y_values']


    #set new path
    story_data['font_size'] = font_size
    story_data['font_style'] = font_style
    story_data['font_color'] = font_color
    story_data['line_thickness'] = line_thickness
    story_data['title_font_size'] = title_font_size
    story_data['title_font_style'] = title_font_style
    story_data['title_font_color'] = title_font_color
    story_data['protagonist_font_size'] = protagonist_font_size
    story_data['protagonist_font_style'] = protagonist_font_style
    story_data['protagonist_font_color'] = protagonist_font_color
    story_data['background_color'] = background_value
    story_data['border_thickness'] = border_thickness
    story_data['border_color'] = border_color
    story_data['arc_text_llm'] = llm_model
    story_data['fixed_margin_in_inches'] = fixed_margin_in_inches
    story_data['product_size'] = f'{width_in_inches}x{height_in_inches}'
    story_data['line_style'] = line_style_name
    new_title = story_data['title'].lower().replace(' ', '-')
    new_size = f'{width_in_inches}x{height_in_inches}'
    new_protagonist = story_data['protagonist'].lower().replace(' ', '-')

    #adding hex color values
    story_data['font_color_hex'] = font_color_hex
    story_data['background_color_hex'] = background_value_hex
    story_data['border_color_hex'] = border_color_hex #NOT USING THIS 
    # story_data['font_color_name'] = map_hex_to_simple_color(font_color_hex)
    # story_data['background_color_name'] = map_hex_to_simple_color(background_value_hex)
    # story_data['border_color_name'] = map_hex_to_simple_color(border_color_hex) #NOT USING THIS 


    
    
    
    #new_story_data_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{new_title}_{new_protagonist}_{new_size}.json'
    # Use os.path.join with the new story_data_dir argument
    #new_story_data_filename = f'{new_title}_{new_protagonist}_{new_size}.json' #commenting 9/18/2025
    #new_story_data_path = os.path.join(story_data_dir, new_story_data_filename) #commenting 9/18/2025
    new_story_data_path = check_path
    
    with open(new_story_data_path, 'w', encoding='utf-8') as file:
        json.dump(story_data, file, ensure_ascii=False, indent=4)

    return new_story_data_path, story_shape_path


def create_shape_single_pass(
                config_path,
                story_data, 
                font_style="",
                font_size=72,
                font_color = (0, 0, 0), #default to black
                line_type = 'char',
                line_thickness = 2,
                line_color = (0,0,0),
                background_type='solid', 
                background_value=(1, 1, 1), 
                has_title = "NO",
                title_text = "",
                title_font_style = "",
                title_font_size=96,
                title_font_color = (0, 0 , 0), #default to black
                title_font_bold = False, 
                title_font_underline = False,
                title_padding = 20,
                gap_above_title = 20,
                protagonist_text = "",
                protagonist_font_style = "Cormorant Garamond",
                protagonist_font_size= 12, 
                protagonist_font_color= (0, 0 , 0),
                protagonist_font_bold = False,
                protagonist_font_underline = False,
                author_text="", # Optional, defaults to story_data['author']
                author_font_style="Cormorant Garamond", # Defaults to title font style if empty
                author_font_size=12, # Suggest smaller than title
                author_font_color='#000000', # Use hex, defaults to title color
                author_font_bold=False,
                author_font_underline=False,
                author_padding=5, # Vertical space BETWEEN title and author
                top_text = "", #only applies when wrapped > 0; if "" will default to author, year
                top_text_font_style = "Cormorant Garamond",
                top_text_font_size = "24",
                top_text_font_color = (0, 0 , 0),
                bottom_text = "", #only applies when wrapped > 0; if "" will default to "Shapes of Stories"
                bottom_text_font_style = "Sans",
                bottom_text_font_size = "12",
                bottom_text_font_color = (0, 0 , 0),
                top_and_bottom_text_band = 1.5,
                border=False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
                fixed_margin_in_inches = 0.625,
                wrap_background_color = (0,0,0),
                story_shape_path = "test",
                recursive_mode = True,
                llm_provider = "anthropic",
                llm_model = "claude-3-5-sonnet-latest",
                output_format = "png",
                save_intermediate=False):
    
    """
    Creates the shape with story data and optionally sets the background 
    and draws a title in a dedicated space at the bottom.

    Parameters:
    - story_data: dict containing story arcs and optional 'title', 'author' fields
    - font_style: string, e.g. "Arial" for font face
    - background_type: str, one of 'transparent', 'solid'
    - background_value: 
        if 'solid', tuple (r, g, b) for background color
        if 'transparent', ignored
    - line_type: 'char' (text along arcs) or 'line' (just a line)
    - has_title: "YES" or "NO" (whether to reserve space and draw a title)
    - title_font_style, title_font_size, title_font_color: style for the title
    - width_in_inches, height_in_inches: final image size in inches
    - recursive_mode: whether to keep adjusting arcs if they're too short/long
    """

    ### START OF DEBUG ###
    # --- ADD DEBUG COLORS ---
    # debug_segment_colors_rgb = [
    #     hex_to_rgb("#FF0000"), # Red
    #     hex_to_rgb("#00FF00"), # Green
    #     hex_to_rgb("#0000FF"), # Blue
    #     hex_to_rgb("#FFFF00"), # Yellow
    #     hex_to_rgb("#FF00FF"), # Magenta
    #     hex_to_rgb("#00FFFF"), # Cyan
    #     hex_to_rgb("#FFA500"), # Orange
    #     hex_to_rgb("#800080"), # Purple
    #     hex_to_rgb("#A52A2A"), # Brown
    #     hex_to_rgb("#FFFFFF")  # White (for markers, if background is dark)
    # ]
    # color_cycle = itertools.cycle(debug_segment_colors_rgb)
    # marker_color_rgb = hex_to_rgb("#000000") # Black for markers, or choose a contrast color
    # if sum(background_value) < 1.5: # If background is dark-ish
    #     marker_color_rgb = hex_to_rgb("#FFFFFF") # Use white markers


    ### END OF DEBUG ###

    # Extract the overall x_values and y_values (scaled from transform_story_data)
    x_values = story_data['x_values']  # Scaled x_values (from 1 to 10)
    y_values = story_data['y_values']  # Scaled y_values (from -10 to 10)

    # Extract original end_time and end_emotional_score values
    original_end_times = [component['end_time'] for component in story_data['story_components']]
    original_emotional_scores = [component['end_emotional_score'] for component in story_data['story_components']]

    # Get the original min and max values from your data
    old_min_x = min(original_end_times)
    old_max_x = max(original_end_times)
    old_min_y = min(original_emotional_scores)
    old_max_y = max(original_emotional_scores)

    # Set the scaling ranges used in transform_story_data
    new_min_x, new_max_x = 1, 10
    new_min_y, new_max_y = -10, 10

  
    # total print area
    total_width_in = width_in_inches + 2*wrap_in_inches
    total_height_in = height_in_inches + 2*wrap_in_inches

    total_width_px = int(total_width_in * CURRENT_DPI)
    total_height_px = int(total_height_in * CURRENT_DPI)


    #SETUP FONTS
    from gi.repository import Pango
    font_size_for_300dpi = font_size * (CURRENT_DPI / 72)
    font_desc = Pango.FontDescription(f"{font_style} {font_size_for_300dpi}")

    title_font_size_for_300dpi = title_font_size * (CURRENT_DPI / 72)
    title_font_desc = Pango.FontDescription(f"{title_font_style} {title_font_size_for_300dpi}")
    if title_font_bold == True:
        title_font_desc.set_weight(Pango.Weight.BOLD)

    protagonist_font_size_for_300dpi = protagonist_font_size * (CURRENT_DPI/72)
    protagonist_font_desc = Pango.FontDescription(f"{protagonist_font_style} {protagonist_font_size_for_300dpi}")
    if protagonist_font_bold == True:
        protagonist_font_desc.set_weight(Pango.Weight.BOLD)

    # Prepare Author Font Desc (using effective style passed in)
    author_font_size_for_300dpi = author_font_size * (CURRENT_DPI / 72)
    author_font_desc = Pango.FontDescription(f"{author_font_style} {author_font_size_for_300dpi}")
    if author_font_bold: author_font_desc.set_weight(Pango.Weight.BOLD)


    top_text_font_size_for_300dpi = top_text_font_size * (CURRENT_DPI/72)
    top_text_font_desc = Pango.FontDescription(f"{top_text_font_style} {top_text_font_size_for_300dpi}")

    bottom_text_font_size_for_300dpi = bottom_text_font_size * (CURRENT_DPI/72)
    bottom_text_font_desc = Pango.FontDescription(f"{bottom_text_font_style} {bottom_text_font_size_for_300dpi}")

    # Create a Cairo surface and context
    import cairo
     # create the surface
    if output_format=="svg":
        surface = cairo.SVGSurface(story_shape_path, total_width_px, total_height_px)
    else:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, total_width_px, total_height_px)
    cr = cairo.Context(surface)

    from gi.repository import Pango, PangoCairo
    pangocairo_context = PangoCairo.create_context(cr)

    # Calculate dimensions
    design_offset_x = wrap_in_inches * CURRENT_DPI
    design_offset_y = wrap_in_inches * CURRENT_DPI
    design_width = int(width_in_inches * CURRENT_DPI)
    design_height = int(height_in_inches * CURRENT_DPI)

    # Paint wrap areas
    if wrap_in_inches > 0:
        cr.save()
        cr.set_source_rgb(*wrap_background_color)
        
        # Top wrap area
        cr.rectangle(0, 0, total_width_px, wrap_in_inches * CURRENT_DPI)
        cr.fill()
        
        # Bottom wrap area
        bottom_y = total_height_px - (wrap_in_inches * CURRENT_DPI)
        cr.rectangle(0, bottom_y, total_width_px, wrap_in_inches * CURRENT_DPI)
        cr.fill()
        
        # Left wrap area
        cr.rectangle(0, wrap_in_inches * CURRENT_DPI, wrap_in_inches * CURRENT_DPI, height_in_inches * CURRENT_DPI)
        cr.fill()
        
        # Right wrap area
        right_x = total_width_px - (wrap_in_inches * CURRENT_DPI)
        cr.rectangle(right_x, wrap_in_inches * CURRENT_DPI, wrap_in_inches * CURRENT_DPI, height_in_inches * CURRENT_DPI)
        cr.fill()
        
        cr.restore()

        # Now translate for main design
        cr.save()
        cr.translate(design_offset_x, design_offset_y)
    else:
        
        # Now translate for main design
        cr.save()
        cr.translate(design_offset_x, design_offset_y)

    # Paint main background
    if background_type == 'transparent':
        cr.rectangle(0, 0, design_width, design_height)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.fill()
        cr.set_operator(cairo.OPERATOR_OVER)
    elif background_type == 'solid':
        cr.rectangle(0, 0, design_width, design_height)
        cr.set_source_rgb(*background_value)
        cr.fill()
    


    if border:
        cr.save()
        cr.set_source_rgb(*border_color)
        cr.set_line_width(border_thickness)
        cr.rectangle(0, 0, design_width, design_height)
        cr.stroke()
        cr.restore()

     # Set margins in inches and convert to pixels
    # Now define margins *inside* that design region
    margin_x = round(fixed_margin_in_inches * CURRENT_DPI)
    margin_y = round(fixed_margin_in_inches * CURRENT_DPI)

    # Determine data range for x and y
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min

   # 3) If we have a title, measure its pixel height

     # --- MODIFIED: Calculate Title/Author Band Height ---
    measured_title_height = 0
    measured_author_height = 0
    title_band_height = 0 # Total height reserved at the bottom
    effective_author_text = "" # Store measured author text

    if has_title == "YES":
        effective_title_text = title_text if title_text else story_data.get('title', '')
        if effective_title_text:
            layout_temp_title = PangoCairo.create_layout(cr)
            layout_temp_title.set_font_description(title_font_desc)
            layout_temp_title.set_text(effective_title_text, -1)
            _, measured_title_height = layout_temp_title.get_pixel_size()
            title_band_height += measured_title_height # Start with title height

            if author_text != "":
                effective_author_text = author_text
                if effective_author_text:
                    layout_temp_author = PangoCairo.create_layout(cr)
                    layout_temp_author.set_font_description(author_font_desc)
                    layout_temp_author.set_text(effective_author_text, -1)
                    _, measured_author_height = layout_temp_author.get_pixel_size()
                    # Add padding *between* title and author, then author height
                    title_band_height += author_padding + measured_author_height
                else:
                    # No author text, just add the title's own bottom padding
                    title_band_height += title_padding
            else:
                # No author requested, add title's own bottom padding
                 title_band_height += title_padding
        else:
            # No title text, band height is 0
            has_title = "NO" # Cannot draw title if text is empty
            has_author = "NO" # Cannot draw author if title isn't drawn

    # If title_band_height is still 0 (no title/author), set has_title/has_author to NO
    if title_band_height == 0:
        has_title = "NO"
        has_author = "NO"


    drawable_width = design_width - 2 * margin_x
    drawable_height = (design_height
                       - 2 * margin_y
                       - title_band_height # Use the combined height
                       - gap_above_title)

    # --- extra padding for PATH/TEXT ONLY (left, right, top) ---
    # inches; set to 0.10" for ~0.45" total side/top safe zone when your base is 0.25"
    TEXT_PAD_SIDE_IN = 0.2   # left and right only
    TEXT_PAD_TOP_IN  = 0.2   # top only

    pad_x   = round(TEXT_PAD_SIDE_IN * CURRENT_DPI)   # px
    pad_top = round(TEXT_PAD_TOP_IN  * CURRENT_DPI)   # px

    # Build a "path-only" box. Bottom stays anchored at (margin_y + drawable_height).
    path_margin_x      = margin_x + pad_x
    path_margin_y_top  = margin_y + pad_top
    path_drawable_w    = drawable_width  - 2 * pad_x
    path_drawable_h    = drawable_height - pad_top

    # NEW: scale for the PATH ONLY
    scale_x_path = path_drawable_w / x_range if x_range else 1
    scale_y_path = path_drawable_h / y_range if y_range else 1

    # NEW: alias so any existing code that references scale_x/scale_y
    # (angles, spacing, etc.) now uses the PATH scales automatically.
    scale_x = scale_x_path
    scale_y = scale_y_path

    if drawable_height <= 0:
         raise ValueError("Drawable height is zero or negative. Check margins, font sizes, paddings.")
    # --- END MODIFIED BAND HEIGHT & DRAWABLE AREA ---
    
    # 4) Compute scale factors & map your story arcs into [margin_y, margin_y+drawable_height]
    x_values = story_data['x_values']
    y_values = story_data['y_values']
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min

    # scale_x = drawable_width / x_range if x_range else 1
    # scale_y = drawable_height / y_range if y_range else 1

    # The bottom edge for arcs is margin_y + drawable_height
    # x_values_scaled = [(x - x_min)*scale_x + margin_x for x in x_values]
    # y_values_scaled = [
    #     (margin_y + drawable_height) - ((y - y_min)*scale_y)
    #     for y in y_values
    # ]
    x_values_scaled = [(x - x_min)*scale_x + path_margin_x for x in x_values]
    y_values_scaled = [
        (path_margin_y_top + path_drawable_h) - ((y - y_min)*scale_y)
        for y in y_values
    ]




    # Create a mapping from original to scaled coordinates
    coordinate_mapping = dict(zip(zip(x_values, y_values), zip(x_values_scaled, y_values_scaled)))

    # Now ready to draw arcs/text
    title = story_data.get('title', '')
    author = story_data.get('author', '')

    # -------------------------------------------------------------
    # Remove the old "title at top" code.
    # We'll draw the title *after* arcs, at the very bottom.
    # -------------------------------------------------------------

    # If line_type = 'line', just draw a line
    if line_type == "line":
        cr.set_source_rgb(*line_color)
        cr.set_line_width(line_thickness)

        cr.move_to(x_values_scaled[0], y_values_scaled[0])
        for sx, sy in zip(x_values_scaled[1:], y_values_scaled[1:]):
            cr.line_to(sx, sy)
        cr.stroke()

            # Respect output_format here
        

    elif line_type == "char":
        from scipy.interpolate import CubicSpline
        import numpy as np
        import copy
        begin_svg_group(cr, "main-text-path", output_format)
        
        

        # # Prepare for text on arcs
        # from gi.repository import Pango
        # font_size_for_300dpi = font_size * (300 / 96)
        # font_desc = Pango.FontDescription(f"{font_style} {font_size_for_300dpi}")
        arc_sample_text = ""
        all_rendered_boxes = []
        status = "completed"

        last_story_component_index = last_index = len(story_data['story_components']) - 1 

        for index, component in enumerate(story_data['story_components'][1:], start=1):
            arc_x_values = component.get('arc_x_values', [])
            arc_y_values = component.get('arc_y_values', [])
            description = component.get('description', '')

            if 'adjust_spacing' not in component:
                component['adjust_spacing'] = False

            if 'arc_manual_override' not in component:
                component['arc_manual_override'] = False
            
            if 'spacing_factor' not in component:
                component['spacing_factor'] = 1

            if not arc_x_values or not arc_y_values:
                continue

            # Scale arc coordinates
            arc_x_values_scaled = []
            arc_y_values_scaled = []
            for (xx, yy) in zip(arc_x_values, arc_y_values):
                if (xx, yy) in coordinate_mapping:
                    arc_x_values_scaled.append(coordinate_mapping[(xx, yy)][0])
                    arc_y_values_scaled.append(coordinate_mapping[(xx, yy)][1])
                else:
                    # fallback
                    # sx = (xx - x_min) * scale_x + margin_x
                    # sy = (margin_y + drawable_height) - ((yy - y_min) * scale_y)
                    sx = (xx - x_min) * scale_x + path_margin_x
                    sy = (path_margin_y_top + path_drawable_h) - ((yy - y_min) * scale_y)
                    arc_x_values_scaled.append(sx)
                    arc_y_values_scaled.append(sy)

            # Reverse scaling functions
            def reverse_scale_plot_points(scaled_x, old_min, old_max, new_min=1, new_max=10):
                return ((scaled_x - new_min) / (new_max - new_min)) * (old_max - old_min) + old_min

            def reverse_scale_y_values(scaled_y, old_min, old_max, new_min=-10, new_max=10):
                return ((scaled_y - new_min) / (new_max - new_min)) * (old_max - old_min) + old_min

            original_arc_end_time_values = [
                reverse_scale_plot_points(xv, old_min_x, old_max_x, new_min_x, new_max_x)
                for xv in arc_x_values
            ]
            original_arc_end_emotional_score_values = [
                reverse_scale_y_values(yv, old_min_y, old_max_y, new_min_y, new_max_y)
                for yv in arc_y_values
            ]

            # Draw the arc path (invisible stroke first)
            cr.set_line_width(2)
            cr.move_to(arc_x_values_scaled[0], arc_y_values_scaled[0])
            for sx, sy in zip(arc_x_values_scaled[1:], arc_y_values_scaled[1:]):
                cr.line_to(sx, sy)

            cr.set_source_rgba(0, 0, 0, 0)  # invisible
            cr.stroke()


            ### START OF BEBUG ###
            # --- DEBUG: DRAW THE CURVE SEGMENT ITSELF (thin line in its color) ---
            # current_segment_color_debug = next(color_cycle) # Get color for this debug segment
            # cr.save()
            # cr.set_source_rgb(*current_segment_color_debug)
            # cr.set_line_width(max(2, line_thickness / 5)) # Draw a thinner line for the segment path itself for debug
            # cr.move_to(arc_x_values_scaled[0], arc_y_values_scaled[0])
            # for sx_seg, sy_seg in zip(arc_x_values_scaled[1:], arc_y_values_scaled[1:]):
            #     cr.line_to(sx_seg, sy_seg)
            # cr.stroke()
            # cr.restore()

            # # --- DEBUG: DRAW MARKERS FOR START AND END OF THIS SCALED SEGMENT ---
            # # Marker at the start of this segment
            # current_segment_color_debug = next(color_cycle) # Get color for this debug segment
            # cr.save()
            # cr.set_source_rgb(*current_segment_color_debug) # Use a contrasting marker color
            # cr.arc(arc_x_values_scaled[0], arc_y_values_scaled[0], 7, 0, 2 * math.pi) # 7px radius circle
            # cr.fill()
            # # Optionally, add a number to the marker
            # layout_marker_idx = PangoCairo.create_layout(cr)
            # font_desc_marker = Pango.FontDescription(f"Sans Bold 12") # Small font for index
            # layout_marker_idx.set_font_description(font_desc_marker)
            # layout_marker_idx.set_text(str(index), -1)
            # mk_w, mk_h = layout_marker_idx.get_pixel_size()
            # cr.move_to(arc_x_values_scaled[0] + 10, arc_y_values_scaled[0] - mk_h / 2) # Offset slightly
            # PangoCairo.show_layout(cr, layout_marker_idx)
            # cr.restore()

            # # Marker at the end of this segment
            # cr.save()
            # cr.set_source_rgb(*marker_color_rgb)
            # cr.arc(arc_x_values_scaled[-1], arc_y_values_scaled[-1], 7, 0, 2 * math.pi)
            # cr.fill()
            # cr.restore()

            ### END OF BEBUG ###











            # Now set real color for text
            cr.set_source_rgb(*font_color)

            # Calculate arc length
            arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled)
            #ADDING 5/18/2025
            #average_rotation_angle = calculate_average_rotation_angle(arc_x_values_scaled, arc_y_values_scaled)


            # If arc_text not generated yet, do so

            create_descriptor = True
            if 'arc_text_valid' in component:
                if component['arc_text_valid'] == True:
                    create_descriptor = False
                
            if create_descriptor:

                if 'target_arc_text_chars' not in component:
                    #calculate target chars based on estimate of the number of chars that could fit in arc segment
                    average_char_width = get_average_char_width(pangocairo_context, font_desc, arc_sample_text)
                    average_rotation_angle = calculate_average_rotation_angle(arc_x_values_scaled, arc_y_values_scaled)
                    target_chars = estimate_characters_fit(arc_length, average_char_width, average_rotation_angle)
                    component['target_arc_text_chars'] = target_chars
                else:
                    target_chars = component['target_arc_text_chars']

                if target_chars < 5:
                    continue

                if index == 1 or index == last_story_component_index:
                    llm_target_chars = target_chars #set llm_target_chars to target chars because there's no net calc needed at this point
                else: #calc llm_target_chars considering net
                    llm_target_chars = target_chars - (story_data['story_components'][index - 1]['actual_arc_text_chars'] - story_data['story_components'][index - 1]['target_arc_text_chars_with_net'] )
                
                print("STORY COMPONENT INDEX: ", index)
                print("")

                if 'arc_text_valid_message' in component:
                    if component['arc_text_valid_message'] == "curve too long but can't change due to constraints":
                        print("old target chars: ", target_chars)
                        target_chars = target_chars + 3
                        component['target_arc_text_chars'] = target_chars
                        llm_target_chars = target_chars
                        print("updated target chars: ", llm_target_chars)
                    elif component['arc_text_valid_message'] == "curve too short but can't change due to constraints":
                        print("old target chars: ", target_chars)
                        target_chars = target_chars - 3
                        component['target_arc_text_chars'] = target_chars
                        llm_target_chars = target_chars
                        print("updated target chars: ", llm_target_chars)
                
                component['target_arc_text_chars_with_net'] = llm_target_chars #save net target in story data dict so it can be referenced in future 
                lower_bound = llm_target_chars - 3
                upper_bound = llm_target_chars + 3
                

                # Generate descriptors 
                descriptors_valid = False 
                reasonable_descriptiors_attempts = 1

                #generate descriptors 
                while descriptors_valid == False and reasonable_descriptiors_attempts <= 5:
                    descriptors_text = generate_descriptors(
                        title=story_data['title'],
                        author=story_data['author'],
                        protagonist=story_data['protagonist'],
                        component_description=description,
                        story_data=story_data,
                        desired_length=llm_target_chars,
                        llm_provider=llm_provider,
                        llm_model=llm_model,
                        config_path=config_path
                    )

                    descriptors_valid, descriptor_message = validate_descriptors(
                        descriptors_text=descriptors_text,
                        protagonist=story_data['protagonist'],
                        lower_bound=lower_bound,
                        upper_bound=upper_bound
                    )

                    #update descriptors text immediately if valid 
                    if descriptors_valid == True:
                        descriptors_text = descriptor_message

                      #if descriptors valid and it's the last index then remove the trailing space
                        if index == last_story_component_index:
                            if descriptors_text.endswith(' '): #check if ends in space
                                descriptors_text = descriptors_text[:-1] #remove last character (the space)
                                

                             
                    if 'arc_text' not in component:
                         component['arc_text_attempts'] = 1
                    else:
                        component['arc_text_attempts'] = component['arc_text_attempts'] + 1

                    component['arc_text'] = descriptors_text
                    component['actual_arc_text_chars'] = len(descriptors_text)
                    component['arc_text_valid'] = descriptors_valid
                    component['arc_text_valid_message'] = descriptor_message

                    
                   

                    actual_chars = len(descriptors_text)

                    if descriptors_valid == True:
                        print("#", reasonable_descriptiors_attempts,".) Descriptors Valid: ", descriptors_text, "(",actual_chars,"/",str(upper_bound-3),") -- LLM Char Target: ", llm_target_chars )

                        component['spaces_in_arc_text'] = component['arc_text'].count(' ')
                        component['spaces_width_multiplier'] = {}
                        component['space_to_modify'] = 0
                        for space_index in range(component['spaces_in_arc_text']):
                            component['spaces_width_multiplier'][space_index] = 1.0
                        component['spacing_adjustment_attempts'] = 0 # Reset total attempts for this new text
                        component['spacing_factor'] = 1
                        component['adjust_spacing'] = False
                        component['modified_end_time'] = component['end_time']
                        component['modified_end_emotional_score'] = component['end_emotional_score']
                    
                    else:
                        print("#", reasonable_descriptiors_attempts,".) Descriptors NOT Valid: ", descriptors_text, "Target Chars: ", llm_target_chars, " Error: ",  descriptor_message)

                        if (actual_chars - target_chars) > 50:
                            llm_target_chars = llm_target_chars - random.randint(20, 30) #if descriptors not even close > 10 chars away
                        elif (actual_chars - target_chars) > 20 and (actual_chars - target_chars) <= 50:
                            llm_target_chars = llm_target_chars - random.randint(13, 17) #if descriptors not even close > 10 chars away
                        elif (actual_chars - target_chars) > 10 and (actual_chars - target_chars) <= 20:
                            llm_target_chars = llm_target_chars - random.randint(4, 9) #if descriptors not even close > 10 chars away
                        elif (actual_chars - target_chars) > 5 and (actual_chars - target_chars) <= 10:
                            llm_target_chars = llm_target_chars - random.randint(3, 5) #if descriptors not even close > 10 chars away
                        elif (actual_chars - target_chars) > 0 and (actual_chars - target_chars) <= 5:
                            llm_target_chars = llm_target_chars - random.randint(1, 2) #if descriptors not even close > 10 chars away
                        elif (actual_chars - target_chars) < 0 and (actual_chars - target_chars) >= -5:
                            llm_target_chars = llm_target_chars + random.randint(1, 2)
                        elif (actual_chars - target_chars) < -5 and (actual_chars - target_chars) >= -10:
                            llm_target_chars = llm_target_chars + random.randint(3, 4)
                        elif (actual_chars - target_chars) < -10:
                            llm_target_chars = llm_target_chars + random.randint(4, 5)
                    
                    reasonable_descriptiors_attempts = reasonable_descriptiors_attempts + 1

                if descriptors_valid == False:
                    if story_data is None:
                        print("STORY DATA NONE -- 9")

                    return story_data, "error"
                
                if component['arc_text_attempts'] > 10:
                    print("❌ Max attempts to create descriptors exceeded")
                    if story_data is None:
                        print("STORY DATA NONE -- 10")
                    return story_data, "error"
                
            else:
                descriptors_text = component['arc_text']
                component['actual_arc_text_chars'] = len(descriptors_text)


            arc_sample_text += " " + descriptors_text

            # --- START OF NEW CALCULATIONS FOR DETAILED MESSAGES ---
            # if descriptors_text:
            #     current_avg_char_width = get_average_char_width(pangocairo_context, font_desc, descriptors_text)
            # else:
            #     current_avg_char_width = get_average_char_width(pangocairo_context, font_desc, "a")

            # if current_avg_char_width > 0:
            #     ideal_chars_for_this_curve = estimate_characters_fit(arc_length, current_avg_char_width, average_rotation_angle)
            # else:
            #     ideal_chars_for_this_curve = 0

            # actual_chars_in_current_text = len(descriptors_text)
            # # --- END OF NEW CALCULATIONS ---

            #  # Convert to NumPy arrays before passing to draw_text_on_curve
            # arc_x_values_scaled_np = np.array(arc_x_values_scaled)
            # arc_y_values_scaled_np = np.array(arc_y_values_scaled)

            # # Calculate arc length
            # # arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled) # Original
            # arc_length = calculate_arc_length(arc_x_values_scaled_np, arc_y_values_scaled_np) # Use NP array
            
            # #ADDING 5/18/2025
            # # average_rotation_angle = calculate_average_rotation_angle(arc_x_values_scaled, arc_y_values_scaled) # Original
            # average_rotation_angle = calculate_average_rotation_angle(arc_x_values_scaled_np, arc_y_values_scaled_np) # Use NP array

            
            
            # Draw text on curve
            curve_length_status = draw_text_on_curve(
                cr=cr,
                x_values_scaled=arc_x_values_scaled,
                y_values_scaled=arc_y_values_scaled,
                text=descriptors_text,
                pangocairo_context=pangocairo_context,
                font_desc=font_desc,
                all_rendered_boxes=all_rendered_boxes,
                margin_x=margin_x, 
                margin_y=margin_y, 
                design_width=design_width, 
                design_height=design_height,
                spaces_width_multiplier=component['spaces_width_multiplier'],
                adjust_spacing=component['adjust_spacing']
            )

            min_space_multipler = min(component['spaces_width_multiplier'].values())
            max_space_multipler = max(component['spaces_width_multiplier'].values())
            #print(curve_length_status)
            # Check if curve too short/long, do your recursion logic...
            if curve_length_status == "curve_too_short":
                # Attempt adjusting via CubicSpline
                x_og = np.array(original_arc_end_time_values)
                y_og = np.array(original_arc_end_emotional_score_values)
                sorted_indices = np.argsort(x_og)
                x_og = x_og[sorted_indices]
                y_og = y_og[sorted_indices]

                # Check that we have at least two points before proceeding with CubicSpline
                if len(x_og) < 2:
                    print("CALLING TO SEE IF THERE'S LESS THAN 2 before removing dups")
                    print("original_arc_end_time_values: ", original_arc_end_time_values)

                # Remove duplicates
                tolerance = 1e-12
                unique_indices = [0]
                for i in range(1, len(x_og)):
                    if x_og[i] - x_og[unique_indices[-1]] > tolerance:
                        unique_indices.append(i)
                x_og = x_og[unique_indices]
                y_og = y_og[unique_indices]

                # Check that we have at least two points before proceeding with CubicSpline
                if len(x_og) < 2:
                    print("Not enough points for cubic spline adjustment; skipping cubic spline update.")
                    print("X_og: ", x_og)
                    # You can decide to either return an error status, skip the adjustment, or use a fallback
                    # For instance, set the status to "error" or simply continue:
                    if story_data is None:
                        print("STORY DATA NONE -- 11")

                    return story_data, "error"  # or handle it in another way

                #print("X: ", x_og)
                cs = CubicSpline(x_og, y_og, extrapolate=True)
                new_x = x_og[-1] + (x_og[1] - x_og[0])
                new_y = float(cs(new_x))

                # print(new_x, " , ", new_y)
                # print(old_max_y, " , ", old_min_y)

                #normal mode
                if (new_x >= old_min_x and new_x <= old_max_x 
                    and new_y >= old_min_y and new_y <= old_max_y
                    and recursive_mode
                    and component['adjust_spacing'] == False):
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y
                    
                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 12")

                    return story_data, "processing"

                #this really only works if like this was suppose to be the last story segment
                # we hit x max and want to extend y
                elif ((new_x >= old_max_x or new_x <= old_min_x) and (new_y >= old_min_y and new_y <= old_max_y) and recursive_mode and component['end_time'] == 100 and (round(new_y,2) != round(y_og[-1],2))
                      and component['adjust_spacing'] == False):
                    new_x = x_og[-1]
                    #print(round(new_y,3), " != ", round(y_og[-1],3)) 
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y

                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 13")

                    return story_data, "processing"
                
                # #we hit y max / min and need to extend x
                elif ((new_y >= old_max_y or new_y <= old_min_y) and (new_x >= old_min_x and new_x <= old_max_x) and recursive_mode 
                      and component['adjust_spacing'] == False):
                    #print("#we hit y max / min and need to extend x")
                    new_y = y_og[-1]
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y

                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 1")
                    
                    return story_data, "processing"
            
                elif component['spacing_adjustment_attempts'] < MAX_SPACING_ADJUSTMENT_ATTEMPTS and component['space_to_modify'] < component['spaces_in_arc_text'] and component["spacing_factor"] < 1000:
                    component['adjust_spacing'] = True

                    #adjust current multiplier
                    if component.get('status', "") == "expanding spacing":
                        print("spacing factor change")
                        component["spacing_factor"] = component["spacing_factor"] * 10
                    
                    try:
                        new_multiplier = max(0.8, component['spaces_width_multiplier'][component['space_to_modify']] - (0.1 / component["spacing_factor"]))
                        component['spaces_width_multiplier'][component['space_to_modify']] = new_multiplier
                    except:
                        new_multiplier = max(0.8, component['spaces_width_multiplier'][str(component['space_to_modify'])] - (0.1 / component["spacing_factor"]))
                        component['spaces_width_multiplier'][str(component['space_to_modify'])] = new_multiplier
                    
                    if new_multiplier == .8:
                        component['space_to_modify'] = component['space_to_modify'] + 1
                        print("NEW SPACE TO MODIFY: ", component['space_to_modify'])
                  

                    #adjust future mulitplier
                    #component['spaces_width_multiplier'][component['space_to_modify']] = component['spaces_width_multiplier'][component['space_to_modify']] - 0.01
                    component['spacing_adjustment_attempts'] = component['spacing_adjustment_attempts'] + 1

                    component['status'] = "reducing spacing"
                    

                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 2")
                    return story_data, "processing"
            
                else: #this means: "curve too short but can't change due to constraints"
                    #so we actually want less chars than we initially thought
                    maybe_save(surface, story_shape_path, output_format, save_intermediate)


                    if component['arc_manual_override'] == True:
                        status = 'Manual Override'
                    # if component['adjust_spacing'] == True:
                    #     status = 'Close Enough!'
                    #     #print("CLOSE ENOUGH!")
                    else:
                        component['arc_text_valid'] = False
                        component['arc_text_valid_message'] = "curve too short but can't change due to constraints"
                        print("curve too short but can't change due to constraints")
                        #status = "curve too short but can't change due to constraints"
                        print("spacing attempts: ", component['spacing_adjustment_attempts'])
                        print("max_space_multipler: ", min_space_multipler)
                        print("spacing_factor: ", component['spacing_factor'])


                        if story_data is None:
                            print("STORY DATA NONE -- 3")

                        return story_data, "processing"


            #curve is too long so need to shorten it
            elif curve_length_status == "curve_too_long":

                #doing - 10 is super janky; the problem is that num a points is fixed so if you make arc length smaller but keep number of points the same then decreasing arc like becomes hard
                #an alternative apprach is instead of defining num of point you could define x_delta size and infer num of points
                original_arc_end_time_index_length = len(original_arc_end_time_values) - 3
                original_arc_end_emotional_score_index_length = len(original_arc_end_emotional_score_values) - 3
                
                #print(original_arc_end_time_values[original_arc_end_time_index_length], " : ", original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length])

                #check if last values of arc segments is the global max; if it's the global max then shouldn't touch unless the second to last is the same value then you can shorten it
                #normal mode can decrease everything 
                if (original_arc_end_time_values[-1] > old_min_x 
                    and original_arc_end_time_values[-1] < old_max_x
                    and original_arc_end_emotional_score_values[-1] > old_min_y
                    and original_arc_end_emotional_score_values[-1] < old_max_y
                    and len(component['arc_x_values']) > 1 and recursive_mode
                    and original_arc_end_time_index_length >= 0 
                    and original_arc_end_emotional_score_index_length >= 0
                    and component['adjust_spacing'] == False):
                    
                    component['modified_end_time'] = original_arc_end_time_values[original_arc_end_time_index_length]
                    component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length]
                    
                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 4")

                    return story_data, "processing"
                
                #cant touch x -- maybe want to remove
                elif ((original_arc_end_time_values[-1] == old_min_x or original_arc_end_time_values[-1] == old_max_x)
                    and original_arc_end_emotional_score_values[-1] > old_min_y
                    and original_arc_end_emotional_score_values[-1] < old_max_y
                    and len(component['arc_x_values']) > 1 and recursive_mode 
                    and round(original_arc_end_emotional_score_values[-1],3) != round(original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length],3)
                    and original_arc_end_emotional_score_index_length >= 0
                    and component['adjust_spacing'] == False):

                    component['modified_end_time'] = original_arc_end_time_values[-1]
                    component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length]
                    
                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 5")

                    return story_data, "processing"
                
                # #cant touch y
                # elif ((original_arc_end_emotional_score_values[-1] == old_min_y or original_arc_end_emotional_score_values[-1] == old_max_y)
                #     and original_arc_end_time_values[-1] > old_min_x 
                #     and original_arc_end_time_values[-1] < old_max_x
                #     and len(component['arc_x_values']) > 1 and recursive_mode
                #     and original_arc_end_time_index_length >= 0):

                #     #print("hey")
                #     print("modifying end time")
                #     component['modified_end_time'] = original_arc_end_time_values[original_arc_end_time_index_length]
                #     component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[-1]

                #     if output_format == "svg":
                #         surface.flush()   # flush the partial drawing, but do *not* finalize!
                #     else:
                #         surface.write_to_png(story_shape_path)
                #     return story_data, "processing"

                elif component['spacing_adjustment_attempts'] < MAX_SPACING_ADJUSTMENT_ATTEMPTS and component['space_to_modify'] < component['spaces_in_arc_text'] and component["spacing_factor"] < 1000:
                    component['adjust_spacing'] = True
                    
                    if component.get('status', "") == "reducing spacing":
                        print("spacing factor change")
                        component["spacing_factor"] = component["spacing_factor"] * 10
                    
                    try:
                        new_multiplier = min(1.5, component['spaces_width_multiplier'][component['space_to_modify']] + (0.1 / component["spacing_factor"]))
                        component['spaces_width_multiplier'][component['space_to_modify']] = new_multiplier
                    except:
                        new_multiplier = min(1.5,component['spaces_width_multiplier'][str(component['space_to_modify'])] + (0.1 / component["spacing_factor"]))
                        component['spaces_width_multiplier'][str(component['space_to_modify'])] = new_multiplier
                    
                    if new_multiplier == 1.5:
                        component['space_to_modify'] = component['space_to_modify'] + 1
                        print("NEW SPACE TO MODIFY: ", component['space_to_modify'])
                    

                     #adjust next multiplier
                    #component['spaces_width_multiplier'][component['space_to_modify']] = component['spaces_width_multiplier'][component['space_to_modify']] + 0.01
                    component['spacing_adjustment_attempts'] = component['spacing_adjustment_attempts'] + 1
                    
                    component['status'] = "expanding spacing"

                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if story_data is None:
                        print("STORY DATA NONE -- 6")

                    return story_data, "processing"

                else: # this means: curve too long but can't change due to constraints
                    # so we want more chars than we initially thought so let's up the number of chars
                    # so we need recalc descriptors and ask for longer 
                    maybe_save(surface, story_shape_path, output_format, save_intermediate)

                    if component['arc_manual_override'] == True:
                        status = 'Manual Override'
                    # elif component['adjust_spacing'] == True:
                    #     status = 'Close Enough'
                        #print("CLOSE ENOUGH!")
                    else:
                        component['arc_text_valid'] = False
                        component['arc_text_valid_message'] = "curve too long but can't change due to constraints"
                        print("curve too long but can't change due to constraints")
                        print("spacing attempts: ", component['spacing_adjustment_attempts'])
                        print("max_space_multipler: ", max_space_multipler)
                        print("spacing_factor: ", component['spacing_factor'])

                        if story_data is None:
                            print("STORY DATA NONE -- 7")

                        return story_data, "processing"

            elif curve_length_status == "curve_correct_length":
                maybe_save(surface, story_shape_path, output_format, save_intermediate)

                status = 'All phrases fit exactly on the curve.'

            component['status'] = status


        # --- MODIFICATION: End main text group ---
        end_svg_group(cr, output_format)
        # -----------------------------------------

   #  --- Draw Title, Author, Protagonist ---
    # These variables will store the calculated positions needed later
    title_y = 0
    title_text_height = 0
    author_y = 0
    author_text_height = 0

    if has_title == "YES":
        # --- Draw Title ---
        final_layout_title = PangoCairo.create_layout(cr)
        final_layout_title.set_font_description(title_font_desc)
        final_layout_title.set_text(effective_title_text, -1)
       
        if title_font_underline:
            attr_list_title = Pango.AttrList(); underline_attr_title = Pango.attr_underline_new(Pango.Underline.SINGLE); attr_list_title.insert(underline_attr_title); final_layout_title.set_attributes(attr_list_title)

        title_text_width, title_text_height = final_layout_title.get_pixel_size() # Store measured height
        title_band_top = margin_y + drawable_height + gap_above_title
        title_x = margin_x
        title_y = title_band_top # Store title Y position

        begin_svg_group(cr, "title-group", output_format)
        cr.move_to(title_x, title_y)
        cr.set_source_rgb(*title_font_color) # Use RGB
        PangoCairo.show_layout(cr, final_layout_title)
        end_svg_group(cr, output_format)
        # --- End Draw Title ---

        # --- Draw Author ---
        if effective_author_text != "":
            final_layout_author = PangoCairo.create_layout(cr)
            final_layout_author.set_font_description(author_font_desc)
            final_layout_author.set_text(effective_author_text, -1)
            if author_font_underline:
                # ... (add underline attribute) ...
                 attr_list_author = Pango.AttrList(); underline_attr_author = Pango.attr_underline_new(Pango.Underline.SINGLE); attr_list_author.insert(underline_attr_author); final_layout_author.set_attributes(attr_list_author)


            author_text_width, author_text_height = final_layout_author.get_pixel_size() # Store measured height
            author_x = title_x
            author_y = title_y + title_text_height + author_padding # Store author Y

            begin_svg_group(cr, "author-group", output_format)
            cr.move_to(author_x, author_y)
            cr.set_source_rgb(*author_font_color) # Use RGB
            PangoCairo.show_layout(cr, final_layout_author)
            end_svg_group(cr, output_format)
        # --- End Draw Author ---

        # --- Draw Protagonist ---
        # effective_protagonist_text = protagonist_text if protagonist_text else story_data.get('protagonist', '')
        # if effective_protagonist_text:
        #     prot_layout = PangoCairo.create_layout(cr)
        #     prot_layout.set_font_description(protagonist_font_desc)
        #     prot_layout.set_text(effective_protagonist_text, -1)
        #     if protagonist_font_underline:
        #         # ... (add underline attribute) ...
        #         attr_list_prot = Pango.AttrList(); underline_attr_prot = Pango.attr_underline_new(Pango.Underline.SINGLE); attr_list_prot.insert(underline_attr_prot); prot_layout.set_attributes(attr_list_prot)

        #     prot_text_width, prot_text_height = prot_layout.get_pixel_size()

        #     # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        #     # --- THE SINGLE PLACE TO CHANGE PROTAGONIST ALIGNMENT ---

        #     # Option 1: Align Protagonist Bottom with TITLE Bottom
        #     target_bottom_line = title_y + title_text_height

        #     # Option 2: Align Protagonist Bottom with AUTHOR Bottom
        #     # To use this: COMMENT OUT the line above and UNCOMMENT the 4 lines below.
        #     # Make sure 'has_author="YES"' and author text exists when uncommenting!
        #     # if effective_author_text != "":
        #     #     target_bottom_line = author_y + author_text_height
        #     # else: # Fallback if author isn't shown but you tried to align
        #     #     target_bottom_line = title_y + title_text_height

        #     # --- END OF ALIGNMENT CHANGE SECTION ---
        #     # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        #     # Calculate protagonist Y based on the chosen target line
        #     prot_y = target_bottom_line - prot_text_height
        #     prot_x = margin_x + drawable_width - prot_text_width # Right aligned

        # --- Draw Protagonist ---
        # --- Draw Protagonist ---
       # --- Draw Protagonist ---
        effective_protagonist_text = protagonist_text if protagonist_text else story_data.get('protagonist', '')
        if effective_protagonist_text:
            prot_layout = PangoCairo.create_layout(cr)
            prot_layout.set_font_description(protagonist_font_desc)
            prot_layout.set_text(effective_protagonist_text, -1)
            if protagonist_font_underline:
                attr_list_prot = Pango.AttrList()
                underline_attr_prot = Pango.attr_underline_new(Pango.Underline.SINGLE)
                attr_list_prot.insert(underline_attr_prot)
                prot_layout.set_attributes(attr_list_prot)

            prot_text_width, _ = prot_layout.get_pixel_size() # Still need width for x-pos

            # --- Configurable BASELINE Alignment Logic (More Robust) ---
            # This method aligns the text baselines for a perfect visual line.

            # Determine the target baseline's Y-coordinate based on the chosen alignment target.
            #protagonist_alignment_target = "title"
            protagonist_alignment_target = "author"
            if protagonist_alignment_target == 'author' and effective_author_text:
                # Target the author's baseline if it exists and is the chosen target.
                # (final_layout_author is defined in the author drawing block from earlier)
                author_baseline_offset = final_layout_author.get_baseline() / Pango.SCALE
                target_baseline_y = author_y + author_baseline_offset
            else:
                # Default to aligning with the title's baseline.
                title_baseline_offset = final_layout_title.get_baseline() / Pango.SCALE
                target_baseline_y = title_y + title_baseline_offset

            # Calculate the protagonist's top Y-coordinate to align its baseline with the target baseline.
            prot_baseline_offset = prot_layout.get_baseline() / Pango.SCALE
            prot_y = target_baseline_y - prot_baseline_offset

            # Calculate the X position for right-alignment.
            prot_x = margin_x + drawable_width - prot_text_width

            begin_svg_group(cr, "protagonist-group", output_format)
            cr.move_to(prot_x, prot_y)
            cr.set_source_rgb(*protagonist_font_color)
            PangoCairo.show_layout(cr, prot_layout)
            end_svg_group(cr, output_format)
        # --- End Draw Protagonist ---


        #     begin_svg_group(cr, "protagonist-group", output_format)
        #     cr.move_to(prot_x, prot_y)
        #     cr.set_source_rgb(*protagonist_font_color) # Use RGB
        #     PangoCairo.show_layout(cr, prot_layout)
        #     end_svg_group(cr, output_format)
        # # --- End Draw Protagonist ---


        # --- MODIFICATION: End Title Group ---
       # --- End Title/Author/Protagonist Block ---


    # MAKE NOTES ON TOP AND BOTTOM OF CANVAS -- only applies when wrap_in_inches > 0
    cr.restore()  # <== restore out of that translation


    if wrap_in_inches > 0:

        if top_text == "":

            author = story_data.get('author','')
            year = story_data.get('year', '')
            if(author == '' and year == ''):
                top_text = ""
            elif(author == '' and year != ''):
                top_text = year 
            elif(author != '' and year == ''):
                top_text = author
            elif(author != '' and year != ''):
                top_text = author + ", " + year
            else:
                top_text = ""

      
        x_top_center = total_width_px / 2
        band_height_top = top_and_bottom_text_band * CURRENT_DPI  # 1.5" band
        band_start_top = design_offset_y - band_height_top  # upper edge of top band
        band_end_top   = design_offset_y                    # shape starts here

        y_top_center = band_start_top + (band_height_top / 2)
       

        place_text_centered(cr,
                            text=top_text,
                            font_size_px=top_text_font_size_for_300dpi,
                            font_face = top_text_font_style,
                            x_center=x_top_center,
                            y_center=y_top_center,
                            rotation_degrees=0,
                            color= (top_text_font_color))

        # 3) Place text on bottom edge, fully centered
        bottom_wrap_y = design_offset_y + design_height  # The shape ends here
        band_height_bottom = top_and_bottom_text_band * dpi                   # Another 1.5" band
        band_start_bottom = bottom_wrap_y
        band_end_bottom   = bottom_wrap_y + band_height_bottom

        x_bottom_center = total_width_px / 2
        y_bottom_center = band_start_bottom + (band_height_bottom / 2)


        if bottom_text == "":
            bottom_text = "THE SHAPES OF STORIES, LLC"
        place_text_centered(cr,
                            text=bottom_text,
                            font_size_px=bottom_text_font_size_for_300dpi,
                            font_face = bottom_text_font_style,
                            color = bottom_text_font_color,
                            x_center=x_bottom_center,
                            y_center=y_bottom_center,
                            rotation_degrees=0)


    
    # 7) Save final image
    if output_format == "svg":
        surface.finish()
    else:
        surface.write_to_png(story_shape_path)

    # 8) QUICK AUDIT (skip for SVG)
    if output_format == "png":
        try:
            margins = verify_safe_margin(
                path=story_shape_path,
                bg_rgb=tuple(int(c*255) for c in background_value),
                dpi=CURRENT_DPI,                    # ← match your real DPI
                margin_in=fixed_margin_in_inches,
                tolerance_px=0             # or 1–2 px if you prefer
            )
            print("✅ margin check:", margins, "px")
        except ValueError as e:
            print(e)
        # optionally: raise, or set status="error", etc.
    if story_data is None:
        print("STORY DATA NONE -- 8")
    return story_data, "completed"


def calculate_arc_length(arc_x_values, arc_y_values):
    segment_lengths = np.hypot(
        np.diff(arc_x_values), np.diff(arc_y_values)
    )
    total_length = np.sum(segment_lengths)
    return total_length

def get_average_char_width(pangocairo_context, font_desc, sample_text=None):
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)

    if sample_text is None or sample_text == "":
        sample_text = (
            "Nervous. First Day. Office. Challenges. Potential."
        )
    layout.set_text(sample_text, -1)
    total_width = layout.get_pixel_size()[0]
    num_chars = len(sample_text.replace(" ", ""))
    average_char_width = total_width / num_chars
    return average_char_width


def estimate_characters_fit(arc_length, average_char_width, average_rotation_angle=0, spacing=1.0):
    rotation_adjustment = 1 + (abs(math.sin(math.radians(average_rotation_angle))) * 0.1)
    adjusted_char_width = average_char_width * rotation_adjustment * spacing
    return int(arc_length / adjusted_char_width)

def calculate_average_rotation_angle(x_values, y_values):
    angles = []
    for idx in range(1, len(x_values)):
        dx = x_values[idx] - x_values[idx - 1]
        dy = y_values[idx] - y_values[idx - 1]
        angle = math.degrees(math.atan2(dy, dx))
        angles.append(angle)
    average_angle = sum(angles) / len(angles)
    return average_angle


def generate_descriptors(title, author, protagonist, component_description, story_data, desired_length, llm_provider, llm_model, config_path):
    
    existing_arc_texts = "\n".join(
        component.get('arc_text', '') 
        for component in story_data['story_components'] 
        if 'arc_text' in component
    )
    
    if existing_arc_texts:
        existing_arc_texts = f"Previous descriptions:\n{existing_arc_texts}"

    
    prompt_template = """ ## INSTRUCTIONS 
Your task is to identify and express the most significant moments from this segment of {author}'s "{title}". Create a series of precise phrases that capture {protagonist}'s key story beats, fitting exactly {desired_length} characters.

## STORY SEGMENT DESCRIPTION:
{component_description}

## REQUIREMENTS:
1. CONTENT:
    - USE ONLY elements directly from the provided STORY SEGMENT DESCRIPTION
    - FOCUS on the perspective of {protagonist} 
    - SELECT concrete actions, events, places, objects, people
    - PRIORITIZE the most significant moments and actions pertaining to {protagonist}'s story
    - NEVER mention {protagonist} by name

2. FORMAT: 
    - BE CONCISE, descriptors should consist of 1-4 word phrases
    - A single phrase is perfectly acceptable 
    - If multiple phrases, each ends with ". " except the last phrase, which ends with just "." and no space
    - CAPITALIZATION: Use Title Case (capitalize the first letter of every word, except minor words like "and," "of," "the," unless they are the first word of a phrase)
    
3. PHRASE CONSTRUCTION:
    - CAPTURE the progression of events that drive the story forward
    - Break compound actions into separate phrases
    - AVOID redundant information across phrases
    - Each phrase should capture a complete, meaningful story beat

4. PHRASE ORDERING: 
    - The order of the phrases MUST be in chronological order as events occur in STORY SEGMENT DESCRIPTION
    - Each phrase should flow naturally into the next to tell a coherent story of {protagonist} 

5. CONTINUITY:
    - Each story segment descriptors joins with other story segments to tell the full {protagonist}'s story
    - Descriptors should be distinct from previous story segment descriptors: {existing_arc_texts}

6. LENGTH: OUTPUT MUST BE EXACTLY {desired_length} CHARACTERS. NO MORE, NO LESS
    - Count EVERY character including spaces and periods
    - Count EVERY period and space between phrases
    - Example: "Green Light." is 12 characters
    
7. VERIFICATION:
    Step 1: Verify Narrative Quality
    - Do phrases capture the most important story moments?
    - Are events in correct chronological order?
    - Does each phrase advance the story?

    Step 2: Verify Technical Requirements
    - Count all characters (including spaces and periods)
    - Check format and capitalization
    - Confirm no protagonist name used
    - Verify source material accuracy

8. OUTPUT: Provide ONLY the descriptor text, exactly {desired_length} characters. No explanation. 


## EXAMPLES:

### EXAMPLE 1
Length Requirements: 12 characters
Author: F. Scott Fitzgerald
Title: The Great Gatsby
Protagonist: Jay Gatsby
Story Segment Description: "Gatsby stands alone in his garden, reaching out towards the green light across the bay, embodying his yearning for Daisy. His elaborate mansion and lavish parties serve as carefully orchestrated attempts to attract her attention, revealing both his hope and desperation. When he finally arranges to meet Nick, his neighbor and Daisy's cousin, Gatsby's carefully constructed facade begins to show cracks of vulnerability as he seeks a way to reconnect with his lost love"

Potential Phrases (with character counts including ending punctuation) -- note phrases shown are non-exhaustive and are just meant to provide examples of potential phrases
- "Alone in Garden." (16 characters)
- "Green Light."  (12 characters)
- "Yearning for Daisy." (20 characters)
- "Lost Love." (10 characters)

Selected Output (12 characters): "Green Light."


### EXAMPLE 2
Length Requirements: 37 characters
Author: Ernest Hemingway
Title: The Old Man and the Sea
Protagonist: Santiago
Story Segment Description: "Despite 84 days without a catch and being considered unlucky, Santiago maintains his dignity and optimism. His friendship with Manolin provides comfort and support, though the boy has been forced to work on another boat. His determination remains strong as he prepares for a new day of fishing, finding peace in his dreams of Africa and its lions."

Potential Phrases -- note phrases shown are non-exhaustive:
- "84 Days No Fish." (16 characters)
- "Unlucky." (8 characters)
- "Optimist." (9 characters)
- "Manolin Friendship." (19 characters)
- "Preps for Fishing." (18 characters)
- "Dreams of Africa." (16 characters)

Selected Output (37 characters): "84 Days. No Fish. Manolin Friendship."


### EXAMPLE 3
Length Requirements: 79 characters
Author: William Shakespeare
Title: Romeo and Juliet
Protagonist: Juliet
Story Segment Description: "Juliet awakens to find Romeo dead beside her, having poisoned himself in the belief she was dead. In her final moments, she experiences complete despair, attempting to die by kissing his poisoned lips before ultimately using his dagger to join him in death, unable to conceive of life without him."

Potential Phrases -- note phrases shown are non-exhaustive:
- "Awakens." (8 characters)
- "Romeo Dead." (11 characters)
- "Despair." (8 characters)
- "Kisses Poisoned Lips." (21 characters)
- "Suicide by Dagger." (18 characters)
- "Reunited with Love." (19 characters)

Selected Output (79 characters): "Awakens. Romeo Dead. Complete Despair. Kisses Poisoned Lips. Suicide by Dagger."

Notes for All Examples:
- Each phrase except the last ends with ". " (period + space = 2 chars). The last phrase ends with "." (period only = 1 char)
- Phrases appear in chronological order as events occur in Story Segment Description
- Character counts include the space after the period in ALL phrases

________

Respond with ONLY the descriptor text, exactly {desired_length} characters. No explanation.
"""
    
    prompt = PromptTemplate(
        input_variables=["desired_length", "author", "title", "protagonist", "component_description", "existing_arc_texts"],  # Define the expected inputs
        template=prompt_template
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=500)

     # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    # Then invoke with the required inputs:
    output = runnable.invoke({
        "desired_length": desired_length,
        "author": author,
        "title": title,
        "protagonist": protagonist,
        "component_description":component_description,
        "existing_arc_texts":existing_arc_texts,
    })

    #print(output)
    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
    
    output_text = output_text.strip()
    return output_text

import numpy as np
import math
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity
import re
from gi.repository import Pango, PangoCairo # Ensure these are imported at the top of your file


# Ensure these are imported at the top of your story_shape.py
import numpy as np
import math
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity
import re
from gi.repository import Pango, PangoCairo

# ... (your other helper functions like get_average_char_width, pango_font_exists etc.)
# story_shape.py (helper function, can be near other Pango helpers)

# story_shape.py

# ... (other imports)

def get_standard_space_width(pangocairo_context, font_desc):
    """
    Gets the pixel width of a standard space character for the given font,
    without any dynamic char_spacing_factor or space_width_multiplier applied.
    """
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)
    layout.set_text(" ", -1)  # A single space character
    width, _ = layout.get_pixel_size()
    # It's possible for a font to have a zero-width space, handle defensively.
    return width if width > 0 else 1 # Return at least 1px to avoid division by zero later



#### THE OLD STORY FUNCTION CODE ###

import pandas as pd
import numpy as np
import json
import itertools
import math


def find_breakpoints(x, y, threshold = 1.0):
    step_points = []
    for i in range(1, len(y)):
        if abs(y[i] - y[i-1]) >= threshold:
            step_points.append(x[i-1])
    return step_points


def insert_points(x, y, num_insert_points, threshold=1.0):
    breakpoints = find_breakpoints(x, y, threshold)
    new_x, new_y = [], []

    for i in range(len(x)):
        new_x.append(x[i])
        new_y.append(y[i])

        if i < len(x) - 1 and x[i] in breakpoints:
            y_increment = (y[i+1] - y[i]) / (num_insert_points + 1)
            for j in range(1, num_insert_points + 1):
                new_x.append(x[i])
                new_y.append(y[i] + j * y_increment)

    return new_x, new_y


#scale plot points to numbers 1 - 10 for consistency across stories
def scale_plot_points(original_plot_points, new_min, new_max):
    old_min = np.min(original_plot_points)
    old_max = np.max(original_plot_points)
    scaled_plot_points = new_min + ((original_plot_points - old_min) / (old_max - old_min)) * (new_max - new_min)
    return scaled_plot_points


def scale_y_values(y_values, new_min, new_max):
    old_min = np.min(y_values)
    old_max = np.max(y_values)
    if old_max == old_min:
        # Avoid division by zero if all y_values are the same
        return np.full_like(y_values, new_min)
    scaled_values = ((y_values - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
    return scaled_values
   


def get_component_arc_function(x1, x2, y1, y2, arc, step_k=15, max_num_steps=3):

    def exponential_step_function(x):
        # 1) If out of range, return None
        if not (x1 <= x <= x2):
            return None
        
        # 2) Decide how many steps you want
        # num_steps = int(math.ceil(x2 - x1))
        # if num_steps < 1:
        #     num_steps = 1
        # elif num_steps > 3:
        #     num_steps = 3


        # distance = math.hypot(x2 - x1, y2 - y1)  # sqrt(dx^2 + dy^2)
        # # Then map distance to [1..3] steps, for example:
        # if distance < 1:
        #     num_steps = 1
        # elif distance < 3:
        #     num_steps = 2
        # else:
        #     num_steps = 3

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx == 0:
            # Avoid dividing by zero
            slope = float('inf')
        else:
            slope = dy / dx

        # Example rule:
        # - if slope is small (< ~ 0.5), only 1 step
        # - if slope is moderate, use 2 steps
        # - if slope is steep, use 3 steps

        if slope < 0.5:
            num_steps = 1
        elif slope < 3.0:
            num_steps = 2
        else:
            num_steps = max_num_steps
        
        
        # 3) We create the sub-intervals
        x_edges = np.linspace(x1, x2, num_steps + 1)  # e.g. [x1, x1+1, x1+2, ..., x2]
        # total change in y is (y2 - y1)
        dy = (y2 - y1) / num_steps
        
        # 4) Find which step i such that x_edges[i] <= x <= x_edges[i+1]
        # e.g. loop or use a quick search:
        for i in range(num_steps):
            start = x_edges[i]
            end   = x_edges[i+1]
            
            if start <= x <= end:
                # y_base is the bottom of step i
                y_base = y1 + i * dy
                
                # now define an exponential from y_base up to y_base + dy
                # choose a k (steepness)
                k = step_k  # or 10, or something user-chosen
                # map x into [0..1] for exponential
                alpha = (x - start) / (end - start)  # 0 to 1
                # standard increase formula:
                local_y = y_base + dy * (1 - math.exp(-k * alpha))
                return local_y
        
        # If x somehow equals x2 exactly, let's ensure we return y2
        return y2


    def s_curve_step_function(x):
        """
        Returns an S-curve-based step interpolation for the interval [x1, x2],
        subdivided into multiple 'step' segments. Each sub-interval uses a
        smoothstep function for a gentle transition, rather than a sharp jump.

        Args:
            x (float): The x-value at which we want the interpolated y.
            x1, x2 (float): The start and end x-values of the overall segment.
            y1, y2 (float): The start and end y-values at x1 and x2.
            max_num_steps (int): Maximum number of steps to use for steep slopes.
            step_k (float): Optional steepness factor for controlling how sharply
                            the step transitions occur.

        Returns:
            float or None:
                - The interpolated y-value if x is within [x1, x2].
                - None if x is outside that range.

        Behavior:
            1. Computes slope = (|y2 - y1| / |x2 - x1|).
            2. Decides how many sub-steps to create:
            - If slope < 0.5, use 1 step.
            - If slope < 3.0, use min(2, max_num_steps).
            - Else, use max_num_steps.
            3. Splits [x1, x2] into 'num_steps' sub-intervals (x_edges).
            4. For each sub-interval, uses a smoothstep-like function to
            ease from the sub-interval's base (y_base) to y_base + (dy).
            5. Returns y2 if x == x2 exactly (to handle any rounding issues).

        Example:
            Suppose (x1, y1) = (0, 0), (x2, y2) = (10, 5), and slope is moderate.
            We might get 2 steps:
                - Step 1 covers x in [0..5], step 2 covers x in [5..10].
                - Within each step, we do a smooth S-curve from y_base to y_base + dy.
        """

        # 1) If x is out of [x1, x2], return None.
        if not (min(x1, x2) <= x <= max(x1, x2)):
            return None

        # 2) Handle the edge case where x1 == x2.
        dx = x2 - x1
        if abs(dx) < 1e-12:  # effectively vertical line
            # If x1 == x2 and x is that same value, just return y1 (or y2).
            return y1

        # 3) Calculate slope and decide number of steps.
        dy_abs = abs(y2 - y1)
        slope = float('inf') if abs(dx) < 1e-12 else (dy_abs / abs(dx))

        if slope < 0.5:
            num_steps = 1
        elif slope < 3.0:
            #num_steps = min(2, max_num_steps)
            num_steps = 2
        else:
            num_steps = max_num_steps

        # 4) Subdivide the interval [x1, x2].
        x_edges = np.linspace(x1, x2, num_steps + 1)
        total_dy = (y2 - y1)
        dy_per_step = total_dy / num_steps

        # 5) Identify which sub-interval x falls into.
        for i in range(num_steps):
            start, end = x_edges[i], x_edges[i + 1]

            # Ensure start <= end for the loop logic, even if x2 < x1.
            if start > end:
                start, end = end, start

            if start <= x <= end:
                # Base y for this step
                y_base = y1 + i * dy_per_step

                # alpha in [0..1] within this sub-interval
                alpha = (x - x_edges[i]) / (x_edges[i + 1] - x_edges[i])

                # Option A: Standard smoothstep
                # local_y = y_base + dy_per_step * (alpha**2 * (3 - 2*alpha))

                # Option B: Use step_k to adjust steepness if desired.
                # The code below is a simple variation: alpha^(n) * ( (n+1) - n*alpha ).
                # Adjust n = step_k / 10.0 or pick your own formula.
                n = max(1.0, step_k / 10.0)  # avoid n=0
                smooth_factor = (alpha**n) * ((n + 1) - n * alpha)

                local_y = y_base + dy_per_step * smooth_factor
                return local_y

        # 6) If we got here, x might be exactly x2 (float rounding).
        return y2


    def smooth_step_function(x):
        if x1 <= x <= x2:
            #num_steps = int((x2) - (x1))
            num_steps = int(math.ceil(x2 - x1))
            #print(x2, " ", x1)
            if num_steps < 1:
                num_steps = 2  # Ensure at least one step
            elif num_steps > 3:
                num_steps = 3
            #num_steps = 2

            # Calculate the positions of the steps
            step_edges = np.linspace(x1, x2, num_steps + 1)
            step_height = (y2 - y1) / num_steps

            # Define smoothing width as a fraction of step width
            step_width = (x2 - x1) / num_steps
            smoothing_fraction = 0.5 # Adjust this value between 0 and 0.5
            smoothing_width = smoothing_fraction * step_width

            # Determine which step we're in
            for i in range(num_steps):
                start = step_edges[i]
                end = step_edges[i + 1]
                y_base = y1 + i * step_height

                # If we're within the smoothing region at the end of the step
                if end - smoothing_width <= x <= end:
                    t = (x - (end - smoothing_width)) / smoothing_width
                    # Smoothstep interpolation
                    transition = t**2 * (3 - 2 * t)
                    return y_base + step_height * transition
                # If we're within the flat part of the step
                elif start <= x < end - smoothing_width:
                    return y_base
            return y2  # In case x == x2
        else:
            return None

    def smooth_exponential_decrease_function(x):
        # Only define behavior in the interval [x1, x2]
        if x1 <= x <= x2:
            # We want the function to rapidly drop from y1 at x1 and approach y2 as x approaches x2.
            # Let's choose k so that at x2 we're close to y2, say within 1%:
            # exp(-k*(x2-x1)) = 0.01 -> -k*(x2-x1)=ln(0.01) -> k = -ln(0.01)/(x2-x1)
            # ln(0.01) ~ -4.60517, so k ≈ 4.6/(x2-x1).
            # You can adjust this factor (4.6) if you want a different "steepness".
            if x2 > x1:  
                k = 15 / (x2 - x1)
            else:
                # Avoid division by zero if times are equal
                k = 1.0

            return y2 + (y1 - y2)*math.exp(-k*(x - x1))
        else:
            return None

    def smooth_exponential_increase_function(x):
        # Similar logic but reversed to create a curve that starts low and rises up.
        if x1 <= x <= x2:
            if x2 > x1:
                #k = 4.6 / (x2 - x1)
                k = 15 / (x2 - x1)
            else:
                k = 1.0

            # For an "increase", you can simply flip the logic:
            # Start at y1 and approach y2 from below using a mirrored exponential shape:
            # y(x) = y1 + (y2 - y1)*(1 - exp(-k*(x - x1)))
            return y1 + (y2 - y1)*(1 - math.exp(-k*(x - x1)))
        else:
            return None
    
    def straight_decrease_function(x):
        if x1 <= x <= x2:
            # Parameters to adjust
            horizontal_fraction = 0.01  # Adjust as needed

            # Calculate key points
            total_interval = x2 - x1
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                # Initial horizontal segment at y1
                return y1
            elif horizontal_end <= x <= x2:
                # Immediate jump to y2
                return y2
            else:
                return None
        else:
            return None
 
    def straight_increase_function(x):
        if x1 <= x <= x2:
            horizontal_fraction = 0.01  # Adjust as needed
            total_interval = x2 - x1
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                return y1
            elif horizontal_end <= x <= x2:
                return y2
            else:
                return None
        else:
            return None

    def step_function(x):
        if x1 <= x <= x2:

            #num_steps = (x2 - x1)
            #num_steps = 2 #setting static number of steps
            #step_height = (y2 - y1) / num_steps
            #print("x1: ", x1, " x2: ", x2, " y1: ", y1, " y2: ", y2)
            #print("num_steps: ", num_steps, "  step_height: ", step_height)
            #steps_completed = int((x - x1) / ((x2 - x1) / num_steps)) # Calculate the number of steps from x1 to x
            
            num_steps = int(x2 - x1)
            if(num_steps < 1):
                num_steps = 1  # Static number of steps
            
            segment_width = (x2 - x1) / (num_steps + 1)
            steps_completed = int((x - x1) / segment_width)
            step_height = (y2 - y1) / num_steps
       
            return y1 + (steps_completed * step_height)
        else:
            return None
            
    def linear_function(x):
        if x1 <= x <= x2:
            return y1 + ((y2 - y1) / (x2 - x1)) * (x - x1)
        else:
            return None
    
    def concave_up_decreasing_function(x):
        if x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) * (x1 + x2 - 2*x2))
            b = y2 - a * (x2 - x2)**2
            return a * (x - x2)**2 + b
        else:
            return None
        
    def concave_down_decreasing_function(x):
        if x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) * (x2 + x1 - 2*x1))
            b = y1 - a * (x1 - x1)**2
            return a * (x - x1)**2 + b
        else:
            return None
        
    def concave_up_increasing_function(x):
        if x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) * (x2 + x1 - 2*x1))
            b = y1 - a * (x1 - x1)**2
            return a * (x - x1)**2 + b
        else:
            return None

    def concave_down_increasing_function(x):
        if x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) * (x1 + x2 - 2*x2))
            b = y2 - a * (x2 - x2)**2
            return a * (x - x2)**2 + b
        else:
            return None

    def test(x):
        
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2
        
        if x1 <= x <= xm:
            # Concave down decreasing function up to the midpoint
            a = (ym - y1) / ((xm - x1)**2)
            return a * (x - xm)**2 + ym
        elif xm < x <= x2:
            # Concave up decreasing function from the midpoint to x2
            a = (ym - y2) / ((xm - x2)**2)
            return a * (x - xm)**2 + ym
        else:
            return None
            
    def curvy_down_up(x):
        
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2
        a_down = (ym - y1) / ((xm - x1)**2)
        b_down = y1 - a_down * (x1 - x1)**2
        
        # Ensure the vertex of concave up is at (x2, y2)
        a_up = (ym - y2) / ((xm - x2)**2)
        b_up = y2 - a_up * (x2 - x2)**2
        
        if x1 <= x <= xm:
            return a_down * (x - x1)**2 + b_down
        elif xm < x <= x2:
            return a_up * (x - x2)**2 + b_up
        else:
            return None
    


   
    if x1 == x2:
        # x1 == x2, return a function that is only defined at x == x1
        def point_function(x):
            if x == x1:
                return y1
            else:
                return None
        return point_function
    else:
        # Existing code for other arcs
        if arc in['Step-by-Step Increase', 'Step-by-Step Decrease']:
            return exponential_step_function
            #return s_curve_step_function
        elif arc in ['Straight Increase']:
            return smooth_exponential_increase_function
        elif arc in ['Straight Decrease']:
            return smooth_exponential_decrease_function
        elif arc in ['Linear Increase','Linear Decrease','Gradual Increase', 'Gradual Decrease', 'Linear Flat']:
            #return linear_function #3/8/2025
            return curvy_down_up #replacing linear function with s-curve function because it avoid gaps in designs
        elif arc in ['Concave Down, Increase', 'Rapid-to-Gradual Increase']:
            return concave_down_increasing_function
        elif arc in ['Concave Down, Decrease', 'Gradual-to-Rapid Decrease']:
            return concave_down_decreasing_function
        elif arc in ['Concave Up, Increase', 'Gradual-to-Rapid Increase']:
            return concave_up_increasing_function
        elif arc in ['Concave Up, Decrease', 'Rapid-to-Gradual Decrease']:
            return concave_up_decreasing_function
        elif arc in ['Hyperbola Increase','Hyperbola Decrease', 'S-Curve Increase', 'S-Curve Decrease']:
            return curvy_down_up
        elif arc  == 'test':
            return test
        else:
            #print(arc)
            raise ValueError(f"{arc} Interpolation method not supported")
    

  
# Master function to evaluate the emotional score for any given plot point number
def get_story_arc(x, functions_list):
    for func in functions_list:
        result = func(x)
        if result is not None:
            return result
    return None  # Return None if x is outside the range of all functions


def transform_story_data(data, x_delta, step_k, max_num_steps ):
    # # Convert JSON to DataFrame
    # try:
    #     df = pd.json_normalize(
    #         data, 
    #         record_path=['story_components'], 
    #         meta=[
    #             'title', 
    #             'protagonist'
    #         ],
    #         record_prefix='story_component_'
    #     )
    # except Exception as e:
    #     print("Error:", e)
    #     print("NORMALIZE IS BREAKING!")
    #     return None

        # --- Start of transform_story_data ---
    if not isinstance(data, dict):
        print(f"transform_story_data FATAL: Input 'data' is not a dictionary. Type: {type(data)}")
        return None 
    
    if 'story_components' not in data:
        print(f"transform_story_data FATAL: 'story_components' key missing from input data. Keys: {list(data.keys())}")
        return None

    if not isinstance(data['story_components'], list):
        print(f"transform_story_data FATAL: 'story_components' is not a list. Type: {type(data['story_components'])}")
        return None

    components_for_df_creation = []
    for comp_idx, component_data_item in enumerate(data['story_components']):
        if not isinstance(component_data_item, dict):
            print(f"transform_story_data WARNING: story_component at index {comp_idx} is not a dict. Skipping.")
            continue 

        mod_end_time = component_data_item.get('modified_end_time')
        mod_emo_score = component_data_item.get('modified_end_emotional_score')
        arc_type = component_data_item.get('arc') 
        description = component_data_item.get('description', '#N/A') # Get description

        # All components (including the first placeholder) need time and score.
        if mod_end_time is None or mod_emo_score is None:
            print(f"transform_story_data WARNING: Essential time/score missing in component {comp_idx}. Skipping. Data: {component_data_item}")
            continue
        
        # If arc_type is None (e.g. for the first component if 'arc' key is missing), default to "#N/A"
        # This ensures the key 'story_component_arc' will exist for all rows going into the DataFrame.
        if arc_type is None:
            arc_type = "#N/A"

        essential_comp_info = {
            # Fields that will be directly used or selected later with these exact names
            'title': data.get('title', 'Unknown Title'), 
            'protagonist': data.get('protagonist', 'Unknown Protagonist'),
            'story_component_arc': arc_type, # Use the direct name
            'story_component_description': description, # Use the direct name

            # Fields that will be renamed later (or you can name them directly now)
            # Using 'modified_...' prefix initially, then renaming, is fine if you prefer that pattern.
            'story_component_modified_end_time': mod_end_time,
            'story_component_modified_end_emotional_score': mod_emo_score,
        }
        components_for_df_creation.append(essential_comp_info)

    if not components_for_df_creation or len(components_for_df_creation) < 2 :
        print(f"transform_story_data ERROR: Not enough valid components ({len(components_for_df_creation)}) to create DataFrame for arc calculation.")
        return None

    try:
        df = pd.DataFrame(components_for_df_creation)
    except Exception as e:
        print(f"transform_story_data ERROR: Creating DataFrame from components_for_df_creation failed: {e}")
        return None
    if not components_for_df_creation or len(components_for_df_creation) < 2 : # Need at least 2 points to form an arc
        print(f"transform_story_data ERROR: Not enough valid components ({len(components_for_df_creation)}) to create DataFrame for arc calculation.")
        return None

    try:
        df = pd.DataFrame(components_for_df_creation)
    except Exception as e:
        print(f"transform_story_data ERROR: Creating DataFrame from components_for_df_creation failed: {e}")
        return None


    # Print the column names for debugging
    #print("DataFrame columns:", df.columns.tolist())

    # Use 'story_component_modified_end_time' and 'story_component_modified_end_emotional_score' directly
    df['story_component_end_time'] = df['story_component_modified_end_time']
    df['story_component_end_emotional_score'] = df['story_component_modified_end_emotional_score']

    # Rename other columns as needed
    df = df.rename(columns={
        'story_component_description': 'story_component_description',
        'story_component_arc': 'story_component_arc'
    })

    # Select relevant columns
    df = df[['title', 'protagonist', 'story_component_end_time', 'story_component_end_emotional_score', 'story_component_arc', 'story_component_description']]
    df = df.sort_values(by='story_component_end_time', ascending=True)

    # Convert time values to x-values
    story_time_values = df['story_component_end_time'].tolist()
    x_original = np.array(story_time_values)
    x_scale = np.array(scale_plot_points(x_original, 1, 10))  # Scale x values so they are 1 - 10

    # Store pairs of x_original values and their scaled counterparts
    x_dict = dict(zip(x_original, x_scale))

    # Extract individual story components
    array_of_dicts = []
    for i in range(len(df) - 1):  # -1 because we are considering pairs of adjacent rows
        start_time = x_dict[df.loc[i, 'story_component_end_time']]
        end_time = x_dict[df.loc[i + 1, 'story_component_end_time']]
        start_emotional_score = df.loc[i, 'story_component_end_emotional_score']
        end_emotional_score = df.loc[i + 1, 'story_component_end_emotional_score']
        arc = df.loc[i + 1, 'story_component_arc']  # Using the arc of the second point

        dict_item = {
            'story_component_times': [start_time, end_time],
            'story_component_end_emotional_scores': [start_emotional_score, end_emotional_score],
            'arc': arc
        }
        array_of_dicts.append(dict_item)

    # Create a list to store the component story arcs
    story_arc_functions_list = []
    for item in array_of_dicts:
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']

        # Create the function based on the specified interpolation
        component_arc_function = get_component_arc_function(
            story_component_times[0],
            story_component_times[1],
            story_component_end_emotional_scores[0],
            story_component_end_emotional_scores[1],
            story_component_arc,
            step_k,
            max_num_steps
        )
        story_arc_functions_list.append(component_arc_function)

    num_points = int((max(x_scale) - min(x_scale)) / x_delta)
    #print(num_points)
    x_values = np.linspace(min(x_scale), max(x_scale), num_points)  # 1000 points for smoothness

    # Ensure x_values includes all x1 and x2 values
    x1_x2_values = set()
    for item in array_of_dicts:
        x1_x2_values.update(item['story_component_times'])
    x_values = np.unique(np.concatenate([x_values, np.array(list(x1_x2_values))]))
    x_values.sort()

    y_values = np.array([get_story_arc(x, story_arc_functions_list) for x in x_values])  # Calculate corresponding y-values
    y_values = scale_y_values(y_values, -10, 10)

    # Process arcs for each story component
    story_component_index = 1
    for item in array_of_dicts:
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']

        component_arc_function = get_component_arc_function(
            story_component_times[0],
            story_component_times[1],
            story_component_end_emotional_scores[0],
            story_component_end_emotional_scores[1],
            story_component_arc, 
            step_k,
            max_num_steps
        )
        result = np.array([get_story_arc(x, [component_arc_function]) for x in x_values])

        non_none_positions = np.where(result != None)[0]

        # **Add check for empty non_none_positions**
        if non_none_positions.size == 0:
            print(f"No valid positions for component at index {story_component_index}, function returns None for all x")
            story_component_index += 1
            continue  # Skip this component or handle accordingly

        arc_x_values = x_values[non_none_positions]
        arc_y_values = y_values[non_none_positions]

        
        #1/12/2024 -- testing to see if I can help produce smoother arcs
        # if(story_component_arc == 'Straight Increase' or story_component_arc == 'Straight Decrease'):
        #     pts = list(zip(arc_x_values, arc_y_values))
        #     smoothed_pts = chaikin_curve(pts, iterations=1)
        #     arc_x_values_smoothed, arc_y_values_smoothed = zip(*smoothed_pts)

        #     arc_x_values = np.array(arc_x_values_smoothed)
        #     arc_y_values = np.array(arc_y_values_smoothed)


        # Handle specific arcs if necessary
        # if story_component_arc in ['Straight Increase', 'Straight Decrease']:
        #     if non_none_positions.size > 1:
        #         prepend_indices = [non_none_positions[0] - 2, non_none_positions[0] - 1]
        #         # Ensure indices are within bounds
        #         prepend_indices = [idx for idx in prepend_indices if idx >= 0]
        #         if prepend_indices:
        #             prepend_x = x_values[prepend_indices]
        #             prepend_y = y_values[prepend_indices]
        #             arc_x_values = np.insert(arc_x_values, 0, prepend_x)
        #             arc_y_values = np.insert(arc_y_values, 0, prepend_y)
            
            # Decrease the number of values inserted
            # prepend_index = non_none_positions[0] - 1
            # # Ensure index is within bounds
            # if prepend_index >= 0:
            #     prepend_x = x_values[prepend_index]
            #     prepend_y = y_values[prepend_index]
            #     arc_x_values = np.insert(arc_x_values, 0, prepend_x)
            #     arc_y_values = np.insert(arc_y_values, 0, prepend_y)
            # else:
            #     print(f"Not enough positions to prepend for component at index {story_component_index}")

        data['story_components'][story_component_index]['arc_x_values'] = arc_x_values.tolist()
        data['story_components'][story_component_index]['arc_y_values'] = arc_y_values.tolist()

        story_component_index += 1

    data['x_values'] = x_values.tolist()
    data['y_values'] = y_values.tolist()

    return data


def place_text_centered(cr, text, font_size_px,
                       x_center, y_center,
                       rotation_degrees=0,
                       color=(0,0,0),
                       font_face="Sans"):
    """
    Draw 'text' so that its center is at (x_center, y_center).
    If rotation_degrees != 0, we rotate about that center point.
    """
    # 1) Create Pango layout to measure text
    layout = PangoCairo.create_layout(cr)
    font_desc = Pango.FontDescription(f"{font_face} {font_size_px}")
    layout.set_font_description(font_desc)
    layout.set_text(text, -1)
    text_width, text_height = layout.get_pixel_size()

    # 2) Compute top-left so the text is centered on (x_center,y_center)
    x_text = x_center - text_width/2
    y_text = y_center - text_height/2

    # 3) If rotating, we translate to center, rotate, then translate back
    cr.save()
    cr.set_source_rgb(*color)
    cr.move_to(x_text, y_text)
    if rotation_degrees != 0:
        cr.translate(x_center, y_center)
        cr.rotate(math.radians(rotation_degrees))
        cr.translate(-x_center, -y_center)

    # 4) Show the layout
    PangoCairo.show_layout(cr, layout)
    cr.restore()

def hex_to_rgb(hex_color):
    """
    Convert a hex color string to an RGB tuple normalized to [0, 1].

    Args:
        hex_color (str): Hex color string (e.g., '#001F3F').

    Returns:
        tuple: Normalized RGB tuple (e.g., (0.0, 0.12156862745098039, 0.24705882352941178)).
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to integer values for RGB
    r = int(hex_color[0:2], 16) / 255.0  # Red
    g = int(hex_color[2:4], 16) / 255.0  # Green
    b = int(hex_color[4:6], 16) / 255.0  # Blue
    
    return (r, g, b)


def validate_descriptors(descriptors_text, protagonist, lower_bound, upper_bound):
    """
    Validates and fixes descriptor text against all requirements.
    
    Args:
        descriptors_text (str): The descriptor text to validate
        protagonist (str): Name of the protagonist to check against
        lower_bound (int): Minimum acceptable character count
        upper_bound (int): Maximum acceptable character count
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message_or_fixed_text)
            If invalid: (False, error_message)
            If valid: (True, potentially_modified_text)
    """
    if not descriptors_text:
        return False, "Empty descriptor text"

    # 1. Length Check
    actual_length = len(descriptors_text)
    if not (lower_bound <= actual_length <= upper_bound):
        return False, f"Length {actual_length} outside bounds {lower_bound}-{upper_bound}"

    # 2. Protagonist Name Check
    if protagonist.lower() in descriptors_text.lower():
        return False, f"Contains protagonist name '{protagonist}'"

    # 3. Define minor words
    minor_words = {
        'a', 'an', 'the',
        'and', 'but', 'or', 'nor',
        'in', 'of', 'to', 'for', 'with', 'by', 'at', 'on', 'from',
    }

    # 4. Split into phrases and verify/fix each one
    # First split on period to get raw phrases
    raw_phrases = [p.strip() for p in descriptors_text.replace('. ', '.').split('.') if p.strip()]
    modified_phrases = []
    
    for phrase in raw_phrases:
        if not phrase:
            return False, "Contains empty phrase"
            
        words = phrase.split()
        if not words:
            return False, "Contains phrase without words"
        
        if len(words) > 5:
            return False, f"Phrase '{phrase}' has more than 5 words"
        if len(words) < 1:
            return False, f"Phrase '{phrase}' has no words"
            
        # Fix capitalization
        modified_words = []
        modified_words.append(words[0].capitalize())  # First word always capitalized
        
        for word in words[1:]:
            if word.lower() in minor_words:
                modified_words.append(word.lower())
            else:
                modified_words.append(word.capitalize())
        
        modified_phrases.append(' '.join(modified_words))

    # 5. Join phrases with proper formatting:
    # - All phrases except last end with ". "
    # - Last phrase ends with "."
    if len(modified_phrases) > 1:
        fixed_text = '. '.join(modified_phrases[:-1]) + '. ' + modified_phrases[-1] + '.'
    else:
        fixed_text = modified_phrases[0] + '.'

    # 6. Final length check after fixes
    if not (lower_bound <= len(fixed_text) <= upper_bound):
        return False, f"After fixes, length {len(fixed_text)} outside bounds {lower_bound}-{upper_bound}"

    return True, fixed_text

def pango_font_exists(font_name):
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

# Utility to safely add attributes using tags
def begin_svg_group(cr, group_id, output_format):
    if output_format == "svg":
        # Using TAG_LINK is standard for adding attributes like id, class, href
        cr.tag_begin(cairo.TAG_LINK, f'id="{group_id}"')
        # You could add fill/stroke attributes here too if needed globally for the group
        # Example: cr.tag_begin(cairo.TAG_LINK, f'id="{group_id}" fill="white"')

def end_svg_group(cr, output_format):
    if output_format == "svg":
        cr.tag_end(cairo.TAG_LINK)
# --- End Helper ---


from PIL import Image
import numpy as np

def verify_safe_margin(
        path: str,
        bg_rgb: tuple,
        dpi: int = CURRENT_DPI,
        margin_in: float = 0.625,
        tolerance_px: int = 0   # allow tiny bleed if you like
    ):
    """
    Opens the finished image and checks that every edge has at least
    `margin_in` inches of background (± `tolerance_px`).

    Raises ValueError if any side is short; returns a dict if all good.
    """
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)

    # distance from solid background colour
    dist = np.linalg.norm(arr - np.array(bg_rgb), axis=2)
    content = dist > 15                    # tweak threshold if needed

    rows = np.where(content.any(1))[0]
    cols = np.where(content.any(0))[0]

    top    = rows.min()
    bottom = img.height - 1 - rows.max()
    left   = cols.min()
    right  = img.width  - 1 - cols.max()

    target = int(round(margin_in * dpi))

    margins = dict(top=top, right=right, bottom=bottom, left=left)
    short   = {k:v for k,v in margins.items()
               if v < (target - tolerance_px)}

    # if short:
    #     raise ValueError(
    #         f"🚨  Margin shortfall: wanted ≥{target}px, "
    #         f"but got {short}"
    #     )

    return margins



# Place this helper function somewhere accessible, e.g., near draw_text_on_curve
def get_standard_space_width(pangocairo_context, font_desc):
    """
    Gets the pixel width of a standard space character for the given font.
    """
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)
    layout.set_text(" ", -1)  # A single space character
    width, _ = layout.get_pixel_size()
    # It's possible for a font to have a zero-width space, handle defensively.
    return width if width > 0 else 1 # Return at least 1px to avoid division by zero later


def draw_text_on_curve(
        cr, 
        x_values_scaled, 
        y_values_scaled, 
        text, 
        pangocairo_context, 
        font_desc, 
        all_rendered_boxes, 
        margin_x, 
        margin_y, 
        design_width, 
        design_height,
        spaces_width_multiplier,
        adjust_spacing):
    
    total_curve_length = np.sum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled)))
    cumulative_curve_lengths = np.insert(np.cumsum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))), 0, 0)

    idx_on_curve = 0
    distance_along_curve = 0

    def get_tangent_angle(x_vals, y_vals, idx):
        if idx == 0:
            dx = x_vals[1] - x_vals[0]
            dy = y_vals[1] - y_vals[0]
        elif idx == len(x_vals) - 1:
            dx = x_vals[-1] - x_vals[-2]
            dy = y_vals[-1] - y_vals[-2]
        else:
            dx = x_vals[idx + 1] - x_vals[idx - 1]
            dy = y_vals[idx + 1] - y_vals[idx - 1]
        angle = math.atan2(dy, dx)
        return angle

    import re
    phrases = re.findall(r'.+?(?:\. |$)', text)
    phrases = [phrase for phrase in phrases if phrase.strip()]

    char_positions = []
    rendered_boxes = []
    all_text_fits = True

    space_count = 0
    for phrase in phrases:
        temp_char_positions = []
        temp_rendered_boxes = []
        saved_idx_on_curve = idx_on_curve
        saved_distance_along_curve = distance_along_curve
        phrase_fits = True

        for char in phrase:
            layout = Pango.Layout.new(pangocairo_context)
            layout.set_font_description(font_desc)
            layout.set_text(char, -1)
            char_width, char_height = layout.get_pixel_size()

            if adjust_spacing == True and char == ' ':
                before_char_width = char_width
                #print("char_width before multiplier: ", char_width)
                try:
                    char_width = get_standard_space_width(pangocairo_context, font_desc) * spaces_width_multiplier[space_count]
                    #print("multiplier: ", spaces_width_multiplier[space_count])
                except:
                    char_width = get_standard_space_width(pangocairo_context, font_desc) * spaces_width_multiplier[str(space_count)]
                    #print("multiplier: ", spaces_width_multiplier[str(space_count)])
                
                after_char_width = char_width
                #print("char width after multiplier: ", char_width, " | diff: ", (after_char_width - before_char_width) )
                


                space_count = space_count + 1

            while idx_on_curve < len(cumulative_curve_lengths) - 1:
                segment_start_distance = cumulative_curve_lengths[idx_on_curve]
                segment_end_distance = cumulative_curve_lengths[idx_on_curve + 1]
                segment_distance = segment_end_distance - segment_start_distance

                if segment_distance == 0:
                    idx_on_curve += 1
                    continue

                ratio = (distance_along_curve - segment_start_distance) / segment_distance

                if ratio < 0 or ratio > 1:
                    idx_on_curve += 1
                    continue

                x = x_values_scaled[idx_on_curve] + ratio * (x_values_scaled[idx_on_curve + 1] - x_values_scaled[idx_on_curve])
                y = y_values_scaled[idx_on_curve] + ratio * (y_values_scaled[idx_on_curve + 1] - y_values_scaled[idx_on_curve])
                angle = get_tangent_angle(x_values_scaled, y_values_scaled, idx_on_curve)

                box = Polygon([
                    (-char_width / 2, -char_height / 2),
                    (char_width / 2, -char_height / 2),
                    (char_width / 2, char_height / 2),
                    (-char_width / 2, char_height / 2)
                ])

                rotated_box = shapely_rotate(box, angle * (180 / math.pi), origin=(0, 0), use_radians=False)
                translated_box = shapely.affinity.translate(rotated_box, xoff=x, yoff=y)

                #CAUSED ALOT OF ISSUES !!!!!!!!!
                # ── NEW: bounce the char if it crosses the 0.625‑in safety zone ──
                # if (translated_box.bounds[0] < margin_x or                 # left
                #     translated_box.bounds[2] > design_width  - margin_x or # right
                #     translated_box.bounds[1] < margin_y or                 # top
                #     translated_box.bounds[3] > design_height - margin_y
                #     ):  # bottom
                #     distance_along_curve += 1      # scoot 1 px along path
                #     continue                       # try again at new spot
                # ───────────────────────────────────────────────

                # Check overlap
                for other_box in rendered_boxes + all_rendered_boxes:
                    if translated_box.intersects(other_box):
                        distance_along_curve += 1
                        break
                else:
                    temp_char_positions.append((x, y, angle, char, char_width, char_height))
                    temp_rendered_boxes.append(translated_box)
                    rendered_boxes.append(translated_box)
                    all_rendered_boxes.append(translated_box)

                    distance_along_curve += char_width
                    break
            else:
                # No space left on the curve
                phrase_fits = False
                break

        if phrase_fits:
            char_positions.extend(temp_char_positions)
        else:
            # rollback
            idx_on_curve = saved_idx_on_curve
            distance_along_curve = saved_distance_along_curve
            rendered_boxes = rendered_boxes[:len(rendered_boxes) - len(temp_rendered_boxes)]
            all_rendered_boxes = all_rendered_boxes[:len(all_rendered_boxes) - len(temp_rendered_boxes)]
            all_text_fits = False
            break

    # Render characters
    for x, y, angle, char, char_width, char_height in char_positions:
        cr.save()
        cr.translate(x, y)
        cr.rotate(angle)

        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(font_desc)
        layout.set_text(char, -1)
        cr.translate(-char_width / 2, -char_height / 2) 
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    average_char_width = get_average_char_width(pangocairo_context, font_desc, text)
    remaining_curve_length = total_curve_length - distance_along_curve

    if not all_text_fits:
        print("curve_too_short | spacing, ", adjust_spacing)
        curve_length_status = "curve_too_short"
    elif remaining_curve_length > average_char_width: #and adjust_spacing == False:
        print("curve_too_long | spacing, ", adjust_spacing, " | remaining length: ", (remaining_curve_length - average_char_width), " | average_char_width", average_char_width)
        curve_length_status = "curve_too_long"
    # elif remaining_curve_length > (average_char_width * 2) and adjust_spacing == True:
    #     print("spacing true | remaining length: ", (remaining_curve_length - (average_char_width * 2)))
    #     curve_length_status = "curve_too_long"
    else:
        curve_length_status = "curve_correct_length"

    return curve_length_status



















                  















def _layout_single_phrase_on_curve(
    cr, x_values_scaled_np, y_values_scaled_np, phrase_text,
    pangocairo_context, font_desc,
    initial_distance_on_curve, initial_idx_on_curve,
    total_curve_length, cumulative_curve_lengths,
    base_char_spacing_factor, space_width_multiplier, standard_space_width,
    existing_rendered_boxes, # Boxes from previous phrases IN THE SAME ARC or previous arcs
    margin_x, margin_y, design_width, design_height,
    arc_drawable_bottom_y # Pre-calculated effective bottom boundary
):
    """
    Attempts to lay out a single phrase on the curve.

    Returns:
        tuple: (
            bool_success,
            final_distance_on_curve,
            final_idx_on_curve,
            list_of_char_render_info,  # [(x, y, angle, char, char_w_measured, char_h_measured), ...]
            list_of_new_boxes_for_this_phrase
        )
    bool_success is True if the entire phrase was laid out without going off curve
                 or causing collisions/boundary issues.
    """
    
    # --- This part is largely from your existing draw_text_on_curve's inner loop ---
    # --- with modifications for space_width_multiplier ---
    
    # Helper to get tangent angle (reuse your existing one)
    def get_tangent_angle(x_vals, y_vals, idx):
        # (Your existing get_tangent_angle implementation)
        if len(x_vals) < 2: return 0
        if idx == 0:
            dx = x_vals[1] - x_vals[0]
            dy = y_vals[1] - y_vals[0]
        elif idx >= len(x_vals) - 1:
            dx = x_vals[-1] - x_vals[-2]
            dy = y_vals[-1] - y_vals[-2]
        else:
            dx = x_vals[idx + 1] - x_vals[idx - 1]
            dy = y_vals[idx + 1] - y_vals[idx - 1]
        if dx == 0 and dy == 0:
            if idx > 0: return get_tangent_angle(x_vals, y_vals, idx - 1)
            return 0
        return math.atan2(dy, dx)

    distance_on_curve = initial_distance_on_curve
    idx_on_curve = initial_idx_on_curve
    
    char_render_info_list = []
    new_boxes_for_this_phrase = []

    for char_idx, char_glyph in enumerate(phrase_text):
        layout = Pango.Layout.new(pangocairo_context)
        layout.set_font_description(font_desc)
        layout.set_text(char_glyph, -1)
        char_width_measured, char_height = layout.get_pixel_size()

        char_width_effective = char_width_measured * base_char_spacing_factor
        if char_glyph == ' ':
            # Use the standard_space_width scaled by multipliers
            char_width_effective = standard_space_width * space_width_multiplier * base_char_spacing_factor
            # Ensure space has some width, even if char_width_measured for space was 0 (unlikely for normal space)
            if char_width_effective <=0 : char_width_effective = base_char_spacing_factor # minimal width


        # --- Find position for this character (your existing robust logic) ---
        char_placed_successfully = False
        # Temp store for nudging if collision/boundary issues
        original_distance_on_curve_for_char = distance_on_curve 
        
        # Retry loop for nudging on collision/boundary
        max_nudges = 5 # Limit nudges to prevent infinite loops
        for nudge_attempt in range(max_nudges + 1):
            current_distance_on_curve_for_placement = original_distance_on_curve_for_char + nudge_attempt * 1.0 # Nudge 1px

            # Ensure we don't fall off the curve before even placing the char center
            if current_distance_on_curve_for_placement + (char_width_effective / 2.0) > total_curve_length:
                return False, distance_on_curve, idx_on_curve, char_render_info_list, new_boxes_for_this_phrase
            
            temp_idx_on_curve = idx_on_curve # Use a temp var for finding segment for this char
            
            char_found_segment = False
            while temp_idx_on_curve < len(cumulative_curve_lengths) - 1:
                segment_start_distance = cumulative_curve_lengths[temp_idx_on_curve]
                segment_end_distance = cumulative_curve_lengths[temp_idx_on_curve + 1]
                segment_length = segment_end_distance - segment_start_distance

                if segment_length <= 1e-6:
                    temp_idx_on_curve += 1
                    continue

                target_center_distance_on_curve = current_distance_on_curve_for_placement + (char_width_effective / 2.0)

                if target_center_distance_on_curve > segment_end_distance and temp_idx_on_curve < len(cumulative_curve_lengths) - 2:
                    temp_idx_on_curve += 1
                    continue
                
                distance_into_segment = target_center_distance_on_curve - segment_start_distance
                ratio = distance_into_segment / segment_length if segment_length > 1e-6 else 0.0


                if not (0 <= ratio <= 1.0):
                    if target_center_distance_on_curve > total_curve_length:
                        return False, distance_on_curve, idx_on_curve, char_render_info_list, new_boxes_for_this_phrase # Off curve
                    if ratio > 1.0 and temp_idx_on_curve < len(cumulative_curve_lengths) - 2:
                        temp_idx_on_curve += 1
                        continue
                    # Cannot place char in this segment or remaining curve under current conditions
                    break # Break from while temp_idx_on_curve loop, will lead to nudge or phrase fail


                x = x_values_scaled_np[temp_idx_on_curve] + ratio * (x_values_scaled_np[temp_idx_on_curve + 1] - x_values_scaled_np[temp_idx_on_curve])
                y = y_values_scaled_np[temp_idx_on_curve] + ratio * (y_values_scaled_np[temp_idx_on_curve + 1] - y_values_scaled_np[temp_idx_on_curve])
                angle = get_tangent_angle(x_values_scaled_np, y_values_scaled_np, temp_idx_on_curve)
                
                char_found_segment = True # Found a potential segment

                # Bounding box for collision
                half_w = char_width_measured / 2.0
                half_h = char_height / 2.0
                box = Polygon([(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)])
                rotated_box = shapely_rotate(box, math.degrees(angle), origin=(0, 0), use_radians=False)
                translated_box = shapely.affinity.translate(rotated_box, xoff=x, yoff=y)

                # Boundary check
                b = translated_box.bounds
                if (b[0] < margin_x or b[2] > (design_width - margin_x) or
                    b[1] < margin_y or b[3] > arc_drawable_bottom_y):
                    # Out of bounds, this nudge attempt failed for this character
                    char_found_segment = False # Mark as not properly placed
                    break # Break from while temp_idx_on_curve, will try next nudge_attempt

                # Collision check
                collision = False
                for other_box in existing_rendered_boxes + new_boxes_for_this_phrase: # Check against ALL so far
                    if translated_box.intersects(other_box):
                        collision = True
                        break
                
                if collision:
                    # Collision, this nudge attempt failed for this character
                    char_found_segment = False # Mark as not properly placed
                    break # Break from while temp_idx_on_curve, will try next nudge_attempt

                # If no collision and in bounds for this nudge:
                char_render_info_list.append((x, y, angle, char_glyph, char_width_measured, char_height))
                new_boxes_for_this_phrase.append(translated_box)
                
                # IMPORTANT: Update main distance_on_curve and idx_on_curve only if successful
                distance_on_curve = current_distance_on_curve_for_placement + char_width_effective 
                idx_on_curve = temp_idx_on_curve # Update the main index on curve
                char_placed_successfully = True
                break # Break from while temp_idx_on_curve loop (found segment and placed)
            # End of: while temp_idx_on_curve < len(cumulative_curve_lengths) - 1

            if char_placed_successfully:
                break # Break from nudge_attempt loop for this character
            
            if not char_found_segment and not char_placed_successfully: 
                # This means even after checking segments, no valid placement was found for the current nudge.
                # If it was the last nudge, this char fails.
                if nudge_attempt == max_nudges:
                    return False, initial_distance_on_curve, initial_idx_on_curve, char_render_info_list, new_boxes_for_this_phrase

        # End of: for nudge_attempt in range(max_nudges + 1)

        if not char_placed_successfully:
            # All nudges failed for this character, so the phrase fails
            return False, initial_distance_on_curve, initial_idx_on_curve, char_render_info_list, new_boxes_for_this_phrase
    # End of: for char_idx, char_glyph in enumerate(phrase_text)

    return True, distance_on_curve, idx_on_curve, char_render_info_list, new_boxes_for_this_phrase


