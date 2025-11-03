from flask import Flask, request, jsonify
import yt_dlp
import os
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "message": "✅ YouTube Audio Direct Link API (no download, no login)",
        "usage": "POST /getaudio {'url': 'https://www.youtube.com/watch?v=...'}"
    })


def extract_audio_direct(url):
    """
    Ambil direct audio stream URL menggunakan yt-dlp,
    fallback ke piped.video jika YouTube menolak akses (CAPTCHA).
    """
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "format": "bestaudio/best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            audio_streams = [f for f in formats if f.get("acodec") != "none"]
            if not audio_streams:
                raise Exception("No audio streams found")
            best_audio = sorted(audio_streams, key=lambda x: x.get("abr", 0), reverse=True)[0]
            return {
                "title": info.get("title"),
                "audio_url": best_audio["url"],
                "mime": best_audio.get("mime_type", "audio/webm"),
                "source": "yt-dlp"
            }
    except Exception as e:
        print(f"⚠️ yt-dlp failed: {e}")
        try:
            # fallback ke piped.video
            video_id = None
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            if not video_id:
                raise Exception("Cannot extract video ID")

            res = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}", timeout=10)
            data = res.json()
            audio_streams = data.get("audioStreams", [])
            if not audio_streams:
                raise Exception("No audio streams found via Piped API")
            # pilih bitrate terendah biar cepat
            best_audio = sorted(audio_streams, key=lambda x: x.get("bitrate", 0))[0]
            return {
                "title": data.get("title", "Unknown Title"),
                "audio_url": best_audio["url"],
                "mime": best_audio.get("mimeType", "audio/webm"),
                "source": "piped"
            }
        except Exception as e2:
            raise Exception(f"Piped fallback failed: {e2}")


@app.route("/getaudio", methods=["POST"])
def getaudio():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    try:
        result = extract_audio_direct(url)
        return jsonify({
            "title": result["title"],
            "audio_url": result["audio_url"],
            "mime": result["mime"],
            "source": result["source"],
            "status": "✅ success"
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "❌ failed"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
