from story_shape import create_shape
#from story_data import create_story_data
import json

#input path should be composite data
summaries_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries'
story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data'

create_shape(story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/the_old_man_and_the_sea_santiago.json',
                x_delta=0.015, #number of points in the line 
                line_type = 'char', #values line or char
                line_thickness = 10, #only used if line_type = line
                line_color = '#1F4534', #only used if line_type = line
                font_style="Cormorant Garamond", #only used if line_type set to char
                font_size= 8, #only used if line_type set to char
                font_color = '#1F4534', #only used if line_type set to char
                background_type='solid', #values solid or transparent
                background_value= '#F7E6C4', #only used if background_type = solid
                has_title = "YES", #values YES or NO
                title_text = "", #optinal if left blank then will use story title as default
                title_font_style = "Cormorant Garamond", #only used if has_title = "YES"
                title_font_size=24, #only used if has_title = "YES"
                title_font_color = '#1F4534', #only used if has_title = "YES"
                title_padding = 0, #extra padding in pixels between bottom and title
                gap_above_title=20, #padding in pixels between title and story shape
                protagonist_text = "", #if you leave blank will include protognaist name in lower right corner; can get rid of by just setting to " ", only works if has title is true
                protagonist_font_style = "Cormorant Garamond",
                protagonist_font_size=12, 
                protagonist_font_color='#1F4534',
                border=True, #True or False
                border_thickness=60, #only applicable if border is set to True
                border_color='#D4B682', #only applicable if border is set to True
                width_in_inches = 6,  #design width size
                height_in_inches = 6, #design width size
                wrap_in_inches=1.5,  # for canvas print outs 
                wrap_background_color = '#D4B682', #wrapped in inches part color only relevant when wrap_in_inches > 0 inc
                recursive_mode = True, #if you want to recurisvely generate story
                recursive_loops = 50, #the number of iterations 
                llm_provider = "anthropic", #for generating descriptors
                llm_model = "claude-3-5-sonnet-latest", #for generating descriptors 
                output_format="png") #options png or svg

# #notes:
# #15x15 -- font_size = 72



# #for running one off - remember to comment out when not using 
# create_story_data(
#     input_path='//Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/romeo_and_juliet_composite_data.json',
#     author = "William Shakespeare",
#     year = "1597",
#     protagonist="Romeo",
#     output_path= '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/',
#     llm_provider="anthropic", #options: anthropic, openai
#     llm_model="o3-mini") #options: claude-3-5-sonnet-latest, gpt-4o, o3-mini