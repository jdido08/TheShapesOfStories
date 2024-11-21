import cairo
import gi
import numpy as np
import math

# Ensure the correct versions of Pango and PangoCairo are used
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

def create_shape(x_values, y_values, text):
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

    # Calculate scaling factors
    drawable_width = width - 2 * margin_x
    drawable_height = height - 2 * margin_y
    scale_x = drawable_width / x_range
    scale_y = drawable_height / y_range

    # Optionally, maintain aspect ratio
    scale = min(scale_x, scale_y)
    scale_x = scale_y = scale

    # Adjust x_values and y_values: scale and shift to include margins
    x_values_scaled = [(x - x_min) * scale_x + margin_x for x in x_values]
    y_values_scaled = [height - ((y - y_min) * scale_y + margin_y) for y in y_values]  # Invert y-axis

    # Create a Cairo surface and context with the specified width and height
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)

    # Set background color (optional)
    cr.set_source_rgb(1, 1, 1)  # White background
    cr.paint()

    # Draw the curve (optional, for visualization)
    cr.set_source_rgb(0, 0, 0)  # Black color for the curve
    cr.set_line_width(2)  # Increase line width for better visibility in high-resolution

    # Move to the starting point of the curve
    cr.move_to(x_values_scaled[0], y_values_scaled[0])

    # Draw the curve using lines
    for x, y in zip(x_values_scaled[1:], y_values_scaled[1:]):
        cr.line_to(x, y)

    cr.stroke()

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

    # Prepare Pango layout
    pangocairo_context = PangoCairo.create_context(cr)
    font_size = 72  # Adjust font size as needed
    font_desc = Pango.FontDescription(f"Sans {font_size}")

    # Measure the width and height of each character
    char_widths = []
    char_heights = []
    for char in text:
        layout = Pango.Layout.new(pangocairo_context)
        layout.set_font_description(font_desc)
        layout.set_text(char, -1)
        char_width, char_height = layout.get_pixel_size()
        char_widths.append(char_width)
        char_heights.append(char_height)

    # Calculate cumulative character positions (distances along the text)
    cumulative_char_positions = [0]  # Start at 0
    for i in range(len(char_widths) - 1):
        # Add half the current character width and half the next character width
        spacing = (char_widths[i] + char_widths[i + 1]) / 2
        cumulative_char_positions.append(cumulative_char_positions[-1] + spacing)
    # Add half-width of the last character to get its center position
    total_text_length = cumulative_char_positions[-1] + char_widths[-1] / 2

    # Total length of the curve
    segment_lengths = np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))
    cumulative_curve_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
    total_curve_length = cumulative_curve_lengths[-1]

    # Ensure that the text fits within the curve length
    if total_text_length > total_curve_length:
        print("Warning: The text is longer than the curve. Some characters may not be displayed.")
        # Optionally, adjust font size or truncate text

    # Determine positions for each character along the curve
    char_positions = []
    for idx, distance_along_text in enumerate(cumulative_char_positions):
        # Map the distance along the text to the same distance along the curve
        distance_along_curve = distance_along_text

        # Find the segment where the character should be placed
        segment_idx = np.searchsorted(cumulative_curve_lengths, distance_along_curve)

        if segment_idx >= len(x_values_scaled) - 1:
            segment_idx = len(x_values_scaled) - 2  # Ensure index is within bounds

        # Calculate the position along the segment
        segment_start_distance = cumulative_curve_lengths[segment_idx]
        segment_end_distance = cumulative_curve_lengths[segment_idx + 1]
        segment_distance = segment_end_distance - segment_start_distance

        if segment_distance == 0:
            ratio = 0
        else:
            ratio = (distance_along_curve - segment_start_distance) / segment_distance

        x = x_values_scaled[segment_idx] + ratio * (x_values_scaled[segment_idx + 1] - x_values_scaled[segment_idx])
        y = y_values_scaled[segment_idx] + ratio * (y_values_scaled[segment_idx + 1] - y_values_scaled[segment_idx])
        angle = get_tangent_angle(x_values_scaled, y_values_scaled, segment_idx)

        char_positions.append((x, y, angle, text[idx], char_widths[idx], char_heights[idx]))

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

    # Save the image to a file
    surface.write_to_png("text_along_curve.png")

