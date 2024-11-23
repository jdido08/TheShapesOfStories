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
   


def get_component_arc_function(x1, x2, y1, y2, arc):

    def drop_function(x):
        if x1 <= x <= x2:
            return y2 
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

      
    if arc in['Step-by-Step Increase', 'Step-by-Step Decrease']:
        return step_function
    elif arc in ['Straight Increase','Straight Decrease']:
        return drop_function
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
    #print(data)
    title = data['title']
    protagonist = data['protagonist']

    #format dataframe
    df = df.rename(columns={
        'end_time': 'story_component_end_time', 
        'description': 'story_component_description', 
        'end_emotional_score': 'story_component_end_emotional_score',
        'arc': 'story_component_arc',
        'descriptors': 'story_component_descriptors'
    })
    df = df[['title', 'protagonist', 'story_component_end_time', 'story_component_description', 'story_component_end_emotional_score','story_component_arc', 'story_component_descriptors']]
    df = df.sort_values(by='story_component_end_time', ascending=True) #sort dataframe so numbers in order 
    
    #convert time values to x-values
    story_time_values = df['story_component_end_time'].tolist()
    x_original = np.array(story_time_values)
    x_scale = np.array(scale_plot_points(story_time_values, 1, 10)) #scale x values so they are 1 - 10
    x_dict = {} #store pairs of x_original values and their scaled counterparts  
    for i in range(len(x_original)):
        x_original_value = x_original[i]
        x_scale_value = x_scale[i]
        x_dict[x_original_value] = x_scale_value

    #extract individual story components
    array_of_dicts = [] #loop through dataframe, grab pairs of values, and store story component data in dictionary
    for i in range(len(df) - 1):  # -1 because we are considering pairs of adjacent rows
        story_component_times = [x_dict[df.loc[i, 'story_component_end_time']], x_dict[df.loc[i + 1, 'story_component_end_time']]]
        story_component_end_emotional_scores = [df.loc[i, 'story_component_end_emotional_score'], df.loc[i + 1, 'story_component_end_emotional_score']]
        arc = df.loc[i + 1, 'story_component_arc']  # Using the interpolation of the second point
        story_component_descriptors = df.loc[i+1, 'story_component_descriptors']
        dict_item = { #contract dict for each story component
            'story_component_times': story_component_times,
            'story_component_end_emotional_scores': story_component_end_emotional_scores,
            'arc': arc,
            'story_component_descriptors': story_component_descriptors
        }
        array_of_dicts.append(dict_item) # Adding the dictionary to the array
        #print(dict_item)

    
    story_arc_functions_list = [] # create ist to store the component story arcs
    for item in array_of_dicts: # Loop through the array to create and add arc to list
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']
        

        # Create the function based on the specified interpolation
        component_arc_function = get_component_arc_function(story_component_times[0], story_component_times[1], story_component_end_emotional_scores[0], story_component_end_emotional_scores[1], story_component_arc)
        story_arc_functions_list.append(component_arc_function)
  
    #get final values 
    x_values = np.linspace(min(x_scale), max(x_scale), 500)  # 1000 points for smoothness
    y_values = np.array([get_story_arc(x, story_arc_functions_list) for x in x_values]) # Calculating corresponding y-values using the master function
    y_values = scale_y_values(y_values, -10, 10)
    
    
    #figure out text -- WIP 
    arcs = []
    story_component_index = 1
    total_chars = 0
    for item in array_of_dicts:
        story_component_times = item['story_component_times']
        story_component_end_emotional_scores = item['story_component_end_emotional_scores']
        story_component_arc = item['arc']
        story_component_descriptors = item['story_component_descriptors']
        
        component_arc_function = get_component_arc_function(story_component_times[0], story_component_times[1], story_component_end_emotional_scores[0], story_component_end_emotional_scores[1], story_component_arc)
        result = np.array([get_story_arc(x, [component_arc_function]) for x in x_values])
        
        non_none_positions = np.where(result != None)[0]
        arc_x_values = x_values[non_none_positions]
        arc_y_values = y_values[non_none_positions]
        # data['story_components'][story_component_index]['arc_x_values'] = arc_x_values.tolist()
        # data['story_components'][story_component_index]['arc_y_values'] = arc_y_values.tolist()

        #maybe delete this
        if story_component_arc in ['Straight Increase','Straight Decrease']:
            prepend_x_posistion = non_none_positions[0] - 1
            prepend_x = x_values[prepend_x_posistion]
            prepend_y = y_values[prepend_x_posistion]
            arc_x_values = np.insert(arc_x_values, 0, prepend_x)
            arc_y_values = np.insert(arc_y_values, 0, prepend_y)
            prepend_x_posistion = non_none_positions[0] - 2
            prepend_x = x_values[prepend_x_posistion]
            prepend_y = y_values[prepend_x_posistion]
            arc_x_values = np.insert(arc_x_values, 0, prepend_x)
            arc_y_values = np.insert(arc_y_values, 0, prepend_y)
        
        data['story_components'][story_component_index]['arc_x_values'] = arc_x_values.tolist()
        data['story_components'][story_component_index]['arc_y_values'] = arc_y_values.tolist()

        story_component_index = story_component_index + 1

    #calc actual chars in story
    text_list = list(itertools.chain.from_iterable(df['story_component_descriptors']))
    text_list = text_list[1:] #get rid of first item which will always be #N/A
    text = "".join(text_list)
    #text = text.replace("!.","!")

    data['x_values'] = x_values.tolist()
    data['y_values'] = y_values.tolist()
    
    return data
