from flask import Flask, request, jsonify
import yt_dlp
import subprocess
import os
import tempfile
import openai

# === Inisialisasi Flask App ===
app = Flask(__name__)

# === Endpoint Utama ===
@app.route("/")
def home():
    return jsonify({
        "message": "✅ YouTube → Whisper transcription API is running.",
        "usage": "POST /transcribe {'url': 'https://www.youtube.com/watch?v=...'}"
    })

# === Endpoint Transkripsi ===
@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        data = request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"error": "Missing 'url' in JSON body"}), 400

        # === 1. Unduh audio dari YouTube ===
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": audio_path,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            title = info.get("title", "Unknown Title")

            # === 2. Transkripsi menggunakan OpenAI Whisper ===
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            if not openai.api_key:
                return jsonify({"error": "Missing OPENAI_API_KEY in environment"}), 500

            with open(audio_path, "rb") as audio_file:
                transcript = openai.Audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            text = transcript.text if hasattr(transcript, "text") else str(transcript)

        return jsonify({
            "title": title,
            "transcription": text.strip(),
            "status": "✅ success"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Jalankan Lokal (Render pakai gunicorn, jadi ini hanya untuk local dev) ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
