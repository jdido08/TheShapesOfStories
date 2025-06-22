# poster_layout_templates.py

poster_layout_templates = {
    # --- 2 Stories ---
    "stories2_horizontal_split": {
        "description": "Two stories side-by-side, splitting the poster horizontally.",
        "num_stories": 2,
        "base_rows": 1,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
        ]
    },
    "stories2_vertical_split": {
        "description": "Two stories stacked, splitting the poster vertically.",
        "num_stories": 2,
        "base_rows": 2,
        "base_cols": 1,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 1},
        ]
    },

    # --- 3 Stories ---
    "stories3_row": {
        "description": "Three stories in a single row.",
        "num_stories": 3,
        "base_rows": 1,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2},
        ]
    },
    "stories3_column": {
        "description": "Three stories in a single column.",
        "num_stories": 3,
        "base_rows": 3,
        "base_cols": 1,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2},
        ]
    },
    "stories3_hero_left_two_stacked_right": {
        "description": "One large story on the left, two smaller stories stacked on the right.",
        "num_stories": 3,
        "base_rows": 2,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 2, 'col_span': 1, 'content_index': 0}, # Hero Left
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Top Right
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Bottom Right
        ]
    },
    "stories3_hero_top_two_bottom": {
        "description": "One large story on the top, two smaller stories side-by-side below.",
        "num_stories": 3,
        "base_rows": 2,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 0}, # Hero Top
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Bottom Left
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Bottom Right
        ]
    },

    # --- 4 Stories ---
     "stories4_4x1_grid": {
        "description": "Four stories in a 4x1 grid.",
        "num_stories": 4,
        "base_rows": 4,
        "base_cols": 1,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            {'base_row': 3, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 3},
        ]
    },
    "stories4_2x2_grid": {
        "description": "Four stories in a 2x2 grid.",
        "num_stories": 4,
        "base_rows": 2,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 3},
        ]
    },
    "stories4_hero_left_three_stacked_right": {
        "description": "One tall story on the left, three smaller stories stacked on the right.",
        "num_stories": 4,
        "base_rows": 3,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 3, 'col_span': 1, 'content_index': 0}, # Hero Left
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Top Right
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Mid Right
            {'base_row': 2, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Bottom Right
        ]
    },
     "stories4_hero_top_three_bottom_row": {
        "description": "One wide story on top, three smaller stories in a row below.",
        "num_stories": 4,
        "base_rows": 2,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 3, 'content_index': 0}, # Hero Top
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Bottom Left
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Bottom Mid
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Bottom Right
        ]
    },

    # --- 5 Stories ---
    "stories5_pinwheel_center_hero": {
        "description": "One story in the center, four stories around it (pinwheel style). All cells are 1x1 in a 3x3 base grid.",
        "num_stories": 5,
        "base_rows": 3,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 0}, # Center
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Top Middle
            {'base_row': 2, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Bottom Middle
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Middle Left
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # Middle Right
        ]
    },
    "stories5_hero_top_left_L_shape": {
        "description": "One large 2x2 story top-left, with four 1x1 stories forming an L-shape around it (bottom and right).",
        "num_stories": 5,
        "base_rows": 3,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 2, 'col_span': 2, 'content_index': 0}, # Hero (2x2)
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Top Right
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Mid Right
            {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Bottom Left
            {'base_row': 2, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # Bottom Mid
        ]
    },
    "stories5_two_top_three_bottom": {
        "description": "Two wider stories in the top row, three narrower stories in the bottom row. Uses a 2x6 base grid.",
        "num_stories": 5,
        "base_rows": 2,
        "base_cols": 6,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 3, 'content_index': 0}, # Top Left (half width)
            {'base_row': 0, 'base_col': 3, 'row_span': 1, 'col_span': 3, 'content_index': 1}, # Top Right (half width)
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 2}, # Bottom Left (third width)
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 2, 'content_index': 3}, # Bottom Mid (third width)
            {'base_row': 1, 'base_col': 4, 'row_span': 1, 'col_span': 2, 'content_index': 4}, # Bottom Right (third width)
        ]
    },

    # --- 6 Stories ---
    "stories6_2x3_grid": {
        "description": "Six stories in a 2x3 grid (2 rows, 3 columns).",
        "num_stories": 6,
        "base_rows": 2,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 3},
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 4},
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 5},
        ]
    },
    "stories6_3x2_grid": {
        "description": "Six stories in a 3x2 grid (3 rows, 2 columns).",
        "num_stories": 6,
        "base_rows": 3,
        "base_cols": 2,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 3},
            {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 4},
            {'base_row': 2, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 5},
        ]
    },
    "stories6_two_wide_left_four_regular_right": {
        "description": "Two wide stories stacked on the left, four regular-width stories in a 2x2 grid on the right. Uses a 2x4 base grid.",
        "num_stories": 6,
        "base_rows": 2,
        "base_cols": 4,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 0}, # Wide Top Left
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 1}, # Wide Bottom Left
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Regular TR1
            {'base_row': 0, 'base_col': 3, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Regular TR2
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # Regular BR1
            {'base_row': 1, 'base_col': 3, 'row_span': 1, 'col_span': 1, 'content_index': 5}, # Regular BR2
        ]
    },

    # --- 7 Stories ---
    "stories7_complex_hero_center_tall": {
        "description": "Three 1x1 stories on top row, three tall (2-row span) stories in middle, one wide (3-col span) story on bottom. Uses a 4x3 base grid.",
        "num_stories": 7,
        "base_rows": 4,
        "base_cols": 3,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0}, # Top Left
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1}, # Top Middle
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Top Right
            {'base_row': 1, 'base_col': 0, 'row_span': 2, 'col_span': 1, 'content_index': 3}, # Left Mid Tall
            {'base_row': 1, 'base_col': 1, 'row_span': 2, 'col_span': 1, 'content_index': 4}, # Center Hero Tall
            {'base_row': 1, 'base_col': 2, 'row_span': 2, 'col_span': 1, 'content_index': 5}, # Right Mid Tall
            {'base_row': 3, 'base_col': 0, 'row_span': 1, 'col_span': 3, 'content_index': 6}, # Bottom Wide
        ]
    },

    # --- 8 Stories ---
    "stories8_2x4_grid": {
        "description": "Eight stories in a 2x4 grid (2 rows, 4 columns).",
        "num_stories": 8,
        "base_rows": 2,
        "base_cols": 4,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            {'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            {'base_row': 0, 'base_col': 3, 'row_span': 1, 'col_span': 1, 'content_index': 3},
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 4},
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 5},
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 6},
            {'base_row': 1, 'base_col': 3, 'row_span': 1, 'col_span': 1, 'content_index': 7},
        ]
    },
    "stories8_4x2_grid": {
        "description": "Eight stories in a 4x2 grid (4 rows, 2 columns).",
        "num_stories": 8,
        "base_rows": 4,
        "base_cols": 2,
        "grid_template": [
            {'base_row': i // 2, 'base_col': i % 2, 'row_span': 1, 'col_span': 1, 'content_index': i} for i in range(8) # Corrected for 4x2
            # Explicitly:
            # Row 0
            #{'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 0},
            #{'base_row': 0, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 1},
            # Row 1
            #{'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2},
            #{'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 3},
            # Row 2
            #{'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 4},
            #{'base_row': 2, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 5},
            # Row 3
            #{'base_row': 3, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 6},
            #{'base_row': 3, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 7},
        ]
    },
    "stories8_2_4_2_rows": {
        "description": "Eight stories: 2 wide on top row, 4 regular in middle row, 2 wide on bottom row. Uses a 3x4 base grid.",
        "num_stories": 8,
        "base_rows": 3,
        "base_cols": 4,
        "grid_template": [
            {'base_row': 0, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 0}, # Top Left Wide
            {'base_row': 0, 'base_col': 2, 'row_span': 1, 'col_span': 2, 'content_index': 1}, # Top Right Wide
            {'base_row': 1, 'base_col': 0, 'row_span': 1, 'col_span': 1, 'content_index': 2}, # Mid R1C1
            {'base_row': 1, 'base_col': 1, 'row_span': 1, 'col_span': 1, 'content_index': 3}, # Mid R1C2
            {'base_row': 1, 'base_col': 2, 'row_span': 1, 'col_span': 1, 'content_index': 4}, # Mid R1C3
            {'base_row': 1, 'base_col': 3, 'row_span': 1, 'col_span': 1, 'content_index': 5}, # Mid R1C4
            {'base_row': 2, 'base_col': 0, 'row_span': 1, 'col_span': 2, 'content_index': 6}, # Bot Left Wide
            {'base_row': 2, 'base_col': 2, 'row_span': 1, 'col_span': 2, 'content_index': 7}, # Bot Right Wide
        ]
    },

    # --- 9 Stories ---
    "stories9_3x3_grid": {
        "description": "Nine stories in a 3x3 grid.",
        "num_stories": 9,
        "base_rows": 3,
        "base_cols": 3,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 3 + c}
            for r in range(3) for c in range(3)
        ]
    },

    # --- 12 Stories ---
    "stories12_3x4_grid": {
        "description": "Twelve stories in a 3x4 grid (3 rows, 4 columns).",
        "num_stories": 12,
        "base_rows": 3,
        "base_cols": 4,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 4 + c}
            for r in range(3) for c in range(4)
        ]
    },
    "stories12_4x3_grid": {
        "description": "Twelve stories in a 4x3 grid (4 rows, 3 columns).",
        "num_stories": 12,
        "base_rows": 4,
        "base_cols": 3,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 3 + c}
            for r in range(4) for c in range(3)
        ]
    },
        # --- 15 Stories ---
    "stories15_3x5_grid" : {
        "description": "Fifteen stories in a 3x5 grid (3 rows, 5 columns).",
        "num_stories": 15,
        "base_rows": 3,
        "base_cols": 5,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 5 + c}
            for r in range(3) for c in range(5)
        ]
    },
    "stories15_5x3_grid" : {
        "description": "Fifteen stories in a 5x3 grid (5 rows, 3 columns).",
        "num_stories": 15,
        "base_rows": 5,
        "base_cols": 3,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 3 + c}
            for r in range(5) for c in range(3)
        ]
    },

    # --- 20 Stories ---
    "stories20_4x5_grid" : {
        "description": "Twenty stories in a 4x5 grid (4 rows, 5 columns).",
        "num_stories": 20,
        "base_rows": 4,
        "base_cols": 5,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 5 + c}
            for r in range(4) for c in range(5)
        ]
    },
    "stories20_5x4_grid" : {
        "description": "Twenty stories in a 5x4 grid (5 rows, 4 columns).",
        "num_stories": 20,
        "base_rows": 5,
        "base_cols": 4,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 4 + c}
            for r in range(5) for c in range(4)
        ]
    },

    # --- 25 Stories ---
    "stories25_5x5_grid" : {
        "description": "Twenty-five stories in a 5x5 grid.",
        "num_stories": 25,
        "base_rows": 5,
        "base_cols": 5,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 5 + c}
            for r in range(5) for c in range(5)
        ]
    },

    # --- 50 Stories ---
    "stories50_5x10_grid" : {
        "description": "Fifty stories in a 5x10 grid (5 rows, 10 columns). Good for landscape posters.",
        "num_stories": 50,
        "base_rows": 5,
        "base_cols": 10,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 10 + c}
            for r in range(5) for c in range(10)
        ]
    },
    "stories50_10x5_grid" : {
        "description": "Fifty stories in a 10x5 grid (10 rows, 5 columns). Good for portrait posters.",
        "num_stories": 50,
        "base_rows": 10,
        "base_cols": 5,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 5 + c}
            for r in range(10) for c in range(5)
        ]
    },

    # --- 100 Stories ---
    "stories100_10x10_grid" : {
        "description": "One hundred stories in a 10x10 grid. Most balanced for large counts.",
        "num_stories": 100,
        "base_rows": 10,
        "base_cols": 10,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 10 + c}
            for r in range(10) for c in range(10)
        ]
    },
    "stories100_5x20_grid" : {
        "description": "One hundred stories in a 5x20 grid (5 rows, 20 columns). Very wide, for panoramic landscape posters.",
        "num_stories": 100,
        "base_rows": 5,
        "base_cols": 20,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 20 + c}
            for r in range(5) for c in range(20)
        ]
    },
    "stories100_20x5_grid" : {
        "description": "One hundred stories in a 20x5 grid (20 rows, 5 columns). Very tall, for panoramic portrait posters.",
        "num_stories": 100,
        "base_rows": 20,
        "base_cols": 5,
        "grid_template": [
            {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 5 + c}
            for r in range(20) for c in range(5)
        ]
    },
}

# Correcting the list comprehension for stories8_4x2_grid
poster_layout_templates["stories8_4x2_grid"]["grid_template"] = [
    {'base_row': r, 'base_col': c, 'row_span': 1, 'col_span': 1, 'content_index': r * 2 + c}
    for r in range(4) for c in range(2)
]


if __name__ == '__main__':
    # This is an example of how you might use these templates with your existing functions.
    # You would need to have your poster_creator.py functions (create_layout_preview,
    # calculate_cell_content_size, create_poster) available in the same scope or imported.

    # --- How to use a template ---

    # 1. Choose a template
    chosen_template_name = "stories5_hero_top_left_L_shape"
    template_details = poster_layout_templates[chosen_template_name]

    print(f"Using template: {chosen_template_name} - {template_details['description']}")
    print(f"  Expected number of stories: {template_details['num_stories']}")
    print(f"  Base grid: {template_details['base_rows']} rows x {template_details['base_cols']} cols")

    # 2. Define poster parameters (these are examples)
    poster_width_inches = 18
    poster_height_inches = 24
    poster_dpi = 72 # Lower for preview, 300 for print
    poster_margin_inches = 1.0
    poster_spacing_inches = 0.5
    output_folder = "./layout_previews/" # Make sure this folder exists
    import os
    os.makedirs(output_folder, exist_ok=True)

    # 3. Generate a layout preview (if you have create_layout_preview function)
    # Assuming create_layout_preview is defined as in your provided code
    # from poster_creator import create_layout_preview, calculate_cell_content_size # If in separate file

    # Example: Call create_layout_preview
    # create_layout_preview(
    #     poster_width_in=poster_width_inches,
    #     poster_height_in=poster_height_inches,
    #     output_path=os.path.join(output_folder, f"preview_{chosen_template_name}.png"),
    #     base_rows=template_details['base_rows'],
    #     base_cols=template_details['base_cols'],
    #     grid_template=template_details['grid_template'],
    #     dpi=poster_dpi,
    #     margin_in=poster_margin_inches,
    #     spacing_in=poster_spacing_inches,
    #     poster_title=f"Layout: {chosen_template_name.replace('_', ' ').title()}",
    #     # ... other preview parameters
    # )
    print(f"Preview would be saved to: {os.path.join(output_folder, f'preview_{chosen_template_name}.png')}")


    # 4. Calculate required sizes for your individual story shape PNGs
    # Assuming calculate_cell_content_size is defined
    print("\n--- Required content sizes for each cell (at 300 DPI for print) ---")
    for i, cell_def in enumerate(template_details['grid_template']):
        # target_size_px = calculate_cell_content_size(
        #     poster_width_in=poster_width_inches,
        #     poster_height_in=poster_height_inches,
        #     dpi=300, # Target DPI for your story shapes
        #     margin_in=poster_margin_inches,
        #     spacing_in=poster_spacing_inches,
        #     base_rows=template_details['base_rows'],
        #     base_cols=template_details['base_cols'],
        #     cell_row_span=cell_def['row_span'],
        #     cell_col_span=cell_def['col_span']
        # )
        # if target_size_px:
        #     print(f"Cell for content_index {cell_def['content_index']} (Span {cell_def['row_span']}x{cell_def['col_span']}): "
        #           f"Target story shape content size = {target_size_px[0]} x {target_size_px[1]} pixels")
        # else:
        #     print(f"Could not calculate size for cell_def: {cell_def}")
        pass # Placeholder for brevity, uncomment if running with your functions

    # 5. Prepare your story_shape_paths (list of N PNGs, correctly sized)
    #    story_files = ["path/to/story0.png", "path/to/story1.png", ...]
    #    Ensure len(story_files) == template_details['num_stories']

    # 6. Create the actual poster (if you have create_poster function)
    # create_poster(
    #     story_shape_paths=story_files, # Your list of N image paths
    #     poster_width_in=poster_width_inches,
    #     poster_height_in=poster_height_inches,
    #     output_path=os.path.join(output_folder, f"poster_{chosen_template_name}.png"),
    #     base_rows=template_details['base_rows'],
    #     base_cols=template_details['base_cols'],
    #     grid_template=template_details['grid_template'],
    #     dpi=300, # For print quality
    #     margin_in=poster_margin_inches,
    #     spacing_in=poster_spacing_inches,
    #     poster_title="My Awesome Story Poster",
    #     # ... other poster parameters
    # )
    print(f"\nActual poster would use {template_details['num_stories']} story shapes and be saved to: {os.path.join(output_folder, f'poster_{chosen_template_name}.png')}")

    print("\n--- All Available Templates ---")
    for name, details in poster_layout_templates.items():
        print(f"- {name}: {details['description']} (expects {details['num_stories']} stories, {details['base_rows']}x{details['base_cols']} base grid)")





template_name = "stories6_2x3_grid" # Example
my_layout = poster_layout_templates[template_name]

num_expected_stories = my_layout["num_stories"]
base_r = my_layout["base_rows"]
base_c = my_layout["base_cols"]
grid_def = my_layout["grid_template"]