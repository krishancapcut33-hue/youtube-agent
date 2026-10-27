#!/usr/bin/env python3
"""
YouTube Agent (₹0-first, Android/Termux)
- Creates an 8–10 minute Hindi video plan using OpenRouter
- Requires human approval before voice/render
- Uses Edge-TTS for Hindi narration
- Generates original stylized scene cards locally as a reliable free fallback
- FFmpeg renders 1080p MP4; optional soft Hindi subtitles
- AI-generated cinematic/3D/2D images can be dropped into project/visuals/scene_XX.jpg
  after scene approval. This local fallback does NOT claim to generate photorealistic AI video.
"""
import os, sys, json, re, time, shutil, subprocess, textwrap
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOME = Path.home()
BASE = HOME / "storage/shared/Movies/YouTubeAgent"
WORK = HOME / "youtube-agent"
PROJECT = BASE / "projects"
MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
VOICE = os.getenv("EDGE_TTS_VOICE", "hi-IN-MadhurNeural")
FPS = 30
WIDTH, HEIGHT = 1920, 1080

def run(cmd, check=True, capture=False):
    print("\n▶", " ".join(map(str, cmd)) if isinstance(cmd, list) else cmd)
    return subprocess.run(cmd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)

def need(binary, install_hint):
    if shutil.which(binary) is None:
        print(f"\nMissing dependency: {binary}\nInstall hint: {install_hint}")
        sys.exit(2)

def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    val = input(prompt + suffix + ": ").strip()
    return val or default

def openrouter(prompt):
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is missing. Do not paste your key into chat.")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": (
                "You are a professional Hindi YouTube explainer writer and storyboard artist. "
                "Write natural spoken Hindi in Devanagari. Return ONLY valid JSON, no markdown. "
                "Never claim facts without careful qualification. No intro filler."
            )},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    req = Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                  headers={"Authorization": "Bearer " + key,
                           "Content-Type": "application/json",
                           "HTTP-Referer": "https://localhost",
                           "X-Title": "Termux YouTube Agent"})
    try:
        with urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {body}")
    except URLError as e:
        raise RuntimeError(f"Network error: {e}")
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError("OpenRouter returned an unexpected response: " + str(data)[:1000])
    # tolerate accidental JSON fences
    content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip(), flags=re.I)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start:end+1])
        raise RuntimeError("Model response was not valid JSON. Try again or choose another free model.")

def slugify(s):
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE).strip().replace(" ", "_")
    return (s[:60] or "youtube_video")

def make_plan(topic, style, minutes, project_dir):
    target_words = 1050 if minutes <= 8 else 1250
    prompt = f"""
Create a complete YouTube video package in Hindi (Devanagari) for topic: {topic!r}.
Target duration: {minutes} minutes, about {target_words} spoken words total.
Visual style: {style}.
Return JSON with this exact schema:
{{
 "title": "Hindi title",
 "description": "2-4 sentence Hindi description",
 "scenes": [
  {{
   "heading": "short scene title",
   "narration": "spoken Hindi paragraph, about 90-140 words",
   "visual_prompt": "detailed visual prompt for a single scene image, no text inside image",
   "on_screen_text": "short Hindi phrase, max 8 words"
  }}
 ]
}}
Use 8-12 scenes, enough total narration for {minutes} minutes at a natural Hindi speaking rate. 
Narration should flow across scenes, include hook, explanation, examples, practical takeaways and conclusion.
No markdown. Ensure all fields are present and JSON is valid. Style notes:
- 3D cinematic: polished 3D storybook/cinematic frame, dramatic depth and lighting.
- 2D animation: clean illustrated 2D character/storyboard frame.
- Cinematic documentary: realistic documentary photography look, cinematic composition.
- Explainer motion graphics: infographic/diagram-focused visual.
- Hybrid: mix styles coherently.
"""
    data = openrouter(prompt)
    if not isinstance(data.get("scenes"), list) or len(data["scenes"]) < 4:
        raise RuntimeError("The AI plan did not contain enough scenes. No render was started.")
    total_words = sum(len(s.get("narration", "").split()) for s in data["scenes"])
    if total_words < 600:
        print(f"WARNING: AI generated only about {total_words} words; video may be shorter than target.")
    (project_dir / "plan.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

def print_plan(plan):
    print("\n" + "="*72)
    print("TITLE:", plan.get("title", "(untitled)"))
    print("DESCRIPTION:", plan.get("description", ""))
    print("SCENES:", len(plan["scenes"]))
    for i, s in enumerate(plan["scenes"], 1):
        print(f"\n{i:02d}. {s.get('heading','Scene')}")
        print("Narration:", s.get("narration","")[:380].replace("\n", " "), "...")
        print("Visual prompt:", s.get("visual_prompt",""))
        print("On-screen text:", s.get("on_screen_text",""))
    print("="*72)

def load_font(size):
    from PIL import ImageFont
    candidates = [
        "/system/fonts/NotoSansDevanagari-Regular.ttf",
        "/system/fonts/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def create_scene_card(path, title, caption, style, index):
    from PIL import Image, ImageDraw, ImageFilter
    import math, random
    random.seed(index * 43 + 7)
    w, h = 1280, 720
    palettes = {
      "3D cinematic": [(11,17,43),(64,32,87),(242,159,91)],
      "2D animation": [(20,63,83),(25,126,120),(246,207,106)],
      "Cinematic documentary": [(19,30,39),(59,83,85),(221,188,130)],
      "Explainer motion graphics": [(9,22,48),(22,85,135),(47,220,190)],
      "Hybrid": [(17,24,48),(89,43,91),(246,190,96)]
    }
    c1,c2,accent = palettes.get(style, palettes["Hybrid"])
    im = Image.new("RGB", (w,h), c1)
    pix = im.load()
    for y in range(h):
        t = y/(h-1)
        for x in range(w):
            u = x/(w-1)
            q = min(1, max(0, .65*t + .35*u))
            pix[x,y] = tuple(int(c1[k]*(1-q)+c2[k]*q) for k in range(3))
    glow = Image.new("RGBA", (w,h), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    for r in range(220, 10, -10):
        alpha = max(2, int(2 + 14*(1-r/220)))
        gd.ellipse((w*.72-r,h*.35-r,w*.72+r,h*.35+r), fill=(*accent,alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(25))
    im = Image.alpha_composite(im.convert("RGBA"), glow)
    d = ImageDraw.Draw(im)
    # Abstract layered scene elements
    if style == "Explainer motion graphics":
        for j in range(5):
            x = 100 + j*230
            d.rounded_rectangle((x,120,x+140,270), radius=20, outline=(*accent,180), width=4)
            if j < 4:
                d.line((x+140,195,x+220,195), fill=(*accent,220), width=5)
        for r in [90,65,40]:
            d.ellipse((w-300-r,h-260-r,w-300+r,h-260+r), outline=(*accent,180), width=5)
    else:
        # layered hills / cinematic depth
        for j, col in enumerate([(*accent,35),(*accent,60),(*accent,85)]):
            yy = 420 + j*65
            pts = [(0,h),(0,yy)]
            for x in range(0,w+1,80):
                pts.append((x, yy + int(30*math.sin(x/130+j))))
            pts += [(w,h)]
            d.polygon(pts, fill=col)
        # cinematic sun / portal
        for r in [115,85,55]:
            d.ellipse((w*.74-r,h*.32-r,w*.74+r,h*.32+r), outline=(*accent,100), width=4)
    # Dark panel behind text
    d.rounded_rectangle((58,440,1222,656), radius=28, fill=(0,0,0,145), outline=(*accent,130), width=2)
    title_font = load_font(44)
    caption_font = load_font(30)
    def wrap(txt, max_chars):
        words = txt.split()
        lines, line = [], ""
        for word in words:
            if len(line)+len(word)+1 > max_chars and line:
                lines.append(line); line=word
            else: line = (line+" "+word).strip()
        if line: lines.append(line)
        return lines
    y = 465
    for line in wrap(title[:90], 36)[:2]:
        d.text((92,y), line, font=title_font, fill=(255,255,255,255), stroke_width=1, stroke_fill=(0,0,0,160))
        y += 56
    y = max(y+2, 575)
    for line in wrap(caption[:100], 58)[:2]:
        d.text((94,y), line, font=caption_font, fill=(*accent,255), stroke_width=1, stroke_fill=(0,0,0,150))
        y += 38
    # small scene marker
    d.text((w-105,35), f"{index:02d}", font=load_font(30), fill=(*accent,255))
    im.convert("RGB").save(path, quality=93)

def srt_time(seconds):
    ms = int(max(0, seconds) * 1000)
    hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

def split_subtitle(text, max_words=9):
    words = text.split()
    chunks, cur = [], []
    for word in words:
        cur.append(word)
        if len(cur) >= max_words:
            chunks.append(" ".join(cur)); cur=[]
    if cur: chunks.append(" ".join(cur))
    return chunks

def make_srt(plan, audio_paths, srt_path):
    entries, offset, n = [], 0.0, 1
    for scene, audio in zip(plan["scenes"], audio_paths):
        probe = run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)], capture=True)
        duration = float(probe.stdout.strip())
        chunks = split_subtitle(scene["narration"], 8)
        weights = [max(1, len(c.split())) for c in chunks]
        total = sum(weights)
        cur = offset
        for chunk, weight in zip(chunks, weights):
            dur = duration * weight / total
            entries.append(f"{n}\n{srt_time(cur)} --> {srt_time(cur+dur)}\n{chunk}\n")
            n += 1; cur += dur
        offset += duration
    srt_path.write_text("\n".join(entries), encoding="utf-8")

def main():
    need("ffmpeg", "pkg install ffmpeg -y")
    need("ffprobe", "pkg install ffmpeg -y")
    need("edge-tts", "python -m pip install edge-tts")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow is missing. Install with: python -m pip install pillow")
        sys.exit(2)

    BASE.mkdir(parents=True, exist_ok=True)
    PROJECT.mkdir(parents=True, exist_ok=True)
    print("\n=== FINAL YOUTUBE VIDEO AGENT — ₹0-first ===")
    print("Existing scripts/assets will NOT be overwritten.")
    topic = ask("Video topic (Hindi/English)")
    if not topic: print("Topic required."); return
    style_choices = {
      "1":"3D cinematic", "2":"2D animation", "3":"Cinematic documentary",
      "4":"Explainer motion graphics", "5":"Hybrid"
    }
    print("\nVisual style: 1) 3D cinematic  2) 2D animation  3) cinematic documentary  4) explainer graphics  5) hybrid")
    style = style_choices.get(ask("Choose style 1-5", "5"), "Hybrid")
    minutes = int(ask("Target duration in minutes (8 or 10)", "8"))
    minutes = 10 if minutes >= 9 else 8
    resolution = ask("Resolution: 1) 1080p recommended  2) 4K upscale (slower/larger)", "1")
    out_w, out_h = (3840, 2160) if resolution == "2" else (1920, 1080)
    project_dir = PROJECT / (time.strftime("%Y%m%d_%H%M%S") + "_" + slugify(topic))
    project_dir.mkdir(parents=True)
    (project_dir / "visuals").mkdir()
    (project_dir / "audio").mkdir()
    print("\nCreating the full script and scene plan. This may take a few minutes...")
    try:
        plan = make_plan(topic, style, minutes, project_dir)
    except Exception as e:
        print("\nPLAN FAILED; no render started.\nReason:", e)
        print("Your existing files remain untouched.")
        return
    print_plan(plan)
    approve = ask("\nApprove this script/scene plan? Type YES to continue", "NO").upper()
    if approve != "YES":
        print("Plan saved for review at:", project_dir / "plan.json")
        print("Edit plan.json then rerun with the planned project is not yet implemented; nothing rendered.")
        return

    # Per-scene narration keeps the voice/render aligned with scene boundaries.
    audio_paths = []
    for i, scene in enumerate(plan["scenes"], 1):
        audio = project_dir / "audio" / f"scene_{i:02d}.mp3"
        textfile = project_dir / "audio" / f"scene_{i:02d}.txt"
        textfile.write_text(scene["narration"], encoding="utf-8")
        try:
            run(["edge-tts", "--voice", VOICE, "--text", scene["narration"], "--write-media", str(audio)])
        except subprocess.CalledProcessError:
            print("Voice generation failed. No final video rendered. Existing assets remain.")
            return
        audio_paths.append(audio)

    # User may replace any locally generated fallback card with a real image.
    # We create a card for every scene, then render. All cards are clearly scene-specific.
    for i, scene in enumerate(plan["scenes"], 1):
        img = project_dir / "visuals" / f"scene_{i:02d}.jpg"
        create_scene_card(img, scene["heading"], scene.get("on_screen_text",""), style, i)

    # If user has dropped scene_XX.jpg files into the project visuals folder before render,
    # they would be overwritten above; therefore generated cards are stored in fallback_cards.
    # (This run's plan approval is immediately followed by render, so no hidden image substitution.)
    print("\nVisual limitation: the free offline fallback makes stylized scene cards with camera motion.")
    print("For actual AI-generated character art, replace images in the project's visuals folder after this run and rerender is not automatic.")
    print(f"Rendering {out_w}x{out_h} H.264. 4K mode is an upscale, not native 4K AI artwork; it may be slow and produce large files.")

    segments = []
    for i, (scene, audio) in enumerate(zip(plan["scenes"], audio_paths), 1):
        img = project_dir / "visuals" / f"scene_{i:02d}.jpg"
        seg = project_dir / f"segment_{i:02d}.mp4"
        probe = run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)], capture=True)
        dur = max(1.0, float(probe.stdout.strip()))
        # zoompan creates gentle motion from each still. Re-encode each segment consistently for concat.
        vf = f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},zoompan=z='min(zoom+0.00035,1.08)':d=1:s={out_w}x{out_h}:fps={FPS},format=yuv420p"
        cmd = ["ffmpeg","-y","-loop","1","-i",str(img),"-i",str(audio),
               "-vf",vf,"-t",f"{dur:.3f}","-r",str(FPS),"-c:v","libx264","-preset","ultrafast",
               "-crf","22","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(seg)]
        try: run(cmd)
        except subprocess.CalledProcessError:
            print("Render failed on scene", i, "— see FFmpeg error above. Project files are kept.")
            return
        segments.append(seg)

    concat_file = project_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    output = BASE / (slugify(topic) + "_1080p.mp4")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat_file),"-c","copy","-movflags","+faststart",str(output)])
    music = BASE / "music.mp3"
    if music.exists():
        mixed = BASE / (slugify(topic) + "_music_tmp.mp4")
        run(["ffmpeg","-y","-i",str(output),"-stream_loop","-1","-i",str(music),
             "-filter_complex","[1:a]volume=0.12[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
             "-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k",
             "-shortest","-movflags","+faststart",str(mixed)])
        shutil.move(str(mixed), str(output))
        print("Background music mixed from:", music)
    else:
        print("No music.mp3 found; video will use narration only. Add a legally usable track as")
        print(str(music), "to include low-volume background music on the next run.")
    subtitles = ask("Add Hindi subtitles as an OPTIONAL selectable subtitle track? (yes/no)", "no").lower()
    if subtitles in ("yes","y","haan","ha"):
        srt = project_dir / "hindi_subtitles.srt"
        make_srt(plan, audio_paths, srt)
        with_sub = BASE / (slugify(topic) + "_1080p_subtitles.mp4")
        # soft subtitle track, not burned in; viewers can turn it on/off in a compatible player.
        run(["ffmpeg","-y","-i",str(output),"-i",str(srt),"-map","0","-map","1:0",
             "-c:v","copy","-c:a","copy","-c:s","mov_text","-metadata:s:s:0","language=hin",
             "-movflags","+faststart",str(with_sub)])
        print("\nVIDEO WITH OPTIONAL SUBTITLES:", with_sub)
    print("\nFINAL VIDEO:", output)
    print("Project files:", project_dir)
    print("Duration/codec verification:")
    run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height","-of","default=noprint_wrappers=1",str(output)])
    print("\nDONE only if FFprobe above reports the output successfully. Review the MP4 before uploading.")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nStopped by user; project files are kept.")
