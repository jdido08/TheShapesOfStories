from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image, ImageOps, ImageFilter, ImageDraw

# ---------- math helpers ----------
def _find_coeffs(pa: List[Tuple[float,float]], pb: List[Tuple[float,float]]):
    # Solve homography (dest->src) for PIL.Image.transform
    A = []
    for (x, y), (u, v) in zip(pa, pb):
        A.extend([
            [x, y, 1, 0, 0, 0, -u*x, -u*y, -u],
            [0, 0, 0, x, y, 1, -v*x, -v*y, -v],
        ])
    # Simple Gauss-Jordan on 8x8 (use floats)
    m = len(A); n = 9
    # augment
    for i, row in enumerate(A):
        A[i] = [float(c) for c in row]
    # RREF
    r = 0
    for c in range(n):
        if r >= m: break
        pivot = None
        for i in range(r, m):
            if abs(A[i][c]) > 1e-9: pivot = i; break
        if pivot is None: continue
        A[r], A[pivot] = A[pivot], A[r]
        div = A[r][c]
        A[r] = [x/div for x in A[r]]
        for i in range(m):
            if i != r and abs(A[i][c]) > 1e-9:
                factor = A[i][c]
                A[i] = [a - factor*b for a,b in zip(A[i], A[r])]
        r += 1
    # last column are solutions
    coeffs = [A[i][8] for i in range(8)]
    return coeffs

def _axis_aligned(c):
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=c
    return abs(y0-y1)<1e-3 and abs(y2-y3)<1e-3 and abs(x0-x3)<1e-3 and abs(x1-x2)<1e-3

# ---------- template spec ----------
@dataclass
class Slot:
    # corners normalized to template width/height, clockwise from top-left
    corners_norm: List[Tuple[float,float]]
    fit: str = "contain"      # 'contain' or 'cover'
    keyline_px: int = 0       # 0 disables
    bleed_px: int = 0         # expand (+) or inset (-) before paste
    use_perspective: Optional[bool] = None  # None = auto

@dataclass
class TemplateSpec:
    path: str
    overlay_path: Optional[str] = None  # PNG with frame/glass on top
    slots: List[Slot] = None

# ---------- core ----------
def compose_mockup(spec: TemplateSpec, art_path: str, out_path: str):
    base = ImageOps.exif_transpose(Image.open(spec.path)).convert("RGBA")
    W, H = base.size
    comp = base.copy()

    for slot in spec.slots:
        art = ImageOps.exif_transpose(Image.open(art_path)).convert("RGBA")

        # corners in pixels
        dest = [(int(u*W), int(v*H)) for (u,v) in slot.corners_norm]
        # auto vs forced perspective
        persp = _axis_aligned(dest) is False if slot.use_perspective is None else slot.use_perspective

        if persp:
            # perspective warp
            src = [(0,0),(art.width,0),(art.width,art.height),(0,art.height)]
            coeffs = _find_coeffs(dest, src)
            warped = art.transform((W,H), Image.PERSPECTIVE, coeffs, Image.Resampling.LANCZOS)
            comp = Image.alpha_composite(comp, warped)
        else:
            # fast path (axis-aligned rectangle)
            minx = min(p[0] for p in dest); maxx = max(p[0] for p in dest)
            miny = min(p[1] for p in dest); maxy = max(p[1] for p in dest)
            box_w = maxx - minx; box_h = maxy - miny

            if slot.fit == "contain":
                resized = ImageOps.contain(art, (box_w, box_h), Image.Resampling.LANCZOS)
                # center into box, then crop/letterbox if needed
                canvas = Image.new("RGBA", (box_w, box_h), (0,0,0,0))
                ox = (box_w - resized.width)//2
                oy = (box_h - resized.height)//2
                canvas.paste(resized, (ox, oy))
                paste_img = canvas
            else:  # cover
                paste_img = ImageOps.fit(art, (box_w, box_h), Image.Resampling.LANCZOS, centering=(0.5,0.5))

            if slot.bleed_px:
                # expand/shrink before paste
                paste_img = ImageOps.expand(paste_img, border=abs(slot.bleed_px), fill=(0,0,0,0))
                minx -= slot.bleed_px; miny -= slot.bleed_px

            # sharpen tiny type a bit
            paste_img = paste_img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=80, threshold=2))

            comp.alpha_composite(paste_img, (minx, miny))

            # optional keyline
            if slot.keyline_px > 0:
                draw = ImageDraw.Draw(comp)
                inset = slot.keyline_px//2
                draw.rectangle([minx+inset, miny+inset, maxx-inset, maxy-inset],
                               outline=(210,210,210,255), width=slot.keyline_px)

    if spec.overlay_path:
        overlay = ImageOps.exif_transpose(Image.open(spec.overlay_path)).convert("RGBA")
        if overlay.size != (W,H): overlay = overlay.resize((W,H), Image.Resampling.LANCZOS)
        comp = Image.alpha_composite(comp, overlay)

    comp.convert("RGB").save(out_path, "JPEG", quality=92, subsampling=1, optimize=True)

# ---------- example ----------
spec = TemplateSpec(
    path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/8x10_print_on_table_in_11x14_frame_with_matt.jpeg",
    overlay_path=None,  # e.g. ".../8x10_table_overlay.png"
    slots=[
        Slot(
            # your coords normalized (219,415)-(532,779) on a 768x768 preview would be:
            corners_norm=[(219/768,415/768),(532/768,415/768),(532/768,779/768),(219/768,779/768)],
            fit="contain",
            keyline_px=1,
            bleed_px=0,
            use_perspective=None,  # auto
        )
    ]
)

artwork_path = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png'
compose_mockup(spec, artwork_path, "final_mockup_test_5.jpg")
