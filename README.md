# Bad Apple, but for notepad and the terminal
This supports both and I started with the terminal version first.

Works on **Windows** (real Notepad!!) and now on **Linux** too :D (KWrite, Kate, gedit or whatever text editor you have, on both Wayland and X11)

## Demo(s)
**Demo 1:**

[![Demo 1](https://img.shields.io/badge/▶_Watch_Demo_1-blue?style=for-the-badge)](https://youtu.be/pSD4fgsSPQY)

**Demo 2:**

[![Demo 2](https://img.shields.io/badge/▶_Watch_Demo_2-blue?style=for-the-badge)](https://youtu.be/o6bDJ5_cRLA)


> [!WARNING]
> Python syntax in VSCode might break randomly after running the script, but that's probably my environment and you most probably wont have the issue. But if it does happen for you, then the only solution is to restart vscode (i think). (this mainly happens sometimes after a video has finished generating its frames)

> [!TIP]
> It's better not to re-generate all of the frames on your own, since it'll either cause many problems or even frame skipping, the frames that were generated, that i embedded in this repository by default, are already good enough to use.

> [!NOTE]
> If your video isn't an mp4, then you might need to convert it to an mp4, fortunately however, you can always use ffmpeg to do so! (if you don't have it, install it via [www.ffmpeg.org](https://www.ffmpeg.org/download.html)).


## How it works
It uses moviepy for audio extracting and extracting the frames of the specified video (bad apple in this instance) and uses a very neat open-source tool called "image-to-ascii" to convert all those frames to ascii text!

It then uses those frames, with correct fps delay stuff, to then, finally, correctly show the video in the windows terminal or any other terminal.

For the notepad part, it uses pywin32 since modifying the txt file and hoping windows notepad refreshes it is hella slow and flickers a ton, so i opted for a more difficult but wayy better option by just modifying the window's text (notepad in this instance).

On Linux there's no notepad (sadly :c), so it opens a text editor instead and swaps its text through the accessibility bus (AT-SPI), which works on both Wayland and X11. If that doesn't work, it tries xdotool (X11 only), and if THAT doesn't work either, it just plays in the terminal instead so you still get your bad apple :3

## How to run it yourself
You need atleast:
- Python 3.8 or newer
- pip and uv
- Windows or Linux
- Git

### 0.1. Clone the repository
Install Git from git-scm.com, then restart your terminal (You can skip this step, only if you already have Git)

Afterwards, run `git clone --recursive https://github.com/lamps-dev/bad-apple-notepad` (Don't forget the '--recursive', without it, the image-to-ascii sub-module will not be cloned!)

Then, `cd bad-apple-notepad`

### 1. Install dependencies
Run `pip install -r requirements.txt`

**Linux only:** notepad mode also needs a couple of system packages (kwrite is just the editor, any other one works too):

```bash
# Arch
sudo pacman -S python-gobject at-spi2-core kwrite

# Debian / Ubuntu
sudo apt install python3-gi gir1.2-atspi-2.0 at-spi2-core kwrite

# Fedora
sudo dnf install python3-gobject at-spi2-core kwrite
```

If you use a venv, make it with `python -m venv --system-site-packages .venv` so it can actually see those packages.

### 2. (optional) Get a video file
(I recommend you using https://cobalt.meowing.de (Recommended) or yt-dlp depending on if you want to get the yt-dlp tool or not)

### 3. Run the script
Recommended command (Terminal mode): `python main.py --input bad_apple.mp4 --width 120 --height 50`

Notepad mode: `python main.py --input bad_apple.mp4 --width 120 --height 50 --mode notepad`

(on Linux you can also say `--mode editor`, since calling it notepad there is kinda lying lol)

and enjoy!!

> [!WARNING]
> You might get high performance issues if you don't have a very good PC so be careful!

## How do I compile?
Before doing so, make sure to use [uv](https://docs.astral.sh/uv) (Recommended)

### Windows
You need to run `pyinstaller --onefile --collect-all imageio --collect-all moviepy --hidden-import=pygame --hidden-import=PIL --hidden-import=numpy --hidden-import=sty --hidden-import=win32gui --hidden-import=win32con --hidden-import=win32api --add-data "image-to-ascii/converter.py;." --add-data "image-to-ascii/config.py;." --add-data "src/music_manager.py;src" --add-data "src/audio_extractor.py;src" --add-data "src/editor_common.py;src" --add-data "src/windows_editor.py;src" main.py` to compile properly for Windows.

### Linux
Same thing but with `:` instead of `;` and without the win32 stuff:

`pyinstaller --onefile --collect-all imageio --collect-all moviepy --hidden-import=pygame --hidden-import=PIL --hidden-import=numpy --hidden-import=sty --add-data "image-to-ascii/converter.py:." --add-data "image-to-ascii/config.py:." --add-data "src/music_manager.py:src" --add-data "src/audio_extractor.py:src" --add-data "src/editor_common.py:src" --add-data "src/linux_editor.py:src" main.py`

(the compiled Linux version still needs the system packages from step 1 on whatever PC runs it)
