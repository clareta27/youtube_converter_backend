from flask import Flask, request, jsonify
import yt_dlp
import os
import random

app = Flask(__name__)

# Daftar proxy kamu diubah ke format http://username:password@ip:port
PROXIES = [
    "http://lejpeagh:q63quxughpxz@142.111.48.253:7030",
    "http://lejpeagh:q63quxughpxz@31.59.20.176:6754",
    "http://lejpeagh:q63quxughpxz@23.95.150.145:6114",
    "http://lejpeagh:q63quxughpxz@198.23.239.134:6540",
    "http://lejpeagh:q63quxughpxz@45.38.107.97:6014",
    "http://lejpeagh:q63quxughpxz@107.172.163.27:6543",
    "http://lejpeagh:q63quxughpxz@64.137.96.74:6641",
    "http://lejpeagh:q63quxughpxz@216.10.27.159:6837",
    "http://lejpeagh:q63quxughpxz@142.111.67.146:5611",
    "http://lejpeagh:q63quxughpxz@142.147.128.93:6593",
]

@app.get("/")
def home():
    return jsonify({
        "message": "✅ YouTube → Audio extractor API (cookies + proxy) ready.",
        "usage": "POST /convert {'url': 'https://www.youtube.com/watch?v=...'}"
    })

@app.post("/convert")
def convert():
    data = request.get_json()
    youtube_url = data.get("url")

    if not youtube_url:
        return jsonify({"status": "error", "message": "Missing YouTube URL"}), 400

    # 1️⃣ cek cookies.txt
    cookies_path = os.path.join(os.getcwd(), "cookies.txt")
    has_cookies = os.path.exists(cookies_path)

    # 2️⃣ pilih proxy acak
    proxy_to_use = random.choice(PROXIES)
    print(f"🌐 Selected proxy: {proxy_to_use}")

    # 3️⃣ konfigurasi yt-dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "nocheckcertificate": True,
        "skip_download": True,
        "geo_bypass": True,
    }

    if has_cookies:
        ydl_opts["cookiefile"] = cookies_path
        print(f"🍪 Using cookies: {cookies_path}")
    else:
        ydl_opts["proxy"] = proxy_to_use
        print("⚠️ No cookies found, using proxy fallback")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            formats = info.get("formats", [])
            title = info.get("title", "Unknown title")

            audio_format = next(
                (f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"),
                None
            )
            if not audio_format:
                return jsonify({"status": "error", "message": "No audio format found"}), 500

            mp3_url = audio_format.get("url")

            return jsonify({
                "status": "success",
                "title": title,
                "mp3_url": mp3_url
            })

    except Exception as e:
        print("❌ yt-dlp error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
