
from create_story_data               import create_story_data
from create_product_data             import create_product_data
from printify_publish_product        import publish_product_on_printify
from shopify_create_product          import create_shopify_product
from shopify_create_product_variant  import create_shopify_product_variant
from shopify_product_variant_mockups import add_shopify_product_variant_mockups



story_data_path = create_story_data(story_type="Literature", 
                  story_title="The Stranger", 
                  story_author="Albert Camus",
                  story_protagonist="Meursault", 
                  story_year="1942", 
                  story_summary_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/summaries/the_stranger_composite_data.json")


product_data_path = create_product_data(story_data_path=story_data_path,
                    product_type="print", 
                    product_details={})


publish_product_on_printify(product_data_path=product_data_path)


create_shopify_product(story_data_path, "print")

create_shopify_product_variant(story_data_path, product_type="print", product_slug="ALL", delete_placeholder_variants=True)


add_shopify_product_variant_mockups(product_data_path)