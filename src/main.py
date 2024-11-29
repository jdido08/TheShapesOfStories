from structured_story_data import create_story_data
from story_function import transform_story_data
#from story_shape_w_descriptors_2 import create_shape
from story_shape_w_descriptors_3 import create_shape
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
create_shape(transformed_data)