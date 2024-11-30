from structured_story_data import create_story_data
from story_function import transform_story_data
from story_shape_w_descriptors import create_shape
import json

#input path should be composite data
input_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea_composite_data.json'
output_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/'
json_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea copy.json'

# story_data = create_story_data(input_path, output_path)

with open(json_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        if 'story_plot_data' in story_data:
            story_data = story_data['story_plot_data']

        
    



for x in range(1):
    # print(story_data['story_components'][1]['modified_end_time'])
    story_data = transform_story_data(story_data)
    story_data = create_shape(story_data)
    #print(story_data['story_components'][1]['modified_end_time'])
    

#print(story_data)
 # Save the modified data back to a JSON file
with open(json_path, 'w', encoding='utf-8') as file:
    json.dump(story_data, file, ensure_ascii=False, indent=4)