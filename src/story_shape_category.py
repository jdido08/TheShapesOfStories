#!/usr/bin/env python3
"""
Deterministic symbolic representation of a story curve
with RELATIVE DISTINCTNESS gating for arrow magnitudes.

If non-flat segments are all roughly the same size,
they are ALL single arrows (↑/↓). Medium (↑↑/↓↓) and large (↑↑↑/↓↓↓)
are used only when there is a clear distinction.

Usage:
  python shape_to_symbolic.py /path/to/story.json
"""

from __future__ import annotations
import json, math, sys
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal

# --------------------
# Tunable thresholds (ABSOLUTE) — act directly on the range-normalized curve
# --------------------
# These thresholds do not depend on other segments; they look only at local geometry.
# "Bigger" generally means stricter/cleaner (fewer segments or fewer escalations).
# "Smaller" generally means more sensitive (more segments or more escalations).

EPSILON_RDP_FACTOR = 0.02
# Ramer–Douglas–Peucker (RDP) simplification tolerance as a fraction of vertical range R.
# ↑ Bigger: heavier smoothing → fewer points → fewer/simpler segments (can hide small wiggles).
# ↓ Smaller: lighter smoothing → keeps more detail → may create extra tiny segments.

SLOPE_ZERO_FRAC    = 0.005
# Two consecutive samples are considered "no slope change" if |Δy| < this * R.
# ↑ Bigger: more changes treated as flat → merges borderline slope changes.
# ↓ Smaller: more sensitive to weak slopes → splits more runs (can oversegment gently sloped areas).

NOISE_DX_MIN       = 0.06
NOISE_DY_MAX       = 0.04
# A run is dropped as noise if (dx < NOISE_DX_MIN) AND (dy_norm < NOISE_DY_MAX).
# ↑ Bigger NOISE_DX_MIN or ↑ smaller NOISE_DY_MAX: stricter noise filter → removes more short/low moves.
# ↓ Smaller NOISE_DX_MIN or ↑ larger NOISE_DY_MAX: more short/low moves survive → potential micro-segments.

FLAT_DY_MAX        = 0.05
FLAT_DX_MIN        = 0.10
# Flat detection: if dy_norm < FLAT_DY_MAX AND dx ≥ FLAT_DX_MIN, label as flat (→).
# ↑ Bigger FLAT_DY_MAX: more near-level spans counted as flat → fewer up/down segments.
# ↓ Smaller FLAT_DY_MAX: only very level spans become flat → more ↑/↓ segments.
# ↑ Bigger FLAT_DX_MIN: requires longer plateaus to call flat → fewer flats, more ↑/↓.
# ↓ Smaller FLAT_DX_MIN: even short plateaus can become flats → may fragment long ↑/↓ with tiny flats.

SMALL_MIN          = 0.12
# Minimum dy_norm to qualify as a real move; below this, we collapse to flat/noise.
# ↑ Bigger: more small moves collapse to → (singles become flats) → simpler outputs.
# ↓ Smaller: more moves count as real ↑/↓ → potentially more single arrows.

MEDIUM_MIN         = 0.25
# Absolute floor for a move to be eligible for "double" (↑↑/↓↓); relative checks still apply later.
# ↑ Bigger: doubles rarer (more singles).
# ↓ Smaller: doubles more common (subject to relative gating).

LARGE_MIN          = 0.70
# Soft context guard for triple evaluation (we also have a hard floor below).
# ↑ Bigger: makes even candidate triples less likely.
# ↓ Smaller: more segments considered for triple (still must pass the strict gate).

LARGE_ABS_MIN      = 0.80
# Hard absolute floor for triple arrows: dy_norm must be ≥ this.
# ↑ Bigger: triples become extremely rare or impossible if set near 1.0.
# ↓ Smaller: triples become easier (still need relative dominance + width).

SEG_DX_MIN         = 0.07
# Minimum horizontal span for a non-flat segment unless it’s obviously huge.
# ↑ Bigger: suppresses short blips → fewer, longer segments.
# ↓ Smaller: allows shorter segments → may oversegment in busy regions.


# --------------------
# Relative distinctness gating — compares segments *within the same curve*
# --------------------
# These thresholds enforce “only escalate when clearly distinct.”
# They prevent doubles/triples when all moves are roughly the same size.

DISTINCT_RATIO     = 1.8
DISTINCT_ABS       = 0.15
# “All-similar” check across non-flat segments:
#   similar = (max/min < DISTINCT_RATIO) AND (max−min < DISTINCT_ABS)
# If similar → force ALL to single arrows.
# ↑ Bigger DISTINCT_RATIO or ↑ Bigger DISTINCT_ABS: harder to trigger “all-similar” → more doubles possible.
# ↓ Smaller DISTINCT_RATIO or ↓ Smaller DISTINCT_ABS: easier to trigger “all-similar” → more singles, fewer escalations.

REL_MED_EDGE       = 0.50
# Relative position within the spread to qualify for doubles:
# rel = (dy_norm − min) / (max − min). Must be ≥ REL_MED_EDGE + meet MEDIUM_MIN.
# ↑ Bigger: doubles rarer (only clearly above-average moves become ↑↑/↓↓).
# ↓ Smaller: doubles more common.

REL_LARGE_EDGE     = 0.88
# Relative position threshold for the largest segment to even be considered triple.
# ↑ Bigger: triples rarer (must be very close to the top of the spread).
# ↓ Smaller: triples more attainable (still need other triple conditions).

TRIPLE_DX_MIN      = 0.18
# Minimum horizontal span required for a triple (must cover ≥18% of the x-axis).
# ↑ Bigger: triples rarer (must be long in time).
# ↓ Smaller: short but tall moves can become triple (riskier).

LARGE_REL_DOM      = 2.0
# Required dominance of the largest vs the second-largest dy_norm to allow a triple.
# ↑ Bigger: triples much rarer (largest must dwarf #2).
# ↓ Smaller: triples easier (more ties/escalations).

@dataclass
class Segment:
    dir: Literal["up", "down", "flat"]
    x0: float
    x1: float
    y0: float
    y1: float
    dy_norm: float
    arrows: Literal["→","↑","↑↑","↑↑↑","↓","↓↓","↓↓↓"] = "→"

    def to_public(self) -> dict:
        return {
            "dir": self.dir,
            "x0": round(self.x0, 3),
            "x1": round(self.x1, 3),
            "dy_norm": round(self.dy_norm, 3),
            "arrows": self.arrows,
        }

# --------------------
# I/O
# --------------------
#def load_points_from_json(path: str) -> Tuple[List[float], List[float]]:
def load_points_from_json(story_components: dict) -> Tuple[List[float], List[float]]:
    # with open(path, "r", encoding="utf-8") as f:
    #     data = json.load(f)

    #items = data.get("story_components") or data.get("points") or data
    items = story_components
    xs, ys = [], []
    for it in items:
        x = it.get("modified_end_time", it.get("end_time"))
        y = it.get("modified_end_fortune_score", it.get("end_fortune_score"))
        if x is None or y is None:
            continue
        xs.append(float(x)); ys.append(float(y))

    if not xs or not ys or len(xs) != len(ys):
        raise ValueError("Could not parse time/emotion series from JSON.")

    pts = sorted(zip(xs, ys), key=lambda p: p[0])
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]

    # normalize x to [0,1]
    xmin, xmax = xs[0], xs[-1]
    span = xmax - xmin if xmax != xmin else 1.0
    xs = [(x - xmin) / span for x in xs]
    return xs, ys

# --------------------
# Geometry helpers
# --------------------
def rdp(points: List[Tuple[float,float]], eps: float) -> List[Tuple[float,float]]:
    if len(points) < 3:
        return points
    x0,y0 = points[0]; x1,y1 = points[-1]
    def perp(x,y):
        denom = math.hypot(x1-x0, y1-y0) or 1e-9
        return abs((y1-y0)*x - (x1-x0)*y + x1*y0 - y1*x0) / denom
    idx, dmax = 0, -1.0
    for i in range(1, len(points)-1):
        d = perp(*points[i])
        if d > dmax: idx, dmax = i, d
    if dmax > eps:
        left = rdp(points[:idx+1], eps)
        right = rdp(points[idx:], eps)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]

def sign_with_zero(dy: float, R: float) -> int:
    if abs(dy) < SLOPE_ZERO_FRAC * R: return 0
    return 1 if dy > 0 else -1

# --------------------
# Core: segmentation
# --------------------
def to_segments(xs: List[float], ys: List[float], simplify: bool = True) -> List[Segment]:
    assert len(xs) == len(ys) >= 2
    y_min, y_max = min(ys), max(ys)
    R = max(y_max - y_min, 1e-9)

    pts = list(zip(xs, ys))
    if simplify:
        eps = EPSILON_RDP_FACTOR * R
        pts = rdp(pts, eps=eps)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]

    # Build monotone runs by slope sign
    runs: List[Tuple[int,int]] = []
    start = 0
    prev_sign = sign_with_zero(ys[1] - ys[0], R)
    for i in range(1, len(xs)-1):
        s = sign_with_zero(ys[i+1] - ys[i], R)
        if s != prev_sign and not (s == 0 and prev_sign == 0):
            runs.append((start, i))
            start = i
            prev_sign = s if s != 0 else prev_sign
    runs.append((start, len(xs)-1))

    segs: List[Segment] = []
    for a,b in runs:
        x0,y0 = xs[a], ys[a]
        x1,y1 = xs[b], ys[b]
        dx = max(x1 - x0, 0.0)
        dy = y1 - y0
        dy_norm = abs(dy) / R

        # Drop micro-noise
        if dx < NOISE_DX_MIN and dy_norm < NOISE_DY_MAX:
            continue

        # Direction / flat
        if dy_norm < FLAT_DY_MAX and dx >= FLAT_DX_MIN:
            direction: Literal["up","down","flat"] = "flat"
        else:
            s = sign_with_zero(dy, R)
            direction = "up" if s > 0 else ("down" if s < 0 else "flat")

        # Enforce minimal span for non-flats unless obviously huge
        if direction != "flat" and dx < SEG_DX_MIN and dy_norm < MEDIUM_MIN:
            continue

        # Placeholders; arrows set later by relative gating
        segs.append(Segment(direction, x0, x1, y0, y1, dy_norm, arrows="→"))

    return segs

# --------------------
# Magnitudes with RELATIVE gating
# --------------------
def assign_arrows_with_relative_gating(segs: List[Segment]) -> None:
    """Mutates segs[].arrows in place, with conservative use of triple arrows."""
    # Convert tiny moves to flats early
    for s in segs:
        if s.dir != "flat" and s.dy_norm < SMALL_MIN:
            s.dir = "flat"
            s.arrows = "→"

    nonflat = [s for s in segs if s.dir != "flat"]
    if not nonflat:
        return

    # Single non-flat: no relative info, so no triples unless it is really huge
    if len(nonflat) == 1:
        s = nonflat[0]
        if s.dy_norm >= LARGE_ABS_MIN and (s.x1 - s.x0) >= TRIPLE_DX_MIN:
            s.arrows = "↑↑↑" if s.dir == "up" else "↓↓↓"
        elif s.dy_norm >= MEDIUM_MIN:
            s.arrows = "↑↑" if s.dir == "up" else "↓↓"
        else:
            s.arrows = "↑" if s.dir == "up" else "↓"
        return

    mags = [s.dy_norm for s in nonflat]
    dmin, dmax = min(mags), max(mags)
    spread = dmax - dmin
    ratio  = dmax / max(dmin, 1e-9)

    # If all similar → only singles
    similar = (ratio < DISTINCT_RATIO) and (spread < DISTINCT_ABS)
    if similar:
        for s in nonflat:
            s.arrows = "↑" if s.dir == "up" else "↓"
        return

    # Base assignment: decide single vs. double by absolute + relative
    # (We intentionally do NOT assign any triple yet.)
    for s in nonflat:
        rel = (s.dy_norm - dmin) / (spread + 1e-9)  # 0..1 within the set
        if s.dy_norm >= MEDIUM_MIN and rel >= REL_MED_EDGE:
            s.arrows = "↑↑" if s.dir == "up" else "↓↓"
        else:
            s.arrows = "↑" if s.dir == "up" else "↓"

    # Triple-candidate evaluation: extremely conservative
    # - Only the largest segment can be triple
    # - Must pass absolute floor, relative dominance, relative position, and width tests
    largest = max(nonflat, key=lambda s: s.dy_norm)
    second  = max([s for s in nonflat if s is not largest], key=lambda s: s.dy_norm)
    rel_pos = (largest.dy_norm - dmin) / (spread + 1e-9)
    dx_span = largest.x1 - largest.x0

    share = largest.dy_norm / (sum(mags) + 1e-9)
    triple_ok = (
        largest.dy_norm >= LARGE_ABS_MIN and
        dx_span >= TRIPLE_DX_MIN and
        share   >= 0.45 and                 # NEW: “dominates the curve” gate
        largest.dy_norm >= second.dy_norm * LARGE_REL_DOM
    )

    if triple_ok:
        largest.arrows = "↑↑↑" if largest.dir == "up" else "↓↓↓"
    # else it stays as assigned (single or double)

# --------------------
# Merge & stringify
# --------------------
def merge_adjacent_equal(segs: List[Segment]) -> List[Segment]:
    merged: List[Segment] = []
    for s in segs:
        if merged and merged[-1].arrows == s.arrows:
            last = merged[-1]
            merged[-1] = Segment(
                dir=last.dir,
                x0=last.x0,
                x1=s.x1,
                y0=last.y0,
                y1=s.y1,
                dy_norm=last.dy_norm,   # leave dy_norm as recorded for first piece
                arrows=last.arrows
            )
        else:
            merged.append(s)
    return merged

def segments_to_symbolic(segs: List[Segment]) -> str:
    return " ".join(s.arrows for s in segs)

# --------------------
# Public API
# --------------------
def analyze_series(xs: List[float], ys: List[float], simplify: bool = True) -> dict:
    segs = to_segments(xs, ys, simplify=simplify)
    assign_arrows_with_relative_gating(segs)
    segs = merge_adjacent_equal(segs)
    width_sum = sum(max(s.x1 - s.x0, 0.0) for s in segs)
    return {
        "segments": [s.to_public() for s in segs],
        "symbolic": segments_to_symbolic(segs),
        "width_sum": round(width_sum, 3)
    }

#########

from typing import List, Tuple, Literal, Optional

Archetype = Literal[
    "Rags to Riches",
    "From Bad to Worse",
    "Man in Hole",
    "Icarus",
    "Boy Meets Girl",
    "Cinderella",
    "Oedipus",
    "Other",
]

def _token_dir(tok: str) -> Literal["U","D","F"]:
    """Map a token like '↑↑', '↓↓↓', '→' to a direction code U/D/F."""
    if "↑" in tok: return "U"
    if "↓" in tok: return "D"
    return "F"  # flats (→)

def _token_mag(tok: str) -> int:
    """Return arrow count (↑↑↑ -> 3, ↓ -> 1, → -> 0)."""
    return tok.count("↑") + tok.count("↓")

def _collapse_consecutive(dirs: List[str], toks: List[str]) -> Tuple[List[str], List[str]]:
    """
    Collapse consecutive identical directions so e.g.
    ['D','D','F','U','U'] -> ['D','F','U'] and keep one representative token
    (used later for Cinderella magnitude check).
    """
    if not dirs: return [], []
    out_dirs, out_toks = [dirs[0]], [toks[0]]
    for d, t in zip(dirs[1:], toks[1:]):
        if d == out_dirs[-1]:
            # merge by keeping the first representative token (direction only matters here)
            continue
        out_dirs.append(d)
        out_toks.append(t)
    return out_dirs, out_toks

def _strip_interior_flats(dirs: List[str], toks: List[str]) -> Tuple[List[str], List[str]]:
    """
    Drop flats except a *leading* flat (kept for Cinderella).
    This makes patterns robust to little '→' plateaus inside larger moves.
    """
    if not dirs: return [], []
    out_dirs, out_toks = [], []
    for i, (d, t) in enumerate(zip(dirs, toks)):
        if d == "F" and i != 0:
            continue
        out_dirs.append(d)
        out_toks.append(t)
    return out_dirs, out_toks

def _first_and_last_rise_mag(toks: List[str]) -> Tuple[Optional[int], Optional[int]]:
    """Find magnitudes of first and last 'U' tokens (None if absent)."""
    first = next(( _token_mag(t) for t in toks if "↑" in t ), None)
    last  = next(( _token_mag(t) for t in reversed(toks) if "↑" in t ), None)
    return first, last

def categorize_symbolic(symbolic: str) -> Archetype:
    """
    Map a symbolic arrow string (e.g., '↓ → ↑↑') to a story archetype.

    Rules (magnitude-agnostic *except* Cinderella):
      1-part:  'U' -> Rags to Riches; 'D' -> From Bad to Worse
      2-part:  'D U' -> Man in Hole; 'U D' -> Icarus
      3-part:  'U D U' -> Boy Meets Girl
      4-part:  'F U D U' with last rise > first rise -> Cinderella
      Else:    Other
    """
    # Normalize whitespace and split into tokens as authored by your pipeline
    toks_raw = [tok.strip() for tok in symbolic.strip().split() if tok.strip()]
    if not toks_raw:
        return "Other"

    # Directions for each token, then collapse consecutive duplicates
    dirs_raw = [_token_dir(t) for t in toks_raw]
    dirs, toks = _collapse_consecutive(dirs_raw, toks_raw)

    # Keep a leading flat (for Cinderella), drop interior flats for robust matching
    dirs_nf, toks_nf = _strip_interior_flats(dirs, toks)

    # Build a magnitude-agnostic key using only directions
    key = " ".join(dirs_nf)

    # 1-part patterns
    if key == "U":
        return "Rags to Riches"
    if key == "D":
        return "From Bad to Worse"

    # 2-part patterns
    if key == "D U":
        return "Man in Hole"
    if key == "U D":
        return "Icarus"

    # 3-part patterns
    if key == "U D U":
        return "Boy Meets Girl"
    if key == "D U D": return "Oedipus"  # <-- added


    # 4-part (Cinderella): requires a *leading* flat and U D U structure
    # We'll check the original collapsed-with-leading-flat sequence (dirs, toks)
    # expecting something like ['F','U','D','U'] possibly with interior flats already removed.
    if len(dirs) >= 4 and dirs[0] == "F":
        # Check the non-flat order after leading flat
        dirs_after_lead = [d for d in dirs[1:] if d != "F"]
        if dirs_after_lead == ["U", "D", "U"]:
            # Magnitude condition: final rise > first rise
            first_u_mag, last_u_mag = _first_and_last_rise_mag(toks)
            if first_u_mag is not None and last_u_mag is not None and last_u_mag > first_u_mag:
                return "Cinderella"

    # Everything else (including ≥5 directional parts, or flats sprinkled in other ways)
    return "Other"


# ---------- Write results back to JSON + CLI ----------

# def write_symbolic_and_archetype_to_json(generated_analysis_path: str, simplify: bool = True, json_file_type: str = "general") -> dict:
def get_story_symbolic_and_archetype(story_components: dict, simplify: bool = True) -> dict:

    """
    Loads the JSON story data, computes the symbolic representation and archetype,
    writes them back to the same JSON file, and returns a small summary dict.
    """
    # Compute from the points in the JSON
    xs, ys = load_points_from_json(story_components)
    out = analyze_series(xs, ys, simplify=simplify)
    symbolic_rep = out["symbolic"]
    archetype = categorize_symbolic(symbolic_rep)

    return symbolic_rep,  archetype

 



### ADDING 11/3/2025 to compare story and product shape but not considering magntidue

import re

# Matches runs of arrow glyphs (the shapes you generate use these three).
_ARROWS_RE = re.compile(r"[↑↓→]+")

def _direction_tokens(symbolic: str) -> list[str]:
    """
    Convert a symbolic shape string like '↓ ↑ ↓ ↑↑↑' into direction-only tokens:
    - Any run of ups (↑ / ↑↑ / ↑↑↑) becomes '↑'
    - Any run of downs (↓ / ↓↓ / ↓↓↓) becomes '↓'
    - Any run of flats (→ / →→ / …) becomes '→'
    Non-arrow characters (spaces, punctuation) are ignored.
    """
    if not symbolic:
        return []
    tokens = []
    for chunk in _ARROWS_RE.findall(symbolic):
        if "↑" in chunk:
            tokens.append("↑")
        elif "↓" in chunk:
            tokens.append("↓")
        else:
            # fall back to flat for anything made of '→'
            tokens.append("→")
    return tokens

def shapes_equal_ignore_magnitude(a: str, b: str) -> bool:
    """
    Return True if two symbolic representations have the same *direction sequence*
    ignoring magnitude differences (↑ vs ↑↑ vs ↑↑↑), e.g.:

        '↓ ↑ ↓ ↑↑↑'  ==  '↓ ↑ ↓ ↑↑'   -> True
        '→ ↑ ↓'      ==  '→ ↑↓'       -> False (different step structure)
        '↑ ↓ ↑'      ==  '↑ ↓ ↑ →'    -> False (extra flat at end)

    This comparison treats only the order of directions as significant.
    """
    return _direction_tokens(a) == _direction_tokens(b)

def shape_direction_diff(a: str, b: str) -> dict:
    """
    Optional helper: get a small diff summary for logging.
    Returns which positions differ (by direction, not magnitude).
    """
    A, B = _direction_tokens(a), _direction_tokens(b)
    maxlen = max(len(A), len(B))
    diffs = []
    for i in range(maxlen):
        ai = A[i] if i < len(A) else None
        bi = B[i] if i < len(B) else None
        if ai != bi:
            diffs.append({"index": i, "a": ai, "b": bi})
    return {"a_tokens": A, "b_tokens": B, "diffs": diffs}
