# Bad Apple, but for notepad and the terminal
This supports both and i started with the terminal version first.

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
> This program is also mainly for windows, im planning to port it over to linux too, but it may take a bit more time to do so, depending on how bad my code is atm.

## How it works
It uses moviepy for audio extracting and extracting the frames of the specified video (bad apple in this instance) and uses a very neat open-source tool called "image-to-ascii" to convert all those frames to ascii text!

It then uses those frames, with correct fps delay stuff, to then, finally, correctly show the video in the windows terminal or any other terminal.

For the notepad part, it uses pywin32 since modifying the txt file and hoping windows notepad refreshes it is hella slow and flickers a ton, so i opted for a more difficult but wayy better option by just modifying the window's text (notepad in this instance).

## How to run it yourself
You need atleast:
- Python 3.8 or newer,
- Pip,
- Mainly a windows PC.

### 1. Install dependencies
Run `pip install -r requirements.txt` to do so.

### 2. (optional) Get a video file
(I recommend you using yt-dlp or https://ytdlp.online if you don't want the program directly)

### 3. Run the script
Recommended command: `python main.py --input bad_apple.mp4 --width 120 --height 50 --mode notepad`

and enjoy!!

> [!WARNING]
> You might get high perfomance issues if you don't have a very good PC so be careful!

## How do I compile?
You need to run `pyinstaller --onefile --add-data "image-to-ascii/converter.py;." --add-data "image-to-ascii/config.py;." --add-data "src/music_manager.py;src" --add-data "src/audio_extractor.py;src" main.py` to compile properly for Windows. (before doing so, make sure to `python -m venv .venv`, `.venv/Scripts/activate` and `pip install -r requirements.txt`)