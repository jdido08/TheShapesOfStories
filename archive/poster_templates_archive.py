import math
from PIL import Image, ImageDraw

def create_poster_template_fixed_grid(
    out_filename="poster_template.png",
    # Canvas size in pixels (scaled to 2:3 for a 24×36 poster).
    width=600,
    height=900,
    margin=25,         # 1-inch margin (scaled)
    title_height=72,   # space at the top for a title
    rows=5,            # total rows of squares
    columns=10,        # total columns of squares
    row_gap=10,        # initial vertical gap between rows
    col_gap=10         # initial horizontal gap between columns
):
    """
    Creates a poster with:
      - A top title box (title_height tall).
      - Below that, a fixed rows×columns grid of squares (perfect squares).
      - We first compute the square side via the usual 'pick the smaller' approach.
      - If we realize we only filled width or height, we adjust the other gap
        to ensure we end up filling the *entire* bounding region in both dimensions.
    """

    # 1) Create a white image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 2) Outline the outer border (for debugging)
    draw.rectangle([(0, 0), (width-1, height-1)], outline="black", width=1)

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

    # -- First pass: compute square_side using the "pick the smaller" logic --

    # Horizontal side if we fill exactly left-to-right:
    # columns*square_side + (columns-1)*col_gap = squares_area_width
    square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns

    # Vertical side if we want to fill top-to-bottom, including one gap above
    # first row + (rows-1) gaps between rows + one gap below last row => rows+1 row gaps
    # rows*square_side + (rows+1)*row_gap = squares_area_height
    square_side_y = (squares_area_height - (rows + 1)*row_gap) / rows

    # Pick the smaller to avoid overflowing
    square_side = min(square_side_x, square_side_y)

    # If square_side is negative => can't fit with initial gaps
    if square_side < 0:
        raise ValueError(
            "Not enough space to fit squares with the given initial row_gap/col_gap."
        )

    # 6) Identify which dimension was limiting
    EPS = 1e-9
    width_limited = abs(square_side - square_side_x) < EPS
    height_limited = abs(square_side - square_side_y) < EPS

    # 7) If width-limited, adjust row_gap to fill the entire height
    if width_limited and not height_limited:
        # We used up all horizontal space exactly, leftover vertical space possibly.
        used_height = rows*square_side + (rows+1)*row_gap
        leftover = squares_area_height - used_height
        if leftover > 0:
            # Distribute leftover among the (rows+1) row gaps
            row_gap += leftover / (rows+1)

    # 8) If height-limited, adjust col_gap to fill the entire width
    elif height_limited and not width_limited:
        used_width = columns*square_side + (columns-1)*col_gap
        leftover = squares_area_width - used_width
        if leftover > 0 and columns > 1:
            col_gap += leftover / (columns-1)

    # 9) If it exactly matches both (perfect ratio), or if it's borderline, 
    # we do nothing more. This code adjusts just one dimension.

    # -- Recalculate the final layout after possible gap adjustment --

    final_square_side_x = (squares_area_width - (columns - 1)*col_gap) / columns
    final_square_side_y = (squares_area_height - (rows + 1)*row_gap) / rows
    final_square_side = min(final_square_side_x, final_square_side_y)

    if final_square_side < 0:
        raise ValueError("After readjusting gaps, we cannot fit squares. Possibly negative gap needed.")

    square_side = final_square_side

    # 10) Draw the squares with the final row_gap/col_gap
    current_y = squares_top + row_gap

    for r in range(rows):
        current_x = squares_left
        for c in range(columns):
            left   = current_x
            top    = current_y
            right  = current_x + square_side
            bottom = current_y + square_side

            draw.rectangle([(left, top), (right, bottom)], outline="black", width=1)
            current_x += square_side + col_gap

        current_y += square_side + row_gap

    # 11) Save the result
    img.save(out_filename)
    square_side_inches = square_side /  300
    print(
        f"Saved '{out_filename}' with {rows} rows × {columns} columns of squares.\n"
        f"Final square side: {square_side_inches} in. , row_gap: {row_gap:.2f}, col_gap: {col_gap:.2f}"
    )


# --- Example usage ---
if __name__ == "__main__":
    # For example, 2x2 squares
    create_poster_template_fixed_grid(
        out_filename="poster_fixed_grid_dynamic_gap_2x2.png",
        width=600,         # scaled-down test
        height=900,
        margin=25,
        title_height=72,
        rows=5,
        columns=5,
        row_gap=10,
        col_gap=10
    )


