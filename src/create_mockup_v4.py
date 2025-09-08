from PIL import Image

def create_mockup(mockup_path, design_path, output_path, coordinates):
    """
    Inserts a design into a mockup template, preserving realism.

    Args:
        mockup_path (str): File path to the mockup template image.
        design_path (str): File path to the design image to insert.
        output_path (str): File path to save the final composite image.
        coordinates (tuple): A tuple containing the (x1, y1, x2, y2) coordinates
                             of the target area in the mockup.
    """
    # 1. Load the mockup and design images
    mockup = Image.open(mockup_path).convert("RGBA")
    design = Image.open(design_path).convert("RGBA")

    # 2. Define the target area from the coordinates
    x1, y1, x2, y2 = coordinates
    target_width = x2 - x1
    target_height = y2 - y1
    
    # 3. Extract the reflection/glare layer from the original mockup for realism
    # This captures the subtle lighting on the glass.
    reflection_layer = mockup.crop(coordinates)

    # 4. Resize the design to fit the target area exactly
    design_resized = design.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 5. Paste the resized design onto the mockup
    mockup.paste(design_resized, (x1, y1), design_resized)
    
    # 6. Blend the original reflection layer back on top to add realism
    # We use the reflection layer itself as the mask for transparency.
    # This adds the glass effect back over your design.
    mockup.paste(reflection_layer, (x1, y1), reflection_layer)

    # 7. Save the final image
    # Convert back to RGB if saving as JPEG
    final_image = mockup.convert("RGB")
    final_image.save(output_path, quality=95)
    print(f"Mockup saved successfully to: {output_path}")


# --- HOW TO USE THE SCRIPT ---

if __name__ == "__main__":
    mockup_template_file = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_table.jpeg" # Your frame mockup image
    design_to_insert_file = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png" # Your Moby Dick design image
    final_output_file = "final_moby_dick_mockup.jpg" # The name for the final file

    # The coordinates we found in Step 2 for the inner frame
    # Format: (top_left_x, top_left_y, bottom_right_x, bottom_right_y)
    frame_coords = (145, 400, 484, 858)

    # Call the function to create the mockup
    create_mockup(
        mockup_path=mockup_template_file,
        design_path=design_to_insert_file,
        output_path=final_output_file,
        coordinates=frame_coords
    )

    # --- To process another design, just change the file paths and run again! ---
    # create_mockup(
    #     mockup_path=mockup_template_file,
    #     design_path="another_design.png",
    #     output_path="final_another_design_mockup.jpg",
    #     coordinates=frame_coords
    # )