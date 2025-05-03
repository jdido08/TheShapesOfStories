#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import argparse
import sys
import os
import re
import warnings
import math

# --- Configuration ---
NAMESPACES = {
    'svg': 'http://www.w3.org/2000/svg',
    'xlink': 'http://www.w3.org/1999/xlink'
}
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix if prefix != 'svg' else '', uri)

# --- Video.tsx Template (Keep as is from previous answer) ---
VIDEO_TSX_TEMPLATE = """\
// {output_filename}
// ... (Same TSX template as the previous answer with Axes first timing) ...
import React, {{ useRef, useEffect }} from 'react';
import {{
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  useVideoConfig,
}} from 'remotion';

// The processed SVG content is embedded here
const RAW_SVG = `{modified_svg_content}`;

// --- Animation Configuration (Axes First Timing) ---
const INITIAL_DELAY = 10; // Frames before anything starts

const AXES_START_FRAME = INITIAL_DELAY;
const AXES_FADE_IN_DURATION = 30;
const AXES_END_FADE_IN_FRAME = AXES_START_FRAME + AXES_FADE_IN_DURATION;

// Start title after axes finish fading in
const AXES_TITLE_DELAY = 5;
const TITLE_START_FRAME = AXES_END_FADE_IN_FRAME + AXES_TITLE_DELAY;
const TITLE_FADE_DURATION = 40;
const TITLE_END_FRAME = TITLE_START_FRAME + TITLE_FADE_DURATION;

// Start name slightly after title
const TITLE_NAME_DELAY = 10;
const NAME_START_FRAME = TITLE_START_FRAME + TITLE_NAME_DELAY;
const NAME_FADE_DURATION = 40;
const NAME_END_FRAME = NAME_START_FRAME + NAME_FADE_DURATION;

// Main path starts after the *later* of title or name finishes
const TITLE_NAME_END_FRAME = Math.max(TITLE_END_FRAME, NAME_END_FRAME);
const MAIN_PATH_START_DELAY = 15;
const MAIN_PATH_START_FRAME = TITLE_NAME_END_FRAME + MAIN_PATH_START_DELAY;

const TEXT_REVEAL_SPEED = 1.5; // For main path
const TEXT_FADE_DURATION = 15; // For main path

// Axes fade out near the end
const END_DELAY = 15; // Frames before the absolute end
const AXES_FADE_OUT_DURATION = 30;

// --- Component ---
export const {component_name}: React.FC = () => {{
  const containerRef = useRef<HTMLDivElement>(null);
  const frame = useCurrentFrame();
  const {{ fps, durationInFrames }} = useVideoConfig();

  const mainTextElementsRef = useRef<SVGGraphicsElement[]>([]);
  const titleGroupRef = useRef<SVGGElement | null>(null);
  const nameGroupRef = useRef<SVGGElement | null>(null);
  const axesGroupRef = useRef<SVGGElement | null>(null); // Ref for axes

  // --- Calculate AXES_FADE_OUT_START_FRAME based on actual duration ---
  // Ensure start frame is not negative if duration is short
  const AXES_FADE_OUT_START_FRAME = Math.max(0, durationInFrames - AXES_FADE_OUT_DURATION - END_DELAY);
  const AXES_FADE_OUT_END_FRAME = AXES_FADE_OUT_START_FRAME + AXES_FADE_OUT_DURATION;
  // ---

  useEffect(() => {{
    if (!containerRef.current) return;
    const svgElement = containerRef.current.querySelector('svg');
    if (!svgElement) return;

    // --- Select Elements ---
    axesGroupRef.current = svgElement.querySelector<SVGGElement>('#axes-group'); // Select axes
    titleGroupRef.current = svgElement.querySelector<SVGGElement>('#title-group');
    nameGroupRef.current = svgElement.querySelector<SVGGElement>('#name-group');
    const mainTextGroup = svgElement.querySelector<SVGGElement>('#main-text-path');
    if (mainTextGroup) {{
         mainTextElementsRef.current = Array.from(
           mainTextGroup.querySelectorAll<SVGGraphicsElement>(':scope > use, :scope > path, :scope > text, :scope > g')
         );
    }} else {{ mainTextElementsRef.current = []; }}

    // --- Animate Axes (Fade In / Fade Out) ---
    if (axesGroupRef.current) {{
       const fadeInOpacity = interpolate(frame, [AXES_START_FRAME, AXES_END_FADE_IN_FRAME], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
       const fadeOutOpacity = interpolate(frame, [AXES_FADE_OUT_START_FRAME, AXES_FADE_OUT_END_FRAME], [1, 0], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
       const axesOpacity = frame >= AXES_FADE_OUT_START_FRAME ? fadeOutOpacity : (frame >= AXES_START_FRAME ? fadeInOpacity : 0);
       axesGroupRef.current.style.opacity = String(axesOpacity);
    }}

    // --- Animate Title ---
    if (titleGroupRef.current) {{
      const titleOpacity = interpolate(frame, [TITLE_START_FRAME, TITLE_END_FRAME], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
      const titleTranslateY = interpolate(frame, [TITLE_START_FRAME, TITLE_END_FRAME], [15, 0], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)}});
      if (frame >= TITLE_START_FRAME) {{
        titleGroupRef.current.style.opacity = String(titleOpacity);
        titleGroupRef.current.style.transform = `translateY(${{titleTranslateY}}px)`;
      }} else {{
        titleGroupRef.current.style.opacity = '0';
        titleGroupRef.current.style.transform = `translateY(15px)`;
      }}
      titleGroupRef.current.querySelectorAll<SVGGraphicsElement>('text, path, tspan, use, g').forEach((el) => {{ el.style.stroke = 'none'; }});
    }}

    // --- Animate Name ---
    if (nameGroupRef.current) {{
      const nameOpacity = interpolate(frame, [NAME_START_FRAME, NAME_END_FRAME], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
      const nameTranslateY = interpolate(frame, [NAME_START_FRAME, NAME_END_FRAME], [15, 0], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)}});
       if (frame >= NAME_START_FRAME) {{
         nameGroupRef.current.style.opacity = String(nameOpacity);
         nameGroupRef.current.style.transform = `translateY(${{nameTranslateY}}px)`;
       }} else {{
         nameGroupRef.current.style.opacity = '0';
         nameGroupRef.current.style.transform = `translateY(15px)`;
       }}
        nameGroupRef.current.querySelectorAll<SVGGraphicsElement>('text, path, tspan, use, g').forEach((el) => {{ el.style.stroke = 'none'; }});
    }}

    // --- Animate Main Text Path ---
    const totalMainElements = mainTextElementsRef.current.length;
    mainTextElementsRef.current.forEach((el, i) => {{
      const startRevealFrame = MAIN_PATH_START_FRAME + i * TEXT_REVEAL_SPEED;
      const endRevealFrame = startRevealFrame + TEXT_FADE_DURATION;
      const opacity = interpolate(frame, [startRevealFrame, endRevealFrame], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.ease) }});
      // Check if element has style before setting (TypeScript safety)
      if (el instanceof SVGElement && 'style' in el) {{
         (el as SVGGraphicsElement).style.opacity = frame >= startRevealFrame ? String(opacity) : '0';
         (el as SVGGraphicsElement).style.stroke = 'none';
      }}
    }});

  }}, [frame, durationInFrames, AXES_FADE_OUT_START_FRAME, AXES_FADE_OUT_END_FRAME]);

  // Initial setup effect
  useEffect(() => {{
    if (!containerRef.current) return;
    const svgElement = containerRef.current.querySelector('svg');
    if (!svgElement) return;
    const axes = svgElement.querySelector<SVGGElement>('#axes-group');
    const title = svgElement.querySelector<SVGGElement>('#title-group');
    const name = svgElement.querySelector<SVGGElement>('#name-group');
    const mainTextGroup = svgElement.querySelector<SVGGElement>('#main-text-path');

    if (axes) axes.style.opacity = '0';
    if (title) {{ title.style.opacity = '0'; title.style.transform = `translateY(15px)`; }}
    if (name) {{ name.style.opacity = '0'; name.style.transform = `translateY(15px)`; }}
    if (mainTextGroup) {{
       const mainTextElements = Array.from(mainTextGroup.querySelectorAll<SVGGraphicsElement>(':scope > use, :scope > path, :scope > text, :scope > g'));
        mainTextElements.forEach(el => {{
          if (el instanceof SVGElement && 'style' in el) {{ (el as SVGGraphicsElement).style.opacity = '0'; }}
        }});
    }}
  }}, []);

  return (
    <AbsoluteFill style={{{{ backgroundColor: '#2C3E50' }}}}>
      <div ref={{containerRef}} dangerouslySetInnerHTML={{{{ __html: RAW_SVG }}}} style={{{{ /* styles */ }}}} />
    </AbsoluteFill>
  );
}};
"""



# --- Helper Functions ---
def to_pascal_case(snake_str): # ... (same) ...
    snake_str = snake_str.replace('-', '_'); return "".join(w.capitalize() for w in snake_str.split('_'))
def generate_component_name(filename): # ... (same) ...
    base_name = os.path.splitext(os.path.basename(filename))[0]; base_name = re.sub(r'^[^a-zA-Z_]+', '', base_name)
    if not base_name or not base_name[0].isalpha(): base_name = "SvgAnimation" + base_name
    return to_pascal_case(base_name)
def is_graphical_element(element): # ... (same) ...
    svg_ns = NAMESPACES['svg']; graphical_tags = [f'{{{svg_ns}}}{t}' for t in ['g','path','text','rect','circle','ellipse','line','polyline','polygon','use','tspan']]
    if element.tag == f'{{{svg_ns}}}text' and (element.text is None or not element.text.strip()):
         tspans = element.findall(f'{{{svg_ns}}}tspan');
         if not any(t.text and t.text.strip() for t in tspans): return False
    return element.tag in graphical_tags
def is_inside_defs(element, parent_map): # ... (same) ...
    parent = parent_map.get(element); svg_ns = NAMESPACES['svg']
    while parent is not None:
        if parent.tag == f'{{{svg_ns}}}defs': return True
        parent = parent_map.get(parent)
    return False
# --- End Helpers ---


def process_svg_structural_v4(input_svg_path, width_in, height_in, dpi, margin_ratio, title_band_height, gap_above_title):
    """
    Reads SVG, ADDS axes group with visual adjustments, identifies Title/Name structurally,
    identifies Path by exclusion, and restructures.
    """
    try:
        tree = ET.parse(input_svg_path)
        root = tree.getroot()
        svg_ns = NAMESPACES['svg']
        parent_map = {c: p for p in root.iter() for c in p}

        # --- Calculate necessary dimensions ---
        design_width_px = int(width_in * dpi)
        design_height_px = int(height_in * dpi)
        margin_x = int(margin_ratio * design_width_px)
        margin_y = int(margin_ratio * design_height_px)
        drawable_width = design_width_px - 2 * margin_x
        drawable_height = (design_height_px - 2 * margin_y - title_band_height - gap_above_title)
        print(f"DEBUG: Drawable Area: {drawable_width}x{drawable_height} at ({margin_x},{margin_y})")
        if drawable_width <= 0 or drawable_height <= 0:
             print(f"ERROR: Calculated drawable dimensions non-positive.", file=sys.stderr); return None

        # --- Modify root <svg> tag ---
        root.set('width', '100%'); root.set('height', '100%')
        root.set('preserveAspectRatio', 'xMidYMid meet')
        if 'viewBox' not in root.attrib: print("Warning: Input SVG missing viewBox.", file=sys.stderr)

        # --- Find potential background rect ---
        background_rect = next((child for child in root if child.tag == f'{{{svg_ns}}}rect'), None)
        if background_rect is not None: print("DEBUG: Identified potential background rect.")

        # --- Create and Add Axes Group ---
        axes_group = ET.Element(f'{{{svg_ns}}}g', attrib={'id': 'axes-group'})
        # --- VISUAL ADJUSTMENTS ---
        axes_color = "#A9A9A9" # DarkGray
        axes_thickness = "10"   # <<< Increased thickness #3
        label_font_size = "75px" #16
        label_padding = -70#10    # Padding *inside* the drawable area for labels
        axis_horizontal_offset = 40#40 # <<< Pixels to shift GI axis left
        # --- END VISUAL ADJUSTMENTS ---

        # GI Axis (Vertical) - Shifted Left
        gi_axis_x_coord = margin_x - axis_horizontal_offset
        gi_axis_x = str(gi_axis_x_coord)
        gi_y1 = str(margin_y)
        gi_y2 = str(margin_y + drawable_height) # Stops before title gap

        gi_line = ET.SubElement(axes_group, f'{{{svg_ns}}}line', attrib={'x1': gi_axis_x, 'y1': gi_y1, 'x2': gi_axis_x, 'y2': gi_y2, 'stroke': axes_color, 'stroke-width': axes_thickness })
        # G Label (Above axis)
        g_label = ET.SubElement(axes_group, f'{{{svg_ns}}}text', attrib={'x': gi_axis_x, 'y': str(margin_y + label_padding), 'fill': axes_color, 'font-size': label_font_size, 'font-family': 'Sans', 'text-anchor': 'middle', 'dominant-baseline': 'hanging'}) # Adjusted baseline
        g_label.text = "G"
        # I Label (Below axis)
        i_label = ET.SubElement(axes_group, f'{{{svg_ns}}}text', attrib={'x': gi_axis_x, 'y': str(margin_y + drawable_height - label_padding), 'fill': axes_color, 'font-size': label_font_size, 'font-family': 'Sans', 'text-anchor': 'middle', 'dominant-baseline': 'alphabetic'}) # Adjusted baseline
        i_label.text = "I"

        # BE Axis (Horizontal) - Starts at shifted GI axis
        be_axis_y = str(margin_y + drawable_height / 2)
        be_x1 = gi_axis_x # Start horizontal axis at the new vertical axis position
        be_x2 = str(margin_x + drawable_width) # End at right margin

        be_line = ET.SubElement(axes_group, f'{{{svg_ns}}}line', attrib={'x1': be_x1, 'y1': be_axis_y, 'x2': be_x2, 'y2': be_axis_y, 'stroke': axes_color, 'stroke-width': axes_thickness})
        # B Label (Right of shifted GI axis)
        b_label = ET.SubElement(axes_group, f'{{{svg_ns}}}text', attrib={'x': str(gi_axis_x_coord + label_padding), 'y': be_axis_y, 'fill': axes_color, 'font-size': label_font_size, 'font-family': 'Sans', 'text-anchor': 'start', 'dominant-baseline': 'middle'}) # Adjusted anchor
        b_label.text = "B"
        # E Label (Left of right margin)
        e_label = ET.SubElement(axes_group, f'{{{svg_ns}}}text', attrib={'x': str(margin_x + drawable_width - label_padding), 'y': be_axis_y, 'fill': axes_color, 'font-size': label_font_size, 'font-family': 'Sans', 'text-anchor': 'end', 'dominant-baseline': 'middle'}) # Adjusted anchor
        e_label.text = "E"

        # Insert the axes group
        defs_element = root.find(f'{{{svg_ns}}}defs')
        insert_pos = list(root).index(defs_element) + 1 if defs_element is not None else 0
        if background_rect is not None:
            try: bg_index = list(root).index(background_rect); insert_pos = max(insert_pos, bg_index + 1)
            except ValueError: print("Warning: Background rect identified but not found during insertion.")
        root.insert(insert_pos, axes_group)
        print(f"DEBUG: Inserted axes-group at index {insert_pos}.")
        parent_map = {c: p for p in root.iter() for c in p} # Rebuild map

        # --- Identify Title and Name Groups ---
        # ... (Same logic as before) ...
        title_group, name_group = None, None
        excluded_tags = {f'{{{svg_ns}}}defs', f'{{{svg_ns}}}metadata', f'{{{svg_ns}}}style'}
        direct_g_children = [child for child in root if child.tag == f'{{{svg_ns}}}g' and child.get('id') != 'axes-group' and child not in excluded_tags]
        if len(direct_g_children) >= 2:
            name_group = direct_g_children[-1]; title_group = direct_g_children[-2]
            title_group.set('id', 'title-group'); name_group.set('id', 'name-group')
            print("Info: Assigned IDs to Title/Name groups.")
        else: print(f"Warning: Cannot ID Title/Name groups.", file=sys.stderr)

        # --- Identify Main Path Elements (Exclusion) ---
        # ... (Same filtering logic as before, excluding defs, axes, title, name, background) ...
        main_path_elements = []
        title_descendants = set(title_group.iter()) if title_group is not None else set()
        name_descendants = set(name_group.iter()) if name_group is not None else set()
        axes_descendants = set(axes_group.iter())
        for elem in root.iter():
            if not is_graphical_element(elem): continue
            if is_inside_defs(elem, parent_map): continue
            if elem == background_rect: continue # Skip background
            if elem == title_group or elem in title_descendants: continue
            if elem == name_group or elem in name_descendants: continue
            if elem == axes_group or elem in axes_descendants: continue

            parent = parent_map.get(elem)
            if parent is not None and parent.get('id') == 'main-text-path': continue

            is_child_of_already_added = False; current = parent
            while current is not None and current != root:
                if current in main_path_elements: is_child_of_already_added = True; break
                current = parent_map.get(current)
            if not is_child_of_already_added:
                 if elem.tag in [f'{{{svg_ns}}}use', f'{{{svg_ns}}}path', f'{{{svg_ns}}}text', f'{{{svg_ns}}}tspan']: main_path_elements.append(elem)
                 elif elem.tag == f'{{{svg_ns}}}g' and len(list(elem)) == 1 and is_graphical_element(list(elem)[0]): main_path_elements.append(elem)
        print(f"Info: Identified {len(main_path_elements)} top-level elements for 'main-text-path'.")

        # --- Restructure ---
        # ... (Same moving logic as before) ...
        main_path_parent_g = ET.Element(f'{{{svg_ns}}}g', attrib={'id': 'main-text-path'})
        elements_to_move = main_path_elements[:]
        moved_count = 0
        for elem in elements_to_move:
            parent = parent_map.get(elem)
            if parent is not None and parent != main_path_parent_g:
                try: parent.remove(elem); main_path_parent_g.append(elem); parent_map[elem] = main_path_parent_g; moved_count += 1
                except ValueError: pass
                except Exception as e_move: print(f"Error moving {elem.tag}: {e_move}", file=sys.stderr)
            elif parent == main_path_parent_g: pass
            elif elem != root: print(f"Warning: No parent for {elem.tag}", file=sys.stderr)
        print(f"Info: Moved {moved_count} elements to 'main-text-path'.")

        # Insert the new group
        # ... (Same insertion logic as before) ...
        insert_index = -1; insert_target = title_group if title_group is not None else name_group
        axes_index = -1
        try: axes_index = list(root).index(axes_group)
        except (ValueError, TypeError): pass
        if insert_target is not None:
             try:
                 temp_target = insert_target
                 while parent_map.get(temp_target) != root and parent_map.get(temp_target) is not None: temp_target = parent_map.get(temp_target)
                 if parent_map.get(temp_target) == root: insert_index = list(root).index(temp_target)
                 else: print("Warning: Title/Name group anchor not under root.")
             except ValueError: print("Warning: Title/Name group anchor not found (ValueError).")
        if insert_index != -1: final_insert_pos = max(axes_index + 1, 0) if axes_index != -1 else 0; final_insert_pos = min(final_insert_pos, insert_index)
        else: final_insert_pos = axes_index + 1 if axes_index != -1 else len(list(root))
        if final_insert_pos > len(list(root)): print(f"Warning: Insert index {final_insert_pos} out of bounds. Appending."); root.append(main_path_parent_g)
        else: root.insert(final_insert_pos, main_path_parent_g)
        print(f"Info: Inserted 'main-text-path' group at index {final_insert_pos}.")

        # --- Serialize ---
        ET.register_namespace('', NAMESPACES['svg'])
        modified_svg_string = ET.tostring(root, encoding='unicode', method='xml')
        modified_svg_string = re.sub(r'<ns0:', '<', modified_svg_string)
        modified_svg_string = re.sub(r'</ns0:', '</', modified_svg_string)
        modified_svg_string = re.sub(r'\s*xmlns="[^"]+"', '', modified_svg_string, flags=re.IGNORECASE)
        if 'xmlns="http://www.w3.org/2000/svg"' not in modified_svg_string[:100]:
             modified_svg_string = modified_svg_string.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        return modified_svg_string

    # --- Exception Handling ---
    except FileNotFoundError: print(f"Error: Input SVG not found at '{input_svg_path}'", file=sys.stderr); return None
    except ET.ParseError as e: print(f"Error: Parsing SVG '{input_svg_path}'. Error: {e}", file=sys.stderr); return None
    except Exception as e: print(f"Unexpected error in process_svg_structural_v4: {e}", file=sys.stderr); import traceback; traceback.print_exc(); return None


# --- Main Execution Block ---
def main():
    # ... (Same argument parsing as before) ...
    parser = argparse.ArgumentParser(description='Add Axes and restructure SVG for Remotion.')
    parser.add_argument('input_svg', help='Path to the original SVG generated by create_shape.')
    parser.add_argument('output_tsx', help='Path for the generated TSX file.')
    parser.add_argument('--width', type=float, required=True, help='Original design width in inches.')
    parser.add_argument('--height', type=float, required=True, help='Original design height in inches.')
    parser.add_argument('--dpi', type=int, default=300, help='DPI used for generation (default: 300).')
    parser.add_argument('--margin_ratio', type=float, default=0.05, help='Margin ratio used (default: 0.05).')
    parser.add_argument('--title_band_height', type=float, default=100, help='Calculated title band height in pixels (incl padding) (default: 0).')
    parser.add_argument('--gap_above_title', type=float, default=70, help='Gap above title in pixels (default: 20).')
    args = parser.parse_args()

    print(f"Processing SVG (adding axes): {args.input_svg}")
    modified_svg = process_svg_structural_v4(
        args.input_svg, args.width, args.height, args.dpi,
        args.margin_ratio, args.title_band_height, args.gap_above_title
    )

    if modified_svg:
        # ... (Same debug save, TSX generation, file writing as before) ...
        debug_svg_path = os.path.splitext(args.output_tsx)[0] + "_debug.svg"
        try:
            with open(debug_svg_path, "w", encoding="utf-8") as f_debug: f_debug.write(modified_svg)
            print(f"DEBUG: Saved modified SVG structure to: {debug_svg_path}")
        except Exception as e_debug: print(f"Warning: Could not save debug SVG: {e_debug}")
        escaped_svg = modified_svg.replace('`', '\\`').replace('${', '$\\{')
        component_name = generate_component_name(args.output_tsx)
        print(f"Generating component: {component_name} in {args.output_tsx}")
        tsx_content = VIDEO_TSX_TEMPLATE.format(modified_svg_content=escaped_svg, component_name=component_name, output_filename=os.path.basename(args.output_tsx))
        try:
            os.makedirs(os.path.dirname(args.output_tsx), exist_ok=True)
            with open(args.output_tsx, 'w', encoding='utf-8') as f: f.write(tsx_content)
            print(f"Successfully created/updated: {args.output_tsx}")
            print(f"\nReminder: Update 'src/RemotionRoot.tsx'.")
            warnings.warn("Verify animation. Inspect *_debug.svg.", UserWarning)
        except IOError as e: print(f"Error writing to '{args.output_tsx}': {e}", file=sys.stderr)
        except Exception as e: print(f"Unexpected error writing file: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()