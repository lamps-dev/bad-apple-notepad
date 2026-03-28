import moviepy

def extract_audio(video_path):
    video = moviepy.VideoFileClip(video_path)
    audio = video.audio
    duration = audio.duration
    fps = audio.fps
    audio.write_audiofile("./src/bad_apple.mp3", fps=fps)
    return duration, fps