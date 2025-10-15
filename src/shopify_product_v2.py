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
# #
# 1. create a shopify product
# 2. fill out metadata for shopify product
# 3. create product variants of the shopify product
# 4. fill out metadata for the product varaint
# 5. link the product variant to the shopify product
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


#product metafields 
"""
## CORE FIELDS ###
title --> product name
handle --> urls
descriptionHtml --> 
productType --> (category)
vendor         --> "The Shapes of Stories"
tags           -->
status
options         
images


### PRODUCT METAFIELDS ####

story.title
story.protagonist
story.slug --> {story.title}-{story.protagonist}
story.year (optional)
story.type --> Literature, Film, Sports, Biographies, etc.. 
story.ref

shape.symbolic_representation
shape.archetype

literature.author
literature.protagonist
literature.year
literature.genres
literature.themes
literature.settings
literature.countries
literature.series_or_universe 
literature.awards
literature.primary_isbns

product.type | print, tshirt, canvas, mugs, etc..
product.slug --> {story_title}-{story_protagonist}-{product_type}
product.description_html
product.manual_collection


## VARIANT CORE FIELDS ###
id
sku
barcode
price
compareAtPrice
inventoryItem
selectedOptions
title
requiresShipping


### VARIANTS METAFIELDS ### 

variant.slug --> different per product type 
variant.description_html
variant.mockups 
variant.manual_collection

print.size  --> 11x14
print.height_in
print.width_in
print.color --> {background_color}/font_color (do I need font color or is background enough?)
print.style --> storybeats, classic 
print.line_style
print.background_color
print.background_color_hex
print.background_color_family
print.background_color_shade
print.font_color
print.font_color_hex
print.font_color_family
print.font_color_shade
print.font

printify.blueprint_id
printify.provider_id
printify.variant_id
printify.sku


"""

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