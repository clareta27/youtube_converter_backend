import os
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

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
        url = data.get("url")
        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        transcript_items = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["id", "en", "en-US", "en-GB"]
        )
        text = " ".join([t["text"] for t in transcript_items if t.get("text")])

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "transcript": text,
            "length": len(text)
        })

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        return jsonify({"status": "error", "message": f"Transcript not available: {str(e)}"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
