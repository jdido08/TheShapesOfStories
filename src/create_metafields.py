# # Fields I know
# - Printify Product ID
# - Shape Archetype
# - Shape Symbols
# - Font Family
# - Medium
# - Line Type
# - Author
# - Character / Protagonist
# - Story Title

# # Fields I can derive
# - Font Color Name
# - Background Color Name
# - Font Color (Hex)
# - Background Color (Hex)
# - Color (Background/Front Color Combo) ---> NEED TO ADD 
# - Story Slug

# # Field I need LLM 
# - Setting Region
# - Setting Country
# - Language
# - Awards
# - Setting Era
# - Setting Time
# - Setting City
# - Subgenre
# - Publication Year (I might have this )
# - Publication Country
# - Genre
# - Series
# - Universe


#Maybe
# openlib
#   - publishing
#       - first_publish_year
#   - physical_dimensions
#        - number_of_pages_median
#   - subjects_and_characters
#       - subjects
#       - subject_places
#       - subject_times
#   - excerpts
#   - covers
#   - ratings_and_reviews
#   - first_sentence


from pathlib import Path
import json
from extract_story_metadata import StoryInput, extract_story_metadata_all

CONFIG, PROVIDER, MODEL = "config.yaml", "openai", "gpt-5"
path = Path("/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/moby-dick_ishmael.json")

doc = json.loads(path.read_text(encoding="utf-8"))
story = StoryInput(
    title=doc["title"],
    author=doc["author"],
    publication_year=int(doc["year"]),
    summary=doc["summary"]
)



res = extract_story_metadata_all(CONFIG, story, PROVIDER, MODEL)

doc["story_metadata"] = res["metadata"]
doc["story_metadata_evidence"] = res["evidence"]
doc["story_metadata_confidence"] = res["confidence"]

path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
