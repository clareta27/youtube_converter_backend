from flask import Flask, request, jsonify
import yt_dlp
import tempfile
import os
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def home():
    return jsonify({
        "message": "✅ YouTube → Whisper streaming mode (no cookies)",
        "usage": "POST /transcribe {'url': 'https://www.youtube.com/watch?v=...'}"
    })

@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    try:
        # Unduh hanya audio kecil ke file sementara
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "audio.mp3")
            ydl_opts = {
                "format": "bestaudio[filesize<20M]/bestaudio/best",
                "outtmpl": out_path,
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "64",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Unknown Title")

            # Kirim ke Whisper API
            with open(out_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            return jsonify({
                "title": title,
                "transcription": transcript.text.strip(),
                "status": "✅ success"
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
