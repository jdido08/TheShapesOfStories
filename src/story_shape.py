# Import necessary libraries
import cairo
import gi
import numpy as np
import math
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity
import openai  # For LLM interactions
import yaml
from openai import OpenAI
import copy
from scipy.interpolate import CubicSpline
import json
import os

# Ensure the correct versions of Pango and PangoCairo are used
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

import anthropic
import yaml

# Load config and create client
with open("config.yaml", 'r') as stream:
    config = yaml.safe_load(stream)
    anthropic_key = config['anthropic_key']

client = anthropic.Anthropic(
    api_key=anthropic_key,
)

# # Load API key from config
# with open("config.yaml", 'r') as stream:
#     config = yaml.safe_load(stream)
#     OPENAI_KEY = config['openai_key_vonnegutgraphs']
#     client = OpenAI(api_key=OPENAI_KEY)

def create_shape(story_data_path,
                x_delta = 0.015,
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
                title_padding = 20,
                gap_above_title = 20,
                protagonist_text = "",
                border = False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
                wrap_background_color = (0,0,0),
                recursive_mode = True,
                recursive_loops = 500,
                output_format="png"):
    

    #convert hex colors to (x,y,z) foramt
    font_color = hex_to_rgb(font_color)
    line_color = hex_to_rgb(line_color)
    title_font_color = hex_to_rgb(title_font_color)
    border_color = hex_to_rgb(border_color)
    background_value = hex_to_rgb(background_value)
    wrap_background_color = hex_to_rgb(wrap_background_color)


    with open(story_data_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        if 'story_plot_data' in story_data:
            story_data = story_data['story_plot_data']
    
    #get title 
    path_title = story_data['title'].lower().replace(' ', '_')
    path_size = f'{width_in_inches}x{height_in_inches}'
    path_protagonist= story_data['protagonist'].lower().replace(' ', '_')
    

    check_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{path_title}_{path_protagonist}_{path_size}.json'
    #check if specific file exists for story + size and if it does exist use it
    if os.path.exists(check_path):
        story_data_path = check_path
        with open(story_data_path, 'r', encoding='utf-8') as file:
            story_data = json.load(file)
            if 'story_plot_data' in story_data:
                story_data = story_data['story_plot_data']

    #create story_shape_path

    story_shape_title = story_data['title'].lower().replace(' ', '_')
    story_shape_size = f'{width_in_inches}x{height_in_inches}'
    story_shape_protagonist = story_data['protagonist'].lower().replace(' ', '_')

    if title_text == "":
        path_title_text = "with_title"
    else:
        path_title_text = "no_title"

    if wrap_in_inches > 0:
        path_canvas = "wrapped_in_" + str(wrap_in_inches) + "inches"
    else:
        path_canvas = "no_wrapped"

    if output_format == "svg":
        story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_protagonist}_{story_shape_size}_{path_canvas}_{line_type}_{path_title_text}.svg'
    elif output_format == "png":
        story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_protagonist}_{story_shape_size}_{path_canvas}_{line_type}_{path_title_text}.png'
   
    status = "processing"
    story_data['status'] = status
    count = 1
    print("starting...")
    # while status == "processing":
    for i in range(recursive_loops):
        # print(story_data['story_components'][1]['modified_end_time'])
        story_data = transform_story_data(story_data, x_delta)

        story_data, status = create_shape_single_pass(
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
                    title_padding = title_padding,
                    gap_above_title = gap_above_title,
                    protagonist_text = protagonist_text,
                    border = border,
                    border_thickness=border_thickness,
                    border_color=border_color,
                    width_in_inches=width_in_inches,
                    height_in_inches=height_in_inches,
                    wrap_in_inches=wrap_in_inches,
                    wrap_background_color = wrap_background_color,
                    story_shape_path=story_shape_path,
                    recursive_mode=recursive_mode,
                    output_format = output_format)

        #print(count, " .) ", status)
        if(count % 50 == 0):
            print(count)

        count = count + 1
        if status == "completed":
            story_data['status'] = status
            break
        #print(story_data['story_components'][1]['modified_end_time'])



    #clean up story_data for saving
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
    story_data['background_color'] = background_value
    story_data['border_thickness'] = border_thickness
    story_data['border_color'] = border_color
    new_title = story_data['title'].lower().replace(' ', '_')
    new_size = f'{width_in_inches}x{height_in_inches}'
    new_protagonist = story_data['protagonist'].lower().replace(' ', '_')
    new_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{new_title}_{new_protagonist}_{new_size}.json'
    with open(new_path, 'w', encoding='utf-8') as file:
        json.dump(story_data, file, ensure_ascii=False, indent=4)

def create_shape_single_pass(story_data, 
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
                title_padding = 20,
                gap_above_title = 20,
                protagonist_text = "",
                border=False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
                wrap_background_color = (0,0,0),
                story_shape_path = "test",
                recursive_mode = True,
                output_format = "png"):
    
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

    dpi = 300

    # total print area
    total_width_in = width_in_inches + 2*wrap_in_inches
    total_height_in = height_in_inches + 2*wrap_in_inches

    total_width_px = int(total_width_in * dpi)
    total_height_px = int(total_height_in * dpi)


    #SETUP FONTS
    # Prepare for text on arcs
    from gi.repository import Pango
    font_size_for_300dpi = font_size * (300 / 96)
    font_desc = Pango.FontDescription(f"{font_style} {font_size_for_300dpi}")
   

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
    design_offset_x = wrap_in_inches * dpi
    design_offset_y = wrap_in_inches * dpi
    design_width = int(width_in_inches * dpi)
    design_height = int(height_in_inches * dpi)

    # Paint wrap areas
    if wrap_in_inches > 0:
        cr.save()
        cr.set_source_rgb(*wrap_background_color)
        
        # Top wrap area
        cr.rectangle(0, 0, total_width_px, wrap_in_inches * dpi)
        cr.fill()
        
        # Bottom wrap area
        bottom_y = total_height_px - (wrap_in_inches * dpi)
        cr.rectangle(0, bottom_y, total_width_px, wrap_in_inches * dpi)
        cr.fill()
        
        # Left wrap area
        cr.rectangle(0, wrap_in_inches * dpi, wrap_in_inches * dpi, height_in_inches * dpi)
        cr.fill()
        
        # Right wrap area
        right_x = total_width_px - (wrap_in_inches * dpi)
        cr.rectangle(right_x, wrap_in_inches * dpi, wrap_in_inches * dpi, height_in_inches * dpi)
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
    margin_ratio = 0.05
    margin_x = int(margin_ratio * design_width)
    margin_y = int(margin_ratio * design_height)

    # Determine data range for x and y
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min

   # 3) If we have a title, measure its pixel height
    if(title_text == ""):
        title_text = story_data.get('title', '')

    measured_title_height = 0

    if has_title == "YES":
        # measure text height
        layout_temp = PangoCairo.create_layout(cr)
        scaled_title_size = title_font_size * (300 / 96)
        temp_desc = Pango.FontDescription(f"{title_font_style} {scaled_title_size}")
        layout_temp.set_font_description(temp_desc)
        layout_temp.set_text(title_text, -1)
        _, measured_title_height = layout_temp.get_pixel_size()

        title_band_height = measured_title_height + title_padding

        # arcs stop short of that band
        # arcs fill up to: design_height - 2*margin_y - (title_band_height + gap_above_title)

    else:
        # no title, so no band
        title_band_height = 0

    drawable_width = design_width - 2 * margin_x
    drawable_height = (design_height
                    - 2 * margin_y
                    - title_band_height
                    - gap_above_title)

    # 4) Compute scale factors & map your story arcs into [margin_y, margin_y+drawable_height]
    x_values = story_data['x_values']
    y_values = story_data['y_values']
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min

    scale_x = drawable_width / x_range if x_range else 1
    scale_y = drawable_height / y_range if y_range else 1

    # The bottom edge for arcs is margin_y + drawable_height
    x_values_scaled = [(x - x_min)*scale_x + margin_x for x in x_values]
    y_values_scaled = [
        (margin_y + drawable_height) - ((y - y_min)*scale_y)
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
        
        

        # # Prepare for text on arcs
        # from gi.repository import Pango
        # font_size_for_300dpi = font_size * (300 / 96)
        # font_desc = Pango.FontDescription(f"{font_style} {font_size_for_300dpi}")
        arc_sample_text = ""

        all_rendered_boxes = []
        status = "completed"

        for index, component in enumerate(story_data['story_components'][1:], start=1):
            arc_x_values = component.get('arc_x_values', [])
            arc_y_values = component.get('arc_y_values', [])
            description = component.get('description', '')

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
                    sx = (xx - x_min) * scale_x + margin_x
                    sy = (margin_y + drawable_height) - ((yy - y_min) * scale_y)
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

            # Now set real color for text
            cr.set_source_rgb(*font_color)

            # Calculate arc length
            arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled)

            # If arc_text not generated yet, do so
            if 'arc_text' not in component:
                average_char_width = get_average_char_width(pangocairo_context, font_desc, arc_sample_text)
                average_rotation_angle = calculate_average_rotation_angle(arc_x_values_scaled, arc_y_values_scaled)
                target_chars = estimate_characters_fit(arc_length, average_char_width, average_rotation_angle)
                component['target_arc_text_chars'] = target_chars

                if target_chars < 5:
                    continue

                lower_bound = target_chars - 3
                upper_bound = target_chars + 3
                #llm_target_chars = target_chars - 2
                llm_target_chars = target_chars

                # Generate descriptors (call your GPT logic)
                descriptors_text, chat_messages = generate_descriptors(
                    title=story_data['title'],
                    author=story_data['author'],
                    protagonist=story_data['protagonist'],
                    component_description=description,
                    story_data=story_data,
                    desired_length=llm_target_chars
                )

                print("DESCRIPTORS: ", descriptors_text)

                

                actual_chars = len(descriptors_text)
                valid_descriptor = False
                max_attempts = 5
                attempt = 1

                if lower_bound <= actual_chars <= upper_bound:
                    valid_descriptor = True
                else:

                    while not valid_descriptor and attempt <= max_attempts:
                        descriptors_text, chat_messages = adjust_descriptors(
                            desired_length=llm_target_chars,
                            actual_length=actual_chars,
                            chat_messages=chat_messages
                        )
                        print("ADJUSTED DESCRIPTORS: ", descriptors_text)
                        actual_chars = len(descriptors_text)
                        
                        if lower_bound <= actual_chars <= upper_bound:
                            valid_descriptor = True
                        else:
                            attempt += 1

                          

                component['arc_text'] = descriptors_text
                component['actual_arc_text_chars'] = len(descriptors_text)
            
            else:
                descriptors_text = component['arc_text']
                component['actual_arc_text_chars'] = len(descriptors_text)

            arc_sample_text += " " + descriptors_text

            # Draw text on curve
            curve_length_status = draw_text_on_curve(
                cr,
                arc_x_values_scaled,
                arc_y_values_scaled,
                descriptors_text,
                pangocairo_context,
                font_desc,
                all_rendered_boxes
            )

            #print(curve_length_status)
            # Check if curve too short/long, do your recursion logic...
            if curve_length_status == "curve_too_short":
                # Attempt adjusting via CubicSpline
                x_og = np.array(original_arc_end_time_values)
                y_og = np.array(original_arc_end_emotional_score_values)
                sorted_indices = np.argsort(x_og)
                x_og = x_og[sorted_indices]
                y_og = y_og[sorted_indices]

                # Remove duplicates
                tolerance = 1e-12
                unique_indices = [0]
                for i in range(1, len(x_og)):
                    if x_og[i] - x_og[unique_indices[-1]] > tolerance:
                        unique_indices.append(i)
                x_og = x_og[unique_indices]
                y_og = y_og[unique_indices]

                cs = CubicSpline(x_og, y_og, extrapolate=True)
                new_x = x_og[-1] + (x_og[1] - x_og[0])
                new_y = float(cs(new_x))

                # print(new_x, " , ", new_y)
                # print(old_max_y, " , ", old_min_y)

                #normal mode
                if (new_x >= old_min_x and new_x <= old_max_x 
                    and new_y >= old_min_y and new_y <= old_max_y
                    and recursive_mode):
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y
                    
                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"

                #this really only works if like this was suppose to be the last story segment
                # we hit x max and want to extend y
                elif ((new_x >= old_max_x or new_x <= old_min_x) and (new_y >= old_min_y and new_y <= old_max_y) and recursive_mode and component['end_time'] == 100 and (round(new_y,3) != round(y_og[-1],3))):
                    new_x = x_og[-1]
                    
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y

                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"
                
                #we hit y max / min and need to extend x
                elif ((new_y >= old_max_y or new_y <= old_min_y) and (new_x >= old_min_x and new_x <= old_max_x) and recursive_mode):
                    
                    new_y = y_og[-1]
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y

                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"
                
                else:
                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                   
                    status = "curve too short but can't change due to constraints"
                    print(status)

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
                    and original_arc_end_emotional_score_index_length >= 0):
                    
                    component['modified_end_time'] = original_arc_end_time_values[original_arc_end_time_index_length]
                    component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length]
                    
                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"
                
                #cant touch x 
                elif ((original_arc_end_time_values[-1] == old_min_x or original_arc_end_time_values[-1] == old_max_x)
                    and original_arc_end_emotional_score_values[-1] > old_min_y
                    and original_arc_end_emotional_score_values[-1] < old_max_y
                    and len(component['arc_x_values']) > 1 and recursive_mode 
                    and round(original_arc_end_emotional_score_values[-1],3) != round(original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length],3)
                    and original_arc_end_emotional_score_index_length >= 0):

                    component['modified_end_time'] = original_arc_end_time_values[-1]
                    component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[original_arc_end_emotional_score_index_length]

                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"
                
                #cant touch y
                elif ((original_arc_end_emotional_score_values[-1] == old_min_y or original_arc_end_emotional_score_values[-1] == old_max_y)
                    and original_arc_end_time_values[-1] > old_min_x 
                    and original_arc_end_time_values[-1] < old_max_x
                    and len(component['arc_x_values']) > 1 and recursive_mode
                    and original_arc_end_time_index_length >= 0):

                    #print("hey")
                    component['modified_end_time'] = original_arc_end_time_values[original_arc_end_time_index_length]
                    component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[-1]

                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"

                else:
                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    status = "curve too long but can't change due to constraints"

            elif curve_length_status == "curve_correct_length":
                if output_format == "svg":
                    surface.flush()   # flush the partial drawing, but do *not* finalize!
                else:
                    surface.write_to_png(story_shape_path)
                status = 'All phrases fit exactly on the curve.'

            component['status'] = status

    if has_title == "YES":
        # -- Prepare the title layout --
        final_layout = PangoCairo.create_layout(cr)
        scaled_title_size = title_font_size * (300 / 96)
        final_desc = Pango.FontDescription(f"{title_font_style} {scaled_title_size}")
        final_layout.set_font_description(final_desc)
        final_layout.set_text(title_text, -1)

        # Measure the title's bounding box
        title_text_width, title_text_height = final_layout.get_pixel_size()

        # The top of the "title band" area
        title_band_top = margin_y + drawable_height + gap_above_title

        # Left-aligned X for the title
        title_x = margin_x
        # Put the title’s top bounding box at 'title_band_top'
        title_y = title_band_top

        # Draw the title at bottom-left
        cr.move_to(title_x, title_y)
        cr.set_source_rgb(*title_font_color)
        PangoCairo.show_layout(cr, final_layout)

        # ------------------------------------------------
        # Draw the protagonist name at bottom-right
        # ------------------------------------------------
        if protagonist_text == "":
            protagonist_text = story_data.get('protagonist', '')

        if protagonist_text:
            # Prepare protagonist layout
            prot_layout = PangoCairo.create_layout(cr)
            # Reuse the *same* font description as the title so styling is consistent
            prot_layout.set_font_description(font_desc)
            prot_layout.set_text(protagonist_text, -1)

            # Measure the protagonist text
            prot_text_width, prot_text_height = prot_layout.get_pixel_size()

            # The bottom edge of the title box is:
            title_bottom_line = title_y + title_text_height

            # Position the protagonist text so that its *bottom* aligns with the title’s bottom
            # i.e., top of its bounding box = (title_bottom_line - protagonist box’s height)
            prot_y = title_bottom_line - prot_text_height

            # Right‐align X so the right edge is near (margin_x + drawable_width)
            prot_x = margin_x + drawable_width - prot_text_width

            cr.move_to(prot_x, prot_y)
            cr.set_source_rgb(*font_color)
            PangoCairo.show_layout(cr, prot_layout)


    # MAKE NOTES ON TOP AND BOTTOM OF CANVAS -- only applies when wrap_in_inches > 0
    cr.restore()  # <== restore out of that translation

    if wrap_in_inches > 0:

        author = story_data.get('author','')
        year = story_data.get('year', '')
        if(author == '' and year == ''):
            author_year = ""
        elif(author == '' and year != ''):
            author_year = year 
        elif(author != '' and year == ''):
            author_year = author
        elif(author != '' and year != ''):
            author_year = author + ", " + year
        else:
            author_year = ""

        top_wrap_h = design_offset_y  # from y=0 to design_offset_y
        # The center x is half the total width
        x_top_center = total_width_px / 2
        # The center y is half the top_wrap_h
        y_top_center = top_wrap_h / 2

        place_text_centered(cr,
                            text=author_year,
                            font_size_px=scaled_title_size,
                            font_face = font_style,
                            x_center=x_top_center,
                            y_center=y_top_center,
                            rotation_degrees=0,
                            color= title_font_color)

        # 3) Place text on bottom edge, fully centered
        bottom_wrap_y = design_offset_y + design_height
        bottom_wrap_h = total_height_px - bottom_wrap_y
        x_bottom_center = total_width_px / 2
        y_bottom_center = bottom_wrap_y + (bottom_wrap_h / 2)

        place_text_centered(cr,
                            text="THE SHAPES OF STORIES, LLC",
                            font_size_px=font_size_for_300dpi,
                            x_center=x_bottom_center,
                            y_center=y_bottom_center,
                            rotation_degrees=0,
                            color=(0,0,0))


    # 7) Save final image
    if output_format == "svg":
        surface.finish()
    else:
        surface.write_to_png(story_shape_path)

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

from anthropic import Anthropic
import copy

# Initialize Anthropic client
anthropic = Anthropic()


def generate_descriptors(title, author, protagonist, component_description, story_data, desired_length):
    # Keep relevant story context
    current_index = next((i for i, comp in enumerate(story_data['story_components']) 
                         if comp['description'] == component_description), None)
    
    total_segments = len(story_data['story_components'])
    
    context = {
        'current_segment': component_description,
        'previous_segment': story_data['story_components'][current_index - 1]['description'] 
                          if current_index > 0 else None,
        'next_segment': story_data['story_components'][current_index + 1]['description'] 
                       if current_index < len(story_data['story_components']) - 1 else None
    }

    existing_arc_texts = "\n".join(
        component.get('arc_text', '') 
        for component in story_data['story_components'] 
        if 'arc_text' in component
    )
    
    if existing_arc_texts:
        existing_arc_texts = f"Previous descriptions:\n{existing_arc_texts}"

    prompt = f""" ## INSTRUCTIONS: Generate EXACTLY {desired_length}-character descriptors for this segment of {author}'s "{title}" that focus on {protagonist}".

    
## STORY SEGMENT DESCRIPTION:
{component_description}


## REQUIREMENTS:
1. LENGTH: EXACTLY {desired_length} characters (including all spaces and periods)
2. SOURCE: ONLY use elements explicitly mentioned in the STORY SEGMENT DESCRIPTION above
3. FORMAT: 
    - Descriptors should consist of 1-4 word phrases. 
    - If multiple phrases, each ends with ". " except the last phrase, which ends with just "." and no space
    - CAPITALIZATION: Use Title Case (capitalize the first letter of every word, except minor words like "and," "of," "the," unless they are the first word of a phrase)
4. PHRASE CONSTRUCTION:
    - USE ONLY elements directly from the provided STORY SEGMENT DESCRIPTION
    - USE specific and concrete elements from the STORY SEGMENT DESCRIPTION e.g. places, actions, people, objects, events
    - USE elements that are most critical and important to the STORY SEGMENT DESCRIPTION
    - AVOID using any analysis or abstractions/metaphors
    - Break compound actions into separate phrases
    - NEVER mention {protagonist} by name
5. PHRASE ORDERING: The order of the phrases MUST be in the chronological order as they appear in STORY SEGMENT DESCRIPTION
6. CONTINUITY:
    - Each story segment descriptors joins with other story story segments to tell the full {protagonist}'s story
    - Descriptors should be dinstinct from previous story segment descriptors: {existing_arc_texts}
7. OUTPUT: Respond with ONLY the descriptor text, exactly {desired_length} characters. No explanation.

## EXAMPLES:

Story Segment Description: "Despite 84 days without a catch and being considered unlucky, Santiago maintains his dignity and optimism. His friendship with Manolin provides comfort and support, though the boy has been forced to work on another boat. His determination remains strong as he prepares for a new day of fishing, finding peace in his dreams of Africa and its lions."
Potential Phases: "84 Days. No Fish. Unlucky. Optimist. Manolin Friendship. Preps for Fishing. Dreams of Africa."
Example 37-character OUTPUT: "84 Days. No Fish. Manolin Friendship."

Story Segment Description: "Gatsby stands alone in his garden, reaching out towards the green light across the bay, embodying his yearning for Daisy. His elaborate mansion and lavish parties serve as carefully orchestrated attempts to attract her attention, revealing both his hope and desperation. When he finally arranges to meet Nick, his neighbor and Daisy's cousin, Gatsby's carefully constructed facade begins to show cracks of vulnerability as he seeks a way to reconnect with his lost love"
Potential Phases: "Alone in Garden. Green Light. Yearning for Daisy. Lost Love."
Example 32-character OUTPUT: "Green Light. Yearning for Daisy."

Story Segment Description: "During the prolonged struggle with the marlin, Santiago endures physical pain and isolation, his hand cramping and cuts deepening. Yet his determination never wavers, drawing strength from memories of his past triumphs. He develops a profound respect for the marlin, calling it his brother while maintaining his resolve to prevail."
Potential Phases: "Struggle with Marlin. Pain. Hand Camps. Deep Cuts. Respect for Marlin. Brother. Unwavering Resolve."
Example 82-character OUTPUT: "Struggle with Marlin. Hand Camps. Deep Cuts. Respect. Brother. Unwavering Resolve."

Story Segment Description: "Juliet awakens to find Romeo dead beside her, having poisoned himself in the belief she was dead. In her final moments, she experiences complete despair, attempting to die by kissing his poisoned lips before ultimately using his dagger to join him in death, unable to conceive of life without him.
Potential Phases: "Awake. Romeo Dead. Despair. Kisses Poisoned Lips. Suicide by Dagger. Reunited in Death."
Example 8-character OUTPUT: "Suicide."

Story Segment Description: "The death of his beloved friend Patroclos shatters Achilles's world, transforming his anger at Agamemnon into consuming grief and rage against Hector. His emotional state plummets as he learns of Patroclos's death and the loss of his armor, driving him to a state of vengeful fury."
Potential Phases: "Patroclos Dies. Grief. Rage for Hector. Vengeful Fury."
Example 21-character OUTPUT: "Patroclos Dies. Rage."

Story Segment Description: "Gatsby's world crumbles during the confrontation at the Plaza Hotel. His desperate attempt to claim Daisy fails as she cannot deny her love for Tom, shattering his dream of recreating the past. His devotion to Daisy remains unchanged even after the accident with Myrtle, as he takes the blame and stands watch outside her house, clinging to the last remnants of his fantasy despite its obvious collapse."
Potential Phases: "Plaza Hotel. Daisy Loves Tom. Shattered Dream. Stand Watch Outside. Clings to Fantasy."
Example 48-character OUTPUT: "Plaza Hotel. Daisy Chooses Tom. Myrtle Accident."

Story Segment Description: "Gatsby's tragic end comes as he waits faithfully for a call from Daisy that never arrives, still believing in the possibility of their future together. His death at Wilson's hands is made more poignant by Daisy's complete absence - she doesn't even send flowers to his funeral. The empty funeral, attended only by Nick, Gatsby's father, and one former party guest, serves as the final testament to the hollow nature of Gatsby's dream and the society he tried to join."
Potential Phases: "Waits for Call. Daisy Never Arrives. Killed by Wilson. No Flowers. Empty Funeral."
Example 66-character OUTPUT: "Waits for Daisy Call. Killed by Wilson. No Flowers. Empty Funeral."

Note about Examples:
The Potential Phases shown are just examples of phrases for the given Story Segment Description. The actual output will be determined by exact character LENGTH requirement as demonstrated by the example outputs. . 






Respond with ONLY the descriptor text, exactly {desired_length} characters. No explanation.
"""


    #print(prompt)
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=desired_length * 5,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text.strip()
    return response_text, [{"role": "user", "content": prompt}, {"role": "assistant", "content": response_text}]

def adjust_descriptors(desired_length, actual_length, chat_messages):
    previous_attempt = chat_messages[-1]["content"]
    
    prompt = f"""Revise the story descriptors to be EXACTLY {desired_length} characters while maintaining accuracy.

Current text ({actual_length} characters):
{previous_attempt}

ADJUSTMENT RULES:
1. If too long ({actual_length} > {desired_length}):
   - Try removing least essential details first
   - Try shortening phrases while retaining their essence
   - Try removing the least essential phrases 
   - Try swapping in new phrases for existing phrases following the story descriptors requirements 

2. If too short ({actual_length} < {desired_length}):
   - Try adding specific details from the segment
   - Try expanding existing phrases with more detail
   - Try breaking longer phrases into smaller ones
   - Try adding new phrases using unused details following the story descriptors requirements 

3. ALWAYS:
   - Keep strongest story elements
   - Use only details from original STORY SEGMENT DESCRIPTION
   - Maintain proper spacing, punctuation, and capitalizaition
   - End phrases with ". " (except last with ".")
   - Avoid repetition with other segments

DO NOT respond with story descriptors previously used: {previous_attempt} 
You MUST adjust the story descriptors before responding

Previous conversation context:
{chat_messages[0]['content']}

Respond with ONLY the revised text, exactly {desired_length} characters."""

    #print(prompt)
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=desired_length * 5,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text.strip()
    return response_text, chat_messages + [{"role": "user", "content": prompt}, {"role": "assistant", "content": response_text}]





def draw_text_on_curve(cr, x_values_scaled, y_values_scaled, text, pangocairo_context, font_desc, all_rendered_boxes):
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
        curve_length_status = "curve_too_short"
    elif remaining_curve_length > average_char_width:
        curve_length_status = "curve_too_long"
    else:
        curve_length_status = "curve_correct_length"

    return curve_length_status



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
   


def get_component_arc_function(x1, x2, y1, y2, arc):

    def exponential_step_function(x):
        # 1) If out of range, return None
        if not (x1 <= x <= x2):
            return None
        
        # 2) Decide how many steps you want
        num_steps = int(math.ceil(x2 - x1))
        if num_steps < 1:
            num_steps = 1
        
        
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
                k = 15  # or 10, or something user-chosen
                # map x into [0..1] for exponential
                alpha = (x - start) / (end - start)  # 0 to 1
                # standard increase formula:
                local_y = y_base + dy * (1 - math.exp(-k * alpha))
                return local_y
        
        # If x somehow equals x2 exactly, let's ensure we return y2
        return y2



    def smooth_step_function(x):
        if x1 <= x <= x2:
            #num_steps = int((x2) - (x1))
            num_steps = int(math.ceil(x2 - x1))
            #print(x2, " ", x1)
            if num_steps < 1:
                num_steps = 2  # Ensure at least one step
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
            #return step_function
            #return smooth_step_function
            return exponential_step_function
        elif arc in ['Straight Increase']:
            return smooth_exponential_increase_function
        elif arc in ['Straight Decrease']:
            return smooth_exponential_decrease_function
        elif arc in ['Linear Increase','Linear Decrease','Gradual Increase', 'Gradual Decrease', 'Linear Flat']:
            return linear_function
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


def transform_story_data(data, x_delta):
    # Convert JSON to DataFrame
    try:
        df = pd.json_normalize(
            data, 
            record_path=['story_components'], 
            meta=[
                'title', 
                'protagonist'
            ],
            record_prefix='story_component_'
        )
    except Exception as e:
        print("Error:", e)
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
            story_component_arc
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
            story_component_arc
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


def chaikin_curve(points, iterations=1):
    """
    points is a list of (x, y) tuples.
    """
    for _ in range(iterations):
        new_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            # Add two new points 1/4 and 3/4 along the edge
            q = (0.75*p1[0] + 0.25*p2[0], 0.75*p1[1] + 0.25*p2[1])
            r = (0.25*p1[0] + 0.75*p2[0], 0.25*p1[1] + 0.75*p2[1])
            new_points.append(q)
            new_points.append(r)
        # Add final point
        new_points.append(points[-1])
        points = new_points
    return points


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

