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
    row_gap=10,        # vertical gap between rows
    col_gap=10         # horizontal gap between columns
):
    """
    Creates a poster with:
      - A top title box (title_height tall).
      - Below that, a fixed rows×columns grid of squares.
        * All squares are perfect squares (same width & height).
        * The entire bounding box (below the title) is attempted to be filled
          both horizontally AND vertically if the aspect ratio matches.
        * There's row_gap space between each row,
          and also one row_gap from the title to the first row.
        * There's col_gap space between squares in the same row.
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

    # We want:
    #   columns squares + (columns-1)*col_gap = squares_area_width
    #   rows squares   + (rows+1)*row_gap to fit in squares_area_height
    #
    # But also we want "perfect squares," so let's figure out the square size 
    # from BOTH horizontal and vertical constraints, then pick the smaller 
    # to ensure we don't overflow in either dimension.

    # Horizontal side if we fill exactly left-to-right:
    # total squares + gaps = squares_area_width
    # columns*square_side + (columns-1)*col_gap = squares_area_width
    # => square_side_x = (squares_area_width - (columns-1)*col_gap) / columns
    square_side_x = (
        squares_area_width - (columns - 1) * col_gap
    ) / columns

    # Vertical side if we want to fill top-to-bottom, allowing for:
    #   - a row_gap above the first row
    #   - a row_gap between each pair of rows
    #   - a row_gap below the last row
    #
    # So total vertical used = rows*square_side + (rows+1)*row_gap
    # We want that to be <= squares_area_height.
    # => square_side_y = (squares_area_height - (rows+1)*row_gap) / rows
    square_side_y = (
        squares_area_height - (rows + 1) * row_gap
    ) / rows

    # Pick the smaller side so we never overflow
    square_side = min(square_side_x, square_side_y)

    # If square_side is negative (meaning we can’t fit), clamp to 0 or raise an error
    if square_side < 0:
        raise ValueError(
            "Not enough space to fit the squares with the given row_gap/col_gap."
        )

    # 6) Now place the rows
    # The top of the first row is squares_top + row_gap
    # Each row we move down by square_side + row_gap
    # We might not fill the entire height if square_side < square_side_y
    current_y = squares_top + row_gap

    for r in range(rows):
        # Left edge of the first square in this row
        current_x = squares_left
        for c in range(columns):
            left   = current_x
            top    = current_y
            right  = current_x + square_side
            bottom = current_y + square_side

            # Draw the square
            draw.rectangle([(left, top), (right, bottom)],
                           outline="black", width=1)

            # Move to the next column
            current_x += square_side + col_gap

        # After finishing this row, move down for the next row
        current_y += square_side + row_gap

    # 7) Save the result
    img.save(out_filename)
    print(f"Saved '{out_filename}' with {rows} rows × {columns} columns of squares.")


# --- Example usage ---
if __name__ == "__main__":
    # Suppose we want 5 rows × 10 columns = 50 squares
    create_poster_template_fixed_grid(
        out_filename="poster_fixed_grid.png",
        width=600,         # scaled-down test
        height=900,
        margin=25,
        title_height=72,
        rows=12,
        columns=12,
        row_gap=10,
        col_gap=10
    )
