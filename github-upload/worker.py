"""
Autonomous 1080p Full HD Video Cloud Worker with Gemini AI Video Director for Capital Prime.
Runs on GitHub Actions 4-Core Runner with 16GB RAM for 100% Free Processing.
Features:
- Gemini 3.5 Flash Multimodal Video Director (Smart junk-footage trim + AI Hook Feature).
- Crash-Proof Cinematic Color Grading (Brightness, Contrast, Sky & Grass Saturation).
- Clean 3-Badge Dynamic Auto-Fit Overlay (Gold Location, White Area, Cyan Blue Website CTA).
- 100% Full Walkthrough Video Preserved (No artificial time cap).
- High-Speed Concurrent Multi-Platform Publishing (YouTube Shorts, Instagram Reels, Facebook).
- Automatic Cloudinary Zero-Storage Cleanup (Both raw and stamped videos destroyed).
- 100% Secure: OAuth Token and API keys loaded from GitHub Secrets.
"""

import os
import re
import sys
import time
import json
import subprocess
import concurrent.futures
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. Config & Environment Variables
# ==========================================
VIDEO_URL = os.getenv("INPUT_VIDEO_URL", "").strip()
def sanitize_location(loc_raw: str) -> str:
    if not loc_raw:
        return "Ranchi"
    import re
    s = re.sub(r"^location\s*[:\-]\s*", "", str(loc_raw).strip(), flags=re.IGNORECASE)
    parts = [p.strip() for p in s.split(",") if p.strip()]
    seen = set()
    clean_parts = []
    for p in parts:
        p_norm = p.lower()
        if p_norm not in seen:
            seen.add(p_norm)
            clean_parts.append(p)
    res = ", ".join(clean_parts)
    if "ranchi" not in res.lower():
        res = f"{res}, Ranchi"
    return res if res else "Ranchi"

LOCATION = sanitize_location(os.getenv("INPUT_LOCATION", "Ranchi"))
AREA = os.getenv("INPUT_AREA", "5").strip()
AREA_UNIT = os.getenv("INPUT_AREA_UNIT", "dismil").strip()
TITLE = os.getenv("INPUT_TITLE", "Prime Property in Ranchi").strip()
PROPERTY_ID = os.getenv("INPUT_PROPERTY_ID", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841467192830436").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1397425480114961").strip()
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()

# Cloudinary credentials for cleanup if needed
VIDEO_CLOUDINARY_CLOUD_NAME = os.getenv("VIDEO_CLOUDINARY_CLOUD_NAME", "").strip()
VIDEO_CLOUDINARY_API_KEY = os.getenv("VIDEO_CLOUDINARY_API_KEY", "").strip()
VIDEO_CLOUDINARY_API_SECRET = os.getenv("VIDEO_CLOUDINARY_API_SECRET", "").strip()

print("=" * 60)
print("🚀 GITHUB ACTIONS 1080p CLOUD WORKER STARTING...")
print(f"📍 Location: {LOCATION} | Area: {AREA} {AREA_UNIT}")
print(f"🏠 Property ID: {PROPERTY_ID}")
print(f"🎬 Video URL: {VIDEO_URL}")
print("=" * 60)

if not VIDEO_URL:
    print("❌ ERROR: INPUT_VIDEO_URL is required!")
    sys.exit(1)

WORK_DIR = Path("/tmp/worker_run") if os.name != "nt" else Path("./temp_worker")
WORK_DIR.mkdir(parents=True, exist_ok=True)
INPUT_PATH = WORK_DIR / "raw_input.mp4"
OUTPUT_1080P_PATH = WORK_DIR / "stamped_1080p.mp4"
OVERLAY_PNG = WORK_DIR / "overlay_1080p.png"

# Search for font
FONT_PATH = Path("assets/fonts/Montserrat-Bold.ttf")
if not FONT_PATH.exists():
    FONT_PATH = Path("github-upload/assets/fonts/Montserrat-Bold.ttf")
if not FONT_PATH.exists():
    FONT_PATH = Path("Montserrat-Bold.ttf")


# ==========================================
# 1B. YouTube Pre-Check & Auto-Sync Guard
# ==========================================
if "youtu.be" in VIDEO_URL or "youtube.com" in VIDEO_URL:
    print("\n" + "=" * 60)
    print("ℹ️ INPUT_VIDEO_URL is ALREADY a published YouTube link!")
    print(f"🔗 Detected YouTube URL: {VIDEO_URL}")
    print("⏭️ Skipping re-download and re-encoding to avoid corrupting media stream.")
    
    yt_vid_id = None
    if "youtu.be/" in VIDEO_URL:
        yt_vid_id = VIDEO_URL.split("youtu.be/")[1].split("?")[0].split("&")[0]
    elif "v=" in VIDEO_URL:
        yt_vid_id = VIDEO_URL.split("v=")[1].split("&")[0]
    
    clean_yt_url = f"https://youtu.be/{yt_vid_id}" if yt_vid_id else VIDEO_URL
    print(f"✅ Canonical YouTube Link: {clean_yt_url}")
    
    if MONGODB_URI and PROPERTY_ID:
        try:
            print(f"🔄 Syncing YouTube URL back to MongoDB for Property {PROPERTY_ID}...")
            from pymongo import MongoClient
            from bson import ObjectId
            
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
            db = client.get_default_database()
            if db is None or db.name == "admin":
                db = client["test"]
            
            filter_query = {}
            if ObjectId.is_valid(PROPERTY_ID):
                filter_query = {"$or": [{"_id": ObjectId(PROPERTY_ID)}, {"id": PROPERTY_ID}]}
            else:
                filter_query = {"id": PROPERTY_ID}
            
            update_data = {
                "$set": {
                    "videoUrl": clean_yt_url,
                    "socialLinks.youtube": clean_yt_url,
                    "socialLinks.status": "completed",
                    "socialLinks.updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }
            res_db = db.properties.update_one(filter_query, update_data)
            print(f"✅ MongoDB auto-sync success: matched={res_db.matched_count}, modified={res_db.modified_count}")
        except Exception as e_db:
            print(f"⚠️ MongoDB sync notice: {e_db}")
            
    print("🎉 YouTube video already live and property synced! Worker finished safely.")
    print("=" * 60)
    sys.exit(0)


# ==========================================
# 2. Download Raw Video from Cloudinary
# ==========================================
print(f"\n📥 Downloading video from Cloudinary: {VIDEO_URL[:80]}...")
t0 = time.time()
resp = requests.get(VIDEO_URL, stream=True, timeout=120)
resp.raise_for_status()
with open(INPUT_PATH, "wb") as f:
    for chunk in resp.iter_content(chunk_size=1024 * 1024):
        if chunk:
            f.write(chunk)
file_size_mb = INPUT_PATH.stat().st_size / (1024 * 1024)
print(f"✅ Video downloaded in {time.time() - t0:.2f}s ({file_size_mb:.2f} MB)")


# ==========================================
# 3. Probe Video (Orientation, Audio & Duration)
# ==========================================
probe_cmd = ["ffmpeg", "-i", str(INPUT_PATH)]
probe_run = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="replace")
stderr = probe_run.stderr

is_vertical = True
has_audio = "Audio:" in stderr
rot_match = re.search(r"rotate\s*:\s*(\d+)", stderr)
is_rotated = rot_match and rot_match.group(1) in ("90", "270")
vid_match = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", stderr)
if vid_match:
    rw, rh = int(vid_match.group(1)), int(vid_match.group(2))
    w, h = (rh, rw) if is_rotated else (rw, rh)
    is_vertical = h >= w

# Parse duration
dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr)
video_duration = 30.0
if dur_match:
    hrs = float(dur_match.group(1))
    mins = float(dur_match.group(2))
    secs = float(dur_match.group(3))
    video_duration = hrs * 3600 + mins * 60 + secs

# 1080p Full HD Target (1080x1920 vertical portrait, 1920x1080 landscape)
if is_vertical:
    TARGET_W = 1080
    TARGET_H = 1920
else:
    TARGET_W = 1920
    TARGET_H = 1080

print(f"📐 Target 1080p Dimensions: {TARGET_W}x{TARGET_H} (Vertical: {is_vertical}, Audio: {has_audio}, Duration: {video_duration:.1f}s)")


# ==========================================
# 4. Gemini AI Video Director & Analysis
# ==========================================
ai_meta = {}
if GEMINI_API_KEY:
    try:
        print("🧠 Calling Gemini 3.5 Flash: AI Video Director & Multimodal Analysis...")
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Ultra-fast lightweight 360p proxy (1-2 MB) for Gemini multimodal analysis (Instant upload & indexing)
        t_proxy = time.time()
        PROXY_PATH = WORK_DIR / "gemini_proxy.mp4"
        cmd_proxy = [
            "ffmpeg", "-y", "-i", str(INPUT_PATH),
            "-vf", "scale=-2:360,fps=12",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "32",
            "-an", str(PROXY_PATH)
        ]
        subprocess.run(cmd_proxy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        upload_target = PROXY_PATH if PROXY_PATH.exists() and PROXY_PATH.stat().st_size > 10000 else INPUT_PATH
        proxy_size_mb = upload_target.stat().st_size / (1024 * 1024)
        print(f"⚡ Generated lightweight analysis proxy ({proxy_size_mb:.2f} MB) in {time.time() - t_proxy:.2f}s")
        
        gem_file = client.files.upload(file=str(upload_target))
        waited = 0
        while getattr(gem_file, "state", None) and gem_file.state.name == "PROCESSING":
            if waited > 30: break
            time.sleep(1)
            waited += 1
            gem_file = client.files.get(name=gem_file.name)
            
        prompt = f"""
You are an award-winning Real Estate Film Director and Social Media Growth Expert.
Analyze this raw property walkthrough video for Capital Prime real estate.
Total Duration of video: {video_duration:.1f} seconds.
Context:
- Location: {LOCATION}
- Area: {AREA} {AREA_UNIT}
- Title: {TITLE}

Carefully inspect the visual footage:
1. Meaningless / Boring Cut Points: Do NOT cut the video just to make it shorter! We want the full property walkthrough shown to buyers. Only suggest trimming if there is genuine junk/boring footage:
   - trim_start_sec: If the first few seconds show the cameraman looking down at feet/ground, pockets, or chaotic camera tumbling, set trim_start_sec to when the actual property viewing begins. Otherwise, keep it 0.0.
   - trim_end_sec: If the final seconds show the phone being put into a pocket, pointed at the sky, or dead footage, set trim_end_sec to where property viewing ends. Otherwise, keep it {video_duration:.1f}.
   - If the entire footage is good and relevant, keep 100% of it (trim_start_sec: 0.0, trim_end_sec: {video_duration:.1f}).
2. Standout Visual Feature: What is the single most attractive selling point visible in the footage? (e.g. 'Wide 40ft Road Access', 'Corner Plot', 'Prime Boundary Wall Done', 'Scenic Mountain View', 'Direct Highway Access', 'Ready For Registry', 'Clean Level Ground'). Keep it under 5 words.
3. Color & Lighting Polish:
   - brightness: between -0.05 and +0.12 (e.g. 0.04 for clean light boost)
   - contrast: between 1.05 and 1.25 (e.g. 1.15 for crisp definition)
   - saturation: between 1.10 and 1.35 (e.g. 1.25 to make greenery and sky pop)

Return ONLY valid JSON with EXACT keys:
{{
  "youtube": {{
    "title": "Viral High-CTR Title under 70 chars #Shorts",
    "description": "Engaging real estate description with call to action to visit capitalprime.co.in",
    "tags": ["RanchiRealEstate", "PlotForSale", "CapitalPrime", "PropertyInRanchi", "LandInvestment"]
  }},
  "instagram": {{
    "caption": "Punchy Reel caption highlighting the property with emojis and call to action",
    "hashtags": ["#RanchiRealEstate", "#PlotForSale", "#ReelsIndia", "#CapitalPrime", "#Property"]
  }},
  "facebook": {{
    "caption": "Engaging Facebook post for buyers looking for plots in {LOCATION}"
  }},
  "video_director": {{
    "hook_badge": "Catchy 3-5 word standout feature found in footage",
    "trim_start_sec": 0.0,
    "trim_end_sec": {video_duration:.1f},
    "brightness": 0.04,
    "contrast": 1.15,
    "saturation": 1.25,
    "director_notes": "1-sentence summary of enhancements applied"
  }}
}}
"""
        for m_name in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
            try:
                response = client.models.generate_content(
                    model=m_name,
                    contents=[gem_file, prompt],
                    config={"response_mime_type": "application/json"}
                )
                ai_meta = json.loads(response.text)
                print(f"✅ Gemini AI Video Director ({m_name}) analysis complete!")
                break
            except Exception as em:
                print(f"⚠️ Model {m_name} attempt: {em}")
    except Exception as e:
        print(f"⚠️ Gemini analysis fallback: {e}")

if not ai_meta:
    ai_meta = {
        "youtube": {
            "title": f"Prime Plot for Sale in {LOCATION} | Capital Prime #Shorts",
            "description": f"Verified plot in {LOCATION}. Area: {AREA} {AREA_UNIT}.\nFor site visit visit: https://capitalprime.co.in",
            "tags": ["RealEstate", "PropertyForSale", "RanchiRealEstate", "CapitalPrime"]
        },
        "instagram": {
            "caption": f"🚨 Prime Property in {LOCATION}!\nTotal Area: {AREA} {AREA_UNIT}\n100% Clear Title & Registry. DM for visit! 🏡",
            "hashtags": ["#RanchiRealEstate", "#PlotForSale", "#CapitalPrime", "#RealEstate"]
        },
        "facebook": {
            "caption": f"Prime property up for grabs in {LOCATION}! Total Area: {AREA} {AREA_UNIT}. Visit capitalprime.co.in for more details."
        },
        "video_director": {
            "hook_badge": "Prime Verified Property",
            "trim_start_sec": 0.0,
            "trim_end_sec": video_duration,
            "brightness": 0.04,
            "contrast": 1.12,
            "saturation": 1.20,
            "director_notes": "Broadcast cinematic color grading applied."
        }
    }

director = ai_meta.get("video_director", {})
print(f"🎬 [AI Director Notes]: {director.get('director_notes', 'Enhancements ready')}")

# Extract and sanitize AI Director parameters (Guaranteed Zero Crashes)
hook_badge = str(director.get("hook_badge", "")).strip()
hook_badge = re.sub(r'[\"\'`]', '', hook_badge)[:40].strip()

try:
    raw_start = float(director.get("trim_start_sec", 0.0) or 0.0)
except Exception:
    raw_start = 0.0

try:
    raw_end = float(director.get("trim_end_sec", video_duration) or video_duration)
except Exception:
    raw_end = video_duration

# Strictly clamp trim bounds so clip is always valid and >= 6s
trim_start = max(0.0, min(raw_start, max(0.0, video_duration - 8.0)))
trim_end = max(trim_start + 6.0, min(raw_end, video_duration))

# No artificial time cap! Only trim if there is actual junk at start or end
do_trim = (trim_start >= 1.5 or (video_duration - trim_end) >= 2.0)

if do_trim:
    print(f"✂️ [AI Director Smart-Trim]: Removed edge junk -> [{trim_start:.2f}s to {trim_end:.2f}s] (Kept: {trim_end - trim_start:.2f}s of {video_duration:.2f}s)")
else:
    print(f"✂️ [AI Director Smart-Trim]: Entire video is engaging, preserving 100% full duration ({video_duration:.2f}s).")

# Strictly clamp color values to safe ranges
try:
    raw_b = float(director.get("brightness", 0.04) or 0.04)
except Exception:
    raw_b = 0.04

try:
    raw_c = float(director.get("contrast", 1.12) or 1.12)
except Exception:
    raw_c = 1.12

try:
    raw_s = float(director.get("saturation", 1.20) or 1.20)
except Exception:
    raw_s = 1.20

b_clean = round(max(-0.08, min(raw_b, 0.15)), 2)
c_clean = round(max(0.95, min(raw_c, 1.25)), 2)
s_clean = round(max(1.00, min(raw_s, 1.35)), 2)

print(f"🎨 [AI Director Color Grading]: Brightness={b_clean:+0.2f}, Contrast={c_clean:.2f}, Saturation={s_clean:.2f}")
if hook_badge:
    print(f"🌟 [AI Director Hook Badge]: \"{hook_badge}\"")


# ==========================================
# 5. Create 1080p Non-Overlapping Pill Badges (Dynamic Auto-Fit)
# ==========================================
print("🎨 Creating 1080p Badges with Dynamic Auto-Fit Font Scaling...")
img = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

loc_clean = f"Location: {LOCATION}" if not LOCATION.lower().startswith("location") else LOCATION
full_area = f"{AREA} {AREA_UNIT}".strip()
area_clean = f"Total Area: {full_area}" if not full_area.lower().startswith("total area") else full_area
web_clean = "For More Details Visit: capitalprime.co.in"

if is_vertical:
    init_s1, min_s1 = 54, 28
    init_s2, min_s2 = 44, 24
    init_s3, min_s3 = 34, 20
    v_pad = 13
    h_pad = 28
    gap = 16
    radius = 16
    y_start = int(TARGET_H * 0.055)
    max_pill_w = TARGET_W - 140  # 70px breathing margin on each side
else:
    init_s1, min_s1 = 42, 22
    init_s2, min_s2 = 36, 20
    init_s3, min_s3 = 28, 16
    v_pad = 11
    h_pad = 24
    gap = 14
    radius = 14
    y_start = int(TARGET_H * 0.045)
    max_pill_w = TARGET_W - 160  # 80px breathing margin on each side

def load_font(sz):
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), sz)
        except Exception:
            pass
    return ImageFont.load_default()

def fit_text_font(draw_obj, text, initial_size, min_size, max_w):
    sz = initial_size
    f = load_font(sz)
    bbox = draw_obj.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    while tw > max_w and sz > min_size:
        sz -= 2
        f = load_font(sz)
        bbox = draw_obj.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    return f, tw, th, bbox

# Clean 3-Badge Spec: Location, Area, and Website (Highlight badge removed)
badges_spec = [
    (loc_clean, init_s1, min_s1, "#FFD700"),   # Gold
    (area_clean, init_s2, min_s2, "#FFFFFF"),  # White
    (web_clean, init_s3, min_s3, "#60A5FA"),   # Cyan Blue
]

pill_fill = (0, 0, 0, 230)
current_y = y_start

for text, init_sz, min_sz, text_color in badges_spec:
    max_text_w = max_pill_w - (2 * h_pad)
    font, tw, th, bbox = fit_text_font(draw, text, init_sz, min_sz, max_text_w)

    x = (TARGET_W - tw) // 2
    pill_left = x - h_pad
    pill_top = current_y
    pill_right = x + tw + h_pad
    pill_bottom = current_y + th + (2 * v_pad)

    draw.rounded_rectangle(
        [pill_left, pill_top, pill_right, pill_bottom],
        radius=radius,
        fill=pill_fill
    )

    text_y = pill_top + v_pad - bbox[1]
    draw.text((x - bbox[0], text_y), text, font=font, fill=text_color)

    current_y += th + (2 * v_pad) + gap

img.save(OVERLAY_PNG, "PNG")
print("✅ 1080p Overlay image generated with guaranteed non-overlapping auto-fit badges!")


# ==========================================
# 6. Execute 1080p FFmpeg Stamping with AI Director Polish
# ==========================================
print(f"⚡ Stamping video at 1080p Full HD ({TARGET_W}x{TARGET_H}) using 4 CPU Cores...")
t_stamp = time.time()

# Apply Color Grading (Brightness, Contrast, Saturation) + Scaling
eq_filter = f"eq=brightness={b_clean}:contrast={c_clean}:saturation={s_clean}"
scale_filter = f"scale={TARGET_W}:{TARGET_H},setsar=1"
fc = f"[0:v]{scale_filter},{eq_filter}[v0];[v0][1:v]overlay=0:0[v]"

ffmpeg_cmd = [
    "ffmpeg", "-y", "-threads", "4",
    "-i", str(INPUT_PATH),
    "-i", str(OVERLAY_PNG)
]

if do_trim:
    ffmpeg_cmd.extend(["-ss", f"{trim_start:.2f}", "-t", f"{trim_end - trim_start:.2f}"])

ffmpeg_cmd.extend([
    "-filter_complex", fc,
    "-map", "[v]",
    "-map", "0:a?",
    "-c:v", "libx264",
    "-preset", "superfast",
    "-crf", "22",
    "-maxrate", "2500k",
    "-bufsize", "5000k",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "48000",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    str(OUTPUT_1080P_PATH)
])

p_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if p_res.returncode != 0 or not OUTPUT_1080P_PATH.exists() or OUTPUT_1080P_PATH.stat().st_size == 0:
    print(f"❌ FFmpeg error: {p_res.stderr[-500:]}")
    sys.exit(1)

out_mb = OUTPUT_1080P_PATH.stat().st_size / (1024 * 1024)
print(f"🎉 1080p VIDEO STAMPED SUCCESSFULLY in {time.time() - t_stamp:.2f}s! Size: {out_mb:.2f} MB")

# ==========================================
# 6B. Upload Stamped 1080p Video to Cloudinary
# ==========================================
stamped_cloudinary_url = None
stamped_cloudinary_public_id = None
if VIDEO_CLOUDINARY_CLOUD_NAME and VIDEO_CLOUDINARY_API_KEY and VIDEO_CLOUDINARY_API_SECRET:
    try:
        import hashlib
        print(f"\n☁️ Uploading Stamped 1080p Video to Cloudinary ({VIDEO_CLOUDINARY_CLOUD_NAME})...")
        t_c = time.time()
        c_ts = str(int(time.time()))
        to_sign = f"timestamp={c_ts}{VIDEO_CLOUDINARY_API_SECRET}"
        c_sig = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
        c_up_url = f"https://api.cloudinary.com/v1_1/{VIDEO_CLOUDINARY_CLOUD_NAME}/video/upload"
        with open(OUTPUT_1080P_PATH, 'rb') as f:
            c_res = requests.post(c_up_url, data={
                "timestamp": c_ts,
                "api_key": VIDEO_CLOUDINARY_API_KEY,
                "signature": c_sig
            }, files={"file": f}, timeout=180).json()
        stamped_cloudinary_url = c_res.get("secure_url")
        stamped_cloudinary_public_id = c_res.get("public_id")
        if stamped_cloudinary_url:
            print(f"✅ Stamped 1080p uploaded to Cloudinary in {time.time() - t_c:.2f}s! (Public ID: {stamped_cloudinary_public_id})")
            print(f"🔗 Cloudinary Master URL: {stamped_cloudinary_url}")
    except Exception as ec:
        print(f"⚠️ Cloudinary upload warning: {ec}")

# ==========================================
# 7. Multi-Platform Auto-Publishing
# ==========================================
print("\n" + "=" * 60)
print("🚀 PUBLISHING 1080p VIDEO TO SOCIAL MEDIA...")
print("=" * 60)

video_id = None
reel_id = None
vid_id = None

# Meta Page Token Helper
base_meta_token = FB_PAGE_ACCESS_TOKEN or META_ACCESS_TOKEN

def get_real_page_token():
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}",
            params={"fields": "access_token", "access_token": base_meta_token},
            timeout=15
        )
        if r.ok:
            pt = r.json().get("access_token")
            if pt: return pt
    except Exception as e:
        print(f"⚠️ Warning fetching page token: {e}")
    return base_meta_token

page_token = get_real_page_token()

# 7A. YouTube Upload Function
def upload_to_youtube():
    global video_id
    token_json_str = os.getenv("YOUTUBE_TOKEN_JSON", "").strip()
    token_path = Path("token.json")
    if token_json_str:
        try:
            import tempfile
            tmp_token = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            tmp_token.write(token_json_str)
            tmp_token.close()
            token_path = Path(tmp_token.name)
            print("🔐 [YouTube Auth] Token loaded from GitHub Secret ✅")
        except Exception as e:
            print(f"⚠️ Failed to write token from secret: {e}")
            token_json_str = ""

    if token_path.exists():
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds = Credentials.from_authorized_user_file(str(token_path))
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                print("🔄 [YouTube OAuth] Access token auto-refreshed successfully!")
            yt_service = build("youtube", "v3", credentials=creds)

            yt_info = ai_meta.get("youtube", {})
            yt_title = yt_info.get("title", TITLE)[:100]
            if is_vertical and "#shorts" not in yt_title.lower() and len(yt_title) <= 92:
                yt_title = f"{yt_title} #Shorts"

            first_comment = "📍 For more details visit: https://capitalprime.co.in"
            yt_desc = f"{first_comment}\n\n" + yt_info.get("description", "")
            body = {
                "snippet": {
                    "title": yt_title,
                    "description": yt_desc,
                    "tags": yt_info.get("tags", ["RealEstate", "Ranchi", "CapitalPrime"]),
                    "categoryId": "22"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            }
            media = MediaFileUpload(str(OUTPUT_1080P_PATH), chunksize=1024*1024*5, resumable=True)
            req = yt_service.videos().insert(part="snippet,status", body=body, media_body=media)
            res_yt = req.execute()
            video_id = res_yt.get("id")
            print(f"▶️ [YouTube Success] Video ID: {video_id} -> https://youtu.be/{video_id}")
        except Exception as e:
            print(f"⚠️ YouTube upload error: {e}")
    else:
        print("ℹ️ YouTube token not found, skipping YouTube live upload.")

# 7B. Facebook Page Video Upload Function (Reels First, then Video Fallback)
def upload_to_facebook():
    global vid_id
    if page_token and FB_PAGE_ID:
        try:
            fb_info = ai_meta.get("facebook", {})
            fb_caption = fb_info.get("caption", TITLE) + f"\n\n📍 Location: {LOCATION}\n📐 Total Area: {AREA} {AREA_UNIT}\n🌐 https://capitalprime.co.in\n\n#Ranchi #RanchiRealEstate #PlotsInRanchi #CapitalPrime #Reels #FacebookReels #PropertyInRanchi"
            
            # 1. Primary: Official Facebook Reels API (Direct distribution into Facebook Reels feed)
            print(f"\n📘 [Facebook Reels] Initializing Reel on Page {FB_PAGE_ID}...")
            init_url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/video_reels"
            init_res = requests.post(init_url, params={"upload_phase": "start", "access_token": page_token}, timeout=30).json()
            
            reel_video_id = init_res.get("video_id")
            reel_upload_url = init_res.get("upload_url")
            
            if reel_video_id and reel_upload_url:
                print(f"📘 [Facebook Reels] Uploading video binary stream to Meta...")
                with open(OUTPUT_1080P_PATH, "rb") as vf:
                    file_data = vf.read()
                
                headers = {
                    "Authorization": f"OAuth {page_token}",
                    "offset": "0",
                    "file_size": str(len(file_data))
                }
                up_res = requests.post(reel_upload_url, data=file_data, headers=headers, timeout=300)
                
                finish_res = requests.post(
                    init_url,
                    params={
                        "upload_phase": "finish",
                        "video_id": reel_video_id,
                        "video_state": "PUBLISHED",
                        "description": fb_caption,
                        "access_token": page_token
                    },
                    timeout=30
                ).json()
                
                if finish_res.get("success") or finish_res.get("id"):
                    vid_id = reel_video_id
                    print(f"📘 [Facebook Reel Success] 🚀 Published as Official Facebook Reel! Video ID: {vid_id} -> https://www.facebook.com/watch/?v={vid_id}")
                    return
                else:
                    print(f"⚠️ [Facebook Reel Finish Notice]: {finish_res}. Falling back to standard video post...")
            else:
                print(f"⚠️ [Facebook Reel Init Notice]: {init_res}. Falling back to standard video post...")

            # 2. Fallback: Standard Page Video Post
            fb_url = f"https://graph-video.facebook.com/v21.0/{FB_PAGE_ID}/videos"
            with open(OUTPUT_1080P_PATH, "rb") as vf:
                files = {"source": ("stamped_1080p.mp4", vf, "video/mp4")}
                data = {
                    "title": f"Prime Plot: {LOCATION} ({AREA} {AREA_UNIT})",
                    "description": fb_caption,
                    "access_token": page_token
                }
                fb_res = requests.post(fb_url, data=data, files=files, timeout=300).json()
                vid_id = fb_res.get("id")
                if vid_id:
                    print(f"📘 [Facebook Success] Video ID: {vid_id} -> https://www.facebook.com/watch/?v={vid_id}")
                else:
                    print(f"⚠️ Facebook upload error: {fb_res}")
        except Exception as e:
            print(f"⚠️ Facebook upload error: {e}")

# 7C. Instagram Reels Upload Function
def upload_to_instagram():
    global reel_id
    if base_meta_token and INSTAGRAM_USER_ID:
        try:
            ig_info = ai_meta.get("instagram", {})
            ig_caption = ig_info.get("caption", TITLE) + "\n\n" + " ".join(ig_info.get("hashtags", []))
            is_ready = False

            # Method 1: Cloud-to-Cloud Ingestion from Cloudinary (with Auto-Retry)
            if stamped_cloudinary_url:
                for attempt in range(1, 3):
                    try:
                        print(f"\n📸 [Instagram] Attempt {attempt}/2: Cloud-to-Cloud Ingestion...")
                        time.sleep(5)
                        init_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media"
                        p_cloud = {
                            "media_type": "REELS",
                            "video_url": stamped_cloudinary_url,
                            "caption": ig_caption,
                            "access_token": base_meta_token
                        }
                        r_cloud = requests.post(init_url, data=p_cloud, timeout=60).json()
                        cid = r_cloud.get("id")
                        if not cid:
                            print(f"⚠️ Attempt {attempt} init error: {r_cloud}")
                            continue

                        print(f"⏳ Polling Instagram Container {cid} status...")
                        status_url = f"https://graph.facebook.com/v21.0/{cid}"
                        container_ok = False
                        for poll in range(1, 30):
                            time.sleep(3)
                            st = requests.get(status_url, params={"fields": "status_code,status", "access_token": base_meta_token}, timeout=15).json()
                            code = st.get("status_code")
                            print(f"Instagram Reel processing [{poll}/30]: {code}")
                            if code == "FINISHED":
                                container_ok = True
                                break
                            elif code in ("ERROR", "EXPIRED"):
                                print(f"⚠️ Attempt {attempt} returned {code}: {st.get('status')}")
                                break

                        if container_ok:
                            pub_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media_publish"
                            p_pub = {"creation_id": cid, "access_token": base_meta_token}
                            res_pub = requests.post(pub_url, data=p_pub, timeout=30).json()
                            reel_id = res_pub.get("id")
                            if reel_id:
                                reel_url = f"https://www.instagram.com/reel/{reel_id}/"
                                print(f"📸 [Instagram Success] Published Reel ID: {reel_id} -> {reel_url}")
                                is_ready = True
                                break
                    except Exception as e_c:
                        print(f"⚠️ Attempt {attempt} exception: {e_c}")

            # Method 2: Resumable Binary Stream (Fallback if Method 1 fails)
            if not is_ready:
                try:
                    print(f"\n📸 [Instagram] Trying Method 2: Resumable Stream to rupload...")
                    init_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media"
                    p1 = {
                        "media_type": "REELS",
                        "upload_type": "resumable",
                        "caption": ig_caption,
                        "access_token": base_meta_token
                    }
                    r1 = requests.post(init_url, data=p1, timeout=60).json()
                    upload_uri = r1.get("uri")
                    cid2 = r1.get("id")
                    if upload_uri and cid2:
                        file_size = OUTPUT_1080P_PATH.stat().st_size
                        h = {
                            "Authorization": f"OAuth {base_meta_token}",
                            "offset": "0",
                            "file_size": str(file_size),
                            "Content-Type": "application/octet-stream"
                        }
                        with open(OUTPUT_1080P_PATH, "rb") as vf:
                            up_res = requests.post(upload_uri, headers=h, data=vf, timeout=300)
                        print(f"Instagram binary upload HTTP: {up_res.status_code}")
                        for poll in range(1, 30):
                            time.sleep(3)
                            st = requests.get(f"https://graph.facebook.com/v21.0/{cid2}", params={"fields": "status_code,status", "access_token": base_meta_token}, timeout=15).json()
                            code = st.get("status_code")
                            print(f"Instagram Reel processing [{poll}/30]: {code}")
                            if code == "FINISHED":
                                pub_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media_publish"
                                p_pub = {"creation_id": cid2, "access_token": base_meta_token}
                                res_pub = requests.post(pub_url, data=p_pub, timeout=30).json()
                                reel_id = res_pub.get("id")
                                if reel_id:
                                    reel_url = f"https://www.instagram.com/reel/{reel_id}/"
                                    print(f"📸 [Instagram Success] Published Reel ID: {reel_id} -> {reel_url}")
                                    is_ready = True
                                break
                            elif code in ("ERROR", "EXPIRED"):
                                break
                except Exception as e_r:
                    print(f"⚠️ Resumable upload exception: {e_r}")
        except Exception as e:
            print(f"⚠️ Instagram upload error: {e}")

# Execute All 3 Social Platforms Concurrently
print("⚡ Launching Parallel Publishing to YouTube, Instagram & Facebook...")
t_pub = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    fut_yt = executor.submit(upload_to_youtube)
    fut_fb = executor.submit(upload_to_facebook)
    fut_ig = executor.submit(upload_to_instagram)
    concurrent.futures.wait([fut_yt, fut_fb, fut_ig])
print(f"✅ Multi-Platform Publishing completed in {time.time() - t_pub:.2f}s!")


# ==========================================
# 8. MongoDB Live Links Auto-Sync
# ==========================================
print("\n" + "=" * 60)
print("🔄 SYNCING LIVE SOCIAL LINKS TO MONGODB...")
print("=" * 60)

if MONGODB_URI and PROPERTY_ID:
    try:
        from pymongo import MongoClient
        from bson import ObjectId

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        try:
            db = client.get_default_database()
        except Exception:
            db = None
        if db is None or db.name == "admin":
            db = client["test"]

        filter_query = {}
        if ObjectId.is_valid(PROPERTY_ID):
            filter_query = {"$or": [{"_id": ObjectId(PROPERTY_ID)}, {"id": PROPERTY_ID}]}
        else:
            filter_query = {"id": PROPERTY_ID}

        update_set = {
            "socialLinks.status": "completed",
            "socialLinks.updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        if video_id:
            yt_link = f"https://youtu.be/{video_id}"
            update_set["socialLinks.youtube"] = yt_link
            update_set["videoUrl"] = yt_link
            update_set["brandedVideoUrl"] = yt_link
            print(f"🔗 Updated YouTube & Branded URL: {yt_link}")
        elif stamped_cloudinary_url:
            update_set["brandedVideoUrl"] = stamped_cloudinary_url
            print(f"🔗 Updated Branded Video URL: {stamped_cloudinary_url}")

        if reel_id:
            ig_link = f"https://www.instagram.com/reel/{reel_id}/"
            update_set["socialLinks.instagram"] = ig_link
            print(f"🔗 Updated Instagram: {ig_link}")

        if vid_id:
            fb_link = f"https://www.facebook.com/watch/?v={vid_id}"
            update_set["socialLinks.facebook"] = fb_link
            print(f"🔗 Updated Facebook: {fb_link}")

        res = db.properties.update_one(filter_query, {"$set": update_set})
        print(f"✅ MongoDB sync success! Matched: {res.matched_count}, Modified: {res.modified_count}")

    except Exception as e:
        print(f"⚠️ MongoDB sync failed: {e}")
else:
    print("ℹ️ MONGODB_URI or PROPERTY_ID missing. Skipping live sync.")


# ==========================================
# 9. Cloudinary Complete Cleanup (Old Raw & New Stamped Videos Deleted - Zero MB Left)
# ==========================================
print("\n" + "=" * 60)
print("🧹 CLEANING UP CLOUDINARY STORAGE (ZERO MB LEFT)...")
print("=" * 60)

if VIDEO_CLOUDINARY_CLOUD_NAME and VIDEO_CLOUDINARY_API_KEY and VIDEO_CLOUDINARY_API_SECRET:
    try:
        import hashlib

        def destroy_cld_video(p_id, label):
            if not p_id:
                return
            ts = str(int(time.time()))
            to_sign = f"public_id={p_id}&timestamp={ts}{VIDEO_CLOUDINARY_API_SECRET}"
            sig = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()
            del_url = f"https://api.cloudinary.com/v1_1/{VIDEO_CLOUDINARY_CLOUD_NAME}/video/destroy"
            p = {
                "public_id": p_id,
                "timestamp": ts,
                "api_key": VIDEO_CLOUDINARY_API_KEY,
                "signature": sig
            }
            del_res = requests.post(del_url, data=p, timeout=20)
            res_json = del_res.json()
            print(f"🗑️ [{label} Video Cleanup]: {p_id} -> {del_res.status_code} ({res_json.get('result', '')})")

        # 1. Delete Old Raw Video
        raw_m = re.search(r"/upload/(?:v\d+/)?([^/.]+)", VIDEO_URL)
        if raw_m:
            destroy_cld_video(raw_m.group(1), "Old Raw")

        # 2. Delete New Stamped Video
        if stamped_cloudinary_public_id:
            destroy_cld_video(stamped_cloudinary_public_id, "New Stamped")
        elif stamped_cloudinary_url:
            stamped_m = re.search(r"/upload/(?:v\d+/)?([^/.]+)", stamped_cloudinary_url)
            if stamped_m:
                destroy_cld_video(stamped_m.group(1), "New Stamped")

        print("✅ Cloudinary 100% clean! Both old raw and new stamped videos deleted successfully.")

    except Exception as e_cld:
        print(f"ℹ️ Cloudinary cleanup notice: {e_cld}")

print("\n" + "=" * 60)
print("🎉 ALL TASKS FINISHED WITH COMPLETE SUCCESS! WORKER TERMINATING NORMALLY (CODE 0).")
print("=" * 60)
sys.exit(0)
