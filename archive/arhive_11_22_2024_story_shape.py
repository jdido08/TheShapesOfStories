import cairo
import gi
import numpy as np
import math
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity

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

    # Calculate scaling factors without preserving aspect ratio
    drawable_width = width - 2 * margin_x
    drawable_height = height - 2 * margin_y
    scale_x = drawable_width / x_range
    scale_y = drawable_height / y_range

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

    # Initialize variables for character placement
    char_positions = []
    total_curve_length = np.sum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled)))
    cumulative_curve_lengths = np.insert(np.cumsum(np.hypot(np.diff(x_values_scaled), np.diff(y_values_scaled))), 0, 0)

    # Start placing characters
    idx_on_curve = 0  # Index on the curve
    distance_along_curve = 0  # Distance along the curve
    rendered_boxes = []  # List to keep track of character bounding boxes

    for char in text:
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

            # Check for overlap with the previous character
            if rendered_boxes:
                if translated_box.intersects(rendered_boxes[-1]):
                    # Move further along the curve to avoid overlap
                    distance_along_curve += 1  # Increase this step as needed for performance vs. precision
                    continue

            # No overlap detected, place the character
            char_positions.append((x, y, angle, char, char_width, char_height))
            rendered_boxes.append(translated_box)

            # Move the distance along the curve forward by the width of the character
            distance_along_curve += char_width  # Adjust as necessary

            break
        else:
            # If we reach the end of the curve, stop placing characters
            break

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

