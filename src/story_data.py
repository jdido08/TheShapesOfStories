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

Framework Overview:
1. Story Timeline: The narrative is viewed on a scale from 0 to 100, representing the percentage of progress through the story.
2. Story Components: The story is segmented into components defined by the protagonist's emotional journey.
3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
4. Emotional Arcs: The protagonist's emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10).

Types of Emotional Arcs:
1. Increase: The protagonist's emotion improves by the end of the arc.
2. Decrease: The protagonist's emotion worsens by the end of the arc.
3. Flat: The protagonist's emotion remains unchanged by the end of the arc.

Specific Emotional Arc Patterns:
1. Step-by-Step Increase/Decrease: Emotions change in distinct, noticeable stages.
2. Linear Increase/Decrease: Consistent, steady change in emotional state.
3. Gradual-to-Rapid Increase/Decrease: Change starts slowly, then accelerates.
4. Rapid-to-Gradual Increase/Decrease: Change starts quickly, then slows down.
5. Straight Increase/Decrease: Sudden, dramatic change in emotions.
6. S-Curve Increase/Decrease: Change follows an 'S' shape (slow-fast-slow).
7. Linear Flat: No change in emotions.

Analysis Steps:
1. Identify the story's protagonist.
2. Segment the story into components based on major changes in the protagonist's emotions.
3. Identify the emotional scores of each story component.
4. Identify the emotional arcs which connect story components.

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

Important Notes:
- The first component always has an end_time of 0, no description, and no arc.
- Ensure that end_emotional_scores are consistent with the arc types (e.g., an "Increase" arc should have a higher end_emotional_score than the previous component).
- Double-check your analysis for accuracy and internal consistency before providing the final JSON output.

Please proceed with your analysis and provide the JSON output. ONLY respond with the JSON and nothing else.
"""

    examples_section = """
<example>
<author_name>
Charles Perrault
</author_name>
<story_title>
Cinderella
</story_title>
<story_summary>
Charles Perrault’s "Cinderella" follows a kind and gentle girl who, after the death of her devoted father, endures cruelty and scorn from her stepmother and stepsisters. Forced into servitude, Cinderella suffers silently but remains compassionate and forgiving, never losing her innate goodness despite her dire circumstances.

One day, the King’s son announces a grand ball to find a bride, inviting all eligible young women. Cinderella longs to attend, but her stepfamily mocks her and denies her the means to participate. While they leave for the festivities, Cinderella is left at home, heartbroken and despairing over her situation.

Suddenly, her Fairy Godmother appears and, through a series of magical transformations, provides Cinderella with a splendid carriage (crafted from a pumpkin), gracious horses (from mice), a dignified coachman (from a rat), attentive footmen (from lizards), and most importantly, a resplendent gown complete with delicate glass slippers. The Fairy Godmother warns her to return before midnight when the magic will end.

At the ball, Cinderella’s kindness, modesty, and radiant beauty enchant the Prince. They spend the evening together, each moment increasing Cinderella’s sense of joy and hope. When the clock strikes midnight, however, she flees to avoid revealing her humble state. In her haste, she leaves a single glass slipper behind.

Determined to find the mysterious young woman who captivated him, the Prince scours the land. He eventually arrives at Cinderella’s home. After her stepsisters fail to fit into the slipper, Cinderella steps forward, and the slipper fits her perfectly, confirming her identity. Overjoyed, the Prince marries her. She, in turn, graciously forgives her stepfamily. Thus, Cinderella ascends from servitude to royalty, symbolizing the reward of patience, kindness, and unwavering inner virtue.
</story_summary>
<ideal_output>
<story_analysis>
Let's analyze the story of Cinderella using the given framework:

1. Protagonist: Cinderella

2. Initial emotional state: We can infer that Cinderella starts in a negative emotional state due to her mistreatment by her stepfamily. Let's assign an initial score of -5.

3. Potential story components:
   a. Life under stepfamily's rule
   b. Meeting the Fairy Godmother
   c. Attending the ball
   d. Fleeing at midnight
   e. Prince's search and reunion

4. Let's assign emotional scores and determine arc types:

   a. Life under stepfamily's rule:
      - Emotional score remains at -5
      - Arc: Linear Flat (no change in emotions)
      - End time: 20% (this sets up the initial situation)

   b. Meeting the Fairy Godmother:
      - Emotional score improves to -1
      - Arc: Step-by-Step Increase (magic transformations happen in stages)
      - End time: 50% (preparation for the ball takes significant story time)

   c. Attending the ball:
      - Emotional score peaks at 5
      - Arc: Rapid-to-Gradual Increase (initial excitement, then enjoyment)
      - End time: 75% (the ball is a crucial event in the story)

   d. Fleeing at midnight:
      - Emotional score drops to -3
      - Arc: Straight Decrease (sudden change as magic ends)
      - End time: 80% (a brief but impactful moment)

   e. Prince's search and reunion:
      - Emotional score rises to 10 (happily ever after)
      - Arc: Gradual-to-Rapid Increase (hope builds, then joy at reunion)
      - End time: 100% (concludes the story)

5. Continuity check: Each component starts where the previous one ended, ensuring a seamless emotional journey.

Now, let's format this analysis into the required JSON structure.
<json_output>
<story_analysis>
{
    "title": "Cinderella",
    "protagonist": "Cinderella",
    "story_components": [
        {
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": -5,
            "arc": "#N/A"
        },
        {
            "end_time": 20,
            "description": "After her father’s death, Cinderella suffers under her stepmother and stepsisters, performing endless chores and facing their cruelty. Though mistreated and scorned, she remains gentle and forgiving, never losing her kind spirit despite the harsh environment of her own home.",
            "end_emotional_score": -5,
            "arc": "Linear Flat"
        },
        {
            "end_time": 50,
            "description": "Denied any chance to attend the King’s son’s grand ball, Cinderella is left behind while her stepfamily goes to enjoy the festivities. Heartbroken and alone, she weeps until her Fairy Godmother appears. Through magical transformations, a pumpkin becomes a splendid carriage, mice become graceful horses, a rat becomes a dignified coachman, and lizards become attentive footmen. Dressed now in a resplendent gown and delicate glass slippers, Cinderella gains renewed hope—provided she returns before midnight, as warned by her benefactor.",
            "end_emotional_score": -1,
            "arc": "Step-by-Step Increase"
        },
        {
            "end_time": 75,
            "description": "At the royal ball, the Prince is immediately drawn to Cinderella’s kindness, modesty, and radiant beauty. They spend the evening together, an event that lifts Cinderella’s spirits as she experiences genuine admiration and the promise of a better life than the one she left at home.",
            "end_emotional_score": 5,
            "arc": "Rapid-to-Gradual Increase"
        },
        {
            "end_time": 80,
            "description": "As the clock strikes midnight, Cinderella abruptly flees to avoid revealing her true, humble condition. In her haste, she leaves behind a single glass slipper, the only trace of her transformed state. With the magic ending, her garments and conveyance revert to their ordinary forms, and she returns to her former life, worried and saddened by what she has lost.",
            "end_emotional_score": -3,
            "arc": "Straight Decrease"
        },
        {
            "end_time": 100,
            "description": "Determined to find the one who enchanted him, the Prince searches the land with the abandoned slipper. When he arrives at Cinderella’s home, the stepsisters fail to fit the glass slipper. Cinderella then tries it on, and it fits perfectly, revealing her identity. Overjoyed, the Prince marries her. Cinderella forgives her stepfamily and rises from servitude to a life of royal happiness, her inner goodness finally rewarded.",
            "end_emotional_score": 10,
            "arc": "Gradual-to-Rapid Increase"
        }
    ]  
}
</json_output>
</story_analysis>
</ideal_output>
</example>
"""

    copy_and_paste = f"""
    {user_message}

    EXAMPLE:
    {examples_section}

    """

    print(copy_and_paste)

    # # Make the API call
    # message = client.messages.create(
    #     model="claude-3-5-sonnet-20241022",
    #     max_tokens=1000,
    #     temperature=0,
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": examples_section
    #                 },
    #                 {
    #                     "type": "text",
    #                     "text": user_message
    #                 }
    #             ]
    #         },
    #         {
    #             "role": "assistant",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": "<json_output></json_output>"
    #                 }
    #             ]
    #         }
    #     ]
    # )

    # #return json 
    # return message.content[0].text

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



# input_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/the_great_gatsby.json'
# output_path = '//Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/'
# create_story_data_v2(input_path, output_path)


