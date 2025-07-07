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
    # 1. Filename of your main mockup image
    #mockup_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/1_8x10_wood_frame_on_ground.psd' # <-- EDIT THIS
    mockup_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/literary-art-print-mockup-template-with-black-frame-straight-on.png'

    #mockup_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/Frame_Mockup_PSD 2.psd'
    # 2. Filename of the artwork you want to insert
    artwork_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/title-the-great-gatsby_protagonist-jay-gatsby_product-print_size-8x10_line-type-char_background-color-#0A1F3B_font-color-#F9D342_border-color-#26834A_font-Josefin Sans_title-display-yes.png' # <-- EDIT THIS
    
    # 3. Filename for the final output file
    output_path = 'final_mockup_test.jpg'

    # 4. Paste the coordinates you found here
    #dest_corners = [(908, 445), (2100, 445), (2100, 1930), (908, 1930)] # <-- EDIT THIS
   
    #dest_corners = [(625, 425), (2345, 425), (2345, 2633), (625, 2633)] # <-- EDIT THIS

    dest_corners = [(612, 170), (1157, 170), (1157, 793), (612, 793)]
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