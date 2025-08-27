# # Fields I know
# - Printify Product ID
# - Shape Archetype
# - Shape Symbols
# - Font Family
# - Medium
# - Line Type
# - Author
# - Character / Protagonist
# - Story Title

# # Fields I can derive
# - Font Color Name
# - Background Color Name
# - Font Color (Hex)
# - Background Color (Hex)
# - Color (Background/Front Color Combo) ---> NEED TO ADD 
# - Story Slug

# # Field I need LLM 
# - Setting Region
# - Setting Country
# - Language
# - Awards
# - Setting Era
# - Setting Time
# - Setting City
# - Subgenre
# - Publication Year (I might have this )
# - Publication Country
# - Genre
# - Series
# - Universe


#Maybe
# openlib
#   - publishing
#       - first_publish_year
#   - physical_dimensions
#        - number_of_pages_median
#   - subjects_and_characters
#       - subjects
#       - subject_places
#       - subject_times
#   - excerpts
#   - covers
#   - ratings_and_reviews
#   - first_sentence



import webcolors
from webcolors import CSS3_NAMES_TO_HEX

def hex_to_color_name(hex_color: str) -> str:
    """Return exact CSS3 name if available; otherwise the nearest CSS3 name."""
    # exact match first
    try:
        return webcolors.hex_to_name(hex_color, spec='css3')
    except ValueError:
        pass

    # nearest by Euclidean RGB distance
    r, g, b = webcolors.hex_to_rgb(hex_color)  # returns ints 0–255
    best_name, best_dist = None, float('inf')
    for name, hx in CSS3_NAMES_TO_HEX.items():
        cr, cg, cb = webcolors.hex_to_rgb(hx)
        dist = (cr - r)**2 + (cg - g)**2 + (cb - b)**2
        if dist < best_dist:
            best_name, best_dist = name, dist
#     return best_name

# print(hex_to_color_name("#F9D342"))   # -> "gold"
# print(hex_to_color_name("#0A1F3B"))   # -> "midnightblue" (very close to your Gatsby navy)