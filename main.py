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
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

app = Flask(__name__)

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

@app.post("/transcript")
def transcript():
    try:
        data = request.get_json(force=True)
        url = (data.get("url") or "").strip()

        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        # ✅ Versi terbaru (Oktober 2025): gunakan instance + .list()
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Ambil salah satu bahasa yang cocok
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
        text = " ".join([t.get("text", "") for t in transcript_items if t.get("text")])
        language = getattr(transcript_obj, "language_code", "unknown")

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "language": language,
            "length": len(text),
            "transcript": text
        })

    except TranscriptsDisabled:
        return jsonify({"status": "error", "message": "Transcripts disabled"}), 403
    except NoTranscriptFound:
        return jsonify({"status": "error", "message": "No transcript found"}), 404
    except VideoUnavailable:
        return jsonify({"status": "error", "message": "Video unavailable"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube Transcript API is running (using instance.list).",
        "usage": "POST /transcript { 'url': 'https://www.youtube.com/watch?v=...' }"
    })

@app.get("/version")
def version():
    try:
        yt_version = importlib_metadata.version("youtube-transcript-api")
    except Exception as e:
        yt_version = f"unknown ({str(e)})"
    return jsonify({"youtube_transcript_api_version": yt_version})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
