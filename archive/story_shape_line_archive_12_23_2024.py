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
from archive.story_function_archive_12_23_2024 import get_component_arc_function
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

def create_shape_line(story_data):

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

        # Draw the arc
        cr.set_source_rgb(0, 0, 0)  # Black color for the arc
        cr.set_line_width(2)

        cr.move_to(arc_x_values_scaled[0], arc_y_values_scaled[0])
        for x, y in zip(arc_x_values_scaled[1:], arc_y_values_scaled[1:]):
            cr.line_to(x, y)
        cr.stroke()

        
    # Save the image to a file
    surface.write_to_png("text_along_curve_line_3.png")
    return story_data, "completed"

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

def generate_descriptors(title, component_description, story_data, desired_length):
        
    story_dict = copy.deepcopy(story_data)

    #clean up story_dict before sending to LLM
    del story_dict['x_values']
    del story_dict['y_values']
    for component in story_dict['story_components']:

        if 'arc_x_values' in component:
            del component['arc_x_values']

        if 'arc_y_values' in component:
            del component['arc_y_values']
        
    #get previous story arc_texts
    existing_arc_texts = ""
    for component in story_dict['story_components']:
        if 'arc_text' in component:
            if(existing_arc_texts == ""):
                existing_arc_texts = """Pay special attention to the `arc_text` of previous story components to maintain continuity and avoid repeating words.

**Previous `arc_text`s:**

"""
            existing_arc_texts = existing_arc_texts + " " + component['arc_text']
    

    # System message to set context for the model
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    

    # User message as the main prompt
    user_message = {
        "role": "user",
        "content": f"""
Generate a succinct, concise, and stylized description for the following segment of the story **"{title}"**: **"{component_description}"**.

Use the JSON below to understand how this segment fits into the larger narrative. {existing_arc_texts}

Your description should:

- Be exactly **35** characters long.
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

- Important words include:
  * Proper nouns (names, places)
  * Significant descriptive words
  * Action words
  * Words that carry narrative weight

- Include spaces within keywords or phrases as needed, and **include a space after the punctuation that separates keywords/phrases.**

- **Do not include any quotation marks ("") in the outputs.**

- **Punctuation and spaces are included and count towards the total character limit.**

- **Punctuation (periods, commas) MUST be counted in the total character limit.**

- **You MUST count each character, including spaces and punctuation, to ensure exact match to the specified length.**

**Example Output:**

For a story segment about a character's first day at a new job, an example 50-character description:
Nervous. First Day. Office. Challenges. Potential.
(Verification: 
"N" = 1, space = 1, "ervous" = 6, "." = 1, "First" = 5, 
space = 1, "Day" = 3, "." = 1, "Office" = 6, "." = 1, 
"Challenges" = 10, "." = 1, "Potential" = 9, "." = 1
Total: 50 characters exactly)

Here's the JSON providing more context on the entire story:
{story_dict}

"""
            }

    #print(user_message)
    # Compile messages
    chat_messages = [system_message, user_message]

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

def adjust_descriptors(desired_length, actual_length, chat_messages ):
    # System message to set context for the model
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    # User message as the main prompt
    user_message = {
        "role": "user",
        "content":f"""
The previous description does not meet the required characters count specifications. It was {actual_length} characters instead of {desired_length} characters. 
Please adjust your description accordingly to meet the exact characters count and guidelines and please output only the updated description and nothing else.
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
