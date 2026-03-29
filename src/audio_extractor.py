import os
import moviepy

def extract_audio(video_path, output_path="./audio.mp3"):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    video = moviepy.VideoFileClip(video_path)
    audio = video.audio
    duration = audio.duration
    fps = audio.fps
    audio.write_audiofile(output_path, fps=fps)
    return duration, fps