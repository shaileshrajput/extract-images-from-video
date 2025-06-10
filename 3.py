import ffmpeg
import os
import pytesseract
from PIL import Image
import shutil
import re # For regular expressions to extract numbers

# --- Configuration ---
VIDEO_FOLDER = r'C:\\ShaileshRajput\\Code\\img-process\\videos'   # IMPORTANT: Change this to your video folder path
OUTPUT_UNIQUE_SLIDES_FOLDER = "unique_slides" # New folder for unique slides
OUTPUT_TEXT_FOLDER = "extracted_text"
TEMP_FRAMES_FOLDER = "temp_frames"
# Path to your Tesseract executable (e.g., 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
PYTESSERACT_PATH = r'C:\\Users\\a735948\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe'

# Set the Tesseract command path
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_PATH

# Frame extraction interval in seconds.
# We might need a smaller interval here to ensure we capture every page change.
# For example, 1 second. If slides change very rapidly, even lower.
FRAME_INTERVAL_SECONDS = 5

# --- Page Number Region Configuration ---
# These values are crucial and might need adjustment based on your videos.
# Define the coordinates (left, upper, right, lower) for the cropping box.
# This assumes page numbers are always in the bottom-right.
# Example: 100 pixels from right, 50 pixels from bottom, 50 pixels wide, 30 pixels tall.
# You'll likely need to adjust these based on your actual video resolution and slide layout.
# It's recommended to extract a few sample frames manually and determine these coordinates precisely.
# For a 1920x1080 video, a bottom-right corner might look like:
# (1920 - width_of_region, 1080 - height_of_region, 1920, 1080)
# Let's start with a general assumption and explain how to refine.
PAGE_NUMBER_REGION_WIDTH = 150 # Estimated width of the region
PAGE_NUMBER_REGION_HEIGHT = 80 # Estimated height of the region
PAGE_NUMBER_REGION_OFFSET_X = -5 # How far from the right edge
PAGE_NUMBER_REGION_OFFSET_Y = 20 # How far from the bottom edge


# --- Functions ---

def create_output_directories():
    """Creates output directories if they don't exist."""
    os.makedirs(OUTPUT_UNIQUE_SLIDES_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_TEXT_FOLDER, exist_ok=True)
    os.makedirs(TEMP_FRAMES_FOLDER, exist_ok=True)

def clean_temp_frames():
    """Removes the temporary frames folder."""
    #if os.path.exists(TEMP_FRAMES_FOLDER):
        #shutil.rmtree(TEMP_FRAMES_FOLDER)
    #os.makedirs(TEMP_FRAMES_FOLDER, exist_ok=True) # Recreate for fresh start

def extract_frames(video_path, output_dir, interval_seconds):
    """
    Extracts frames from a video at a specified interval using FFmpeg.
    """
    print(f"Extracting frames from {video_path}...")
    try:
        # ffmpeg -i input.mp4 -vf fps=1/X output_frames_%04d.png
        (
            ffmpeg
            .input(video_path)
            .output(os.path.join(output_dir, 'frame_%04d.png'), vf=f'fps=1/{interval_seconds}')
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Frames extracted to {output_dir}")
    except ffmpeg.Error as e:
        print(f"FFmpeg error for {video_path}:")
        print(e.stderr.decode('utf8'))
        return False
    return True

def get_page_number_from_image(image_path):
    """
    Extracts the page number from the bottom-right corner of an image.
    Returns None if no number is found or on error.
    """
    try:
        img = Image.open(image_path)
        img_width, img_height = img.size

        # Calculate crop box coordinates
        left = img_width - PAGE_NUMBER_REGION_WIDTH - PAGE_NUMBER_REGION_OFFSET_X
        upper = img_height - PAGE_NUMBER_REGION_HEIGHT - PAGE_NUMBER_REGION_OFFSET_Y
        right = img_width - PAGE_NUMBER_REGION_OFFSET_X
        lower = img_height - PAGE_NUMBER_REGION_OFFSET_Y

        # Ensure coordinates are within image bounds
        left = max(0, left)
        upper = max(0, upper)
        right = min(img_width, right)
        lower = min(img_height, lower)

        crop_box = (left, upper, right, lower)
        cropped_img = img.crop(crop_box)
        
        # You can uncomment to save cropped images for debugging:
        #cropped_img.save(f"debug_cropped_{os.path.basename(image_path)}")

        text = pytesseract.image_to_string(cropped_img, config='--psm 6') # psm 8 for single word/number
        print(text)
        # Use regex to find digits. Tesseract might pick up noise.
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0]) # Return the first number found
        return None
    except pytesseract.TesseractNotFoundError:
        print("Tesseract OCR is not installed or not found in your PATH.")
        print(f"Please ensure Tesseract is installed and {PYTESSERACT_PATH} is correct.")
        return None
    except Exception as e:
        print(f"Error processing image {image_path} for page number: {e}")
        return None

def process_video_for_unique_slides(video_file):
    """
    Processes a single video file to extract unique slides based on page number.
    """
    video_name = os.path.splitext(os.path.basename(video_file))[0]
    video_full_path = os.path.join(VIDEO_FOLDER, video_file)
    
    temp_video_frames_dir = os.path.join(TEMP_FRAMES_FOLDER, video_name)
    os.makedirs(temp_video_frames_dir, exist_ok=True)

    if not extract_frames(video_full_path, temp_video_frames_dir, FRAME_INTERVAL_SECONDS):
        print(f"Skipping {video_file} due to FFmpeg error during frame extraction.")
        #shutil.rmtree(temp_video_frames_dir)
        return

    frame_files = sorted([f for f in os.listdir(temp_video_frames_dir) if f.lower().endswith(('.png', '.jpg'))])

    if not frame_files:
        print(f"No frames extracted for {video_file}. Check video file or FRAME_INTERVAL_SECONDS.")
        #shutil.rmtree(temp_video_frames_dir)
        return

    print(f"Comparing frames for unique slides from {video_file}...")

    previous_page_number = -1 # Initialize with a value that ensures the first page is always picked
    current_image_path = None
    
    # Text extraction for each unique slide will be accumulated
    video_extracted_texts = []

    for i, frame_file in enumerate(frame_files):
        current_frame_path = os.path.join(temp_video_frames_dir, frame_file)
        current_page_number = get_page_number_from_image(current_frame_path)

        # Handle cases where page number cannot be read
        if current_page_number is None:
            # If it's the first frame and no number, or if we cannot read a number,
            # we might still want to consider it if a previous page number was valid.
            # For simplicity, if we can't read, we'll treat it as 'no change' for now,
            # or you could try to pick it if the previous was valid.
            print(f"Warning: Could not read page number from {frame_file}. Skipping comparison for this frame.")
            continue # Move to the next frame

        # Logic for comparing page numbers
        if current_page_number > previous_page_number:
            # New page detected or first frame of a new sequence
            if i == 0 or current_image_path is not None:
                # If it's the very first frame or we have a valid previous image, copy it.
                # Copy the *previous* identified unique slide if it exists
                # Or copy the current if it's the first actual valid page.
                
                # Let's simplify: always copy the *current* frame if its page number is greater
                # than the previously recognized page number. This ensures we pick the *first*
                # instance of a new page.
                unique_slide_name = f"{video_name}_page_{current_page_number}_{os.path.basename(current_frame_path)}"
                destination_path = os.path.join(OUTPUT_UNIQUE_SLIDES_FOLDER, unique_slide_name)
                shutil.copy2(current_frame_path, destination_path)
                print(f"Copied unique slide: {unique_slide_name} (Page: {current_page_number})")

                # # Also perform OCR on this unique slide for full text extraction
                # full_text = pytesseract.image_to_string(Image.open(current_frame_path))
                # if full_text:
                #     clean_text = "\n".join([line.strip() for line in full_text.split('\n') if line.strip()])
                #     if clean_text:
                #         video_extracted_texts.append(f"--- Unique Slide: {unique_slide_name} (Page: {current_page_number}) ---\n{clean_text}\n")
                
            previous_page_number = current_page_number
            current_image_path = current_frame_path # Set current for next comparison
        elif current_page_number == previous_page_number:
            # Page number is the same, just update current_image_path for the next iteration
            current_image_path = current_frame_path
        # If current_page_number < previous_page_number, it's likely a misread or a loop in video, ignore.

    # # Save all extracted texts for the video
    # output_text_file = os.path.join(OUTPUT_TEXT_FOLDER, f"{video_name}_unique_slides_text.txt")
    # if video_extracted_texts:
    #     with open(output_text_file, "w", encoding="utf-8") as f:
    #         f.write("\n\n".join(video_extracted_texts))
    #     print(f"Extracted unique slide text saved to {output_text_file}")
    # else:
    #     print(f"No unique slide text extracted from {video_file}.")

    # Clean up temporary frames for this video
    #shutil.rmtree(temp_video_frames_dir)

# --- Main Execution ---
if __name__ == "__main__":
    create_output_directories()
    clean_temp_frames() # Ensure a clean start for temp frames

    if not os.path.exists(VIDEO_FOLDER):
        print(f"Error: Video folder not found at '{VIDEO_FOLDER}'")
        print("Please update the VIDEO_FOLDER variable to the correct path.")
    else:
        video_files = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))]
        if not video_files:
            print(f"No video files found in '{VIDEO_FOLDER}'. Please check the folder and file extensions.")
        else:
            print(f"Found {len(video_files)} video files to process.")
            print("\n--- IMPORTANT: Adjust PAGE_NUMBER_REGION_WIDTH/HEIGHT/OFFSET_X/Y ---")
            print("These values are critical for accurate page number detection.")
            print("You may need to manually inspect a few frames to determine the correct crop box.")
            print("------------------------------------------------------------------\n")
            
            for video_file in video_files:
                process_video_for_unique_slides(video_file)
    
    print("\nProcessing complete.")
   # clean_temp_frames() # Final cleanup of the main temp frames folder