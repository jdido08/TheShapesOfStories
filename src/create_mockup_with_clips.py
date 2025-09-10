# mockup_multi.py
from PIL import Image, ImageDraw, ImageFilter
import os
import itertools

from dataclasses import dataclass
from typing import Optional, Tuple, List
from PIL import Image, ImageFilter
from PIL.Image import Resampling  # Pillow 10+

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

# ---------- CORE HELPERS ----------

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

def overlay_clips_exact(
    base_path: str,
    clips: List[ClipSpec],
    output_path: str,
):
    base = Image.open(base_path).convert("RGBA")

    for spec in clips:
        overlay = Image.open(spec.path).convert("RGBA")
        if spec.trim_transparent_edges:
            overlay = _trim_transparent_edges(overlay)

        overlay = _resize_keep_aspect(overlay, spec.size_px)
        if abs(spec.rotation_deg) > 1e-6:
            overlay = overlay.rotate(spec.rotation_deg, expand=True, resample=Resampling.BICUBIC)

        # anchor math
        ax, ay = _ANCHOR_OFFSETS[spec.anchor](overlay.width, overlay.height)
        x = int(spec.pos[0] - ax)
        y = int(spec.pos[1] - ay)

        # shadow (optional)
        if spec.add_shadow:
            sh, shift = _make_shadow(overlay, spec.shadow_offset, spec.shadow_blur, spec.shadow_opacity)
            base.alpha_composite(sh, (x + shift[0], y + shift[1]))

        base.alpha_composite(overlay, (x, y))

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

# def place_artworks(
#     mockup_path,
#     output_path,
#     slots,
#     artwork_paths,
#     default_mode="fill",       # "fill" | "fit" | "stretch"
#     lip_width_px=5,            # overlay line width
#     lip_feather=0.8            # slight softness
# ):
#     """
#     slots: list of dicts, each:
#       - either {"rect": (x,y,w,h)} or {"quad": [(tl),(tr),(br),(bl)]}
#       - optional "mode": "fill"|"fit"|"stretch"
#       - optional "art_idx": index into artwork_paths
#     artwork_paths: list of file paths (can be length 1 to reuse same art for all)
#     """
#     base = Image.open(mockup_path).convert("RGBA")
#     W,H = base.size

#     # Preload all arts once
#     arts = [Image.open(p).convert("RGBA") for p in artwork_paths]
#     if not arts:
#         raise ValueError("No artwork_paths provided.")

#     comp = base.copy()

#     for i, slot in enumerate(slots):
#         quad = slot.get("quad")
#         rect = slot.get("rect")
#         if rect and not quad:
#             quad = rect_to_quad(*rect)

#         if not quad or len(quad) != 4:
#             raise ValueError(f"Slot {i}: must provide 'rect' or 4-pt 'quad'.")

#         mode = slot.get("mode", default_mode)
#         art = arts[slot.get("art_idx", i if i < len(arts) else len(arts)-1)]

#         # Aspect handling
#         opening_aspect = avg_aspect_from_quad(quad)
#         if mode == "fill":
#             art_prepped = crop_to_aspect(art, opening_aspect)
#         elif mode == "fit":
#             art_prepped = fit_to_aspect_canvas(art, opening_aspect)
#         elif mode == "stretch":
#             art_prepped = art
#         else:
#             raise ValueError(f"Slot {i}: unknown mode '{mode}'")

#         # Warp to quad on a base-sized canvas
#         warped = warp_art_into_quad((W,H), art_prepped, quad)

#         # Mask to the quad and composite
#         mask = polygon_mask((W,H), quad, feather=0.7)
#         comp = Image.alpha_composite(comp, Image.composite(warped, Image.new("RGBA", (W,H), (0,0,0,0)), mask))

#         # Inner-lip overlay to hide seams
#         comp = overlay_inner_lip(comp, quad, width_px=lip_width_px, feather=lip_feather)

#     # Save
#     out_ext = os.path.splitext(output_path)[1].lower()
#     if out_ext in (".jpg", ".jpeg"):
#         comp.convert("RGB").save(output_path, "JPEG", quality=95, optimize=True)
#     else:
#         comp.save(output_path, "PNG", optimize=True)
#     return output_path

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


# ---------------------- example configs ----------------------
if __name__ == "__main__":
    # 1) Single frame on table (rect example; straight-on)
    single_slots = [
        {"rect": (238, 222, 722-238, 853-222), "mode": "fill"}  # your chosen crop that slightly overlaps under the lip
    ]

    ## 11x14 on WALL
    # place_artworks(
    #     mockup_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.png",
    #     output_path="fina_mockup_11x14_wall.png",
    #     slots=[{"quad": [(1316, 900), (2772, 900), (2772, 2792), (1316, 2792)], "mode": "fill"}],
    #     artwork_paths=["/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png"],
    #     supersample=1,
    #     sharpen=True,
    #     unsharp=(0.7, 200, 0),
    #     lip_width_px=5,
    #     lip_feather=0.8,
    # )


    ## 11x14 on TABLE
    # place_artworks(
    #     mockup_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2@BIG.png",
    #     output_path="fina_mockup_11x14_table.png",
    #     slots=[{"quad": [(714, 666), (2166, 666), (2166, 2559), (714, 2559)], "mode": "fill"}],
    #     artwork_paths=["/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png"],
    #     supersample=1,
    #     sharpen=True,
    #     unsharp=(0.7, 200, 0),
    #     lip_width_px=5,
    #     lip_feather=0.8,
    # )

    ##POSTER ONLY
    # place_artworks(
    #     mockup_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base@BIG.png",
    #     output_path="fina_mockup_poster_only.png",
    #     slots=[{"quad": [(60, 110), (1706, 110), (1706, 2204), (60, 2204)], "mode": "fill"}],
    #     artwork_paths=["/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png"],
    #     supersample=1,
    #     sharpen=True,
    #     unsharp=(0.7, 200, 0),
    #     lip_width_px=5,
    #     lip_feather=0.8,
    # )

    

    # mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base.jpeg"
    # dest_corners = [(30, 55), (853, 55), (853, 1102), (30, 1102)] #cutting into borders



    # 2) Three frames on wall (quad example)
    # three_quads = [
    #     # left
    #     [(750, 2040), (2118, 2040), (2118, 3822), (750, 3822)],
    #     # center
    #     [(2388, 2040), (3756, 2040), (3756, 3822), (2388, 3822)],
    #     # right
    #     [(4032, 2040), (5400, 2040), (5400, 3822), (4032, 3822)]
    # ]
    # #[{"quad": [[750, 2040], [2118, 2040], [2118, 3822], [750, 3822]]}, {"quad": [[2388, 2040], [3756, 2040], [3756, 3822], [2388, 3822]]}, {"quad": [[4032, 2040], [5400, 2040], [5400, 3822], [4032, 3822]]}]
    # three_slots = [{"quad": q, "mode": "fill"} for q in three_quads]

    # place_artworks(
    #     mockup_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall@BIG.png",
    #     output_path="fina_mockup_11x14_3x_wall.png",
    #     slots=three_slots,
    #     # Use one art for all frames OR pass three different files
    #     artwork_paths=[
    #         "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png",
    #         "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png",
    #         "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png"
    #     ],
    #     default_mode="fill", #fill --> default
    #     supersample=1,
    #     sharpen=True,
    #     unsharp=(0.7, 200, 0),
    #     lip_width_px=5,
    #     lip_feather=0.8,
    # )


    out = overlay_clips_exact(
    base_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/fina_mockup_poster_only.png",
    clips=[
        ClipSpec(
            path="mockup_templates/gold-clip.png",
            pos=(230, 50),              # EXACT pixel where the anchor should land
            size_px=(60, None),         # EXACT width (height auto)
            rotation_deg=-1.2,
            anchor="top_center"          # anchor aligns the ring/center at pos
        ),
        ClipSpec(
            path="mockup_templates/gold-clip.png",
            pos=(1560, 50),
            size_px=(60, None),
            rotation_deg=1.5,
            anchor="top_center"
        ),
    ],
    output_path="poster_with_clips_exact.png",
)







    print("Done.")



#ORIGNAL DATA

    # #11x14 wall 
    # mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall.jpeg"
    # output_path = "fina_mockup_11x14_wall.png"
    # dest_corners = [(329, 225), (693, 225), (693, 698), (329, 698)] 


    # #11x14 table
    # mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2.jpeg"
    # output_path = "fina_mockup_11x14_table.png"
    # dest_corners = [(238, 222), (722, 222), (722, 853), (238, 853)] #cutting into borders --> this one 
    # #dest_corners = [(237, 222), (722, 222), (722, 853), (237, 853)] #cutting into borders
    # #dest_corners = [(239, 222), (722, 222), (722, 853), (239, 853)] #cutting into borders

    # #11x14 3x wall
    # mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall.jpeg"
    # output_path = "fina_mockup_11x14_3x_wall.png"

    # dest_corners = [
    #     (125, 340), (353, 340), (353, 637), (125, 637), #--> frame on left
    #     (398, 340), (626, 340), (626, 637), (398, 637), #--> frame in center
    #     (672, 340), (900, 340), (900, 637), (672, 637 ) #--> frame on right 
    # ]

    #POSTER
    # mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base.jpeg"
    # dest_corners = [(31, 55), (853, 55), (853, 1102), (31, 1102)] #cutting into borders

