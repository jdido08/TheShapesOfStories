from PIL import Image, ImageDraw, ImageFont

def create_poster_template_and_get_squares(
    out_filename="poster_template.png",
    width=7200,           # e.g. 24″×300 DPI
    height=10800,         # e.g. 36″×300 DPI
    margin=25,
    title_height=72,
    rows=5,
    columns=10,
    row_gap=10,
    col_gap=10,
    # New parameters for the overall poster title
    poster_title="",
    poster_title_font_path="arial.ttf",   # path to a .ttf font file
    poster_title_font_size=100
):
    """
    Creates a white poster template with an optional title text at the top,
    returns a list of bounding boxes for squares (left, top, right, bottom).
    """
    # 1) Create a white image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 2) Outline the outer border (optional)
    #    Remove if you don't want an outer border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline="black", width=1)

    # 3) Draw the title box
    title_top_left = (margin, margin)
    title_bottom_right = (width - margin - 1, margin + title_height)
    #draw.rectangle([title_top_left, title_bottom_right], outline="black", width=1)

    # (A) Draw the actual title text inside the title box
    if poster_title:
        try:
            title_font = ImageFont.truetype(poster_title_font_path, poster_title_font_size)
        except OSError:
            print("HEY")
            title_font = ImageFont.load_default()

        # Instead of `title_font.getsize(...)` do:
        bbox = draw.textbbox((0, 0), poster_title, font=title_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Now you can center the text with text_w and text_h
        box_left, box_top = title_top_left
        box_right, box_bottom = title_bottom_right
        box_width  = box_right  - box_left
        box_height = box_bottom - box_top

        title_x = box_left + (box_width  - text_w) // 2
        title_y = box_top  + (box_height - text_h) // 2

        draw.text((title_x, title_y), poster_title, fill="black", font=title_font)

     

    # 4) Determine bounding box for squares
    squares_top    = margin + title_height
    squares_bottom = height - margin - 1
    squares_left   = margin
    squares_right  = width - margin - 1

    # 5) Compute square side, possibly adjust row/col gaps
    squares_area_width  = squares_right - squares_left
    squares_area_height = squares_bottom - squares_top

    square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns
    square_side_y = (squares_area_height - (rows + 1)*row_gap)   / rows
    square_side   = min(square_side_x, square_side_y)
    if square_side < 0:
        raise ValueError("Not enough space for squares with the given row_gap/col_gap.")

    import math
    EPS = 1e-9
    width_limited  = math.isclose(square_side, square_side_x, abs_tol=EPS)
    height_limited = math.isclose(square_side, square_side_y, abs_tol=EPS)

    # Adjust row_gap or col_gap if we have leftover space
    if width_limited and not height_limited:
        used_height = rows*square_side + (rows + 1)*row_gap
        leftover = squares_area_height - used_height
        if leftover > 0:
            row_gap += leftover / (rows + 1)
    elif height_limited and not width_limited:
        used_width = columns*square_side + (columns - 1)*col_gap
        leftover = squares_area_width - used_width
        if leftover > 0 and columns > 1:
            col_gap += leftover / (columns - 1)

    final_square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns
    final_square_side_y = (squares_area_height - (rows + 1)*row_gap)   / rows
    square_side          = min(final_square_side_x, final_square_side_y)
    if square_side < 0:
        raise ValueError("After gap readjustment, squares still do not fit.")

    # 6) Build the squares' bounding boxes
    squares_bboxes = []
    current_y = squares_top + row_gap
    for r in range(rows):
        current_x = squares_left
        for c in range(columns):
            left   = current_x
            top    = current_y
            right  = current_x + square_side
            bottom = current_y + square_side

            # Optionally draw each square boundary. 
            # Remove/comment if you don’t want a visible grid.
            #draw.rectangle([(left, top), (right, bottom)], outline="black", width=1)

            squares_bboxes.append((left, top, right, bottom))
            current_x += square_side + col_gap
        current_y += square_side + row_gap

    # 7) Save your template (optional)
    img.save(out_filename, dpi=(300, 300))
    square_side_inches = square_side / 300
    print(f"Saved template '{out_filename}' with {rows}×{columns} squares that's {square_side_inches} in.")
    return squares_bboxes


from PIL import Image, ImageDraw, ImageFont

def place_shapes_onto_template(
    template_path,
    output_path,
    squares_bboxes,
    shape_paths,
    shape_titles=None,               # <- List of titles for each shape
    font_path="arial.ttf",           # <- Font to use for the shape titles
    font_size=10000,
    fill_color=(0,0,0)
):
    """
    - `template_path`: Poster template PNG path (the big background).
    - `output_path`: Where to save the final composite.
    - `squares_bboxes`: List of bounding boxes (left, top, right, bottom) from your template.
    - `shape_paths`: List of PNGs to place.
    - `shape_titles`: List of strings (same length as shape_paths) for the labels under each shape.
    - `font_path`: Path to .ttf font file
    - `font_size`: The size for the shape labels
    - `fill_color`: The color for the shape labels (RGB)
    """
    base_img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(base_img)
    
    try:
        shape_font = ImageFont.truetype(font_path, font_size)
    except OSError:
        shape_font = ImageFont.load_default()

    # If no titles were given, use empty strings
    if shape_titles is None:
        shape_titles = [""] * len(shape_paths)

    for (bbox, shape_path, shape_label) in zip(squares_bboxes, shape_paths, shape_titles):
        left, top, right, bottom = bbox
        box_width  = int(right - left)
        box_height = int(bottom - top)

        # 1) Paste the shape image
        shape_img = Image.open(shape_path).convert("RGBA")
        shape_resized = shape_img.resize((box_width, box_height), Image.Resampling.LANCZOS)
        base_img.paste(shape_resized, (int(left), int(top)), mask=shape_resized)

        # 2) Draw the shape title label (if any) below the box
        #    For example, place it ~5 pixels below the shape:
        if shape_label.strip():
            # some gap below the shape
            label_y = bottom + 5  
            # measure text with the new textbbox approach
            bbox = draw.textbbox((0, 0), shape_label, font=shape_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # Center under the shape
            label_x = left + (box_width - text_w)//2

            draw.text((label_x, label_y), shape_label, fill=fill_color, font=shape_font)

    base_img.save(output_path, dpi=(300,300))
    print(f"Saved final poster with shapes & labels to '{output_path}'.")



dpi = 300
# 1) Create a hi-res template with an overall poster title:
bboxes = create_poster_template_and_get_squares(
    out_filename="poster_template.png",
    width=24 * dpi,           # 24" × 300 DPI
    height=36 * dpi,         # 36" × 300 DPI
    margin= 0.5 * dpi,           # ~1/3 inch
    title_height= 0 * dpi,     # ~1 inch tall at 300 DPI
    rows= 3,
    columns=3,
    row_gap=50,
    col_gap=50,
    poster_title="The Shapes of the Classics",
    poster_title_font_path="/System/Library/Fonts/Supplemental/Arial.ttf",
    poster_title_font_size= (72 * (dpi / 72))
)

# 2) List your shape files
shapes = [
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png",
   "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_4.466x4.466_char_sans_6.png"
]

# 3) Provide optional shape titles
titles = [
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
    "The Old Man and the Sea",
]

# 4) Place shapes & their labels
place_shapes_onto_template(
    template_path="poster_template.png",
    output_path="final_poster_with_shapes_2.png",
    squares_bboxes=bboxes,
    shape_paths=shapes,
    shape_titles=titles,   # <--
    font_path="/System/Library/Fonts/Supplemental/Arial.ttf", # or any local .ttf
    font_size= (12 * (dpi / 72))
)
