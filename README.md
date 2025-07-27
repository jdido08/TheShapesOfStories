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
2. ASSESS
    - accuracy score
    - classification 
3. PUBLISH
    - printinfy
4. POLISH 
    - mockups 
    - product description