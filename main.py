import os
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

def get_random_proxy():
    if not PROXY_LIST:
        return None
    proxy_url = random.choice(PROXY_LIST)
    return {"http": proxy_url, "https": proxy_url}

# === Helper: extract video ID ===
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

# === Transcript endpoint ===
@app.post("/transcript")
def transcript():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        proxy = get_random_proxy()
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
            "length": len(text),
            "transcript": text,
        })

    except TranscriptsDisabled:
        return jsonify({"status": "error", "message": "Transcripts are disabled for this video"}), 403
    except NoTranscriptFound:
        return jsonify({"status": "error", "message": "No transcript available for this video"}), 404
    except VideoUnavailable:
        return jsonify({"status": "error", "message": "Video unavailable or invalid"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube Transcript API via Proxy is running.",
        "proxies_loaded": len(PROXY_LIST),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
