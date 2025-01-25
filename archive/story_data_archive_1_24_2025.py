import anthropic
import yaml
import tiktoken
import json 
import os 

def analyze_story(author_name, story_title, story_summary):
    with open("config.yaml", 'r') as stream:
        config = yaml.safe_load(stream)
        anthropic_key = config['anthropic_key']

    client = anthropic.Anthropic(
        api_key=anthropic_key,
    )

    # The user_message includes placeholders that will be replaced by the function arguments
    user_message = f"""You are a world-class literary scholar and expert in story analysis. Your task is to analyze a story using a specific framework that segments the narrative based on the protagonist's emotional journey. Please carefully read and analyze the following story summary:

<author_name>
{author_name}
</author_name>

<story_title>
{story_title}
</story_title>

<story_summary>
{story_summary}
</story_summary>

## Framework Overview:
1. Story Timeline: The narrative is viewed on a scale from 0 to 100, representing the percentage of progress through the story.
2. Story Components: The story is segmented into components defined by the protagonist's emotional journey.
3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
4. Emotional Arcs: The protagonist's emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10).


## Emotional Arcs
### Types of Emotional Arcs:
1. Increase: The protagonist's emotion improves by the end of the arc.
2. Decrease: The protagonist's emotion worsens by the end of the arc.
3. Flat: The protagonist's emotion remains unchanged by the end of the arc.

### Specific Emotional Arc Patterns:
1. Step-by-Step Increase/Decrease: Emotions change in distinct, noticeable stages
   Example: A character moving from fear (-5) to uncertainty (-2) to hope (+2) to joy (+6)
2. Linear Increase/Decrease: Consistent, steady change in emotional state
   Example: A character's growing dread as they approach danger, declining steadily from +3 to -4
3. Gradual-to-Rapid Increase/Decrease: Change starts slowly, then accelerates
   Example: A slow build of suspicion that suddenly turns to shocking realization
4. Rapid-to-Gradual Increase/Decrease: Change starts quickly, then slows down
   Example: An immediate burst of joy that settles into content satisfaction
5. Straight Increase/Decrease: Sudden, dramatic change in emotions
   Example: An unexpected tragedy causing immediate shift from +5 to -8
6. S-Curve Increase/Decrease: Change follows an 'S' shape (slow-fast-slow)
   Example: Gradually accepting good news, rapid excitement, then settling into happiness
7. Linear Flat: No change in emotions
   Example: Maintaining determined focus throughout a challenging task

## Analysis Guidelines

### Analysis Steps:
1. Identify the story's protagonist.
   - Choose the character whose emotional journey is most explicitly detailed in the summary
   - Prioritize the character with clearly described emotional states and transitions
   - Consider the character whose emotions most directly drive plot events
   - If the title character's emotional journey is well-documented, they are often the best choice
2. Segment the story into components based on major changes in the protagonist's emotions.
   - The number of components should be determined by the natural emotional transitions in the story
   - Most stories will naturally fall into 4-8 components, though shorter or longer stories may fall outside this range
   - Each significant emotional change should mark the start of a new component
   - As a general guideline, major emotional changes typically involve shifts of at least 3-4 points on the -10 to +10 scale
   - Components can vary in length based on the pace of emotional change in the story
   - Avoid over-segmentation: only create new components for meaningful emotional shifts, not minor fluctuations
3. Identify the emotional scores of each story component.
   - Scores must be whole numbers between -10 and +10
   - Score changes must match the selected arc type
4. For each story component:
   - Identify the exact portion of the story summary that corresponds to this segment
   - Extract all concrete details, events, and character actions from that portion
   - Note specific settings, dialogue, and interactions described
   - Use these details to write a comprehensive description that closely mirrors the source text
5. Identify the emotional arcs which connect story components.


Before providing the final JSON output, wrap your analysis in <story_analysis> tags. Consider the following:
- Identify the protagonist and their initial emotional state.
- Quote key phrases from the story summary that indicate emotional changes.
- List out potential story components with brief descriptions.
- Assign tentative emotional scores to each component (from -10 to +10).
- Determine the arc type for each component based on the score changes.
- Assign appropriate end times (as percentages) to each component.
- Ensure continuity between components.

After your analysis, provide the final output in the following JSON format:

{{
    "title": "Story Title",
    "protagonist": "Protagonist Name",
    "story_components": [
        {{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": initial_score,
            "arc": "#N/A"
        }},
        {{
            "end_time": percentage,
            "description": "Detailed description of events in this component",
            "end_emotional_score": score,
            "arc": "Arc Type"
        }},
        // Additional components as needed
    ]
}}

### Story Component Description Guidelines:
- Each description must be derived directly from the provided story summary
- Include specific events, actions, and dialogue from the source text
- Detail the physical settings where events take place
- Describe concrete actions taken by characters
- Incorporate relevant character interactions and relationships
- Avoid generalizations or interpretations not supported by the source text
- Quote or closely paraphrase key passages when possible
- Include sensory details mentioned in the summary

### Initial Emotional Score Guidelines:
- Consider the protagonist's state at the story's opening
- Look for descriptive words indicating emotional state

## Important Notes:
- The first component always has an end_time of 0, no description, and no arc.
- Ensure that end_emotional_scores are consistent with the arc types (e.g., an "Increase" arc should have a higher end_emotional_score than the previous component).
- Emotional scores must be whole numbers between -10 and +10.
- Adjacent components should not have the same emotional score unless using Linear Flat arc.
- End times must be in ascending order and the final component must end at 100.
- Each arc type must match the emotional change described:
  * Increase arcs must show higher end scores than start scores
  * Decrease arcs must show lower end scores than start scores
  * Flat arcs must maintain the same score
- Double-check your analysis for accuracy and internal consistency before providing the final JSON output.

Please proceed with your analysis and provide the JSON output. ONLY respond with the JSON and nothing else.
"""

    examples_section = """
<example>
<author_name>
Charles Perrault
</author_name>
<story_title>
Cinderella at the Ball
</story_title>
<story_summary>
Heartbroken and alone after being mocked and denied attendance by her stepfamily, Cinderella weeps in the garden until her Fairy Godmother appears. Through magical transformations, she provides Cinderella with a splendid carriage, resplendent gown, and delicate glass slippers, warning her to return before midnight. At the grand royal ball, Cinderella's kindness, modesty, and radiant beauty immediately enchant the Prince, who spends the entire evening dancing with her. Each moment increases her joy, until the clock strikes midnight. She flees in panic, losing a glass slipper on the palace steps. The Prince, determined to find her, searches the kingdom with the slipper until he reaches her home. When the slipper fits perfectly, they joyfully marry, with Cinderella's inner goodness finally rewarded.
</story_summary>
<ideal_output>
{
    "title": "Cinderella at the Ball",
    "protagonist": "Cinderella",
    "story_components": [
        {
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": -5,
            "arc": "#N/A"
        },
        {
            "end_time": 30,
            "description": "Weeping alone in the garden after being mocked and denied attendance by her stepfamily, Cinderella encounters her Fairy Godmother. Through a series of magical transformations, she receives a splendid carriage, resplendent gown, and delicate glass slippers, though warned about the midnight deadline.",
            "end_emotional_score": 2,
            "arc": "Step-by-Step Increase"
        },
        {
            "end_time": 60,
            "description": "Arriving at the grand ball in her magical carriage, Cinderella enters wearing her resplendent gown and glass slippers. Her kindness, modesty, and radiant beauty immediately enchant the Prince, who chooses to spend the entire evening dancing with her. Each passing moment increases her joy as they dance together in the palace.",
            "end_emotional_score": 8,
            "arc": "Gradual-to-Rapid Increase"
        },
        {
            "end_time": 75,
            "description": "As the clock strikes midnight, Cinderella flees the palace in panic. Running down the palace steps, she loses one of her glass slippers. Her magical evening comes to an abrupt end as she rushes away before her transformation wears off.",
            "end_emotional_score": -3,
            "arc": "Straight Decrease"
        },
        {
            "end_time": 100,
            "description": "The Prince, captivated by the mysterious woman who fled, searches throughout the kingdom with her abandoned glass slipper. Upon reaching Cinderella's home, the slipper fits her foot perfectly. Overjoyed at finding his true love, the Prince marries Cinderella, finally rewarding her genuine goodness.",
            "end_emotional_score": 10,
            "arc": "Gradual-to-Rapid Increase"
        }
    ]
}
</ideal_output>
</example>

Note About Example Output:
The descriptions in the example output demonstrate the minimum expected level of detail for story components. Each description should:
- Be at least as detailed as shown in the example
- Include as many concrete details from the source text as the story summary provides
- Mirror the source text's specific language and events
- Capture all relevant character actions, settings, and interactions mentioned
"""

    copy_and_paste = f"""
    {user_message}

    EXAMPLE:
    {examples_section}

    """

    #print(copy_and_paste)

    # Make the API call
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        temperature=0.3,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message
                    },
                    {
                        "type": "text",
                        "text": examples_section
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "<json_output></json_output>"
                    }
                ]
            }
        ]
    )

    #return json 
    return message.content[0].text

# Example usage:
# response = analyze_story("Homer", "The Odyssey", "In The Odyssey...")
# print(response)


def validate_story_arcs(data): #data should be json object
    
    # Initialize an empty list to store validation results
    validation_results = []
    
    # Previous emotional score for comparison; start with the first component
    title = data['title']
    prev_score = data['story_components'][0]['end_emotional_score']
    
    # Iterate through story components, starting from the second one
    for component in data['story_components'][1:]:
        current_score = component['end_emotional_score']
        arc = component['arc']
        end_time = component['end_time']
        expected_change = None
        
        # Determine expected change based on the arc description
        if "Increase" in arc:
            expected_change = "increase"
        elif "Decrease" in arc:
            expected_change = "decrease"
        elif "Flat" in arc:
            expected_change = "flat"
        
        # Determine actual change
        actual_change = None
        if current_score > prev_score:
            actual_change = "increase"
        elif current_score < prev_score:
            actual_change = "decrease"
        else:
            actual_change = "flat"
        
        # Compare expected change with actual change
        matches_description = expected_change == actual_change
        
        if(matches_description == False):
            error_string = f'ERROR: In {title} at end_time: {end_time} arc specified was: {expected_change} but actual score change was: {actual_change}'
            print(error_string)
            return "invalid"
        
        # Update previous score for the next iteration
        prev_score = current_score
    
    return "valid"


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    #encoding = tiktoken.get_encoding(encoding_name)
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def create_story_data(input_path, output_path):

    with open(input_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    
    story_title = story_data['title']
    author_name = story_data['openlib']['author_name'][0]
    year = story_data['openlib']['publishing']['first_publish_year']

    # List is in priority order
    summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    story_summary = ""
    story_summary_source = ""

    #use longest summary proxy for most complete
    for summary_source in summary_sources:
        if summary_source in story_data:
            summary_text = story_data[summary_source].get('summary', '')
            if summary_text and len(summary_text) > len(story_summary):
                story_summary = summary_text
                story_summary_source = summary_source
    
    print(story_summary_source)
    story_plot_data = analyze_story(author_name, story_title, story_summary)
    story_plot_data = json.loads(story_plot_data)
    story_validity = validate_story_arcs(story_plot_data)
    story_plot_data["type"] = "book"
    story_data["author"] = author_name
    story_data["year"] = year
    story_plot_data['summary'] = story_summary
    story_plot_data['story_summary_source'] = story_summary_source
    story_plot_data['shape_validity'] = story_validity
    story_data = {'story_plot_data': story_plot_data, **story_data} #add it so story_plot_data appears at the top
    

    for component in story_plot_data["story_components"]:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    output_path = output_path
    title = story_data['title'].lower().replace(' ', '_')
    output_path = os.path.join(output_path, f"{title}.json")
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data









def create_story_data_v2(input_path, output_path):

    with open(input_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
        print(story_data)
    

    story_plot_data = story_data
    #story_plot_data = json.loads(story_plot_data)
    story_validity = validate_story_arcs(story_plot_data)
    story_plot_data["type"] = "book"
    # story_data["author"] = author_name
    # story_data["year"] = year
    # story_plot_data['summary'] = story_summary
    # story_plot_data['story_summary_source'] = story_summary_source
    story_plot_data['shape_validity'] = story_validity
    story_data = {'story_plot_data': story_plot_data, **story_data} #add it so story_plot_data appears at the top
    

    for component in story_plot_data["story_components"]:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    output_path = output_path
    title = story_data['title'].lower().replace(' ', '_')
    output_path = os.path.join(output_path, f"{title}.json")
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data





create_story_data('/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_great_gatsby_composite_data.json', '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/')