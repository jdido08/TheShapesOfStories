
### COLOR MAPPINGS #### 

# import webcolors
# from webcolors import CSS3_NAMES_TO_HEX

# def hex_to_color_name(hex_color: str) -> str:
#     """Return exact CSS3 name if available; otherwise the nearest CSS3 name."""
#     # exact match first
#     try:
#         return webcolors.hex_to_name(hex_color, spec='css3')
#     except ValueError:
#         pass

#     # nearest by Euclidean RGB distance
#     r, g, b = webcolors.hex_to_rgb(hex_color)  # returns ints 0–255
#     best_name, best_dist = None, float('inf')
#     for name, hx in CSS3_NAMES_TO_HEX.items():
#         cr, cg, cb = webcolors.hex_to_rgb(hx)
#         dist = (cr - r)**2 + (cg - g)**2 + (cb - b)**2
#         if dist < best_dist:
#             best_name, best_dist = name, dist
#     return best_name

import math
import re
import webcolors

# ----------------------------
# 1) Canonical retail palette
# ----------------------------
SIMPLE_PALETTE = {
    # Neutrals
    "White":      "#FFFFFF",
    "Ivory":      "#FFFFF0",  # 'Cream' aliases to this
    "Beige":      "#F5F5DC",
    "Tan":        "#D2B48C",
    "Light Gray": "#D3D3D3",
    "Gray":       "#808080",
    "Charcoal":   "#36454F",
    "Black":      "#000000",

    # Blues/Teals
    "Sky Blue":   "#87CEEB",
    "Blue":       "#1E90FF",
    "Navy":       "#001F3F",
    "Teal":       "#008080",

    # Greens
    "Mint":       "#98FF98",
    "Sage":       "#9C9F84",
    "Olive":      "#808000",
    "Forest":     "#228B22",

    # Warm
    "Yellow":     "#FFFF00",
    "Gold":       "#FFD700",
    "Orange":     "#FF8C00",
    "Red":        "#FF0000",
    "Pink":       "#FFC0CB",
    "Purple":     "#800080",
    "Brown":      "#8B4513",
}

# Color families for storefront filters
COLOR_FAMILY = {
    # Neutrals
    "White":"Neutral","Ivory":"Neutral","Beige":"Neutral","Tan":"Neutral",
    "Light Gray":"Neutral","Gray":"Neutral","Charcoal":"Neutral","Black":"Neutral",
    # Blues/Teals
    "Sky Blue":"Blue","Blue":"Blue","Navy":"Blue","Teal":"Blue-Green",
    # Greens
    "Mint":"Green","Sage":"Green","Olive":"Green","Forest":"Green",
    # Warm
    "Yellow":"Yellow","Gold":"Yellow","Orange":"Orange","Red":"Red",
    "Pink":"Pink","Purple":"Purple","Brown":"Brown",
}

# Synonyms you might see in copy that should resolve to canonical labels
ALIASES = {
    # neutrals
    "cream":"Ivory", "off white":"Ivory", "off-white":"Ivory", "eggshell":"Ivory", "bone":"Ivory",
    "stone":"Beige", "sand":"Tan", "khaki":"Tan", "camel":"Tan", "gunmetal":"Charcoal", "silver":"Gray",
    # blues/teals
    "baby blue":"Sky Blue", "cyan":"Sky Blue", "aqua":"Teal", "turquoise":"Teal", "royal blue":"Blue",
    "navy blue":"Navy",
    # greens
    "mint green":"Mint", "seafoam":"Mint", "sage green":"Sage", "forest green":"Forest",
    # warm
    "mustard":"Yellow", "amber":"Yellow", "golden":"Gold",
    "peach":"Pink", "coral":"Pink", "magenta":"Pink", "fuchsia":"Pink", "rose":"Pink",
    "violet":"Purple", "lilac":"Purple", "lavender":"Purple",
    "rust":"Brown", "copper":"Brown", "bronze":"Brown", "chocolate":"Brown", "espresso":"Brown",
    "burgundy":"Red", "maroon":"Red", "wine":"Red",
    # fallbacks
    "indigo":"Blue"
}

# ----------------------------
# 2) sRGB -> Lab helpers
# ----------------------------
def _srgb_to_linear(c):
    c = c/255.0
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055) ** 2.4

def _rgb_to_xyz(r,g,b):
    R, G, B = map(_srgb_to_linear, (r,g,b))
    X = 0.4124564*R + 0.3575761*G + 0.1804375*B
    Y = 0.2126729*R + 0.7151522*G + 0.0721750*B
    Z = 0.0193339*R + 0.1191920*G + 0.9503041*B
    return X, Y, Z

def _f_lab(t):
    eps = (6/29)**3
    kappa = 24389/27
    return t ** (1/3) if t > eps else (kappa * t + 16) / 116

def _xyz_to_lab(X, Y, Z):
    # D65 reference white
    Xn, Yn, Zn = 0.95047, 1.00000, 1.08883
    fx, fy, fz = _f_lab(X/Xn), _f_lab(Y/Yn), _f_lab(Z/Zn)
    L = 116*fy - 16
    a = 500*(fx - fy)
    b = 200*(fy - fz)
    return (L, a, b)

def _hex_to_lab(hex_color: str):
    r, g, b = webcolors.hex_to_rgb(hex_color)
    return _xyz_to_lab(*_rgb_to_xyz(r, g, b))

# ----------------------------
# 3) CIEDE2000 distance
# ----------------------------
def delta_e_ciede2000(lab1, lab2, kL=1, kC=1, kH=1):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    avg_L = (L1 + L2) / 2.0
    C1 = math.sqrt(a1*a1 + b1*b1)
    C2 = math.sqrt(a2*a2 + b2*b2)
    avg_C = (C1 + C2) / 2.0
    G = 0.5 * (1 - math.sqrt((avg_C**7) / (avg_C**7 + 25**7)))
    a1p = (1 + G) * a1
    a2p = (1 + G) * a2
    C1p = math.sqrt(a1p*a1p + b1*b1)
    C2p = math.sqrt(a2p*a2p + b2*b2)
    avg_Cp = (C1p + C2p) / 2.0

    def _hp(ap, b):
        if ap == 0 and b == 0:
            return 0.0
        h = math.degrees(math.atan2(b, ap))
        return h + 360 if h < 0 else h

    h1p = _hp(a1p, b1)
    h2p = _hp(a2p, b2)
    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p*C2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        if dh > 180: dh -= 360
        elif dh < -180: dh += 360
        dhp = dh
    dHp = 2 * math.sqrt(C1p*C2p) * math.sin(math.radians(dhp / 2.0))

    avg_hp = h1p + h2p
    if C1p*C2p != 0:
        if abs(h1p - h2p) > 180:
            avg_hp += 360 if (h1p + h2p) < 360 else -360
        avg_hp /= 2.0

    T = (1
         - 0.17 * math.cos(math.radians(avg_hp - 30))
         + 0.24 * math.cos(math.radians(2 * avg_hp))
         + 0.32 * math.cos(math.radians(3 * avg_hp + 6))
         - 0.20 * math.cos(math.radians(4 * avg_hp - 63)))

    d_ro = 30 * math.exp(-((avg_hp - 275) / 25) ** 2)
    Rc = 2 * math.sqrt((avg_Cp ** 7) / (avg_Cp ** 7 + 25 ** 7))
    Sl = 1 + (0.015 * (avg_L - 50) ** 2) / math.sqrt(20 + (avg_L - 50) ** 2)
    Sc = 1 + 0.045 * avg_Cp
    Sh = 1 + 0.015 * avg_Cp * T
    Rt = -math.sin(math.radians(2 * d_ro)) * Rc

    return math.sqrt(
        (dLp / (kL * Sl)) ** 2 +
        (dCp / (kC * Sc)) ** 2 +
        (dHp / (kH * Sh)) ** 2 +
        Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh))
    )

# Precompute palette in Lab
_PALETTE_LAB = {name: _hex_to_lab(hx) for name, hx in SIMPLE_PALETTE.items()}

# ----------------------------
# 4) Neutral gate + public API
# ----------------------------
ACHROMA_C_THRESHOLD = 2.5  # below this chroma => neutral bucket
WHITE_L_MIN = 97
BLACK_L_MAX = 12

def _shade_from_L(L):
    if L >= 80: return "Light"
    if L <= 35: return "Dark"
    return "Medium"

def canonicalize_label(label: str) -> str:
    """Collapse common synonyms to your canonical labels."""
    if not label: return label
    key = re.sub(r"\s+", " ", label.strip().lower())
    return ALIASES.get(key, label).title()

def map_hex_to_simple_color(hex_color: str, max_delta_e: float | None = None):
    """
    Returns:
      {
        'name': <canonical label>,
        'family': <broad family>,
        'shade': <Light/Medium/Dark>,
        'distance': <ΔE00 to prototype>,
        'matched_hex': <palette hex>
      }
    If max_delta_e is set and best match is farther, returns name='Other'.
    """
    L, a, b = _hex_to_lab(hex_color)

    # Neutral gate: keep near-achromatic colors from drifting into hues
    chroma = math.sqrt(a*a + b*b)
    if chroma < ACHROMA_C_THRESHOLD:
        if L >= WHITE_L_MIN:
            return {"name":"White","family":"Neutral","shade":"Light","distance":0.0,"matched_hex":SIMPLE_PALETTE["White"]}
        if L <= BLACK_L_MAX:
            return {"name":"Black","family":"Neutral","shade":"Dark","distance":0.0,"matched_hex":SIMPLE_PALETTE["Black"]}
        # Else Gray band
        return {"name":"Gray","family":"Neutral","shade":_shade_from_L(L),"distance":0.0,"matched_hex":SIMPLE_PALETTE["Gray"]}

    # Chromatic: closest by CIEDE2000
    target = (L, a, b)
    best_name, best_d = None, float("inf")
    for name, lab in _PALETTE_LAB.items():
        d = delta_e_ciede2000(target, lab)
        if d < best_d:
            best_name, best_d = name, d

    if max_delta_e is not None and best_d > max_delta_e:
        return {"name":"Other","family":None,"shade":_shade_from_L(L),"distance":round(best_d,2),"matched_hex":None}

    matched_hex = SIMPLE_PALETTE[best_name]
    family = COLOR_FAMILY.get(best_name)
    return {"name": best_name, "family": family, "shade": _shade_from_L(L),
            "distance": round(best_d, 2), "matched_hex": matched_hex}
