poster_width_in_px  = 24 * 300  # = 7200
poster_height_in_px = 36 * 300  # = 10800


def create_poster_template_and_get_squares(
    out_filename="poster_template.png",
    width=poster_width_in_px,
    height=poster_height_in_px,
    margin=25,
    title_height=72,
    rows=5,
    columns=10,
    row_gap=10,
    col_gap=10
):
    """
    Creates a poster grid (as before) and returns a list of bounding boxes for each square:
    [
      (left, top, right, bottom),
      (left, top, right, bottom),
      ...
    ]
    """
    from PIL import Image, ImageDraw

    # 1) Create a white image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 2) Outline the outer border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline="black", width=1)

    # 3) Draw the title box
    title_top_left = (margin, margin)
    title_bottom_right = (width - margin - 1, margin + title_height)
    draw.rectangle([title_top_left, title_bottom_right], outline="black", width=1)

    # 4) Determine the bounding box for the squares
    squares_top    = margin + title_height
    squares_bottom = height - margin - 1
    squares_left   = margin
    squares_right  = width - margin - 1

    # 5) Usable width/height
    squares_area_width  = squares_right - squares_left
    squares_area_height = squares_bottom - squares_top

    # 6) First pass: compute `square_side`
    square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns
    square_side_y = (squares_area_height - (rows + 1)*row_gap)   / rows
    square_side   = min(square_side_x, square_side_y)
    if square_side < 0:
        raise ValueError("Not enough space to fit squares with the given row_gap/col_gap.")

    # 7) Figure out which dimension was limiting
    import math
    EPS = 1e-9
    width_limited  = math.isclose(square_side, square_side_x, abs_tol=EPS)
    height_limited = math.isclose(square_side, square_side_y, abs_tol=EPS)

    # 8) Adjust the row or column gaps if needed, so we fill the entire area
    if width_limited and not height_limited:
        # leftover space in vertical dimension => distribute among row gaps
        used_height = rows*square_side + (rows + 1)*row_gap
        leftover = squares_area_height - used_height
        if leftover > 0:
            row_gap += leftover / (rows + 1)
    elif height_limited and not width_limited:
        # leftover in horizontal dimension => distribute among column gaps
        used_width = columns*square_side + (columns - 1)*col_gap
        leftover = squares_area_width - used_width
        if leftover > 0 and columns > 1:
            col_gap += leftover / (columns - 1)

    # 9) Recompute final square_side after gap adjustment
    final_square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns
    final_square_side_y = (squares_area_height - (rows + 1)*row_gap)   / rows
    square_side          = min(final_square_side_x, final_square_side_y)
    if square_side < 0:
        raise ValueError("After gap readjustment, squares still do not fit.")

    # 10) Draw the squares and capture bounding boxes
    squares_bboxes = []
    current_y = squares_top + row_gap
    for r in range(rows):
        current_x = squares_left
        for c in range(columns):
            left   = current_x
            top    = current_y
            right  = current_x + square_side
            bottom = current_y + square_side

            # Draw the square outline
            #draw.rectangle([(left, top), (right, bottom)], outline="black", width=1)

            # Store the bounding box for this square
            squares_bboxes.append((left, top, right, bottom))

            current_x += square_side + col_gap
        current_y += square_side + row_gap

    # 11) Save the template (if you want to see it)
    img.save(out_filename)
    print(f"Saved template '{out_filename}' with {rows}×{columns} squares.")

    return squares_bboxes


from PIL import Image

def place_shapes_onto_template(template_path, output_path, squares_bboxes, shape_paths):
    """
    - `template_path`: Path to the poster_template.png (or an in-memory Image object).
    - `output_path`: Where the final composite should be saved.
    - `squares_bboxes`: List of bounding boxes (left, top, right, bottom).
    - `shape_paths`: List of PNGs to be placed. Must be the same length or shorter than squares_bboxes.
    """
    # 1) Open the template as background
    base_img = Image.open(template_path).convert("RGBA")

    # 2) For each shape, place it into the corresponding bounding box
    for bbox, shape_path in zip(squares_bboxes, shape_paths):
        # (left, top, right, bottom)
        left, top, right, bottom = bbox
        box_width  = int(right - left)
        box_height = int(bottom - top)

        # Open the shape
        shape_img = Image.open(shape_path).convert("RGBA")
        # Resize shape to the bounding box
        shape_resized = shape_img.resize((box_width, box_height), Image.Resampling.LANCZOS)

        # Paste the shape onto the template
        base_img.paste(shape_resized, (int(left), int(top)), mask=shape_resized)

    # 3) Save the final poster
    base_img.save(output_path,dpi=(300,300))
    print(f"Saved final poster with shapes to '{output_path}'.")


# 1) Make the template and get bounding boxes
bboxes = create_poster_template_and_get_squares(
    out_filename="poster_template.png",
    rows=2,
    columns=2
)

# 2) Suppose we have 25 “shape of a story” PNGs in a list
shape_of_story_pngs = [
    "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_15x15_char_sans_48.png",
    "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_15x15_char_sans_48.png",
    "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_15x15_char_sans_48.png",
    "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_shapes/the_old_man_and_the_sea_15x15_char_sans_48.png"
]

# 3) Overlay them
place_shapes_onto_template(
    template_path="poster_template.png",
    output_path="final_poster_with_shapes.png",
    squares_bboxes=bboxes,
    shape_paths=shape_of_story_pngs
)
