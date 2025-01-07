from story_data import create_story_data
from story_shape import create_shape
import json

#input path should be composite data
summaries_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries'
story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data'

create_shape(story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/the_old_man_and_the_sea.json',
                num_points=500, #number of points in the line 
                line_type = 'char', #values line or char
                line_thickness = 10, #only used if line_type = line
                line_color = (0, 0, 0), #only used if line_type = line
                font_style="Sans", #only used if line_type set to char
                font_size= 8, #only used if line_type set to char
                font_color = (0, 0, 0), #only used if line_type set to char
                background_type='solid', #values solid or transparent
                background_value=(1, 1, 1), #only used if background_type = solid
                has_title = "YES", #values YES or NO
                title_font_style = "Sans", #only used if has_title = "YES"
                title_font_size=24, #only used if has_title = "YES"
                title_font_color = (0, 0, 0), #only used if has_title = "YES"
                title_padding = 0, #extra padding in pixels between bottom and title
                gap_above_title=100, #padding in pixels between title and story shape
                width_in_inches = 7,
                height_in_inches = 5,
                recursive_mode = True) #if you want to recurisvely generate story

#notes:
#15x15 -- font_size = 72