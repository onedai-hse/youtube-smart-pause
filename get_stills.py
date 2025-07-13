#pip install pytubefix

import subprocess
import os
from pytubefix import YouTube

end_time_seconds = 300  # укажите на какой секунде нажали кнопку
video_id = "lEY2JxA2gZ0"  # video_id, взять из ссылки после v....


def extract_frames(input_file: str, start: float, end: float, interval: float = 5.0, output_dir: str = "frames"):
    os.makedirs(output_dir, exist_ok=True)
    duration = end - start
    fps = 1.0 / interval
    subprocess.run([
        "ffmpeg",
        "-ss", str(start),
        "-t", str(duration),
        "-i", input_file,
        "-vf", f"fps={fps}",
        os.path.join(output_dir, "frame_%04d.jpg")
    ], check=True)


if __name__ == "__main__":
    start_time = max(0, end_time_seconds - 120)

    yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
    stream = yt.streams.filter(file_extension='mp4', progressive=True).order_by('resolution').desc().first()
    stream.download(filename="video.mp4")

    extract_frames("video.mp4", start_time, end_time_seconds, interval=5.0, output_dir="frames")

    print(f"✅ Извлечены кадры каждые 5 секунд с {start_time}s до {end_time_seconds}s в папке 'frames'")
