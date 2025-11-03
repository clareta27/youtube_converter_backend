import os
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
try:
    import importlib.metadata as importlib_metadata  # ✅ Python 3.8+
except ImportError:
    import importlib_metadata  # fallback untuk versi lama

app = Flask(__name__)

# === Helper: Extract video ID dari berbagai format URL YouTube ===
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

# === Endpoint utama: ambil transcript YouTube ===
@app.post("/transcript")
def transcript():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        # ✅ API baru youtube-transcript-api (v1.x): langsung pakai get_transcript()
        transcript_items = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=["id", "en", "en-US", "en-GB"],
        )

        text = " ".join([t["text"] for t in transcript_items if t.get("text")])
        language = transcript_items[0].get("language", "unknown")

        return jsonify(
            {
                "status": "success",
                "video_id": video_id,
                "language": language,
                "transcript": text,
                "length": len(text),
            }
        )

    except TranscriptsDisabled:
        return jsonify(
            {"status": "error", "message": "Transcripts are disabled for this video"}
        ), 403
    except NoTranscriptFound:
        return jsonify(
            {"status": "error", "message": "No transcript available for this video"}
        ), 404
    except VideoUnavailable:
        return jsonify(
            {"status": "error", "message": "Video unavailable or invalid"}
        ), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === Endpoint root (cek server aktif) ===
@app.get("/")
def home():
    return jsonify(
        {
            "message": "✅ YouTube Transcript API is running.",
            "usage": "POST /transcript { 'url': 'https://www.youtube.com/watch?v=...' }",
        }
    )


# === Endpoint cek versi library ===
@app.get("/version")
def version():
    try:
        yt_version = importlib_metadata.version("youtube-transcript-api")
    except Exception as e:
        yt_version = f"unknown ({str(e)})"
    return jsonify({"youtube_transcript_api_version": yt_version})


# === Start server (untuk Render) ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # 🔥 wajib untuk Render
    app.run(host="0.0.0.0", port=port)
