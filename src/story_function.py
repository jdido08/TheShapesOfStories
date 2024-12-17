import pandas as pd
import numpy as np
import json
import itertools
import math


def find_breakpoints(x, y, threshold = 1.0):
    step_points = []
    for i in range(1, len(y)):
        if abs(y[i] - y[i-1]) >= threshold:
            step_points.append(x[i-1])
    return step_points


def insert_points(x, y, num_insert_points, threshold=1.0):
    breakpoints = find_breakpoints(x, y, threshold)
    new_x, new_y = [], []

    for i in range(len(x)):
        new_x.append(x[i])
        new_y.append(y[i])

        if i < len(x) - 1 and x[i] in breakpoints:
            y_increment = (y[i+1] - y[i]) / (num_insert_points + 1)
            for j in range(1, num_insert_points + 1):
                new_x.append(x[i])
                new_y.append(y[i] + j * y_increment)

    return new_x, new_y


#scale plot points to numbers 1 - 10 for consistency across stories
def scale_plot_points(original_plot_points, new_min, new_max):
    old_min = np.min(original_plot_points)
    old_max = np.max(original_plot_points)
    scaled_plot_points = new_min + ((original_plot_points - old_min) / (old_max - old_min)) * (new_max - new_min)
    return scaled_plot_points


def scale_y_values(y_values, new_min, new_max):
    old_min = np.min(y_values)
    old_max = np.max(y_values)
    if old_max == old_min:
        # Avoid division by zero if all y_values are the same
        return np.full_like(y_values, new_min)
    scaled_values = ((y_values - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
    return scaled_values
   


def get_component_arc_function(x1, x2, y1, y2, arc):

    # def smooth_step_function(x):
    #     if x1 <= x <= x2:
    #         x_center = (x1 + x2) / 2
    #         k = (x2 - x1) / 10  # Adjust k for smoothness; smaller k means steeper transition
    #         transition = 1 / (1 + np.exp(-(x - x_center) / k))
    #         return y1 + (y2 - y1) * transition
    #     else:
    #         return None

    def smooth_step_function(x):
        if x1 <= x <= x2:
            #num_steps = int((x2) - (x1))
            num_steps = int(math.ceil(x2 - x1))
            #print(x2, " ", x1)
            if num_steps < 1:
                num_steps = 2  # Ensure at least one step
            #num_steps = 2

            # Calculate the positions of the steps
            step_edges = np.linspace(x1, x2, num_steps + 1)
            step_height = (y2 - y1) / num_steps

            # Define smoothing width as a fraction of step width
            step_width = (x2 - x1) / num_steps
            smoothing_fraction = 0.5 # Adjust this value between 0 and 0.5
            smoothing_width = smoothing_fraction * step_width

            # Determine which step we're in
            for i in range(num_steps):
                start = step_edges[i]
                end = step_edges[i + 1]
                y_base = y1 + i * step_height

                # If we're within the smoothing region at the end of the step
                if end - smoothing_width <= x <= end:
                    t = (x - (end - smoothing_width)) / smoothing_width
                    # Smoothstep interpolation
                    transition = t**2 * (3 - 2 * t)
                    return y_base + step_height * transition
                # If we're within the flat part of the step
                elif start <= x < end - smoothing_width:
                    return y_base
            return y2  # In case x == x2
        else:
            return None

    def smooth_drop_function(x):
        if x1 <= x <= x2:
            x_center = x1 + (x2 - x1) / 2
            k = (x2 - x1) / 10
            transition = 1 / (1 + np.exp(-(x - x_center) / k))
            return y1 + (y2 - y1) * transition
        else:
            return None

    def straight_decrease_function(x):
        if x1 <= x <= x2:
            # Parameters to adjust
            horizontal_fraction = 0.01  # Adjust as needed

            # Calculate key points
            total_interval = x2 - x1
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                # Initial horizontal segment at y1
                return y1
            elif horizontal_end <= x <= x2:
                # Immediate jump to y2
                return y2
            else:
                return None
        else:
            return None

        if x1 <= x <= x2:
            # Parameters to adjust
            horizontal_fraction = 0.01  # Adjust as needed

            # Calculate key points
            #total_interval = x2 - x1
            total_interval = 0
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                # Initial horizontal segment at y1
                return y1
            elif horizontal_end <= x <= x2:
                # Linear decrease from y1 to y2
                t = (x - horizontal_end) / (x2 - horizontal_end)
                return y1 + (y2 - y1) * t
            else:
                return None
        else:
            return None

    def drop_function(x):
        if x1 <= x <= x2:
            return y2 
        else:
            return None
        
    def straight_increase_function(x):
        if x1 <= x <= x2:
            horizontal_fraction = 0.01  # Adjust as needed
            total_interval = x2 - x1
            horizontal_end = x1 + horizontal_fraction * total_interval

            if x1 <= x < horizontal_end:
                return y1
            elif horizontal_end <= x <= x2:
                return y2
            else:
                return None
        else:
            return None

    def smooth_exponential_decrease_function(x):
        # Only define behavior in the interval [x1, x2]
        if x1 <= x <= x2:
            # We want the function to rapidly drop from y1 at x1 and approach y2 as x approaches x2.
            # Let's choose k so that at x2 we're close to y2, say within 1%:
            # exp(-k*(x2-x1)) = 0.01 -> -k*(x2-x1)=ln(0.01) -> k = -ln(0.01)/(x2-x1)
            # ln(0.01) ~ -4.60517, so k ≈ 4.6/(x2-x1).
            # You can adjust this factor (4.6) if you want a different "steepness".
            if x2 > x1:  
                k = 4.6 / (x2 - x1)
            else:
                # Avoid division by zero if times are equal
                k = 1.0

            return y2 + (y1 - y2)*math.exp(-k*(x - x1))
        else:
            return None

    def smooth_exponential_increase_function(x):
        # Similar logic but reversed to create a curve that starts low and rises up.
        if x1 <= x <= x2:
            if x2 > x1:
                k = 4.6 / (x2 - x1)
            else:
                k = 1.0

            # For an "increase", you can simply flip the logic:
            # Start at y1 and approach y2 from below using a mirrored exponential shape:
            # y(x) = y1 + (y2 - y1)*(1 - exp(-k*(x - x1)))
            return y1 + (y2 - y1)*(1 - math.exp(-k*(x - x1)))
        else:
            return None
    
    def step_function(x):
        if x1 <= x <= x2:

            #num_steps = (x2 - x1)
            #num_steps = 2 #setting static number of steps
            #step_height = (y2 - y1) / num_steps
            #print("x1: ", x1, " x2: ", x2, " y1: ", y1, " y2: ", y2)
            #print("num_steps: ", num_steps, "  step_height: ", step_height)
            #steps_completed = int((x - x1) / ((x2 - x1) / num_steps)) # Calculate the number of steps from x1 to x
            
            num_steps = int(x2 - x1)
            if(num_steps < 1):
                num_steps = 1  # Static number of steps
            
            segment_width = (x2 - x1) / (num_steps + 1)
            steps_completed = int((x - x1) / segment_width)
            step_height = (y2 - y1) / num_steps
       
            return y1 + (steps_completed * step_height)
        else:
            return None
            
    def linear_function(x):
        if x1 <= x <= x2:
            return y1 + ((y2 - y1) / (x2 - x1)) * (x - x1)
        else:
            return None
    
    def concave_up_decreasing_function(x):
        if x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) * (x1 + x2 - 2*x2))
            b = y2 - a * (x2 - x2)**2
            return a * (x - x2)**2 + b
        else:
            return None
        
    def concave_down_decreasing_function(x):
        if x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) * (x2 + x1 - 2*x1))
            b = y1 - a * (x1 - x1)**2
            return a * (x - x1)**2 + b
        else:
            return None
        
    def concave_up_increasing_function(x):
        if x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) * (x2 + x1 - 2*x1))
            b = y1 - a * (x1 - x1)**2
            return a * (x - x1)**2 + b
        else:
            return None

    def concave_down_increasing_function(x):
        if x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) * (x1 + x2 - 2*x2))
            b = y2 - a * (x2 - x2)**2
            return a * (x - x2)**2 + b
        else:
            return None

    def test(x):
        
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2
        
        if x1 <= x <= xm:
            # Concave down decreasing function up to the midpoint
            a = (ym - y1) / ((xm - x1)**2)
            return a * (x - xm)**2 + ym
        elif xm < x <= x2:
            # Concave up decreasing function from the midpoint to x2
            a = (ym - y2) / ((xm - x2)**2)
            return a * (x - xm)**2 + ym
        else:
            return None
            
    def curvy_down_up(x):
        
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2
        a_down = (ym - y1) / ((xm - x1)**2)
        b_down = y1 - a_down * (x1 - x1)**2
        
        # Ensure the vertex of concave up is at (x2, y2)
        a_up = (ym - y2) / ((xm - x2)**2)
        b_up = y2 - a_up * (x2 - x2)**2
        
        if x1 <= x <= xm:
            return a_down * (x - x1)**2 + b_down
        elif xm < x <= x2:
            return a_up * (x - x2)**2 + b_up
        else:
            return None
    
    def partial_exponential_transition_function(x):
        vertical_fraction = 0.01
        flatten_fraction = 0.01
        horizontal_fraction = 0.01  # New parameter to mimic the original horizontal pause

        if x1 <= x <= x2:
            total_length = x2 - x1
            x_horizontal_end = x1 + horizontal_fraction * total_length
            x_mid = x1 + vertical_fraction * total_length

            # Determine y_mid
            delta = 0.1 * (y1 - y2)
            y_mid = y2 + delta

            # Phase 1: Horizontal portion at the start
            if x < x_horizontal_end:
                # For a tiny fraction of the interval, just stay at y1
                return y1

            # Phase 2: Linear descent (or ascent) from y1 to y_mid by x_mid
            # After the horizontal segment, we have a smaller effective linear portion
            # That goes from (x_horizontal_end, y1) to (x_mid, y_mid)
            # Adjust the linear interpolation to start from x_horizontal_end instead of x1
            if x_horizontal_end <= x <= x_mid:
                # Avoid division by zero if vertical_fraction and horizontal_fraction overlap significantly
                if x_mid == x_horizontal_end:
                    return y_mid
                t = (x - x_horizontal_end) / (x_mid - x_horizontal_end)
                return y1 + (y_mid - y1)*t

            # Phase 3: Exponential tail from x_mid to x2
            if x > x_mid:
                if x2 == x_mid:
                    return y_mid
                k = -math.log(flatten_fraction)/(x2 - x_mid)
                return y2 + (y_mid - y2)*math.exp(-k*(x - x_mid))

        else:
            return None

   
    if x1 == x2:
        # x1 == x2, return a function that is only defined at x == x1
        def point_function(x):
            if x == x1:
                return y1
            else:
                return None
        return point_function
    else:
        # Existing code for other arcs
        if arc in['Step-by-Step Increase', 'Step-by-Step Decrease']:
            #return step_function
            return smooth_step_function
        elif arc in ['Straight Increase']:
            #return drop_function
            #return smooth_drop_function
            #return straight_increase_function
            #return smooth_exponential_increase_function
            return partial_exponential_transition_function
        elif arc in ['Straight Decrease']:
            #return straight_decrease_function
            #return smooth_exponential_decrease_function
            return partial_exponential_transition_function
        elif arc in ['Linear Increase','Linear Decrease','Linear Flat']:
            return linear_function
        elif arc in ['Concave Down, Increase', 'Rapid-to-Gradual Increase']:
            return concave_down_increasing_function
        elif arc in ['Concave Down, Decrease', 'Gradual-to-Rapid Decrease']:
            return concave_down_decreasing_function
        elif arc in ['Concave Up, Increase', 'Gradual-to-Rapid Increase']:
            return concave_up_increasing_function
        elif arc in ['Concave Up, Decrease', 'Rapid-to-Gradual Decrease']:
            return concave_up_decreasing_function
        elif arc in ['Hyperbola Increase','Hyperbola Decrease', 'S-Curve Increase', 'S-Curve Decrease']:
            return curvy_down_up
        elif arc  == 'test':
            return test
        else:
            #print(arc)
            raise ValueError("Interpolation method not supported")
    


      
   

    
# Master function to evaluate the emotional score for any given plot point number
def get_story_arc(x, functions_list):
    for func in functions_list:
        result = func(x)
        if result is not None:
            return result
    return None  # Return None if x is outside the range of all functions


def transform_story_data(data):
    # Convert JSON to DataFrame
    try:
        df = pd.json_normalize(
            data, 
            record_path=['story_components'], 
            meta=[
                'title', 
                'protagonist'
            ],
            record_prefix='story_component_'
        )
    except Exception as e:
        print("Error:", e)
        return None

    # Print the column names for debugging
    #print("DataFrame columns:", df.columns.tolist())

    # Use 'story_component_modified_end_time' and 'story_component_modified_end_emotional_score' directly
    df['story_component_end_time'] = df['story_component_modified_end_time']
    df['story_component_end_emotional_score'] = df['story_component_modified_end_emotional_score']

    # Rename other columns as needed
    df = df.rename(columns={
        'story_component_description': 'story_component_description',
        'story_component_arc': 'story_component_arc'
    })

    # Select relevant columns
    df = df[['title', 'protagonist', 'story_component_end_time', 'story_component_end_emotional_score', 'story_component_arc', 'story_component_description']]
    df = df.sort_values(by='story_component_end_time', ascending=True)

    # Convert time values to x-values
    story_time_values = df['story_component_end_time'].tolist()
    x_original = np.array(story_time_values)
    x_scale = np.array(scale_plot_points(x_original, 1, 10))  # Scale x values so they are 1 - 10

    # Store pairs of x_original values and their scaled counterparts
    x_dict = dict(zip(x_original, x_scale))

    # Extract individual story components
    array_of_dicts = []
    for i in range(len(df) - 1):  # -1 because we are considering pairs of adjacent rows
        start_time = x_dict[df.loc[i, 'story_component_end_time']]
        end_time = x_dict[df.loc[i + 1, 'story_component_end_time']]
        start_emotional_score = df.loc[i, 'story_component_end_emotional_score']
        end_emotional_score = df.loc[i + 1, 'story_component_end_emotional_score']
        arc = df.loc[i + 1, 'story_component_arc']  # Using the arc of the second point

        dict_item = {
            'story_component_times': [start_time, end_time],
            'story_component_end_emotional_scores': [start_emotional_score, end_emotional_score],
            'arc': arc
        }
        array_of_dicts.append(dict_item)

    # Create a list to store the component story arcs
    story_arc_functions_list = []
    for item in array_of_dicts:
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']

        # Create the function based on the specified interpolation
        component_arc_function = get_component_arc_function(
            story_component_times[0],
            story_component_times[1],
            story_component_end_emotional_scores[0],
            story_component_end_emotional_scores[1],
            story_component_arc
        )
        story_arc_functions_list.append(component_arc_function)

    # Get final values
    x_values = np.linspace(min(x_scale), max(x_scale), 500)  # 1000 points for smoothness

    # Ensure x_values includes all x1 and x2 values
    x1_x2_values = set()
    for item in array_of_dicts:
        x1_x2_values.update(item['story_component_times'])
    x_values = np.unique(np.concatenate([x_values, np.array(list(x1_x2_values))]))
    x_values.sort()

    y_values = np.array([get_story_arc(x, story_arc_functions_list) for x in x_values])  # Calculate corresponding y-values
    y_values = scale_y_values(y_values, -10, 10)

    # Process arcs for each story component
    story_component_index = 1
    for item in array_of_dicts:
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']

        component_arc_function = get_component_arc_function(
            story_component_times[0],
            story_component_times[1],
            story_component_end_emotional_scores[0],
            story_component_end_emotional_scores[1],
            story_component_arc
        )
        result = np.array([get_story_arc(x, [component_arc_function]) for x in x_values])

        non_none_positions = np.where(result != None)[0]

        # **Add check for empty non_none_positions**
        if non_none_positions.size == 0:
            print(f"No valid positions for component at index {story_component_index}, function returns None for all x")
            story_component_index += 1
            continue  # Skip this component or handle accordingly

        arc_x_values = x_values[non_none_positions]
        arc_y_values = y_values[non_none_positions]

        # Handle specific arcs if necessary
        # if story_component_arc in ['Straight Increase', 'Straight Decrease']:
        #     if non_none_positions.size > 1:
        #         prepend_indices = [non_none_positions[0] - 2, non_none_positions[0] - 1]
        #         # Ensure indices are within bounds
        #         prepend_indices = [idx for idx in prepend_indices if idx >= 0]
        #         if prepend_indices:
        #             prepend_x = x_values[prepend_indices]
        #             prepend_y = y_values[prepend_indices]
        #             arc_x_values = np.insert(arc_x_values, 0, prepend_x)
        #             arc_y_values = np.insert(arc_y_values, 0, prepend_y)
            
            # Decrease the number of values inserted
            # prepend_index = non_none_positions[0] - 1
            # # Ensure index is within bounds
            # if prepend_index >= 0:
            #     prepend_x = x_values[prepend_index]
            #     prepend_y = y_values[prepend_index]
            #     arc_x_values = np.insert(arc_x_values, 0, prepend_x)
            #     arc_y_values = np.insert(arc_y_values, 0, prepend_y)
            # else:
            #     print(f"Not enough positions to prepend for component at index {story_component_index}")

        data['story_components'][story_component_index]['arc_x_values'] = arc_x_values.tolist()
        data['story_components'][story_component_index]['arc_y_values'] = arc_y_values.tolist()

        story_component_index += 1

    data['x_values'] = x_values.tolist()
    data['y_values'] = y_values.tolist()

    return data


