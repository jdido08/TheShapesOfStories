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
import inflect
from paths import PATHS


def build_sources_block(all_summary_sources, story_summary_data) -> str:
    """
    all_summary_sources: iterable of source names in the order you want preserved
    story_summary_data: dict like {src: {"summary": "..."}}
    """
    parts = []
    for name in all_summary_sources:
        text = story_summary_data.get(name, {}).get("summary", "")
        if not text:
            continue
        text = text.strip()
        # If text includes XML-ish chars, wrap in CDATA for safety
        if any(ch in text for ch in "<&"):
            parts.append(f'<source name="{name}"><![CDATA[\n{text}\n]]></source>')
        else:
            parts.append(f'<source name="{name}">\n{text}\n</source>')
    if not parts:
        return "<sources>\n  <!-- no sources provided -->\n</sources>"
    return "<sources>\n" + "\n\n".join(parts) + "\n</sources>"



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

     # List is in priority order -- this is all possible summary sources will need to update in future 
    all_summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    sources_block = build_sources_block(all_summary_sources, story_summary_data)

    #create a dictionary that has all the summaries in order 
    # story_summaries_dict = {}
    # for summary_source in all_summary_sources:
    #     if summary_source in story_summary_data:
    #         story_summaries_dict[summary_source] = story_summary_data[summary_source]['summary']

    # story_summaries_string = ""
    # for key, value in story_summaries_dict.items():
    #     story_summaries_string += f"Summary from {key}:\n{value}\n\n"
    
    # p = inflect.engine()
    # num_of_summaries = len(story_summaries_dict)
    # num_of_summaries_words = p.number_to_words(num_of_summaries)

    # print(num_of_summaries_words)

    SYSTEM_PROMPT = """You are a meticulous literary editor. 
    Your job is to synthesize multiple authoritative plot summaries into one canonical, comprehensive, chronologically ordered narrative focused on the protagonist’s concrete actions and experiences. 
    You never invent details not present in the sources. You write clearly, precisely, and neutrally; no analysis, no interpretation, no themes—just the story as it happens.
    """


    prompt_template = """
    <task> Synthesize the provided sources into ONE comprehensive summary for downstream story-shape analysis. Write in third person, neutral register, and simple past tense. Include the ending (spoilers are allowed). Do not summarize or analyze—recount the sequence of events as they occur to the protagonist. No length limit: include every salient event that meaningfully affects the protagonist.</task>
    
    <context>
        <title>{title}</title>
        <author>{author}</author>
        <protagonist>{protagonist}</protagonist>
        <focus>Center every paragraph on events that directly affect {protagonist}’s actions, choices, emotions, and consequences.</focus>
        <style>
            - Chronological order from beginning → middle → end.
            - Use concrete nouns and verbs; avoid abstractions and summaries of themes.
            - Prefer specificity: name places, people, and objects when known.
            - Maintain consistent canonical names for characters and places.
            - Use paragraph breaks for major phases or location changes.
            - Keep tone factual and precise, not interpretive.
        </style>
    </context>

    <sources>
        <source name="sparknotes">{sparknotes_summary}</source>
        <source name="cliffnotes">{cliffnotes_summary}</source>
        <source name="wikipedia">{wikipedia_summary}</source>
        {other_tagged_sources}
    </sources>

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
            - Use the provided <protagonist>{protagonist}</protagonist> as the canonical name.
            - Before writing, internally map all aliases and spellings found in sources back to this canonical form.
            - Apply the same one-form-only rule to recurring characters and key places; choose a single form and use it consistently.
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
        - Every sentence describes something that happens to or is done by {protagonist}.
        - Ending included.
        - No facts appear that are unsupported by at least one source.
        - No meta-text or analysis.
    </quality_checks>

    <output>
    Return ONLY the final synthesized summary as plain paragraphs.
    Do not include labels, XML tags, commentary, or preambles—just the story itself.
    </output>
    """

    prompt = PromptTemplate(
        input_variables=["num_of_summaries_words", "author", "title", "protagonist", "story_summaries_string"],  # Define the expected inputs
        template=prompt_template
    )


    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=10000)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    # # Then invoke with the required inputs:
    output = runnable.invoke({
        "num_of_summaries_words": num_of_summaries_words,
        "author": story_author,
        "title": story_title,
        "protagonist": story_protagonist,
        "story_summaries_string": story_summaries_string
    })

    print(output)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    



    with open("test_summary_dict.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
    print("✅ Story Summary Saved")



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

story_title = "Les Miserables"
story_author = "Victor Hugo"
story_protagonist = "Jean Valjean"
story_summary_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/les_miserables_composite_data.json"
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