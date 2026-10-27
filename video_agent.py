import subprocess
from pathlib import Path

BASE = Path.home() / "storage/shared/Movies/YouTubeAgent"
IMAGES = BASE / "images"
VOICE = BASE / "test_voice.mp3"
OUTPUT = BASE / "automated_video.mp4"

def make_video():
    image = IMAGES / "scene1.jpg"

    if not image.exists():
        print("Image nahi mili:", image)
        return

    if not VOICE.exists():
        print("Voice nahi mili:", VOICE)
        return

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", str(image),
        "-i", str(VOICE),
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=increase,"
        "crop=1280:720,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ]

    try:
        subprocess.run(cmd, check=True)
        print("\nVIDEO READY!")
        print("Saved at:", OUTPUT)
    except subprocess.CalledProcessError:
        print("Video banane mein error aaya.")

if __name__ == "__main__":
    make_video()
