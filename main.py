from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({"message": "OK", "usage": "POST /convert { url: 'https://youtube.com/...'}"})

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

        return jsonify({"status": "success", "title": title, "mp3_url": audio_url})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
