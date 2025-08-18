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
# Tunable thresholds (absolute)
# --------------------
EPSILON_RDP_FACTOR = 0.02
SLOPE_ZERO_FRAC    = 0.005

NOISE_DX_MIN       = 0.06
NOISE_DY_MAX       = 0.04

FLAT_DY_MAX        = 0.05
FLAT_DX_MIN        = 0.10

SMALL_MIN          = 0.12
MEDIUM_MIN         = 0.25
LARGE_MIN          = 0.7      # soft gate used with relative checks (kept as context)
LARGE_ABS_MIN      = 0.8      # NEW: hard floor for triple arrows

SEG_DX_MIN         = 0.07

# --------------------
# Relative distinctness gating
# --------------------
DISTINCT_RATIO     = 1.8
DISTINCT_ABS       = 0.15

REL_LARGE_EDGE     = 0.88      # stricter: must be near the top of the spread
REL_MED_EDGE       = 0.50      # slightly stricter for doubles

TRIPLE_DX_MIN      = 0.18      # NEW: triple must span at least 15% of width
LARGE_REL_DOM      = 2      # NEW: triple must be ≥1.35x the second-largest dy_norm

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
def load_points_from_json(path: str) -> Tuple[List[float], List[float]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("story_components") or data.get("points") or data
    xs, ys = [], []
    for it in items:
        x = it.get("modified_end_time", it.get("end_time"))
        y = it.get("modified_end_emotional_score", it.get("end_emotional_score"))
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

    triple_ok = (
        largest.dy_norm >= LARGE_ABS_MIN and
        rel_pos >= REL_LARGE_EDGE and
        dx_span >= TRIPLE_DX_MIN and
        largest.dy_norm >= LARGE_MIN and       # soft guard for context
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


path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/for-whom-the-bell-tolls_robert-jordan_8x10.json"
#path = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet.json'
#path = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby_jay-gatsby.json'
xs, ys = load_points_from_json(path)
out = analyze_series(xs, ys, simplify=True)
print(json.dumps(out, ensure_ascii=False, indent=2))

