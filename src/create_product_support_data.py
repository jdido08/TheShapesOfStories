# this file holds function for creating supporting product attributes like:
# mockups
# descriptions
# supporting files 
# Note this was originally in create_product_data.py but it makes more sense to seperate

from product_description import create_product_description
from paths import PATHS
from product_mockups import create_mockups
from create_product_data import create_print_11x14_product_data

import json 
import time 

def create_product_support_data(product_data_path):

    with open(product_data_path, "r", encoding="utf-8") as f:
        product_data = json.load(f)

    story_data_path = product_data['story_data_path']
    title = product_data['title']
    protagonist = product_data['protagonist']
    author = product_data['author']
    year = product_data['year']
    product_type = product_data['product_type']
    product_design_path = product_data['product_design_path']
    background_color_hex = product_data['background_color_hex']
    font_color_hex = product_data['font_color_hex']
    font = product_data['font_style']

    if product_type == "print":
        print_size = product_data['product_size']


    llm_provider_product_description = "google"
    llm_model_product_description = "gemini-2.5-pro"
    create_product_description(
        image_path=product_design_path,
        story_json_or_path=product_data_path,
        config_path=PATHS['config'],
        llm_provider = llm_provider_product_description,
        llm_model = llm_model_product_description
    )
    print("✅ Product Description")


    #CREATE MOCKUPS
    create_mockups(
        product_data_path=product_data_path,
        product_design_path=product_design_path,
        mockup_list=["11x14_poster","11x14_table", "11x14_wall", "3x_11x14_wall"],
        output_dir=PATHS['product_mockups'] 
    )
    print("✅ Product Mockups")

    # CREATE SUPPORTING DESIGNS 
    supporting_designs = [
         {
            "line_type":"char",
            "output_format":"png"
        },
        {
            "line_type":"line",
            "output_format":"png"
        },
        {
            "line_type":"line",
            "output_format":"svg"
        },
        {
            "line_type":"char",
            "output_format":"svg"
        }
    ]
    supporting_design_file_paths = []

    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    if product_type == "print":
        if print_size == "11x14":
            for supporting_design in supporting_designs:
                product_data_path, product_design_path = create_print_11x14_product_data(
                    story_data_path=story_data_path,
                    title=title,
                    protagonist=protagonist,
                    author=author,
                    year=year,
                    background_color_hex=background_color_hex,
                    font_color_hex=font_color_hex,
                    font=font,
                    line_type = supporting_design['line_type'],
                    output_format=supporting_design['output_format'],
                    output_dir=PATHS['supporting_designs']
                )
                supporting_design_file_paths.append(product_design_path)
                print("✅ ", supporting_design['line_type'], " - ", supporting_design['output_format'])
        else:
            print("ERROR: Only 11x14 print supported today")
            return
    else:
        print("ERROR: Only print supported today")
        return


    product_data['all_design_file_paths'] = supporting_design_file_paths
    product_data['llm_models']['product_description'] = llm_model_product_description

    with open(product_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(product_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(2)

    return product_data_path