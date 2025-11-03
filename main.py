from flask import Flask, request, jsonify
import yt_dlp
import requests
import openai
import os

app = Flask(__name__)

# --- API KEY OpenAI dari environment variable ---
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube → Audio + Transcription API is running.",
        "usage": {
            "/convert": "POST {'url': 'https://youtube.com/...'} → dapatkan mp3_url",
            "/transcribe": "POST {'url': 'https://youtube.com/...'} → dapatkan teks transkripsi"
        }
    })


@app.post("/convert")
def convert():
    try:
        body = request.get_json(force=True) or {}
        url = body.get("url")
        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get("url")
            title = info.get("title", "Unknown Title")

        return jsonify({
            "status": "success",
            "title": title,
            "mp3_url": audio_url
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.post("/transcribe")
def transcribe():
    """
    Endpoint untuk konversi langsung dari URL YouTube ke teks menggunakan OpenAI Whisper.
    """
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        # Ambil link audio terbaik dari YouTube
        ydl_opts = {"format": "bestaudio/best", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get("url")
            title = info.get("title", "Unknown Title")

        # Unduh audio file sementara
        temp_filename = "temp_audio.webm"
        r = requests.get(audio_url, stream=True)
        with open(temp_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)

        # Kirim ke OpenAI Whisper API
        with open(temp_filename, "rb") as audio_file:
            transcript = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        # Hapus file sementara
        os.remove(temp_filename)

        return jsonify({
            "status": "success",
            "title": title,
            "text": transcript.text
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
