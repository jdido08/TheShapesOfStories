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






#UPSCALE 1 FRAM ON WALL


# 1) 11×14 — 1 frame on wall
wall_quad = [(329,225),(693,225),(693,698),(329,698)]
wall_slots = [{"quad": wall_quad}]

scale_wall, wall_slots_big = upscale_template_and_slots(
    in_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall.jpeg",
    out_path= "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.png",
    slots=wall_slots,
    target_short_side=1200,   # bump to 1400–1500 if you want even crisper
    min_scale=2
)
print("WALL scale used:", scale_wall)
report_slot_sizes(wall_slots_big)
# (optional) Save scaled slots for reuse
with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall@BIG.slots.json","w") as f:
    json.dump(wall_slots_big, f)



# 11x14 FRAME ON TABLE
table_quad = [(238,222),(722,222),(722,853),(238,853)]
table_slots = [{"quad": table_quad}]

scale_table, table_slots_big = upscale_template_and_slots(
    in_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2.jpeg",
    out_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2@BIG.png",
    slots=table_slots,
    target_short_side=1200,
    min_scale=2
)
print("TABLE scale used:", scale_table)
report_slot_sizes(table_slots_big)
with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2@BIG.slots.json","w") as f:
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
