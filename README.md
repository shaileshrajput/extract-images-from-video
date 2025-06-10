**This project extract frames at regular intervals or when significant visual changes occur (scene changes), and then use Optical Character Recognition (OCR) on those extracted images.**

FFmpeg is excellent for video manipulation (extracting frames, audio, converting formats), but it doesn't directly perform OCR. To extract text from images, you'll need an OCR library. Tesseract OCR is a popular open-source (non-commercial) choice that works well with Python.

Here's a breakdown of the process and a Python script using `ffmpeg-python` (a Pythonic wrapper for FFmpeg) and `Pillow` (for image manipulation) along with `pytesseract` (for Tesseract OCR).

**Important Prerequisites:**

1.  **FFmpeg Installation:** You MUST have FFmpeg installed on your Windows 11 system and its `bin` directory added to your system's PATH environment variable. You can download static builds from the official FFmpeg website ([ffmpeg.org/download.html](https://ffmpeg.org/download.html)). If you're unsure how to add it to PATH, search for "add ffmpeg to path windows 11".
2.  **Tesseract OCR Installation:** Download and install the Tesseract OCR engine for Windows. You can find installers on its GitHub page or a reliable source like UB Mannheim's Tesseract build. Remember the installation path.
3.  **Python Libraries:** You'll need to install the following Python libraries:
    * `ffmpeg-python`: `pip install ffmpeg-python`
    * `Pillow`: `pip install Pillow`
    * `pytesseract`: `pip install pytesseract`

**Why this approach?**

* **Non-commercial:** FFmpeg, Tesseract, and the Python libraries are all open-source and free to use.
* **Easiest (relatively):** While it involves a few steps, it's a well-established and reliable method without proprietary software.
* **FFmpeg-only (for video processing):** FFmpeg handles all the video-related tasks (frame extraction). The OCR is a separate image processing step.
* **Python:** The script is written in Python, leveraging the `ffmpeg-python` wrapper for cleaner FFmpeg command execution.

**How to Use:**

1.  **Save the code:** Save the code above as a Python file (e.g., `video_text_extractor.py`).
2.  **Install Prerequisites:**
    * Install FFmpeg (if you haven't already) and add it to your system PATH.
    * Install Tesseract OCR (if you haven't already).
    * Open your VS Code terminal (or any command prompt) and run:
        ```bash
        pip install ffmpeg-python Pillow pytesseract
        ```
3.  **Configure Paths in the script:**
    * **`VIDEO_FOLDER`**: Change `"path/to/your/video/folder"` to the actual path of your video tutorials folder (e.g., `r"C:\Users\YourUser\Videos\Tutorials"`). The `r` before the string makes it a raw string, which is good for Windows paths to avoid issues with backslashes.
    * **`PYTESSERACT_PATH`**: Update this to the actual path of your `tesseract.exe` executable. By default, it's often in `C:\Program Files\Tesseract-OCR\tesseract.exe`.
4.  **Run the script:**
    ```bash
    python video_text_extractor.py
    ```

**Explanation:**

1.  **Imports:**
    * `ffmpeg`: The Python wrapper for FFmpeg.
    * `os`: For interacting with the operating system (listing files, creating directories).
    * `pytesseract`: The Python binding for Tesseract OCR.
    * `PIL (Pillow)`: Used by `pytesseract` to open and process images.
    * `shutil`: For removing directories.
2.  **Configuration:**
    * `VIDEO_FOLDER`: Where your video files are located.
    * `OUTPUT_TEXT_FOLDER`: Where the extracted text files will be saved.
    * `TEMP_FRAMES_FOLDER`: A temporary directory to store the extracted image frames before OCR. This will be cleaned up.
    * `PYTESSERACT_PATH`: Crucial for `pytesseract` to find your Tesseract installation.
    * `FRAME_INTERVAL_SECONDS`: Defines how often FFmpeg extracts a frame. A higher value means fewer frames and faster processing, but you might miss some slide changes. A lower value (e.g., 1 or 2 seconds) will be more comprehensive but generate many more frames and take longer.
3.  **`create_output_directories()` and `clean_temp_frames()`:** Utility functions for managing the folders.
4.  **`extract_frames(video_path, output_dir, interval_seconds)`:**
    * This is where FFmpeg is used.
    * `ffmpeg.input(video_path)`: Specifies the input video.
    * `.output(os.path.join(output_dir, 'frame_%04d.png'), vf=f'fps=1/{interval_seconds}')`: This is the core FFmpeg command.
        * `os.path.join(output_dir, 'frame_%04d.png')`: Defines the output path for frames. `_ %04d` ensures sequential numbering (e.g., `frame_0001.png`, `frame_0002.png`).
        * `vf=f'fps=1/{interval_seconds}'`: This is the video filter that tells FFmpeg to extract frames at the specified rate. `fps=1/5` means 1 frame every 5 seconds.
    * `.run()`: Executes the FFmpeg command. `capture_stdout` and `capture_stderr` are used to catch potential errors.
5.  **`extract_text_from_image(image_path)`:**
    * Opens the image using `PIL.Image.open()`.
    * Calls `pytesseract.image_to_string()` to perform OCR and return the extracted text.
    * Includes error handling for Tesseract not being found.
6.  **`process_video_for_text(video_file)`:**
    * Orchestrates the process for each video.
    * Creates a unique temporary folder for each video's frames.
    * Calls `extract_frames`.
    * Iterates through the extracted frames, calls `extract_text_from_image` for each, and appends the results.
    * Saves the combined text for each video into a `.txt` file in the `OUTPUT_TEXT_FOLDER`.
    * Cleans up the temporary frames for that specific video.
7.  **Main Execution (`if __name__ == "__main__":`)**
    * Sets up directories.
    * Iterates through all video files in `VIDEO_FOLDER`.
    * Calls `process_video_for_text` for each.
    * Performs final cleanup.

**Considerations and Potential Improvements (beyond "FFmpeg only" for the core logic):**

* **Slide Change Detection (Advanced):** Instead of fixed intervals, you could use a more advanced approach to detect *scene changes* (when a new slide appears). This would involve comparing consecutive frames for significant differences. While FFmpeg has some capabilities for scene change detection (e.g., using `select` filters with `scenecut`), integrating it for optimal text extraction would likely involve more complex image processing logic in Python (e.g., using OpenCV for image comparison) which goes beyond *only* FFmpeg. For a purely FFmpeg solution, fixed interval or keyframe extraction is the closest you can get.
* **OCR Accuracy:** OCR accuracy depends heavily on the quality of the slides, font, contrast, and resolution. You might need to experiment with `FRAME_INTERVAL_SECONDS` or preprocess frames (e.g., enhance contrast, resize) before passing them to Tesseract if accuracy is low.
* **Language:** Tesseract supports many languages. If your tutorials are not in English, you'll need to install the relevant Tesseract language packs and specify the language to `pytesseract.image_to_string()`.
* **Parallel Processing:** For 58 video files, processing them sequentially might take a while. You could use Python's `multiprocessing` module to process multiple videos concurrently, which would significantly speed up the process on multi-core CPUs.
* **Error Handling:** The current script has basic error handling for FFmpeg and Tesseract. You might want to add more robust error logging.
