# create_mockup.py
# -----------------
# Paste an artwork image into the inner mat opening of the mockup
# image "11x14_1_frame_on_table" (straight-on; no keystone).
#
# Just set:
#   BASE_PATH  -> your mockup image path
#   ART_PATH   -> your design image path
#   OUT_PATH   -> where to save the result
#
# Advanced: If you use a different-resolution copy of this mockup,
# the code scales the opening rectangle from the 1024×1024 reference.

from PIL import Image, ImageOps, ImageDraw

# --- USER INPUTS -------------------------------------------------------------
BASE_PATH = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_table.jpeg"  # mockup image
ART_PATH  = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-moby-dick_protagonist-ishmael_product-print_size-11x14_line-type-char_background-color-#1B2E4B_font-color-#F5E6D3_border-color-#FFFFFF_font-Alegreya_title-display-yes.png"              # your artwork
OUT_PATH  = "final_mockup_test_6.png"            # output


# Safety inset to hide the mat bevel (in pixels for the 1024×1024 reference);
# will scale with image size.
BLEED_REF_PX = 2

# Debug: also save a version with a thin rectangle drawn over the opening
SAVE_DEBUG_OVERLAY = False
DEBUG_PATH = OUT_PATH.replace(".png", "_debug.png").replace(".jpg", "_debug.jpg")

# --- TEMPLATE-SPECIFIC CALIBRATION (do not change unless you re-measure) -----
# Coordinates measured on the 1024×1024 reference mockup.
REF_W, REF_H = 1024, 1024

# Inner mat opening (the area where your print should appear)
# (left, top, right, bottom) in the 1024×1024 reference
#OPENING_BOX_REF = (131, 383, 482, 857)
OPENING_BOX_REF = (152, 401, 483, 857)


# If you ever want to cover closer to the inner mat edge:
# OUTER_EDGE_BOX_REF = (148, 399, 498, 875)
# -----------------------------------------------------------------------------


def scale_box(box, base_w, base_h, ref_w=REF_W, ref_h=REF_H):
    """Scale a (l,t,r,b) box from reference size to the actual base image size."""
    lx, ty, rx, by = box
    sx = base_w / float(ref_w)
    sy = base_h / float(ref_h)
    return (
        int(round(lx * sx)),
        int(round(ty * sy)),
        int(round(rx * sx)),
        int(round(by * sy)),
    )


def paste_into_opening(base_img, art_img, opening_box, bleed_px=0):
    """Fit art into opening_box with optional inset (bleed_px) and paste."""
    l, t, r, b = opening_box
    # Apply safety inset
    l += bleed_px
    t += bleed_px
    r -= bleed_px
    b -= bleed_px

    w, h = max(1, r - l), max(1, b - t)  # guard against rounding

    # Fit art to exactly fill the opening while preserving aspect
    fitted = ImageOps.fit(art_img, (w, h), method=Image.LANCZOS)

    # Paste (handles alpha automatically if art has transparency)
    base_img.paste(fitted, (l, t), fitted if fitted.mode == "RGBA" else None)
    return base_img


def draw_debug_overlay(img, box):
    """Draw a 1px rectangle on a copy for visual verification."""
    dbg = img.copy()
    draw = ImageDraw.Draw(dbg)
    draw.rectangle(box, outline=(255, 0, 255))
    return dbg


def main():
    base = Image.open(BASE_PATH).convert("RGBA")
    art  = Image.open(ART_PATH).convert("RGBA")

    # Scale opening box and bleed for the actual mockup size
    opening_box = scale_box(OPENING_BOX_REF, base.width, base.height)
    avg_scale = (base.width / REF_W + base.height / REF_H) / 2.0
    bleed_px = max(1, int(round(BLEED_REF_PX * avg_scale)))

    if SAVE_DEBUG_OVERLAY:
        dbg = draw_debug_overlay(base, opening_box)
        dbg.save(DEBUG_PATH)

    result = paste_into_opening(base, art, opening_box, bleed_px=bleed_px)
    # Save as PNG to preserve quality; change to .jpg if you prefer
    result.convert("RGB").save(OUT_PATH, quality=95)
    print(f"Saved mockup → {OUT_PATH}")


if __name__ == "__main__":
    main()
