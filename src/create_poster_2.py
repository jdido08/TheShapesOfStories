# poster_creator.py
import math
import os
from PIL import Image, ImageDraw, ImageFont # Added ImageFont
import platform

DEFAULT_DPI = 300
# poster_creator.py
import math
import os
from PIL import Image, ImageDraw, ImageFont
import platform

DEFAULT_DPI = 300

# (get_default_font and parse_color functions remain the same)
def get_default_font():
    """Attempt to find a default system font."""
    system = platform.system()
    if system == "Windows":
        font_paths = [
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "Arial.ttf"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "TIMES.TTF"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "Verdana.ttf"),
        ]
    elif system == "Darwin": # macOS
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Times New Roman.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        ]
    else: # Linux/other
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            # print(f"Using default font: {font_path}") # Optional: less verbose
            return font_path

    print("Warning: Could not find a default system font. Please specify a font_path.")
    try:
        ImageFont.load_default()
        print("Using Pillow's limited default font.")
        return None
    except IOError:
        print("Error: Pillow's default font also failed to load.")
        return "FONT_ERROR"

def parse_color(color_input):
    """Converts hex string or RGB tuple (0-255) to Pillow-compatible RGB tuple."""
    if isinstance(color_input, str):
        if color_input.startswith('#'):
            hex_color = color_input.lstrip('#')
            if len(hex_color) == 3:
                hex_color = "".join([c * 2 for c in hex_color])
            if len(hex_color) != 6:
                 raise ValueError("Invalid hex color string format. Use '#RRGGBB' or '#RGB'.")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:
            raise ValueError("Invalid hex color string format. Use '#RRGGBB'.")
    elif isinstance(color_input, tuple) and len(color_input) == 3:
        if all(0 <= c <= 1 for c in color_input):
             return tuple(int(c * 255) for c in color_input)
        elif all(0 <= c <= 255 for c in color_input):
             return tuple(int(c) for c in color_input)
        else:
             raise ValueError("RGB tuple values must be between 0 and 1 or 0 and 255.")
    else:
        raise TypeError("Color must be a hex string ('#RRGGBB') or an RGB tuple.")


def create_poster(
    story_shape_paths,
    poster_width_in,
    poster_height_in,
    output_path,
    # --- Grid Definition ---
    base_rows, # Number of rows in the underlying conceptual grid
    base_cols, # Number of columns in the underlying conceptual grid
    grid_template, # List of dicts defining visible cells and content mapping
    # --- Standard Options ---
    dpi=DEFAULT_DPI,
    margin_in=0.75,
    spacing_in=0.5, # Spacing BETWEEN visible cells
    background_color='#FFFFFF',
    # --- Poster Title Options ---
    poster_title="",
    poster_title_font_path=None,
    poster_title_font_size_pt=36,
    poster_title_font_color='#000000',
    poster_title_v_align='center',
    poster_title_padding_in=0.1
):
    """
    Creates a poster using a variable grid layout defined by a template.

    Args:
        story_shape_paths (list): List of file paths to the individual story shape PNGs.
        poster_width_in (float): Desired width of the poster in inches.
        poster_height_in (float): Desired height of the poster in inches.
        output_path (str): Path to save the final poster image.
        base_rows (int): Number of rows in the conceptual base grid.
        base_cols (int): Number of columns in the conceptual base grid.
        grid_template (list): List of dictionaries defining the layout. Each dict should have:
            'base_row' (int): Starting row index (0-based) in the base grid.
            'base_col' (int): Starting column index (0-based) in the base grid.
            'row_span' (int): Number of base rows the cell occupies (>=1).
            'col_span' (int): Number of base columns the cell occupies (>=1).
            'content_index' (int): Index (0-based) of the image from story_shape_paths
                                    to place in this cell.
        dpi (int): Dots per inch for the output poster.
        margin_in (float): Margin around the edge of the poster in inches.
        spacing_in (float): Spacing between visible grid cells in inches.
        background_color (str or tuple): Background color ('#RRGGBB' or (R, G, B)).
        poster_title (str): Text for the main poster title. If empty, no title is drawn.
        # ... (other poster title args remain the same) ...
        poster_title_font_path (str, optional): Path to font file.
        poster_title_font_size_pt (int): Font size in points.
        poster_title_font_color (str or tuple): Color for title text.
        poster_title_v_align (str): Vertical alignment ('top', 'center', 'bottom').
        poster_title_padding_in (float): Padding around title.
    """
    num_stories_provided = len(story_shape_paths)
    num_cells_defined = len(grid_template)
    if num_cells_defined == 0:
        print("Error: grid_template is empty.")
        return
    print(f"Grid template defines {num_cells_defined} cells.")

    # --- Input Validation & Setup ---
    if poster_width_in <= 0 or poster_height_in <= 0: print("Error: Poster dimensions must be positive."); return
    if dpi <= 0: print("Error: DPI must be positive."); return
    if base_rows <= 0 or base_cols <= 0: print("Error: Base rows/cols must be positive."); return
    if not poster_title_v_align in ['top', 'center', 'bottom']: print("Error: poster_title_v_align must be 'top', 'center', or 'bottom'."); return

    # Validate grid_template structure and indices
    max_content_index = -1
    for i, cell in enumerate(grid_template):
        if not all(k in cell for k in ['base_row', 'base_col', 'row_span', 'col_span', 'content_index']):
            print(f"Error: grid_template item {i} is missing required keys."); return
        if not all(isinstance(cell[k], int) for k in cell):
             print(f"Error: grid_template item {i} values must be integers."); return
        if cell['row_span'] < 1 or cell['col_span'] < 1:
             print(f"Error: grid_template item {i} row/col spans must be at least 1."); return
        if cell['base_row'] < 0 or cell['base_col'] < 0 or \
           cell['base_row'] + cell['row_span'] > base_rows or \
           cell['base_col'] + cell['col_span'] > base_cols:
             print(f"Error: grid_template item {i} goes outside the base {base_rows}x{base_cols} grid bounds."); return
        if cell['content_index'] < 0:
             print(f"Error: grid_template item {i} has invalid content_index {cell['content_index']}."); return
        max_content_index = max(max_content_index, cell['content_index'])

    if max_content_index >= num_stories_provided:
        print(f"Error: grid_template requires content_index {max_content_index}, but only {num_stories_provided} story paths were provided."); return
    if num_cells_defined > num_stories_provided:
         print(f"Warning: grid_template defines {num_cells_defined} cells, but only {num_stories_provided} story paths provided. Some cells will be empty/skipped.")


    # --- Calculate Dimensions in Pixels ---
    poster_width_px = int(poster_width_in * dpi)
    poster_height_px = int(poster_height_in * dpi)
    margin_px = int(margin_in * dpi)
    spacing_px = int(spacing_in * dpi)
    title_padding_px = int(poster_title_padding_in * dpi)
    bg_color_rgb = parse_color(background_color)

    # --- Load Poster Title Font (same logic as before) ---
    poster_title_font = None
    if poster_title:
        # (Font loading logic remains the same - omitted for brevity)
        title_font_color_rgb = parse_color(poster_title_font_color)
        title_font_path = poster_title_font_path or get_default_font()
        if title_font_path == "FONT_ERROR": poster_title = ""
        else:
            title_font_size_px = int(poster_title_font_size_pt * dpi / 72); title_font_size_px=max(1, title_font_size_px)
            try: poster_title_font = ImageFont.truetype(title_font_path, title_font_size_px) if title_font_path else ImageFont.load_default()
            except Exception as e: print(f"Error loading title font: {e}"); poster_title = ""

    # --- Create Poster Canvas ---
    poster_img = Image.new('RGB', (poster_width_px, poster_height_px), bg_color_rgb)
    draw = ImageDraw.Draw(poster_img)

    # --- Draw Poster Title (same logic as before) ---
    if poster_title and poster_title_font:
        # (Title drawing logic remains the same - omitted for brevity)
         try:
            title_bbox = draw.textbbox((0, 0), poster_title, font=poster_title_font)
            title_width = title_bbox[2] - title_bbox[0]; title_height = title_bbox[3] - title_bbox[1]
            title_x = (poster_width_px - title_width) / 2
            if poster_title_v_align == 'top': title_y = title_padding_px
            elif poster_title_v_align == 'bottom': title_y = margin_px - title_height - title_padding_px
            else: title_y = (margin_px - title_height) / 2
            title_y = max(title_padding_px, title_y)
            draw.text((title_x, title_y), poster_title, fill=title_font_color_rgb, font=poster_title_font)
            # print(f"Drew poster title '{poster_title}' at ({title_x:.0f}, {title_y:.0f})")
         except Exception as e: print(f"Error drawing poster title: {e}")


    # --- Calculate Base Cell Content Size (accounting for spacing) ---
    grid_area_width = poster_width_px - 2 * margin_px
    grid_area_height = poster_height_px - 2 * margin_px

    if grid_area_width <= 0 or grid_area_height <= 0: print("Error: Margins are larger than the poster dimensions."); return

    total_h_spacing = max(0, (base_cols - 1) * spacing_px)
    total_v_spacing = max(0, (base_rows - 1) * spacing_px)

    effective_grid_width = grid_area_width - total_h_spacing
    effective_grid_height = grid_area_height - total_v_spacing

    base_content_width = effective_grid_width / base_cols
    base_content_height = effective_grid_height / base_rows

    if base_content_width <= 0 or base_content_height <= 0: print("Error: Calculated base cell content size is negative or zero. Check spacing/margins/base grid size."); return

    print(f"Base grid unit content size: {base_content_width:.2f}x{base_content_height:.2f} px")

    # --- Process Grid Template: Load, Resize, Paste Images ---
    for cell_template in grid_template:
        content_idx = cell_template['content_index']
        if content_idx >= num_stories_provided:
            print(f"Skipping cell for content_index {content_idx} as only {num_stories_provided} paths were given.")
            continue # Skip if template asks for content we don't have

        img_path = story_shape_paths[content_idx]
        br = cell_template['base_row']
        bc = cell_template['base_col']
        rs = cell_template['row_span']
        cs = cell_template['col_span']

        # --- Calculate this cell's geometry ---
        # Content area size
        target_content_width = cs * base_content_width
        target_content_height = rs * base_content_height
        # Top-left position (including spacing offsets)
        cell_x_start = margin_px + bc * (base_content_width + spacing_px)
        cell_y_start = margin_px + br * (base_content_height + spacing_px)

        if not img_path or not os.path.isfile(img_path):
            print(f"Error: Input file not found for content_index {content_idx}: {img_path}")
            # Draw placeholder
            draw.rectangle([cell_x_start, cell_y_start, cell_x_start + target_content_width, cell_y_start + target_content_height], outline="red", width=2)
            draw.text((cell_x_start + 5, cell_y_start + 5), f"Missing\nIndex {content_idx}", fill="red", font=ImageFont.load_default())
            continue

        try:
            img = Image.open(img_path)
            img_w_orig, img_h_orig = img.size

            # Resize image to fit the calculated content area
            ratio = min(target_content_width / img_w_orig, target_content_height / img_h_orig)
            new_w = max(1, int(img_w_orig * ratio))
            new_h = max(1, int(img_h_orig * ratio))

            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Calculate paste position (centered within the cell's content area)
            paste_x = int(cell_x_start + (target_content_width - new_w) / 2)
            paste_y = int(cell_y_start + (target_content_height - new_h) / 2)

            # Paste image
            if img_resized.mode == 'RGBA':
                poster_img.paste(img_resized, (paste_x, paste_y), img_resized)
            else:
                poster_img.paste(img_resized, (paste_x, paste_y))

            img.close()
            print(f"Placed '{os.path.basename(img_path)}' (Index {content_idx}) in cell spanning [{br}:{br+rs-1},{bc}:{bc+cs-1}] at ({paste_x},{paste_y}) size {new_w}x{new_h}")

        except Exception as e:
            print(f"Error processing image {img_path} (Index {content_idx}): {e}")
            # Draw placeholder
            draw.rectangle([cell_x_start, cell_y_start, cell_x_start + target_content_width, cell_y_start + target_content_height], outline="orange", width=2)
            draw.text((cell_x_start + 5, cell_y_start + 5), f"Error\nIndex {content_idx}", fill="orange", font=ImageFont.load_default())


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
    # 1. List of paths to your generated story shape PNGs
    story_files = [
        # Index 0
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-harry-potter-and-the-sorcerers-stone_protagonist-harry-potter_product-print_size-8x10_line-type-char_char_background-color-#0B1A4F_font-color-#FFD700_border-color-#051030_font-Cinzel Decorative_title-display-yes.png",
        # Index 1
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-romeo-and-juliet_protagonist-romeo_product-print_size-8x10_line-type-char_char_background-color-#1F2A40_font-color-#DAA520_border-color-#101520_font-Playfair Display_title-display-yes.png",
        # Index 2
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-the-great-gatsby_protagonist-jay-gatsby_product-print_size-8x10_line-type-char_char_background-color-#FDF6E3_font-color-#003366_border-color-#B58863_font-Cormorant Garamond_title-display-yes.png",
        # Index 3
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-to-kill-a-mockingbird_protagonist-scout-finch_product-print_size-8x10_line-type-char_char_background-color-#E8E4D8_font-color-#544945_border-color-#A0948A_font-Merriweather_title-display-yes.png",
        # Index 4 (Add one more for a 5-item example)
        "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/title-1984_protagonist-winston-smith_product-print_size-8x10_line-type-char_char_background-color-#A9A9A9_font-color-#E5E5E5_border-color-#404040_font-Orbitron_title-display-yes.png"
    ]

    # --- Define Variable Grid Layout ---
    # Example: 3 base rows, 3 base columns
    example_base_rows = 3
    example_base_cols = 3

    # Template:
    # Cell 1: Top-left, large (2x2 span), showing Story 0 (HP)
    # Cell 2: Top-right, standard (1x1 span), showing Story 1 (R&J)
    # Cell 3: Mid-right, standard (1x1 span), showing Story 2 (Gatsby)
    # Cell 4: Bottom-left, wide (1x2 span), showing Story 3 (Mockingbird)
    # Cell 5: Bottom-right, standard (1x1 span), showing Story 4 (1984)
    example_template = [
        {'base_row': 0, 'base_col': 0, 'row_span': 2, 'col_span': 2, 'content_index': 0}, # HP
        {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # R&J
        {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Gatsby
        {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 3}, # Mockingbird
        {'base_row': 2, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # 1984
    ]


    # --- Define Poster Parameters ---
    poster_output_folder = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/posters/"
    os.makedirs(poster_output_folder, exist_ok=True)

    poster_filename = "literature_variable_grid_poster_24x18.png"
    output_file = os.path.join(poster_output_folder, poster_filename)
    poster_w_inches = 24
    poster_h_inches = 18
    poster_margin_inches = 1.25
    poster_spacing_inches = 0.75 # Space between the cells

    # --- Font Path (Update for your system!) ---
    title_font = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    if not os.path.exists(title_font): title_font = None

    create_poster(
        story_shape_paths=story_files,
        poster_width_in=poster_w_inches,
        poster_height_in=poster_h_inches,
        output_path=output_file,
        # Grid Definition
        base_rows=example_base_rows,
        base_cols=example_base_cols,
        grid_template=example_template,
        # Standard Options
        dpi=300,
        margin_in=poster_margin_inches,
        spacing_in=poster_spacing_inches,
        background_color='#F8F8F8',
        # Poster Title Options
        poster_title="A Collection of Story Shapes",
        poster_title_font_path=title_font,
        poster_title_font_size_pt=40,
        poster_title_font_color='#333333',
        poster_title_v_align='center',
        poster_title_padding_in=0.2
    )
# Add this function to your poster_creator.py or a separate utility file

def calculate_cell_content_size(
    poster_width_in,
    poster_height_in,
    dpi,
    margin_in,
    spacing_in,
    base_rows,
    base_cols,
    cell_row_span,
    cell_col_span
):
    """
    Calculates the maximum pixel dimensions available for content within a specific
    cell of a variable grid layout.

    Args:
        poster_width_in (float): Poster width in inches.
        poster_height_in (float): Poster height in inches.
        dpi (int): Poster resolution.
        margin_in (float): Poster margin in inches.
        spacing_in (float): Spacing between cells in inches.
        base_rows (int): Number of rows in the base grid.
        base_cols (int): Number of columns in the base grid.
        cell_row_span (int): The row span of the target cell (>=1).
        cell_col_span (int): The column span of the target cell (>=1).

    Returns:
        tuple: (max_width_px, max_height_px) for the content area of the cell,
               or None if parameters are invalid. Returns dimensions as integers.
    """
    # --- Input Validation ---
    if not all(arg > 0 for arg in [poster_width_in, poster_height_in, dpi, base_rows, base_cols, cell_row_span, cell_col_span]):
        print("Error: All dimension/span inputs must be positive.")
        return None
    if margin_in < 0 or spacing_in < 0:
        print("Error: Margins and spacing cannot be negative.")
        return None

    # --- Calculations (mirrors the logic in create_poster) ---
    poster_width_px = poster_width_in * dpi
    poster_height_px = poster_height_in * dpi
    margin_px = margin_in * dpi
    spacing_px = spacing_in * dpi

    grid_area_width = poster_width_px - 2 * margin_px
    grid_area_height = poster_height_px - 2 * margin_px

    if grid_area_width <= 0 or grid_area_height <= 0:
        print("Error: Margins are larger than the poster dimensions.")
        return None

    total_h_spacing = max(0, (base_cols - 1)) * spacing_px
    total_v_spacing = max(0, (base_rows - 1)) * spacing_px

    effective_grid_width = grid_area_width - total_h_spacing
    effective_grid_height = grid_area_height - total_v_spacing

    if effective_grid_width <= 0 or effective_grid_height <= 0:
         print("Error: Effective grid area is non-positive after accounting for spacing.")
         return None

    base_content_width = effective_grid_width / base_cols
    base_content_height = effective_grid_height / base_rows

    if base_content_width <= 0 or base_content_height <= 0:
        print("Error: Calculated base cell content size is non-positive.")
        return None

    # --- Calculate target cell's maximum content size ---
    cell_max_width_px = cell_col_span * base_content_width
    cell_max_height_px = cell_row_span * base_content_height

    # Return as integers
    return (int(round(cell_max_width_px)), int(round(cell_max_height_px)))

# --- Example Usage (using parameters from the previous Variable Grid example) ---
if __name__ == "__main__":
    # Paste the new function above this block if adding to poster_creator.py

    # Define the *same* poster and grid parameters used in create_poster
    poster_w_inches = 24
    poster_h_inches = 18
    poster_dpi = 300
    poster_margin_inches = 1.25
    poster_spacing_inches = 0.75
    example_base_rows = 3
    example_base_cols = 3

    # The template defined which cell spans what and holds which content index
    example_template = [
        {'base_row': 0, 'base_col': 0, 'row_span': 2, 'col_span': 2, 'content_index': 0}, # HP (Large)
        {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # R&J (Standard)
        {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Gatsby (Standard)
        {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 3}, # Mockingbird (Wide)
        {'base_row': 2, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # 1984 (Standard)
    ]

    print("\n--- Calculating Target Cell Sizes ---")

    for i, cell_def in enumerate(example_template):
        rs = cell_def['row_span']
        cs = cell_def['col_span']
        content_idx = cell_def['content_index']

        target_size = calculate_cell_content_size(
            poster_width_in=poster_w_inches,
            poster_height_in=poster_h_inches,
            dpi=poster_dpi,
            margin_in=poster_margin_inches,
            spacing_in=poster_spacing_inches,
            base_rows=example_base_rows,
            base_cols=example_base_cols,
            cell_row_span=rs,
            cell_col_span=cs
        )

        if target_size:
            print(f"Cell {i} (Content Index {content_idx}, Span {rs}x{cs}): Max content size = {target_size[0]} x {target_size[1]} pixels")
        else:
             print(f"Could not calculate size for Cell {i}")

    # Example calculation for a specific cell (e.g., the large 2x2 cell for HP)
    hp_cell = example_template[0] # Assuming HP is the first item in the template
    hp_size = calculate_cell_content_size(
        poster_width_in=poster_w_inches, poster_height_in=poster_h_inches, dpi=poster_dpi,
        margin_in=poster_margin_inches, spacing_in=poster_spacing_inches,
        base_rows=example_base_rows, base_cols=example_base_cols,
        cell_row_span=hp_cell['row_span'], cell_col_span=hp_cell['col_span']
    )
    if hp_size:
        print(f"\nSpecifically for HP (Cell 0, Span {hp_cell['row_span']}x{hp_cell['col_span']}): Target {hp_size[0]}x{hp_size[1]} px")

    # Example calculation for a standard 1x1 cell (e.g., R&J)
    rj_cell = example_template[1]
    rj_size = calculate_cell_content_size(
        poster_width_in=poster_w_inches, poster_height_in=poster_h_inches, dpi=poster_dpi,
        margin_in=poster_margin_inches, spacing_in=poster_spacing_inches,
        base_rows=example_base_rows, base_cols=example_base_cols,
        cell_row_span=rj_cell['row_span'], cell_col_span=rj_cell['col_span']
    )
    if rj_size:
        print(f"Specifically for R&J (Cell 1, Span {rj_cell['row_span']}x{rj_cell['col_span']}): Target {rj_size[0]}x{rj_size[1]} px")