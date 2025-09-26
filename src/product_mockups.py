# mockup_multi.py
from PIL import Image, ImageDraw, ImageFilter
import os
import itertools
import json, os, tempfile
from PIL import Image, ImageDraw, ImageFilter
import os
import itertools

from dataclasses import dataclass
from typing import Optional, Tuple, List
from PIL import Image, ImageFilter
from PIL.Image import Resampling  # Pillow 10+


### CLIPS FUNCTIONS #####
# ---------- CONFIG DATACLASS ----------

@dataclass
class ClipSpec:
    path: str                       # path to the clip PNG
    pos: Tuple[int, int]            # target position (in base-image pixels)
    size_px: Optional[Tuple[Optional[int], Optional[int]]] = (220, None)
    #   - (width, height), either can be None to preserve aspect ratio.
    rotation_deg: float = 0.0       # rotate overlay before placing
    anchor: str = "center"          # 'center','top_left','top_center','top_right',
                                    # 'center_left','center_right','bottom_left',
                                    # 'bottom_center','bottom_right'
    add_shadow: bool = True
    shadow_offset: Tuple[int, int] = (3, 6)
    shadow_blur: int = 6
    shadow_opacity: int = 110       # 0–255
    trim_transparent_edges: bool = True  # remove extra transparent padding around the clip

# ---------- CORE CLIP HELPERS ----------

def _unsharp_rgb(img: Image.Image, params=(0.5, 180, 0)) -> Image.Image:
    """UnsharpMask on RGB only (keeps alpha edges clean; no light halo)."""
    if img.mode != "RGBA":
        return img.filter(ImageFilter.UnsharpMask(*params))
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(*params))
    return Image.merge("RGBA", (*rgb.split(), a))


_ANCHOR_OFFSETS = {
    "top_left":       lambda w,h: (0, 0),
    "top_center":     lambda w,h: (w//2, 0),
    "top_right":      lambda w,h: (w, 0),
    "center_left":    lambda w,h: (0, h//2),
    "center":         lambda w,h: (w//2, h//2),
    "center_right":   lambda w,h: (w, h//2),
    "bottom_left":    lambda w,h: (0, h),
    "bottom_center":  lambda w,h: (w//2, h),
    "bottom_right":   lambda w,h: (w, h),
}

def _trim_transparent_edges(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img

def _resize_keep_aspect(img: Image.Image, size_px: Tuple[Optional[int], Optional[int]]) -> Image.Image:
    w, h = img.size
    tw, th = size_px
    if tw is None and th is None:
        return img
    if tw is None:
        tw = int(w * (th / h))
    elif th is None:
        th = int(h * (tw / w))
    return img.resize((int(tw), int(th)), Resampling.LANCZOS)

def _make_shadow(img: Image.Image, offset=(3,6), blur=6, opacity=110) -> Tuple[Image.Image, Tuple[int,int]]:
    # Build a blurred alpha-based shadow
    a = img.getchannel("A")
    shadow = Image.new("RGBA", img.size, (0,0,0,0))
    solid = Image.new("RGBA", img.size, (0,0,0,opacity))
    shadow.paste(solid, mask=a)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas = Image.new("RGBA", (img.width + abs(offset[0]), img.height + abs(offset[1])), (0,0,0,0))
    ox, oy = max(offset[0], 0), max(offset[1], 0)
    canvas.alpha_composite(shadow, (ox, oy))
    return canvas, (-ox, -oy)  # how much to shift overlay to align with its shadow


def clip_positions_from_poster_quad(poster_quad, inset_pct=0.06, raise_px=18):
    """
    Returns ((x_left,y_top), (x_right,y_top)) for ClipSpec(anchor='top_center').
    - inset_pct: horizontal inset from the poster edges (as % of poster width)
    - raise_px: how far ABOVE the poster top the clip's TOP should sit.
                This creates a small 'bite' below the top edge like the reference.
    """
    (xL, yT), (xR, _), *_ = poster_quad
    poster_w = xR - xL
    inset = int(round(poster_w * inset_pct))
    x_left  = xL + inset
    x_right = xR - inset
    y_top   = yT - int(round(raise_px))
    return (x_left, y_top), (x_right, y_top)

def overlay_clips_exact(
    base_path: str,
    clips: List[ClipSpec],
    output_path: str,
    supersample: int = 1,                 # 2 gives extra crisp edges; 1 = off
    post_unsharp: tuple = (0.5, 180, 0),  # after rotate/resize (per clip)
    final_unsharp: tuple = (0.4, 120, 1), # gentle pass after downsample
):
    base = Image.open(base_path).convert("RGBA")
    W0, H0 = base.size
    ss = max(1, int(supersample))

    # render larger, then shrink once (optional but recommended)
    if ss > 1:
        base = base.resize((W0 * ss, H0 * ss), Resampling.LANCZOS)

    for spec in clips:
        overlay = Image.open(spec.path).convert("RGBA")
        if spec.trim_transparent_edges:
            overlay = _trim_transparent_edges(overlay)

        # scale to requested size (honor aspect) — scale the target by supersample
        tw, th = spec.size_px
        if tw is not None: tw = int(round(tw * ss))
        if th is not None: th = int(round(th * ss))
        overlay = _resize_keep_aspect(overlay, (tw, th))

        # rotate, then sharpen RGB a touch to recover edge contrast
        if abs(spec.rotation_deg) > 1e-6:
            overlay = overlay.rotate(spec.rotation_deg, expand=True, resample=Resampling.BICUBIC)
        overlay = _unsharp_rgb(overlay, post_unsharp)

        # anchor math (positions scaled by supersample)
        cx, cy = spec.pos
        cx, cy = int(round(cx * ss)), int(round(cy * ss))
        ax, ay = _ANCHOR_OFFSETS[spec.anchor](overlay.width, overlay.height)
        x = int(cx - ax)
        y = int(cy - ay)

        # shadow (optional)
        if spec.add_shadow:
            sh, shift = _make_shadow(overlay, spec.shadow_offset, spec.shadow_blur, spec.shadow_opacity)
            base.alpha_composite(sh, (x + shift[0], y + shift[1]))

        base.alpha_composite(overlay, (x, y))

    # one high-quality downscale + light global sharpen
    if ss > 1:
        base = base.resize((W0, H0), Resampling.LANCZOS)
        base = _unsharp_rgb(base, final_unsharp)

    base.save(output_path, "PNG", optimize=True)
    return output_path


# ---------------------- geometry & transforms ----------------------

def _sanitize_poly(poly, W, H):
    """Return a list of (int,int) tuples clamped to [0..W-1],[0..H-1]."""
    clean = []
    for pt in poly:
        # Accept (x,y) as tuple or list; cast to float->int to be safe
        x, y = pt
        xi = int(round(float(x)))
        yi = int(round(float(y)))
        # clamp to valid canvas so PIL doesn't complain
        xi = 0 if xi < 0 else (W-1 if xi >= W else xi)
        yi = 0 if yi < 0 else (H-1 if yi >= H else yi)
        clean.append((xi, yi))
    return clean

def linsolve(A, B):
    """Simple Gaussian elimination (no numpy)."""
    n = len(A)
    # forward elimination
    for i in range(n):
        # pivot
        max_row = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[max_row] = A[max_row], A[i]
        B[i], B[max_row] = B[max_row], B[i]
        # eliminate below
        for r in range(i+1, n):
            if A[i][i] == 0: continue
            c = -A[r][i] / A[i][i]
            for cidx in range(i, n):
                A[r][cidx] = A[r][cidx] + c * A[i][cidx] if i != cidx else 0
            B[r] += c * B[i]
    # back substitution
    x = [0.0]*n
    for i in range(n-1, -1, -1):
        x[i] = B[i] / A[i][i]
        for r in range(i-1, -1, -1):
            B[r] -= A[r][i] * x[i]
    return x

def find_coeffs(src_pts, dst_pts):
    """
    Perspective coeffs for PIL.Image.transform(PERSPECTIVE).
    src_pts: list[(x,y)] in source image
    dst_pts: list[(x,y)] in destination image
    """
    matrix = []
    for (sx, sy), (dx, dy) in zip(src_pts, dst_pts):
        matrix.append([dx, dy, 1, 0, 0, 0, -dx*sx, -dy*sx])
        matrix.append([0, 0, 0, dx, dy, 1, -dx*sy, -dy*sy])
    A = matrix
    B = []
    for sx, sy in src_pts:
        B.extend([sx, sy])
    res = linsolve(A, B)
    return res  # 8 coeffs

def avg_aspect_from_quad(q):
    """Approximate opening aspect (width/height) from a 4-pt quad (tl,tr,br,bl)."""
    import math
    def dist(a,b): return math.hypot(b[0]-a[0], b[1]-a[1])
    top, bottom = dist(q[0],q[1]), dist(q[3],q[2])
    left, right = dist(q[0],q[3]), dist(q[1],q[2])
    w = 0.5*(top+bottom)
    h = 0.5*(left+right)
    return (w / max(h,1e-6)) if h else 1.0

def rect_to_quad(x, y, w, h):
    return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]

# ---------------------- aspect handling ----------------------

def crop_to_aspect(img, target_aspect):
    W, H = img.size
    src = W / H
    if abs(src - target_aspect) < 1e-6:
        return img
    if src > target_aspect:  # too wide -> crop width
        new_w = int(round(H * target_aspect))
        x0 = (W - new_w) // 2
        return img.crop((x0, 0, x0 + new_w, H))
    else:                     # too tall -> crop height
        new_h = int(round(W / target_aspect))
        y0 = (H - new_h) // 2
        return img.crop((0, y0, W, y0 + new_h))

def fit_to_aspect_canvas(img, target_aspect):
    """Return an RGBA canvas of the target aspect with the image centered (letterbox/pillarbox)."""
    W, H = img.size
    src = W / H
    if abs(src - target_aspect) < 1e-6:
        return img.convert("RGBA")
    # keep the smaller dimension, letterbox the other
    if src > target_aspect:  # too wide -> keep width
        new_w = W
        new_h = int(round(W / target_aspect))
        canvas = Image.new("RGBA", (new_w, new_h), (0,0,0,0))
        y0 = (new_h - H) // 2
        canvas.paste(img.convert("RGBA"), (0, y0))
    else:                    # too tall -> keep height
        new_h = H
        new_w = int(round(H * target_aspect))
        canvas = Image.new("RGBA", (new_w, new_h), (0,0,0,0))
        x0 = (new_w - W) // 2
        canvas.paste(img.convert("RGBA"), (x0, 0))
    return canvas

# ---------------------- compositing helpers ----------------------

def warp_art_into_quad(base_size, art_rgba, quad):
    """
    Warp the art to the quad area on a canvas sized like base.
    Then you can mask it with a polygon and alpha_composite onto the base.
    """
    W,H = base_size
    src_quad = [(0,0),(art_rgba.width,0),(art_rgba.width,art_rgba.height),(0,art_rgba.height)]
    coeffs = find_coeffs(src_quad, quad)
    warped = art_rgba.transform((W,H), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)
    return warped

def polygon_mask(size, poly, feather=0.5):
    W, H = size
    poly_int = _sanitize_poly(poly, W, H)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m, "L").polygon(poly_int, fill=255)
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m

def overlay_inner_lip(base_rgba, quad, width_px=5, feather=1.0):
    W, H = base_rgba.size
    quad_int = _sanitize_poly(quad, W, H)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask, "L")
    pts = quad_int + [quad_int[0]]
    # Some Pillow builds don't support joint=..., so keep it simple:
    d.line(pts, fill=255, width=width_px)
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    overlay = base_rgba.copy()
    overlay.putalpha(mask)
    return Image.alpha_composite(base_rgba, overlay)


# ---------------------- main placement function ----------------------



# ---------------------3x Wall Mockups Product Pool --------------------------

mockup_pool_11x14 = [
    {
        "story_title": "Frankenstein",
        "story_author": "Mary Shelley",
        "bg_hex": "#0A192F",  # navy
        "product_slug": "frankenstein-victor-frankenstein-print-11x14-navy-sky-blue",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/frankenstein-victor-frankenstein-print-11x14-navy-sky-blue.png"
    },
    {
        "story_title": "Romeo and Juliet",
        "story_author": "William Shakespeare",
        "bg_hex": "#4A235A",  # purple (approx)
        "product_slug": "romeo-and-juliet-juliet-print-11x14-purple-gold",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/romeo-and-juliet-juliet-print-11x14-purple-gold.png"
    },
    {
        "story_title": "Dracula",
        "story_author": "Bram Stoker",
        "bg_hex": "#2B090A",  # black
        "product_slug": "dracula-jonathan-harker-print-11x14-black-beige",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/dracula-jonathan-harker-print-11x14-black-beige.png"
    },
    {
        "story_title": "Little Women",
        "story_author": "Louisa May Alcott",
        "bg_hex": "#2D4F3C",  # charcoal
        "product_slug": "little-women-jo-march-print-11x14-charcoal-ivory",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/little-women-jo-march-print-11x14-charcoal-ivory.png"
    },
    {
        "story_title": "The Catcher in the Rye",
        "story_author": "J.D. Salinger",
        "bg_hex": "#2B4C5C",  # charcoal (same as Little Women variant)
        "product_slug": "the-catcher-in-the-rye-holden-caulfield-print-11x14-charcoal-ivory",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/the-catcher-in-the-rye-holden-caulfield-print-11x14-charcoal-ivory.png"
    },
    {
        "story_title": "Dune",
        "story_author": "Frank Herbert",
        "bg_hex": "#D68227",  # orange
        "product_slug": "dune-paul-atreides-print-11x14-orange-charcoal",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/dune-paul-atreides-print-11x14-orange-charcoal.png"
    },
    {
        "story_title": "To Kill a Mockingbird",
        "story_author": "Harper Lee",
        "bg_hex": "#E8DCC4",  # beige
        "product_slug": "to-kill-a-mockingbird-scout-finch-print-11x14-beige-navy",
        "design_image_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/prop_left_and_right_posters/to-kill-a-mockingbird-scout-finch-print-11x14-beige-navy.png"
    }
]


import random, colorsys
from typing import List, Dict, Tuple

# --- helpers ---
def hex_to_hsl(hex_str: str) -> Tuple[float, float, float]:
    h = hex_str.lstrip("#")
    r,g,b = (int(h[i:i+2], 16)/255.0 for i in (0,2,4))
    H,L,S = colorsys.rgb_to_hls(r,g,b)  # colorsys is HLS
    return (H*360.0, S*100.0, L*100.0)  # return as H,S,L

def ang_diff(a: float, b: float) -> float:
    d = abs(a-b) % 360.0
    return d if d <= 180.0 else 360.0 - d

def color_complement_score(center_hex: str, cand_hex: str) -> float:
    """0..1 score favoring hue + lightness contrast."""
    Hc, Sc, Lc = hex_to_hsl(center_hex)
    Hd, Sd, Ld = hex_to_hsl(cand_hex)
    dH = ang_diff(Hc, Hd)         # 0..180
    dL = abs(Lc - Ld)             # 0..100
    hue_term   = max(0.0, min(1.0, (dH - 20.0) / 130.0))  # reward >~20°
    light_term = max(0.0, min(1.0, dL / 30.0))            # 30 ≈ full credit
    return 0.65*hue_term + 0.35*light_term

def pair_diversity_penalty(a_hex: str, b_hex: str) -> float:
    """Penalty 0..1 if two flankers are too similar to each other."""
    Ha, Sa, La = hex_to_hsl(a_hex)
    Hb, Sb, Lb = hex_to_hsl(b_hex)
    hue_sim   = max(0.0, min(1.0, (20.0 - ang_diff(Ha, Hb)) / 20.0))   # ≤20° similar
    light_sim = max(0.0, min(1.0, (10.0 - abs(La - Lb)) / 10.0))       # ≤10 L* similar
    return 0.6*hue_sim + 0.4*light_sim

# --- main API ---
def choose_flanker_paths(
    product_slug: str,
    background_hex: str,
    title: str,
    author: str,
    mockup_pool: List[Dict],
    *,
    min_color_score: float = 0.35,
    top_k: int = 8
) -> Tuple[str, str]:
    """
    Returns (left_path, right_path) for two designs from mockup_pool that:
      - best complement the center color,
      - are different from each other,
      - are not the same story as the center.
    Deterministic by product_slug.
    """
    rng = random.Random(hash(product_slug) & 0xFFFFFFFF)

    # candidates = everything except the same story title
    cands = [d for d in mockup_pool if d.get("story_title") != title and "bg_hex" in d and "design_image_path" in d]

    # score by color complement vs center
    scored = []
    for d in cands:
        s = color_complement_score(background_hex, d["bg_hex"])
        if s >= min_color_score:
            scored.append((s, d))

    # relax threshold if too few
    if len(scored) < 4:
        scored = [(color_complement_score(background_hex, d["bg_hex"]), d) for d in cands]

    # deterministic shuffle then sort by score desc
    rng.shuffle(scored)
    scored.sort(key=lambda x: x[0], reverse=True)

    # pick best diverse pair from top_k
    best_pair, best_score = None, -1.0
    K = min(top_k, len(scored))
    for i in range(K):
        for j in range(i+1, K):
            d1, d2 = scored[i][1], scored[j][1]
            pen = pair_diversity_penalty(d1["bg_hex"], d2["bg_hex"])
            pair_score = (scored[i][0] + scored[j][0]) / 2.0 - 0.25*pen
            if pair_score > best_score:
                best_score, best_pair = pair_score, (d1, d2)

    # absolute fallback
    if not best_pair:
        if len(cands) >= 2:
            best_pair = tuple(rng.sample(cands, k=2))
        else:
            # degenerate case: duplicate the only candidate (shouldn't happen with your pool)
            best_pair = (cands[0], cands[0])

    a, b = best_pair

    # order left/right to balance around center lightness (optional, looks nicer)
    _, _, Lc = hex_to_hsl(background_hex)
    La = hex_to_hsl(a["bg_hex"])[2]
    Lb = hex_to_hsl(b["bg_hex"])[2]
    if Lc < 40:       # center dark → lighter on left
        left, right = (a, b) if La > Lb else (b, a)
    elif Lc > 60:     # center light → darker on left
        left, right = (a, b) if La < Lb else (b, a)
    else:             # mid → deterministic by title
        left, right = (a, b) if a["story_title"] < b["story_title"] else (b, a)

    return left["design_image_path"], right["design_image_path"]



# --------------------- MAIN FUNCTIONS -----------------------
# MAIN FUNCTIONS 
def place_artworks(
    mockup_path,
    output_path,
    slots,
    artwork_paths,
    default_mode="fill",       # "fill" | "fit" | "stretch"
    lip_width_px=5,            # overlay line width (at final size)
    lip_feather=0.8,           # overlay softness (at final size)
    supersample=2,             # 1 = off; 2–3 strongly recommended for text-heavy art
    sharpen=True,              # unsharp-mask only where art is placed
    unsharp=(1.0, 150, 2),     # (radius, percent, threshold)
):
    """
    slots: list of dicts, each:
      - either {"rect": (x,y,w,h)} or {"quad": [(tl),(tr),(br),(bl)]}
      - optional "mode": "fill"|"fit"|"stretch"
      - optional "art_idx": index into artwork_paths
    artwork_paths: list of file paths (can be length 1 to reuse same art for all)
    """
    from PIL import Image, ImageDraw, ImageFilter  # ensure available inside function
    import os

    base = Image.open(mockup_path).convert("RGBA")
    W0, H0 = base.size
    ss = max(1, int(round(supersample)))  # supersample factor

    # Preload all arts once
    arts = [Image.open(p).convert("RGBA") for p in artwork_paths]
    if not arts:
        raise ValueError("No artwork_paths provided.")

    # Upscale base & slots for supersampling
    if ss > 1:
        base = base.resize((W0 * ss, H0 * ss), Image.LANCZOS)

        scaled_slots = []
        for slot in slots:
            s = dict(slot)
            if "rect" in s and "quad" not in s:
                x, y, w, h = s["rect"]
                s["quad"] = [(x*ss, y*ss), ((x+w)*ss, y*ss), ((x+w)*ss, (y+h)*ss), (x*ss, (y+h)*ss)]
                s.pop("rect", None)
            elif "quad" in s:
                s["quad"] = [(qx*ss, qy*ss) for (qx, qy) in s["quad"]]
            else:
                raise ValueError("Each slot must include 'rect' or 'quad'.")
            scaled_slots.append(s)
        work_slots = scaled_slots
    else:
        # Normalize rect -> quad without scaling
        work_slots = []
        for slot in slots:
            s = dict(slot)
            if "rect" in s and "quad" not in s:
                x, y, w, h = s["rect"]
                s["quad"] = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
                s.pop("rect", None)
            work_slots.append(s)

    comp = base.copy()
    union_mask = Image.new("L", base.size, 0)  # track art areas (for selective sharpening)

    # Scale edge softening with supersample so it looks the same after downscale
    poly_feather = 0.7 * ss if ss > 1 else 0.7
    lip_w = max(1, int(round(lip_width_px * ss)))
    lip_f = float(lip_feather) * ss if ss > 1 else float(lip_feather)

    for i, slot in enumerate(work_slots):
        quad = slot["quad"]

        # Choose which artwork to use for this slot
        art_idx = slot.get("art_idx", i if i < len(arts) else len(arts) - 1)
        art = arts[art_idx]

        # Aspect handling
        opening_aspect = avg_aspect_from_quad(quad)
        mode = slot.get("mode", default_mode)
        if mode == "fill":
            art_prepped = crop_to_aspect(art, opening_aspect)
        elif mode == "fit":
            art_prepped = fit_to_aspect_canvas(art, opening_aspect)
        elif mode == "stretch":
            art_prepped = art
        else:
            raise ValueError(f"Slot {i}: unknown mode '{mode}'")

        # Warp to quad on a base-sized canvas
        warped = warp_art_into_quad(base.size, art_prepped, quad)

        # Mask to the quad and composite
        mask = polygon_mask(base.size, quad, feather=poly_feather)
        comp = Image.alpha_composite(
            comp,
            Image.composite(warped, Image.new("RGBA", base.size, (0, 0, 0, 0)), mask),
        )

        # Track art region for later selective sharpening
        ImageDraw.Draw(union_mask, "L").polygon(quad, fill=255)

        # Inner-lip overlay to hide micro seams
        comp = overlay_inner_lip(comp, quad, width_px=lip_w, feather=lip_f)

    # Selective sharpen of the art regions (helps text edges)
    if sharpen:
        radius, percent, thresh = unsharp
        sharpened = comp.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=thresh))
        comp = Image.composite(sharpened, comp, union_mask)

    # Downscale back to original size (high-quality)
    if ss > 1:
        comp = comp.resize((W0, H0), Image.LANCZOS)

    # Save
    out_ext = os.path.splitext(output_path)[1].lower()
    if out_ext in (".jpg", ".jpeg"):
        comp.convert("RGB").save(output_path, "JPEG", quality=95, optimize=True)
    else:
        comp.save(output_path, "PNG", optimize=True)
    return output_path

MOCKUPS = {
    "11x14_poster":{
        "mockup_template_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base@BIG.png",
        "slots":[{"quad": [(60, 110), (1706, 110), (1706, 2204), (60, 2204)], "mode": "fill"}],
        "name": "poster"
    },
    "11x14_table":{
        "mockup_template_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2@BIG.png",
        "slots":[{"quad": [(714, 666), (2166, 666), (2166, 2559), (714, 2559)], "mode": "fill"}],
        "name": "table"
    },
     "11x14_wall":{
        "mockup_template_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.png",
        "slots":[{"quad": [(1316, 900), (2772, 900), (2772, 2792), (1316, 2792)], "mode": "fill"}],
        "name": "wall"
    },
    "3x_11x14_wall":{
        "mockup_template_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall@BIG.png",
        "slots":[{'quad': [(750, 2040), (2118, 2040), (2118, 3822), (750, 3822)], 'mode': 'fill'}, {'quad': [(2388, 2040), (3756, 2040), (3756, 3822), (2388, 3822)], 'mode': 'fill'}, {'quad': [(4032, 2040), (5400, 2040), (5400, 3822), (4032, 3822)], 'mode': 'fill'}],
        "name": "3x_wall"
    }
}

def create_mockups(product_data_path, product_design_path, mockup_list, output_dir="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/product_mockups"):
    
    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    product_slug = product_data.get("product_slug")
    design_background_color = product_data.get("background_color_hex")
    design_title = product_data.get("title")
    design_author = product_data.get("author")

    mockups_paths_added = []
    for mockup_type in mockup_list:

        mockup_details = MOCKUPS.get(mockup_type, "")
        if mockup_details == "":
            print("❌ Mockup: ", mockup_type, " does not exist. Skipping.")
            continue 

        mockup_output_path = f"{output_dir}/{product_slug}-{mockup_details.get('name')}.png"

        if mockup_type == "3x_11x14_wall":
            
            #get paths for left and right
            # deterministically pick two other designs from set pool that have (a) complementary color 
            left_path, right_path = choose_flanker_paths(
                product_slug=product_slug,
                background_hex=design_background_color,
                title=design_title,
                author=design_author,
                mockup_pool=mockup_pool_11x14
            )

            # slots order is: LEFT, CENTER, RIGHT
            center_path = product_design_path  # keep the original arg value
            product_design_path_list = [left_path, center_path, right_path]
        else:
            # for non-3x mockups, just use the center art
            product_design_path_list = [product_design_path]


        place_artworks(
            mockup_path=mockup_details.get("mockup_template_path"),
            output_path=mockup_output_path,
            slots=mockup_details.get("slots"),
            artwork_paths=product_design_path_list,
            supersample=1,
            sharpen=True,
            unsharp=(0.7, 200, 0),
            lip_width_px=5,
            lip_feather=0.8,
        )

        #need to create poster only mockup after initial artworks place
        if mockup_type == "11x14_poster":
            out = overlay_clips_exact(
                base_path=mockup_output_path,
                clips=[
                    ClipSpec(
                        path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/gold-clip@BIG.png",
                        pos=(230, 30),  
                        size_px=(65, None),
                        rotation_deg=-0.2,
                        anchor="top_center",
                        shadow_offset=(1, 2),
                        shadow_blur=2,
                        shadow_opacity=105
                    ),
                    ClipSpec(
                        path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/gold-clip@BIG.png",
                        pos=(1560, 30),
                        size_px=(65, None),
                        rotation_deg=0.2,
                        anchor="top_center",
                        shadow_offset=(1, 2),
                        shadow_blur=2,
                        shadow_opacity=105
                    ),
                ],
                output_path=mockup_output_path,
                supersample=3,                   # key for tiny overlays
                post_unsharp=(0.6, 240, 0),      # per-clip after rotate
                final_unsharp=(0.35, 110, 1),    # gentle overall after downscale
            )


        #added mockup path added 
        mockups_paths_added.append(mockup_output_path)

    
    #save mockup_paths_added back to product_data and save
    product_data["mockup_paths"] = mockups_paths_added

    # Atomic write to avoid partial/corrupt files
    dir_name = os.path.dirname(product_data_path) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmp:
        json.dump(product_data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, product_data_path)





## CREATE STORIES + PRODUCTS TO HAVE FOR 3x WALL MOCKUP 

# example_stories = [
#     {
#         "story_type": "Literature",
#         "story_title": "The Great Gatsby",
#         "story_author": "F. Scott Fitzgerald",
#         "story_protagonist": "Jay Gatsby",
#         "story_year": "1925",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_great_gatsby_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Pride and Prejudice",
#         "story_author": "Jane Austen",
#         "story_protagonist": "Elizabeth Bennet",
#         "story_year": "1813",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/pride_and_prejudice_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Moby-Dick",
#         "story_author": "Herman Melville",
#         "story_protagonist": "Ishmael",
#         "story_year": "1851",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/moby_dick_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "To Kill a Mockingbird",
#         "story_author": "Harper Lee",
#         "story_protagonist": "Scout Finch",
#         "story_year": "1960",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/to_kill_a_mockingbird_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "1984",
#         "story_author": "George Orwell",
#         "story_protagonist": "Winston Smith",
#         "story_year": "1949",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/1984_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Alice Adventures in Wonderland",
#         "story_author": "Lewis Carroll",
#         "story_protagonist": "Alice",
#         "story_year": "1865",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/alice_in_wonderland_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Catcher in the Rye",
#         "story_author": "J.D. Salinger",
#         "story_protagonist": "Holden Caulfield",
#         "story_year": "1951",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_catcher_in_the_rye_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Dune",
#         "story_author": "Frank Herbert",
#         "story_protagonist": "Paul Atreides",
#         "story_year": "1965",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/dune_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Alchemist",
#         "story_author": "Paulo Coelho",
#         "story_protagonist": "Santiago",
#         "story_year": "1988",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_alchemist_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Frankenstein",
#         "story_author": "Mary Shelley",
#         "story_protagonist": "Victor Frankenstein",
#         "story_year": "1818",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/frankenstein_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Romeo and Juliet",
#         "story_author": "William Shakespeare",
#         "story_protagonist": "Juliet",
#         "story_year": "1597",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/romeo_and_juliet_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Dracula",
#         "story_author": "Bram Stoker",
#         "story_protagonist": "Jonathan Harker",
#         "story_year": "1897",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/dracula_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Adventures of Huckleberry Finn",
#         "story_author": "Mark Twain",
#         "story_protagonist": "Huckleberry Finn",
#         "story_year": "1884",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_adventures_of_huckleberry_finn_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Little Women",
#         "story_author": "Louisa May Alcott",
#         "story_protagonist": "Jo March",
#         "story_year": "1868",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/little_women_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Old Man and the Sea",
#         "story_author": "Ernest Hemingway",
#         "story_protagonist": "Santiago",
#         "story_year": "1952",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_old_man_and_the_sea_composite_data.json"
#     }
# ]

# from create_story_and_product_data import create_story_data
# from create_story_and_product_data import create_product_data

# for story in example_stories:
#     create_story_data(story_type=story['story_type'], 
#                   story_title=story['story_title'], 
#                   story_author=story['story_author'], 
#                   story_protagonist=story['story_protagonist'], 
#                   story_year=story['story_year'], 
#                   story_summary_path=story['story_summary_path'])


# example_story_data = [
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-old-man-and-the-sea-santiago.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/little-women-jo-march.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-adventures-of-huckleberry-finn-huckleberry-finn.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/dracula-jonathan-harker.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/romeo-and-juliet-juliet.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/frankenstein-victor-frankenstein.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-alchemist-santiago.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/dune-paul-atreides.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-catcher-in-the-rye-holden-caulfield.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/alice-adventures-in-wonderland-alice.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/1984-winston-smith.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/moby-dick-ishmael.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice-elizabeth-bennet.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby-jay-gatsby.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/to-kill-a-mockingbird-scout-finch.json"
# ]


# for story_data_path in example_story_data:
#     create_product_data(story_data_path=story_data_path,
#                         product_type="print", 
#                         product_size="11x14", 
#                         product_style="")