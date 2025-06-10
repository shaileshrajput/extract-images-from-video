import ffmpeg
import os
import pytesseract
from PIL import Image, ImageEnhance # Import ImageEnhance for potential preprocessing
import shutil
import re

# --- Configuration ---
VIDEO_FOLDER = r'C:\\ShaileshRajput\\Code\\img-process\\videos'   # IMPORTANT: Change this to your video folder path
OUTPUT_UNIQUE_SLIDES_FOLDER = "unique_slides" # New folder for unique slides
OUTPUT_TEXT_FOLDER = "extracted_text"
TEMP_FRAMES_FOLDER = "temp_frames"
# Path to your Tesseract executable (e.g., 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
PYTESSERACT_PATH = r'C:\\Users\\a735948\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe'

# Set the Tesseract command path
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_PATH

FRAME_INTERVAL_SECONDS = 5 

# --- Page Number Region Configuration ---
# These values are crucial and might need adjustment based on your videos.
PAGE_NUMBER_REGION_WIDTH = 150 
PAGE_NUMBER_REGION_HEIGHT = 80 
PAGE_NUMBER_REGION_OFFSET_X = -5 
PAGE_NUMBER_REGION_OFFSET_Y = 20 

# --- Functions (unchanged, but adding preprocessing options) ---

def create_output_directories():
    """Creates output directories if they don't exist."""
    os.makedirs(OUTPUT_UNIQUE_SLIDES_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_TEXT_FOLDER, exist_ok=True)
    os.makedirs(TEMP_FRAMES_FOLDER, exist_ok=True)

def clean_temp_frames():
    """Removes the temporary frames folder."""
    # if os.path.exists(TEMP_FRAMES_FOLDER):
    #     shutil.rmtree(TEMP_FRAMES_FOLDER)
    os.makedirs(TEMP_FRAMES_FOLDER, exist_ok=True) # Recreate for fresh start

def extract_frames(video_path, output_dir, interval_seconds):
    """
    Extracts frames from a video at a specified interval using FFmpeg.
    """
    print(f"Extracting frames from {video_path}...")
    try:
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

        left = img_width - PAGE_NUMBER_REGION_WIDTH - PAGE_NUMBER_REGION_OFFSET_X
        upper = img_height - PAGE_NUMBER_REGION_HEIGHT - PAGE_NUMBER_REGION_OFFSET_Y
        right = img_width - PAGE_NUMBER_REGION_OFFSET_X
        lower = img_height - PAGE_NUMBER_REGION_OFFSET_Y

        left = max(0, left)
        upper = max(0, upper)
        right = min(img_width, right)
        lower = min(img_height, lower)

        crop_box = (left, upper, right, lower)
        
        # Optional: Debugging cropped images
        # debug_cropped_path = os.path.join("debug_crops", f"cropped_{os.path.basename(image_path)}")
        # os.makedirs("debug_crops", exist_ok=True) 
        
        cropped_img = img.crop(crop_box)
        # cropped_img.save(debug_cropped_path) # UNCOMMENT THIS TO DEBUG CROPPING
        
        # --- Image Preprocessing for better OCR (Uncomment and adjust as needed) ---
        # cropped_img = cropped_img.convert('L') # Grayscale
        # enhancer = ImageEnhance.Contrast(cropped_img)
        # cropped_img = enhancer.enhance(2.0) # Adjust factor
        # threshold = 180 # Adjust this threshold based on your image
        # cropped_img = cropped_img.point(lambda x: 0 if x < threshold else 255, '1')
        # new_width = cropped_img.width * 2
        # new_height = cropped_img.height * 2
        # cropped_img = cropped_img.resize((new_width, new_height), Image.LANCZOS)
        # --- End Image Preprocessing ---

        # Tesseract configuration: try without whitelist first if previous attempt failed
        # If whitelist causes issues, try without it first to see if Tesseract extracts *anything*.
        # text = pytesseract.image_to_string(cropped_img, config='--psm 6') # More general PSM
        
        # Preferred for numbers with whitelist if Tesseract version supports it well
        text = pytesseract.image_to_string(cropped_img, config='--psm 6 -c tessedit_char_whitelist=0123456789') 
        
        # DEBUG: Print raw OCR output
        # if text.strip() == "":
        #     print(f"DEBUG: No text extracted from {os.path.basename(image_path)} (cropped box: {crop_box})")
        # else:
        #     print(f"DEBUG: Raw OCR from {os.path.basename(image_path)}: '{text.strip()}'")

        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        return None
    except pytesseract.TesseractNotFoundError:
        print("Tesseract OCR is not installed or not found in your PATH.")
        print(f"Please ensure Tesseract is installed and {PYTESSERACT_PATH} is correct.")
        return None
    except Exception as e:
        print(f"Error processing image {image_path} for page number: {e}")
        return None

# --- REWRITTEN process_video_for_unique_slides ---

def process_video_for_unique_slides(video_file):
    """
    Processes a single video file: extracts frames, performs OCR, and saves unique slides
    by iterating from the last image to the first and selecting the smaller page number.
    """
    video_name = os.path.splitext(os.path.basename(video_file))[0]
    video_full_path = os.path.join(VIDEO_FOLDER, video_file)
    
    temp_video_frames_dir = os.path.join(TEMP_FRAMES_FOLDER, video_name)
    os.makedirs(temp_video_frames_dir, exist_ok=True)

    if not extract_frames(video_full_path, temp_video_frames_dir, FRAME_INTERVAL_SECONDS):
        print(f"Skipping {video_file} due to FFmpeg error during frame extraction.")
        shutil.rmtree(temp_video_frames_dir)
        return

    # Get all frame files and sort them to ensure correct sequential order
    frame_files_unsorted = [f for f in os.listdir(temp_video_frames_dir) if f.lower().endswith(('.png', '.jpg'))]
    if not frame_files_unsorted:
        print(f"No frames extracted for {video_file}. Check video file or FRAME_INTERVAL_SECONDS.")
        shutil.rmtree(temp_video_frames_dir)
        return
    
    # Sort numerically (important for 'frame_0001.png', 'frame_0010.png' etc.)
    # This creates a list like ['frame_0001.png', ..., 'frame_N.png']
    frame_files = sorted(frame_files_unsorted)

    print(f"Processing {len(frame_files)} frames from {video_file} in reverse for unique slides...")

    unique_slides_to_save = [] # List to store paths of unique slides we want to keep
    # Text for the unique slides will be stored here
    video_extracted_texts = []

    # Initialize with a high value to ensure the last page number found is always smaller
    # This also handles cases where no page number is found for some frames.
    last_processed_page_number = float('inf') 
    
    # Iterate from the last frame to the first
    # Using enumerate with reversed(list) is memory efficient
    for i in reversed(range(len(frame_files))):
        current_frame_filename = frame_files[i]
        current_frame_path = os.path.join(temp_video_frames_dir, current_frame_filename)
        
        current_page_number = get_page_number_from_image(current_frame_path)

        # Skip if no page number can be read for the current frame
        if current_page_number is None:
            # print(f"Warning: No page number read from {current_frame_filename}. Skipping for comparison.")
            continue 

        # The logic: If the current frame's page number is SMALLER than the last processed (larger) one,
        # it means we've just stepped back into a new (previous) page. This frame is unique.
        if current_page_number < last_processed_page_number:
            # This frame is the "first" occurrence of this page number when scanning backwards.
            # So, it's the last frame of the previous page in the original video sequence.
            
            # Add this frame to our list of unique slides to save
            unique_slides_to_save.append(current_frame_path)
            last_processed_page_number = current_page_number # Update for the next comparison
            
            # Extract full text for this unique slide
            # full_text = pytesseract.image_to_string(Image.open(current_frame_path))
            # if full_text:
            #     clean_text = "\n".join([line.strip() for line in full_text.split('\n') if line.strip()])
            #     if clean_text:
            #         video_extracted_texts.append(f"--- Unique Slide (Reverse Scan): {os.path.basename(current_frame_path)} (Page: {current_page_number}) ---\n{clean_text}\n")
            print(f"Identified unique slide (Page: {current_page_number}) from {current_frame_filename}")
        # If current_page_number is equal or greater than last_processed_page_number, it means
        # we're still on the same page or have an OCR error, so we ignore it.
        # This handles cases where numbers might be the same, or if they jump up (OCR error).

    # Now, save the identified unique slides and their texts
    # We collected them in reverse, but let's save them in numerical (forward) order
    unique_slides_to_save.sort() # Sort by filename to get chronological order
    
    saved_count = 0
    for unique_slide_path in unique_slides_to_save:
        unique_slide_name = f"{video_name}_{os.path.basename(unique_slide_path)}"
        destination_path = os.path.join(OUTPUT_UNIQUE_SLIDES_FOLDER, unique_slide_name)
        shutil.copy2(unique_slide_path, destination_path)
        saved_count += 1
    print(f"Copied {saved_count} unique slides to {OUTPUT_UNIQUE_SLIDES_FOLDER}")

    # # Save all extracted texts for the video
    # output_text_file = os.path.join(OUTPUT_TEXT_FOLDER, f"{video_name}_unique_slides_text_reverse.txt")
    # if video_extracted_texts:
    #     # The texts were collected in reverse order of page detection.
    #     # If you want them in forward page order, you'd need to sort 'video_extracted_texts'
    #     # based on the page number extracted in their header.
    #     # For simplicity, we'll save them as they were collected (reverse temporal scan).
    #     with open(output_text_file, "w", encoding="utf-8") as f:
    #         f.write("\n\n".join(video_extracted_texts))
    #     print(f"Extracted unique slide text saved to {output_text_file}")
    # else:
    #     print(f"No unique slide text extracted from {video_file}.")

    # Clean up temporary frames for this video
    #shutil.rmtree(temp_video_frames_dir)

# --- Main Execution (unchanged) ---
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
    clean_temp_frames() # Final cleanup of the main temp frames folder