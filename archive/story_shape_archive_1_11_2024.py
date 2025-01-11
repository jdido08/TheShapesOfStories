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


# Load API key from config
with open("config.yaml", 'r') as stream:
    config = yaml.safe_load(stream)
    OPENAI_KEY = config['openai_key_vonnegutgraphs']
    client = OpenAI(api_key=OPENAI_KEY)

def create_shape(story_data_path,
                num_points = 500,
                font_style="Sans",
                font_size=72,
                font_color = (0, 0, 0), #default to black
                line_type = 'char',
                line_thickness = 2,
                line_color = (0,0,0),
                background_type='solid', 
                background_value=(1, 1, 1), 
                has_title = "NO", #values YES or NO
                title_font_style = "Sans",
                title_font_size=96,
                title_font_color = (0, 0, 0),#default to black
                title_padding = 20,
                gap_above_title = 20,
                border = False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
                recursive_mode = True,
                output_format="png"):
    

    with open(story_data_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        if 'story_plot_data' in story_data:
            story_data = story_data['story_plot_data']
    
    #get title 
    path_title = story_data['title'].lower().replace(' ', '_')
    path_size = f'{width_in_inches}x{height_in_inches}'
    check_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{path_title}_{path_size}.json'
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
    
    if line_type == "line":
        if output_format == "svg":
            story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_size}_{line_type}_{line_thickness}.svg'
        elif output_format == "png":
            story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_size}_{line_type}_{line_thickness}.png'
    else:
        story_shape_font = font_style.lower().replace(' ', '_') + "_" + str(font_size)
        if output_format == "svg":
            story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_size}_{line_type}_{story_shape_font}.svg'
        elif output_format == "png":
            story_shape_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/{story_shape_title}_{story_shape_size}_{line_type}_{story_shape_font}.png'

    status = "processing"
    count = 1
    # while status == "processing":
    for i in range(1000):
        # print(story_data['story_components'][1]['modified_end_time'])
        story_data = transform_story_data(story_data, num_points)

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
                    title_font_style=title_font_style,
                    title_font_size=title_font_size,
                    title_font_color = title_font_color,
                    title_padding = title_padding,
                    gap_above_title = gap_above_title,
                    border = border,
                    border_thickness=border_thickness,
                    border_color=border_color,
                    width_in_inches=width_in_inches,
                    height_in_inches=height_in_inches,
                    wrap_in_inches=wrap_in_inches,
                    story_shape_path=story_shape_path,
                    recursive_mode=recursive_mode,
                    output_format = output_format)

        #print(count, " .) ", status)
        if(count % 50 == 0):
            print(count)

        count = count + 1
        if status == "completed":
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
    new_title = story_data['title'].lower().replace(' ', '_')
    new_size = f'{width_in_inches}x{height_in_inches}'
    new_path = f'/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/{new_title}_{new_size}.json'
    with open(new_path, 'w', encoding='utf-8') as file:
        json.dump(story_data, file, ensure_ascii=False, indent=4)

def create_shape_single_pass(story_data, 
                font_style="Sans",
                font_size=72,
                font_color = (0, 0, 0), #default to black
                line_type = 'char',
                line_thickness = 2,
                line_color = (0,0,0),
                background_type='solid', 
                background_value=(1, 1, 1), 
                has_title = "NO",
                title_font_style = "Sans",
                title_font_size=96,
                title_font_color = (0, 0 , 0), #default to black
                title_padding = 20,
                gap_above_title = 20,
                border=False,
                border_thickness=4,
                border_color=(0, 0, 0),
                width_in_inches = 15,
                height_in_inches = 15,
                wrap_in_inches=1.5,
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


    # Set margins in inches and convert to pixels
    ratio = 1.0 / 15.0
    margin_in_inches = ratio * min(width_in_inches, height_in_inches)
    margin_in_inches = max(0.25, min(margin_in_inches, 1.0))
    margin_x = int(margin_in_inches * dpi)
    margin_y = int(margin_in_inches * dpi)

    # Determine data range for x and y
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Create a Cairo surface and context
    import cairo
    if output_format == "svg":
        surface = cairo.SVGSurface(story_shape_path, width, height)
    else:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)

    from gi.repository import Pango, PangoCairo
    pangocairo_context = PangoCairo.create_context(cr)

    # Set background according to specified type
    if background_type == 'transparent':
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
    elif background_type == 'solid':
        r, g, b = background_value
        cr.set_source_rgb(r, g, b)
        cr.paint()
    else:
        print("background_type:", background_type, "is not valid (must be 'transparent' or 'solid').")

    # if border == True:
    #     cr.set_source_rgb(*border_color)       # e.g. (0,0,0) for black
    #     cr.set_line_width(border_thickness)    # e.g. 4 px thick
    #     cr.rectangle(0, 0, width, height)      # outer edge
    #     cr.stroke()


    # We shift the origin so that (0,0) effectively starts at the
    # top-left corner of the “actual” area.
    actual_area_x_offset = wrap_in_inches * dpi
    actual_area_y_offset = wrap_in_inches * dpi

    cr.save()
    cr.translate(actual_area_x_offset, actual_area_y_offset)

    # 2) After you have defined design_width and design_height,
    #    draw the border AFTER translating.
    design_width = int(width_in_inches * dpi)
    design_height = int(height_in_inches * dpi)

    if border:
        cr.save()
        cr.set_source_rgb(*border_color)
        cr.set_line_width(border_thickness)
        cr.rectangle(0, 0, design_width, design_height)
        cr.stroke()
        cr.restore()

   # 3) If we have a title, measure its pixel height
    title_text = story_data.get('title', '')
    measured_title_height = 0

    if has_title == "YES":
        layout_temp = PangoCairo.create_layout(cr)
        scaled_title_size = title_font_size * (300 / 96)
        temp_desc = Pango.FontDescription(f"{title_font_style} {scaled_title_size}")
        layout_temp.set_font_description(temp_desc)
        layout_temp.set_text(title_text, -1)
        _, measured_title_height = layout_temp.get_pixel_size()

    # So the total vertical space for the "title band" is:
    # measured_title_height + title_padding
    title_band_height = measured_title_height + title_padding

    # The arcs should stop 'gap_above_title' pixels above that band.
    # So we subtract (title_band_height + gap_above_title) from the available space.
    drawable_width = width - 2 * margin_x
    drawable_height = (height - 2 * margin_y) - (title_band_height + gap_above_title)
    if drawable_height < 0:
        drawable_height = 0

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
        if output_format == "svg":
            surface.finish()
        else:
            surface.write_to_png(story_shape_path)
        return story_data, "completed"

    elif line_type == "char":
        from scipy.interpolate import CubicSpline
        import numpy as np

        font_size_for_300dpi = font_size * (300 / 96)
        import copy

        # Prepare for text on arcs
        from gi.repository import Pango
        font_desc = Pango.FontDescription(f"{font_style} {font_size_for_300dpi}")
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

                # Generate descriptors (call your GPT logic)
                descriptors_text, chat_messages = generate_descriptors(
                    title=title,
                    component_description=description,
                    story_data=story_data,
                    desired_length=target_chars
                )

                actual_chars = len(descriptors_text)
                lower_bound = target_chars - 3
                upper_bound = target_chars + 3
                valid_descriptor = False
                max_attempts = 5
                attempt = 1

                if lower_bound <= actual_chars <= upper_bound:
                    valid_descriptor = True
                else:
                    while not valid_descriptor and attempt <= max_attempts:
                        descriptors_text, chat_messages = adjust_descriptors(
                            desired_length=target_chars,
                            actual_length=actual_chars,
                            chat_messages=chat_messages
                        )
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

                elif ((new_x >= old_max_x or new_x <= old_min_x) and recursive_mode):
                    new_x = x_og[-1]
                    component['modified_end_time'] = new_x
                    component['modified_end_emotional_score'] = new_y


                    if output_format == "svg":
                        surface.flush()   # flush the partial drawing, but do *not* finalize!
                    else:
                        surface.write_to_png(story_shape_path)
                    return story_data, "processing"
                
                elif ((new_y >= old_max_y or new_y <= old_min_y) and recursive_mode):
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
                    status = "curve too long but can't change due to constraints"

            elif curve_length_status == "curve_too_long":
                if (original_arc_end_time_values[-1] != old_min_x 
                    and original_arc_end_time_values[-1] != new_max_x
                    and original_arc_end_emotional_score_values[-1] != old_min_y
                    and original_arc_end_emotional_score_values[-1] != old_max_y
                    and len(component['arc_x_values']) > 1 and recursive_mode):
                    
                    original_arc_end_time_values.pop()
                    original_arc_end_emotional_score_values.pop()
                    component['modified_end_time'] = original_arc_end_time_values[-1]
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
                    status = "curve too short but can't change due to constraints"

            elif curve_length_status == "curve_correct_length":
                if output_format == "svg":
                    surface.flush()   # flush the partial drawing, but do *not* finalize!
                else:
                    surface.write_to_png(story_shape_path)
                status = 'All phrases fit exactly on the curve.'

            component['status'] = status

        # Once arcs are fully drawn, we place the title in the reserved space at bottom
        # (instead of top).
        # 6) Now place the title, below that gap
        if has_title == "YES":
            # The top of the "title band" is at 'height - margin_y - title_band_height'.
            # But we actually added 'gap_above_title' above that band, so:
            # The arcs end at: margin_y + drawable_height
            # The gap is: gap_above_title
            # Title band starts at: (margin_y + drawable_height) + gap_above_title
            # or equivalently: height - margin_y - title_band_height
            # They should be the same number.

            final_layout = PangoCairo.create_layout(cr)
            final_desc = Pango.FontDescription(f"{title_font_style} {scaled_title_size}")
            final_layout.set_font_description(final_desc)
            final_layout.set_text(title_text, -1)

            # The top of the title band:
            title_band_top = (margin_y + drawable_height) + gap_above_title
            # That is the same as (height - margin_y - title_band_height).

            # If you want to place it flush at that top:
            title_x = margin_x
            title_y = title_band_top  # same as above

            # If you want it centered in that band, do:
            # _, actual_title_height = final_layout.get_pixel_size()
            # title_y = title_band_top + (title_band_height - actual_title_height)/2

            cr.set_source_rgb(*title_font_color)
            cr.move_to(title_x, title_y)
            PangoCairo.show_layout(cr, final_layout)

        # 7) Save final image
        if output_format == "svg":
            surface.finish()
        else:
            surface.write_to_png(story_shape_path)

        return story_data, "completed"

    else:
        print("line_type:", line_type, " is not valid. Needs to be 'line' or 'char'.")


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

def generate_descriptors(title, component_description, story_data, desired_length):
    story_dict = copy.deepcopy(story_data)
    del story_dict['x_values']
    del story_dict['y_values']
    for component in story_dict['story_components']:
        if 'arc_x_values' in component:
            del component['arc_x_values']
        if 'arc_y_values' in component:
            del component['arc_y_values']

    existing_arc_texts = ""
    for component in story_dict['story_components']:
        if 'arc_text' in component:
            if(existing_arc_texts == ""):
                existing_arc_texts = """Pay special attention to the `arc_text` of previous story components to maintain continuity and avoid repeating words.

**Previous `arc_text`s:**

"""
            existing_arc_texts = existing_arc_texts + " " + component['arc_text']

    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    user_message = {
        "role": "user",
        "content": f"""
Generate a succinct, concise, and stylized description for the following segment of the story **"{title}"**: **"{component_description}"**.

Use the structured data below to understand how this segment fits into the larger narrative. {existing_arc_texts}

Your description should:

- Be exactly {desired_length} characters long.
- Consist of keywords or phrases that best represent and describe this story segment.
- Help observers identify this particular story segment.
- Include elements such as:
  1. Iconic phrases or popular quotes from the story segment.
  2. Names or descriptions of important or iconic characters involved or introduced in that part of the story.
  3. Names or descriptions of significant events that occur during the segment.
  4. Names or descriptions of notable inanimate objects that play a role in the story segment.
  5. Names or descriptions of key settings where the story segment takes place.
  6. Descriptive phrases of the story segment.

- **After generating your output, verify that it is EXACTLY the specified length.**

- **Avoid using words or phrases that have already appeared in previous `arc_text`s, unless necessary for coherence. Use synonyms or alternative expressions to keep the narrative fresh.**

- **Ensure the description continues the flow of the overall story, connecting smoothly with previous segments.**

- List the keywords/phrases in chronological order.

- **Capitalize all important words in the keywords/phrases, except for unimportant words such as articles, conjunctions, and prepositions.**

- Include spaces within keywords or phrases as needed, and **include a space after the punctuation that separates keywords/phrases.**

- **Do not include any quotation marks ("") in the outputs.**

- **Punctuation and spaces are included and count towards the total character limit.**

- **Punctuation (periods, commas) MUST be counted in the total character limit.**

- **You MUST count each character, including spaces and punctuation, to ensure exact match to the specified length.**


Here's some structured data providing more context on the entire story:
{story_dict}

"""
    }

    chat_messages = [system_message, user_message]

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=chat_messages,
        max_tokens=int(desired_length * 5),
        temperature=0.7
    )

    response_text = completion.choices[0].message.content.strip()
    data = {"role":"assistant", "content":response_text}
    chat_messages.append(data)

    return response_text, chat_messages

def adjust_descriptors(desired_length, actual_length, chat_messages):
    user_message = {
        "role": "user",
        "content": f"""
The previous description was {actual_length} characters long but needs to be adjusted to exactly {desired_length} characters.

CRITICAL DESCRIPTOR GENERATION GUIDELINES:

Your task is to create a COMPLETELY UNIQUE segment description that:
- STANDS ENTIRELY ON ITS OWN
- CONTAINS NO REFERENCE to previous story segments
- INTRODUCES NEW NARRATIVE ELEMENTS
- CAPTURES THE ESSENCE of this specific moment WITHOUT relying on prior context

Key Principles:
- ZERO CONTINUITY with previous descriptions
- INDEPENDENT narrative snapshot
- FRESH perspective for EACH story segment
- ZERO character or event callbacks

REQUIREMENTS:
- Exactly {desired_length} characters long
- Each description is a SELF-CONTAINED narrative fragment
- Use ENTIRELY NEW descriptive language
- AVOID any linguistic or thematic echoes from previous segments

Think of each descriptor as a STANDALONE HAIKU of the moment - capturing its UNIQUE EMOTIONAL and NARRATIVE CORE without external references.

Output ONLY the updated description that is a COMPLETE NARRATIVE UNIVERSE unto itself.
"""
    }

    chat_messages.append(user_message)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=chat_messages,
        max_tokens=int(desired_length * 5),
        temperature=0.7
    )

    response_text = completion.choices[0].message.content.strip()
    assistant_message = {"role": "assistant", "content": response_text}
    chat_messages.append(assistant_message)

    return response_text, chat_messages

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

    # def smooth_step_function(x):
    #     if x1 <= x <= x2:
    #         x_center = (x1 + x2) / 2
    #         k = (x2 - x1) / 10  # Adjust k for smoothness; smaller k means steeper transition
    #         transition = 1 / (1 + np.exp(-(x - x_center) / k))
    #         return y1 + (y2 - y1) * transition
    #     else:
    #         return None

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

    def smooth_drop_function(x):
        if x1 <= x <= x2:
            x_center = x1 + (x2 - x1) / 2
            k = (x2 - x1) / 10
            transition = 1 / (1 + np.exp(-(x - x_center) / k))
            return y1 + (y2 - y1) * transition
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

        if x1 <= x <= x2:
            # Parameters to adjust
            horizontal_fraction = 0.01  # Adjust as needed

            # Calculate key points
            #total_interval = x2 - x1
            total_interval = 0
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                # Initial horizontal segment at y1
                return y1
            elif horizontal_end <= x <= x2:
                # Linear decrease from y1 to y2
                t = (x - horizontal_end) / (x2 - horizontal_end)
                return y1 + (y2 - y1) * t
            else:
                return None
        else:
            return None

    def drop_function(x):
        if x1 <= x <= x2:
            return y2 
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

    def smooth_exponential_decrease_function(x):
        # Only define behavior in the interval [x1, x2]
        if x1 <= x <= x2:
            # We want the function to rapidly drop from y1 at x1 and approach y2 as x approaches x2.
            # Let's choose k so that at x2 we're close to y2, say within 1%:
            # exp(-k*(x2-x1)) = 0.01 -> -k*(x2-x1)=ln(0.01) -> k = -ln(0.01)/(x2-x1)
            # ln(0.01) ~ -4.60517, so k ≈ 4.6/(x2-x1).
            # You can adjust this factor (4.6) if you want a different "steepness".
            if x2 > x1:  
                k = 4.6 / (x2 - x1)
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
                k = 4.6 / (x2 - x1)
            else:
                k = 1.0

            # For an "increase", you can simply flip the logic:
            # Start at y1 and approach y2 from below using a mirrored exponential shape:
            # y(x) = y1 + (y2 - y1)*(1 - exp(-k*(x - x1)))
            return y1 + (y2 - y1)*(1 - math.exp(-k*(x - x1)))
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
    
    def partial_exponential_transition_function(x):
        vertical_fraction = 0.5
        flatten_fraction = 0.01
        horizontal_fraction = 0.01  # New parameter to mimic the original horizontal pause

        if x1 <= x <= x2:
            total_length = x2 - x1
            x_horizontal_end = x1 + horizontal_fraction * total_length
            x_mid = x1 + vertical_fraction * total_length

            # Determine y_mid
            delta = 0.1 * (y1 - y2)
            y_mid = y2 + delta

            # Phase 1: Horizontal portion at the start
            if x < x_horizontal_end:
                # For a tiny fraction of the interval, just stay at y1
                return y1

            # Phase 2: Linear descent (or ascent) from y1 to y_mid by x_mid
            # After the horizontal segment, we have a smaller effective linear portion
            # That goes from (x_horizontal_end, y1) to (x_mid, y_mid)
            # Adjust the linear interpolation to start from x_horizontal_end instead of x1
            if x_horizontal_end <= x <= x_mid:
                # Avoid division by zero if vertical_fraction and horizontal_fraction overlap significantly
                if x_mid == x_horizontal_end:
                    return y_mid
                t = (x - x_horizontal_end) / (x_mid - x_horizontal_end)
                return y1 + (y_mid - y1)*t

            # Phase 3: Exponential tail from x_mid to x2
            if x > x_mid:
                if x2 == x_mid:
                    return y_mid
                k = -math.log(flatten_fraction)/(x2 - x_mid)
                return y2 + (y_mid - y2)*math.exp(-k*(x - x_mid))

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
            return smooth_step_function
        elif arc in ['Straight Increase']:
            #return drop_function
            #return smooth_drop_function
            return straight_increase_function
            #return smooth_exponential_increase_function
            #return partial_exponential_transition_function
        elif arc in ['Straight Decrease']:
            return straight_decrease_function
            #return smooth_exponential_decrease_function
            #return partial_exponential_transition_function
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


def transform_story_data(data, num_points):
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

    # Get final values
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


