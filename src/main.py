from story_data import create_story_data
from story_shape import create_shape
import json

#input path should be composite data
summaries_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries'
story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data'

create_shape(story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/the_great_gatsby.json',
                x_delta=0.015, #number of points in the line 
                line_type = 'char', #values line or char
                line_thickness = 10, #only used if line_type = line
                line_color = '#D4AF37', #only used if line_type = line
                font_style="Sans", #only used if line_type set to char
                font_size= 8, #only used if line_type set to char
                font_color = '#D4AF37', #only used if line_type set to char
                background_type='solid', #values solid or transparent
                background_value= '#001F3F', #only used if background_type = solid
                has_title = "YES", #values YES or NO
                title_text = "", #optinal if left blank then will use story title as default
                title_font_style = "Sans", #only used if has_title = "YES"
                title_font_size=24, #only used if has_title = "YES"
                title_font_color = '#D4AF37', #only used if has_title = "YES"
                title_padding = 0, #extra padding in pixels between bottom and title
                gap_above_title=20, #padding in pixels between title and story shape
                border=True, #True or False
                border_thickness=60, #only applicable if border is set to True
                border_color='#000000', #only applicable if border is set to True
                width_in_inches = 6,  #design width size
                height_in_inches = 6, #design width size
                wrap_in_inches=1.5,  # for canvas print outs 
                recursive_mode = True, #if you want to recurisvely generate story
                recursive_loops = 200, #the number of iterations 
                output_format="png") #options png or svg

#notes:
#15x15 -- font_size = 72