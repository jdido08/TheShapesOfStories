from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import yaml
import tiktoken
import json 
import os 

def analyze_story(author_name, story_title, protagonist, story_summary, llm_provider, llm_model):
    

    # The user_message includes placeholders that will be replaced by the function arguments
    prompt_template = """You are a world-class literary scholar and expert in story analysis. Your task is to analyze a story through the emotional journey of {protagonist}. Please carefully read and analyze the following story summary:

<author_name>
{author_name}
</author_name>

<story_title>
{story_title}
</story_title>

<protagonist>
{protagonist}
</protagonist>

<story_summary>
{story_summary}
</story_summary>

## Framework Overview:
1. Story Timeline: The narrative is viewed on a scale from 0 to 100, representing the percentage of progress through the story.
2. Story Components: The story is segmented into components defined by {protagonist}'s emotional journey.
3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
4. Emotional Arcs: {protagonist}'s emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10), based on their direct experiences and reactions to events.


## Emotional Arcs
### Types of Emotional Arcs:
1. Increase: The protagonist's emotional state improves by the end of the arc.
2. Decrease: The protagonist's emotional state worsens by the end of the arc.
3. Flat: The protagonist's emotional state remains unchanged by the end of the arc.

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
1. Understand {protagonist}'s starting position in the story.
   - Identify their initial circumstances and relationships
   - Look for early indicators of their emotional state
   - Note their primary motivations and desires
2. Segment the story into components based on major changes in {protagonist}'s emotions.
   - The number of components should be determined by the natural transitions in their emotional state
   - Most stories will naturally fall into 4-8 components, though shorter or longer stories may fall outside this range
   - Each significant change in their emotional state should mark the start of a new component
   - As a general guideline, major emotional changes typically involve shifts of at least 3-4 points on the -10 to +10 scale
   - Components can vary in length based on the pace of emotional change
   - Avoid over-segmentation: only create new components for meaningful shifts in emotional state
3. Identify the emotional scores of each story component.
   - Scores must be whole numbers between -10 and +10 that reflect {protagonist}'s emotional state as evidenced in the story summary
   - Score changes must match the selected arc type
4. For each story component:
   - Identify the portion of the story summary that shows {protagonist}'s experience
   - Focus on events and details that reveal their emotional state
   - Note their actions, reactions, and key interactions
   - Use these details to write a description that centers on their journey
5. Identify the emotional arcs which connect story components.

After your analysis, provide the final output in the following JSON format:

{{{{
    "title": "Story Title",
    "protagonist": "Protagonist",
    "story_components": [
        {{{{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": initial_score,
            "arc": "#N/A"
        }}}},
        {{{{
            "end_time": percentage,
            "description": "Detailed description of events in this component",
            "end_emotional_score": score,
            "arc": "Arc Type"
        }}}},
    ]
}}}}

### Story Component Description Guidelines:
- Each description must be derived directly from the provided story summary
- Center the description on {protagonist}'s experience and perspective
- Describe events primarily in terms of their impact on {protagonist}
- Include their actions, reactions, and emotional responses
- Detail settings as they relate to their experience
- Include other characters mainly through their interaction with or impact on {protagonist}
- Quote or closely paraphrase passages that reveal their emotional state
- Include sensory details that contribute to understanding their experience

### Initial Emotional Score Guidelines:
- Carefully examine how {protagonist} is first presented in the story
- Look for descriptive words indicating their initial emotional state
- Consider their starting circumstances and relationships

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

____________________

EXAMPLE:

<example>
<author_name>
Charles Perrault
</author_name>
<story_title>
Cinderella at the Ball
</story_title>
<protagonist>
Cinderella
</protagonist>
<story_summary>
Heartbroken and alone after being mocked and denied attendance by her stepfamily, Cinderella weeps in the garden until her Fairy Godmother appears. Through magical transformations, she provides Cinderella with a splendid carriage, resplendent gown, and delicate glass slippers, warning her to return before midnight. At the grand royal ball, Cinderella's kindness, modesty, and radiant beauty immediately enchant the Prince, who spends the entire evening dancing with her. Each moment increases her joy, until the clock strikes midnight. She flees in panic, losing a glass slipper on the palace steps. The Prince, determined to find her, searches the kingdom with the slipper until he reaches her home. When the slipper fits perfectly, they joyfully marry, with Cinderella's inner goodness finally rewarded.
</story_summary>
<ideal_output>
{{{{
    "title": "Cinderella at the Ball",
    "protagonist": "Cinderella",
    "story_components": [
        {{{{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": -5,
            "arc": "#N/A"
        }}}},
        {{{{
            "end_time": 30,
            "description": "Cinderella weeps alone in the garden, heartbroken after her stepfamily mocks her desires and denies her chance to attend the ball. Her despair turns to wonder when her Fairy Godmother appears, transforming her circumstances through magical gifts: her pumpkin becomes a splendid carriage, mice become horses, and she receives a resplendent gown with glass slippers. Despite her rising hopes, she must bear the weight of the midnight deadline.",
            "end_emotional_score": 2,
            "arc": "Step-by-Step Increase"
        }}}},
        {{{{
            "end_time": 60,
            "description": "Cinderella experiences a profound transformation as she arrives at the grand ball. Her kindness and radiant beauty draw the Prince's attention, and she finds herself, for the first time, being treated with admiration and respect. As she dances with the Prince throughout the evening, each moment fills her with increasing joy and wonder, allowing her to momentarily forget her life of servitude.",
            "end_emotional_score": 8,
            "arc": "Gradual-to-Rapid Increase"
        }}}},
        {{{{
            "end_time": 75,
            "description": "Cinderella's magical evening shatters as the clock strikes midnight. Panic overtakes her as she flees the palace, losing a glass slipper in her desperate rush to escape. Her brief taste of happiness ends abruptly as she races to prevent the revelation of her true identity, watching her transformed world revert to its ordinary state.",
            "end_emotional_score": -3,
            "arc": "Straight Decrease"
        }}}},
        {{{{
            "end_time": 100,
            "description": "Cinderella's hopes revive when the Prince begins searching for her with the glass slipper. Her moment of triumph arrives when she steps forward in her home to try on the slipper, and it fits perfectly. Her patient endurance is finally rewarded as she marries the Prince, rising from her life of servitude to find happiness, maintaining her gracious nature by forgiving her stepfamily.",
            "end_emotional_score": 10,
            "arc": "Gradual-to-Rapid Increase"
        }}}}
    ]
}}}}
</ideal_output>
</example>

Note About Example Output:
The descriptions in the example output demonstrate the minimum expected level of detail for story components. Each description should:
- Center on the protagonist's experience and emotional journey
- Include concrete details that reveal the protagonist's state of mind
- Use language that reflects the protagonist's perspective
- Capture interactions primarily through their impact on the protagonist

"""
    prompt = PromptTemplate(
        input_variables=["author_name", "story_title", "protagonist", "story_summary"],  # Define the expected inputs
        template=prompt_template
    )


    config = load_config()
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    # Then invoke with the required inputs:
    output = runnable.invoke({
        "author_name": author_name,
        "story_title": story_title,
        "protagonist": protagonist,
        "story_summary": story_summary,
    })

    print(output)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    #attempt to extact json (if needed)
    output_text = extract_json(output_text)


    return output_text



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


def create_story_data(input_path="", author="", year="", protagonist="", output_path="", 
                      llm_provider="anthropic", llm_model="claude-3-5-sonnet-20241022"):

    with open(input_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    
    story_title = story_data['title']
    print("Creating story data for ", story_title)

    if author == "":
        author = story_data['openlib']['author_name'][0]
    
    if year == "":
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
    
    #print(story_summary_source)
    story_plot_data = analyze_story(author_name=author, story_title=story_title, protagonist=protagonist, story_summary=story_summary,
                                    llm_provider=llm_provider,llm_model=llm_model)
    story_plot_data = json.loads(story_plot_data)
    story_validity = validate_story_arcs(story_plot_data)
    story_plot_data["type"] = "book"
    story_plot_data["author"] = author
    story_plot_data["year"] = year
    story_plot_data['summary'] = story_summary
    story_plot_data['story_summary_source'] = story_summary_source
    story_plot_data['shape_validity'] = story_validity
    story_plot_data['story_data_llm'] = llm_model
   

    for component in story_plot_data["story_components"]:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    output_path = output_path
    title = story_plot_data['title'].lower().replace(' ', '_') + "_" + story_plot_data['protagonist'].lower().replace(' ', '_')
    output_path = os.path.join(output_path, f"{title}.json")
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data








