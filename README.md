# TikTok Auto Compiler 🎥

A powerful Python automation tool that scrapes TikTok videos based on hashtags, avoids duplicates, and merges them into high-quality compilation videos with standardized formatting and attribution.

## 🚀 Features

* **Automated Scraping:** Uses Selenium to navigate TikTok tags and collect video links.
* **Smart Deduplication:** Maintains a `history.txt` file to ensure you never download the same video twice across different runs.
* **Visual Processing (FFmpeg):**
    * **Standardization:** Forces all videos to **720x1280 (HD Vertical)** so they merge perfectly without crashing.
    * **Overlays:** Automatically burns in the Video Title and Creator Name at the bottom (Vine/Compilation style).
    * **Transitions:** Adds smooth 0.5s fade-in/out effects to video and audio.
* **Hardware Acceleration:** Automatically detects NVIDIA GPUs to speed up rendering by 5x-10x.
* **Reload Loop:** Allows you to keep reloading the browser to grab more videos until your target duration is met.

## 🛠️ Prerequisites

1.  **Python 3.10+**: Ensure Python is installed and added to your PATH.
2.  **Google Chrome**: The script uses the installed Chrome browser for scraping.
3.  **FFmpeg**: **(Crucial)** You must have FFmpeg installed and added to your system PATH for video processing to work.
    * *Windows Guide:* Download the build from gyan.dev, extract it, and add the `bin` folder to your Environment Variables.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Gh0styTongue/tiktok-auto-compiler.git
    cd tiktok-auto-compiler
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install yt-dlp selenium webdriver-manager
    ```

##  ▶️ How to Use

1.  **Run the script:**
    ```bash
    python tik.py
    ```

2.  **Follow the prompts:**
    * **Enter Hashtags:** Type tags separated by commas (e.g., `nostalgia, 2000s, retro`). No need for the `#` symbol.
    * **Target Duration:** Enter how many minutes long you want the final video to be.

3.  **Browser Interaction:**
    * A Chrome window will open.
    * **Action Required:** Solve the Captcha if it appears. Scroll down until you have loaded enough videos.
    * Press **ENTER** in the terminal to capture the links and start processing.

4.  **Wait for Processing:**
    * The script will download videos, process them using FFmpeg, and merge them.
    * **Output:** The final video will be saved as `final_compilation.mp4`.

## ⚙️ Configuration

You can tweak the constants at the top of the script to change settings:

```python
MAX_HASHTAGS = 1        # How many hashtags to keep in the video title
MAX_TITLE_LEN = 100     # Max characters for the title overlay
VIDEO_WIDTH = 720       # Output width
VIDEO_HEIGHT = 1280     # Output height
