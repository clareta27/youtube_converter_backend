import os
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# OpenAI SDK v1.x
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)


# ---------- helpers ----------
def extract_video_id(youtube_url: str) -> str:
    """
    Support formats:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/shorts/VIDEO_ID
    """
    try:
        u = urlparse(youtube_url)
        if u.netloc.endswith("youtu.be"):
            return u.path.strip("/")

        if "watch" in u.path:
            return parse_qs(u.query).get("v", [""])[0]

        # shorts
        if "/shorts/" in u.path:
            return u.path.split("/shorts/")[1].split("/")[0]

        # fallback: last path segment
        return u.path.strip("/").split("/")[-1]
    except Exception:
        return ""


def fetch_transcript(video_id: str, lang_priority=None) -> str:
    """
    Try to fetch transcript in preferred languages with fallbacks.
    """
    if lang_priority is None:
        # urutan prioritas: Indonesia & English + auto-captions
        lang_priority = ["id", "id-**", "en", "en-US", "en-GB", "en-**"]

    try:
        # Try prioritized languages
        for lang in lang_priority:
            try:
                items = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                return " ".join([x["text"] for x in items if x.get("text")])
            except NoTranscriptFound:
                continue

        # As ultimate fallback, try any available transcript
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        first = transcripts.find_transcript([t.language_code for t in transcripts])
        items = first.fetch()
        return " ".join([x["text"] for x in items if x.get("text")])
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        raise RuntimeError(f"Transcript not available: {str(e)}")


def build_prompt(mode: str) -> str:
    mode = (mode or "").lower()
    if mode == "bullet":
        return "Summarize the following text into concise bullet points:"
    if mode == "mindmap":
        return "Create a hierarchical, mind-map style outline of the following text:"
    # default = paragraph
    return "Summarize the following text in a short, clear paragraph:"


def summarize_with_openai(text: str, mode: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Server missing OPENAI_API_KEY.")

    prompt = build_prompt(mode)
    # OpenAI Responses API (recommended for 4.1 / 4.1-mini)
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}\n\n{text}"}
                ],
            }
        ],
    )
    # SDK convenience: join all text parts
    return resp.output_text.strip()


# ---------- routes ----------
@app.get("/")
def root():
    return jsonify({"message": "OK", "usage": "POST /convert { url, mode? }"})

@app.post("/convert")
def convert():
    """
    Request JSON:
      { "url": "https://www.youtube.com/watch?v=...", "mode": "bullet|paragraph|mindmap" }

    Response JSON (success):
      {
        "status": "success",
        "title": "...",
        "transcript": "...",
        "summary": "..."
      }
    """
    try:
        body = request.get_json(force=True) or {}
        url = body.get("url", "").strip()
        mode = body.get("mode", "bullet")

        if not url:
            return jsonify({"status": "error", "message": "Missing 'url'"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"status": "error", "message": "Invalid YouTube URL"}), 400

        # 1) Fetch transcript (no cookies/login required)
        transcript = fetch_transcript(video_id)

        # Optional: quick & dirty title from first 12 words
        title_guess = " ".join(transcript.split()[:12]) + ("..." if len(transcript.split()) > 12 else "")

        # 2) Summarize with OpenAI
        summary = summarize_with_openai(transcript, mode)

        return jsonify({
            "status": "success",
            "title": title_guess,
            "transcript": transcript,
            "summary": summary
        })

    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"{type(e).__name__}: {str(e)}"}), 500


if __name__ == "__main__":
    # allow Render/railway/heroku style PORT
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
