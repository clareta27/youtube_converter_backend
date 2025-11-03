import os
import tempfile
import yt_dlp
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # diambil dari environment Render


def extract_video_id(url: str):
    """Ekstrak video_id dari berbagai format URL YouTube."""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    return None


@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube → Whisper transcription API is running.",
        "usage": "POST /transcribe {'url': 'https://www.youtube.com/watch?v=...'}"
    })


@app.post("/transcribe")
def transcribe():
    try:
        data = request.get_json(force=True)
        url = (data.get("url") or "").strip()

        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400
        if not OPENAI_API_KEY:
            return jsonify({"status": "error", "message": "OPENAI_API_KEY not configured"}), 500

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, f"{video_id}.mp3")

        # === Download audio dari YouTube ===
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            ],
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = os.path.join(tmpdir, f"{info['id']}.mp3")

        if not os.path.exists(downloaded_file):
            return jsonify({"status": "error", "message": "Failed to download audio"}), 500

        # === Kirim audio ke Whisper ===
        with open(downloaded_file, "rb") as audio_file:
            whisper_res = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": (f"{video_id}.mp3", audio_file, "audio/mpeg")},
                data={"model": "whisper-1"},
                timeout=180
            )

        if whisper_res.status_code != 200:
            return jsonify({
                "status": "error",
                "message": "Whisper API failed",
                "details": whisper_res.text
            }), 500

        transcript = whisper_res.json().get("text", "")

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "title": info.get("title"),
            "duration": info.get("duration"),
            "transcript": transcript
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
