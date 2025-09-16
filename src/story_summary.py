import json

# need to revise --> want to combine all summaries in one master summary
def get_story_summary(story_summary_path):

    """
    Inputs are a file path that contains story summary(s) and returns story summary
    """

    with open(story_summary_path, 'r', encoding='utf-8') as file:
        story_summary_data = json.load(file)

     # List is in priority order
    summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    story_summary = ""
    story_summary_source = ""

    #use longest summary proxy for most complete
    for summary_source in summary_sources:
        if summary_source in story_summary_data:
            summary_text = story_summary_data[summary_source].get('summary', '')
            if summary_text and len(summary_text) > len(story_summary):
                story_summary = summary_text
                story_summary_source = summary_source
    
    return story_summary

