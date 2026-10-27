# Final YouTube Agent for Samsung Galaxy Tab S9 / Termux

## Honest capability boundary
This is a ₹0-first 1080p video assembly pipeline. It uses:
- OpenRouter free text model for Hindi script + scene plan (subject to provider/model limits)
- Edge-TTS Hindi neural voice (online service; availability/terms may change)
- FFmpeg for 1080p H.264 MP4 or 4K upscale, zoom motion, audio and optional selectable subtitle track
- Pillow-generated stylized scene cards as the dependable free fallback

It does **not** magically generate photorealistic moving 3D/2D characters locally. True AI image/video generation generally needs a separate service with its own limits, API key, free allowance or paid credits. This agent's styles choose scene-card design and visual planning; they are not equivalent to full AI animation generation. 4K export may be possible in FFmpeg, but is intentionally not the default because Android render time, heat, storage and battery can be substantial.

## Install dependencies in Termux
```bash
pkg update
pkg install python ffmpeg -y
python -m pip install --upgrade pip
python -m pip install pillow edge-tts
termux-setup-storage
```
If FFmpeg/Pillow already exist, don't reinstall unless an error asks for it.

## Keep the existing OpenRouter key private
If the environment variable is already set, keep using it. Otherwise in Termux:
```bash
export OPENROUTER_API_KEY='YOUR_KEY_HERE'
```
Replace the placeholder locally; never paste the key into ChatGPT or share screenshots containing it. For persistence, add the export line to `~/.bashrc` (or the shell startup file you actually use) and restart Termux. If a key has ever been shown publicly, revoke it and create a new one.

## Install without deleting old scripts
1. Download/extract this ZIP in Android Downloads.
2. In Termux, allow storage and copy `video_agent.py` into the existing project:
```bash
termux-setup-storage
mkdir -p ~/youtube-agent
cp ~/storage/shared/Download/video_agent.py ~/youtube-agent/video_agent_final.py
```
If Android saves the ZIP in a different folder/name, use the file manager to extract it and adjust only the source path.
3. Run:
```bash
cd ~/youtube-agent
python video_agent_final.py
```

## Workflow
1. Enter a topic.
2. Select a visual style.
3. Select 8 or 10 minute target.
4. Review the full script and scene plan; type YES only if approved.
5. The program generates Hindi narration and scene cards, renders 1080p MP4 or a 4K upscale, optionally mixes `music.mp3`, and asks whether to attach optional Hindi subtitles.
6. It verifies the final file using ffprobe.

Outputs go to:
`~/storage/shared/Movies/YouTubeAgent/`

Projects, script JSON, audio and scene visuals are retained under:
`~/storage/shared/Movies/YouTubeAgent/projects/`

## Optional background music\nCopy a music track you have permission to use to `~/storage/shared/Movies/YouTubeAgent/music.mp3`. The agent mixes it quietly under narration. If that file is absent, the final video has narration only.\n\n## Important notes
- OpenRouter free model availability and quotas can change; a 10-minute video may need retries or a different currently-free text model.
- Edge-TTS requires internet access and its availability is not guaranteed.
- The script creates a target-length plan but narration pace and final duration vary. Check the final duration; a short script can produce a shorter video.
- Optional subtitles are a soft selectable track. In players that support subtitle tracks, they can be turned on/off. They are not burned into the picture.
- The generated local cards are not photorealistic AI visuals. To get genuine 3D/2D cinematic character images, generate/download the images separately and substitute them in the scene visuals before rendering; the current version does not automatically connect a free image-generation API.
