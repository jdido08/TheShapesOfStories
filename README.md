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