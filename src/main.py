from story_shape import create_shape
#from story_data import create_story_data
import json

#input path should be composite data
# summaries_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries'
# story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data'

### YOU JUST NEED 12x12 and then you shrinnk it down 
# size     | 6x6 | 12x12
# wrap     | 1.5 | 3
# t/b band | 1.5 | 1.5
# ------------------------
# arc      | 8   | 16
# title    | 24  | 48
# protag   | 12  | 24
# top      | 24  | 48
# bottom   | 6   | 12
#-----------------------
# line     | 20  | 40
# border   | ?   | 150
# gap      | 20  | 40
#-----------------------


# create_shape(story_data_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/the_great_gatsby_jay_gatsby.json',
#                 product= "canvas",
#                 x_delta=0.015, #number of points in the line 
#                 step_k = 10, #step-by-step steepness; higher k --> more steepness; values = 3, 4.6, 6.9, 10, 15
#                 line_type = 'char', #values line or char
#                 line_thickness = 20, #only used if line_type = line
#                 line_color = '#FFD700', #only used if line_type = line
#                 font_style="Playfair Display", #only used if line_type set to char
#                 font_size= 8, #only used if line_type set to char
#                 font_color = '#FFD700', #only used if line_type set to char
#                 background_type='solid', #values solid or transparent
#                 background_value= '#0F1E2D', #only used if background_type = solid
#                 has_title = "YES", #values YES or NO
#                 title_text = "", #optinal if left blank then will use story title as default
#                 title_font_style = "Playfair Display", #only used if has_title = "YES"
#                 title_font_size=24, #only used if has_title = "YES"
#                 title_font_color = '#FFD700', #only used if has_title = "YES"
#                 title_font_bold = False, #can be True or False
#                 title_font_underline = False, #can be true or False
#                 title_padding = 0, #extra padding in pixels between bottom and title
#                 gap_above_title=20, #padding in pixels between title and story shape
#                 protagonist_text = "", #if you leave blank will include protognaist name in lower right corner; can get rid of by just setting to " ", only works if has title is true
#                 protagonist_font_style = "Playfair Display",
#                 protagonist_font_size=12, 
#                 protagonist_font_color='#FFD700',
#                 protagonist_font_bold = False, #can be True or False
#                 protagonist_font_underline = False, #can be True or False
#                 top_text = "", #only applies when wrapped > 0; if "" will default to author, year
#                 top_text_font_style = "Playfair Display",
#                 top_text_font_size = 24,
#                 top_text_font_color = "#FFD700",
#                 bottom_text = "", #only applies when wrapped > 0; if "" will default to "Shapes of Stories"
#                 bottom_text_font_style = "Sans",
#                 bottom_text_font_size = 6,
#                 bottom_text_font_color = "#000000",
#                 top_and_bottom_text_band = 1.5, #this determines the band which top and center text is centered on above/below design; if you want to center along full wrap in inches set value to wrap_in_inches else standard is 1.5 
#                 border=True, #True or False
#                 border_thickness= 75, #only applicable if border is set to True
#                 border_color='#0B6E4F', #only applicable if border is set to True
#                 width_in_inches = 6,  #design width size
#                 height_in_inches = 6, #design width size
#                 wrap_in_inches=1.5,  # for canvas print outs 
#                 wrap_background_color = '#0B6E4F', #wrapped in inches part color only relevant when wrap_in_inches > 0 inc
#                 recursive_mode = True, #if you want to recurisvely generate story
#                 recursive_loops = 250, #the number of iterations 
#                 llm_provider = "anthropic", #for generating descriptors
#                 llm_model = "claude-3-5-sonnet-latest", #for generating descriptors 
#                 output_format="png") #options png or svg

# #notes:
# #15x15 -- font_size = 72



#for running one off - remember to comment out when not using 
# create_story_data(
#     input_path='/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/to_kill_a_mockingbird_composite_data.json',
#     author = "Harper Lee",
#     year = "1960",
#     protagonist="Scout Finch",
#     output_path= '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/',
#     llm_provider="anthropic", #options: anthropic, openai
#     llm_model="claude-3-5-sonnet-latest") #options: claude-3-5-sonnet-latest, gpt-4o, o3-mini