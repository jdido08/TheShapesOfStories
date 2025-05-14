# poster_creator.py
import math
import os
from PIL import Image, ImageDraw, ImageFont
import platform

from poster_layout_templates import poster_layout_templates

DEFAULT_DPI = 300

def get_default_font():
    # ... (no changes)
    system = platform.system()
    if system == "Windows":
        font_paths = [
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "Arial.ttf"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "TIMES.TTF"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "Verdana.ttf"),
        ]
    elif system == "Darwin": # macOS
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Times New Roman.ttf",
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
        if os.path.exists(font_path): return font_path
    print("Warning: Could not find a default system font.")
    try:
        font = ImageFont.load_default()
        if font: print("Using Pillow's limited default font."); return None
    except IOError: print("Error: Pillow's default font also failed to load.")
    return "FONT_ERROR"

def parse_color(color_input):
    # ... (no changes)
    if isinstance(color_input, str):
        if color_input.startswith('#'):
            hex_color = color_input.lstrip('#')
            if len(hex_color) == 3: hex_color = "".join([c * 2 for c in hex_color])
            if len(hex_color) != 6: raise ValueError("Invalid hex format.")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        raise ValueError("Invalid hex string format.")
    elif isinstance(color_input, tuple) and len(color_input) == 3:
        if all(0 <= c <= 1 for c in color_input): return tuple(int(c * 255) for c in color_input)
        if all(0 <= c <= 255 for c in color_input): return tuple(int(c) for c in color_input)
        raise ValueError("RGB tuple values out of range.")
    raise TypeError("Color must be hex string or RGB tuple.")

def calculate_cell_content_size( # KEEP THIS CORRECTED VERSION
    poster_width_in, poster_height_in, dpi, margin_in, spacing_in,
    base_rows, base_cols, cell_row_span, cell_col_span
):
    # ... (Keep the version that correctly calculates total block size including internal spacing)
    if not all(arg > 0 for arg in [poster_width_in, poster_height_in, dpi, base_rows, base_cols, cell_row_span, cell_col_span]): return None
    if margin_in < 0 or spacing_in < 0: return None
    poster_width_px, poster_height_px = poster_width_in * dpi, poster_height_in * dpi
    margin_px, spacing_px_val = margin_in * dpi, spacing_in * dpi # renamed spacing_px to avoid conflict
    grid_area_width = poster_width_px - 2 * margin_px
    grid_area_height = poster_height_px - 2 * margin_px # This is initial, will be adjusted by title/subtitle
    if grid_area_width <= 0 or grid_area_height <= 0: return None
    total_h_spacing = max(0, (base_cols - 1)) * spacing_px_val
    total_v_spacing = max(0, (base_rows - 1)) * spacing_px_val
    effective_grid_width = grid_area_width - total_h_spacing
    effective_grid_height = grid_area_height - total_v_spacing # This refers to sum of base content heights
    if effective_grid_width <= 0 or effective_grid_height <= 0: return None
    base_content_width_float = effective_grid_width / base_cols
    base_content_height_float = effective_grid_height / base_rows
    if base_content_width_float <= 0 or base_content_height_float <= 0: return None
    cell_total_block_width_px = (cell_col_span * base_content_width_float) + max(0, (cell_col_span - 1)) * spacing_px_val
    cell_total_block_height_px = (cell_row_span * base_content_height_float) + max(0, (cell_row_span - 1)) * spacing_px_val
    return (int(round(cell_total_block_width_px)), int(round(cell_total_block_height_px)))



def create_layout_preview(
    poster_width_in,
    poster_height_in,
    output_path,
    base_rows,
    base_cols,
    grid_template,
    dpi=72, # Typically lower DPI for previews
    margin_in=0.75,
    spacing_in=0.5,
    background_color='#EFEFEF', # Preview-specific background
    # --- Text Block Options (mirroring create_poster) ---
    poster_title="",
    poster_title_font_path=None,
    poster_title_font_size_pt=36,
    poster_title_font_color='#000000',
    poster_subtitle="",
    poster_subtitle_font_path=None,
    poster_subtitle_font_size_pt=24,
    poster_subtitle_font_color='#000000',
    text_block_v_align='top',
    text_edge_padding_in=0.2,
    space_between_texts_in=0.05,
    space_text_grid_in=0.2,
    # --- Preview Specific Appearance ---
    preview_cell_fill_color='#D0D0FF',
    preview_cell_outline_color='#333333',
    preview_text_color='#000000', # For annotations inside cells
    preview_annotation_font_path=None,
    preview_annotation_font_size_pt=10,
    preview_text_padding_px=5
):
    # --- Basic Validations ---
    if not grid_template: print("Error (Preview): grid_template is empty."); return
    if not text_block_v_align in ['top', 'bottom']:
        print("Error (Preview): text_block_v_align must be 'top' or 'bottom'. Defaulting to 'top'.")
        text_block_v_align = 'top'
    # ... (other validations) ...

    # --- Convert Inches to Pixels ---
    poster_width_px = int(poster_width_in * dpi)
    poster_height_px = int(poster_height_in * dpi)
    margin_px = int(margin_in * dpi)
    spacing_px_grid = int(spacing_in * dpi)
    text_edge_padding_px = int(text_edge_padding_in * dpi)
    space_between_texts_px = int(space_between_texts_in * dpi)
    space_text_grid_px = int(space_text_grid_in * dpi)

    try:
        bg_color_rgb = parse_color(background_color)
        cell_fill_rgb = parse_color(preview_cell_fill_color)
        cell_outline_rgb = parse_color(preview_cell_outline_color)
        annotation_text_color_rgb = parse_color(preview_text_color)
    except ValueError as e: print(f"Error (Preview) parsing color: {e}"); return

    # --- Load Fonts & Calculate Text Element Dimensions ---
    title_font, subtitle_font, annotation_draw_font = None, None, None
    title_color_rgb, subtitle_color_rgb = None, None
    rendered_title_width, rendered_title_height = 0, 0
    rendered_subtitle_width, rendered_subtitle_height = 0, 0

    # Title Font
    if poster_title:
        try: title_color_rgb = parse_color(poster_title_font_color)
        except ValueError: poster_title = ""
        if poster_title:
            font_path = poster_title_font_path or get_default_font()
            if font_path != "FONT_ERROR":
                font_size = max(1, int(poster_title_font_size_pt * dpi / 72))
                try:
                    title_font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(size=font_size)
                    temp_draw = ImageDraw.Draw(Image.new("RGB",(1,1)))
                    try: bbox = temp_draw.textbbox((0,0), poster_title, font=title_font, anchor="lt")
                    except TypeError: bbox = temp_draw.textbbox((0,0), poster_title, font=title_font)
                    rendered_title_width, rendered_title_height = bbox[2]-bbox[0], bbox[3]-bbox[1]
                except Exception: poster_title = "" # Failed to load/measure
            else: poster_title = ""
    
    # Subtitle Font
    if poster_subtitle:
        try: subtitle_color_rgb = parse_color(poster_subtitle_font_color)
        except ValueError: poster_subtitle = ""
        if poster_subtitle:
            font_path = poster_subtitle_font_path or get_default_font()
            if font_path != "FONT_ERROR":
                font_size = max(1, int(poster_subtitle_font_size_pt * dpi / 72))
                try:
                    subtitle_font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(size=font_size)
                    temp_draw = ImageDraw.Draw(Image.new("RGB",(1,1)))
                    try: bbox = temp_draw.textbbox((0,0), poster_subtitle, font=subtitle_font, anchor="lt")
                    except TypeError: bbox = temp_draw.textbbox((0,0), poster_subtitle, font=subtitle_font)
                    rendered_subtitle_width, rendered_subtitle_height = bbox[2]-bbox[0], bbox[3]-bbox[1]
                except Exception: poster_subtitle = ""
            else: poster_subtitle = ""

    # Annotation Font (for inside cells)
    ann_font_path = preview_annotation_font_path or get_default_font()
    ann_font_size_px = max(1, int(preview_annotation_font_size_pt * dpi / 72))
    if ann_font_path != "FONT_ERROR":
        try: annotation_draw_font = ImageFont.truetype(ann_font_path, ann_font_size_px) if ann_font_path else ImageFont.load_default(size=ann_font_size_px)
        except: annotation_draw_font = ImageFont.load_default() # Fallback
    else: annotation_draw_font = ImageFont.load_default()


    # --- Calculate Total Height of the Text Block ---
    total_text_block_height_px = 0
    if poster_title and title_font: total_text_block_height_px += rendered_title_height
    if poster_subtitle and subtitle_font:
        if total_text_block_height_px > 0: total_text_block_height_px += space_between_texts_px
        total_text_block_height_px += rendered_subtitle_height
    
    # --- Determine Grid Area Boundaries ---
    grid_area_top_y = margin_px
    grid_area_bottom_y = poster_height_px - margin_px
    if total_text_block_height_px > 0:
        if text_block_v_align == 'top':
            grid_area_top_y = text_edge_padding_px + total_text_block_height_px + space_text_grid_px
            grid_area_top_y = max(margin_px, grid_area_top_y)
        elif text_block_v_align == 'bottom':
            grid_area_bottom_y = poster_height_px - (text_edge_padding_px + total_text_block_height_px + space_text_grid_px)
            grid_area_bottom_y = min(poster_height_px - margin_px, grid_area_bottom_y)

    # --- Calculate Grid Area Dimensions ---
    grid_area_width_px = poster_width_px - 2 * margin_px
    grid_area_height_px = grid_area_bottom_y - grid_area_top_y
    if grid_area_width_px <= 0 or grid_area_height_px <= 0:
        print("Error (Preview): No space left for grid."); # Draw text only if possible
        # ... (optional: draw text on blank canvas if grid fails) ...
        return

    # --- Calculate Base Cell Dimensions for the Grid (these are the crucial content sizes) ---
    total_h_spacing_grid = max(0, (base_cols - 1)) * spacing_px_grid
    total_v_spacing_grid = max(0, (base_rows - 1)) * spacing_px_grid
    effective_grid_width = grid_area_width_px - total_h_spacing_grid
    effective_grid_height = grid_area_height_px - total_v_spacing_grid

    if effective_grid_width <=0 or effective_grid_height <=0: print("Error (Preview): Effective grid area non-positive."); return
    # THIS IS THE BASE CONTENT SIZE OF A 1x1 CELL IN THE *ACTUAL* AVAILABLE GRID SPACE
    base_content_width_for_cells = effective_grid_width / base_cols
    base_content_height_for_cells = effective_grid_height / base_rows
    if base_content_width_for_cells <= 0 or base_content_height_for_cells <= 0: print("Error (Preview): Base content size non-positive."); return

    print(f"\n--- Preview: Calculated Cell Content Dimensions (at {dpi} DPI for preview) ---")
    print(f"Based on available grid area: {grid_area_width_px}x{grid_area_height_px}px at ({margin_px},{grid_area_top_y})")
    print(f"A 1x1 cell's base content area would be: {base_content_width_for_cells:.2f} x {base_content_height_for_cells:.2f} px")

    # --- Create Canvas & Draw Object ---
    preview_img = Image.new('RGB', (poster_width_px, poster_height_px), bg_color_rgb)
    draw = ImageDraw.Draw(preview_img)

    # --- Draw Text Elements ---
    y_cursor = 0
    if text_block_v_align == 'top':
        y_cursor = text_edge_padding_px
        if poster_title and title_font:
            draw.text(((poster_width_px - rendered_title_width) / 2, y_cursor), poster_title, fill=title_color_rgb, font=title_font)
            y_cursor += rendered_title_height
            if poster_subtitle and subtitle_font: y_cursor += space_between_texts_px
        if poster_subtitle and subtitle_font:
            draw.text(((poster_width_px - rendered_subtitle_width) / 2, y_cursor), poster_subtitle, fill=subtitle_color_rgb, font=subtitle_font)
    elif text_block_v_align == 'bottom':
        bottom_text_start_y = poster_height_px - text_edge_padding_px
        if poster_subtitle and subtitle_font:
            bottom_text_start_y -= rendered_subtitle_height
            draw.text(((poster_width_px - rendered_subtitle_width) / 2, bottom_text_start_y), poster_subtitle, fill=subtitle_color_rgb, font=subtitle_font)
            if poster_title and title_font: bottom_text_start_y -= (space_between_texts_px + rendered_title_height)
        if poster_title and title_font: # Handles only title, or title above subtitle
             # If subtitle was drawn, bottom_text_start_y is already adjusted. If not, adjust now.
             if not (poster_subtitle and subtitle_font): bottom_text_start_y -= rendered_title_height
             draw.text(((poster_width_px - rendered_title_width) / 2, bottom_text_start_y), poster_title, fill=title_color_rgb, font=title_font)

    # --- Draw Grid Cells and Annotations ---
    for i, cell_template_item in enumerate(grid_template):
        br, bc = cell_template_item['base_row'], cell_template_item['base_col']
        rs, cs = cell_template_item['row_span'], cell_template_item['col_span']
        content_idx = cell_template_item['content_index']

        # Dimensions of the visual block for this cell in the preview (includes internal spacing)
        preview_cell_block_width = (cs * base_content_width_for_cells) + max(0, (cs - 1)) * spacing_px_grid
        preview_cell_block_height = (rs * base_content_height_for_cells) + max(0, (rs - 1)) * spacing_px_grid
        
        # ACTUAL CONTENT size for this cell (this is what your PNG should be for create_poster)
        actual_content_width_for_image = int(round(preview_cell_block_width))
        actual_content_height_for_image = int(round(preview_cell_block_height))

        # Position of the cell block within the grid area
        block_x_start_in_grid = bc * (base_content_width_for_cells + spacing_px_grid)
        block_y_start_in_grid = br * (base_content_height_for_cells + spacing_px_grid)
        
        # Absolute position on the poster
        block_x_start_abs = margin_px + block_x_start_in_grid
        block_y_start_abs = grid_area_top_y + block_y_start_in_grid

        if actual_content_width_for_image <=0 or actual_content_height_for_image <= 0: continue

        draw.rectangle(
            [block_x_start_abs, block_y_start_abs,
             block_x_start_abs + actual_content_width_for_image, # Use actual content size for rect
             block_y_start_abs + actual_content_height_for_image],
            fill=cell_fill_rgb, outline=cell_outline_rgb, width=max(1, dpi // 100) # Thinner outline for preview
        )
        
        # Calculate dimensions in inches for annotation
        # This uses the DPI that was passed to create_layout_preview
        content_width_in_for_ann = actual_content_width_for_image / dpi
        content_height_in_for_ann = actual_content_height_for_image / dpi

        annotation_text_lines = [
            f"Cell: {i} (CI: {content_idx})",
            f"Span: {rs}x{cs}",
            f"Size for PNG:",
            f"{actual_content_width_for_image}x{actual_content_height_for_image}px (at {dpi} DPI)",
            f"~{content_width_in_for_ann:.2f}x{content_height_in_for_ann:.2f} in" # NEW LINE
        ]
        # Also update the console print statement if you want inches there too
        print(f"  - Cell {i} (CI: {content_idx}, Span {rs}x{cs}): PNG Target = "
              f"{actual_content_width_for_image}x{actual_content_height_for_image}px "
              f"(~{content_width_in_for_ann:.2f}x{content_height_in_for_ann:.2f} inches at {dpi} DPI)")
        
        # ... (your existing annotation text drawing logic, using annotation_draw_font and annotation_text_color_rgb)
        current_y_ann = block_y_start_abs + preview_text_padding_px
        line_h_approx = ann_font_size_px * 1.2 
        for line_idx, line_text in enumerate(annotation_text_lines):
            if current_y_ann + line_h_approx > block_y_start_abs + actual_content_height_for_image - preview_text_padding_px and line_idx > 0:
                draw.text((block_x_start_abs + preview_text_padding_px, current_y_ann), "...", fill=annotation_text_color_rgb, font=annotation_draw_font); break
            try:
                # Simplified text drawing for preview
                draw.text((block_x_start_abs + preview_text_padding_px, current_y_ann), line_text, fill=annotation_text_color_rgb, font=annotation_draw_font)
                # Estimate line height for next line
                current_y_ann += ann_font_size_px * 1.2 # Simpler advance
            except Exception: break 

    # --- Save Preview Image ---
    try:
        preview_img.save(output_path)
        print(f"\nLayout preview saved to {output_path}")
    except Exception as e: print(f"Error (Preview) saving image: {e}")
    finally: preview_img.close()

def create_poster(
    story_shape_paths,
    poster_width_in,
    poster_height_in,
    output_path,
    base_rows,
    base_cols,
    grid_template,
    dpi=DEFAULT_DPI,
    margin_in=0.75,         # General margin around the grid area
    spacing_in=0.5,         # Spacing BETWEEN grid cells
    background_color='#FFFFFF',
    # --- Text Block Options ---
    poster_title="",
    poster_title_font_path=None,
    poster_title_font_size_pt=36,
    poster_title_font_color='#000000',
    poster_subtitle="",
    poster_subtitle_font_path=None,
    poster_subtitle_font_size_pt=24,
    poster_subtitle_font_color='#000000',
    text_block_v_align='top',    # 'top', 'bottom' (center is more complex for dynamic grid)
    text_edge_padding_in=0.2,    # Padding from poster top/bottom edge to the text block
    space_between_texts_in=0.05, # Space between title and subtitle
    space_text_grid_in=0.2       # Space between the entire text block and the grid
):
    # --- Basic Validations ---
    if not grid_template: print("Error: grid_template is empty."); return
    if not text_block_v_align in ['top', 'bottom']:
        print("Error: text_block_v_align must be 'top' or 'bottom'. Defaulting to 'top'.")
        text_block_v_align = 'top'
    # ... (keep your other initial validations for dimensions, dpi, story_paths etc.)

    # --- Convert Inches to Pixels ---
    poster_width_px = int(poster_width_in * dpi)
    poster_height_px = int(poster_height_in * dpi)
    margin_px = int(margin_in * dpi) # This is the margin for the grid area primarily
    spacing_px_grid = int(spacing_in * dpi)
    
    text_edge_padding_px = int(text_edge_padding_in * dpi)
    space_between_texts_px = int(space_between_texts_in * dpi)
    space_text_grid_px = int(space_text_grid_in * dpi)

    try: bg_color_rgb = parse_color(background_color)
    except ValueError as e: print(f"Error parsing background color: {e}"); return

    # --- Load Fonts & Calculate Text Element Dimensions ---
    title_font, subtitle_font = None, None
    title_color_rgb, subtitle_color_rgb = None, None
    rendered_title_width, rendered_title_height = 0, 0
    rendered_subtitle_width, rendered_subtitle_height = 0, 0

    # Title
    if poster_title:
        try: title_color_rgb = parse_color(poster_title_font_color)
        except ValueError as e: print(f"Error parsing title color: {e}"); poster_title = ""
        if poster_title:
            font_path = poster_title_font_path or get_default_font()
            if font_path != "FONT_ERROR":
                font_size = max(1, int(poster_title_font_size_pt * dpi / 72))
                try:
                    title_font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(size=font_size)
                    # Use a temporary draw object to measure text
                    temp_draw = ImageDraw.Draw(Image.new("RGB",(1,1)))
                    try: bbox = temp_draw.textbbox((0,0), poster_title, font=title_font, anchor="lt")
                    except TypeError: bbox = temp_draw.textbbox((0,0), poster_title, font=title_font)
                    rendered_title_width = bbox[2] - bbox[0]
                    rendered_title_height = bbox[3] - bbox[1]
                except Exception as e: print(f"Error loading/measuring title font: {e}"); poster_title = ""
            else: poster_title = ""

    # Subtitle
    if poster_subtitle:
        try: subtitle_color_rgb = parse_color(poster_subtitle_font_color)
        except ValueError as e: print(f"Error parsing subtitle color: {e}"); poster_subtitle = ""
        if poster_subtitle:
            font_path = poster_subtitle_font_path or get_default_font()
            if font_path != "FONT_ERROR":
                font_size = max(1, int(poster_subtitle_font_size_pt * dpi / 72))
                try:
                    subtitle_font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(size=font_size)
                    temp_draw = ImageDraw.Draw(Image.new("RGB",(1,1)))
                    try: bbox = temp_draw.textbbox((0,0), poster_subtitle, font=subtitle_font, anchor="lt")
                    except TypeError: bbox = temp_draw.textbbox((0,0), poster_subtitle, font=subtitle_font)
                    rendered_subtitle_width = bbox[2] - bbox[0]
                    rendered_subtitle_height = bbox[3] - bbox[1]
                except Exception as e: print(f"Error loading/measuring subtitle font: {e}"); poster_subtitle = ""
            else: poster_subtitle = ""

    # --- Calculate Total Height of the Text Block ---
    total_text_block_height_px = 0
    if poster_title and title_font:
        total_text_block_height_px += rendered_title_height
    if poster_subtitle and subtitle_font:
        if total_text_block_height_px > 0: # If title also exists, add space between
            total_text_block_height_px += space_between_texts_px
        total_text_block_height_px += rendered_subtitle_height
    
    # --- Determine Grid Area Boundaries based on Text Alignment ---
    grid_area_top_y = margin_px
    grid_area_bottom_y = poster_height_px - margin_px

    if total_text_block_height_px > 0: # Only adjust if there's text
        if text_block_v_align == 'top':
            grid_area_top_y = text_edge_padding_px + total_text_block_height_px + space_text_grid_px
            # Ensure grid doesn't start below the general top margin if text block is small
            grid_area_top_y = max(margin_px, grid_area_top_y) 
        elif text_block_v_align == 'bottom':
            grid_area_bottom_y = poster_height_px - (text_edge_padding_px + total_text_block_height_px + space_text_grid_px)
            # Ensure grid doesn't end above the general bottom margin if text block is small
            grid_area_bottom_y = min(poster_height_px - margin_px, grid_area_bottom_y)

    # --- Calculate Grid Area Dimensions ---
    grid_area_width_px = poster_width_px - 2 * margin_px # Horizontal margins for grid
    grid_area_height_px = grid_area_bottom_y - grid_area_top_y

    if grid_area_width_px <= 0 or grid_area_height_px <= 0:
        print("Error: No space left for grid. Check text sizes, paddings, margins, or poster dimensions.")
        # Optionally, save poster with just text if any text was processed
        # ... (code to draw text only if grid fails) ...
        return

    # --- Calculate Base Cell Dimensions for the Grid ---
    total_h_spacing_grid = max(0, (base_cols - 1)) * spacing_px_grid
    total_v_spacing_grid = max(0, (base_rows - 1)) * spacing_px_grid
    effective_grid_width = grid_area_width_px - total_h_spacing_grid
    effective_grid_height = grid_area_height_px - total_v_spacing_grid

    if effective_grid_width <=0 or effective_grid_height <=0: print("Error: Effective grid area non-positive."); return
    base_content_width = effective_grid_width / base_cols
    base_content_height = effective_grid_height / base_rows
    if base_content_width <= 0 or base_content_height <= 0: print("Error: Base content size non-positive."); return

    # --- Create Canvas & Draw Object ---
    poster_img = Image.new('RGB', (poster_width_px, poster_height_px), bg_color_rgb)
    draw = ImageDraw.Draw(poster_img)

    # --- Draw Text Elements ---
    y_cursor = 0
    if text_block_v_align == 'top':
        y_cursor = text_edge_padding_px
        if poster_title and title_font:
            draw.text(((poster_width_px - rendered_title_width) / 2, y_cursor), poster_title, fill=title_color_rgb, font=title_font)
            y_cursor += rendered_title_height
            if poster_subtitle and subtitle_font: y_cursor += space_between_texts_px
        if poster_subtitle and subtitle_font:
            draw.text(((poster_width_px - rendered_subtitle_width) / 2, y_cursor), poster_subtitle, fill=subtitle_color_rgb, font=subtitle_font)
            y_cursor += rendered_subtitle_height
    
    elif text_block_v_align == 'bottom':
        # Calculate starting y for the bottom-most text element (subtitle or title)
        bottom_text_start_y = poster_height_px - text_edge_padding_px
        if poster_subtitle and subtitle_font:
            bottom_text_start_y -= rendered_subtitle_height # y is top of text, so subtract height
            draw.text(((poster_width_px - rendered_subtitle_width) / 2, bottom_text_start_y), poster_subtitle, fill=subtitle_color_rgb, font=subtitle_font)
            if poster_title and title_font: # If title is above it
                bottom_text_start_y -= (space_between_texts_px + rendered_title_height)
                draw.text(((poster_width_px - rendered_title_width) / 2, bottom_text_start_y), poster_title, fill=title_color_rgb, font=title_font)
        elif poster_title and title_font: # Only title at the bottom
             bottom_text_start_y -= rendered_title_height
             draw.text(((poster_width_px - rendered_title_width) / 2, bottom_text_start_y), poster_title, fill=title_color_rgb, font=title_font)

    # --- Process Grid Template: Load, Resize, Paste Images ---
    for cell_template_item in grid_template:
        content_idx = cell_template_item['content_index']
        img_path = story_shape_paths[content_idx] if content_idx < len(story_shape_paths) else None
        br, bc = cell_template_item['base_row'], cell_template_item['base_col']
        rs, cs = cell_template_item['row_span'], cell_template_item['col_span']

        image_target_block_width = (cs * base_content_width) + max(0, (cs - 1)) * spacing_px_grid
        image_target_block_height = (rs * base_content_height) + max(0, (rs - 1)) * spacing_px_grid
        
        block_x_start_in_grid = bc * (base_content_width + spacing_px_grid)
        block_y_start_in_grid = br * (base_content_height + spacing_px_grid)
        
        block_x_start_abs = margin_px + block_x_start_in_grid # Relative to poster edge (left margin)
        block_y_start_abs = grid_area_top_y + block_y_start_in_grid # Relative to poster edge (top of grid area)

        if not img_path or not os.path.isfile(img_path):
            # ... (placeholder drawing - keep your existing logic) ...
            draw.rectangle([block_x_start_abs, block_y_start_abs, block_x_start_abs + image_target_block_width, block_y_start_abs + image_target_block_height], outline="red", width=2)
            # Simplified placeholder text
            try: temp_font = ImageFont.load_default(size=15)
            except: temp_font = ImageFont.load_default()
            draw.text((block_x_start_abs + 5, block_y_start_abs + 5), f"Missing {content_idx}", fill="red", font=temp_font)
            continue
        try:
            img = Image.open(img_path)
            img_w_orig, img_h_orig = img.size
            if img_w_orig == 0 or img_h_orig == 0: continue
            
            ratio = min(image_target_block_width / img_w_orig, image_target_block_height / img_h_orig)
            new_w = max(1, int(img_w_orig * ratio))
            new_h = max(1, int(img_h_orig * ratio))
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            paste_x = int(block_x_start_abs + (image_target_block_width - new_w) / 2)
            paste_y = int(block_y_start_abs + (image_target_block_height - new_h) / 2)

            if img_resized.mode == 'RGBA':
                poster_img.paste(img_resized, (paste_x, paste_y), img_resized)
            else:
                poster_img.paste(img_resized, (paste_x, paste_y))
            img.close()
        except Exception as e:
            print(f"Error processing image {img_path}: {e}")
            # ... (error placeholder drawing - keep your existing logic) ...
            draw.rectangle([block_x_start_abs, block_y_start_abs, block_x_start_abs + image_target_block_width, block_y_start_abs + image_target_block_height], outline="orange", width=2)
            try: temp_font = ImageFont.load_default(size=15)
            except: temp_font = ImageFont.load_default()
            draw.text((block_x_start_abs + 5, block_y_start_abs + 5), f"Error {content_idx}", fill="orange", font=temp_font)


    # --- Save Poster ---
    try:
        poster_img.save(output_path)
        print(f"Poster saved successfully to {output_path}")
    except Exception as e: print(f"Error saving poster: {e}")
    finally: poster_img.close()

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # Step 1: Define Poster General Parameters
    poster_output_folder = "./generated_posters/"
    os.makedirs(poster_output_folder, exist_ok=True)
    dummy_image_folder = os.path.join(poster_output_folder, "dummy_story_shapes")
    os.makedirs(dummy_image_folder, exist_ok=True)

    poster_w_inches = 24 
    poster_h_inches = 36 
    print_dpi = 300
    preview_dpi = 72 

    poster_general_margin_in = 1.0 # General margin for grid from poster edges
    grid_cell_spacing_in = 0.15  # Spacing between grid cells
    
    # --- Text Element Configuration ---
    main_title_text = "The Shapes of Awesome Stories"
    title_font_path_config = None 
    title_font_size_config = 100 # Test with large font
    title_color_config = '#222222'

    #subtitle_text_config = "A Deep Dive into Narrative Structures"
    subtitle_text_config = "" # Test with no subtitle
    subtitle_font_path_config = None
    subtitle_font_size_config = 40
    subtitle_color_config = '#444444'
    
    text_alignment = 'top' # 'top' or 'bottom'
    padding_from_edge_in = 0.5      # Padding from poster edge to text block
    padding_between_texts_in = 0.1  # Padding between title and subtitle
    padding_text_to_grid_in = 0.5   # Padding between text block and grid

    # Step 2: Choose a Layout Template
    chosen_template_name = "stories5_two_top_three_bottom" 
    # chosen_template_name = "stories4_hero_left_three_stacked_right"

    if chosen_template_name not in poster_layout_templates:
        print(f"Error: Template '{chosen_template_name}' not found."); exit()
    
    selected_layout = poster_layout_templates[chosen_template_name]
    print(f"\n--- Using Template: {chosen_template_name} ({selected_layout['description']}) ---")

    num_expected_stories = selected_layout["num_stories"]
    base_r_template = selected_layout["base_rows"]
    base_c_template = selected_layout["base_cols"]
    grid_def_template = selected_layout["grid_template"]
    print(f"Expects {num_expected_stories} stories. Base grid: {base_r_template}x{base_c_template}.")


    print(f"\n--- Generating Layout Preview (DPI: {preview_dpi}) ---")
    preview_filename = f"PREVIEW_{chosen_template_name}_{poster_w_inches}x{poster_h_inches}_text-{text_alignment}_DPI{preview_dpi}.png"
    preview_output_file = os.path.join(poster_output_folder, preview_filename)

    create_layout_preview(
        poster_width_in=poster_w_inches, poster_height_in=poster_h_inches,
        output_path=preview_output_file,
        base_rows=base_r_template, base_cols=base_c_template,
        grid_template=grid_def_template,
        dpi=preview_dpi, # Use the preview DPI here
        margin_in=poster_general_margin_in, 
        spacing_in=grid_cell_spacing_in,
        background_color='#E0E0E0', 
        # Text Block
        poster_title=main_title_text,
        poster_title_font_path=title_font_path_config, 
        poster_title_font_size_pt=title_font_size_config,
        poster_title_font_color=title_color_config, 
        poster_subtitle=subtitle_text_config,
        poster_subtitle_font_path=subtitle_font_path_config,
        poster_subtitle_font_size_pt=subtitle_font_size_config,
        poster_subtitle_font_color=subtitle_color_config,
        text_block_v_align=text_alignment,
        text_edge_padding_in=padding_from_edge_in,
        space_between_texts_in=padding_between_texts_in,
        space_text_grid_in=padding_text_to_grid_in,
        # Preview specific appearance
        preview_cell_fill_color='#C8C8FA', # Slightly different fill
        preview_annotation_font_size_pt=9 # Smaller for more text
    )
    
    # The print statements inside create_layout_preview will now output the
    # dimensions your PNGs should be if you were targeting the *preview_dpi_main*.
    # To get sizes for your *print_dpi* (e.g., 300), you would ideally run create_layout_preview
    # once with dpi=300 (and save it to a different filename, or just note the output).
    # Or, you can manually scale the output from the preview_dpi run.
    # Example: If preview at 72 DPI says 100x100px, for 300 DPI it's (100 * 300/72) x (100 * 300/72)

    print("\n--- To get PNG sizes for PRINT, re-run preview with print_dpi or scale the above. ---")

    # Step 4: Calculate Required Story Shape Sizes & Prepare Dummies
    # This step becomes more complex if we want dummy sizes to be perfectly accurate
    # before create_poster runs, as create_poster now calculates the final grid area.
    # For now, we'll use calculate_cell_content_size with initial poster dimensions,
    # understanding that create_poster will handle the true final sizing and placement.
    # The dummy images are mainly for having *something* to pass to create_poster.
    print("\n--- Calculating Initial Target Sizes for Dummy Story Shapes (Print DPI) ---")
    required_sizes = {} 
    for i, cell_def in enumerate(grid_def_template):
        idx, rs, cs = cell_def['content_index'], cell_def['row_span'], cell_def['col_span']
        size = calculate_cell_content_size(
            poster_w_inches, poster_h_inches, print_dpi, poster_general_margin_in, 
            grid_cell_spacing_in, base_r_template, base_c_template, rs, cs
        )
        required_sizes[idx] = size if size else (50,50) # Fallback
        # if size: print(f"  - Dummy for idx {idx} (Cell {i}, Span {rs}x{cs}): ~{size[0]}x{size[1]}px")

    story_files = [None] * num_expected_stories
    print("\n--- Preparing/Checking Dummy Story Shape Image Paths ---")
    for i in range(num_expected_stories):
        s = required_sizes.get(i, (50,50))
        dw, dh = max(1,s[0]), max(1,s[1]) # Ensure positive
        name = f"dummy_idx{i}_{dw}x{dh}.png"
        path = os.path.join(dummy_image_folder, name)
        if not os.path.exists(path):
            try:
                img = Image.new('RGB', (dw, dh), (210,210,230))
                dr = ImageDraw.Draw(img)
                try: f = ImageFont.load_default(size=max(10,int(min(dw,dh)/8)))
                except: f = ImageFont.load_default()
                txt = f"idx {i}\n{dw}x{dh}"
                try:
                    bb = dr.textbbox((0,0),txt,font=f,align="center")
                    dr.text(((dw-(bb[2]-bb[0]))/2, (dh-(bb[3]-bb[1]))/2), txt, (0,0,0), f, align="center")
                except: dr.text((5,5),txt,(0,0,0),f)
                img.save(path)
            except Exception as e: print(f"Err dummy {i}: {e}"); path=None
        story_files[i] = path
    
    # Step 7: Create Actual Poster
    print("\n--- Generating Actual Poster ---")
    filename = f"POSTER_{chosen_template_name}_{poster_w_inches}x{poster_h_inches}_text-{text_alignment}.png"
    output_file_path = os.path.join(poster_output_folder, filename)
    
    create_poster(
        story_shape_paths=story_files,
        poster_width_in=poster_w_inches, poster_height_in=poster_h_inches,
        output_path=output_file_path,
        base_rows=base_r_template, base_cols=base_c_template,
        grid_template=grid_def_template,
        dpi=print_dpi, 
        margin_in=poster_general_margin_in, 
        spacing_in=grid_cell_spacing_in,
        background_color='#F0F0F0', 
        # Text Block
        poster_title=main_title_text,
        poster_title_font_path=title_font_path_config, 
        poster_title_font_size_pt=title_font_size_config,
        poster_title_font_color=title_color_config, 
        poster_subtitle=subtitle_text_config,
        poster_subtitle_font_path=subtitle_font_path_config,
        poster_subtitle_font_size_pt=subtitle_font_size_config,
        poster_subtitle_font_color=subtitle_color_config,
        text_block_v_align=text_alignment,
        text_edge_padding_in=padding_from_edge_in,
        space_between_texts_in=padding_between_texts_in,
        space_text_grid_in=padding_text_to_grid_in
    )

    print(f"\nCheck '{poster_output_folder}' for '{filename}'.")
    # You would also update create_layout_preview with similar text block logic if you use it.