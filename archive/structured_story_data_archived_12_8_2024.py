import yaml
from openai import OpenAI
import tiktoken
import json 
import os 


#define variables 
OPENAI_KEY = None

system_message = """
You're a helpful assistant and expert literary scholar. 

Please analyze any story using the following framework inspired by Kurt Vonnegut's thesis on the shapes of stories. The frameworks segments a story into components based on the protagonist's emotional journey.

Framework Overview:
1. Story Time: A story's narrative is viewed on a timeline from 0 to 100, representing the percentage of progress through the story. Time 0 is the very start of the story, and time 100 is its conclusion.
2. Story Components: A story can be segmented into components defined by the protagonist's emotional journey.
3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
4. Emotional Arcs: The protagonist's emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10). See details below for the different types of emotional arcs.

Types of Emotional Arcs:
There are three main emotional arcs:
1. Increase i.e. the emotion of the protagonist increases by the end of the arc
2. Decrease i.e. the emotion of the protagonist decreases by the end of the arc
3. Flat i.e. the emotion of the protagonist does not increase or decrease by the end of the arc

These main emotional arcs can be further divided into specific patterns:
1. Step-by-Step Increase: The protagonist's emotions improve in distinct, noticeable stages. Each step signifies a clear, positive change in their emotional state.
2. Step-by-Step Decrease: The protagonist's emotions deteriorate in distinct, noticeable stages. Each step signifies a clear, negative change in their emotional state.
3. Linear Increase: The protagonist experiences a consistent, steady improvement in their emotional state, marked by a gradual, ongoing increase without major jumps or drops.
4. Linear Decrease: The protagonist’s emotional state consistently worsens at a steady rate, characterized by a gradual, ongoing decrease without sudden dips or recoveries.
5. Gradual-to-Rapid Increase: The protagonist's emotions rise gradually initially, then accelerating over time, creating a concave up curve.
6. Rapid-to-Gradual Increase: The protagonist's emotions rise rapidly initially, then slowing down over time, creating a concave down curve.
7. Rapid-to-Gradual Decrease: The protagonist's emotions drop sharply initially, then gradually over time, creating a concave up curve.
8. Gradual-to-Rapid Decrease: The protagonist's emotions drop slowly initially, and then sharply over time, creating a concave down curve.
9. Straight Increase: The protagonist’s emotions improve in a sudden, dramatic fashion, marked by a sharp, upward change in their emotional state without gradual progression.
10. Straight Decrease: The protagonist experiences a swift, dramatic decline in emotions, characterized by a sharp, downward shift without the gradual fall of a linear decrease.
11. S-Curve Increase: The protagonist's emotions begin with a gradual improvement, accelerates to a more rapid increase in the middle, and then decelerates towards the end, resembling the shape of an 'S'.
12. S-Curve Decrease: The protagonist's emotions start to decline slowly, accelerates into a faster decline in the middle, and then finally, slows down again as it approaches the end, creating a reverse 'S' shape.
13. Linear Flat: The protagonist's emotions do not increase or decrease i.e. they remain unchanged.

Structure of Analysis:
The framework is applied using the following steps:
1. Identify the story's protagonist.
2. Segment the story into story components based on major changes in the protagonist's emotions.
3. Identify the emotional scores of each story component.
4. Identify the emotional arcs which connect story components.

Example:
Below are a few examples of the framework applied and the resultant JSON output. Please note:
    a. The "title" field represents the name of the story.
    b. The "protagonist" field represents the main character of the story.
    c. The "story_components" is an array representing different segments of the story. Each story component consists of the following sub-fields:
        c.1 The 'end_time' field marks the relative point in the story's timeline, on a scale from 0 (the beginning) to 100 (the end), indicating when a component concludes. For example, an 'end_time' of 20 means this component ends 20% into the story.
        c.2 The "description" field provides a brief overview or summary of the particular story component.
        c.3 The "end_emotional_score" field indicates the emotional state of the protagonist at the conclusion of that story component, on a scale from the +10 (best positive emotion) to -10 (the worst negative emotion)
        c.4 The "arc" field describes the type of emotional arc experienced by the protagonist during the story component. 
    d. The "end_emotional_score" and "end_time" fields of one component mark the beginning emotional state and starting point, respectively, for the subsequent component.
    e. The initial or first story component is treated differently than the rest as it sets the baseline for the emotional journey:
        e.1 The "end_time" field is always set 0 
        e.2 The "description" and "arc" fields are not applicable.
        e.3 The "end_emotional_score" field represents the emotional score of the protogonist at the beginning of the story

Example 1: Cinderella
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
            "description": "Cinderella suffers under her stepfamily, feeling emotionally stagnant and unhappy.",
            "end_emotional_score": -5,
            "arc": "Linear Flat"
        },
        {
            "end_time": 50,
            "description": "Meeting her Fairy Godmother, Cinderella experiences a step-by-step uplift in spirits.",
            "end_emotional_score": -1,
            "arc": "Step-by-Step Increase"
        },
        {
            "end_time": 75,
            "description": "Her joy at the ball peaks but fades as midnight approaches.",
            "end_emotional_score": 5,
            "arc": "Rapid-to-Gradual Increase"
        },
        {
            "end_time": 80,
            "description": "The enchantment's abrupt end plunges her back into despair.",
            "end_emotional_score": -3,
            "arc": "Straight Decrease"
        },
        {
            "end_time": 100,
            "description": "The prince's search and their reunion lift Cinderella to peak happiness.",
            "end_emotional_score": 10,
            "arc": "Gradual-to-Rapid Increase"
        }
    ]  
}


Example 2: Man in Hole
{
    "title": "Man in Hole",
    "protagonist": "Man",
    "story_components": [
        {
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": 2,
            "arc": "#N/A"
        },
        {
            "end_time": 50,
            "description": "The man falls into a hole, plunging into despair and struggling to adapt.",
            "end_emotional_score": -5,
            "arc": "Rapid-to-Gradual Decrease"
        },
        {
            "end_time": 100,
            "description": "Gradually, he regains hope and makes progress towards escape.",
            "end_emotional_score": 2,
            "arc": "Gradual-to-Rapid Increase"
        }
    ]
}




Example 3: Boy Meets Girl
{
    "title": "Boy Meets Girl",
    "protagonist": "Boy",
    "story_components": [
        {
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": 0,
            "arc": "N/A"
        },
        {
            "end_time": 33,
            "description": "Boy's life changes with the girl's arrival, bringing joy and a new normal.",
            "end_emotional_score": 5,
            "arc": "Rapid-to-Gradual Increase"
        },
        {
            "end_time": 66,
            "description": "Relationship strains lead to a breakup, causing emotional turmoil.",
            "end_emotional_score": -5,
            "arc": "S-Curve Decrease"
        },
        {
            "end_time": 100,
            "description": "Reflection and renewed communication lead to a happy, mature reunion.",
            "end_emotional_score": 5,
            "arc": "Gradual-to-Rapid Increase"
        }
    ]
}


Example 4: Creation Story 
{
    "title": "Creation Story",
    "protagonist": "God",
    "story_components": [
        {
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": 0,
            "arc": ""
        },
        {
            "end_time": 86,
            "description": "Out of nothing God creates the universe, Earth, and all living creatures in six days.",
            "end_emotional_score": 10,
            "arc": "Step-by-Step Increase"
        },
        {
            "end_time": 100,
            "description": "God rested on the seventh day.",
            "end_emotional_score": 10,
            "arc": "Linear Flat"
        }
    ]
}

Questions?
If you have any questions about this framework or need further clarification on how to apply it to, please feel free to ask.

"""


story_descriptor_prompt = """
Please identify key words and/or phrases that best represent and describe each story component.

The key words/phrases should help observers identify this particular story segment. Key words and/or phrases should be:
1. Iconic phrases or popular quotes from the story segment.
2. Names or descriptions of important or iconic characters involved in that part of the story.
3. Names or descriptions of significant events that occur during the segment.
4. Names or descriptions of notable inanimate objects that play a role in the story segment.
5. Names or descriptions of key settings where the story segment takes place.
6. Descriptive phrases of the story segment
Note that:
- all key words/phrases should be listed in chronological order
- no key words/phrases should contain the name of the story or the name of the main protagonist

Please output your response like the JSON examples below. Note that:
- "descriptors" field is where the key words/phrases are listed. 
- all key words/phrases end with some punctation e.g. period ("."), exclamation point ("!"), question mark ("?"), or an ellipsis ("...").



Cinderella Example:
{
  "title": "Cinderella",
  "protagonist": "Cinderella",
  "story_components": [
    {
      "end_time": 0,
      "description": "#N/A",
      "end_emotional_score": -5,
      "arc": "#N/A",
      "descriptors": [
        "#N/A"
      ]
    },
    {
      "end_time": 20,
      "description": "Cinderella suffers under her stepfamily, feeling emotionally stagnant and unhappy.",
      "end_emotional_score": -5,
      "arc": "Linear Flat",
      "descriptors": [
        "Stepmother.",
        "Stepsisters.",
        "Chores."
      ]
    },
    {
      "end_time": 50,
      "description": "Meeting her Fairy Godmother, Cinderella experiences a step-by-step uplift in spirits.",
      "end_emotional_score": -1,
      "arc": "Step-by-Step Increase",
      "descriptors": [
        "Fairy Godmother.",
        "Bibbidi-Bobbidi-Boo.",
        "Pumpkin Carriage."
      ]
    },
    {
      "end_time": 75,
      "description": "Her joy at the ball peaks but fades as midnight approaches.",
      "end_emotional_score": 5,
      "arc": "Rapid-to-Gradual Increase",
      "descriptors": [
        "Royal Ball.",
        "Prince Charming."
      ]
    },
    {
      "end_time": 80,
      "description": "The enchantment's abrupt end plunges her back into despair.",
      "end_emotional_score": -3,
      "arc": "Straight Decrease",
      "descriptors": [
        "The Stroke of Midnight.",
        "Glass Slipper."
      ]
    },
    {
      "end_time": 100,
      "description": "The prince's search and their reunion lift Cinderella to peak happiness.",
      "end_emotional_score": 10,
      "arc": "Gradual-to-Rapid Increase",
      "descriptors": [
        "Search for Love.",
        "The Shoe Fits.",
        "Happily Ever After."
      ]
    }
  ]
}

A Christmas Carol Story Example:
{
  "title": "A Christmas Carol",
  "protagonist": "Ebenezer Scrooge",
  "story_components": [
    {
      "end_time": 0,
      "description": "#N/A",
      "end_emotional_score": -3,
      "arc": "#N/A",
      "descriptors": [
        "#N/A"
      ]
    },
    {
      "end_time": 20,
      "description": "Scrooge is bitter, miserly and uncaring towards others on Christmas Eve.",
      "end_emotional_score": -3,
      "arc": "Linear Flat",
      "descriptors": [
        "Bah!",
        "Humbug!"
      ]
    },
    {
      "end_time": 30,
      "description": "Scrooge is visited by the ghost of Jacob Marley.",
      "end_emotional_score": -4,
      "arc": "S-Curve Decrease",
      "descriptors": [
        "Marley."
      ]
    },
    {
      "end_time": 50,
      "description": "Scrooge is forced to confront his past thanks to the Ghost of Christmas Past, causing sadness and regret.",
      "end_emotional_score": -1,
      "arc": "Gradual-to-Rapid Increase",
      "descriptors": [
        "Past.",
        "Fezziwig.",
        "Belle."
      ]
    },
    {
      "end_time": 65,
      "description": "Scrooge sees joy around him with the Ghost of Christmas Present but also suffering, moving him with pity and concern.",
      "end_emotional_score": 3,
      "arc": "Linear Increase",
      "descriptors": [
        "Present.",
        "Cratchit.",
        "Tiny Tim.",
        "Games."
      ]
    },
    {
      "end_time": 70,
      "description": "Ghost of Christmas Present shows Scrooge two starved children, Ignorance and Want, living under his coat",
      "end_emotional_score": -3,
      "arc": "Gradual-to-Rapid Decrease",
      "descriptors": [
        "Ignorance.",
        "Want."
      ]
    },
    {
      "end_time": 90,
      "description": "Seeing his own grave, Scrooge is terrified and desperate to change his fate.",
      "end_emotional_score": -6,
      "arc": "S-Curve Decrease",
      "descriptors": [
        "Yet to Come.",
        "Pawn Shop.",
        "Gravestone... "
      ]
    },
    {
      "end_time": 100,
      "description": "Scrooge wakes up overjoyed at having a second chance and keeps his promise to honor Christmas.",
      "end_emotional_score": 9,
      "arc": "Rapid-to-Gradual Increase",
      "descriptors": [
        "Awake.",
        "Joy.",
        "Merry Christmas!",
        "Turkey.",
        "Pay Raise.",
        "Party.",
        "God bless us, Every one!"
      ]
    }
  ]
}
"""

import json

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

    
    if(summary_count > 1):
        user_prompt_1 = f'You are a literary scholar with a particular focus on {author}\'s {title}. As a helpful reference below are summaries of the story. Please carefully read the summaries and then carefully analyze the story step-by-step. When you are complete, please double check your analysis so it is both accurate and internally consistent (e.g. decreasing arcs are matched by decreasing end_emotional_scores between story components). \n\n {all_summaries}'
    else:
        user_prompt_1 = f'You are a literary scholar with a particular focus on {author}\'s {title}. As a helpful reference below is a summary of the story. Please carefully read the summary and then carefully analyze the story step-by-step. When you are complete, please double check your analysis so it is both accurate and internally consistent (e.g. decreasing arcs are matched by decreasing end_emotional_scores between story components). \n\n {all_summaries}'
    
    user_prompt_2 = f'Please carefully double check your analysis to ensure it is both accurate and internally consistent (e.g. decreasing arcs are matched by decreasing end_emotional_scores between story components). If corrections are needed, please only output the corrected JSON'
 
    user_prompt_3 = story_descriptor_prompt
   

    user_prompts = [user_prompt_1, user_prompt_2, user_prompt_3]
    chat_messages = [
        {"role":"system", "content":system_message}
    ]

    with open("config.yaml", 'r') as stream:
        config = yaml.safe_load(stream)
        OPENAI_KEY = config['openai_key_vonnegutgraphs']
        client = OpenAI(api_key=OPENAI_KEY)


    for user_prompt in user_prompts:
        data = {"role":"user", "content":user_prompt}
        chat_messages.append(data)

        completion = client.chat.completions.create(
            #model="gpt-3.5-turbo-1106",
            model="gpt-4-1106-preview", 
            max_tokens=4095,
            temperature = 0.4,
            response_format={ "type": "json_object" }, #note only "gpt-4-1106-preview" and "gpt-3.5-turbo-1106" support JSON MODE 
            messages=chat_messages
        ) 

        response = completion.choices[0].message.content #get response
        data = {"role":"assistant", "content":response}
        chat_messages.append(data)

    story_plot_data = json.loads(response)
     #story_data = {'story_plot_data': story_plot_data, **story_data} #add it so story_plot_data appears at the top


    for component in story_plot_data["story_components"]:
        component['modified_end_point'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_time']
    
    output_path = output_path
    title = story_data['title'].lower().replace(' ', '_')
    output_path = os.path.join(output_path, f"{title}.json")
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data




