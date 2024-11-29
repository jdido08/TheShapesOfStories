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

def get_position_along_curve(distance, x_values_scaled, y_values_scaled, cumulative_lengths):
    total_length = cumulative_lengths[-1]
    if distance <= 0:
        return x_values_scaled[0], y_values_scaled[0], get_tangent_angle(x_values_scaled, y_values_scaled, 0)
    elif distance >= total_length:
        return x_values_scaled[-1], y_values_scaled[-1], get_tangent_angle(x_values_scaled, y_values_scaled, -1)
    else:
        idx = np.searchsorted(cumulative_lengths, distance) - 1
        segment_length = cumulative_lengths[idx + 1] - cumulative_lengths[idx]
        if segment_length == 0:
            ratio = 0
        else:
            ratio = (distance - cumulative_lengths[idx]) / segment_length
        x = x_values_scaled[idx] + ratio * (x_values_scaled[idx + 1] - x_values_scaled[idx])
        y = y_values_scaled[idx] + ratio * (y_values_scaled[idx + 1] - y_values_scaled[idx])
        angle = get_tangent_angle(x_values_scaled, y_values_scaled, idx)
        return x, y, angle


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
    # Extract the overall x_values and y_values
    x_values = story_data['x_values']
    y_values = story_data['y_values']

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

    # Prepare Pango layout
    pangocairo_context = PangoCairo.create_context(cr)
    font_size = 72  # Adjust font size as needed
    font_desc = Pango.FontDescription(f"Sans {font_size}")

    # For overlap detection between arcs
    all_rendered_boxes = []

    # Precompute scaled arc coordinates for all components
    for component in story_data['story_components'][1:]:
        arc_x_values = component.get('arc_x_values', [])
        arc_y_values = component.get('arc_y_values', [])

        # Skip if arc data is missing
        if not arc_x_values or not arc_y_values:
            component['arc_x_values_scaled'] = []
            component['arc_y_values_scaled'] = []
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

        # Store the scaled values in the component
        component['arc_x_values_scaled'] = arc_x_values_scaled
        component['arc_y_values_scaled'] = arc_y_values_scaled


    # Process each story component
    for idx, component in enumerate(story_data['story_components'][1:]):
        arc_x_values = component.get('arc_x_values', [])
        arc_y_values = component.get('arc_y_values', [])
        description = component.get('description', '')
        descriptors = component.get('descriptors', [])

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

        # Step 1: Calculate arc length
        arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled)

        # Step 2: Estimate characters that fit
        average_char_width = get_average_char_width(pangocairo_context, font_desc)
        num_characters = estimate_characters_fit(arc_length, average_char_width)

        # Step 3: Generate descriptors
        descriptors_text = generate_descriptors(
            overall_context=story_data.get('overall_context', ''),
            specific_section=description,
            existing_descriptors=descriptors,
            desired_length=int(num_characters * 1.1)  # Slightly overestimate
        )

        # Calculate actual text length in pixels
        text_length_in_pixels = calculate_text_length_in_pixels(descriptors_text, pangocairo_context, font_desc)

        # Step 4: Adjust arc to match text length
        adjusted_arc_x_values_scaled, adjusted_arc_y_values_scaled = adjust_arc_to_text_length(
            arc_x_values_scaled, arc_y_values_scaled, text_length_in_pixels
        )

        # Update the arc's coordinates in the story component
        component['arc_x_values_scaled'] = adjusted_arc_x_values_scaled
        component['arc_y_values_scaled'] = adjusted_arc_y_values_scaled

        # Step 5: Update subsequent arcs
        adjusted_end_point = (adjusted_arc_x_values_scaled[-1], adjusted_arc_y_values_scaled[-1])
        update_subsequent_arcs(story_data['story_components'], idx, adjusted_end_point)

        # Step 6: Draw the adjusted arc
        cr.set_source_rgb(0, 0, 0)  # Black color for the arc
        cr.set_line_width(2)

        cr.move_to(adjusted_arc_x_values_scaled[0], adjusted_arc_y_values_scaled[0])
        for x, y in zip(adjusted_arc_x_values_scaled[1:], adjusted_arc_y_values_scaled[1:]):
            cr.line_to(x, y)
        cr.stroke()

        # Step 7: Render the text along the adjusted arc
        draw_text_on_curve(
            cr, adjusted_arc_x_values_scaled, adjusted_arc_y_values_scaled, descriptors_text,
            pangocairo_context, font_desc, all_rendered_boxes
        )

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
    sample_text = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    layout.set_text(sample_text, -1)
    total_width = layout.get_pixel_size()[0]
    average_char_width = total_width / len(sample_text)
    return average_char_width

def estimate_characters_fit(arc_length, average_char_width, spacing=1.0):
    # Estimate the number of characters that can fit along the arc
    return int(arc_length / (average_char_width * spacing))

def generate_descriptors(overall_context, specific_section, existing_descriptors, desired_length):
    descriptors = existing_descriptors.copy()
    descriptors_text = ' '.join(descriptors)

    # If descriptors are empty or insufficient, use LLM to generate more
    while len(descriptors_text) < desired_length:
        # Call LLM to generate additional descriptors
        required_length = desired_length - len(descriptors_text)
        new_descriptors = get_additional_descriptors(overall_context, specific_section, required_length)
        descriptors.extend(new_descriptors)
        descriptors = list(dict.fromkeys(descriptors))  # Remove duplicates
        descriptors_text = ' '.join(descriptors)

    # Trim or pad descriptors_text to match desired_length
    if len(descriptors_text) > desired_length:
        descriptors_text = descriptors_text[:desired_length].rstrip()
        if not descriptors_text.endswith((' ', '.', '!', '?')):
            descriptors_text = descriptors_text.rsplit(' ', 1)[0]
        descriptors_text += '.'

    return descriptors_text

def get_additional_descriptors(overall_context, specific_section, required_length):
    # System message to set context for the model
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide additional concise keywords or phrases to describe a story segment effectively."
    }

    # User message as the main prompt
    user_message = {
        "role": "user",
        "content": f"""
Given the context of the novel and the specific section, provide additional concise keywords or phrases to describe the story segment. Focus on generating descriptors that will help fill approximately {required_length} more characters.

**Overall Context:**
{overall_context}

**Specific Section:**
{specific_section}

**Additional Descriptors:**
"""
    }

    # Compile messages
    chat_messages = [system_message, user_message]

    # Calculate max_tokens with a minimum fallback
    max_tokens = max(1, required_length // 4)  # Ensure it's at least 1

    # Create completion request
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Update as needed
        messages=chat_messages,
        max_tokens=max_tokens,  # Estimate tokens from character length
        temperature=0.7
    )

    # Parse and extract the response content
    response_text = completion.choices[0].message.content.strip()

    # Split the generated text into descriptors
    new_descriptors = [phrase.strip() for phrase in response_text.split('\n') if phrase.strip()]

    # Ensure descriptors end with punctuation
    new_descriptors = [desc if desc[-1] in '.!?' else desc + '.' for desc in new_descriptors]

    return new_descriptors


def calculate_text_length_in_pixels(text, pangocairo_context, font_desc):
    # Create a layout for the text
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)
    layout.set_text(text, -1)
    text_width, _ = layout.get_pixel_size()
    return text_width

def adjust_arc_to_text_length(arc_x_values, arc_y_values, required_arc_length):
    # Calculate the current arc length
    current_arc_length = calculate_arc_length(arc_x_values, arc_y_values)

    if current_arc_length == 0:
        return arc_x_values, arc_y_values  # Avoid division by zero

    # Calculate scaling factor
    scaling_factor = required_arc_length / current_arc_length

    # Adjust the arc's x and y values
    adjusted_arc_x_values = [arc_x_values[0]]
    adjusted_arc_y_values = [arc_y_values[0]]

    for i in range(1, len(arc_x_values)):
        delta_x = (arc_x_values[i] - arc_x_values[i - 1]) * scaling_factor
        delta_y = (arc_y_values[i] - arc_y_values[i - 1]) * scaling_factor
        adjusted_arc_x_values.append(adjusted_arc_x_values[-1] + delta_x)
        adjusted_arc_y_values.append(adjusted_arc_y_values[-1] + delta_y)

    return adjusted_arc_x_values, adjusted_arc_y_values

def update_subsequent_arcs(story_components, current_index, adjusted_end_point):
    if current_index + 1 < len(story_components):
        next_component = story_components[current_index + 1]
        original_start_point = (next_component['arc_x_values_scaled'][0], next_component['arc_y_values_scaled'][0])
        delta_x = adjusted_end_point[0] - original_start_point[0]
        delta_y = adjusted_end_point[1] - original_start_point[1]

        # Shift all subsequent arcs
        for idx in range(current_index + 1, len(story_components)):
            component = story_components[idx]
            component['arc_x_values_scaled'] = [x + delta_x for x in component['arc_x_values_scaled']]
            component['arc_y_values_scaled'] = [y + delta_y for y in component['arc_y_values_scaled']]

def draw_text_on_curve(cr, x_values_scaled, y_values_scaled, text, pangocairo_context, font_desc, all_rendered_boxes):
    # Initialize variables for character placement
    char_positions = []
    segment_lengths = np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))
    cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
    total_curve_length = cumulative_lengths[-1]

    # Measure dimensions for all characters
    char_widths = []
    char_heights = []
    for char in text:
        layout = Pango.Layout.new(pangocairo_context)
        layout.set_font_description(font_desc)
        layout.set_text(char, -1)
        char_width, char_height = layout.get_pixel_size()
        char_widths.append(char_width)
        char_heights.append(char_height)

    # Convert lists to NumPy arrays for element-wise operations
    char_widths = np.array(char_widths)
    char_heights = np.array(char_heights)

    total_text_width = np.sum(char_widths)
    if total_text_width == 0:
        return  # Avoid division by zero

    # Calculate scaling factor to map text width to curve length
    scaling_factor = total_curve_length / total_text_width

    # Map character positions along the curve
    char_cumulative_widths = np.insert(np.cumsum(char_widths), 0, 0)
    char_positions_along_curve = (char_cumulative_widths[:-1] + char_widths / 2) * scaling_factor

    for i, char in enumerate(text):
        char_width = char_widths[i]
        char_height = char_heights[i]
        distance_along_curve = char_positions_along_curve[i]

        # Get position along the curve
        x, y, angle = get_position_along_curve(distance_along_curve, x_values_scaled, y_values_scaled, cumulative_lengths)

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

        # Check for overlap with other boxes
        overlap = False
        for other_box in all_rendered_boxes:
            if translated_box.intersects(other_box):
                overlap = True
                break
        if overlap:
            # Skip this character or adjust position
            continue

        # No overlap detected, place the character
        char_positions.append((x, y, angle, char, char_width, char_height))
        all_rendered_boxes.append(translated_box)

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
