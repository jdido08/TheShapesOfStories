import pandas as pd
import numpy as np
import json
import itertools


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
   

def get_component_arc_function(x1, x2, y1, y2, arc, allow_extrapolation=False):

    def drop_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            return y2 
        else:
            return None

    def step_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            num_steps = int(x2 - x1)
            if num_steps < 1:
                num_steps = 1  # Ensure at least one step

            segment_width = (x2 - x1) / (num_steps + 1)
            steps_completed = int((x - x1) / segment_width)
            step_height = (y2 - y1) / num_steps

            return y1 + (steps_completed * step_height)
        else:
            return None

    def linear_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            return y1 + ((y2 - y1) / (x2 - x1)) * (x - x1)
        else:
            return None

    def concave_up_decreasing_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) ** 2)
            b = y2
            return a * (x - x2) ** 2 + b
        else:
            return None

    def concave_down_decreasing_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) ** 2)
            b = y1
            return a * (x - x1) ** 2 + b
        else:
            return None

    def concave_up_increasing_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            a = (y2 - y1) / ((x2 - x1) ** 2)
            b = y1
            return a * (x - x1) ** 2 + b
        else:
            return None

    def concave_down_increasing_function(x):
        if allow_extrapolation or x1 <= x <= x2:
            a = (y1 - y2) / ((x1 - x2) ** 2)
            b = y2
            return a * (x - x2) ** 2 + b
        else:
            return None

    def curvy_down_up(x):
        if allow_extrapolation or x1 <= x <= x2:
            xm = (x1 + x2) / 2
            ym = (y1 + y2) / 2
            if x <= xm:
                # First half: concave down
                a = (ym - y1) / ((xm - x1) ** 2)
                return a * (x - x1) ** 2 + y1
            else:
                # Second half: concave up
                a = (ym - y2) / ((xm - x2) ** 2)
                return a * (x - x2) ** 2 + y2
        else:
            return None

    def test(x):
        if allow_extrapolation or x1 <= x <= x2:
            xm = (x1 + x2) / 2
            ym = (y1 + y2) / 2
            if x <= xm:
                # Concave down decreasing function up to the midpoint
                a = (ym - y1) / ((xm - x1) ** 2)
                return a * (x - xm) ** 2 + ym
            else:
                # Concave up decreasing function from the midpoint to x2
                a = (ym - y2) / ((xm - x2) ** 2)
                return a * (x - xm) ** 2 + ym
        else:
            return None

    # Map arc types to functions
    if arc in ['Step-by-Step Increase', 'Step-by-Step Decrease']:
        return step_function
    elif arc in ['Straight Increase', 'Straight Decrease']:
        return drop_function
    elif arc in ['Linear Increase', 'Linear Decrease', 'Linear Flat']:
        return linear_function
    elif arc in ['Concave Down, Increase', 'Rapid-to-Gradual Increase']:
        return concave_down_increasing_function
    elif arc in ['Concave Down, Decrease', 'Gradual-to-Rapid Decrease']:
        return concave_down_decreasing_function
    elif arc in ['Concave Up, Increase', 'Gradual-to-Rapid Increase']:
        return concave_up_increasing_function
    elif arc in ['Concave Up, Decrease', 'Rapid-to-Gradual Decrease']:
        return concave_up_decreasing_function
    elif arc in ['Hyperbola Increase', 'Hyperbola Decrease', 'S-Curve Increase', 'S-Curve Decrease']:
        return curvy_down_up
    elif arc == 'test':
        return test
    else:
        raise ValueError("Interpolation method not supported")

    
# Master function to evaluate the emotional score for any given plot point number
def get_story_arc(x, functions_list):
    for func in functions_list:
        result = func(x)
        if result is not None:
            return result
    return None  # Return None if x is outside the range of all functions

def transform_story_data(data):

    # with open(file_path, 'r') as file:
    #     data = json.load(file)
                       
    #convert json to dataframe - mostly for historical reasons I'm setup elsewhere to handle dataframes
    try:
        # Directly use the dictionary
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
        try:
            df = pd.json_normalize(
            data, 
            meta=[
                'title', 
                'protagonist'
            ],
            record_prefix='story_component_'
        )
        except Exception as e:
            print("Error:", e)


    # Get the title directly from the dictionary
    title = data['title']
    protagonist = data['protagonist']

    # Format dataframe
    df = df.rename(columns={
        'end_time': 'story_component_end_time', 
        'description': 'story_component_description', 
        'end_emotional_score': 'story_component_end_emotional_score',
        'arc': 'story_component_arc'
    })
    df = df[['title', 'protagonist', 'story_component_end_time', 'story_component_end_emotional_score', 'story_component_arc']]
    df = df.sort_values(by='story_component_end_time', ascending=True)  # Sort dataframe so numbers in order 

    # Convert time values to x-values
    story_time_values = df['story_component_end_time'].tolist()
    x_original = np.array(story_time_values)
    x_scale = np.array(scale_plot_points(story_time_values, 1, 10))  # Scale x values so they are 1 - 10
    x_dict = {}  # Store pairs of x_original values and their scaled counterparts  
    for i in range(len(x_original)):
        x_original_value = x_original[i]
        x_scale_value = x_scale[i]
        x_dict[x_original_value] = x_scale_value

    # Extract individual story components
    array_of_dicts = []  # Loop through dataframe, grab pairs of values, and store story component data in dictionary
    for i in range(len(df) - 1):  # -1 because we are considering pairs of adjacent rows
        x1_unscaled = x_dict[df.loc[i, 'story_component_end_time']]
        x2_unscaled = x_dict[df.loc[i + 1, 'story_component_end_time']]
        y1_unscaled = df.loc[i, 'story_component_end_emotional_score']
        y2_unscaled = df.loc[i + 1, 'story_component_end_emotional_score']
        arc = df.loc[i + 1, 'story_component_arc']  # Using the arc of the second point

        dict_item = {
            'story_component_times': [x1_unscaled, x2_unscaled],
            'story_component_end_emotional_scores': [y1_unscaled, y2_unscaled],
            'arc': arc,
            'x1_unscaled': x1_unscaled,
            'x2_unscaled': x2_unscaled,
            'y1_unscaled': y1_unscaled,
            'y2_unscaled': y2_unscaled,
            'arc_type': arc  # Assuming 'arc' is the arc type
        }
        array_of_dicts.append(dict_item)

    # Create the list to hold the arc functions
    story_arc_functions_list = []
    for item in array_of_dicts:
        x1 = item['x1_unscaled']
        x2 = item['x2_unscaled']
        y1 = item['y1_unscaled']
        y2 = item['y2_unscaled']
        arc_type = item['arc_type']

        # Create the function based on the specified interpolation
        component_arc_function = get_component_arc_function(x1, x2, y1, y2, arc_type)
        story_arc_functions_list.append(component_arc_function)

    # Get final values 
    x_values = np.linspace(min(x_scale), max(x_scale), 1000)  # 1000 points for smoothness
    y_values = np.array([get_story_arc(x, story_arc_functions_list) for x in x_values])  # Calculating corresponding y-values using the master function
    y_values = scale_y_values(y_values, -10, 10)

    # Assign components to data['story_components']
    data['story_components'] = array_of_dicts

    # For each component, extract arc_x_values and arc_y_values
    for idx, item in enumerate(array_of_dicts):
        x1 = item['x1_unscaled']
        x2 = item['x2_unscaled']
        y1 = item['y1_unscaled']
        y2 = item['y2_unscaled']
        arc_type = item['arc_type']

        component_arc_function = get_component_arc_function(x1, x2, y1, y2, arc_type)
        result = np.array([component_arc_function(x) for x in x_values])

        non_none_positions = np.where(result != None)[0]
        arc_x_values = x_values[non_none_positions]
        arc_y_values = y_values[non_none_positions]

        data['story_components'][idx]['arc_x_values'] = arc_x_values.tolist()
        data['story_components'][idx]['arc_y_values'] = arc_y_values.tolist()

    # Assign x_values and y_values to data
    data['x_values'] = x_values.tolist()
    data['y_values'] = y_values.tolist()

    return data
