YOUTUBE AGENT V2 — Samsung Galaxy Tab S9 / Termux
=================================================

This is a real upgrade over the previous fallback-card version:
- OpenRouter: generates a longer Hindi script and distinct prompts for 10 scenes.
- Approval gate: script and storyboard must be approved before image generation.
- AI Horde: requests a separate AI-generated 16:9 image for every scene from volunteer workers.
- Edge-TTS: offers four Hindi neural voice choices; narration is slightly slower and audio is loudness-normalized.
- FFmpeg: 1080p video with slow camera motion per scene; optional soft/selectable Hindi subtitle track.
- Optional background music: add a track you have permission to use at:
  ~/storage/shared/Movies/YouTubeAgent/music.mp3

HONEST LIMITATIONS
- AI Horde is a volunteer-powered service. Anonymous requests have lower queue priority and image generation may take a long time or fail. The agent will stop if a scene image fails; it will not pretend generic cards are AI art.
- It creates AI scene images with camera movement, not fully generated continuous 3D animation/video. Real continuous AI video generation is not guaranteed free.
- Output is 1080p. Upscaling a still-image montage to 4K would not create true 4K detail, so this version prioritizes 1080p quality.
- Edge-TTS is an online neural voice service; voice availability can change. The four selectable voices are listed by Microsoft for Hindi; this does not guarantee every voice sounds human to every listener.
- Script length and speaking pace can vary. Always check final duration and listen through the video.

INSTALL
1. Download and extract this ZIP to Android Downloads.
2. In Termux:
   termux-setup-storage
   pkg install python ffmpeg -y
   python -m pip install --upgrade pip
   python -m pip install edge-tts
   mkdir -p ~/youtube-agent
   cp ~/storage/shared/Download/video_agent_v2.py ~/youtube-agent/video_agent_v2.py
3. Ensure your OpenRouter key is available in the Termux environment:
   echo "$OPENROUTER_API_KEY" | head -c 5
   (This prints only the first few characters for a local presence check; do not send that output or your key to anyone.)
   If unset, set it privately in Termux:
   export OPENROUTER_API_KEY='YOUR_KEY_HERE'
   Replace the placeholder locally. Never paste the key into ChatGPT.
4. Run:
   cd ~/youtube-agent
   python video_agent_v2.py

FLOW
- Enter topic.
- Select visual style.
- Select 8 or 10 minutes.
- Select male/female Hindi voice.
- Review full script/storyboard; type YES to approve.
- Wait while distinct AI images are generated, one per scene.
- Wait for narration and FFmpeg render.
- Choose whether to include selectable Hindi subtitles.
- Output is saved under:
  ~/storage/shared/Movies/YouTubeAgent/

AI HORDE ANONYMOUS ACCESS
The code uses the documented anonymous key value for public queue access. Queue times are not guaranteed. An AI Horde account key can improve queue priority if the user chooses to create one, but is not required for this setup. Do not enter a paid key or pay for anything to run the free path.
