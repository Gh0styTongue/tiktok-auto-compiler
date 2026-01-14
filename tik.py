import os
import sys
import re
import subprocess
import yt_dlp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

MAX_HASHTAGS = 1
MAX_TITLE_LEN = 100
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
HISTORY_FILE = "history.txt"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_to_history(video_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

def extract_video_id(url):
    match = re.search(r'/video/(\d+)', url)
    return match.group(1) if match else url

def get_encoder_settings():
    print(">> Checking for GPU acceleration...")
    test_cmd = ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc", "-c:v", "h264_nvenc", "-t", "0.1", "-f", "null", "-"]
    try:
        subprocess.run(test_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(">> NVIDIA GPU DETECTED: Enabling High-Speed NVENC Encoding")
        return ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "constqp", "-qp", "28"]
    except:
        print(">> GPU NOT DETECTED: Falling back to CPU (Ultrafast)")
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]

ENCODER_FLAGS = get_encoder_settings()

def clean_text_for_ffmpeg(text, max_len):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 #@-_."
    clean = "".join([c for c in text if c in allowed])
    if len(clean) > max_len:
        return clean[:max_len-3] + "..."
    return clean

def format_title_with_hashtags(title):
    parts = title.split()
    clean_words = []
    hashtag_count = 0
    for word in parts:
        if word.startswith("#"):
            if hashtag_count < MAX_HASHTAGS:
                clean_words.append(word)
                hashtag_count += 1
        else:
            clean_words.append(word)
    return " ".join(clean_words)

def get_video_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 0

def process_clip(input_path, output_path, title, creator_name, duration):
    print(f"   > Processing clip: '{title[:30]}...'")
    safe_title = clean_text_for_ffmpeg(title, MAX_TITLE_LEN)
    credit_line = clean_text_for_ffmpeg(f"Creator - {creator_name}", 50)
    font_cmd = "font='Arial':" 

    fade_out_start = max(0, duration - 0.5)
    
    scale_cmd = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    
    box_height = 100
    text_y = f"h-{box_height}+15"
    credit_y = f"h-{box_height}+55"

    video_filters = (
        f"{scale_cmd},"
        f"drawbox=y=ih-{box_height}:color=white@0.6:width=iw:height={box_height}:t=fill,"
        f"drawtext={font_cmd}text='{safe_title}':fontcolor=black:fontsize=24:x=(w-text_w)/2:y={text_y},"
        f"drawtext={font_cmd}text='{credit_line}':fontcolor=black:fontsize=18:x=(w-text_w)/2:y={credit_y},"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_start}:d=0.5"
    )

    audio_filters = f"afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_start}:d=0.5"
    
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", video_filters, "-af", audio_filters, "-r", "30"]
    cmd.extend(ENCODER_FLAGS)
    cmd.extend(["-c:a", "aac", "-ar", "44100", output_path])
    
    print("   > Applying filters & re-encoding...")
    
    result = subprocess.run(
        cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.PIPE, 
        text=True, 
        encoding='utf-8', 
        errors='replace'
    )
    
    if result.returncode != 0:
        print(f"   [!] FFmpeg Error on {input_path}:\n{result.stderr}")
        return False
    
    print("   > Clip processed successfully.")
    return True

def get_links_from_browser(tags):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--log-level=3") 
    
    print(">> Launching Chrome Browser...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_links = []

    for tag in tags:
        tag = tag.strip().replace("#", "")
        if not tag: continue

        url = f"https://www.tiktok.com/tag/{tag}"

        print(f"\n>> Opening Hashtag: #{tag}")
        driver.get(url)
        
        print("\n" + "="*50)
        print(f"ACTION REQUIRED for #{tag}:")
        print("1. Solve Captcha if needed.")
        print("2. Scroll down to load videos.")
        input("3. PRESS ENTER HERE WHEN DONE SCROLLING...")
        print("="*50 + "\n")
        
        print(">> Scanning page for video links...")
        elements = driver.find_elements(By.TAG_NAME, "a")
        count_new = 0
        for elem in elements:
            href = elem.get_attribute("href")
            if href and "/video/" in href and href not in all_links:
                all_links.append(href)
                count_new += 1
        print(f">> Collected {count_new} new links from #{tag}.")

    print(">> Closing Browser...")
    driver.quit()
    return all_links

def main():
    try:
        user_input = input("Enter hashtags (comma separated, no # needed): ")
        tags = user_input.split(',')
        
        target_min = float(input("Target compilation length (minutes)? "))
    except: target_min = 5.0
    
    target_sec = target_min * 60
    print(f"\n>> Target Duration: {target_sec} seconds")

    history = load_history()
    print(f">> Loaded {len(history)} previously used videos from history.")

    compiled_files = []
    current_duration = 0
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True, 'ignoreerrors': True
    }

    while current_duration < target_sec:
        print(f"\n>> Status: {int(current_duration)}s collected / {int(target_sec)}s target.")
        
        links = get_links_from_browser(tags)
        
        if not links:
            print(">> No links found this run.")
        
        print(f"\n>> Filtering duplicates...")
        new_links = []
        for link in links:
            vid_id = extract_video_id(link)
            if vid_id not in history:
                new_links.append(link)
        
        print(f">> Found {len(new_links)} NEW videos (skipped {len(links) - len(new_links)} duplicates).")

        if not new_links:
            print(">> All videos found are duplicates!")
            retry = input(">> Would you like to reload the browser to scroll further? (y/n): ")
            if retry.lower() != 'y':
                break
            continue

        print(f"\n>> Starting Batch Processing...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(new_links):
                if current_duration >= target_sec:
                    break
                
                print(f"\n[{i+1}/{len(new_links)}] Downloading: {url}...")
                try:
                    info = ydl.extract_info(url, download=True)
                    if not info: 
                        print("   [!] Failed to download.")
                        continue
                    
                    vid_id = info['id']
                    raw_path = f"{vid_id}.mp4"
                    processed_path = f"proc_{vid_id}.mp4"
                    
                    if os.path.exists(raw_path):
                        raw_title = info.get('title', 'TikTok')
                        uploader = info.get('uploader', 'Unknown')
                        duration = get_video_duration(raw_path)
                        
                        final_title = format_title_with_hashtags(raw_title)
                        
                        success = process_clip(raw_path, processed_path, final_title, uploader, duration)
                        
                        if success and os.path.exists(processed_path):
                            abs_path = os.path.abspath(processed_path)
                            compiled_files.append(abs_path)
                            
                            current_duration += duration
                            save_to_history(vid_id)
                            history.add(vid_id)
                            
                            print(f"   > Added! Total Duration: {int(current_duration)}s")
                        else:
                            print("   [!] Processing failed.")
                        
                        if os.path.exists(raw_path):
                            os.remove(raw_path)
                except Exception as e:
                    print(f"   [!] Error: {e}")

        if current_duration < target_sec:
            print(f"\n>> Target time not reached ({int(current_duration)}s / {int(target_sec)}s).")
            retry = input(">> Reload browser to find more videos? (y/n): ")
            if retry.lower() != 'y':
                break
        else:
            print("\n>> Target duration reached!")

    if not compiled_files:
        print("\n>> No videos ready for compilation.")
        return

    print(f"\n>> Generating file list for {len(compiled_files)} clips...")
    list_path = os.path.abspath("mylist.txt")
    final_output = os.path.abspath("final_compilation.mp4")

    with open(list_path, 'w', encoding='utf-8') as f:
        for path in compiled_files:
            safe_path = path.replace('\\', '/').replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    print(f">> Merging clips into {final_output}...")
    
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", final_output], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.PIPE, 
        text=True, 
        encoding='utf-8', 
        errors='replace'
    )

    if result.returncode != 0:
        print(f"ERROR: Merge Failed!\n{result.stderr}")
        return

    print(f"\n>> DONE! Saved as: {final_output}")
    
    print(">> Cleaning up temporary files...")
    for f in compiled_files:
        if os.path.exists(f): os.remove(f)
    if os.path.exists(list_path): os.remove(list_path)
    print(">> Cleanup complete.")

if __name__ == "__main__":
    main()
