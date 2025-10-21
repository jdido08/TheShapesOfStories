# The Shapes of Stories

This project creates beautiful and insightful "story shape" visualizations that trace the emotional journey of a story's protagonist. Inspired by Kurt Vonnegut's theory on the shapes of stories, this tool transforms narrative arcs into unique pieces of art.

The core idea is to plot a story's emotional highs and lows along a "Good & Ill Fortune" (y-axis) against the story's timeline from "Beginning" to "End" (x-axis). Unlike Vonnegut's theory, which groups stories into a few archetypal shapes, this project celebrates the unique fingerprint of every story, creating a visual representation of its specific narrative journey.

## Features

* **Automated Story Analysis**: Leverages Large Language Models (LLMs) to analyze a story summary, breaking it down into key emotional components and scoring the protagonist's fortune over time.
* **Dynamic Shape Generation**: Procedurally generates the story's shape based on the emotional analysis, creating smooth and complex curves that capture the protagonist's narrative journey.
* **Contextual Text Descriptors**: The curve of the story shape is constructed from text snippets that describe the protagonist's experiences at each point in the narrative.
* **Customizable Aesthetics**: Offers deep customization for fonts, colors, and dimensions to capture the unique spirit of each story.
* **Versatile Output**:
    * Creates artwork for single stories in various sizes and formats (`.png`, `.svg`).
    * Designs complex multi-story posters with sophisticated grid layouts.
    * Supports different product types, from prints to wrapped canvases.
* **Extensible Framework**: Can be adapted to visualize the shape of any story type, including literature, films, biographies, and more.

## How It Works

The system follows a proprietary, multi-step process to generate a story shape:

1.  **Story Analysis**: The system takes a story title, protagonist name, and a comprehensive summary as input. It uses an LLM to analyze the protagonist's emotional journey, breaking the narrative into 4-8 key components. Each component is assigned an emotional score (from -10 for ill-fortune to +10 for good-fortune) and a corresponding emotional arc (e.g., "Linear Increase", "S-Curve Decrease").
2.  **Shape & Text Construction**: Based on the analysis, the system:
    * Generates a continuous, curved path representing the emotional scores over the story's timeline.
    * Uses an LLM to generate concise, descriptive text phrases for each story component. These phrases are carefully crafted to fit the exact length of their corresponding curve segment.
3.  **Rendering**: The final artwork is rendered using the Cairo graphics library. The system meticulously places the generated text along the curve, adjusting spacing and orientation to ensure readability. It then adds the title, protagonist's name, and applies the specified colors and fonts to produce the final image file.





# 7/26/2025:
- about page 
- story double check --> is it accurate, is the shape correct, what is the shape 
- story mocks 
- story descriptions 

ORDER:
1. CREATE
    - 
2. ASSESS
    - shape accuracy score -- need to do
    - word/summary accuracy score -- need to do 
    - shape classification -- need to do 
3. PUBLISH
    - printinfy -- basics set up 
4. POLISH 
    - mockups 
    - product description
    - product tags 

MISC:
- printify branding inserts 

8/4/2025 To Dos:
- about page
- make mockups more realistic 
- assess functions 

8/5/2025:
- about page -- finished for now; still some clean up to do 
- branding insert -- will do later 

8/7/2025: Assesments
- Shape Accuracy 
- Word Accuracy 
- Story Category 


8/8/2025:
- Grade Shape
- Grade Text
- Categorize Shape

Operations:
--> Create Story Data -- done
--> Grade Shape -- done 
--> CHECK IF SHAPE PASSES
--> Categorize Shape -- done; general 
--> Create Story Graph for standard x by y size -- done 
--> Grade Text -- DONE 
--> CHECK IF TEXT PASSES
--> Regrade Categorize Shape --> make sure it hasn't changed; size_specific
--> CHECK IF SHAPE HASN'T CHANGED
--> Create Solid Line Version and SVG version 




Product Creation / Listing 

--> Create Product Description --> mostly using symbolic and arhectype 
--> Create Product Tags 
--> Create Product Mockups 
--> Publish to Printify 
--> Edit on Shopify 
--> Final Grader 
--> Branding Insert 
--> stiching it all together

____

Marketing 





8/11/2025:
- Grade Shape --> finished
- Grade Text
- Categorize Shape

NEED TO INCORPORATE INTO CREATE FILE 

8/13/2025:
- Grade Shale --> Done
- Categorize Shape --> WIP
- Grade Text - TO DO
- Tie it all together - TO DO


other stuff:
- mockups 
- tags 
- descriptions 


8/25/2025:
- create product and product variant metafields via Shopify API
- create metafields for a story using LLM + story data
- create metafields for a story variant LLM + story data 
- in the future create metaobjects for stories, authors, groups, etc.. 



8/24/2025 Operations:
1. Create Story Data --> specify:
    - type: literature, film, biographies, sports, etc...
    - title 
    - subtitle 
    - protganist 
    etc..
2. Assess Story 
3. Categorize Story  
4. Create Story Description 
5. Craate Tags for story 

Product Data Model
1. Product Name e.g. "The Great Gatsby"
2. Product Description e.g "...
3. Product Tags:
    - story-type: Literature, Film, Biographies, Sports, etc..
    - genre
    - subgenre
    - title
    - author (if applicable)
    - protagonist
    - director (if applicable)
    - team (if applicable)
    - subject (if applicable)
    - shape
    - shape-archetype:
    - series
    - universe
    - publication-year
    - setting-country
    - publication-country
    - publication-time
    - setting-time 
    - setting-city
    - setting-region
    - setting-era
    - background-color-hex 
    - background-color-general
    - typography-font
    - typography-color-hex
    - typography-color-general
    - language
    - awards
4. Product Variants:
    - product: print, canvas, t-shirt, mug, etc...
    - size: 8x10, 11x14, small, medium, large, 8oz, 160z, etc... 
    - line-type: text, solid 
    - Printify SKU
    - metaattributes:
        - 


# Tags:
# Story Type: Literature, Film, Biographies, Sports, Business/Companies et..
# Genre: Classics, Sci-Fi, 
# Author: F. Scott Fitzgerald
# Protagnist: Jay Gatsby
# Title: The Great Gatsby
# Product: Print
# Size: 8x10
# shape-archetype: 
# Shape Archetype: Man in Hole 
# Publication Year
# Universe
# Series 


# 8/26/2025:
1. Create MetaFields for Shopify Product Model
2. Script for Creating Metafields for Product
3. Script for Setting metafields for Shopify 

- Need to think about Variants 



# Set Basic Fields
# Create Story Data
# Validate Shape
# Determine Shape 
# Create Metadata

# Create Versions -- 10x8, 8x10, 11x14, 14x11
# Grade Text 
# Verify Shape hasn't changed 

<!-- # Style: line, text -->
# Size: 8x10, 11x14
# Orientation: Portrait, Landscape 
# Color: Navy/Gold 


### 9/12/2025 To Dos:

# Folders
1. Summaries
2. Story Data
3. Product Data
4. Product Designs
    - TEXT PNG
    - LINE PNG
    - TEXT SVG
    - LINE SVG 


- I have the basic pieces and function and need to string things together now
- I need to create clean interfaces for all of my functions

#High Level Overview:
1. Create Story Base Data
    - base story data
    - grade story shape 
    - categorize story 
    - create default story style --> font + color 
2. Create Story Product Data
    - story product size, style (color, font)
    - text + designs 
    - assess shape 
    - description
    - metafields
    - mockups
    - supporting variants svg, lines, etc.. 
3. Create Story Product Printify
4. Publish Story Product 
5. Edit Story Product

#Steps 1-4 --> Create Story Base --> Basics of the story used to create products
1. Create Base Story Data
    - Inputs: Title, Author, Protagonist, Year, Summary File 
    - Logic: Transforms summary into story data file 
    - Outputs: [title]-[protagonist].json --> where to save this probably in like base story data files
    - Note: (a) replace spaces with "_" in output file name; (b) open question of format
2. Grade Story Data Shape
    - Input: [title]-[protagonist].json, Summary (need to think if just going to reuse summary initially provided)
    - Logic: Double Checks that Generated Story Shape is Accurate; If not a passing grade then need to redo step #1 
    - Ouput: updated [title]-[protagonist].json w/ field
3. Categorize Story Shape
    - Input: [title]-[protagonist].json
    - Logic: analyzes story shape to determine shape representative and any archetypes 
    - Output: updated [title]-[protagonist].json w/ shape fields 
4. Create Base Story Style 
    - Inputs: [title]-[protagonist].json
    - Logic: Get story colors + font 
    - Outputs: [title]-[protagonist].json --> add fields to base story data file 
5. Create Story Metafields
    - Inputs: [title]-[protagonist].json
    - Logic: turns story data to product metafields
    - Output: updated [title]-[protagonist]-[product]-[size]-[style].json

# --- Content Specific -- # 
## Create Story Product --> 
5. Create Story Shape Varaint
    - Inputs: Product + product specific parameters e.g. print-11x14; other input parameters
    - Logic: Transforms Story Data to Art
    - Outputs: --> need to figure out where to save
        - [title]-[protagonist]-[product]-[size]-[style].json --> this as text specific things with it
        - [title]-[protagonist]-[product]-[size]-[style].png 
6. Compare Story Shape 
    - Inputs: [title]-[protagonist]-[product]-[size]-[style].json, [title]-[protagonist].json
    - Logic: recategorizes story shape of new version and compares to original to makes sure basic shape did not shape 
    - Outputs: updated [title]-[protagonist]-[product]-[size]-[style].json with field that verifies accuracy
7. Grade Story Data Text
    - Inputs: [title]-[protagonist]-[product]-[size]-[style].json, (maybe summary?)
    - Logic: Verfies that generates story text is accurate 
    - Output: updated [title]-[protagonist]-[product]-[size]-[style].json
8. Create Product Description 
    - Inputs: 
        - [title]-[protagonist]-[product]-[size]-[style].json
        - [title]-[protagonist]-[product]-[size]-[style].png
    - Logic: turns story data + data into description
    - Output: updated [title]-[protagonist]-[product]-[size]-[style].json
9. Create Mockups:
    - Inputs: Product Type is probably an input
        - [title]-[protagonist]-[product]-[size]-[style].json
        - [title]-[protagonist]-[product]-[size]-[style].png
    - Logic: turns story designs into product mockups
    - Outputs: (for prints)
        - png files for 11x14-wall, 11x14-table, 11x14-poster, 11x14-3-wall
        - updated[title]-[protagonist]-[product]-[size]-[style].json for local links
10. Create SVG
11. Create Line PNG Version
12. Create Line SVG Version
13. Create Links betweeen Story Data <--> Product Data <--> Designs <---> Mockups <---> Extra Designs 

___

14. Create Printify Product 
15. Publish Printify Product to Shopify
16. Edit Shopify Product





# STILL TODOS:
1. finish wiring up story and product create process
2. printify scripts
3. shopify scripts
4. summary process
5. make product design creation faster: https://chatgpt.com/share/68dfc540-a1bc-8011-9408-7357fe64931b 

Mockups


# TODOs 9/19/2025:

- story data creation --> DONE
- product data / design creation --> WIP 
- printify product creation 
- shopify production 

- need to revisit logic for summaries as having these accurate with facts will help product 



#10/9/2025:
--> Create Product Variant in Printify --> Get SKU 
--> Create Product in Shopify w/ Variants 
--> Map Printify Variants to Shopify Variants using SKU


#10/19/2025:
1. Clean up mockup quality --> I actually think it's fine 
2. Clean up content creation pipeline --> 
    --> centrlize llms to use in yaml (so it's easier to change?)
    --> redo summary creation process 
3. Figure out website product page layout 
4. Redo Summary Creation 
5. Identify Stories to Launch With
6. Create Stories
7. Launch 
8. Work on Marketing 