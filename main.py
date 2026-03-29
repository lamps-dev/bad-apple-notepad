import argparse
import os
import subprocess
import sys
import time
import threading
import win32gui, win32con, win32api

from moviepy import VideoFileClip
from converter import image_to_ascii

# support both normal execution and PyInstaller bundled exe
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'src'))
else:
    sys.path.insert(0, './src')

from music_manager import stop_music, play_music
from audio_extractor import extract_audio

parser = argparse.ArgumentParser(description="Bad Apple Python for notepad arguments")
parser.add_argument("--input", help="path to your input file (video file), by default: bad_apple.mp4", default="bad_apple.mp4")
parser.add_argument("-o", "--output", help="filename and file format to output (default: output.txt)", default="output.txt")
parser.add_argument("--width", help="ASCII art width in characters (default: 80)", type=int, default=80)
parser.add_argument("--height", help="ASCII art height in characters (default: 40)", type=int, default=40)
parser.add_argument("--mode", help="display mode: 'notepad' or 'terminal' (default: terminal)", default="terminal")
parser.add_argument("--color", help="enable colorful output: true/false (default: false)", default="false", choices=["true", "false"])

args = parser.parse_args()

def extract_frames(clip, times, imgdir):
    if not os.path.exists(imgdir):
        os.makedirs(imgdir)

    for t in times:
        imgpath = os.path.join(imgdir, '{}.png'.format(int(t * clip.fps)))
        clip.save_frame(imgpath, t)

if not str(args.input).endswith((".mp4")):
     print("please either use a video file")
     exit(1)

if args.mode == "notepad" and args.color == "true":
     print("color mode is not supported with notepad (notepad cannot render ANSI color codes)")
     exit(1)

clip = VideoFileClip(args.input)
fps = clip.fps

# skip extraction if frames and audio already exist
imgs_exist = os.path.isdir("./imgs") and len(os.listdir("./imgs")) > 0
audio_exists = os.path.isfile("./src/bad_apple.mp3")

if not imgs_exist or not audio_exists:
    print("processing, this may take a moment (depending on your video duration)")
    times = [i/fps for i in range(int(fps * clip.duration))]
    if not imgs_exist:
        extract_frames(clip, times, "./imgs")
    if not audio_exists:
        extract_audio(args.input)
else:
    print("using cached frames and audio")

frame_delay = 1.0 / fps
filenames = sorted(os.listdir("./imgs"), key=lambda f: int(f.split('.')[0]))

# set up display mode
if args.mode == "notepad":
    subprocess.Popen(['notepad.exe'])
    time.sleep(2)  # wait for Notepad to open

    # find the Notepad window — try both classic and modern class names
    hwnd = win32gui.FindWindow("Notepad", None)
    if not hwnd:
        # Windows 11 modern Notepad uses a different class
        def find_notepad(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "Notepad" in title or "Untitled" in title:
                    results.append(hwnd)
        results = []
        win32gui.EnumWindows(find_notepad, results)
        hwnd = results[0] if results else None

    if not hwnd:
        print("could not find Notepad window")
        exit(1)

    # walk all descendants to find a text edit control
    edit = win32gui.FindWindowEx(hwnd, None, "Edit", None)
    if not edit:
        # modern Notepad nests the edit control deeper — search recursively
        def find_edit(parent):
            child = None
            while True:
                child = win32gui.FindWindowEx(parent, child, None, None)
                if not child:
                    return None
                class_name = win32gui.GetClassName(child)
                if class_name in ("Edit", "RichEditD2DPT"):
                    return child
                # recurse into children
                found = find_edit(child)
                if found:
                    return found
        edit = find_edit(hwnd)

    if not edit:
        print("could not find Notepad's edit control")
        print("debug: Notepad hwnd =", hwnd, "class =", win32gui.GetClassName(hwnd))
        exit(1)
else:
    os.system('cls' if os.name == 'nt' else 'clear')

# start music in a thread so it doesn't block frame rendering
music_thread = threading.Thread(target=play_music, args=('./src/bad_apple.mp3',))
music_thread.start()

for filename in filenames:
    frame_start = time.time()

    filepath = os.path.join("./imgs", filename)
    ascii_art = image_to_ascii(filepath, size=(args.width, args.height), colorful=args.color == "true", fix_scaling=False)

    if args.mode == "notepad":
        win32api.SendMessage(edit, win32con.WM_SETTEXT, 0, ascii_art)
    else:
        print("\033[H" + ascii_art, flush=True)

    # sleep the remaining time to stay in sync with the video's FPS
    elapsed = time.time() - frame_start
    sleep_time = frame_delay - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)

stop_music()