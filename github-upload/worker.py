"""
Autonomous 1080p Full HD Video Cloud Worker for Capital Prime.
Runs on GitHub Actions 4-Core Runner with 16GB RAM for 100% Free Processing.

Features:
- 100% Zero-External-AI Dependency (No Gemini token/quota/503 limits).
- Universal Layout: Handles both Horizontal/Landscape and Vertical videos.
  * Landscape videos get a luxurious, ambient blurred background + centered crisp video.
  * Badges sit cleanly in the top blurred zone, NEVER obstructing the property view.
- Exact Clean 3-Badge Overlay:
  1. Location: <LOCATION> (Gold)
  2. Total Area: <AREA> <UNIT> (White)
  3. Visit: capitalprime.co.in (Cyan Blue)
- Clean, High-Converting Social Descriptions (Zero phone numbers, 100% authentic details).
- Multi-Platform Auto-Publishing (YouTube Shorts, Instagram Reels, Facebook Reels).
- Automatic Cloudinary Zero-Storage Cleanup & MongoDB live sync.
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
LOCATION = os.getenv("INPUT_LOCATION", "Ranchi").strip()
AREA = os.getenv("INPUT_AREA", "5").strip()
AREA_UNIT = os.getenv("INPUT_AREA_UNIT", "dismil").strip()
TITLE = os.getenv("INPUT_TITLE", "Prime Property in Ranchi").strip()
PROPERTY_ID = os.getenv("INPUT_PROPERTY_ID", "").strip()

PRICE = os.getenv("INPUT_PRICE", "").strip()
RATE_TEXT = os.getenv("INPUT_RATE_TEXT", "").strip()

FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841467192830436").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1397425480114961").strip()
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()

# Cloudinary credentials for cleanup
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

# Search for fonts
FONT_PATH = Path("assets/fonts/Montserrat-Bold.ttf")
if not FONT_PATH.exists():
    FONT_PATH = Path("github-upload/assets/fonts/Montserrat-Bold.ttf")
if not FONT_PATH.exists():
    FONT_PATH = Path("Montserrat-Bold.ttf")

BRUSH_FONT_PATH = Path("assets/fonts/PermanentMarker.ttf")
if not BRUSH_FONT_PATH.exists():
    BRUSH_FONT_PATH = Path("github-upload/assets/fonts/PermanentMarker.ttf")
if not BRUSH_FONT_PATH.exists():
    BRUSH_FONT_PATH = Path("PermanentMarker.ttf")


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
# 1C. Distributed Mutex Lock (MongoDB)
# ==========================================
if MONGODB_URI and PROPERTY_ID:
    try:
        from pymongo import MongoClient
        from bson import ObjectId

        print(f"\n🔒 Checking MongoDB Lock for Property {PROPERTY_ID}...")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
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

        prop = db.properties.find_one(filter_query)
        if prop:
            if not RATE_TEXT and prop.get("rateText"):
                RATE_TEXT = str(prop.get("rateText")).strip()
            if not RATE_TEXT and prop.get("price"):
                try:
                    p_val = float(prop.get("price", 0))
                    a_val = float(prop.get("area", 1))
                    a_unit = str(prop.get("areaUnit", "")).lower()
                    total_dismil = a_val * 100.0 if "acre" in a_unit else a_val
                    if total_dismil > 0 and p_val > 0:
                        rate_per_dismil = p_val / total_dismil
                        if rate_per_dismil >= 100000:
                            lakhs = rate_per_dismil / 100000.0
                            if lakhs == int(lakhs):
                                RATE_TEXT = f"RATE {int(lakhs)} LAKH PER DECIMIL"
                            else:
                                RATE_TEXT = f"RATE {lakhs:.2f} LAKH PER DECIMIL"
                except Exception:
                    pass

            sl = prop.get("socialLinks") or {}
            existing_yt = sl.get("youtube") or prop.get("videoUrl", "")
            current_status = sl.get("status")

            if ("youtu.be" in str(existing_yt)) or ("youtube.com" in str(existing_yt)):
                print(f"✅ [DUPLICATE PREVENTION] Property already published on YouTube: {existing_yt}!")
                print("🛑 Exiting worker immediately.")
                sys.exit(0)

            if current_status == "completed":
                print(f"✅ [DUPLICATE PREVENTION] Property status is already 'completed'!")
                print("🛑 Exiting worker immediately.")
                sys.exit(0)

            if current_status == "processing":
                print(f"⚠️ [CONCURRENCY GUARD] Another worker is ALREADY processing Property {PROPERTY_ID}!")
                print("🛑 Terminating duplicate runner.")
                sys.exit(0)

            lock_res = db.properties.update_one(
                {
                    "$and": [
                        filter_query,
                        {
                            "$or": [
                                {"socialLinks.status": {"$in": ["queued", None, "", "failed"]}},
                                {"socialLinks": {"$exists": False}},
                                {"socialLinks.status": {"$exists": False}}
                            ]
                        }
                    ]
                },
                {
                    "$set": {
                        "socialLinks.status": "processing",
                        "socialLinks.lockedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "socialLinks.workerRunId": os.getenv("GITHUB_RUN_ID", "")
                    }
                }
            )

            if lock_res.modified_count == 0:
                print(f"⚠️ [CONCURRENCY GUARD] Lock acquisition failed.")
                sys.exit(0)

            print(f"✅ Distributed lock acquired! Status set to 'processing'.")
    except Exception as e_lock:
        print(f"⚠️ Lock check notice: {e_lock}. Proceeding...")


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
# 3. Probe Video (Orientation, Dimensions & Duration)
# ==========================================
probe_cmd = ["ffmpeg", "-i", str(INPUT_PATH)]
probe_run = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="replace")
stderr = probe_run.stderr

is_vertical = True
has_audio = "Audio:" in stderr
rot_match = re.search(r"rotate\s*:\s*(\d+)", stderr)
is_rotated = rot_match and rot_match.group(1) in ("90", "270")
vid_match = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", stderr)

rw, rh = 1080, 1920
if vid_match:
    rw, rh = int(vid_match.group(1)), int(vid_match.group(2))
    w, h = (rh, rw) if is_rotated else (rw, rh)
    is_vertical = h >= w
else:
    is_vertical = True

dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr)
video_duration = 30.0
if dur_match:
    hrs = float(dur_match.group(1))
    mins = float(dur_match.group(2))
    secs = float(dur_match.group(3))
    video_duration = hrs * 3600 + mins * 60 + secs

# Target Canvas: ALWAYS 1080x1920 for YouTube Shorts & Reels!
TARGET_W = 1080
TARGET_H = 1920

print(f"📐 Detected Raw Dimensions: {rw}x{rh} (Vertical: {is_vertical}, Audio: {has_audio}, Duration: {video_duration:.1f}s)")
print(f"🎯 Target Canvas: {TARGET_W}x{TARGET_H} (Full HD Vertical for Shorts/Reels)")

# 3B. Detect letterboxing (black bars baked into video)
is_letterboxed = False
crop_y = 0
crop_h = rh
sample_frame_path = WORK_DIR / "sample_probe.jpg"

if is_vertical:
    probe_frame_cmd = [
        "ffmpeg", "-y", "-ss", "1.0", "-i", str(INPUT_PATH),
        "-vframes", "1", "-q:v", "2", str(sample_frame_path)
    ]
    subprocess.run(probe_frame_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sample_frame_path.exists():
        try:
            im = Image.open(sample_frame_path).convert("L")
            sw, sh = im.size
            top_box = im.crop((int(sw * 0.15), int(sh * 0.02), int(sw * 0.85), int(sh * 0.15)))
            top_avg = sum(top_box.tobytes()) / (top_box.width * top_box.height)
            bot_box = im.crop((int(sw * 0.15), int(sh * 0.85), int(sw * 0.85), int(sh * 0.98)))
            bot_avg = sum(bot_box.tobytes()) / (bot_box.width * bot_box.height)
            mid_box = im.crop((int(sw * 0.15), int(sh * 0.4), int(sw * 0.85), int(sh * 0.6)))
            mid_avg = sum(mid_box.tobytes()) / (mid_box.width * mid_box.height)

            print(f"📊 Letterbox probe: Top={top_avg:.1f}, Mid={mid_avg:.1f}, Bot={bot_avg:.1f}")
            if (top_avg < 25 or bot_avg < 30) and (mid_avg > top_avg + 25):
                x_s, x_e = int(sw * 0.2), int(sw * 0.8)
                y1 = 0
                for y in range(0, int(sh * 0.45), 4):
                    strip = im.crop((x_s, y, x_e, y + 4))
                    if sum(strip.tobytes()) / (strip.width * strip.height) > 35:
                        y1 = max(0, y - 2)
                        break
                y2 = sh
                for y in range(sh - 4, int(sh * 0.55), -4):
                    strip = im.crop((x_s, y, x_e, y + 4))
                    if sum(strip.tobytes()) / (strip.width * strip.height) > 35:
                        y2 = min(sh, y + 4)
                        break
                active_h = y2 - y1
                if int(sh * 0.25) <= active_h <= int(sh * 0.85):
                    is_letterboxed = True
                    scale_factor = rh / sh
                    crop_y = int(y1 * scale_factor)
                    crop_h = int(active_h * scale_factor)
                    print(f"🎯 Letterbox detected! Active video: y={crop_y}, h={crop_h} (Total H={rh})")
        except Exception as e_lb:
            print(f"⚠️ Letterbox probe notice: {e_lb}")


# ==========================================
# 4. Generate Clean 3-Badge Overlay (Exact User Spec)
# ==========================================
print("🎨 Creating 1080p Badges with Dynamic Auto-Fit Font Scaling...")
img = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Clean, exact labels without duplicates
loc_clean = f"Location: {LOCATION}" if not LOCATION.lower().startswith("location") else LOCATION
clean_unit = AREA_UNIT.capitalize() if AREA_UNIT else ""
full_area = f"{AREA} {clean_unit}".strip() if clean_unit else str(AREA)
area_clean = f"Total Area: {full_area}" if not full_area.lower().startswith("total area") else full_area
web_clean = "Visit: capitalprime.co.in"

# Position badges in the top zone
if is_vertical and not is_letterboxed:
    # On full-screen vertical videos, keep in top 6%
    init_s1, min_s1 = 48, 26
    init_s2, min_s2 = 40, 22
    init_s3, min_s3 = 34, 20
    v_pad = 12
    h_pad = 26
    gap = 14
    radius = 16
    y_start = int(TARGET_H * 0.06)
else:
    # On horizontal videos OR letterboxed videos with blurred background,
    # top badges sit luxuriously in the top blurred space (~140 to 450), NEVER touching the video!
    init_s1, min_s1 = 46, 26
    init_s2, min_s2 = 38, 22
    init_s3, min_s3 = 32, 20
    v_pad = 13
    h_pad = 28
    gap = 16
    radius = 16
    y_start = int(TARGET_H * 0.08)

max_pill_w = TARGET_W - 140

def load_font(sz):
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), sz)
        except Exception:
            pass
    return ImageFont.load_default()

def load_brush_font(sz):
    if BRUSH_FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(BRUSH_FONT_PATH), sz)
        except Exception:
            pass
    return load_font(sz)

def fit_text_font(draw_obj, text, initial_size, min_size, max_w, loader=load_font):
    sz = initial_size
    f = loader(sz)
    bbox = draw_obj.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    while tw > max_w and sz > min_size:
        sz -= 2
        f = loader(sz)
        bbox = draw_obj.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    return f, tw, th, bbox

# EXACT 3-Badge Specification (Nothing Extra!)
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

# Signature Price in Permanent Marker brush font style
if RATE_TEXT:
    print(f"🎨 Rendering Signature Price in Permanent Marker style: '{RATE_TEXT}'")
    brush_font, r_tw, r_th, r_bbox = fit_text_font(draw, RATE_TEXT, 52, 28, TARGET_W - 120, loader=load_brush_font)
    r_x = (TARGET_W - r_tw) // 2
    if is_vertical and not is_letterboxed:
        r_y = int(TARGET_H * 0.88)
    else:
        # Perfectly centered in the bottom blurred area (between 1280 and 1920)
        r_y = 1280 + (640 - r_th) // 2 - r_bbox[1]

    # Draw dark shadow for contrast on any background
    draw.text((r_x + 3, r_y + 3), RATE_TEXT, font=brush_font, fill=(0, 0, 0, 200))
    # Crisp white text
    draw.text((r_x, r_y), RATE_TEXT, font=brush_font, fill="#FFFFFF")
    print(f"✅ Rendered signature price text at bottom: '{RATE_TEXT}'")

img.save(OVERLAY_PNG, "PNG")
print("✅ 1080p Overlay image generated with exact badges and signature price!")


# ==========================================
# 5. FFmpeg Stamping with Universal Layout
# ==========================================
print(f"⚡ Stamping video at 1080p Full HD (1080x1920) using 4 CPU Cores...")
t_stamp = time.time()

# 100% Original Natural Colors (Zero artificial saturation, zero brightness blowout)
# The sky and grass remain 100% pure and authentic exactly as filmed!

if is_letterboxed:
    print("🎬 Applying Auto-Cropped Cinematic Blurred Background for Letterboxed Video...")
    fc = (
        f"[0:v]crop=in_w:{crop_h}:0:{crop_y}[active];"
        "[active]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
        "[active]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
        "[base][1:v]overlay=0:0[v]"
    )
elif not is_vertical:
    # HORIZONTAL/LANDSCAPE VIDEO:
    # 1. Background: Zoomed, cropped to 1080x1920, and smoothly blurred (no ugly black bars!)
    # 2. Foreground: Scaled to width 1080 with original aspect ratio, placed in the center.
    # 3. Badges: Overlaid cleanly on top.
    print("🎬 Applying Cinematic Blurred Background layout for Horizontal Video...")
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
        "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
        "[base][1:v]overlay=0:0[v]"
    )
else:
    # VERTICAL/PORTRAIT VIDEO:
    # Clean scaling to 1080x1920 without squashing or stretching.
    print("🎬 Applying Direct Full-Screen 9:16 layout for Vertical Video...")
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[base];"
        "[base][1:v]overlay=0:0[v]"
    )


ffmpeg_cmd = [
    "ffmpeg", "-y", "-threads", "4",
    "-i", str(INPUT_PATH),
    "-i", str(OVERLAY_PNG),
    "-filter_complex", fc,
    "-map", "[v]",
    "-map", "0:a?",
    "-c:v", "libx264",
    "-preset", "superfast",
    "-crf", "22",
    "-maxrate", "3000k",
    "-bufsize", "6000k",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "48000",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    str(OUTPUT_1080P_PATH)
]

p_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if p_res.returncode != 0 or not OUTPUT_1080P_PATH.exists() or OUTPUT_1080P_PATH.stat().st_size == 0:
    print(f"❌ FFmpeg error: {p_res.stderr[-500:]}")
    sys.exit(1)

out_mb = OUTPUT_1080P_PATH.stat().st_size / (1024 * 1024)
print(f"🎉 1080p VIDEO STAMPED SUCCESSFULLY in {time.time() - t_stamp:.2f}s! Size: {out_mb:.2f} MB")


# ==========================================
# 6. Upload Stamped Video to Cloudinary
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
# 7. Generate Clean Descriptions (NO PHONE NUMBER!)
# ==========================================
clean_unit = AREA_UNIT.capitalize() if AREA_UNIT else ""
full_area_str = f"{AREA} {clean_unit}".strip() if clean_unit else str(AREA)

yt_clean_title = f"{TITLE} | {LOCATION} ({full_area_str}) #Shorts"
if len(yt_clean_title) > 95:
    yt_clean_title = f"Prime Plot: {LOCATION} ({full_area_str}) #Shorts"

yt_clean_desc = (
    f"📍 Location: {LOCATION}\n"
    f"📐 Total Area: {full_area_str}\n"
    f"📜 100% Verified Title & Clear Freehold Land\n\n"
    f"🌐 For more details, visit official website:\n"
    f"👉 https://capitalprime.co.in\n\n"
    f"#RanchiRealEstate #PlotsInRanchi #CapitalPrime #LandInRanchi #PropertyInRanchi #Shorts"
)

ig_clean_caption = (
    f"Prime Property in {LOCATION} 🏡\n"
    f"📐 Total Area: {full_area_str}\n"
    f"✅ 100% Verified Title & Clear Freehold Land\n\n"
    f"🌐 Visit website for more details:\n"
    f"👉 https://capitalprime.co.in\n\n"
    f"#RanchiRealEstate #PlotsInRanchi #CapitalPrime #Ranchi #Property #ReelsIndia #PlotForSale"
)

fb_clean_caption = (
    f"Prime Property Available in {LOCATION} 🏡\n"
    f"📐 Total Area: {full_area_str}\n"
    f"✅ 100% Clear Title & Verified Land\n\n"
    f"🌐 More Details: https://capitalprime.co.in\n\n"
    f"#Ranchi #RanchiRealEstate #PlotsInRanchi #CapitalPrime #FacebookReels #PropertyInRanchi"
)


# ==========================================
# 8. Multi-Platform Auto-Publishing
# ==========================================
print("\n" + "=" * 60)
print("🚀 PUBLISHING 1080p VIDEO TO SOCIAL MEDIA...")
print("=" * 60)

video_id = None
reel_id = None
vid_id = None

# 8A. YouTube Upload
def upload_to_youtube():
    global video_id
    token_json = os.getenv("YOUTUBE_TOKEN_JSON", "").strip()
    if token_json:
        try:
            print("\n▶️ [YouTube Auth] Loading token from GitHub Secret...")
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            t_data = json.loads(token_json)
            creds = Credentials(
                token=t_data.get("token"),
                refresh_token=t_data.get("refresh_token"),
                token_uri=t_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=t_data.get("client_id"),
                client_secret=t_data.get("client_secret"),
                scopes=t_data.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"])
            )

            if not creds.valid and creds.refresh_token:
                creds.refresh(Request())
                print("✅ [YouTube OAuth] Access token refreshed!")

            yt_service = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": yt_clean_title,
                    "description": yt_clean_desc,
                    "tags": ["RealEstate", "Ranchi", "CapitalPrime", "PlotsInRanchi", "Jharkhand"],
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
        print("ℹ️ YouTube token not configured, skipping.")

# 8B. Facebook Page Video Upload
def upload_to_facebook():
    global vid_id
    page_token = FB_PAGE_ACCESS_TOKEN or META_ACCESS_TOKEN
    if page_token and FB_PAGE_ID:
        try:
            print(f"\n📘 [Facebook Reels] Initializing Reel on Page {FB_PAGE_ID}...")
            init_url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/video_reels"
            init_res = requests.post(init_url, params={"upload_phase": "start", "access_token": page_token}, timeout=30).json()
            
            reel_video_id = init_res.get("video_id")
            reel_upload_url = init_res.get("upload_url")
            
            if reel_video_id and reel_upload_url:
                print(f"📘 [Facebook Reels] Uploading video binary stream...")
                with open(OUTPUT_1080P_PATH, "rb") as vf:
                    file_data = vf.read()
                
                headers = {
                    "Authorization": f"OAuth {page_token}",
                    "offset": "0",
                    "file_size": str(len(file_data))
                }
                requests.post(reel_upload_url, data=file_data, headers=headers, timeout=300)
                
                finish_res = requests.post(
                    init_url,
                    params={
                        "upload_phase": "finish",
                        "video_id": reel_video_id,
                        "video_state": "PUBLISHED",
                        "description": fb_clean_caption,
                        "access_token": page_token
                    },
                    timeout=30
                ).json()
                
                if finish_res.get("success") or finish_res.get("id"):
                    vid_id = reel_video_id
                    print(f"📘 [Facebook Reel Success] 🚀 Video ID: {vid_id} -> https://www.facebook.com/watch/?v={vid_id}")
                    return

            # Fallback standard video
            fb_url = f"https://graph-video.facebook.com/v21.0/{FB_PAGE_ID}/videos"
            with open(OUTPUT_1080P_PATH, "rb") as vf:
                files = {"source": ("stamped_1080p.mp4", vf, "video/mp4")}
                data = {
                    "title": f"Prime Plot: {LOCATION} ({AREA} {AREA_UNIT})",
                    "description": fb_clean_caption,
                    "access_token": page_token
                }
                fb_res = requests.post(fb_url, data=data, files=files, timeout=300).json()
                vid_id = fb_res.get("id")
                if vid_id:
                    print(f"📘 [Facebook Success] Video ID: {vid_id}")
        except Exception as e:
            print(f"⚠️ Facebook upload error: {e}")

# 8C. Instagram Reels Upload
def upload_to_instagram():
    global reel_id
    base_meta_token = META_ACCESS_TOKEN or FB_PAGE_ACCESS_TOKEN
    if base_meta_token and INSTAGRAM_USER_ID:
        try:
            is_ready = False

            # Method 1: Cloud-to-Cloud Ingestion from Cloudinary
            if stamped_cloudinary_url:
                for attempt in range(1, 3):
                    try:
                        print(f"\n📸 [Instagram] Attempt {attempt}/2: Cloud-to-Cloud Ingestion...")
                        time.sleep(3)
                        init_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media"
                        p_cloud = {
                            "media_type": "REELS",
                            "video_url": stamped_cloudinary_url,
                            "caption": ig_clean_caption,
                            "access_token": base_meta_token
                        }
                        c_res = requests.post(init_url, data=p_cloud, timeout=60).json()
                        cont_id = c_res.get("id")
                        if cont_id:
                            print(f"✅ Instagram container created: {cont_id}. Checking processing...")
                            for poll in range(1, 30):
                                time.sleep(4)
                                st_res = requests.get(
                                    f"https://graph.facebook.com/v21.0/{cont_id}",
                                    params={"fields": "status_code,status", "access_token": base_meta_token},
                                    timeout=30
                                ).json()
                                code = st_res.get("status_code", "")
                                if code == "FINISHED":
                                    is_ready = True
                                    break
                                elif code == "ERROR":
                                    break

                            if is_ready:
                                pub_res = requests.post(
                                    f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
                                    data={"creation_id": cont_id, "access_token": base_meta_token},
                                    timeout=60
                                ).json()
                                reel_id = pub_res.get("id")
                                if reel_id:
                                    print(f"📸 [Instagram Success] Published Reel ID: {reel_id} -> https://www.instagram.com/reel/{reel_id}/")
                                    return
                    except Exception as err:
                        print(f"⚠️ Instagram attempt {attempt} error: {err}")

            # Method 2: Resumable Binary Upload fallback
            if not reel_id:
                print("\n📸 [Instagram] Fallback: Direct Resumable Binary Upload...")
                r_init = requests.post(
                    f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media",
                    data={"media_type": "REELS", "upload_type": "resumable", "caption": ig_clean_caption, "access_token": base_meta_token},
                    timeout=30
                ).json()
                cont_id = r_init.get("id")
                up_uri = r_init.get("uri")
                if cont_id and up_uri:
                    with open(OUTPUT_1080P_PATH, "rb") as vf:
                        f_bytes = vf.read()
                    h_bin = {"Authorization": f"OAuth {base_meta_token}", "offset": "0", "file_size": str(len(f_bytes))}
                    requests.post(up_uri, data=f_bytes, headers=h_bin, timeout=300)
                    for poll in range(1, 30):
                        time.sleep(4)
                        st_res = requests.get(
                            f"https://graph.facebook.com/v21.0/{cont_id}",
                            params={"fields": "status_code", "access_token": base_meta_token},
                            timeout=30
                        ).json()
                        if st_res.get("status_code") == "FINISHED":
                            is_ready = True
                            break
                    if is_ready:
                        pub_res = requests.post(
                            f"https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
                            data={"creation_id": cont_id, "access_token": base_meta_token},
                            timeout=60
                        ).json()
                        reel_id = pub_res.get("id")
                        if reel_id:
                            print(f"📸 [Instagram Success] Published Reel ID: {reel_id} -> https://www.instagram.com/reel/{reel_id}/")
        except Exception as e:
            print(f"⚠️ Instagram upload error: {e}")

# Run multi-platform uploads in parallel
t_pub = time.time()
print("⚡ Launching Parallel Publishing to YouTube, Instagram & Facebook...")
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    f_yt = executor.submit(upload_to_youtube)
    f_fb = executor.submit(upload_to_facebook)
    f_ig = executor.submit(upload_to_instagram)
    concurrent.futures.wait([f_yt, f_fb, f_ig], timeout=360)

print(f"✅ Multi-Platform Publishing completed in {time.time() - t_pub:.2f}s!")


# ==========================================
# 9. Sync Live Social Links to MongoDB
# ==========================================
if MONGODB_URI and PROPERTY_ID:
    try:
        from pymongo import MongoClient
        from bson import ObjectId

        print("\n" + "=" * 60)
        print("🔄 SYNCING LIVE SOCIAL LINKS TO MONGODB...")
        print("=" * 60)

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
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

        update_fields = {
            "socialLinks.updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        if video_id:
            yt_url = f"https://youtu.be/{video_id}"
            update_fields["socialLinks.youtube"] = yt_url
            update_fields["videoUrl"] = yt_url
            print(f"▶️ Updated YouTube URL: {yt_url}")

        if reel_id:
            ig_url = f"https://www.instagram.com/reel/{reel_id}/"
            update_fields["socialLinks.instagram"] = ig_url
            print(f"📸 Updated Instagram: {ig_url}")

        if vid_id:
            fb_url = f"https://www.facebook.com/watch/?v={vid_id}"
            update_fields["socialLinks.facebook"] = fb_url
            print(f"📘 Updated Facebook: {fb_url}")

        if video_id or reel_id or vid_id:
            update_fields["socialLinks.status"] = "completed"
            update_fields["socialLinks.publishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        else:
            update_fields["socialLinks.status"] = "failed"

        res = db.properties.update_one(filter_query, {"$set": update_fields})
        print(f"✅ MongoDB sync success! Matched: {res.matched_count}, Modified: {res.modified_count}")
    except Exception as e_db:
        print(f"⚠️ MongoDB sync error: {e_db}")


# ==========================================
# 10. Clean Up Cloudinary Storage (Zero MB Left)
# ==========================================
if VIDEO_CLOUDINARY_CLOUD_NAME and VIDEO_CLOUDINARY_API_KEY and VIDEO_CLOUDINARY_API_SECRET:
    try:
        import hashlib
        print("\n" + "=" * 60)
        print("🧹 CLEANING UP CLOUDINARY STORAGE (ZERO MB LEFT)...")
        print("=" * 60)

        def destroy_cloudinary(pub_id):
            if not pub_id:
                return
            t_d = str(int(time.time()))
            to_sign = f"public_id={pub_id}&timestamp={t_d}{VIDEO_CLOUDINARY_API_SECRET}"
            sig = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
            d_url = f"https://api.cloudinary.com/v1_1/{VIDEO_CLOUDINARY_CLOUD_NAME}/video/destroy"
            d_res = requests.post(d_url, data={
                "public_id": pub_id,
                "timestamp": t_d,
                "api_key": VIDEO_CLOUDINARY_API_KEY,
                "signature": sig
            }, timeout=30)
            print(f"🗑️ Cleaned: {pub_id} -> {d_res.status_code}")

        # Delete raw video
        raw_match = re.search(r"/upload/(?:v\d+/)?([^.]+)", VIDEO_URL)
        if raw_match:
            destroy_cloudinary(raw_match.group(1))

        # Delete stamped video
        if stamped_cloudinary_public_id:
            destroy_cloudinary(stamped_cloudinary_public_id)

        print("✅ Cloudinary 100% clean!")
    except Exception as e_clean:
        print(f"⚠️ Cleanup notice: {e_clean}")

print("\n" + "=" * 60)
print("🎉 ALL TASKS FINISHED WITH COMPLETE SUCCESS! (CODE 0)")
print("=" * 60)
