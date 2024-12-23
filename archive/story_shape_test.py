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
import itertools
from openai import OpenAI
from archive.story_function_archive_12_23_2024 import get_component_arc_function

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
    margin_in_inches = 0.5  # Reduced margins
    margin_x = int(margin_in_inches * dpi)
    margin_y = int(margin_in_inches * dpi)

    # Determine data range
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_range = x_max - x_min if x_max != x_min else 1
    y_range = y_max - y_min if y_max != y_min else 1

    # Calculate scaling factors
    drawable_width = width - 2 * margin_x
    drawable_height = height - 2 * margin_y
    scale_x = drawable_width / x_range
    scale_y = drawable_height / y_range

    # Adjust x_values and y_values: scale and shift to include margins
    x_values_scaled = [margin_x + (x - x_min) * scale_x for x in x_values]
    y_values_scaled = [margin_y + (y_max - y) * scale_y for y in y_values]

    # Create a mapping from original to scaled coordinates
    coordinate_mapping = dict(zip(zip(x_values, y_values), zip(x_values_scaled, y_values_scaled)))

    # Create a Cairo surface and context with the specified width and height
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)

    # Set background color
    cr.set_source_rgb(1, 1, 1)  # White background
    cr.paint()

    # Draw the drawable area boundary for debugging
    cr.set_source_rgb(0, 0, 1)  # Blue color
    cr.set_line_width(5)
    cr.rectangle(margin_x, margin_y, drawable_width, drawable_height)
    cr.stroke()

    # Initialize offset before the loop
    offset = 0

    # Prepare Pango layout
    pangocairo_context = PangoCairo.create_context(cr)
    font_size = 144  # Increased font size
    font_desc = Pango.FontDescription(f"Sans {font_size}")

    # For overlap detection between arcs
    all_rendered_boxes = []

    # Precompute scaled arc coordinates for all components
    for component in story_data['story_components']:
        arc_x_values = component.get('arc_x_values', [])
        arc_y_values = component.get('arc_y_values', [])
        description = component.get('description', '')

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
                y_scaled = margin_y + (y_max - y) * scale_y
            arc_x_values_scaled.append(x_scaled)
            arc_y_values_scaled.append(y_scaled)

        # Store the scaled values in the component
        component['arc_x_values_scaled'] = arc_x_values_scaled
        component['arc_y_values_scaled'] = arc_y_values_scaled

    # Process each story component
    for idx, component in enumerate(story_data['story_components']):
        arc_x_values_scaled = component['arc_x_values_scaled']
        arc_y_values_scaled = component['arc_y_values_scaled']
        description = component.get('description', '')

        # Skip if arc data is missing
        if not arc_x_values_scaled or not arc_y_values_scaled:
            continue

        # Step 1: Calculate arc length
        arc_length = calculate_arc_length(arc_x_values_scaled, arc_y_values_scaled)

        # Step 2: Estimate characters that fit
        average_char_width = get_average_char_width(pangocairo_context, font_desc)
        num_characters = estimate_characters_fit(arc_length, average_char_width)

        # Step 3: Generate descriptors with desired length range
        desired_length = num_characters + offset
        min_length = max(0, desired_length - 5)  # Ensure min_length is non-negative
        max_length = desired_length + 5

        descriptors_text = get_descriptors_from_llm(
            overall_context=story_data.get('overall_context', ''),
            specific_section=description,
            min_length=min_length,
            max_length=max_length
        )

        # Step 4: Calculate the actual number of characters in LLM output
        actual_length = len(descriptors_text)

        # Step 5: Update offset
        #offset = actual_length - desired_length

        # Step 6: Adjust arc to match text length
        text_length_in_pixels = calculate_text_length_in_pixels(descriptors_text, pangocairo_context, font_desc)
        adjusted_arc_x_values_scaled, adjusted_arc_y_values_scaled = adjust_arc_to_text_length(
            arc_x_values_scaled, arc_y_values_scaled, text_length_in_pixels
        )

        # Update the arc's coordinates in the story component
        component['arc_x_values_scaled'] = adjusted_arc_x_values_scaled
        component['arc_y_values_scaled'] = adjusted_arc_y_values_scaled

        # Step 7: Update subsequent arcs
        adjusted_end_point = (adjusted_arc_x_values_scaled[-1], adjusted_arc_y_values_scaled[-1])
        # After adjusting the arc and obtaining the adjusted end point
        update_subsequent_arcs(
            story_data['story_components'],
            idx,
            adjusted_end_point,
            scale_x,
            scale_y,
            margin_x,
            margin_y,
            x_min,
            y_max
        )


        # Draw the adjusted arc
        cr.set_source_rgb(0, 0, 0)  # Black color for the arc
        cr.set_line_width(2)

        cr.move_to(adjusted_arc_x_values_scaled[0], adjusted_arc_y_values_scaled[0])
        for x, y in zip(adjusted_arc_x_values_scaled[1:], adjusted_arc_y_values_scaled[1:]):
            cr.line_to(x, y)
        cr.stroke()

        # Render the text along the adjusted arc
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

def get_descriptors_from_llm(overall_context, specific_section, min_length, max_length):
    system_message = {
        "role": "system",
        "content": "You are an expert storyteller. Your task is to provide a list of concise keywords or phrases that represent and describe story segments effectively."
    }

    user_message = {
        "role": "user",
        "content": f"""
Given the context of the novel and the specific section, provide concise keywords or phrases that describe the story segment. The total length should be between {min_length} and {max_length} characters.

**Overall Context:**
{overall_context}

**Specific Section:**
{specific_section}

**Descriptors:**
"""
    }

    # Compile messages
    chat_messages = [system_message, user_message]

    # Create completion request
    completion = client.chat.completions.create(
        model="gpt-4-0613",  # Update as needed
        messages=chat_messages,
        max_tokens=int(max_length / 4),  # Approximate token count
        temperature=0.7
    )

    # Parse and extract the response content
    response_text = completion.choices[0].message.content.strip()

    # Ensure the generated text meets the length requirements
    if len(response_text) < min_length:
        # Optionally, you can make another request or handle this case as needed
        pass

    print(response_text)
    return response_text

def calculate_text_length_in_pixels(text, pangocairo_context, font_desc):
    # Create a layout for the text
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)
    layout.set_text(text, -1)
    text_width, _ = layout.get_pixel_size()
    return text_width

def adjust_arc_to_text_length(arc_x_values, arc_y_values, required_arc_length, arc_function=None, x1=None, x2=None, num_points=100):
    current_arc_length = calculate_arc_length(arc_x_values, arc_y_values)

    if current_arc_length == 0:
        return arc_x_values, arc_y_values

    # Calculate cumulative lengths
    segment_lengths = np.hypot(np.diff(arc_x_values), np.diff(arc_y_values))
    cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)

    if required_arc_length < current_arc_length:
        # Truncate the arc
        idx = np.searchsorted(cumulative_lengths, required_arc_length)
        if idx == 0:
            # Required length is less than the first segment
            adjusted_arc_x_values = [arc_x_values[0]]
            adjusted_arc_y_values = [arc_y_values[0]]
        else:
            # Interpolate to find the exact point where to cut off
            overshoot = cumulative_lengths[idx] - required_arc_length
            segment_length = segment_lengths[idx - 1]
            ratio = (segment_length - overshoot) / segment_length
            new_x = arc_x_values[idx - 1] + ratio * (arc_x_values[idx] - arc_x_values[idx - 1])
            new_y = arc_y_values[idx - 1] + ratio * (arc_y_values[idx] - arc_y_values[idx - 1])

            adjusted_arc_x_values = arc_x_values[:idx]
            adjusted_arc_y_values = arc_y_values[:idx]
            adjusted_arc_x_values = adjusted_arc_x_values
            adjusted_arc_y_values = adjusted_arc_y_values
            adjusted_arc_x_values.append(new_x)
            adjusted_arc_y_values.append(new_y)
    else:
        # Extrapolate the arc
        if arc_function is None or x1 is None or x2 is None:
            # Cannot extrapolate without the arc function and x-range
            return arc_x_values, arc_y_values

        # Calculate how much more length we need
        extra_length_needed = required_arc_length - current_arc_length

        # Start from the last point
        x_prev = arc_x_values[-1]
        y_prev = arc_y_values[-1]
        cumulative_length = current_arc_length

        adjusted_arc_x_values = list(arc_x_values)
        adjusted_arc_y_values = list(arc_y_values)

        # Estimate x increment
        x_increment = (x2 - x1) / num_points
        if x_increment == 0:
            x_increment = (arc_x_values[-1] - arc_x_values[0]) / num_points

        # Continue extending x-values
        while cumulative_length < required_arc_length:
            x_new = x_prev + x_increment
            y_new = arc_function(x_new)

            dx = x_new - x_prev
            dy = y_new - y_prev
            segment_length = np.hypot(dx, dy)
            cumulative_length += segment_length

            adjusted_arc_x_values.append(x_new)
            adjusted_arc_y_values.append(y_new)

            x_prev = x_new
            y_prev = y_new

            # Safety check to prevent infinite loops
            if len(adjusted_arc_x_values) > 1000:
                break

        # If we overshoot, truncate back to required length
        segment_lengths = np.hypot(np.diff(adjusted_arc_x_values), np.diff(adjusted_arc_y_values))
        cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
        idx = np.searchsorted(cumulative_lengths, required_arc_length)
        if idx == 0:
            adjusted_arc_x_values = [adjusted_arc_x_values[0]]
            adjusted_arc_y_values = [adjusted_arc_y_values[0]]
        else:
            overshoot = cumulative_lengths[idx] - required_arc_length
            segment_length = segment_lengths[idx - 1]
            ratio = (segment_length - overshoot) / segment_length
            new_x = adjusted_arc_x_values[idx - 1] + ratio * (adjusted_arc_x_values[idx] - adjusted_arc_x_values[idx - 1])
            new_y = adjusted_arc_y_values[idx - 1] + ratio * (adjusted_arc_y_values[idx] - adjusted_arc_y_values[idx - 1])

            adjusted_arc_x_values = adjusted_arc_x_values[:idx]
            adjusted_arc_y_values = adjusted_arc_y_values[:idx]
            adjusted_arc_x_values.append(new_x)
            adjusted_arc_y_values.append(new_y)

    return adjusted_arc_x_values, adjusted_arc_y_values


def update_subsequent_arcs(story_components, current_index, adjusted_end_point, scale_x, scale_y, margin_x, margin_y, x_min, y_max):
    if current_index + 1 < len(story_components):
        next_component = story_components[current_index + 1]

        # Skip if next component has no arc data
        if not next_component.get('arc_x_values') or not next_component.get('arc_y_values'):
            return

        # Convert adjusted_end_point back to unscaled values
        adjusted_x_unscaled = (adjusted_end_point[0] - margin_x) / scale_x + x_min
        adjusted_y_unscaled = y_max - (adjusted_end_point[1] - margin_y) / scale_y

        # Update the start time and emotional score of the next component
        x1 = adjusted_x_unscaled
        print(next_component['end_time'])
        x2 = next_component['end_time']  # Original end time remains the same
        y1 = adjusted_y_unscaled
        y2 = next_component['end_emotional_score']  # Original end emotional score remains the same
        arc_type = next_component['arc']

        # Recalculate the arc function with updated start point and original end point
        arc_function = get_component_arc_function(x1, x2, y1, y2, arc_type)

        # Generate new x and y values for the next component
        num_points = len(next_component['arc_x_values'])  # Use the same number of points
        x_values = np.linspace(x1, x2, num_points)
        y_values = np.array([arc_function(x) for x in x_values])

        # Update unscaled x and y values
        next_component['arc_x_values'] = x_values.tolist()
        next_component['arc_y_values'] = y_values.tolist()

        # Scale and shift x and y values
        x_values_scaled = [margin_x + (x - x_min) * scale_x for x in x_values]
        y_values_scaled = [margin_y + (y_max - y) * scale_y for y in y_values]

        # Update the component's scaled x and y values
        next_component['arc_x_values_scaled'] = x_values_scaled
        next_component['arc_y_values_scaled'] = y_values_scaled

        # Get the new adjusted end point for this component
        new_adjusted_end_point = (x_values_scaled[-1], y_values_scaled[-1])

        # Recursively update subsequent arcs
        update_subsequent_arcs(
            story_components,
            current_index + 1,
            new_adjusted_end_point,
            scale_x,
            scale_y,
            margin_x,
            margin_y,
            x_min,
            y_max
        )


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

    acceptable_overlap_ratio = 0.1  # Allow up to 10% overlap
    max_adjustments = 5  # Maximum times to adjust character position

    for i, char in enumerate(text):
        char_width = char_widths[i]
        char_height = char_heights[i]
        distance_along_curve = char_positions_along_curve[i]
        adjustment_count = 0

        while True:
            # Get position along the curve
            x, y, angle = get_position_along_curve(distance_along_curve, x_values_scaled, y_values_scaled, cumulative_lengths)

            # Create the bounding box with shrink factor
            bbox_shrink_factor = 0.8
            box = Polygon([
                (-char_width / 2 * bbox_shrink_factor, -char_height / 2 * bbox_shrink_factor),
                (char_width / 2 * bbox_shrink_factor, -char_height / 2 * bbox_shrink_factor),
                (char_width / 2 * bbox_shrink_factor, char_height / 2 * bbox_shrink_factor),
                (-char_width / 2 * bbox_shrink_factor, char_height / 2 * bbox_shrink_factor)
            ])

            # Rotate and translate the box
            rotated_box = shapely_rotate(box, angle * (180 / math.pi), origin=(0, 0), use_radians=False)
            translated_box = shapely.affinity.translate(rotated_box, xoff=x, yoff=y)

            # Check for overlap
            overlap = False
            for other_box in all_rendered_boxes:
                intersection_area = translated_box.intersection(other_box).area
                if intersection_area > acceptable_overlap_ratio * translated_box.area:
                    overlap = True
                    break

            if not overlap or adjustment_count >= max_adjustments:
                # Place the character
                char_positions.append((x, y, angle, char, char_width, char_height))
                all_rendered_boxes.append(translated_box)
                break
            else:
                # Adjust position
                distance_along_curve += char_width * 0.1  # Move ahead slightly
                adjustment_count += 1
                if distance_along_curve > total_curve_length:
                    break  # No more space on the curve

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
