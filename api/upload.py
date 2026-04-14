from http.server import BaseHTTPRequestHandler
import os, time, json, base64, urllib.request

ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
BLOB_READ_WRITE_TOKEN = os.environ["BLOB_READ_WRITE_TOKEN"]
KV_REST_API_URL      = os.environ["KV_REST_API_URL"]
KV_REST_API_TOKEN    = os.environ["KV_REST_API_TOKEN"]


# ── Vercel Blob ───────────────────────────────────────────────────────────────

def blob_upload(filename, jpeg_bytes):
    req = urllib.request.Request(
        "https://blob.vercel-storage.com",
        data=jpeg_bytes,
        method="PUT",
        headers={
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "Content-Type":  "image/jpeg",
            "x-api-version": "7",
            "x-pathname":    filename,
            "x-content-type": "image/jpeg",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["url"]

def blob_delete(url):
    req = urllib.request.Request(
        "https://blob.vercel-storage.com",
        data=json.dumps({"urls": [url]}).encode(),
        method="DELETE",
        headers={
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "Content-Type":  "application/json",
        },
    )
    urllib.request.urlopen(req).close()


# ── Vercel KV (Upstash Redis REST) ────────────────────────────────────────────

def kv_command(*args):
    req = urllib.request.Request(
        KV_REST_API_URL,
        data=json.dumps(list(args)).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("result")

def kv_get_items():
    raw = kv_command("GET", "items")
    return json.loads(raw) if raw else []

def kv_set_items(items):
    kv_command("SET", "items", json.dumps(items))


# ── Claude ────────────────────────────────────────────────────────────────────

def ask_claude(jpeg_bytes):
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.b64encode(jpeg_bytes).decode(),
                    },
                },
                {"type": "text", "text": "What do you see in this image? Be concise."},
            ],
        }],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["content"][0]["text"]


# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        jpeg_bytes = self.rfile.read(length)

        try:
            filename    = f"{int(time.time())}.jpg"
            blob_url    = blob_upload(filename, jpeg_bytes)
            description = ask_claude(jpeg_bytes)

            item = {
                "filename":    filename,
                "url":         blob_url,
                "description": description,
                "time":        time.strftime("%B %d, %Y at %I:%M %p", time.localtime()),
            }

            items = kv_get_items()
            kv_set_items([item] + items[:99])   # keep newest 100

            print(f"Saved: {filename}")
            print(f"Claude: {description}")

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            print("Upload error:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        pass
