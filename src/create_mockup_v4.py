
# create_mockup.py
# Perspective-safe mockup compositor: auto-detects the inner mat opening
# as a quadrilateral and warps your art into it.
#
# Set BASE_PATH, ART_PATH, OUT_PATH below and run:
#   python create_mockup.py

from PIL import Image, ImageOps, ImageDraw
import numpy as np

# ------------------- USER INPUTS -------------------
BASE_PATH = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_table.jpeg"  # mockup image
ART_PATH  = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-moby-dick_protagonist-ishmael_product-print_size-11x14_line-type-char_background-color-#1B2E4B_font-color-#F5E6D3_border-color-#FFFFFF_font-Alegreya_title-display-yes.png"              # your artwork
OUT_PATH  = "final_mockup_test_6.png"            # output

# Measured on the 1024×1024 reference mockup (TL, TR, BR, BL)
QUAD_REF = [(132, 383), (484, 383), (483, 857), (129, 857)]
REF_SIZE = (1024, 1024)

INSET_PX_REF = 2      # inward safety inset at reference size
SAVE_DEBUG = False    # set True to export an outline overlay

def scale_point(p, base_size, ref_size=REF_SIZE):
    rx, ry = ref_size
    bx, by = base_size
    return (int(round(p[0] * bx / rx)), int(round(p[1] * by / ry)))

def scale_quad(quad, base_size):
    return [scale_point(p, base_size) for p in quad]

def inset_quad(quad, inset_px):
    if inset_px <= 0:
        return quad
    cx = sum(p[0] for p in quad) / 4.0
    cy = sum(p[1] for p in quad) / 4.0
    out = []
    for (x, y) in quad:
        dx, dy = cx - x, cy - y
        d = (dx*dx + dy*dy) ** 0.5 or 1.0
        out.append((int(round(x + inset_px * dx / d)),
                    int(round(y + inset_px * dy / d))))
    return out

def find_coeffs(pa, pb):
    # pa: destination quad (TL,TR,BR,BL); pb: source quad (TL,TR,BR,BL)
    matrix = []
    for (x, y), (u, v) in zip(pa, pb):
        matrix.extend([
            [x, y, 1, 0, 0, 0, -u*x, -u*y],
            [0, 0, 0, x, y, 1, -v*x, -v*y],
        ])
    A = [row[:] for row in matrix]
    B = [u for (u, v) in pb] + [v for (u, v) in pb]
    # small 8×8 solve
    import numpy as np
    return np.linalg.lstsq(np.array(A, float), np.array(B, float), rcond=None)[0].tolist()

def warp_into_quad(base, art, dst_quad):
    bw, bh = base.size
    xs, ys = zip(*dst_quad)
    bb_w, bb_h = max(1, max(xs) - min(xs)), max(1, max(ys) - min(ys))

    # Fit art to bounding box to keep resolution reasonable
    art_fit = ImageOps.fit(art, (bb_w, bb_h), method=Image.LANCZOS)
    src_quad = [(0, 0), (bb_w, 0), (bb_w, bb_h), (0, bb_h)]

    coeffs = find_coeffs(dst_quad, src_quad)
    warped = art_fit.transform((bw, bh), Image.PERSPECTIVE, coeffs, Image.BICUBIC)

    # Polygon mask for crisp edges
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).polygon(dst_quad, fill=255)

    # Composite (use paste with mask to avoid the earlier alpha_composite error)
    base.paste(warped, (0, 0), mask)
    return base

def main():
    base = Image.open(BASE_PATH).convert("RGBA")
    art  = Image.open(ART_PATH).convert("RGBA")

    quad = scale_quad(QUAD_REF, base.size)

    # scale inset to your image size
    inset_scaled = max(1, round(INSET_PX_REF * (base.width / REF_SIZE[0] + base.height / REF_SIZE[1]) / 2))
    quad_in = inset_quad(quad, inset_scaled)

    if SAVE_DEBUG:
        dbg = base.copy()
        d = ImageDraw.Draw(dbg)
        d.polygon(quad, outline=(255, 0, 0))
        d.polygon(quad_in, outline=(0, 255, 0))
        dbg.save(OUT_PATH.replace(".jpg", "_debug.jpg").replace(".png", "_debug.png"))

    out = warp_into_quad(base, art, quad_in)
    out.convert("RGB").save(OUT_PATH, quality=95)
    print("Saved →", OUT_PATH)
    print("Quad (TL,TR,BR,BL):", quad)
    print("Inset quad:", quad_in)

if __name__ == "__main__":
    main()