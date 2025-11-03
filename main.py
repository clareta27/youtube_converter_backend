import os
import random
import time
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

app = Flask(__name__)

# === Load proxy list ===
def load_proxy_list():
    raw = os.getenv("PROXY_LIST", "")
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]

PROXY_LIST = load_proxy_list()

def extract_video_id(youtube_url: str) -> str:
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
    if not PROXY_LIST:
        return None
    proxy_url = random.choice(PROXY_LIST)
    return {"http": proxy_url, "https": proxy_url}

def delay_between_requests():
    sleep_time = random.uniform(1.5, 3.5)
    time.sleep(sleep_time)
    return sleep_time

@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube Transcript API (v1.2.3+) working with .list() method",
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

        proxy = get_random_proxy()
        delay = delay_between_requests()

        # ✅ Cara baru sesuai 1.2.3
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id, proxies=proxy)

        transcript_obj = None
        for lang in ["id", "en", "en-US", "en-GB"]:
            try:
                transcript_obj = transcript_list.find_transcript([lang])
                break
            except Exception:
                continue

        if not transcript_obj:
            transcript_obj = next(iter(transcript_list))

        transcript_items = transcript_obj.fetch()
        text = " ".join([t["text"] for t in transcript_items if t.get("text")])
        lang = transcript_obj.language_code

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
        return jsonify({"status": "error", "message": "Transcripts are disabled"}), 403
    except NoTranscriptFound:
        return jsonify({"status": "error", "message": "No transcript available"}), 404
    except VideoUnavailable:
        return jsonify({"status": "error", "message": "Video unavailable"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
