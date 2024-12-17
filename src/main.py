from archive.structured_story_data_archive_12_16_2024 import create_story_data
from story_function import transform_story_data
from story_shape_w_descriptors import create_shape
from story_shape_line import create_shape_line
import json

#input path should be composite data
input_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea_composite_data.json'
output_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/'
json_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/the_old_man_and_the_sea.json'

#story_data = create_story_data(input_path, output_path)
# print(story_data)
with open(json_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        if 'story_plot_data' in story_data:
            story_data = story_data['story_plot_data']

print(story_data)
story_data = transform_story_data(story_data)
story_data, status = create_shape_line(story_data)
   



# status = "processing"
# count = 1
# # while status == "processing":
# for i in range(2):
#     # print(story_data['story_components'][1]['modified_end_time'])
#     story_data = transform_story_data(story_data)
#     story_data, status = create_shape(story_data)
#     #print(count, " .) ", status)
#     count = count + 1
#     if status == "completed":
#         break
#     #print(story_data['story_components'][1]['modified_end_time'])



#clean up story_data for saving
# del story_data['x_values']
# del story_data['y_values']
# for component in story_data['story_components']:

#     if 'arc_x_values' in component:
#         del component['arc_x_values']

#     if 'arc_y_values' in component:
#         del component['arc_y_values']

# with open(json_path, 'w', encoding='utf-8') as file:
#     json.dump(story_data, file, ensure_ascii=False, indent=4)