# upsample_template.py
from PIL import Image, ImageFilter
import math, json, os

def _dist(a,b):
    return math.hypot(b[0]-a[0], b[1]-a[1])

def _quad_from_slot(s):
    if "quad" in s: return s["quad"]
    x,y,w,h = s["rect"]
    return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]

def _short_side(q):
    w = 0.5*(_dist(q[0],q[1]) + _dist(q[3],q[2]))
    h = 0.5*(_dist(q[0],q[3]) + _dist(q[1],q[2]))
    return min(w,h), (w,h)

def compute_scale(slots, target_short_side=1200, min_scale=2):
    shorts = []
    for s in slots:
        q = _quad_from_slot(s)
        short,_ = _short_side(q)
        shorts.append(short)
    curr_min = min(shorts)
    return max(min_scale, int(math.ceil(target_short_side / max(curr_min,1))))

def upscale_template_and_slots(in_path, out_path, slots,
                               target_short_side=1200,
                               min_scale=2,
                               unsharp=(0.6,120,1)):
    scale = compute_scale(slots, target_short_side, min_scale)
    img = Image.open(in_path).convert("RGB")
    up  = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    up  = up.filter(ImageFilter.UnsharpMask(*unsharp))  # mild crisping
    up.save(out_path, "PNG")

    scaled_slots = []
    for s in slots:
        t = dict(s)
        if "rect" in s:
            x,y,w,h = s["rect"]
            t["rect"] = (x*scale, y*scale, w*scale, h*scale)
        if "quad" in s:
            t["quad"] = [(x*scale, y*scale) for (x,y) in _quad_from_slot(s)]
        scaled_slots.append(t)
    return scale, scaled_slots

def report_slot_sizes(slots):
    for i,s in enumerate(slots):
        q = _quad_from_slot(s)
        short,(w,h) = _short_side(q)
        print(f"slot {i}: {int(w)}×{int(h)} px (short={int(short)})")

from PIL import Image, ImageFilter
from PIL.Image import Resampling
import math, json, os

def upscale_paper_clip(in_path, out_path, slots,
                               target_short_side=1200,
                               min_scale=2,
                               unsharp=(0.6,120,1)):
    scale = compute_scale(slots, target_short_side, min_scale)

    # Keep transparency if present (PNG clips)
    img = Image.open(in_path).convert("RGBA")

    # High-quality resize
    up = img.resize((img.width*scale, img.height*scale), Resampling.LANCZOS)

    # Sharpen only the color channels (alpha untouched)
    r, g, b, a = up.split()
    rgb_sharp = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(*unsharp))
    up = Image.merge("RGBA", (*rgb_sharp.split(), a))

    # Save as PNG to preserve alpha
    up.save(out_path, "PNG")

    # Scale any slot metadata you pass in
    scaled_slots = []
    for s in slots:
        t = dict(s)
        if "rect" in s:
            x,y,w,h = s["rect"]
            t["rect"] = (x*scale, y*scale, w*scale, h*scale)
        if "quad" in s:
            t["quad"] = [(x*scale, y*scale) for (x,y) in _quad_from_slot(s)]
        scaled_slots.append(t)
    return scale, scaled_slots



## POSTER SCALE UO
# poster_quad = [(30, 55), (853, 55), (853, 1102), (30, 1102)]
# poster_slots = [{"quad": poster_quad}]
# scale_poster, poster_slots_big = upscale_template_and_slots(
#     in_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base.jpeg",
#     out_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base@BIG.png",
#     slots=poster_slots,
#     target_short_side=1200,   # bump to 1400–1500 if you want even crisper
#     min_scale=2
# )
# print("WALL scale used:", scale_poster)
# report_slot_sizes(poster_slots_big)
# # (optional) Save scaled slots for reuse
# with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_poster_no_frame_base@BIG.slots.json","w") as f:
#     json.dump(poster_slots_big, f)


#UPSCALE 1 FRAM ON WALL
# 1) 11×14 — 1 frame on wall
# wall_quad = [(329,225),(693,225),(693,698),(329,698)]
# wall_slots = [{"quad": wall_quad}]

# scale_wall, wall_slots_big = upscale_template_and_slots(
#     in_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall.jpeg",
#     out_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.png",
#     slots=wall_slots,
#     target_short_side=1200,   # bump to 1400–1500 if you want even crisper
#     min_scale=2
# )
# print("WALL scale used:", scale_wall)
# report_slot_sizes(wall_slots_big)
# # (optional) Save scaled slots for reuse
# with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.slots.json","w") as f:
#     json.dump(wall_slots_big, f)



# 11x14 FRAME ON TABLE
table_quad = [(238,222),(722,222),(722,853),(238,853)]
table_slots = [{"quad": table_quad}]

scale_table, table_slots_big = upscale_template_and_slots(
    in_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2.jpeg",
    out_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2@BIG.png",
    # in_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2_wood.png",
    # out_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2_wood@BIG.png",
    slots=table_slots,
    target_short_side=1200,
    min_scale=2
)
print("TABLE scale used:", scale_table)
report_slot_sizes(table_slots_big)
with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2_wood@BIG.slots.json","w") as f:
    json.dump(table_slots_big, f)




# UPSCALE 3 FRAMES ON WALL
# three_quads = [
#     [(125,340),(353,340),(353,637),(125,637)],
#     [(398,340),(626,340),(626,637),(398,637)],
#     [(672,340),(900,340),(900,637),(672,637)],
# ]
# three_slots = [{"quad": q} for q in three_quads]

# # 1) Upscale the template + coords
# scale, slots_big = upscale_template_and_slots(
#     in_path  = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall.jpeg",
#     out_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall@BIG.png",
#     slots    = three_slots,
#     target_short_side=1200,   # aim for ≥1200 px short side per opening
#     min_scale=2               # at least 2× even if already big
# )

# print("scale used:", scale)
# report_slot_sizes(slots_big)

# # (optional) Save slots to JSON for reuse
# with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall@BIG.slots.json","w") as f:
#     json.dump(slots_big, f)



#UPSCALING CLIP

# paths
clip_in  = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/gold-clip.png"
clip_out = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/gold-clip@BIG.png"

# describe the full image as a single 'slot' so scale is computed properly
w, h = Image.open(clip_in).size
clip_slots = [{"rect": (0, 0, w, h)}]

# upscale: aim for a larger short side; 1600–1800 is a good target for crisp rotation/resampling
scale_clip, _ = upscale_paper_clip(
    in_path=clip_in,
    out_path=clip_out,
    slots=clip_slots,
    target_short_side=1600,   # try 1800 if you want bigger
    min_scale=2,              # at least 2×
    unsharp=(0.6, 120, 1)     # mild crisping
)

print("Clip scale used:", scale_clip)
report_slot_sizes([{"rect": (0, 0, w*scale_clip, h*scale_clip)}])
# Now use `clip_out` in your overlay step
