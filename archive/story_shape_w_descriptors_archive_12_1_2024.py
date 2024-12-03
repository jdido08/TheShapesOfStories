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
from story_function import get_component_arc_function
from scipy.interpolate import CubicSpline
import json

# Ensure the correct versions of Pango and PangoCairo are used
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo


    # Load API key from config
with open("config.yaml", 'r') as stream:
    config = yaml.safe_load(stream)
    OPENAI_KEY = config['openai_key_vonnegutgraphs']
    client = OpenAI(api_key=OPENAI_KEY)

def create_shape(story_data):

    simple_story_data = copy.deepcopy(story_data)
    # Remove specified keys ('arc_x_values', 'arc_y_values') from 'story_components'
    # and remove 'x_values' and 'y_values' from the main dictionary
    keys_to_remove = ['x_values', 'y_values']

    # Remove the keys from the main dictionary
    for key in keys_to_remove:
        simple_story_data.pop(key, None)

    # Remove keys from each story component
    for component in simple_story_data["story_components"]:
        component.pop("arc_x_values", None)
        component.pop("arc_y_values", None)

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

    #print(old_min_x, " ",old_max_x, " " ,old_min_y , " ",old_max_y )

    # Set the scaling ranges used in transform_story_data
    new_min_x, new_max_x = 1, 10
    new_min_y, new_max_y = -10, 10

    # Set image dimensions based on desired inches and DPI
    dpi = 300  # High-quality print resolution
    width_in_inches = 15
    height_in_inches = 15
    width = int(width_in_inches * dpi)
    height = int(height_in_inches * dpi)

    # Set margins in inches and convert to pixels
    margin_in_inches = 1  # 1-inch margins
    margin_x = int(margin_in_inches * dpi)
    margin_y = int(margin_in_inches * dpi)

    # Determine data range
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_range = x_max - x_min
    y_range = y_max - y_min


    # Calculate scaling factors without preserving aspect ratio
    drawable_width = width - 2 * margin_x
    drawable_height = height - 2 * margin_y
    scale_x = drawable_width / x_range
    scale_y = drawable_height / y_range

    # Adjust x_values and y_values: scale and shift to include margins
    x_values_scaled = [(x - x_min) * scale_x + margin_x for x in x_values]
    y_values_scaled = [height - ((y - y_min) * scale_y + margin_y) for y in y_values]  # Invert y-axis

    
    # Create a mapping from original to scaled coordinates
    coordinate_mapping = dict(zip(zip(x_values, y_values), zip(x_values_scaled, y_values_scaled)))


    # Create a Cairo surface and context with the specified width and height
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)

    # Set background color (optional)
    cr.set_source_rgb(1, 1, 1)  # White background
    cr.paint()

    # Draw the overall curve (optional, for visualization)
    cr.set_source_rgb(0, 0, 0)  # Black color for the curve
    cr.set_line_width(2)  # Increase line width for better visibility in high-resolution

    # Move to the starting point of the curve
    cr.move_to(x_values_scaled[0], y_values_scaled[0])

    # Draw the curve using lines
    for x, y in zip(x_values_scaled[1:], y_values_scaled[1:]):
        cr.line_to(x, y)

    cr.stroke()

    # Prepare Pango layout
    pangocairo_context = PangoCairo.create_context(cr)
    font_size = 72  # Adjust font size as needed
    font_desc = Pango.FontDescription(f"Sans {font_size}")

    # For overlap detection between arcs
    all_rendered_boxes = []

    title = story_data.get('title', '')

    # Process each story component
    for index, component in enumerate(story_data['story_components'][1:]):
        index = index + 1  # Because [1:] shifts the starting index

        arc_x_values = component.get('arc_x_values', [])
        arc_y_values = component.get('arc_y_values', [])
        description = component.get('description', '')

        # Skip if arc data is missing
        if not arc_x_values or not arc_y_values:
            continue

        # Scale and shift arc coordinates
        arc_x_values_scaled = []
        arc_y_values_scaled = []
        for x, y in zip(arc_x_values, arc_y_values):
            if (x, y) in coordinate_mapping:
                x_scaled, y_scaled = coordinate_mapping[(x, y)]
            else:
                # Scale individually if not in the overall mapping
                x_scaled = (x - x_min) * scale_x + margin_x
                y_scaled = height - ((y - y_min) * scale_y + margin_y)
            arc_x_values_scaled.append(x_scaled)
            arc_y_values_scaled.append(y_scaled)

        #get arc x and y values in original scales in json
        # Create a mapping from scaled coordinates to original end_time and end_emotional_score
        # First, reverse the scaling from transform_story_data to get original values
        def reverse_scale_plot_points(scaled_x, old_min, old_max, new_min=1, new_max=10):
            return ((scaled_x - new_min) / (new_max - new_min)) * (old_max - old_min) + old_min

        def reverse_scale_y_values(scaled_y, old_min, old_max, new_min=-10, new_max=10):
            return ((scaled_y - new_min) / (new_max - new_min)) * (old_max - old_min) + old_min

        # Reverse scaling from transform_story_data
        original_arc_end_time_values = [reverse_scale_plot_points(x, old_min_x, old_max_x, new_min_x, new_max_x) for x in arc_x_values]
        original_arc_end_emotional_score_values = [reverse_scale_y_values(y, old_min_y, old_max_y, new_min_y, new_max_y) for y in arc_y_values]
        #print(original_arc_end_time_values)

        #print(min(original_arc_end_time_values), " ", max(original_arc_end_time_values), " ", min(original_arc_end_emotional_score_values), " ", max(original_arc_end_emotional_score_values))

        # # Create mapping between x_values_scaled and y_values_scaled and original end_time and end_emotional_score values
        # coordinate_mapping_scaled_to_original = dict(zip(zip(x_values_scaled, y_values_scaled), zip(original_arc_end_time_values, original_arc_end_emotional_score_values)))

        # Draw the arc
        cr.set_source_rgb(0, 0, 0)  # Black color for the arc
        cr.set_line_width(2)

        cr.move_to(arc_x_values_scaled[0], arc_y_values_scaled[0])
        for x, y in zip(arc_x_values_scaled[1:], arc_y_values_scaled[1:]):
            cr.line_to(x, y)
        cr.stroke()

        # Step 1: Calculate arc length
        arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled)

        # Step 2: Calculate Descriptors (if needed)
        if 'arc_text' not in component:
            average_char_width = get_average_char_width(pangocairo_context, font_desc)
            target_chars = estimate_characters_fit(arc_length, average_char_width)
            component['target_arc_text_chars'] = target_chars
            target_words = target_chars / 4.7

            # Ensure at least some characters can be displayed
            if target_chars < 5:
                continue  # Skip this arc if too small
            
            x = 5  # Acceptable percentage range
            # lower_bound = target_words * (1 - x / 100)
            # upper_bound = target_words * (1 + x / 100)
            lower_bound = target_words - 5
            upper_bound = target_words + 5

            valid_descriptor = False
            # Step 3: Generate descriptors
            descriptors_text, chat_messages = generate_descriptors(
                title=title,
                component_description=description,
                story_dict=simple_story_data,
                desired_length=target_words
            )
            
            actual_chars = len(descriptors_text) 
            actual_words = len(descriptors_text.split())

            print("original descriptors: ", descriptors_text, " | target: ", target_words, " | actual: ",  actual_words, "Acceptable Range: ", lower_bound, " - ", upper_bound)

            # Check if actual_chars falls within the range
            if lower_bound <= actual_chars <= upper_bound:
                valid_descriptor = True
            else:
                count = 1
                while not valid_descriptor and count < 2:
                    
                    descriptors_text, chat_messages = adjust_descriptors(
                        desired_length=target_words,
                        actual_length=actual_words,
                        original_output=descriptors_text,
                        chat_messages=chat_messages
                    )
                

                    actual_chars = len(descriptors_text)
                    actual_words = len(descriptors_text.split())
                    if lower_bound <= actual_words <= upper_bound:
                        valid_descriptor = True

                    print("adjusted_descriptors: ", descriptors_text, " | target: ", target_words, " | actual: ",  actual_words, "Acceptable Range: ", lower_bound, " - ", upper_bound)
                    count = count + 1
        
            component['arc_text'] = descriptors_text
            component['actual_arc_text_chars'] = len(descriptors_text)
        else:
            descriptors_text = component['arc_text']
            component['actual_arc_text_chars'] = len(component['arc_text'])

       # Draw text on curve using the updated function
        curve_length_status = draw_text_on_curve(
            cr, arc_x_values_scaled, arc_y_values_scaled, descriptors_text,
            pangocairo_context, font_desc, all_rendered_boxes
        )

        # You can now use curve_length_status as needed
        if curve_length_status == "curve_too_short":
            print("Result: The curve was too short; not all phrases could be plotted.")
            
            # Use cubic spline model to extrapolate
            cs = CubicSpline(original_arc_end_time_values, original_arc_end_emotional_score_values, extrapolate=True)

            # Calculate increment for x (1/9 of the last x value)
            x_increment = (original_arc_end_time_values[1] - original_arc_end_time_values[0])+.001


            # New x value
            new_x = original_arc_end_time_values[-1] + x_increment
            #print(original_arc_end_time_values)

            # New y value using the spline
            new_y = float(cs(new_x))  # Ensure it's a Python float
            
            # print("last x: ", original_arc_end_time_values[-1])
            # print("new_x: ", new_x)
            # print("new_y: ", new_y)
            print("og_end_x: ", component['end_time'], " new_x: ", new_x, " og_end_y: ", component['end_emotional_score'] ," new_y: ", new_y)
            if(new_x >= old_min_x and new_max_x <= old_max_x and new_y >= old_min_y and new_y <= old_max_y):
                component['modified_end_time'] = new_x
                component['modified_end_emotional_score'] = new_y
                surface.write_to_png("text_along_curve.png")
                #print("HEY")
                return story_data

        elif curve_length_status == "curve_too_long":
            print("Result: The curve was too long; extra space remains after placing all phrases.")

            if(original_arc_end_time_values[-1] != old_min_x and original_arc_end_time_values[-1] != new_max_x and original_arc_end_emotional_score_values[-1] != old_min_y and original_arc_end_emotional_score_values[-1] != old_max_y and len(component['arc_x_values']) > 1):

                original_arc_end_time_values.pop()
                original_arc_end_emotional_score_values.pop()

                component['modified_end_time'] = original_arc_end_time_values[-1]
                component['modified_end_emotional_score'] = original_arc_end_emotional_score_values[-1]
                surface.write_to_png("text_along_curve.png")
                return story_data

        elif curve_length_status == "curve_correct_length":
            surface.write_to_png("text_along_curve.png")
            print("Result: All phrases fit exactly on the curve.")

    # Save the image to a file
    surface.write_to_png("text_along_curve.png")

def calculate_arc_length(arc_x_values, arc_y_values):
    segment_lengths = np.hypot(
        np.diff(arc_x_values), np.diff(arc_y_values)
    )
    total_length = np.sum(segment_lengths)
    return total_length

def get_average_char_width(pangocairo_context, font_desc):
    # Measure average character width
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)

    # Use a representative sample of characters
    sample_text = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " .,!?;:'\"()-"
    )

    layout.set_text(sample_text, -1)
    total_width = layout.get_pixel_size()[0]
    average_char_width = total_width / len(sample_text)
    return average_char_width

def estimate_characters_fit(arc_length, average_char_width, spacing=1.0):
    # Estimate the number of characters that can fit along the arc
    return int(arc_length / (average_char_width * spacing))

def generate_descriptors(title, component_description, story_dict, desired_length):

    # System message to set context for the model
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    # User message as the main prompt
    user_message = {
        "role": "user",
        "content": f"""
Generate a succinct, concise, and stylized description for the following segment of the story **"{title}"**: **"{component_description}"**. Use the JSON below to understand how this segment fits into the larger narrative.

Your description should:

- Be exactly **{desired_length}** characters long.
- Consist of keywords or phrases that best represent and describe this story segment.
- Help observers identify this particular story segment.
- Include elements such as:
  1. Iconic phrases or popular quotes from the story segment.
  2. Names or descriptions of important or iconic characters involved or introduced in that part of the story.
  3. Names or descriptions of significant events that occur during the segment.
  4. Names or descriptions of notable inanimate objects that play a role in the story segment.
  5. Names or descriptions of key settings where the story segment takes place.
  6. Descriptive phrases of the story segment.
- List the keywords/phrases in chronological order.
- **Capitalize all important words in the keywords/phrases, except for unimportant words such as articles, conjunctions, and prepositions.**
- Include spaces within keywords or phrases as needed, and **include a space after the punctuation that separates keywords/phrases.**
- **Do not include any quotation marks ("") in the outputs.**
- **Punctuation and spaces are included but do not count as words.**

Here's the JSON providing more context on the entire story:
{story_dict}
"""
            }

    # Compile messages
    chat_messages = [system_message, user_message]

    print(user_message)

    # Create completion request
    completion = client.chat.completions.create(
        model="gpt-4o",  # Update as needed
        messages=chat_messages,
        max_tokens=int(desired_length * 5),  # Estimate tokens from character length
        temperature=0.7
    )

    # Parse and extract the response content
    response_text = completion.choices[0].message.content.strip()
    data = {"role":"assistant", "content":response_text}
    chat_messages.append(data)

    return response_text, chat_messages


def adjust_descriptors(desired_length, actual_length, original_output, chat_messages ):
    # System message to set context for the model
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    # User message as the main prompt
    user_message = {
        "role": "user",
        "content":f"""
The previous description does not meet the required word count specifications.

- **Target Word Count:** {desired_length}
- **Actual Word Count:** {actual_length}
- **Original Output:**

{original_output}

Please revise the description to meet the following requirements:

- Adjust the description to be exactly **{desired_length}** words long.
- Ensure that all previous guidelines are followed:

  - Consist of keywords or phrases that best represent and describe the story segment.
  - Help observers identify this particular story segment.
  - Include elements such as:
    1. Iconic phrases or popular quotes from the story segment.
    2. Names or descriptions of important or iconic characters involved or introduced in that part of the story.
    3. Names or descriptions of significant events that occur during the segment.
    4. Names or descriptions of notable inanimate objects that play a role in the story segment.
    5. Names or descriptions of key settings where the story segment takes place.
    6. Descriptive phrases of the story segment.
  - List the keywords/phrases in chronological order.
  - **Capitalize all important words in the keywords/phrases, except for unimportant words such as articles, conjunctions, and prepositions.**
  - Include spaces within keywords or phrases as needed, and **include a space after the punctuation that separates keywords/phrases.**
  - **Do not include any quotation marks ("") in the outputs.**
  - **Punctuation and spaces are included but do not count as words.**

Please adjust your description accordingly to meet the exact word count and guidelines and please output only the updated description and nothing else.

---

**Example Adjustment:**

If the original output was:

Privet Drive. Hagrid Arrives. Diagon Alley. Wand Chooses. Hogwarts Express. Sorting Hat.

- **Actual Word Count:** 12
- **Target Word Count:** 15

An adjusted version meeting the 15-word requirement could be:

Privet Drive. Letters Arrive. Hagrid Visits. Diagon Alley. Ollivander's Wand Chooses. Hogwarts Express. Sorting Hat.

- **Adjusted Word Count:** 15 words
"""
    }

    # Compile messages
    chat_messages.append(user_message)

    # Create completion request
    completion = client.chat.completions.create(
        model="gpt-4o",  # Update as needed
        messages=chat_messages,
        max_tokens=int(desired_length * 5),  # Estimate tokens from character length
        temperature=0.7
    )

    # Parse and extract the response content
    response_text = completion.choices[0].message.content.strip()
    data = {"role":"assistant", "content":response_text}
    chat_messages.append(data)

    return response_text, chat_messages
    
# def draw_text_on_curve(cr, x_values_scaled, y_values_scaled, text, pangocairo_context, font_desc, all_rendered_boxes):
#     # Initialize variables for character placement
#     char_positions = []
#     total_curve_length = np.sum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled)))
#     cumulative_curve_lengths = np.insert(np.cumsum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))), 0, 0)

#     idx_on_curve = 0  # Index on the curve
#     distance_along_curve = 0  # Distance along the curve
#     rendered_boxes = []  # List to keep track of character bounding boxes

#     # Function to calculate the tangent angle at a point on the curve
#     def get_tangent_angle(x_vals, y_vals, idx):
#         if idx == 0:
#             dx = x_vals[1] - x_vals[0]
#             dy = y_vals[1] - y_vals[0]
#         elif idx == len(x_vals) - 1:
#             dx = x_vals[-1] - x_vals[-2]
#             dy = y_vals[-1] - y_vals[-2]
#         else:
#             dx = x_vals[idx + 1] - x_vals[idx - 1]
#             dy = y_vals[idx + 1] - y_vals[idx - 1]
#         angle = math.atan2(dy, dx)
#         return angle

#     all_text_fits = True  # Flag to check if all text fits
#     extra_space = False   # Flag to check if extra space remains after placing all text

#     for char in text:
#         # Measure character dimensions
#         layout = Pango.Layout.new(pangocairo_context)
#         layout.set_font_description(font_desc)
#         layout.set_text(char, -1)
#         char_width, char_height = layout.get_pixel_size()

#         # Start searching for the next position along the curve
#         while idx_on_curve < len(cumulative_curve_lengths) - 1:
#             # Get the current position on the curve
#             segment_start_distance = cumulative_curve_lengths[idx_on_curve]
#             segment_end_distance = cumulative_curve_lengths[idx_on_curve + 1]
#             segment_distance = segment_end_distance - segment_start_distance

#             if segment_distance == 0:
#                 idx_on_curve += 1
#                 continue

#             # Calculate the ratio along the segment
#             ratio = (distance_along_curve - segment_start_distance) / segment_distance

#             if ratio < 0 or ratio > 1:
#                 idx_on_curve += 1
#                 continue

#             x = x_values_scaled[idx_on_curve] + ratio * (x_values_scaled[idx_on_curve + 1] - x_values_scaled[idx_on_curve])
#             y = y_values_scaled[idx_on_curve] + ratio * (y_values_scaled[idx_on_curve + 1] - y_values_scaled[idx_on_curve])
#             angle = get_tangent_angle(x_values_scaled, y_values_scaled, idx_on_curve)

#             # Create the bounding box for the character
#             box = Polygon([
#                 (-char_width / 2, -char_height / 2),
#                 (char_width / 2, -char_height / 2),
#                 (char_width / 2, char_height / 2),
#                 (-char_width / 2, char_height / 2)
#             ])

#             # Rotate and translate the box to the character's position
#             rotated_box = shapely_rotate(box, angle * (180 / math.pi), origin=(0, 0), use_radians=False)
#             translated_box = shapely.affinity.translate(rotated_box, xoff=x, yoff=y)

#             # Check for overlap with the previous character
#             overlap = False
#             if rendered_boxes:
#                 if translated_box.intersects(rendered_boxes[-1]):
#                     # Move further along the curve to avoid overlap
#                     distance_along_curve += 1  # Increase this step as needed for performance vs. precision
#                     continue

#             # Check for overlap with other arcs' characters
#             for other_box in all_rendered_boxes:
#                 if translated_box.intersects(other_box):
#                     # Move further along the curve to avoid overlap
#                     distance_along_curve += 1  # Increase this step as needed for performance vs. precision
#                     overlap = True
#                     break
#             if overlap:
#                 continue

#             # No overlap detected, place the character
#             char_positions.append((x, y, angle, char, char_width, char_height))
#             rendered_boxes.append(translated_box)
#             all_rendered_boxes.append(translated_box)

#             # Move the distance along the curve forward by the width of the character
#             distance_along_curve += char_width  # Adjust as necessary

#             break
#         else:
#             # If we reach the end of the curve, stop placing characters
#             all_text_fits = False
#             break

#     # Check if extra space remains on the curve after placing all text
#     if all_text_fits:
#         remaining_curve_length = total_curve_length - distance_along_curve
#         if remaining_curve_length > average_char_width:
#             extra_space = True

#     # Render each character at its position
#     for x, y, angle, char, char_width, char_height in char_positions:
#         cr.save()
#         cr.translate(x, y)
#         cr.rotate(angle)

#         # Create a layout for the character
#         layout = PangoCairo.create_layout(cr)
#         layout.set_font_description(font_desc)
#         layout.set_text(char, -1)

#         # Adjust position to center the character horizontally and vertically
#         cr.translate(-char_width / 2, -char_height / 2)  # Center the character

#         # Render the character
#         PangoCairo.show_layout(cr, layout)
#         cr.restore()

#     return all_text_fits, extra_space

def draw_text_on_curve(cr, x_values_scaled, y_values_scaled, text, pangocairo_context, font_desc, all_rendered_boxes):
    # Initialize variables for character placement
    total_curve_length = np.sum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled)))
    cumulative_curve_lengths = np.insert(np.cumsum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))), 0, 0)

    idx_on_curve = 0  # Index on the curve
    distance_along_curve = 0  # Distance along the curve

    # Function to calculate the tangent angle at a point on the curve
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

    # Split text into phrases, including the ". " between phrases
    import re
    phrases = re.findall(r'.+?(?:\. |$)', text)
    phrases = [phrase for phrase in phrases if phrase.strip()]  # Remove empty phrases

    char_positions = []
    rendered_boxes = []  # List to keep track of character bounding boxes

    all_text_fits = True  # Flag to check if all text fits

    for phrase in phrases:
        # Temporary lists to store positions and boxes for the current phrase
        temp_char_positions = []
        temp_rendered_boxes = []

        # Save the current state to rollback if the phrase doesn't fit
        saved_idx_on_curve = idx_on_curve
        saved_distance_along_curve = distance_along_curve

        phrase_fits = True  # Flag to determine if the entire phrase fits

        for char in phrase:
            # Measure character dimensions
            layout = Pango.Layout.new(pangocairo_context)
            layout.set_font_description(font_desc)
            layout.set_text(char, -1)
            char_width, char_height = layout.get_pixel_size()

            # Start searching for the next position along the curve
            while idx_on_curve < len(cumulative_curve_lengths) - 1:
                # Get the current position on the curve
                segment_start_distance = cumulative_curve_lengths[idx_on_curve]
                segment_end_distance = cumulative_curve_lengths[idx_on_curve + 1]
                segment_distance = segment_end_distance - segment_start_distance

                if segment_distance == 0:
                    idx_on_curve += 1
                    continue

                # Calculate the ratio along the segment
                ratio = (distance_along_curve - segment_start_distance) / segment_distance

                if ratio < 0 or ratio > 1:
                    idx_on_curve += 1
                    continue

                x = x_values_scaled[idx_on_curve] + ratio * (x_values_scaled[idx_on_curve + 1] - x_values_scaled[idx_on_curve])
                y = y_values_scaled[idx_on_curve] + ratio * (y_values_scaled[idx_on_curve + 1] - y_values_scaled[idx_on_curve])
                angle = get_tangent_angle(x_values_scaled, y_values_scaled, idx_on_curve)

                # Create the bounding box for the character
                box = Polygon([
                    (-char_width / 2, -char_height / 2),
                    (char_width / 2, -char_height / 2),
                    (char_width / 2, char_height / 2),
                    (-char_width / 2, char_height / 2)
                ])

                # Rotate and translate the box to the character's position
                rotated_box = shapely_rotate(box, angle * (180 / math.pi), origin=(0, 0), use_radians=False)
                translated_box = shapely.affinity.translate(rotated_box, xoff=x, yoff=y)

                # Check for overlap with previous characters
                overlap = False
                for other_box in rendered_boxes + all_rendered_boxes:
                    if translated_box.intersects(other_box):
                        # Move further along the curve to avoid overlap
                        distance_along_curve += 1  # Adjust as needed
                        break  # Try placing the character at the new position
                else:
                    # No overlap detected, place the character
                    temp_char_positions.append((x, y, angle, char, char_width, char_height))
                    temp_rendered_boxes.append(translated_box)
                    rendered_boxes.append(translated_box)
                    all_rendered_boxes.append(translated_box)

                    # Move the distance along the curve forward by the width of the character
                    distance_along_curve += char_width  # Adjust as necessary

                    break  # Move to the next character in the phrase
            else:
                # If we reach the end of the curve, the phrase doesn't fit
                phrase_fits = False
                break

        if phrase_fits:
            # Add the positions of this phrase to the main list
            char_positions.extend(temp_char_positions)
        else:
            # Phrase doesn't fit, rollback the state and skip the phrase
            idx_on_curve = saved_idx_on_curve
            distance_along_curve = saved_distance_along_curve
            rendered_boxes = rendered_boxes[:len(rendered_boxes) - len(temp_rendered_boxes)]
            all_rendered_boxes = all_rendered_boxes[:len(all_rendered_boxes) - len(temp_rendered_boxes)]
            all_text_fits = False  # Not all text fits
            break  # Exit the loop since the curve is too short

    # Render each character at its position
    for x, y, angle, char, char_width, char_height in char_positions:
        cr.save()
        cr.translate(x, y)
        cr.rotate(angle)

        # Create a layout for the character
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(font_desc)
        layout.set_text(char, -1)

        # Adjust position to center the character horizontally and vertically
        cr.translate(-char_width / 2, -char_height / 2)  # Center the character

        # Render the character
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    # Determine the curve length status
    average_char_width = get_average_char_width(pangocairo_context, font_desc)
    remaining_curve_length = total_curve_length - distance_along_curve

    if not all_text_fits:
        curve_length_status = "curve_too_short"
    elif remaining_curve_length > average_char_width:
        curve_length_status = "curve_too_long"
    else:
        curve_length_status = "curve_correct_length"

    return curve_length_status
