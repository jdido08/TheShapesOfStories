###

# get all sources from summary files --> so "source":"[summary]" I think is a format we should maintain 
# order then in trustworthiness 
# great giant string e.g. 
    # SparkNotes: 
    # XXXX
    #
    # Wikipedia:
    # XXXX
# Write Task for LLM, include:
# persona:
# task: title, author, year, protgaonsit
# focus: concrete actions, things, places
# information 
# WHY:
# --> not all summaries have equal / same info
# --> I can create a summary that's focused on the protagonist which will be better to feed into my story_components file 

import json 
import time
from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

def get_story_summary(story_title, author, protagonist, story_summary_path, config_path, llm_provider, llm_model):

    """
    Inputs are a file path that contains story summary(s) and returns story summary
    """

    with open(story_summary_path, 'r', encoding='utf-8') as file:
        story_summary_data = json.load(file)

     # List is in priority order -- this is all possible summary sources will need to update in future 
    all_summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    #create a dictionary that has all the summaries in order 
    story_summaries_dict = {}
    for summary_source in all_summary_sources:
        if summary_source in story_summary_data:
            story_summaries_dict[summary_source] = story_summary_data[summary_source]['summary']

    story_summaries_string = ""
    for key, value in story_summaries_dict.items():
        story_summaries_string += f"Summary from {key}:\n{value}\n\n"
    


    prompt_template = """
    You are a meticulous story synthesis assistant. 

    Your task: Create a comprehensive summary of {story_author}'s {story_title} that's centered on the character: {protagonist}.

    Instructions:
    1. Carefully read the summaries below. Each summary is from an authorative source. For each summary, focus on the concrete events that happen to {protagonist} (e.g. the actions they take, the places they go, the things that happen to them, the decisions they make, turning points, etc...) 
    2. Combine the details of each summary to create a single comphrehenseive summary.  

    
    {story_author}'s {story_title} Summaries:

    {story_summaries_string}
    """


    prompt = PromptTemplate(
        input_variables=["story_title", "author", "protagonist"],  # Define the expected inputs
        template=prompt_template
    )


    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1000)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    # Then invoke with the required inputs:
    output = runnable.invoke({
        "story_title": story_title,
        "author": author,
        "protagonist": protagonist
    })

    #print(output)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    



    # with open("test_summary_dict.txt", "w", encoding="utf-8") as f:
    #     f.write(story_summaries_string)
    # print("✅ Story Summary Saved")



    # summary_test_path = "test_summary_dict.json"
    # with open(summary_test_path, "w", encoding="utf-8") as f:     # save it back to the same file
    #     json.dump(story_summaries_dict, f, ensure_ascii=False, indent=2)
    #     f.write("\n")  # optional newline at EOF
    # time.sleep(1)
    # print("✅ Story Summary Saved")

    #print(story_summaries_dict)



    # story_summary = ""
    # story_summary_source = ""

    # #use longest summary proxy for most complete
    # for summary_source in summary_sources:
    #     if summary_source in story_summary_data:
    #         summary_text = story_summary_data[summary_source].get('summary', '')
    #         if summary_text and len(summary_text) > len(story_summary):
    #             story_summary = summary_text
    #             story_summary_source = summary_source
    
    # return story_summary

story_summary_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/les_miserables_composite_data.json"
get_story_summary(story_summary_path)