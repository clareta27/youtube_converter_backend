import os
import random
import time
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# === Load proxy list ===
def load_proxy_list():
    raw = os.getenv("PROXY_LIST", "")
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]

PROXY_LIST = load_proxy_list()

# === Ambil video_id dari YouTube URL ===
def extract_video_id(youtube_url: str) -> str:
    u = urlparse(youtube_url)
    if u.netloc.endswith("youtu.be"):
        return u.path.strip("/")
    if "watch" in u.path:
        return parse_qs(u.query).get("v", [""])[0]
    if "/shorts/" in u.path:
        return u.path.split("/shorts/")[1].split("/")[0]
    return u.path.strip("/").split("/")[-1]

# === Ambil proxy acak ===
def get_random_proxy():
    if not PROXY_LIST:
        return None
    p = random.choice(PROXY_LIST)
    return {"http": p, "https": p}

# === Delay random agar tidak dianggap spam ===
def delay_between_requests():
    delay = random.uniform(1.5, 3.5)
    time.sleep(delay)
    return delay

# === Parse caption XML ke plain text ===
def parse_caption_xml(xml_data: str):
    try:
        root = ET.fromstring(xml_data)
        texts = [n.text.strip() for n in root.findall(".//text") if n.text]
        return " ".join(texts)
    except Exception:
        return ""

# === Fetch transcript langsung via proxy ===
def fetch_transcript(video_id: str, lang_list=None):
    if lang_list is None:
        lang_list = ["id", "en", "en-US", "en-GB"]

    for lang in lang_list:
        url = f"https://youtube.com/api/timedtext?v={video_id}&lang={lang}"
        proxy = get_random_proxy()
        delay = delay_between_requests()

        try:
            res = requests.get(url, proxies=proxy, timeout=10)
            if res.status_code == 200 and res.text.strip():
                text = parse_caption_xml(res.text)
                if len(text) > 0:
                    return {
                        "success": True,
                        "lang": lang,
                        "proxy_used": proxy["http"] if proxy else "None",
                        "delay": round(delay, 2),
                        "text": text,
                    }
        except Exception as e:
            print(f"⚠️ Proxy {proxy} failed: {e}")
            continue

    return {"success": False, "message": "No transcript found or all proxies failed"}

# === Endpoint utama ===
@app.post("/transcript")
def transcript():
    try:
        data = request.get_json(force=True)
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        result = fetch_transcript(video_id)
        if not result["success"]:
            return jsonify({"status": "error", "message": result["message"]}), 404

        text = result["text"]
        return jsonify({
            "status": "success",
            "video_id": video_id,
            "language": result["lang"],
            "proxy_used": result["proxy_used"],
            "delay": result["delay"],
            "length": len(text),
            "transcript": text[:1000] + "..." if len(text) > 1000 else text,
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.get("/")
def home():
    return jsonify({
        "message": "✅ Custom YouTube Transcript Fetcher with Proxy Rotation is running",
        "proxies_loaded": len(PROXY_LIST),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
