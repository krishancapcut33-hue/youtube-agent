#!/usr/bin/env python3
"""
YouTube Agent V2 — scene-by-scene AI images + selectable Hindi neural voice.
For Termux on Android. Uses OpenRouter for script/storyboard, AI Horde volunteer
workers for scene images, Edge-TTS for narration, FFmpeg for editing.
No fallback still-card render: if scene image generation fails, it stops rather than
pretending the result is a cinematic video.
"""
import os, sys, json, re, time, shutil, subprocess, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
BASE = HOME / "storage/shared/Movies/YouTubeAgent"
PROJECTS = BASE / "projects"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HORDE_URL = "https://stablehorde.net/api/v2"
MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
FPS = 30

STYLES = {
 "1": ("3D cinematic", "high-end 3D animated feature film still, detailed physically based materials, expressive Indian characters, cinematic composition, dramatic volumetric lighting, rich depth of field"),
 "2": ("2D animation", "premium hand-drawn 2D animation frame, expressive Indian characters, clean linework, detailed painted background, film-quality composition, rich colors"),
 "3": ("Cinematic documentary", "cinematic documentary photograph, realistic Indian locations and people, natural skin texture, grounded lighting, premium documentary color grading"),
 "4": ("Explainer motion graphics", "premium educational explainer visual, elegant 3D infographic objects, layered diagrams, clear visual hierarchy, no readable text, professional motion-design frame"),
 "5": ("Hybrid", "visually rich hybrid of cinematic 3D illustration and premium documentary composition, expressive Indian characters where relevant, dramatic lighting, polished art direction")
}
VOICES = {
 "1": ("hi-IN-MadhurNeural", "Hindi male — Madhur"),
 "2": ("hi-IN-SwaraNeural", "Hindi female — Swara"),
 "3": ("hi-IN-KunalNeural", "Hindi male — Kunal"),
 "4": ("hi-IN-KavyaNeural", "Hindi female — Kavya"),
}

def cmd(args, capture=False, check=True):
    print("\n▶ " + " ".join(map(str,args)))
    return subprocess.run(args, text=True, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, check=check)

def require(name, hint):
    if shutil.which(name) is None:
        print(f"\nDependency missing: {name}\nInstall with: {hint}")
        sys.exit(2)

def ask(prompt, default=""):
    value = input(prompt + (f" [{default}]" if default else "") + ": ").strip()
    return value or default

def slug(s):
    return (re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE).strip().replace(" ","_")[:65] or "youtube_video")

def request_json(url, payload=None, headers=None, timeout=90, method=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    h = {"User-Agent":"TermuxYouTubeAgent/2.0", "Content-Type":"application/json"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type","")
        return json.loads(raw.decode("utf-8")) if "json" in ctype or raw[:1] in (b"{",b"[") else raw

def ask_openrouter(topic, style, minutes):
    key = os.getenv("OPENROUTER_API_KEY","").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this Termux session. Do not paste the key into chat.")
    target_words = 1350 if minutes == 8 else 1650
    style_name = STYLES[style][0]
    prompt = f"""
Create a full Hindi YouTube explainer video package in Devanagari for topic: {topic!r}.
Target runtime {minutes} minutes, aim for approximately {target_words} spoken words total.
Visual style: {style_name}.
Return ONLY valid JSON, no Markdown, exactly this structure:
{{
 "title":"engaging Hindi title",
 "description":"short Hindi description",
 "scenes":[
  {{"heading":"scene heading","narration":"natural spoken Hindi narration paragraph",
    "visual_prompt":"detailed English image-generation prompt for ONE distinct 16:9 image; describe subject, action, setting, composition, lighting, camera angle and visual details; no written text or logos",
    "on_screen_text":"optional short Hindi phrase, max 7 words"}}
 ]
}}
Create 10 scenes with roughly equal narration, aiming for {target_words} words total.
Narration must sound natural when spoken aloud, use short sentences, punctuation and pause-friendly phrasing.
Structure: hook, context, explanation, relatable examples, practical steps, recap and strong ending.
Every scene image must be visually different and illustrate that scene, not generic backgrounds.
Keep character appearance consistent if recurring characters appear. Avoid unsupported factual claims.
"""
    data = request_json(OPENROUTER_URL, {
      "model": MODEL, "temperature":0.65,
      "messages":[
       {"role":"system","content":"You are a professional Hindi documentary writer, explainer producer and storyboard artist. Output valid JSON only."},
       {"role":"user","content":prompt}
      ]
    }, {"Authorization":"Bearer "+key,"HTTP-Referer":"https://localhost","X-Title":"Termux YouTube Agent V2"}, 180)
    content = data["choices"][0]["message"]["content"].strip()
    content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$","",content,flags=re.I)
    try: plan=json.loads(content)
    except json.JSONDecodeError:
        a,b=content.find("{"),content.rfind("}")
        if a<0 or b<=a: raise RuntimeError("Model response was not valid JSON.")
        plan=json.loads(content[a:b+1])
    scenes=plan.get("scenes",[])
    if len(scenes)<8: raise RuntimeError(f"Storyboard has only {len(scenes)} scenes; expected at least 8.")
    words=sum(len(x.get("narration","").split()) for x in scenes)
    if words < 500:
        raise RuntimeError(f"Script too short ({words} words). No rendering started. Rerun and retry the free model.")
    return plan, words

def show_plan(plan, words):
    print("\n"+"="*68)
    print("TITLE:",plan.get("title",""))
    print("Approx spoken words:",words)
    print("SCENES:",len(plan["scenes"]))
    for i,s in enumerate(plan["scenes"],1):
        print(f"\n{i:02d}. {s.get('heading','Scene')}")
        print("Narration:",s.get("narration","")[:280].replace("\n"," "),"…")
        print("Visual:",s.get("visual_prompt","")[:240],"…")
    print("="*68)

def horde_image(prompt, destination, style_text, index, timeout_seconds=600):
    # Anonymous key is supported but has the lowest queue priority. No paid API key is used.
    api_key = os.getenv("AIHORDE_API_KEY","0000000000").strip()
    full_prompt = (style_text + ". " + prompt +
      ". 16:9 widescreen composition, visually coherent frame, detailed foreground and background, cinematic lighting, high quality. "
      "No subtitles, no typography, no watermarks. ### text, watermark, logo, low quality, blurry, deformed hands, duplicate limbs")
    payload = {
      "prompt": full_prompt,
      "params": {"width": 1024, "height": 576, "steps": 25, "n": 1, "cfg_scale": 7.0},
      "nsfw": False, "censor_nsfw": True, "r2": True
    }
    headers = {"apikey":api_key,"Client-Agent":"TermuxYouTubeAgent:2.0:anonymous"}
    data = request_json(HORDE_URL+"/generate/async", payload, headers, 90)
    rid = data.get("id")
    if not rid:
        raise RuntimeError("AI Horde did not return a request ID: "+str(data)[:400])
    print(f"\n[Image {index}] Queued with AI Horde. Request ID: {rid}")
    start=time.time()
    while time.time()-start < timeout_seconds:
        time.sleep(8)
        status=request_json(HORDE_URL+f"/generate/check/{rid}", None, headers, 60, method="GET")
        wait=status.get("wait_time",0)
        queue=status.get("queue_position","?")
        print(f"[Image {index}] waiting={wait}s, queue={queue}, done={status.get('done',False)}")
        if status.get("faulted"):
            raise RuntimeError("AI Horde request faulted. Its volunteer worker may have failed.")
        if status.get("done"):
            result=request_json(HORDE_URL+f"/generate/status/{rid}", None, headers, 90, method="GET")
            gens=result.get("generations",[])
            if not gens: raise RuntimeError("AI Horde marked the image done but returned no image.")
            img_url=gens[0].get("img")
            if not img_url: raise RuntimeError("AI Horde response had no image URL.")
            parsed=urlparse(img_url)
            if parsed.scheme!="https": raise RuntimeError("Refusing non-HTTPS image URL.")
            req=urllib.request.Request(img_url,headers={"User-Agent":"TermuxYouTubeAgent/2.0"})
            with urllib.request.urlopen(req,timeout=120) as resp:
                content=resp.read()
            if not content.startswith(b"\x89PNG") and not content.startswith(b"\xff\xd8") and b"RIFF" not in content[:12]:
                raise RuntimeError("Downloaded result does not look like an image.")
            destination.write_bytes(content)
            return
    raise TimeoutError(f"Image {index} did not finish in {timeout_seconds//60} minutes. No fake fallback will be substituted.")

def srt_time(seconds):
    ms=int(max(0,seconds)*1000); hh,ms=divmod(ms,3600000); mm,ms=divmod(ms,60000); ss,ms=divmod(ms,1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

def make_srt(scenes, audios, path):
    entries=[]; offset=0; n=1
    for scene,audio in zip(scenes,audios):
        r=cmd(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],True)
        dur=float(r.stdout.strip())
        words=scene["narration"].split()
        chunks=[]
        for j in range(0,len(words),8): chunks.append(" ".join(words[j:j+8]))
        weights=[max(1,len(c.split())) for c in chunks]; total=sum(weights); t=offset
        for chunk,w in zip(chunks,weights):
            dt=dur*w/total
            entries.append(f"{n}\n{srt_time(t)} --> {srt_time(t+dt)}\n{chunk}\n")
            n+=1; t+=dt
        offset+=dur
    path.write_text("\n".join(entries),encoding="utf-8")

def main():
    require("ffmpeg","pkg install ffmpeg -y")
    require("ffprobe","pkg install ffmpeg -y")
    require("edge-tts","python -m pip install edge-tts")
    BASE.mkdir(parents=True,exist_ok=True); PROJECTS.mkdir(parents=True,exist_ok=True)
    print("\n=== YOUTUBE AGENT V2 — REAL SCENE IMAGES + VOICE OPTIONS ===")
    print("No old files will be overwritten. Real images are required; no fake still-card fallback.")
    topic=ask("Video topic")
    if not topic: print("Topic is required."); return
    print("\nStyle: 1) 3D cinematic  2) 2D animation  3) cinematic documentary  4) explainer graphics  5) hybrid")
    style=ask("Choose style 1-5","5")
    if style not in STYLES: style="5"
    minutes=10 if int(ask("Target duration: 8 or 10 minutes","10"))>=9 else 8
    print("\nHindi voice: 1) Madhur male  2) Swara female  3) Kunal male  4) Kavya female")
    voice_choice=ask("Choose voice 1-4","1")
    voice=VOICES.get(voice_choice,VOICES["1"])[0]
    print("Selected:",STYLES[style][0], "|", VOICES.get(voice_choice,VOICES["1"])[1], "|", minutes,"min")
    project=PROJECTS/(time.strftime("%Y%m%d_%H%M%S")+"_"+slug(topic)+"_v2")
    (project/"visuals").mkdir(parents=True); (project/"audio").mkdir()
    try:
        print("\nGenerating longer script and scene-by-scene prompts...")
        plan,words=ask_openrouter(topic,style,minutes)
        (project/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
        show_plan(plan,words)
    except Exception as e:
        print("\nSCRIPT/STORYBOARD FAILED:",e)
        print("No rendering started. Project folder:",project)
        return
    approval=ask("\nApprove script and scene plan? Type YES to continue","NO").upper()
    if approval!="YES":
        print("Not rendered. Editable plan saved:",project/"plan.json")
        return
    style_text=STYLES[style][1]
    images=[]
    try:
        print("\nGenerating a DIFFERENT AI image for each scene using AI Horde volunteer workers.")
        print("Anonymous queue may be slow. If image generation fails, the agent stops instead of using one still image.")
        for i,scene in enumerate(plan["scenes"],1):
            path=project/"visuals"/f"scene_{i:02d}.png"
            if path.exists(): raise RuntimeError("Refusing to overwrite an existing image.")
            horde_image(scene.get("visual_prompt",scene.get("heading","scene")),path,style_text,i)
            images.append(path)
    except Exception as e:
        print("\nSCENE IMAGE GENERATION FAILED:",e)
        print("No video was rendered; completed images and plan remain in:",project)
        print("You can rerun later, but this version does not silently replace missing AI images with generic cards.")
        return
    audios=[]
    try:
        print("\nGenerating narration using selected Hindi neural voice:",voice)
        for i,scene in enumerate(plan["scenes"],1):
            a=project/"audio"/f"scene_{i:02d}.mp3"
            txt=scene["narration"].strip()
            # Slightly slower delivery; punctuation in Hindi text gives natural pauses.
            cmd(["edge-tts","--voice",voice,"--rate=-5%","--text",txt,"--write-media",str(a)])
            audios.append(a)
    except Exception as e:
        print("\nVOICE GENERATION FAILED:",e)
        print("AI images are saved; no final video rendered.")
        return
    segments=[]
    for i,(img,audio) in enumerate(zip(images,audios),1):
        probe=cmd(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],True)
        dur=max(1,float(probe.stdout.strip()))
        seg=project/f"segment_{i:02d}.mp4"
        vf=f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.00025,1.08)':d=1:s=1920x1080:fps={FPS},format=yuv420p"
        try:
            cmd(["ffmpeg","-y","-loop","1","-i",str(img),"-i",str(audio),"-vf",vf,"-t",f"{dur:.3f}",
                 "-r",str(FPS),"-c:v","libx264","-preset","ultrafast","-crf","19","-c:a","aac","-b:a","192k",
                 "-af","loudnorm=I=-16:TP=-1.5:LRA=11","-shortest","-movflags","+faststart",str(seg)])
        except subprocess.CalledProcessError:
            print("FFmpeg failed at scene",i,". Project files are retained."); return
        segments.append(seg)
    concat=project/"concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments),encoding="utf-8")
    out=BASE/(slug(topic)+"_V2_1080p.mp4")
    try:
        cmd(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy","-movflags","+faststart",str(out)])
    except subprocess.CalledProcessError:
        print("Final concat failed; segments remain in",project); return
    music=BASE/"music.mp3"
    if music.exists():
        mixed=project/"mixed.mp4"
        try:
            cmd(["ffmpeg","-y","-i",str(out),"-stream_loop","-1","-i",str(music),
                 "-filter_complex","[1:a]volume=0.10[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=3[a]",
                 "-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(mixed)])
            shutil.move(str(mixed),str(out))
        except subprocess.CalledProcessError:
            print("Music mix failed; narration-only video is still available.")
    want_sub=ask("Attach OPTIONAL selectable Hindi subtitle track? yes/no","no").lower() in ("yes","y","haan","ha")
    if want_sub:
        srt=project/"hindi_subtitles.srt"; make_srt(plan["scenes"],audios,srt)
        subout=BASE/(slug(topic)+"_V2_1080p_subtitles.mp4")
        cmd(["ffmpeg","-y","-i",str(out),"-i",str(srt),"-map","0","-map","1:0","-c:v","copy","-c:a","copy",
             "-c:s","mov_text","-metadata:s:s:0","language=hin","-movflags","+faststart",str(subout)])
        print("SUBTITLED VIDEO:",subout)
    print("\nFINAL VIDEO:",out)
    print("Project folder:",project)
    print("\nVerifying actual output...")
    r=cmd(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height","-of","default=noprint_wrappers=1",str(out)],True)
    print(r.stdout)
    print("Review the MP4 visually and listen to the narration before uploading.")
if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled. Existing project files were kept.")
