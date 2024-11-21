from structured_story_data import create_story_data
from story_function import transform_story_data
from story_shape import create_shape
import json

#input path should be composite data
input_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea_composite_data.json'
output_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/'

#story_data = create_story_data(input_path, output_path)
#story_data = story_data['story_plot_data']

with open('/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea.json', 'r', encoding='utf-8') as file:
    story_data = json.load(file)
    story_data = story_data['story_plot_data']

transformed_data = transform_story_data(story_data)


x_values = transformed_data['x_values']
y_values = transformed_data['y_values']




# Create the cubic spline interpolator
#import numpy as np
#from scipy.interpolate import CubicSpline
# cs = CubicSpline(x_values, y_values)
# num_points = 500  # Adjust as needed
# x_new = np.linspace(x_values[0], x_values[-1], num_points)
# y_new = cs(x_new)

# Create the univariate spline with smoothing factor
# from scipy.interpolate import UnivariateSpline
# smoothing_factor = 1  # Adjust as needed (0 for interpolation)
# us = UnivariateSpline(x_values, y_values, s=smoothing_factor)
# num_points = 5000  # Adjust as needed
# x_new = np.linspace(x_values[0], x_values[-1], num_points)
# y_new = us(x_new)




text = 'This is an example of sample text. This is an example of sample text. This is an example of sample text. This is an example of sample text. This is an example of sample text. This is an example of sample text.'
create_shape(x_values, y_values, text) 


# Sample data for the curve (replace with your actual data)
# # For demonstration, we'll create a sine wave curve
# x_values = np.linspace(50, 550, 500)
# y_values = 300 + 100 * np.sin((x_values - 50) * (2 * np.pi / 500))

# # The text you want to render along the curve
# text = "This is a sample text rendered along the curve.This is a sample text rendered along the curve.This is a sample text rendered along the curve.This is a sample text rendered along the curve."

# # Create a Cairo surface and context
# width, height = 600, 400