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
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
import inflect
import textwrap
from paths import PATHS

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm import extract_json


 # List is in priority order -- this is all possible summary sources will need to update in future 
SUMMARY_SOURCES = [
    'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
    'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
]


def build_sources_block(story_summary_data) -> str:
    """
    all_summary_sources: iterable of source names in the order you want preserved
    story_summary_data: dict like {src: {"summary": "..."}}
    """

    for key, value in story_summary_data.items():
        #print(key)
        if key not in SUMMARY_SOURCES and key != "title" and key != "openlib" and key!= "gutenberg":
            print("❌ ERROR: Unexpected Summary Source: ", key , " in ", story_summary_data.get("title", ""))
            raise ValueError("Need to Investigate ", key, " summary")
            return None 
            
    parts = []
    sources_used = []
    for name in SUMMARY_SOURCES:
        text = story_summary_data.get(name, {}).get("summary", "")
        if not text:
            continue
        text = text.strip()
        # If text includes XML-ish chars, wrap in CDATA for safety
        if any(ch in text for ch in "<&"):
            parts.append(f'<source name="{name}"><![CDATA[\n{text}\n]]></source>')
            sources_used.append(name)
        else:
            parts.append(f'<source name="{name}">\n{text}\n</source>')
            sources_used.append(name)
    if not parts:
        raise ValueError("No usable sources found; aborting to prevent hallucination.")
        #return "<sources>\n  <!-- no sources provided -->\n</sources>"
    sources_block = "<sources>\n" + "\n\n".join(parts) + "\n</sources>"

    if len(sources_used) < 2:
        print("⚠️ WARNING: Only ", len(sources_used), " sources used. Need more!")

    return sources_block, sources_used



#CAN BE SOMETHING SIMPLE LIKE:
# Below are 3 authoritative summaries of Victor Hugo's Les Miserables. 
# Please carefully read each then create a comprehensive summary of the story using details from all three sources that's focused on the story's protagonist Jean Valjean.

# def get_story_summary(story_title, author, protagonist, story_summary_path, config_path, llm_provider, llm_model):
def get_story_summary(story_title, story_author, story_protagonist, story_summary_path, config_path, llm_provider, llm_model):

    """
    Inputs are a file path that contains story summary(s) and returns story summary
    """

    with open(story_summary_path, 'r', encoding='utf-8') as file:
        story_summary_data = json.load(file)

    
    sources_block, sources_used = build_sources_block(story_summary_data)
    #print("soource block created!")

    #testing
    # sources_block = ""
    # story_title = ""
    # story_author= "" 
    # story_protagonist = ""
    #print(sources_block)

    SYSTEM_PROMPT = textwrap.dedent("""\
    You are a meticulous literary editor. 
    Your job is to synthesize multiple authoritative plot summaries into one canonical, comprehensive, chronologically ordered narrative focused on the protagonist’s concrete actions and experiences. 
    You ALWAYS ground your synthesis in the provided sources and NEVER invent details. You write clearly, precisely, and neutrally; no analysis, no interpretation, no themes—just the story as it happens.
    """).strip()


    USER_PROMPT = textwrap.dedent("""\
    <task>
    Synthesize the provided sources into ONE comprehensive, canonical summary focused on the story’s protagonist.
    Write in third person, neutral register, and simple past tense. Be strictly chronological and include the ending.
    Use only facts from the provided sources. No length limit: include every salient event that meaningfully affects the protagonist.
    </task>
    
    <context>
        <title>{title}</title>
        <author>{author}</author>
        <protagonist>{protagonist}</protagonist>
        <focus>Center every paragraph on events that directly affect {protagonist}’s actions, choices, emotions, and consequences.</focus>
        <style>
            - Chronological order from beginning → middle → end.
            - Use concrete nouns and verbs; avoid abstractions and summaries of themes.
            - Prefer specificity: use proper names for people, places, organizations, and objects whenever given in the sources.
            - Maintain consistent canonical names for characters and places.
            - Use paragraph breaks for major phases or location changes.
            - Keep tone factual and precise, not interpretive.
        </style>
    </context>
                                  
    <structure>
        You must split the synthesis into two labeled sections:
        1) <backstory> … </backstory> — ONLY events that occur before the on-page narrative begins (childhood, prior relationships, past wars, world/lore setup, flashbacks, expository context). Do not include any on-page present-timeline events.
        2) <main_story> … </main_story> — The on-page narrative from the opening scene through the ending. Be strictly chronological and include the ending.
        Keep both sections concise but complete. If there is no meaningful backstory, output "" for backstory.
    </structure>

    {sources_block}

    <rules>
        <grounding>
            - You may include only immediate, source-supported motivations that directly cause an action; exclude themes, symbolism, and moral interpretation.
            - If a motivation is not explicitly stated in the sources, do not infer or speculate about it; describe only observable actions and consequences.
            - Use only facts explicitly present in the provided sources.
            - Prefer consensus: include details supported by two or more sources.
            - Include single-source details only when other sources are silent (no contradiction).
            - If sources conflict:
                a) Choose the version that is more specific and concrete (e.g., explicit actions,
                locations, or causal links).
                b) If specificity is similar, choose the version that maintains strict chronological
                coherence with surrounding events.
                c) If ambiguity remains, omit the contested micro-detail and use minimally
                committed phrasing that stays true to both versions (e.g., “soon after,” “a
                brief conflict,” “a local official”).
        </grounding>


        <normalization>
            - Use the provided <protagonist>{protagonist}</protagonist> as the canonical name for the protagonist.
            - For every recurring person, place, organization, or named object, select ONE canonical spelling by majority usage across sources and use it consistently.
        </normalization>

        <coverage>
            - Include: the inciting situation, all major turning points, key reversals, midpoints,
            crises, climax, and ending.
            - Each major event must describe what {protagonist} does, perceives, decides, or
            experiences in consequence.
            - Include all concrete, specific details that appear in the sources — such as named places,
            objects, and supporting characters — whenever they directly affect the plot or the
            protagonist’s actions.
            - Use proper names (for places, people, organizations, and items) whenever available,
            rather than general descriptors.
            - Mention supporting characters only when their actions directly influence {protagonist}.
        </coverage>


        <prohibitions>
            - No literary analysis, symbolism, themes, or moral interpretation.
        </prohibitions>
    </rules>

    <quality_checks> <!-- perform silently; do NOT include in output -->
        - Events progress strictly from beginning → end with no backtracking.
        - All proper nouns are consistent with the canonical map.
        - Content is centered on {protagonist}; sentences primarily describe actions, events, or consequences for {protagonist}, with occasional brief context (time/place/other actors) only when needed for coherence.
        - Ending included.
        - No facts appear that are unsupported by at least one source.
        - No meta-text or analysis.
    </quality_checks>

    <output>
        Return a JSON object with EXACTLY these two string fields and nothing else (no code fences, no preamble, no trailing commentary):

        {{
        "backstory": "Only events that precede the on-page narrative. If none, use an empty string.",
        "main_story": "The on-page narrative from the opening scene through the ending, strictly chronological."
        }}
    </output>
    """).strip()


    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    #print(chat_prompt)

    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=10000)

    runnable = chat_prompt | llm  # everything else stays the same

    output = runnable.invoke({
        "title": story_title,
        "author": story_author,
        "protagonist": story_protagonist,
        "sources_block": sources_block
    })


    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
    
    output_text = extract_json(output_text)
    output_text = json.loads(output_text)

    #print(output_text)
    
    if output_text == "" or output_text == None or output_text == {}:
        print("❌ ERROR: LLM Build Story Summary")
        raise ValueError("ERROR: LLM Build Story Summary")

    
    #save in 
    summary_file_name = f'{story_title.lower().replace(" ", "-")}-{story_protagonist.lower().replace(" ", "-")}_summary.json'
    summary_file_path = PATHS['story_summaries'] + "/" + summary_file_name

    summary_data = {
        "title": story_title,
        "author": story_author,
        "protagonist": story_protagonist,
        "backstory": output_text['backstory'],
        "main_story": output_text['main_story'],
        "summary_sources": sources_used,
        "summary_sources_file_path": story_summary_path
    }

    with open(summary_file_path, 'w') as f:
        json.dump(summary_data, f, indent=4)
    
    #wait a few seconds 
    time.sleep(3)
    print("✅ Story Summary Saved")
    

    return output_text


story_title = "The Great Gatsby"
story_author = "F. Scott Fitzgerald"
story_protagonist = "Jay Gatsby"
#story_summary_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/summaries/les_miserables_composite_data.json"
story_summary_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_great_gatsby_composite_data.json"
config_path=PATHS['config']
llm_provider = "google" #"google", #"openai",#, #"openai",, #"anthropic", #google", 
llm_model = "gemini-2.5-pro" #"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2

get_story_summary(
    story_title = story_title,
    story_author = story_author,
    story_protagonist = story_protagonist,
    story_summary_path = story_summary_path,
    config_path=config_path,
    llm_provider = llm_provider,
    llm_model = llm_model
)