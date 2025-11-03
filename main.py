import os
import tempfile
import yt_dlp
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# === Extract video_id ===
def extract_video_id(url: str):
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    return None


@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube Audio Converter API is running.",
        "usage": "POST /convert {'url': 'https://www.youtube.com/watch?v=...'}"
    })


@app.post("/convert")
def convert():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        # === Temp directory for output ===
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, f"{video_id}.mp3")

        # === yt_dlp options ===
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_path,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            ],
            "quiet": True,
            "noplaylist": True,
        }

        # === Download audio ===
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # === Return file directly ===
        return send_file(output_path, as_attachment=True, download_name=f"{video_id}.mp3")

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
