"""
Spacing Optimizer for The Shapes of Stories
============================================

This module provides optimized binary-search-based spacing adjustment
to replace the iterative approach in product_shape.py.

Integration: Import these functions into product_shape.py and replace
the spacing adjustment logic in the curve_too_short and curve_too_long
branches.

Author: Claude (for John Mike DiDonato)
"""

import numpy as np
import math
from gi.repository import Pango, PangoCairo
from shapely.geometry import Polygon
from shapely.affinity import rotate as shapely_rotate
import shapely.affinity

# Configuration constants - adjust these to tune behavior
SPACE_MULTIPLIER_MIN = 0.8    # Minimum allowed space width multiplier
SPACE_MULTIPLIER_MAX = 1.35   # Maximum allowed (slightly tightened from 1.5)
BINARY_SEARCH_ITERATIONS = 12  # Gives precision of ~0.0004
FIT_TOLERANCE = 0.02          # 2% tolerance for "close enough" fits


def get_standard_space_width(pangocairo_context, font_desc):
    """
    Gets the pixel width of a standard space character for the given font.
    """
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_font_description(font_desc)
    layout.set_text(" ", -1)
    width, _ = layout.get_pixel_size()
    return width if width > 0 else 1


def test_text_fit_on_curve(
    x_values_scaled,
    y_values_scaled,
    text,
    pangocairo_context,
    font_desc,
    spaces_width_multiplier,
    existing_boxes,
    margin_x,
    margin_y,
    design_width,
    design_height
):
    """
    Quick test if text fits on curve WITHOUT actually rendering.
    
    This is a lightweight version of draw_text_on_curve that only checks
    if the text fits, without creating Cairo drawing commands.
    
    Returns:
        tuple: (status, final_distance, total_curve_length)
            status: "fits" | "too_short" | "too_long"
            final_distance: how far along the curve the text ended
            total_curve_length: total length of the curve
    """
    # Calculate curve properties
    x_arr = np.array(x_values_scaled)
    y_arr = np.array(y_values_scaled)
    
    segment_lengths = np.hypot(np.diff(x_arr), np.diff(y_arr))
    total_curve_length = np.sum(segment_lengths)
    cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
    
    # Get standard space width for this font
    standard_space_width = get_standard_space_width(pangocairo_context, font_desc)
    
    # Track position along curve
    distance_along_curve = 0.0
    idx_on_curve = 0
    space_count = 0
    
    def get_tangent_angle(idx):
        if idx == 0:
            dx = x_arr[1] - x_arr[0]
            dy = y_arr[1] - y_arr[0]
        elif idx >= len(x_arr) - 1:
            dx = x_arr[-1] - x_arr[-2]
            dy = y_arr[-1] - y_arr[-2]
        else:
            dx = x_arr[idx + 1] - x_arr[idx - 1]
            dy = y_arr[idx + 1] - y_arr[idx - 1]
        return math.atan2(dy, dx)
    
    # Process each character
    for char in text:
        # Measure character
        layout = Pango.Layout.new(pangocairo_context)
        layout.set_font_description(font_desc)
        layout.set_text(char, -1)
        char_width, char_height = layout.get_pixel_size()
        
        # Apply space multiplier if this is a space
        if char == ' ':
            try:
                multiplier = spaces_width_multiplier.get(space_count, 1.0)
            except (AttributeError, TypeError):
                multiplier = spaces_width_multiplier.get(str(space_count), 1.0)
            char_width = standard_space_width * multiplier
            space_count += 1
        
        # Check if we'd go past the curve
        if distance_along_curve + char_width > total_curve_length:
            return "too_long", distance_along_curve, total_curve_length
        
        # Find position on curve for this character
        target_distance = distance_along_curve + char_width / 2
        
        # Advance idx_on_curve as needed
        while idx_on_curve < len(cumulative_lengths) - 1:
            if cumulative_lengths[idx_on_curve + 1] >= target_distance:
                break
            idx_on_curve += 1
        
        # Check if we've run out of curve
        if idx_on_curve >= len(cumulative_lengths) - 1:
            return "too_long", distance_along_curve, total_curve_length
        
        # Calculate position for boundary check
        segment_start = cumulative_lengths[idx_on_curve]
        segment_end = cumulative_lengths[idx_on_curve + 1]
        segment_length = segment_end - segment_start
        
        if segment_length > 1e-6:
            ratio = (target_distance - segment_start) / segment_length
            ratio = max(0, min(1, ratio))
            
            x = x_arr[idx_on_curve] + ratio * (x_arr[idx_on_curve + 1] - x_arr[idx_on_curve])
            y = y_arr[idx_on_curve] + ratio * (y_arr[idx_on_curve + 1] - y_arr[idx_on_curve])
            angle = get_tangent_angle(idx_on_curve)
            
            # Quick boundary check (without full collision detection for speed)
            half_w = char_width / 2
            half_h = char_height / 2
            
            # Check if character center is within margins
            if (x - half_w < margin_x or 
                x + half_w > design_width - margin_x or
                y - half_h < margin_y or 
                y + half_h > design_height - margin_y):
                # Character would be out of bounds
                return "too_long", distance_along_curve, total_curve_length
        
        # Advance along curve
        distance_along_curve += char_width
    
    # Check how well we filled the curve
    fill_ratio = distance_along_curve / total_curve_length
    
    if fill_ratio < (1.0 - FIT_TOLERANCE):
        return "too_short", distance_along_curve, total_curve_length
    elif fill_ratio > (1.0 + FIT_TOLERANCE):
        return "too_long", distance_along_curve, total_curve_length
    else:
        return "fits", distance_along_curve, total_curve_length


def apply_uniform_multiplier(component, multiplier):
    """
    Apply the same multiplier to all spaces in the component.
    """
    for i in range(component['spaces_in_arc_text']):
        try:
            component['spaces_width_multiplier'][i] = multiplier
        except (KeyError, TypeError):
            component['spaces_width_multiplier'][str(i)] = multiplier


def optimize_spacing_binary_search(
    component,
    x_values_scaled,
    y_values_scaled,
    text,
    pangocairo_context,
    font_desc,
    existing_boxes,
    margin_x,
    margin_y,
    design_width,
    design_height,
    initial_status
):
    """
    Use binary search to find the MINIMAL space adjustment needed to fit text.
    
    This replaces the iterative approach that could take 200+ attempts.
    Binary search finds the optimal value in ~12 iterations.
    
    Args:
        component: The story component dict with spacing info
        x_values_scaled, y_values_scaled: Curve coordinates
        text: The descriptor text to fit
        pangocairo_context, font_desc: Pango rendering context
        existing_boxes: Already rendered boxes for collision detection
        margin_x, margin_y: Margins
        design_width, design_height: Canvas dimensions
        initial_status: "too_short" or "too_long" from initial test
        
    Returns:
        tuple: (success: bool, final_multiplier: float, attempts: int)
    """
    if component['spaces_in_arc_text'] == 0:
        # No spaces to adjust
        return False, 1.0, 0
    
    # Determine search range based on whether we need to expand or shrink
    if initial_status == "too_long":
        # Text overflows curve → need to EXPAND spaces to slow down text
        low, high = 1.0, SPACE_MULTIPLIER_MAX
    else:  # too_short
        # Text doesn't reach end → need to SHRINK spaces to speed up text
        low, high = SPACE_MULTIPLIER_MIN, 1.0
    
    best_fit_multiplier = None
    attempts = 0
    
    for iteration in range(BINARY_SEARCH_ITERATIONS):
        attempts += 1
        mid = (low + high) / 2
        
        # Apply uniform multiplier to all spaces
        apply_uniform_multiplier(component, mid)
        
        # Test fit
        status, final_dist, total_len = test_text_fit_on_curve(
            x_values_scaled=x_values_scaled,
            y_values_scaled=y_values_scaled,
            text=text,
            pangocairo_context=pangocairo_context,
            font_desc=font_desc,
            spaces_width_multiplier=component['spaces_width_multiplier'],
            existing_boxes=existing_boxes,
            margin_x=margin_x,
            margin_y=margin_y,
            design_width=design_width,
            design_height=design_height
        )
        
        if status == "fits":
            best_fit_multiplier = mid
            # Keep searching for something closer to 1.0 (less adjustment)
            if initial_status == "too_long":
                high = mid  # Try smaller expansion
            else:
                low = mid   # Try smaller compression
        else:
            # Doesn't fit yet, need more adjustment
            if initial_status == "too_long":
                if status == "too_long":
                    low = mid   # Need more expansion
                else:
                    high = mid  # Went too far
            else:  # initial was too_short
                if status == "too_short":
                    high = mid  # Need more compression
                else:
                    low = mid   # Went too far
    
    if best_fit_multiplier is not None:
        # Apply the optimal multiplier we found
        apply_uniform_multiplier(component, best_fit_multiplier)
        print(f"  ✓ Binary search found fit: multiplier={best_fit_multiplier:.4f} in {attempts} iterations")
        return True, best_fit_multiplier, attempts
    else:
        # Could not fit - return False so caller knows to regenerate text
        apply_uniform_multiplier(component, 1.0)
        return False, 1.0, attempts  # ← This should trigger text regeneration


def check_has_constraints(
    original_arc_end_time_values,
    original_arc_end_emotional_score_values,
    old_min_x, old_max_x,
    old_min_y, old_max_y,
    recursive_mode
):
    """
    Check if the current arc segment has constraints that prevent
    extending/shortening the curve.
    
    Returns:
        tuple: (has_constraints: bool, constraint_type: str)
    """
    if not recursive_mode:
        return True, "recursive_mode_disabled"
    
    end_time = original_arc_end_time_values[-1]
    end_score = original_arc_end_emotional_score_values[-1]
    
    constraints = []
    
    # Check X constraints (beginning or end of story)
    if end_time <= old_min_x:
        constraints.append("at_story_start")
    if end_time >= old_max_x:
        constraints.append("at_story_end")
    
    # Check Y constraints (peak or nadir)
    if end_score >= old_max_y:
        constraints.append("at_peak")
    if end_score <= old_min_y:
        constraints.append("at_nadir")
    
    if constraints:
        return True, "+".join(constraints)
    
    return False, "no_constraints"


# =============================================================================
# INTEGRATION HELPER: Drop-in replacement for the spacing adjustment section
# =============================================================================

def handle_spacing_adjustment_optimized(
    component,
    curve_length_status,
    arc_x_values_scaled,
    arc_y_values_scaled,
    descriptors_text,
    pangocairo_context,
    font_desc,
    all_rendered_boxes,
    margin_x,
    margin_y,
    design_width,
    design_height,
    original_arc_end_time_values,
    original_arc_end_emotional_score_values,
    old_min_x, old_max_x,
    old_min_y, old_max_y,
    recursive_mode
):
    """
    Optimized spacing adjustment that replaces the iterative approach.
    
    Call this when you've detected curve_too_short or curve_too_long
    AND the curve cannot be extended/shortened due to constraints.
    
    Returns:
        tuple: (success: bool, final_multiplier: float, message: str)
    """
    # Check if we even have spaces to adjust
    if component.get('spaces_in_arc_text', 0) == 0:
        return False, 1.0, "no_spaces_to_adjust"
    
    # Initialize spacing tracking if not present
    if 'spacing_optimized' not in component:
        component['spacing_optimized'] = False
    
    # If we already tried optimization, don't repeat
    if component.get('spacing_optimized', False):
        return False, 1.0, "already_optimized"
    
    print(f"  → Attempting binary search spacing optimization for '{curve_length_status}'")
    
    # Run binary search optimization
    success, final_multiplier, attempts = optimize_spacing_binary_search(
        component=component,
        x_values_scaled=arc_x_values_scaled,
        y_values_scaled=arc_y_values_scaled,
        text=descriptors_text,
        pangocairo_context=pangocairo_context,
        font_desc=font_desc,
        existing_boxes=all_rendered_boxes,
        margin_x=margin_x,
        margin_y=margin_y,
        design_width=design_width,
        design_height=design_height,
        initial_status="too_short" if curve_length_status == "curve_too_short" else "too_long"
    )
    
    # Mark that we've tried optimization
    component['spacing_optimized'] = True
    component['spacing_adjustment_attempts'] = attempts
    component['final_space_multiplier'] = final_multiplier
    
    if success:
        component['adjust_spacing'] = True
        return True, final_multiplier, "spacing_optimized_successfully"
    else:
        return False, 1.0, "spacing_optimization_failed"


# =============================================================================
# EXAMPLE INTEGRATION CODE
# =============================================================================
"""
To integrate this into product_shape.py, replace the spacing adjustment 
sections (around lines 1127-1158 for curve_too_short and 1254-1284 for 
curve_too_long) with calls to handle_spacing_adjustment_optimized().

BEFORE (current code - ~30 lines, 200+ iterations):
```python
elif component['spacing_adjustment_attempts'] < MAX_SPACING_ADJUSTMENT_ATTEMPTS and component['space_to_modify'] < component['spaces_in_arc_text'] and component["spacing_factor"] < 1000:
    component['adjust_spacing'] = True
    # ... lots of incremental adjustment code ...
    return story_data, "processing"
```

AFTER (optimized - single call, ~12 iterations):
```python
# First, import at top of file:
from spacing_optimizer import handle_spacing_adjustment_optimized

# Then replace the spacing adjustment block with:
success, multiplier, message = handle_spacing_adjustment_optimized(
    component=component,
    curve_length_status=curve_length_status,
    arc_x_values_scaled=arc_x_values_scaled,
    arc_y_values_scaled=arc_y_values_scaled,
    descriptors_text=descriptors_text,
    pangocairo_context=pangocairo_context,
    font_desc=font_desc,
    all_rendered_boxes=all_rendered_boxes,
    margin_x=margin_x,
    margin_y=margin_y,
    design_width=design_width,
    design_height=design_height,
    original_arc_end_time_values=original_arc_end_time_values,
    original_arc_end_emotional_score_values=original_arc_end_emotional_score_values,
    old_min_x=old_min_x,
    old_max_x=old_max_x,
    old_min_y=old_min_y,
    old_max_y=old_max_y,
    recursive_mode=recursive_mode
)

if success:
    # Spacing adjustment worked, re-render with new spacing
    return story_data, "processing"
else:
    # Spacing couldn't fix it, need to regenerate text
    component['arc_text_valid'] = False
    component['arc_text_valid_message'] = f"curve {curve_length_status} but can't change due to constraints"
    return story_data, "processing"
```
"""
