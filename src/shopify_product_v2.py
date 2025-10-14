# STEPS:
# 1.) Create SHOPIFY product
#   - inputs: story, product_type
#.  - logic: 
#       - based on product type --> fetch options/vairants e.g. prints --> color, line, size 
#       - create product shell with variants
#       - set basic product metafields 
#   - shopify product 
#
# 2.) Add Product Vairant to SHOPIFY product 
#
# product metafields:
# STORY 
#   - story_title,
#.  - story_protagonist
#.  - story_slug --> {story_title}-{story_protagonist}
#.  - story_year
#.  - story_type | Literature, Film, Sports, Biographies, etc.. 
#   - shape_symbolic_representation
#.  - shape_archetype

## SOME STORY META FIELDS ARE SPECIFIC TO STORY_TYPE
# LITERATURE 
#.  - story_themes
#.  - story_genres
#.  - story_settings
#.  - story_associated_countries
#.  - story_series_or_universe
#.  - story_awards
#.  - story_primary_isbns
#.  - story_manual_colletion ---> something I can manuall edit 

# PRODUCT 
#   - product_type | print, tshirt, canvas, mugs, etc..
#.  - product_description

# PRODUCT VAIRANT ATTRIBUTES ARE SPECIFIC TO PRODUCT TYPE
# PRINT 
#.  - product_slug --> {story_title}-{story_protagonist}-{product_type}-{print_size}-{background_color}-{font_color}-{line_style}
#           -- when line_style = storybeats then {story_title}-{story_protagonist}-{product_type}-{print_size}-{background_color}-{font_color}-{line_style}-{font_style}
#.  - product_variant_color --> need to make this {background_color}/{font_color} --> need to think about
#.  - product_variant_size  e.g. 11x14
#.  - product_variant_line e.g. storybeats, classic 
#.  - product_variant_typography 
# ALL
#   - product_variarnt_mockups
#.  - product_variant_print_description 

#.  - product_variant_manual_collection --> manually set this to put a specific variant in collect (is this possible?)