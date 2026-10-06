import argparse
import os
import sys
import time
import threading

# support both normal execution and PyInstaller bundled exe.
# this has to happen before converter / src imports below.
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'src'))
    sys.path.insert(0, sys._MEIPASS)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(base_dir, 'src'))
    sys.path.insert(0, os.path.join(base_dir, 'image-to-ascii'))

from moviepy import VideoFileClip
from converter import image_to_ascii

from music_manager import stop_music, play_music
from audio_extractor import extract_audio
from editor_common import NoEditorFound, NoTextBackend

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

parser = argparse.ArgumentParser(description="Bad Apple Python for notepad arguments")
parser.add_argument("--input", help="path to your input file (video file), by default: bad_apple.mp4", default="bad_apple.mp4")
parser.add_argument("-o", "--output", help="filename and file format to output (default: output.txt)", default="output.txt")
parser.add_argument("--width", help="ASCII art width in characters (default: 80)", type=int, default=80)
parser.add_argument("--height", help="ASCII art height in characters (default: 40)", type=int, default=40)
parser.add_argument("--mode", help="display mode: 'notepad' (a text editor window) or 'terminal' (default: terminal)", default="terminal", choices=["notepad", "editor", "terminal"])
parser.add_argument("--color", help="enable colorful output: true/false (default: false)", default="false", choices=["true", "false"])

args = parser.parse_args()

# "editor" is just a nicer alias for "notepad" on non-Windows systems
editor_mode = args.mode in ("notepad", "editor")


def extract_frames(clip, times, imgdir):
    if not os.path.exists(imgdir):
        os.makedirs(imgdir)

    for t in times:
        imgpath = os.path.join(imgdir, '{}.png'.format(int(t * clip.fps)))
        clip.save_frame(imgpath, t)


def make_editor_driver():
    """Return a driver for the current platform, or None to use the terminal."""
    if IS_WINDOWS:
        from windows_editor import create_driver
    elif IS_LINUX:
        from linux_editor import create_driver
    else:
        print("editor mode is only supported on Windows and Linux, "
              "falling back to terminal mode")
        return None

    try:
        return create_driver()
    except NoEditorFound as exc:
        # nothing to draw into at all -- this one is fatal
        print(exc)
        sys.exit(1)
    except NoTextBackend as exc:
        # an editor exists but nothing can push text into it
        print(exc)
        print("\nfalling back to terminal mode so the video still plays.")
        return None


if not str(args.input).endswith(".mp4"):
    print("please either use a video file")
    exit(1)

if editor_mode and args.color == "true":
    print("color mode is not supported in editor mode (text editors cannot render ANSI color codes)")
    exit(1)

clip = VideoFileClip(args.input)
fps = clip.fps

# each video gets its own cache, bad apple keeps using the frames shipped in the repo
video_name = os.path.splitext(os.path.basename(args.input))[0]
if video_name == "bad_apple":
    imgs_dir = "./imgs"
    audio_path = "./audio.mp3"
else:
    imgs_dir = os.path.join("./cache", video_name, "imgs")
    audio_path = os.path.join("./cache", video_name, "audio.mp3")

# skip extraction if frames and audio already exist
imgs_exist = os.path.isdir(imgs_dir) and len(os.listdir(imgs_dir)) > 0
audio_exists = os.path.isfile(audio_path)

if not imgs_exist or not audio_exists:
    print("processing, this may take a moment (depending on your video duration)")
    times = [i/fps for i in range(int(fps * clip.duration))]
    if not imgs_exist:
        extract_frames(clip, times, imgs_dir)
    if not audio_exists:
        extract_audio(args.input, audio_path)
else:
    print("using cached frames and audio")

frame_delay = 1.0 / fps
filenames = sorted(os.listdir(imgs_dir), key=lambda f: int(f.split('.')[0]))

# set up display mode
driver = make_editor_driver() if editor_mode else None
if driver is None:
    os.system('cls' if os.name == 'nt' else 'clear')

# start music in a thread so it doesn't block frame rendering
music_thread = threading.Thread(target=play_music, args=(audio_path,))
music_thread.start()

try:
    for filename in filenames:
        frame_start = time.time()

        filepath = os.path.join(imgs_dir, filename)
        ascii_art = image_to_ascii(filepath, size=(args.width, args.height), colorful=args.color == "true", fix_scaling=False)

        if driver is not None:
            driver.set_text(ascii_art)
        else:
            print("\033[H" + ascii_art, flush=True)

        # sleep the remaining time to stay in sync with the video's FPS
        elapsed = time.time() - frame_start
        sleep_time = frame_delay - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass
finally:
    stop_music()
    if driver is not None:
        driver.close()
