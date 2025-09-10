# MOCKUP STRATEGY:
# 1. shows the [8x10, 11x14] poster by itself no frame 
# 2. shows the [8x10, 11x14] poster framed on a table with no mat i.e. frames are [8x10, 11x14]
# 3. shows the [8x10, 11x14] poster framed on a wall with mat i.e. frames that are [11x14, 16x20]
# 4. shows 3 [8x10, 11x14] posters together on a wall with mat i.e. frames taht are [11x14, 16x20]
# 5. shows two posters one 8x10 and the other 11x14 on wall wit matt i.e. frames taht are [11x14, 16x20]
# Each image should have a small annotation clarifying the print and frame size that's in the photo


# “Print size: 8×10 in (unframed). Fits any 8×10 frame, or use an 11×14 frame with 8×10 mat.”
# “Print size: 11×14 in (unframed). Fits any 11×14 frame, or use a 16×20 frame with 11×14 mat for a gallery look.”
# Annotations in photo should clarify the design print size and also the frame size 

#NEW MOCKUP
# only 11x14 prints --> consider 8x10 later; it's too confusing to offer multiple sizes
# include white border 
# mockups no matt (like obvious state) they're my inspiration 
# mockups poster, table, wall, three prints


from PIL import Image

def find_coeffs(pa, pb):
    """
    Finds the coefficients for a perspective transformation.
    """
    matrix = []
    for i in range(0, 4):
        matrix.append([pa[i][0], pa[i][1], 1, 0, 0, 0, -pb[i][0]*pa[i][0], -pb[i][0]*pa[i][1]])
        matrix.append([0, 0, 0, pa[i][0], pa[i][1], 1, -pb[i][1]*pa[i][0], -pb[i][1]*pa[i][1]])
    A = matrix
    B = []
    for i in range(0, 4):
        B.append(pb[i][0])
        B.append(pb[i][1])
    res = linsolve(A, B)
    return [res[0],res[1],res[2],res[3],res[4],res[5],res[6],res[7]]

def linsolve(A, B):
    """
    Solves a system of linear equations.
    """
    n = len(A)
    for i in range(0, n):
        max_row = i
        for k in range(i+1, n):
            if abs(A[k][i]) > abs(A[max_row][i]):
                max_row = k
        A[i], A[max_row] = A[max_row], A[i]
        B[i], B[max_row] = B[max_row], B[i]
        for k in range(i+1, n):
            c = -A[k][i]/A[i][i]
            for j in range(i, n):
                if i==j:
                    A[k][j] = 0
                else:
                    A[k][j] += c * A[i][j]
            B[k] += c * B[i]
    x = [0 for i in range(n)]
    for i in range(n-1, -1, -1):
        x[i] = B[i]/A[i][i]
        for k in range(i-1, -1, -1):
            B[k] -= A[k][i] * x[i]
    return x

from PIL import Image

def main():
    # --- CONFIGURATION ---

    artwork_path  = ["/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/version-4-0.6-border.png"]


    #11x14 wall 
    mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_1_frame_on_wall.jpeg"
    output_path = "fina_mockup_11x14_wall.png"
    dest_corners = [(329, 225), (693, 225), (693, 698), (329, 698)] 


    #11x14 table
    mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_on_table_v2.jpeg"
    output_path = "fina_mockup_11x14_table.png"
    dest_corners = [(238, 222), (722, 222), (722, 853), (238, 853)] #cutting into borders --> this one 
    #dest_corners = [(237, 222), (722, 222), (722, 853), (237, 853)] #cutting into borders
    #dest_corners = [(239, 222), (722, 222), (722, 853), (239, 853)] #cutting into borders

    #11x14 3x wall
    mockup_path = "/Users/johnmikedidonato/Projects/TheShapesOfStories/mockup_templates/11x14_3_frames_on_wall.jpeg"
    output_path = "fina_mockup_11x14_3x_wall.png"

    dest_corners = [
        (125, 340), (353, 340), (353, 637), (125, 637), #--> frame on left
        (398, 340), (626, 340), (626, 637), (398, 637), #--> frame in center
        (672, 340), (900, 340), (900, 637), (672, 637 ) #--> frame on right 
    ]





    #11x14 on wall
 

    
   

    # --- END CONFIGURATION ---

    try:
        mockup_img = Image.open(mockup_path)
        artwork_img = Image.open(artwork_path)

        # Ensure the background and artwork can handle transparency
        mockup_img = mockup_img.convert('RGBA')
        artwork_img = artwork_img.convert('RGBA')

        # Calculate the width and height from your coordinates
        top_left_corner = dest_corners[0]
        width = dest_corners[1][0] - dest_corners[0][0]
        height = dest_corners[3][1] - dest_corners[0][1]

        # Resize the artwork to the exact dimensions
        resized_artwork = artwork_img.resize((width, height), Image.Resampling.LANCZOS)

        # Paste the resized artwork onto the mockup at the top-left position
        mockup_img.paste(resized_artwork, top_left_corner, resized_artwork)
        
        # Convert back to RGB before saving as JPEG to avoid potential issues
        final_image = mockup_img.convert('RGB')
        final_image.save(output_path, 'JPEG')
        
        print(f"Success! Mockup saved to: {output_path}")

    except FileNotFoundError:
        print("Error: Could not find one of the image files. Make sure the filenames in the CONFIGURATION section are correct.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()