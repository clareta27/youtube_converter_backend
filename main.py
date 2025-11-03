import os
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
import youtube_transcript_api
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

def fetch_transcript(video_id: str):
    langs = ["id", "id-**", "en", "en-US", "en-GB"]

    # A. Versi lama (classmethod list_transcripts)
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        t = None
        for lang in langs:
            try:
                t = transcripts.find_transcript([lang])
                break
            except Exception:
                continue
        if not t:
            t = next(iter(transcripts))
        return t.fetch(), t.language_code, "path_A_class_list"
    except (AttributeError, TypeError):
        pass

    # B. Versi baru (instance.list_transcripts)
    try:
        api = YouTubeTranscriptApi()
        transcripts = api.list_transcripts(video_id)
        t = None
        for lang in langs:
            try:
                t = transcripts.find_transcript([lang])
                break
            except Exception:
                continue
        if not t:
            t = next(iter(transcripts))
        return t.fetch(), t.language_code, "path_B_instance_list"
    except (AttributeError, TypeError):
        pass

    # C. Versi 1.2.3 ke atas (get_transcript langsung)
    items = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
    lang_code = items[0].get("language", "unknown") if items else "unknown"
    return items, lang_code, "path_C_direct_get"

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

        items, lang_code, path_used = fetch_transcript(video_id)
        text = " ".join([t.get("text", "") for t in items if isinstance(t, dict)])

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "language": lang_code,
            "length": len(text),
            "transcript": text,
            "engine_path": path_used,
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
        "message": "✅ YouTube Transcript API is running.",
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
