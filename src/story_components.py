
from llm import load_config, get_llm, extract_json
import yaml
import tiktoken
import json 
import os 

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser



#call LLM to get story components
def analyze_story(config_path, author_name, story_title, protagonist, story_summary, llm_provider, llm_model):
    

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
   - Identify as many components as necessary to accurately track the protagonist's journey. Do not worry about the total number of components; accuracy is prioritized over brevity.
   - Each significant change in their emotional state should mark the start of a new component
   - Create a new component for any discernible shift in emotional state (e.g., a shift of even 1 or 2 points). We want to capture the granular nuance of the journey.
   - Components can vary in length based on the pace of emotional change
   - When in doubt, create a new segment. Capture the sequence of events precisely.
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
- The first component (end_time = 0) is the baseline emotional state *before* any on-page events shift the protagonist’s emotions.
- If the backstory implies a sharp change *into* the opening scene, do not reflect the change at end_time = 0; instead, start from the baseline and make the first change in the first arc that ends > 0.
- Ensure that end_emotional_scores are consistent with the arc types (e.g., an "Increase" arc should have a higher end_emotional_score than the previous component).
- Emotional scores must be whole numbers between -10 and +10. 
- If the emotional score remains the same (e.g., -5 to -5), the Arc Type MUST be "Linear Flat". You strictly cannot label an arc as "Increase" or "Decrease" if the score number does not change.
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
Heartbroken and exhausted, Cinderella toils endlessly in her own home after her father’s death leaves her at the mercy of her cruel stepmother and spiteful stepsisters. Forced to cook, clean, and tend to every chore while enduring their constant insults, Cinderella clings to a quiet hope for a kinder future, though she often feels lonely and powerless. One day, an announcement arrives that the royal family is hosting a grand ball to find a bride for the Prince. Eager for a chance at happiness, Cinderella timidly asks if she may attend. Her stepmother and stepsisters mock her wish and forbid it, leaving her devastated. Even so, Cinderella manages to gather scraps of optimism, trying to sew a suitable dress from her late mother’s belongings—only for her stepsisters to shred it in a fit of jealousy moments before the ball. Crushed by this cruel betrayal, she flees to the garden, overwhelmed by despair. It is there that her Fairy Godmother appears, transforming Cinderella’s tattered clothes into a resplendent gown and conjuring a gleaming carriage from a humble pumpkin. As Cinderella’s hopes rise, the Fairy Godmother warns her that the magic will end at midnight. At the grand royal ball, the Prince is immediately enchanted by her gentle grace and luminous presence. For the first time, Cinderella basks in admiration instead of scorn, feeling her spirits soar with each dance and conversation. However, as the clock strikes midnight, she is forced to flee the palace. In her panic to escape before the spell breaks, she loses one of her delicate glass slippers on the palace steps. Despite her sudden disappearance, the Prince is determined to find this mysterious young woman, traveling throughout the kingdom with the slipper in hand. When his search brings him to Cinderella’s home, her stepsisters deride the idea that she could be the one who captured the Prince’s heart. Yet, as soon as Cinderella tries on the slipper, it fits perfectly. Freed at last from servitude, she marries the Prince, and her enduring kindness and patience are joyously rewarded.
</story_summary>
<ideal_output>
{{
    "title": "Cinderella at the Ball",
    "protagonist": "Cinderella",
    "story_components": [
        {{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": -5,
            "arc": "#N/A"
        }},
        {{
            "end_time": 15,
            "description": "Cinderella asks to attend the ball, hoping for a brief respite from her misery. Her stepmother and stepsisters cruelly mock her request and forbid her from going, crushing her tentative hope.",
            "end_emotional_score": -7,
            "arc": "Linear Decrease"
        }},
        {{
            "end_time": 25,
            "description": "Despite the ban, Cinderella tries to sew a dress from her mother's old things. However, right before the ball, her stepsisters discover her and physically rip the dress to shreds. Devastated and betrayed, she runs to the garden sobbing.",
            "end_emotional_score": -9,
            "arc": "Rapid-to-Gradual Decrease"
        }},
        {{
            "end_time": 35,
            "description": "The Fairy Godmother appears in the garden. Cinderella's despair turns to shock and then rising wonder as the pumpkin is transformed into a carriage and her rags into a gown.",
            "end_emotional_score": 4,
            "arc": "Step-by-Step Increase"
        }},
        {{
            "end_time": 60,
            "description": "Cinderella enters the ball. She is overcome with joy as the Prince asks her to dance. For the first time in her life, she feels seen, admired, and deeply happy, forgetting her life of servitude completely.",
            "end_emotional_score": 9,
            "arc": "Gradual-to-Rapid Increase"
        }},
        {{
            "end_time": 70,
            "description": "The clock strikes midnight. The dream abruptly ends. Cinderella is seized by panic and anxiety as she flees the palace, losing her slipper and terrified of being discovered in her rags.",
            "end_emotional_score": -2,
            "arc": "Straight Decrease"
        }},
        {{
            "end_time": 90,
            "description": "Back home, Cinderella resumes her chores. She is anxious and fearful as the Prince searches the kingdom, watching her stepsisters try to force the slipper on. She feels powerless, unsure if she should reveal herself.",
            "end_emotional_score": -4,
            "arc": "Linear Decrease"
        }},
        {{
            "end_time": 100,
            "description": "The Prince allows Cinderella to try the slipper. It fits perfectly. In a moment of pure vindication and relief, she is whisked away to marry the Prince, her kindness finally rewarded with a happily ever after.",
            "end_emotional_score": 10,
            "arc": "Straight Increase"
        }}
    ]
}}
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


    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    try:
        output = runnable.invoke({
            "author_name": author_name,
            "story_title": story_title,
            "protagonist": protagonist,
            "story_summary": story_summary
        })
        # If output is a AIMessage, its `response_metadata` might have info
        # if hasattr(output, "response_metadata"):
        #     print("LLM Response Metadata:", output.response_metadata)

    except Exception as e:
        print(f"Error during LLM call: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'): # Example for some libraries
            print("Prompt Feedback:", e.response.prompt_feedback)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    if hasattr(output, "content"):
        # Check if content is a list (Google/LangChain edge case)
        if isinstance(output.content, list):
            # Extract text from all blocks
            text_parts = []
            for block in output.content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            output_text = "".join(text_parts)
        else:
            # Standard string content
            output_text = str(output.content)
    else:
        output_text = str(output)

    #attempt to extact json (if needed)
    output_text = extract_json(output_text)

    if output_text == "" or output_text == None or output_text == {}:
        print("❌ ERROR: LLM failed to analyze story into components")
        raise ValueError("ERROR: LLM failed to analyze story into components")


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
            raise ValueError(error_string)
        
        # Update previous score for the next iteration
        prev_score = current_score
    
    return "valid"


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    #encoding = tiktoken.get_encoding(encoding_name)
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


# return story components 
def get_story_components(config_path,story_title, story_summary, author, year, protagonist, 
                      llm_provider="anthropic", llm_model="claude-3-5-sonnet-20241022"):

   
    #print(story_summary_source)
    story_components = analyze_story(config_path=config_path, author_name=author, story_title=story_title, protagonist=protagonist, story_summary=story_summary,
                                    llm_provider=llm_provider,llm_model=llm_model)
    
    story_components = extract_json(story_components)
    # print(story_components)
    story_components = json.loads(story_components)
    #print(story_components)

    #chekc if story_component are valid
    story_components_validity = validate_story_arcs(story_components) #call to confirm story_components are valid

    #check if right protagonist was chosen
    if story_components['protagonist'] != protagonist:
        print("LLM designated protagonist as: ", story_components['protagonist'], " but I specified protagonist as: ", protagonist)
        print("PLEASE RESOLVE")
        raise ValueError

    #check if right author was chosen
    if story_components['title'] != story_title:
        print("LLM designated title as: ", story_components['title'], " but I specified title as: ", story_title)
        print("PLEASE RESOLVE")
        raise ValueError
   
    #end modified times -- needed for product creation
    for component in story_components["story_components"]:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    return story_components["story_components"]


# ## distill ganular components 

# keep high and lows 
# consolidate

#visual weight
#zoom out
#events that explain the net movement;  descriptions to match the shape of the curve.


# visual weight --> 3 stage of processing 

import json
from langchain_core.prompts import PromptTemplate
from llm import load_config, get_llm, extract_json

def clean_distilled_scores(components, tolerance=1, strict=False):
    """
    Forces mathematical flatness if the LLM labeled the arc as 'Flat'.
    
    Args:
        components: List of story components
        tolerance: Maximum acceptable score deviation for Flat arcs (default: 1)
        strict: If True, raises error for large deviations. If False, logs warning (default: False)
    """
    for i in range(1, len(components)):
        prev_score = components[i-1]['end_emotional_score']
        curr_score = components[i]['end_emotional_score']
        arc_label = components[i]['arc']

        if "Flat" in arc_label and curr_score != prev_score:
            score_diff = abs(curr_score - prev_score)
            
            if score_diff <= tolerance:
                # Small deviation - auto-correct
                print(f"⚠️ Adjusting Component {i}: Arc is '{arc_label}' with minor deviation "
                      f"({prev_score} → {curr_score}), snapping to {prev_score}")
                components[i]['end_emotional_score'] = prev_score
            else:
                # Large deviation
                error_msg = (
                    f"Component {i}: Arc labeled as '{arc_label}' but score changed by "
                    f"{score_diff} points ({prev_score} → {curr_score}). "
                    f"Flat arcs should have changes ≤{tolerance}."
                )
                
                if strict:
                    raise ValueError(f"❌ ERROR: {error_msg}")
                else:
                    print(f"⚠️ WARNING: {error_msg} Auto-correcting anyway.")
                    components[i]['end_emotional_score'] = prev_score
            
    return components

def ensure_finale_visibility(components, min_finale_duration=10, min_score_change=3):
    """
    Simple rule: If the last component is very short but has a meaningful
    emotional shift, expand it by compressing earlier components.
    
    Args:
        components: List of story components
        min_finale_duration: Minimum percentage duration for finale (default: 10)
        min_score_change: Minimum score change to consider "meaningful" (default: 3)
    """
    if len(components) < 3:
        print("⚠️ NEED TO CHECK STORY COMPONENTS LESS THAN 3")


    # Check last component
    last_duration = components[-1]['end_time'] - components[-2]['end_time']
    last_score_change = abs(components[-1]['end_emotional_score'] - 
                            components[-2]['end_emotional_score'])
    
    if last_duration < min_finale_duration and last_score_change >= min_score_change:
        needed = min_finale_duration - last_duration

        print("⚠️ Changing Duration of Final Component to Ensure Visibility")
        
        # Compress all earlier components proportionally
        # Everything from 0 to components[-2]['end_time'] needs to fit in 0 to (100 - min_finale_duration)
        total_earlier_time = components[-2]['end_time']
        available_earlier_time = 100 - min_finale_duration
        compression_ratio = available_earlier_time / total_earlier_time
        
        for i in range(1, len(components) - 1):
            original_end = components[i]['end_time']
            components[i]['end_time'] = int(original_end * compression_ratio)
        
        # Finale now starts at the compressed endpoint and ends at 100
        components[-2]['end_time'] = available_earlier_time
        components[-1]['end_time'] = 100
    
    return components


#review / grade accuracy of story components
#VERSION 1
# 2.1) Simplify and Distill Components i.e. **The "Zoom Out" Rule**
#    - You MUST reduce the story to **between 3 and 6 components total**.
#    - **Identify Major Inflection Points:** Only create a new component when the narrative's emotional direction **significantly reverses** (e.g. a sustained rise hits a peak and turns into a fall).
#    - **Filter out Noise:** If the protagonist fluctuates slightly (e.g., -5 to -8 to -6 to -9), this is NOT a zig-zag. It is ONE single "Decrease" trend. Ignore the minor blips.
#    - **The "Stasis" Rule:** If the narrative feels static or stuck, and the score changes only negligibly (e.g. +/- 1 point), you MUST adjust the end_emotional_score to match the previous component's score exactly to create a flat line.
#    - **Merge Aggressively:** Create a broad "Trend Line" that connects the Start, the Major Turning Points (Peaks/Valleys), and the End.
#    - **Preserve the Start:** Keep the first component (end_time 0) exactly as is.
#    - **Preserve the End:** The final component (end_time 100) MUST have the exact same end_emotional_score as the input data.

#VERSION 2
    # 2.1) Simplify and Distill Components i.e. **The "Zoom Out" Rule**
    #    - You MUST reduce the story to **between 3 and 6 components total**.
    #    - **Define Components by Direction (Slope):** A single component represents a continuous trend in one direction (Up, Down, or Flat).
    #      * If the score goes -2 -> -5 -> -9, that is ONE "Decrease" component. Merge them.
    #      * If the score goes -9 -> -2, that is a NEW "Increase" component.
    #    - **Preserve the Vertices (Peaks & Valleys):** When merging components, you must preserve the *magnitude* of the emotional extreme.
    #      * Example: If inputs are Score -5 (Start) -> Score -7 (Middle) -> Score -9 (Low Point), the merged component MUST end at -9. Do not average them.
    #    - **Filter out Noise:** Ignore minor fluctuations that do not alter the macro-trend.
    #      * Example: -5 -> -8 -> -6 -> -9 is a "Decrease" trend. The brief jump to -6 is noise. The trend is from -5 down to -9.
    #    - **The "Stasis" Rule:** If the emotional score varies by only +/- 1 point over a long duration (e.g. -5 to -6 to -5), treat this as "Linear Flat" and flatten the score to the baseline.
    #    - **Preserve the Start:** Keep the first component (end_time 0) exactly as is.
    #    - **Preserve the End:** The final component (end_time 100) MUST have the exact same end_emotional_score as the input data.


def distill_story_components(config_path, story_summary, granular_components, story_title, author, protagonist, llm_provider="anthropic", llm_model="claude-3-5-sonnet-20241022"):
    """
    Phase 2: Aggressively distills granular data into a macro-shape.
    """
    
    prompt_template = """
    You are a world-class literary scholar and expert in story analysis. 
    
    Below is a detailed analysis of "{story_title}" by {author} that's focused specifically on the emotional journey of {protagonist} from the story. 
    
    Your task is:
    1. carefully review the provided story summary and detailed analysis, THEN
    2. simplify and distill the analysis, THEN
    3. output the distilled analysis 
 
    The simplified and distilled output will be used to help visualize the essence of {protagonist}'s emotional journey. The current detailed analysis is too noisy.

    Please carefully follow the instructions below. 

    # 1.) REVIEW SUMMARY AND DETAILED ANALYSIS

    ## 1.1) Review the following summary of "{story_title}" by {author}.
    This summary is your SOURCE OF TRUTH for all plot events and details:
    {story_summary}

    ## 1.2) Carefully review the provided detailed analysis of {protagonist} using the framework provided.

    ### ANALYSIS FRAMEWORK
    The detailed analysis follows the following framework:
    1. Story Timeline: The narrative is viewed on a scale from 0 to 100, representing the percentage of progress through the story.
    2. Story Components: The story is segmented into components defined by {protagonist}'s emotional journey.
    3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
    4. Emotional Arcs: {protagonist}'s emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10), based on their direct experiences and reactions to events.

    ### DETAILED ANALYSIS (INPUT DATA):
    {granular_components}

    # 2.) SIMPLIFY AND DISTILL ANALYSIS 

    ## 2.1) Simplify and Distill Components i.e. **The "Zoom Out" Rule**
        - You MUST reduce the story to between 3 and 5 components total. (Target 3 or 4 for most stories).
        - Define Components by Structural Trend: Do not simply track every change in direction. Look for the dominant trajectory.
        - The "False Reversal" Rule: If the emotional score reverses direction briefly but then returns to its previous trajectory, IGNORE the reversal.
            - Example (False Summit): If the score goes -5 (Start) -> -2 (Brief Hope) -> -9 (New Low), this is NOT three components (Down, Up, Down). This is ONE "Decrease" component from -5 to -9. The rise to -2 was a "False Summit" and should be smoothed out.
            - Example (False Bottom): If the score goes +5 (Start) -> +2 (Brief Scare) -> +8 (New High), this is ONE "Increase" component from +5 to +8.
        - Preserve the Global Vertices: You must preserve the Absolute Lowest Point (Nadir) and Absolute Highest Point (Climax) of the narrative.
        - Ensure the distilled shape hits these exact extremes at the correct time.
        - The "Stasis" Rule: Use "Linear Flat" ONLY when the emotional score changes by ±1 point or less from start to end of the component. You may use "Linear Flat" for periods where the protagonist oscillates through ups and downs (e.g., -5 → -3 → -7 → -5) but returns to within ±1 point of the starting score. CRITICAL: If the component's ending score differs from the starting score by ±2 or more points, you MUST use an appropriate Increase/Decrease arc type, NOT Linear Flat—even if the character felt "stuck" or "trapped" during this period. Major events that cause sustained emotional shifts must be reflected in the arc type.        
        - Preserve the Start: Keep the first component (end_time 0) exactly as is.
        - Preserve the End: The final component (end_time 100) MUST have the exact same end_emotional_score as the input data.

    ## 2.2) Distilled Component **Arc Selection:**
       For each distilled component, choose the emotional arc pattern that best fits the rate of change for distilled component. Here are the following choices:
       a. Step-by-Step Increase/Decrease: Emotions change in distinct, noticeable stages
       b. Linear Increase/Decrease: Consistent, steady change in emotional state
       c. Gradual-to-Rapid Increase/Decrease: Change starts slowly, then accelerates
       d. Rapid-to-Gradual Increase/Decrease: Change starts quickly, then slows down
       e. Straight Increase/Decrease: Sudden, dramatic change in emotions
       f. S-Curve Increase/Decrease: Change follows an 'S' shape (slow-fast-slow)
       g. Linear Flat: No change in emotions

    ## 2.3) Distilled Component **Description Synthesis:**
       For each distilled component, write a new description.
       - **Focus on Events:** The description must be a chronological sequence of concrete actions and plot beats focused on {protagonist}'s experience and perspective. Do not use abstract emotional summaries; instead, state exactly what happens using specific details (e.g. specific proper names, settings, and physical actions).
       - **Source Material:** Construct the description strictly from the events in the story summary and the underlying components. When merging components, cross-reference the story summary to ensure factual accuracy.       
       - **Alignment:** Select events that justify the specific emotional arc of this distilled component i.e. the new description should reflect the emotional trajectory (change or stasis) of the distilled component
         * If the arc is "Increase," focus on the positive events/wins.
         * If the arc is "Decrease," focus on the negative events/losses.
         * EXCEPTION: If the arc is "Linear Flat" (Stasis), you must include the full sequence of events (both good and bad) to show the lack of net progress.
       - **Naming & Clarity:** **Use {protagonist}'s name explicitly.** Do not rely on pronouns (e.g. "He" or "She") to start the description. Ensure the protagonist is clearly identified as the subject of the actions.
    
    ## 2.4) **Cross-Reference with Story Summary:**
        Before finalizing each distilled component description:
        - Verify that all events mentioned actually occur in the story summary
        - Confirm the chronological sequence is accurate
        - Check that character names and specific details match the source material
        - If you've merged multiple components, ensure the combined description doesn't 
            contradict or omit crucial story beats from the summary
    
    ## 2.5)  Double Check according to the following **TECHNICAL & VALIDATION RULES (CRITICAL):**
       - **Anchor Check:** Ensure the Start Score (Time 0) and End Score (Time 100) match the input data exactly.
       - Ensure that end_emotional_scores are consistent with the arc types (e.g., an "Increase" arc should have a higher end_emotional_score than the previous component).
       - Emotional scores must be whole numbers between -10 and +10. 
       - If the emotional score remains the same (e.g., -5 to -5), the Arc Type MUST be "Linear Flat". You strictly cannot label an arc as "Increase" or "Decrease" if the score number does not change.
       - Adjacent components should not have the same emotional score unless using Linear Flat arc.
       - End times must be in ascending order and the final component must end at 100.
       - Each arc type must match the emotional change described:
        * Increase arcs must show higher end scores than start scores
        * Decrease arcs must show lower end scores than start scores
        * Flat arcs must maintain the same score
       - Double-check your analysis for accuracy and internal consistency before providing the final JSON output.

    # 3.) OUTPUT DISTILLED ANALYSIS
    Please output your distilled analysis in the following format (JSON ONLY):
    
    {{
        "title": "{story_title}",
        "protagonist": "{protagonist}",
        "story_components": [
            {{
                "end_time": 0,
                "description": "N/A",
                "end_emotional_score": <int matches input>,
                "arc": "N/A"
            }},
            {{
                "end_time": <int>, 
                "description": "<Narrative description of the dominant trend>",
                "end_emotional_score": <int>,
                "arc": "<Selected Arc Pattern>"
            }}
            ...
        ]
    }}

    # EXAMPLE:
    Below is a simple illustrative example of how to peform the task.
    
    <example>
    <author_name>Charles Perrault</author_name>
    <story_title>Cinderella at the Ball</story_title>
    <protagonist>Cinderella</protagonist>
    
    <story_summary_(input_data)>
    Heartbroken and exhausted, Cinderella toils endlessly in her own home after her father’s death leaves her at the mercy of her cruel stepmother and spiteful stepsisters. Forced to cook, clean, and tend to every chore while enduring their constant insults, Cinderella clings to a quiet hope for a kinder future, though she often feels lonely and powerless. One day, an announcement arrives that the royal family is hosting a grand ball to find a bride for the Prince. Eager for a chance at happiness, Cinderella timidly asks if she may attend. Her stepmother and stepsisters mock her wish and forbid it, leaving her devastated. Even so, Cinderella manages to gather scraps of optimism, trying to sew a suitable dress from her late mother’s belongings—only for her stepsisters to shred it in a fit of jealousy moments before the ball. Crushed by this cruel betrayal, she flees to the garden, overwhelmed by despair. It is there that her Fairy Godmother appears, transforming Cinderella’s tattered clothes into a resplendent gown and conjuring a gleaming carriage from a humble pumpkin. As Cinderella’s hopes rise, the Fairy Godmother warns her that the magic will end at midnight. At the grand royal ball, the Prince is immediately enchanted by her gentle grace and luminous presence. For the first time, Cinderella basks in admiration instead of scorn, feeling her spirits soar with each dance and conversation. However, as the clock strikes midnight, she is forced to flee the palace. In her panic to escape before the spell breaks, she loses one of her delicate glass slippers on the palace steps. Despite her sudden disappearance, the Prince is determined to find this mysterious young woman, traveling throughout the kingdom with the slipper in hand. When his search brings him to Cinderella’s home, her stepsisters deride the idea that she could be the one who captured the Prince’s heart. Yet, as soon as Cinderella tries on the slipper, it fits perfectly. Freed at last from servitude, she marries the Prince, and her enduring kindness and patience are joyously rewarded.
    </story_summary_(input_data)>

    <detailed_analysis_(input_data)>
    {{
        "title": "Cinderella at the Ball",
        "protagonist": "Cinderella",
        "story_components": [
            {{
                "end_time": 0,
                "description": "#N/A",
                "end_emotional_score": -5,
                "arc": "#N/A"
            }},
            {{
                "end_time": 15,
                "description": "Cinderella timidly asks to attend the ball, feeling a spark of hope that she might be allowed a night of happiness.",
                "end_emotional_score": -3,
                "arc": "Linear Increase"
            }},
            {{
                "end_time": 25,
                "description": "Her stepmother mocks the request. Then, her stepsisters discover her homemade dress and rip it to shreds. Devastated, she runs to the garden.",
                "end_emotional_score": -9,
                "arc": "Straight Decrease"
            }},
            {{
                "end_time": 35,
                "description": "The Fairy Godmother appears. Cinderella's despair turns to rising wonder as the pumpkin is transformed into a carriage.",
                "end_emotional_score": 4,
                "arc": "Step-by-Step Increase"
            }},
            {{
                "end_time": 60,
                "description": "Cinderella enters the ball and dances with the Prince. She feels seen and adored, forgetting her life of servitude.",
                "end_emotional_score": 9,
                "arc": "Gradual-to-Rapid Increase"
            }},
            {{
                "end_time": 70,
                "description": "Midnight strikes. Cinderella panics and flees, losing her slipper on the stairs.",
                "end_emotional_score": -2,
                "arc": "Straight Decrease"
            }},
            {{
                "end_time": 90,
                "description": "Back in rags, she resumes chores. She watches helplessly as the Prince searches the kingdom and her stepsisters try on the slipper.",
                "end_emotional_score": -4,
                "arc": "Linear Decrease"
            }},
            {{
                "end_time": 100,
                "description": "The slipper fits. Cinderella reveals herself, marries the Prince, and leaves her abusive home forever.",
                "end_emotional_score": 10,
                "arc": "Straight Increase"
            }}
        ]
    }}
    </detailed_analysis_(input_data)>

    <ideal_output>
    {{
        "title": "Cinderella at the Ball",
        "protagonist": "Cinderella",
        "story_components": [
            {{
                "end_time": 0,
                "description": "N/A",
                "end_emotional_score": -5,
                "arc": "N/A"
            }},
            {{
                "end_time": 25,
                "description": "Cinderella asks to attend the ball but is mocked and forbidden by her stepmother. She attempts to sew a dress from her mother's old things, but her stepsisters discover her, rip the dress to shreds, and leave her sobbing in the garden.",
                "end_emotional_score": -9,
                "arc": "Rapid-to-Gradual Decrease"
            }},
            {{
                "end_time": 60,
                "description": "The Fairy Godmother transforms a pumpkin into a carriage and rags into a gown. Cinderella enters the ball, dances with the Prince, and is admired by the entire court, forgetting her life of servitude.",
                "end_emotional_score": 9,
                "arc": "Step-by-Step Increase"
            }},
            {{
                "end_time": 90,
                "description": "The clock strikes midnight, forcing Cinderella to flee and lose a glass slipper. Back in her rags, she resumes chores while the Prince searches the kingdom; she watches helplessly as her stepsisters try to force their feet into the slipper.",
                "end_emotional_score": -4,
                "arc": "Rapid-to-Gradual Decrease"
            }},
            {{
                "end_time": 100,
                "description": "The Prince allows Cinderella to try the slipper, and it fits perfectly. She reveals her identity, leaves her stepfamily behind, and marries the Prince.",
                "end_emotional_score": 10,
                "arc": "Straight Increase"
            }}
        ]
    }}
    </ideal_output>

    <distillation_notes>
    The following notes explain the key decisions made in creating the distilled output above. 
    Use these principles when analyzing your assigned story:

    **Score Preservation:**
    Notice that the distilled output preserves the EXACT peak (+9) and nadir (-9) from 
    the detailed analysis. When you see:
    - Detailed: -5 → -3 → -9 (nadir) → 4 → 9 (peak) → -2 → -4 → 10
    - Distilled: -5 → -9 (nadir) → 9 (peak) → -4 → 10

    The distillation "smooths through" the brief rise to -3 and the dip to -2/-4, but 
    it MUST hit the absolute extremes (-9 and +9 in the detailed data become -9 and +9 
    in the distilled data). Never average or skip the peaks and valleys.

    **False Reversal Identification:**
    In the detailed analysis, Cinderella briefly felt hope when asking to attend (score 
    improved -5 → -3), but this was immediately crushed (-3 → -9). This is a "False 
    Summit" because:
    1. The hope was fleeting and immediately reversed
    2. The dominant trend is DOWNWARD: -5 → -9
    3. The distilled output correctly merges this into ONE Decrease component

    Counter-example: If Cinderella had sustained the hope for 20% of the story before 
    the dress incident, that WOULD be a separate component.

    **Description Synthesis:**
    The distilled component at end_time 90 merges THREE detailed components (time 60→70, 
    70→90, 90→100 from detailed data). Notice how the description:

    ✅ DOES:
    - Use specific plot beats: "clock strikes midnight," "lose a glass slipper," "stepsisters 
    try to force their feet"
    - Maintain chronological order
    - Focus on events that justify the DECREASE (-2 → -4): the fleeing, the return to rags, 
    the helpless watching

    ❌ DOES NOT:
    - Include emotional adjectives like "sadly" or "desperately" (show, don't tell)
    - Omit the brief panic at midnight (time 60→70) just because it had a different arc 
    type in the detailed data
    - Use vague language like "things get worse"

    All events are traceable to the story summary.
    </distillation_notes>
    </example>
    """

    prompt = PromptTemplate(
        input_variables=["story_summary","granular_components", "story_title", "protagonist", "author"],
        template=prompt_template
    )

    

    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=16384)

    # Calculate count to shame the LLM into compressing
    granular_json_str = json.dumps(granular_components, indent=2)

    #test to see what prompt actually looks like
    # try:
    #     final_rendered_prompt = prompt.format(
    #         granular_components=granular_json_str,
    #         story_title=story_title,
    #         protagonist=protagonist,
    #         author=author
    #     )
    #     print("\n" + "="*40)
    #     print("DEBUG: ACTUAL PROMPT SENT TO LLM")
    #     print("="*40)
    #     print(final_rendered_prompt)
    #     print("="*40 + "\n")
    # except Exception as e:
    #     print(f"❌ Error formatting prompt: {e}")
    #     # This usually happens if you have a syntax error in the template 

    runnable = prompt | llm

    try:
        output = runnable.invoke({
            "story_summary": story_summary,
            "granular_components": granular_json_str,
            "story_title": story_title,
            "protagonist": protagonist,
            "author": author
        })
    except Exception as e:
        print(f"Error during Distillation LLM call: {e}")
        raise e

    # if hasattr(output, "content"):
    #     output_text = output.content
    # else:
    #     output_text = output

    #attempt to extact json (if needed)
    if hasattr(output, "content"):
        # Check if content is a list (Google/LangChain edge case)
        if isinstance(output.content, list):
            # Extract text from all blocks
            text_parts = []
            for block in output.content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            output_text = "".join(text_parts)
        else:
            # Standard string content
            output_text = str(output.content)
    else:
        output_text = str(output)

    output_text = extract_json(output_text)
    
    try:
        result = json.loads(output_text)
    except json.JSONDecodeError as e:
        # Added 'e' here so you can see the actual error if it happens again
        print(f"Error decoding JSON from distillation step: {e}")
        print(f"Raw Text causing error: {output_text[:200]}...") 
        return "ERROR!" 
    
    
    # Final Safety Check: If it didn't compress, print a warning
    if len(result["story_components"]) > 8:
        print(f"⚠️ WARNING: Distillation failed to compress significantly (Count: {len(result['story_components'])})")

    return result





def get_distilled_story_components(config_path, story_components_detailed, story_summary, story_title, story_author, story_protagonist, 
                      llm_provider="anthropic", llm_model="claude-3-5-sonnet-20241022"):

   
    #print(story_summary_source)
    story_components = distill_story_components(
        config_path=config_path,
        story_summary=story_summary,
        granular_components=story_components_detailed,
        story_title=story_title,
        author=story_author,
        protagonist=story_protagonist,
        llm_provider = llm_provider, #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    )

    # 4. Process the list of components
    final_components = story_components["story_components"]

    #POST PROCESSING 
    #handle issues with "Flat" Arc Types:
    final_components = clean_distilled_scores(final_components, tolerance=1, strict=False)

    #ensure big changes at the end are visibale
    final_components = ensure_finale_visibility(final_components, min_finale_duration=10)


    #check if story_component are valid
    story_components_for_validation = {
        'title': story_title,
        'story_components': final_components
    }
    story_components_validity = validate_story_arcs(story_components_for_validation)

    #check if right protagonist was chosen
    if story_components.get('protagonist') != story_protagonist:
         print(f"⚠️ WARNING: LLM returned protagonist {story_components.get('protagonist')} vs expected {story_protagonist}")

    # 5. Add modified times -- needed for product creation
    for component in final_components:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    # 6. Return complete structure with title and protagonist
    return final_components





def grade_story_components(config_path: str, story_components: dict, canonical_summary: str, title:str, author: str, protagonist: str, llm_provider: str, llm_model: str) -> dict:
  """
  Grades the accuracy of a story's emotional shape using a two-phase analysis.

  Phase 1 (Bottom-Up): Verifies that each emotional transition is factually justified.
  Phase 2 (Top-Down): Assesses the holistic accuracy of the entire emotional arc,
  checking for correct proportions, pacing, and identification of key turning points.

  Args:
      config_path (str): Path to the LLM configuration file.
      generated_analysis (dict): The generated story JSON.
      canonical_summary (str): An objective, external summary of the story.
      llm_provider (str): The LLM provider to use.
      llm_model (str): The specific LLM model to use (e.g., 'gpt-4-turbo').

  Returns:
      dict: A detailed dictionary with both component-level and holistic assessments.
  """
  
  # --- 1. Prepare Inputs for the Prompt ---
  simplified_components = []
  # Start with the initial state as the first component for the prompt
  initial_component = story_components[0]
  simplified_components.append({
      "end_time": initial_component.get("end_time"),
      "description": "Initial State",
      "end_emotional_score": initial_component.get("end_emotional_score")
  })
  for component in story_components:
      if component.get("end_time") > 0:
          simplified_components.append({
              "end_time": component.get("end_time"),
              "description": component.get("description"),
              "end_emotional_score": component.get("end_emotional_score")
          })
          
  analysis_to_grade = {
      "title": title,
      "protagonist": protagonist,
      "story_components_with_scores": simplified_components
  }
  generated_analysis_str = json.dumps(analysis_to_grade, indent=4)

  # --- 2. Define the Two-Phase Prompt ---
  prompt_template = """
You are an expert literary scholar specializing in narrative theory and the quantitative analysis of story structures. You are trained to evaluate character arcs with academic rigor, objectivity, and precision. 

Your task is to perform a rigorous two-phase quality assessment of a story's emotional shape.


---
## INPUT DATA

### 1. Generated Story Analysis
This JSON contains the proposed emotional scores for {protagonist} from {author}'s {title} and the text descriptions for each story segment. 
Emotional scores range from euphoric (+10) to depressed (-10), based on {protagonist}'s direct experiences and reactions to events in each story segment.
{generated_analysis}

### 2. Canonical Story Summary (External Ground Truth)
This text is the source of truth for the story's events.
"{canonical_summary}"

---
## FRAMEWORK FOR JUDGMENT (Your Analytical Rubric)

You must apply the following principles when assessing the emotional scores:
1.  **Anchoring:** Scores must be anchored to the protagonist's emotional stakes. +10 represents ultimate triumph/euphoria; -10 represents ultimate despair/tragedy (e.g., death, total failure).
2.  **Proportionality:** The *magnitude* of a score change must be proportional to the *magnitude* of the causal event. A minor setback should not cause a 10-point drop.
3.  **Narrative Weight:** The story's most pivotal moment (the climax or point of no return) should be clearly identifiable in the trajectory, often marked by the largest emotional shift.

---
## ASSESSMENT & INSTRUCTIONS

### Phase 1: Bottom-Up Component Validation
For each emotional transition, determine if the event in the `description` factually justifies the change in `end_emotional_score` according to the `Canonical Story Summary`.

### Phase 2: Top-Down Holistic Review
After completing Phase 1, evaluate the entire emotional journey using the `FRAMEWORK FOR JUDGMENT`.
-   Is the shape **proportional** and well-paced?
-   Are the scores correctly **anchored** to the story's stakes?
-   Does the shape give appropriate **narrative weight** to the climax?

### Final Grade
Your `final_grade` must be the more critical of the two assessments. A story can have factually correct components but a holistically incorrect shape.

---
## OUTPUT

Provide your complete two-phase assessment in the following JSON format ONLY. Output a single JSON object. Do not use Markdown fences or any prose.

```json
{{
"shape_accuracy": {{
  "component_assessments": [
    {{
      "end_time": 40, 
      "emotional_transition": "1 -> 8",
      "is_justified": true,
      "reasoning": "The reunion with Daisy after years of obsession justifies a significant rise to euphoria."
    }},
    {{
      "end_time": 55,
      "emotional_transition": "8 -> 4",
      "is_justified": true,
      "reasoning": "Daisy's negative reaction to the party correctly tempers Gatsby's euphoria, justifying a moderate fall."
    }}
  ],
  "holistic_assessment": {{
      "holistic_grade": "A|B|C|D|F",
      "holistic_justification": "The overall shape brilliantly captures the Icarus-like rise fueled by hope and the subsequent, catastrophic collapse into tragedy. The proportions feel correct, with the final fall being the most significant move."
  }},
  "final_grade": "A|B|C|D|F",
  "final_justification": "The final grade is A because both the individual components are logically sound and the overall shape accurately reflects the tragic spirit and proportions of the novel."
}}
}}
"""

  prompt = PromptTemplate(
      input_variables=["generated_analysis", "canonical_summary", "title", "author", "protagonist"],
      template=prompt_template
  )
  config = load_config(config_path=config_path)
  llm = get_llm(llm_provider, llm_model, config, max_tokens=4000) # Increased tokens for the more detailed analysis
  runnable = prompt | llm
  output = runnable.invoke({
        "generated_analysis": generated_analysis_str,
        "canonical_summary": canonical_summary,
        "title": title,
        "author": author,
        "protagonist": protagonist
    })

  if hasattr(output, "content"):
      output_text = output.content
  else:
      output_text = output

  ## --- FIXES ARE IN THIS FINAL SECTION --- ##

  extracted_text = extract_json(output_text)
    
  try:
      # The `extracted_text` is a string; we load it into our dictionary.
      grades_dict = json.loads(extracted_text)
  except (json.JSONDecodeError, TypeError) as e:
      print(f"Error parsing JSON from LLM output: {e}")
      print(f"Raw extracted text was: {extracted_text}")
      # Return a dictionary with an error state to prevent crashes downstream
      return {"error": "Failed to parse LLM response as JSON."}
    

  #MAYBE ADD SOME CHECKS IF STORY COMPONENTS ACCURATE OR NOT

  # 3. UPDATED to return the dictionary `grades_dict`.
  return grades_dict


#TESTING!
# #
# story_components_detailed = [
#     {
#       "end_time": 0,
#       "description": "#N/A",
#       "end_emotional_score": -5,
#       "arc": "#N/A",
#       "modified_end_time": 0,
#       "modified_end_emotional_score": -5
#     },
#     {
#       "end_time": 8,
#       "description": "Holden, already expelled and having bungled the fencing team's equipment, skips the big game and trudges to Mr. Spencer's. The lecture—\"life is a game\"—lands as condescension. He fidgets, resents the pity, and bolts with relief, the encounter confirming his sense that adults are phony and that he's failing out of everything.",
#       "end_emotional_score": -6,
#       "arc": "Linear Decrease",
#       "modified_end_time": 8,
#       "modified_end_emotional_score": -6
#     },
#     {
#       "end_time": 15,
#       "description": "Back in the dorm, his red hunting cap gives him a fragile, private comfort, but Ackley's grating presence needles him. Stradlater's casual date with Jane Gallagher stirs anxious protectiveness and jealousy. Holden pours himself into writing about Allie's baseball glove—tender, mournful memories—leaving him raw and exposed.",
#       "end_emotional_score": -7,
#       "arc": "Gradual-to-Rapid Decrease",
#       "modified_end_time": 15,
#       "modified_end_emotional_score": -7
#     },
#     {
#       "end_time": 20,
#       "description": "Stradlater sneers at the composition; when he hints he might have fooled around with Jane, Holden explodes. The fight is brief and humiliating—he's pinned and bloodied. The dorm feels unendurable, and he impulsively decides to leave Pencey that night, hollow and angry.",
#       "end_emotional_score": -9,
#       "arc": "Straight Decrease",
#       "modified_end_time": 20,
#       "modified_end_emotional_score": -9
#     },
#     {
#       "end_time": 28,
#       "description": "On the train to New York, he reinvents himself as \"Rudolf Schmidt,\" flattering Mrs. Morrow about her son. The lies give him a perverse, fleeting buoyancy. In the hotel, voyeuristic glimpses across the courtyard are titillating and sad. Rebuffed by Faith Cavendish, he's left alone with the city's neon and his own ache.",
#       "end_emotional_score": -8,
#       "arc": "Rapid-to-Gradual Increase",
#       "modified_end_time": 28,
#       "modified_end_emotional_score": -8
#     },
#     {
#       "end_time": 40,
#       "description": "At the Lavender Room he dances well and briefly enjoys Bernice's company, but is abandoned with the tab. At Ernie's, the crowd's pretension and Lillian Simmons's phoniness drive him out. Maurice sells him a prostitute; faced with Sunny, he panics, pays to talk instead, and is then shaken down. Maurice punches him; Holden fantasizes melodramatic revenge and even suicide before dawn.",
#       "end_emotional_score": -10,
#       "arc": "Gradual-to-Rapid Decrease",
#       "modified_end_time": 40,
#       "modified_end_emotional_score": -10
#     },
#     {
#       "end_time": 52,
#       "description": "After a fitful sleep, small human connections rekindle him: an earnest chat with two nuns about Romeo and Juliet, pressing donations on them; hunting for \"Little Shirley Beans\" for Phoebe; and a little boy's off-key \"If a body catch a body…,\" which oddly soothes him. These kindnesses and signs of innocence lift the heaviness.",
#       "end_emotional_score": -6,
#       "arc": "Step-by-Step Increase",
#       "modified_end_time": 52,
#       "modified_end_emotional_score": -6
#     },
#     {
#       "end_time": 60,
#       "description": "He meets Sally Hayes, is dazzled, then repelled by her polish and social climbing. After the Lunts' play and a phony reunion with a boy from Andover, he spirals. At Radio City's rink and over lunch, he rants that he's fed up with everything and blurts a fantasy of running away to a New England cabin. Sally's refusal triggers his cruel \"royal pain in the ass,\" and he storms off.",
#       "end_emotional_score": -8,
#       "arc": "Rapid-to-Gradual Decrease",
#       "modified_end_time": 60,
#       "modified_end_emotional_score": -8
#     },
#     {
#       "end_time": 66,
#       "description": "He numbs himself with the Christmas show's spectacle and a dreary movie, then meets Carl Luce at the Wicker Bar. Holden's fixation on sex annoys Luce—\"typical Caulfield conversation\"—who briskly advises a psychiatrist and leaves. Holden gets very drunk and flails at forming any genuine contact.",
#       "end_emotional_score": -9,
#       "arc": "Linear Decrease",
#       "modified_end_time": 66,
#       "modified_end_emotional_score": -9
#     },
#     {
#       "end_time": 74,
#       "description": "In Central Park, the ducks' disappearance becomes an emblem of his own fear of vanishing. He breaks Phoebe's record, is seized by diarrhea, and staggers through crosswalks convinced he will die each time. Exhausted and near-delirious, he decides to go home to see Phoebe.",
#       "end_emotional_score": -10,
#       "arc": "Gradual-to-Rapid Decrease",
#       "modified_end_time": 74,
#       "modified_end_emotional_score": -10
#     },
#     {
#       "end_time": 82,
#       "description": "Sneaking into his parents' apartment, he wakes Phoebe. She is stricken that he's flunked again and demands to know what he likes. He fumbles—Allie, the nuns, a dead boy at Elkton Hills—then articulates his one true wish: to be \"the catcher in the rye,\" saving children from tumbling over a cliff. This confession, and Phoebe's presence, give him a rare sense of purpose and love.",
#       "end_emotional_score": -5,
#       "arc": "Gradual-to-Rapid Increase",
#       "modified_end_time": 82,
#       "modified_end_emotional_score": -5
#     },
#     {
#       "end_time": 88,
#       "description": "At Mr. Antolini's, he finds a concerned adult who speaks seriously of a \"fall\" ahead and quotes Stekel about living humbly rather than dying nobly. The sober talk feels like guidance, not a lecture. Holden, bone-tired, falls asleep with a faint sense of being looked after.",
#       "end_emotional_score": -4,
#       "arc": "Linear Increase",
#       "modified_end_time": 88,
#       "modified_end_emotional_score": -4
#     },
#     {
#       "end_time": 90,
#       "description": "He wakes to Mr. Antolini patting his head in the dark. Startled and mistrustful, he interprets it as a sexual advance, panics, and flees into the night, clutching at his bags and the last shreds of trust.",
#       "end_emotional_score": -8,
#       "arc": "Straight Decrease",
#       "modified_end_time": 90,
#       "modified_end_emotional_score": -8
#     },
#     {
#       "end_time": 92,
#       "description": "He dozes at Grand Central and wakes to Monday with mounting dread. Convinced he should run west and live as a deaf-mute to avoid phoniness, he drifts deeper into isolation while drafting a goodbye to Phoebe.",
#       "end_emotional_score": -9,
#       "arc": "Linear Decrease",
#       "modified_end_time": 92,
#       "modified_end_emotional_score": -9
#     },
#     {
#       "end_time": 96,
#       "description": "He meets Phoebe at the museum to say goodbye. She insists on coming with him; he refuses, she goes silent and furious. Confronted with her hurt, he abandons the runaway fantasy and agrees to stay—choosing connection over flight.",
#       "end_emotional_score": -7,
#       "arc": "Linear Increase",
#       "modified_end_time": 96,
#       "modified_end_emotional_score": -7
#     },
#     {
#       "end_time": 98,
#       "description": "At the zoo's carousel, he buys Phoebe a ticket and watches in the rain as she rides, reaching for the gold ring. He lets her try, accepting risk. Something breaks open; he cries and says he is happy, soaking in a simple, undiluted joy he's chased all along.",
#       "end_emotional_score": 2,
#       "arc": "Gradual-to-Rapid Increase",
#       "modified_end_time": 98,
#       "modified_end_emotional_score": 2
#     },
#     {
#       "end_time": 100,
#       "description": "A year later in the California sanitarium, he won't say how he got sick. He's supposed to go back to school, unsure if anything will change. Telling the story makes him miss people—Stradlater, Ackley, even Maurice—softening his edges, but uncertainty and melancholy remain.",
#       "end_emotional_score": -1,
#       "arc": "Linear Decrease",
#       "modified_end_time": 100,
#       "modified_end_emotional_score": -1
#     }
#   ]

# catcher_in_the_rye_summary = """
# "Holden Caulfield, seventeen years old, was narrating from a mental hospital or sanitarium in southern California about events that took place over a two-day period the previous December. He was a student at Pencey Prep School in Pennsylvania. On a Saturday afternoon in December, Holden missed the traditional football game between Pencey Prep and Saxon Hall. As manager of the fencing team, he had lost the team's equipment on the subway that morning, resulting in the cancellation of a match in New York. Holden had been expelled from Pencey for failing four out of his five classes and was not to return after Christmas break, which began the following Wednesday. He went to the home of his history teacher, Mr. Spencer, to say good-bye. Mr. Spencer advised him that life is a game and one should play it according to the rules, but Holden dismissed much of what Spencer said. After gladly escaping from the long-winded old man, Holden returned to his dormitory, which was almost deserted. Wearing his new red hunting cap, he began to read.\n\nHolden's reverie was interrupted when a dorm neighbor named Robert Ackley, an obnoxious student with a terrible complexion, disturbed him. Later, Holden's roommate, Ward Stradlater, returned. Stradlater was conceited, arrogant, and a \"secret slob.\" He asked Holden to write an English composition for him while he prepared for a date with Jane Gallagher. Holden went with Ackley and Mal Brossard to see a movie in New York City. When Holden returned, he wrote the composition for Stradlater about his brother Allie's left-handed baseball glove, which had poems written all over it in green ink. When Stradlater returned from his date, he became upset at Holden for writing what he considered a poor essay. Holden responded by tearing up the composition. Holden asked about the date with Jane, and when Stradlater indicated that he might have had sex with her, Holden became enraged and tried to punch Stradlater. Stradlater quickly overpowered him, knocked him out, and won the fight easily. Holden could not bear to remain in the dormitory and decided on a whim to leave Pencey that night instead of waiting until Wednesday.\n\nHolden caught a train to New York City, where he planned to stay in a hotel until Wednesday, when his parents expected him to return home for Christmas vacation. On the train, he sat next to the mother of a Pencey student, Ernest Morrow. Claiming that his name was Rudolf Schmidt, Holden lied to Mrs. Morrow, telling her what a popular and well-respected boy her son was at Pencey, when in fact Ernest was loathed by the other boys. Holden invited her to have a drink with him at the club car. When Holden reached New York, he did not know whom he should call. He considered inviting his younger sister Phoebe, as well as Jane Gallagher and another friend, Sally Hayes. He finally decided to stay at the Edmond Hotel. Holden checked into the hotel, and his room faced windows of another wing of the hotel. From his window he observed assorted behavior by guests, including a transvestite and a couple who spit drinks back at each other. He decided to call Faith Cavendish, a former burlesque stripper and reputed prostitute, but she rejected his advances.\n\nHolden went down to the Lavender Room, a nightclub in the hotel, where he met three women in their thirties who were tourists from Seattle. He danced with one of them, Bernice Krebs, a blonde woman, and enjoyed dancing with her, but he ended up with only the check. After leaving the Lavender Room, Holden decided to go to Ernie's, a nightclub in Greenwich Village that his brother D.B. had often frequented before moving to Hollywood. Holden left almost immediately after he arrived because he saw Lillian Simmons, one of D.B.'s former girlfriends, and wished to avoid her because she was a \"phony.\" He walked back to the hotel, where Maurice, the elevator man, offered him a prostitute for the night. Holden accepted. When Sunny, the prostitute, arrived, Holden became too nervous, made up an excuse about having just had an operation, and refused to go on with it. He paid the girl five dollars to leave. Sunny demanded ten dollars, but Holden believed he only owed five based on the earlier deal. Sunny and Maurice soon returned and demanded the extra five dollars. Holden argued with them, but Maurice threatened him while Sunny stole the money from his wallet. Maurice punched him in the stomach before leaving. Holden then imagined shooting Maurice in the stomach and even jumping out of the window to commit suicide. It was near dawn Sunday morning.\n\nAfter a short sleep, Holden telephoned Sally Hayes and agreed to meet her that afternoon to go to a play. He left the hotel, checked his luggage at Grand Central Station so that he would not have to go back to the hotel where he might face Maurice again, and had a late breakfast. At Grand Central Station, he met two nuns, one an English teacher, with whom he discussed Romeo and Juliet. He insisted on giving them a donation. Holden looked for a special record for his ten-year-old sister Phoebe called \"Little Shirley Beans.\" He spotted a small boy singing \"If a body catch a body coming through the rye,\" which made Holden feel less depressed. He met Sally for their matinee date. Although he immediately wanted to marry her, he did not particularly like her because she was snobbish and \"phony.\" They went to see a play starring the married Broadway stars Alfred Lunt and Lynn Fontanne. After the show, Sally kept mentioning that she saw a boy from Andover whom she knew, and Holden told her to go over and give the boy \"a big soul kiss.\" While she talked to the boy, Holden became disgusted at how phony the conversation was.\n\nSally and Holden went ice skating at Radio City and then had lunch together. During lunch, Holden complained that he was fed up with everything around him and suddenly suggested that they run away together to New England, where they could live in a cabin in the woods. When Sally dismissed the idea, Holden called her a \"royal pain in the ass,\" causing her to cry. Holden left. After the date, he saw the Christmas show at Radio City Music Hall and endured a movie. He called Carl Luce, a friend from the Whooton School who went to Columbia, and arranged to meet him at the Wicker Bar. At the bar, Holden had a conversation that was preoccupied with sex, and Carl soon became annoyed, calling it a \"typical Caulfield conversation.\" Carl suggested that Holden see a psychiatrist and left early. Holden remained at the Wicker Bar, where he got very drunk. After trying to make a date with the coat-check girl, he left the bar.\n\nThroughout his time in New York, Holden had been worried about the ducks in the lagoon at Central Park. He went to Central Park to look for them but only managed to break Phoebe's record in the process. He became increasingly distraught and delusional, believing that he would die every time he crossed the street. He fell unconscious after suffering from diarrhea. Exhausted physically and mentally and thinking he might die of pneumonia, he headed home to see his sister. He sneaked into his parents' apartment, attempting to avoid his parents, and awakened Phoebe. She soon became distressed when she heard that Holden had failed out of Pencey. She said that their father would kill him. He told her that he might go out to a ranch in Colorado, but she dismissed his idea as foolish. When he complained about the phoniness of Pencey, Phoebe asked him if he actually liked anything. He claimed that he liked Allie, and he thought about how he liked the nuns at Grand Central and a boy at Elkton Hills who had committed suicide. He told Phoebe that the one thing he would like to be was \"the catcher in the rye.\" He explained that he would stand near the edge of a cliff by a field of rye and catch any of the playing children who, in their abandon, came close to falling off. Phoebe informed him that the song he had heard about the catcher in the rye was actually a poem by Robert Burns, and it was about bodies meeting bodies, not catching bodies.\n\nWhen his parents returned from a late night out, Holden left the apartment undetected and visited the home of Mr. Antolini, a favorite teacher and his former English teacher at Elkton Hills, where he hoped to stay a few days. Mr. Antolini told Holden that he was headed for a serious fall and that he was the type who might die nobly for a highly unworthy cause. He quoted Wilhelm Stekel: \"The mark of an immature man is that he wants to die nobly for a cause, while the mark of the mature man is that he wants to live humbly for one.\" Holden fell asleep on the couch. In the predawn hours, Holden awoke startled to find Mr. Antolini patting Holden's head. Holden immediately interpreted this as a homosexual advance and quickly left. He told Mr. Antolini that he had to get his bags from Grand Central Station but would return soon.\n\nHolden spent the night at Grand Central Station. It was Monday morning. He became increasingly distraught and depressed. He decided to run away and head west where he hoped to live as a deaf-mute. He sent a note to Phoebe at school, telling her to meet him for lunch at the museum. He arranged to meet Phoebe to say good-bye. When he met Phoebe, she told him that she wanted to go with him and became angry when he refused. She pulled a \"Fine, I'm not talking to you anymore.\" Holden finally agreed to stay and not run away. He bought Phoebe a ticket for the carousel at the nearby zoo. As he watched her ride the carousel, going around and around, he began to cry. He declared he was happy.\n\nHolden's story ended with Phoebe riding the carousel in the rain as Holden watched. In the final chapter, Holden was at the sanitarium in California, in psychiatric care one year later. He did not want to tell any more about what happened next or how he got sick. He said he was supposed to go back to school in September, but he was not sure whether or not things would be any different this time around. He concluded that relating the whole story had only made him miss people, even the jerks like Stradlater and Ackley and even Maurice.",
# """


# from paths import PATHS
# story_component_distill_llm_model = "gemini-3-pro-preview" #"gpt-5-2025-08-07"
# story_components = get_distilled_story_components(
#     config_path=PATHS['config'],
#     story_summary=catcher_in_the_rye_summary,
#     story_components_detailed=story_components_detailed,
#     story_title="The Catcher in the Rye",
#     story_author="J.D. Salinger",
#     story_protagonist="Holden Caulfield",
#     llm_provider = "google", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
#     llm_model = story_component_distill_llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
# )
# print("DISTILLED STORY COMPONENTS")
# print(story_components)