import os
import time
import random
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

app = Flask(__name__)

# === Load proxy list from environment ===
def load_proxy_list():
    raw = os.getenv("PROXY_LIST", "")
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]

PROXY_LIST = load_proxy_list()

def extract_video_id(youtube_url: str) -> str:
    """Ambil ID video dari berbagai format URL YouTube"""
    try:
        u = urlparse(youtube_url)
        if u.netloc.endswith("youtu.be"):
            return u.path.strip("/")
        if "watch" in u.path:
            return parse_qs(u.query).get("v", [""])[0]
        if "/shorts/" in u.path:
            return u.path.split("/shorts/")[1].split("/")[0]
        return u.path.strip("/").split("/")[-1]
    except Exception:
        return ""

def get_random_proxy():
    """Pilih 1 proxy acak dari list"""
    if not PROXY_LIST:
        return None
    proxy_url = random.choice(PROXY_LIST)
    return {"http": proxy_url, "https": proxy_url}

def delay_between_requests():
    """Tambahkan delay acak agar tidak cepat diblok YouTube"""
    sleep_time = random.uniform(1.5, 3.5)
    time.sleep(sleep_time)
    return sleep_time

@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube Transcript API with Auto Proxy Rotation is running.",
        "proxies_loaded": len(PROXY_LIST),
    })

@app.post("/transcript")
def transcript():
    try:
        data = request.get_json(force=True)
        url = (data.get("url") or "").strip()

        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        # Rotasi proxy & delay
        proxy = get_random_proxy()
        delay = delay_between_requests()

        # Ambil subtitle via proxy
        transcript_items = YouTubeTranscriptApi.get_transcript(
            video_id,
            proxies=proxy,
            languages=["id", "en", "en-US", "en-GB"],
        )

        text = " ".join([t.get("text", "") for t in transcript_items])
        lang = transcript_items[0].get("language", "unknown") if transcript_items else "unknown"

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "language": lang,
            "proxy_used": proxy["http"] if proxy else "None",
            "delay": round(delay, 2),
            "length": len(text),
            "transcript": text[:1000] + "..." if len(text) > 1000 else text,
        })

    except TranscriptsDisabled:
        return jsonify({"status": "error", "message": "Transcripts are disabled for this video"}), 403
    except NoTranscriptFound:
        return jsonify({"status": "error", "message": "No transcript available for this video"}), 404
    except VideoUnavailable:
        return jsonify({"status": "error", "message": "Video unavailable or invalid"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
