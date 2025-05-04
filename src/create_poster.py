# poster_creator.py
import math
import os
from PIL import Image, ImageDraw # Requires Pillow: pip install Pillow

DEFAULT_DPI = 300

def parse_color(color_input):
    """Converts hex string or RGB tuple (0-255) to Pillow-compatible RGB tuple."""
    if isinstance(color_input, str):
        if color_input.startswith('#'):
            hex_color = color_input.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:
            raise ValueError("Invalid hex color string format. Use '#RRGGBB'.")
    elif isinstance(color_input, tuple) and len(color_input) == 3:
        # Check if values are normalized (0-1) like Cairo uses
        if all(0 <= c <= 1 for c in color_input):
             # Convert from 0-1 range to 0-255
             return tuple(int(c * 255) for c in color_input)
        elif all(0 <= c <= 255 for c in color_input):
             # Assume it's already 0-255
             return tuple(int(c) for c in color_input) # Ensure they are ints
        else:
             raise ValueError("RGB tuple values must be between 0 and 1 or 0 and 255.")
    else:
        raise TypeError("Color must be a hex string ('#RRGGBB') or an RGB tuple.")

def create_poster(
    story_shape_paths,
    poster_width_in,
    poster_height_in,
    output_path,
    dpi=DEFAULT_DPI,
    margin_in=0.75,
    spacing_in=0.5,
    background_color='#FFFFFF', # Hex or RGB tuple (0-255)
    rows=None, # Optionally force number of rows
    cols=None  # Optionally force number of columns
):
    """
    Creates a poster by arranging individual story shape images in a grid.

    Args:
        story_shape_paths (list): List of file paths to the individual story shape PNGs.
        poster_width_in (float): Desired width of the poster in inches.
        poster_height_in (float): Desired height of the poster in inches.
        output_path (str): Path to save the final poster image.
        dpi (int): Dots per inch for the output poster.
        margin_in (float): Margin around the edge of the poster in inches.
        spacing_in (float): Spacing between grid items in inches.
        background_color (str or tuple): Background color ('#RRGGBB' or (R, G, B)).
        rows (int, optional): Force a specific number of rows. Defaults to None (auto-calculate).
        cols (int, optional): Force a specific number of columns. Defaults to None (auto-calculate).
    """
    num_stories = len(story_shape_paths)
    if num_stories == 0:
        print("Error: No story shape paths provided.")
        return

    # --- Input Validation ---
    for path in story_shape_paths:
        if not os.path.isfile(path):
            print(f"Error: Input file not found: {path}")
            return
    if poster_width_in <= 0 or poster_height_in <= 0:
        print("Error: Poster dimensions must be positive.")
        return
    if dpi <= 0:
        print("Error: DPI must be positive.")
        return

    # --- Calculate Dimensions in Pixels ---
    poster_width_px = int(poster_width_in * dpi)
    poster_height_px = int(poster_height_in * dpi)
    margin_px = int(margin_in * dpi)
    spacing_px = int(spacing_in * dpi)
    bg_color_rgb = parse_color(background_color)

    # --- Determine Grid Dimensions ---
    if rows is None or cols is None:
        # Auto-calculate grid trying for a roughly square layout
        cols_auto = max(1, math.ceil(math.sqrt(num_stories)))
        rows_auto = max(1, math.ceil(num_stories / cols_auto))
        # If dimensions were specified, override auto-calc
        cols = cols or cols_auto
        rows = rows or rows_auto
    elif rows * cols < num_stories:
         print(f"Warning: Specified grid {rows}x{cols} is too small for {num_stories} stories. Adjusting...")
         # Recalculate cols based on fixed rows, or vice-versa, or error out
         cols = max(cols, math.ceil(num_stories / rows)) # Adjust cols if rows fixed
         # Or adjust rows if cols fixed: rows = max(rows, math.ceil(num_stories / cols))
         print(f"Adjusted grid to {rows}x{cols}")


    if rows * cols < num_stories:
         print(f"Error: Cannot fit {num_stories} stories in a {rows}x{cols} grid.")
         return

    # --- Calculate Cell Size ---
    grid_area_width = poster_width_px - 2 * margin_px
    grid_area_height = poster_height_px - 2 * margin_px

    if grid_area_width <= 0 or grid_area_height <= 0:
        print("Error: Margins are larger than the poster dimensions.")
        return

    # Total spacing needed horizontally and vertically
    total_h_spacing = max(0, (cols - 1) * spacing_px)
    total_v_spacing = max(0, (rows - 1) * spacing_px)

    # Size available for each cell
    cell_width = (grid_area_width - total_h_spacing) / cols
    cell_height = (grid_area_height - total_v_spacing) / rows

    if cell_width <= 0 or cell_height <= 0:
        print("Error: Calculated cell size is negative or zero. Check spacing/margins.")
        return

    print(f"Poster Size: {poster_width_px}x{poster_height_px} px ({poster_width_in}x{poster_height_in} in @ {dpi} DPI)")
    print(f"Grid Layout: {rows} rows x {cols} columns")
    print(f"Cell Size: {cell_width:.2f}x{cell_height:.2f} px")

    # --- Create Poster Canvas ---
    poster_img = Image.new('RGB', (poster_width_px, poster_height_px), bg_color_rgb)

    # --- Load, Resize, and Paste Images ---
    current_story_index = 0
    for r in range(rows):
        for c in range(cols):
            if current_story_index >= num_stories:
                break # Stop if we've placed all images

            img_path = story_shape_paths[current_story_index]
            try:
                img = Image.open(img_path)
                img_w, img_h = img.size

                # Calculate resize ratio to fit within cell, maintaining aspect ratio
                ratio = min(cell_width / img_w, cell_height / img_h)
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)

                # Resize using a high-quality filter
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Calculate top-left position for the cell
                cell_x_start = margin_px + c * (cell_width + spacing_px)
                cell_y_start = margin_px + r * (cell_height + spacing_px)

                # Calculate top-left position to center the resized image within the cell
                paste_x = int(cell_x_start + (cell_width - new_w) / 2)
                paste_y = int(cell_y_start + (cell_height - new_h) / 2)

                # Paste (handle transparency if original is RGBA)
                if img_resized.mode == 'RGBA':
                    poster_img.paste(img_resized, (paste_x, paste_y), img_resized)
                else:
                    poster_img.paste(img_resized, (paste_x, paste_y))

                print(f"Placed '{os.path.basename(img_path)}' at row {r}, col {c} ({paste_x},{paste_y}) size {new_w}x{new_h}")
                img.close() # Close the original image file

            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                # Optionally draw a placeholder box
                draw = ImageDraw.Draw(poster_img)
                cell_x_start = int(margin_px + c * (cell_width + spacing_px))
                cell_y_start = int(margin_px + r * (cell_height + spacing_px))
                draw.rectangle(
                    [cell_x_start, cell_y_start, cell_x_start + cell_width, cell_y_start + cell_height],
                    outline="red", width=2
                )
                draw.text((cell_x_start + 5, cell_y_start + 5), f"Error\n{os.path.basename(img_path)}", fill="red")


            current_story_index += 1
        if current_story_index >= num_stories:
            break

    # --- Save Poster ---
    try:
        poster_img.save(output_path)
        print(f"Poster saved successfully to {output_path}")
    except Exception as e:
        print(f"Error saving poster: {e}")
    finally:
        poster_img.close()


# --- Example Usage ---
if __name__ == "__main__":
    # 1. Generate your individual story shapes first using create.py or story_shape.py
    # Make sure the output paths are correct. Assume they are in a 'shapes_output' folder.

    # Example list of generated story shape PNG files:
    # (Replace these with the actual paths to your generated images)
    story_files = [
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-harry-potter-&-the-sorcerer's-stone_protagonist-harry-potter_product-print_size-8x10_line-type-char_char_background-color-#1A237E_font-color-#FFD700_border-color-#0D1642_font-Sans_title-display-yes.png",
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-brave-new-world_protagonist-bernard-marx_product-print_size-8x10_line-type-char_char_background-color-#E6F3FF_font-color-#1B3142_border-color-#7CA6C7_font-Orbitron_title-display-yes.png",
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-romeo-and-juliet_protagonist-romeo_product-print_size-8x10_line-type-char_char_background-color-#1B2A4A_font-color-#DAA520_border-color-#0F2557_font-Sans_title-display-yes.png"
    ]

    # Define poster parameters
    poster_output_folder = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/posters/"
    os.makedirs(poster_output_folder, exist_ok=True) # Create folder if it doesn't exist

    poster_filename = "literature_classics_poster_16x20.png"
    output_file = os.path.join(poster_output_folder, poster_filename)
    poster_w_inches = 16
    poster_h_inches = 20
    poster_margin_inches = 1.0 # Larger margin for a poster
    poster_spacing_inches = 0.75 # Space between stories

    create_poster(
        story_shape_paths=story_files,
        poster_width_in=poster_w_inches,
        poster_height_in=poster_h_inches,
        output_path=output_file,
        dpi=300,
        margin_in=poster_margin_inches,
        spacing_in=poster_spacing_inches,
        background_color='#F0F0F0' # Light grey background
        # rows=2, # You could force 2 rows
        # cols=2  # And force 2 columns
    )

    # --- Example for a different size poster ---
    poster_filename_2 = "literature_classics_poster_24x18.png"
    output_file_2 = os.path.join(poster_output_folder, poster_filename_2)
    poster_w_inches_2 = 24
    poster_h_inches_2 = 18

    create_poster(
        story_shape_paths=story_files,
        poster_width_in=poster_w_inches_2,
        poster_height_in=poster_h_inches_2,
        output_path=output_file_2,
        dpi=300,
        margin_in=1.25,
        spacing_in=1.0,
        background_color='#FFFFFF' # White background
    )