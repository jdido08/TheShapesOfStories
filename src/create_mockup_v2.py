# batch_mockups.py
from PIL import Image, ImageOps, ImageDraw
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math, os

# ---------------------------- Template registry ----------------------------

# Corners are normalized floats in [0,1], as (x,y) pairs in TL, TR, BR, BL order.
# This makes a template portable across resolutions of the same image.

@dataclass
class Window:
    name: str
    corners_norm: List[Tuple[float, float]]  # [(x,y)*4], normalized 0..1

@dataclass
class Template:
    id: str
    path: str                       # file path to the background/mockup image
    windows: List[Window] = field(default_factory=list)

TEMPLATES: Dict[str, Template] = {
    # --- STRAIGHT-ON wall (matted), inner mat window for 8×10 in an 11×14 frame ---
    "wall_matted_8x10": Template(
        id="wall_matted_8x10",
        path="/Users/you/…/framed-wall-mockup-template-for-8x10-poster.png",
        windows=[
            Window(
                name="print",
                # Example derived from your coords: (603,234)-(930,654) on a 1536×1024 sample,
                # translate to normalized by (x/W, y/H). Replace with YOUR image dims & corners.
                corners_norm=[(603/1536,234/1024), (930/1536,234/1024),
                              (930/1536,654/1024), (603/1536,654/1024)]
            )
        ]
    ),

    # --- STRAIGHT-ON wall (matted), inner mat window for 11×14 in a 16×20 frame ---
    "wall_matted_11x14": Template(
        id="wall_matted_11x14",
        path="/Users/you/…/framed-wall-mockup-template-for-11x14-poster.png",
        windows=[
            Window(
                name="print",
                # PLACEHOLDER: measure once, convert to normalized.
                corners_norm=[(0.390,0.230),(0.610,0.230),(0.610,0.755),(0.390,0.755)]
            )
        ]
    ),

    # --- TABLE vignette (no mat) — ANGLED: slight right-lean frame (8×10) ---
    "table_no_mat_8x10": Template(
        id="table_no_mat_8x10",
        path="/Users/you/…/table-nomat-8x10.png",
        windows=[
            Window(
                name="print",
                # Example ANGLED coords (you’ll measure yours):
                # TL, TR, BR, BL in normalized space, forming a slight trapezoid.
                corners_norm=[(0.345,0.180),(0.645,0.160),(0.625,0.650),(0.330,0.675)]
            )
        ]
    ),

    # --- TABLE vignette (no mat) — ANGLED: slight right-lean frame (11×14) ---
    "table_no_mat_11x14": Template(
        id="table_no_mat_11x14",
        path="/Users/you/…/table-nomat-11x14.png",
        windows=[
            Window(
                name="print",
                corners_norm=[(0.320,0.165),(0.690,0.155),(0.670,0.725),(0.305,0.740)]
            )
        ]
    ),

    # --- POSTER ONLY flat-lay 8×10 (no frame) ---
    "flatlay_8x10": Template(
        id="flatlay_8x10",
        path="/Users/you/…/poster-flatlay-8x10.png",
        windows=[
            Window(
                name="sheet",
                corners_norm=[(0.265,0.140),(0.735,0.140),(0.735,0.860),(0.265,0.860)]
            )
        ]
    ),

    # --- POSTER ONLY flat-lay 11×14 (no frame) ---
    "flatlay_11x14": Template(
        id="flatlay_11x14",
        path="/Users/you/…/poster-flatlay-11x14.png",
        windows=[
            Window(
                name="sheet",
                corners_norm=[(0.260,0.120),(0.740,0.120),(0.740,0.880),(0.260,0.880)]
            )
        ]
    ),

    # --- TWO-SIZE COMPARISON (both matted) ---
    "two_size_comparison": Template(
        id="two_size_comparison",
        path="/Users/you/…/two-size-comparison.png",
        windows=[
            Window(
                name="left_11x14",
                corners_norm=[(0.160,0.220),(0.455,0.220),(0.455,0.780),(0.160,0.780)]
            ),
            Window(
                name="right_8x10",
                corners_norm=[(0.545,0.260),(0.810,0.260),(0.810,0.740),(0.545,0.740)]
            ),
        ]
    ),

    # --- UNIFORM 3-UP gallery wall (all 8×10 → 11×14 matted) ---
    "uniform_three_up": Template(
        id="uniform_three_up",
        path="/Users/you/…/three-up-gallery.png",
        windows=[
            Window(name="left",   corners_norm=[(0.115,0.260),(0.315,0.260),(0.315,0.740),(0.115,0.740)]),
            Window(name="center", corners_norm=[(0.415,0.260),(0.615,0.260),(0.615,0.740),(0.415,0.740)]),
            Window(name="right",  corners_norm=[(0.715,0.260),(0.915,0.260),(0.915,0.740),(0.715,0.740)]),
        ]
    ),
}

# ---------------------------- Core compositor ----------------------------

def _is_axis_aligned(px):
    (x1,y1),(x2,y2),(x3,y3),(x4,y4) = px
    return y1==y2 and y3==y4 and x1==x4 and x2==x3

def _px_from_norm(w, h, corners_norm):
    return [(int(round(x*w)), int(round(y*h))) for (x,y) in corners_norm]

def _width_height_from_corners(px):
    (x1,y1),(x2,y2),(x3,y3),(x4,y4) = px
    W = int(round(math.hypot(x2-x1, y2-y1)))
    H = int(round(math.hypot(x4-x1, y4-y1)))
    return W, H

def _linsolve(A, B):
    n = len(A)
    for i in range(n):
        max_row = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[max_row] = A[max_row], A[i]
        B[i], B[max_row] = B[max_row], B[i]
        for k in range(i+1, n):
            c = -A[k][i]/A[i][i]
            for j in range(i, n):
                A[k][j] = 0 if i==j else A[k][j] + c*A[i][j]
            B[k] += c*B[i]
    x = [0]*n
    for i in range(n-1,-1,-1):
        x[i] = B[i]/A[i][i]
        for k in range(i-1,-1,-1):
            B[k] -= A[k][i]*x[i]
    return x

def _find_coeffs(src_quad, dst_quad):
    M, B = [], []
    for (x_src, y_src), (x_dst, y_dst) in zip(src_quad, dst_quad):
        M.append([x_src, y_src, 1, 0, 0, 0, -x_dst*x_src, -x_dst*y_src])
        M.append([0, 0, 0, x_src, y_src, 1, -y_dst*x_src, -y_dst*y_src])
        B.extend([x_dst, y_dst])
    return _linsolve(M, B)

def place_art(mockup_img, art_img, dest_px, bleed_px=2, fit_mode="cover"):
    """
    Paste art_img into quadrilateral window dest_px on mockup_img.
    fit_mode: "cover" (default) or "contain" inside window before warp/paste.
    """
    mock = mockup_img.convert("RGBA")
    art  = art_img.convert("RGBA")

    if _is_axis_aligned(dest_px):
        W, H = _width_height_from_corners(dest_px)
        # fit/cover while preserving aspect ratio
        size = (W + 2*bleed_px, H + 2*bleed_px)
        if fit_mode == "contain":
            fitted = ImageOps.contain(art, size, method=Image.Resampling.LANCZOS)
        else:
            fitted = ImageOps.fit(art, size, method=Image.Resampling.LANCZOS, centering=(0.5,0.5))
        x0, y0 = dest_px[0]
        paste_xy = (x0 - bleed_px, y0 - bleed_px)
        mock.paste(fitted, paste_xy, fitted)
        return mock

    # Perspective warp for angled/table shots
    src = [(0,0), (art.width,0), (art.width,art.height), (0,art.height)]
    coeffs = _find_coeffs(src, dest_px)
    warped = art.transform(mock.size, Image.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    mask = Image.new("L", mock.size, 0)
    ImageDraw.Draw(mask).polygon(dest_px, fill=255)
    return Image.composite(warped, mock, mask)

def compose_to_file(template: Template, window_name_to_art: Dict[str, str],
                    out_path: str, bleed_px=2, fit_mode="cover",
                    quality=92, dpi=(300,300)):
    bg = Image.open(template.path).convert("RGBA")
    W, H = bg.size

    # Paste each window
    composed = bg
    for win in template.windows:
        if win.name not in window_name_to_art:
            continue
        art_path = window_name_to_art[win.name]
        art = Image.open(art_path)

        dest_px = _px_from_norm(W, H, win.corners_norm)
        composed = place_art(composed, art, dest_px, bleed_px=bleed_px, fit_mode=fit_mode)

    composed = composed.convert("RGB")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    composed.save(out_path, "JPEG", quality=quality, subsampling=0, optimize=True, progressive=True, dpi=dpi)

def preview_windows(template: Template, out_path: str, stroke_px=3):
    """Quick sanity-check: draw window outlines on the template."""
    bg = Image.open(template.path).convert("RGBA")
    W, H = bg.size
    overlay = Image.new("RGBA", bg.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay, "RGBA")
    for win in template.windows:
        poly = _px_from_norm(W, H, win.corners_norm)
        d.line(poly + [poly[0]], fill=(255,0,0,160), width=stroke_px)
        # draw corners
        for (x,y) in poly:
            d.ellipse((x-4,y-4,x+4,y+4), fill=(0,0,255,200))
    Image.alpha_composite(bg, overlay).convert("RGB").save(out_path, "JPEG", quality=90)

# ---------------------------- Batch runner ----------------------------

@dataclass
class Job:
    template_id: str
    out_path: str
    window_name_to_art: Dict[str, str]  # e.g. {"print": "/path/to/art_8x10.png"}

def run_batch(jobs: List[Job], bleed_px=2, fit_mode="cover"):
    for j in jobs:
        tpl = TEMPLATES[j.template_id]
        compose_to_file(tpl, j.window_name_to_art, j.out_path,
                        bleed_px=bleed_px, fit_mode=fit_mode)

# ---------------------------- Example usage ----------------------------
if __name__ == "__main__":
    # Preview outlines once (optional):
    # preview_windows(TEMPLATES["two_size_comparison"], "DEBUG_two_size_preview.jpg")

    jobs = [
        # 8x10 variant
        Job("wall_matted_8x10",
            out_path="out/gatsby_8x10_wall_matted.jpg",
            window_name_to_art={"print": "/Users/you/…/gatsby_8x10.png"}),

        Job("flatlay_8x10",
            out_path="out/gatsby_8x10_flatlay.jpg",
            window_name_to_art={"sheet": "/Users/you/…/gatsby_8x10.png"}),

        Job("table_no_mat_8x10",
            out_path="out/gatsby_8x10_table_nomatt.jpg",
            window_name_to_art={"print": "/Users/you/…/gatsby_8x10.png"}),

        # 11x14 variant
        Job("wall_matted_11x14",
            out_path="out/gatsby_11x14_wall_matted.jpg",
            window_name_to_art={"print": "/Users/you/…/gatsby_11x14.png"}),

        Job("flatlay_11x14",
            out_path="out/gatsby_11x14_flatlay.jpg",
            window_name_to_art={"sheet": "/Users/you/…/gatsby_11x14.png"}),

        Job("table_no_mat_11x14",
            out_path="out/gatsby_11x14_table_nomatt.jpg",
            window_name_to_art={"print": "/Users/you/…/gatsby_11x14.png"}),

        # Shared images
        Job("two_size_comparison",
            out_path="out/gatsby_twosize.jpg",
            window_name_to_art={
                "left_11x14": "/Users/you/…/gatsby_11x14.png",
                "right_8x10": "/Users/you/…/gatsby_8x10.png"
            }),

        Job("uniform_three_up",
            out_path="out/gatsby_threeup.jpg",
            window_name_to_art={
                "left":   "/Users/you/…/gatsby_8x10_alt1.png",
                "center": "/Users/you/…/gatsby_8x10.png",
                "right":  "/Users/you/…/gatsby_8x10_alt2.png",
            }),
    ]

    run_batch(jobs, bleed_px=2, fit_mode="cover")
