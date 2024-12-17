import yaml
from openai import OpenAI
from anthropic import Anthropic
import tiktoken
import json 
import os 




# Define variables 
ANTHROPIC_API_KEY = None


#define variables 
OPENAI_KEY = None

system_message = """
You are a helpful assistant and expert literary scholar.

Your task: Analyze any story by segmenting it into components based on the protagonist's emotional journey, following a framework inspired by Kurt Vonnegut's theory of story shapes.

-------------------------------------
FRAMEWORK OVERVIEW
-------------------------------------
- Timeline: Represent the story from 0% (start) to 100% (end).
- Protagonist’s Emotional State: Rated on a scale from +10 (euphoric) to -10 (depressed).
- Story Components: Divide the story into sequential components, each ending at a certain percentage (end_time) and capturing a segment of the protagonist’s emotional journey.

Each story component:
- Picks up where the last one ended (continuity).
- Is defined by a change or stability in the protagonist’s emotional state.
- Has an emotional arc describing how that state changes during the component.

-------------------------------------
EMOTIONAL ARCS
-------------------------------------
All arcs reflect how the protagonist’s emotions shift from the start to the end of that component. Broad categories:

1. Increase: End emotion > Start emotion.
2. Decrease: End emotion < Start emotion.
3. Flat: End emotion = Start emotion.

More specific patterns:
- **Step-by-Step Increase/Decrease**: Emotions change in distinct stages.
- **Linear Increase/Decrease**: Emotions change steadily and consistently.
- **Gradual-to-Rapid Increase/Decrease**: Emotions start slow and then accelerate.
- **Rapid-to-Gradual Increase/Decrease**: Emotions start fast and then slow down.
- **Straight Increase/Decrease**: Emotions shift sharply, suddenly.
- **S-Curve Increase/Decrease**: Emotions follow an S-shaped progression, starting slow, accelerating in the middle, then slowing again.
- **Linear Flat**: Emotions do not change.

-------------------------------------
OUTPUT FORMAT
-------------------------------------
Produce a JSON object with the following structure:

{
  "title": "<Story Title>",
  "protagonist": "<Protagonist Name>",
  "story_components": [
    {
      "end_time": 0,
      "description": "#N/A",
      "end_emotional_score": <initial_score>,
      "arc": "#N/A"
    },
    {
      "end_time": <int>,
      "description": "<A concise yet detailed summary of this story component, reflecting key events, emotional context, and narrative developments.>",
      "end_emotional_score": <int between -10 and 10>,
      "arc": "<Arc Type>"
    },
    ...
  ]
}

**Notes:**
- The first component at end_time=0 sets the baseline emotional state. It has no description or arc.
- Subsequent components define a story segment’s end_time, provide a brief description, assign an end_emotional_score, and choose an appropriate arc.
- Arcs must match the emotional trend between consecutive components. For example, an Increase arc requires that the end_emotional_score is higher than the previous component’s end_emotional_score.

-------------------------------------
EXAMPLE (Cinderella)
-------------------------------------
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
      "description": "Forced into servitude by her cruel stepfamily, Cinderella toils at endless chores and endures constant belittlement, maintaining a weary, stagnant emotional state.",
      "end_emotional_score": -5,
      "arc": "Linear Flat"
    },
    {
      "end_time": 50,
      "description": "A miraculous encounter with her Fairy Godmother—who provides a dazzling gown, a pumpkin-turned-carriage, and glass slippers—sparks newfound hope, gradually lifting her from despair.",
      "end_emotional_score": 0,
      "arc": "Step-by-Step Increase"
    },
    {
      "end_time": 70,
      "description": "At the grand royal ball, surrounded by music and laughter, she dances with the prince. This warm, accepting atmosphere elevates her spirits swiftly, granting her a sense of true belonging.",
      "end_emotional_score": 5,
      "arc": "Rapid-to-Gradual Increase"
    },
    {
      "end_time": 85,
      "description": "As midnight strikes and the spell dissolves, she flees the palace in panic, leaving behind a glass slipper. The abrupt loss of magic and potential love plunges her mood downward.",
      "end_emotional_score": -3,
      "arc": "Straight Decrease"
    },
    {
      "end_time": 100,
      "description": "The prince’s determined search leads to Cinderella’s discovery and the joyous reunion she longed for. Freed from her old life and embraced by love, her happiness soars to its highest peak.",
      "end_emotional_score": 10,
      "arc": "Gradual-to-Rapid Increase"
    }
  ]
}
"""


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

import yaml
from anthropic import Anthropic
import tiktoken
import json 
import os 
import re

def create_story_data(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    title = story_data['title']
    author = story_data['openlib']['author_name'][0]

    #list is in priority order
    summary_sources = ['sparknotes','cliffnotes','bookwolf','gradesaver','novelguide','pinkmonkey','shmoop','thebestnotes','wiki','other']
    all_summaries = ""
    summary_count = 1
    for summary_source in summary_sources:
        if summary_count < 3: #keeping things to max of two data sources 
            if(summary_source in story_data):
                summary_text = story_data[summary_source]['summary']
                if(summary_text != ""):
                    summary = f'Summary #{summary_count}: {summary_text}\n\n'
                    all_summaries = all_summaries + summary
                    summary_count = summary_count + 1

    user_prompt_1 = f"""
You are a literary scholar focusing on {author}'s "{title}". Below are up to two reference summaries of the story. Review these summaries and then produce a JSON analysis following the given framework. Ensure internal logic: arcs match emotional changes, and the structure is consistent.

Summaries:
{all_summaries}

When done, output ONLY the JSON structure as instructed. Do NOT include any additional text or explanation.
"""

    user_prompt_2 = """
Now, carefully double-check the JSON analysis you just provided. Confirm that every arc chosen aligns with the change in emotional score between that component and the previous one.

- If corrections are needed (e.g., arc does not match the emotional trend), output the corrected JSON.
- If no corrections are needed, just output the same JSON again.

Output ONLY the JSON. Do NOT include any additional text or explanation.
"""

    user_prompts = [user_prompt_1, user_prompt_2]

    # Read Anthropic API key from config
    with open("config.yaml", 'r') as stream:
        config = yaml.safe_load(stream)
        ANTHROPIC_API_KEY = config['anthropic_key']
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

    messages = []
    # Prepare messages for Claude
    for user_prompt in user_prompts:
      # Call Claude 3.5 Sonnet
      print("Sending prompt:", user_prompt)  # Debug print
        
      completion = client.messages.create(
          model="claude-3-5-sonnet-20240620", 
          max_tokens=4095,
          temperature=0.4,
          system=system_message,
          messages=[
              {"role": "user", "content": user_prompt}
          ]
      )
        
      response = completion.content[0].text
      data = {"role":"assistant", "content":response}
      messages.append(data)

    # Extract JSON with regex
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    
    if not json_match:
        # If no JSON found, handle gracefully
        return None

    clean_json = json_match.group(0)

    try:
        story_plot_data = json.loads(clean_json)
    except json.JSONDecodeError:
        return None

    # Validation step
    if validate_story_arcs(story_plot_data) == "invalid":
        # If invalid, let the next user prompt fix it
        print("DATA IS INVALID NEED TO RECOMPUTE")


    # Add modified end points (if needed)
    for component in story_plot_data["story_components"]:
        
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    # Prepare output path
    output_path = output_path
    title = story_data['title'].lower().replace(' ', '_')
    output_path = os.path.join(output_path, f"{title}.json")
    
    # Write to file
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data

