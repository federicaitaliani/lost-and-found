from http.server import BaseHTTPRequestHandler
import os, time, json, base64, urllib.request, urllib.parse

ANTHROPIC_API_KEY     = "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"
BLOB_READ_WRITE_TOKEN = os.environ["BLOB_READ_WRITE_TOKEN"]
KV_REST_API_URL       = os.environ["KV_REST_API_URL"]
KV_REST_API_TOKEN     = os.environ["KV_REST_API_TOKEN"]


def blob_upload(filename, jpeg_bytes):
    url = "https://blob.vercel-storage.com/" + filename
    req = urllib.request.Request(
        url,
        data=jpeg_bytes,
        method="PUT",
        headers={
            "Authorization": "Bearer " + BLOB_READ_WRITE_TOKEN,
            "Content-Type": "image/jpeg",
            "x-api-version": "7",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result["url"]


def kv_command(*args):
    req = urllib.request.Request(
        KV_REST_API_URL,
        data=json.dumps(list(args)).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer " + KV_REST_API_TOKEN,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("result")

def kv_get_items():
    raw = kv_command("GET", "items")
    return json.loads(raw) if raw else []

def kv_set_items(items):
    kv_command("SET", "items", json.dumps(items))


def ask_claude(jpeg_bytes):
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
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
                {"type": "text", "text": "You are analyzing a photo taken for a lost and found box. Describe the lost item you see — include color, type of object, any visible brand, text, or distinguishing features. Be specific and concise so a student can identify if it's theirs."},
            ],
        }],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["content"][0]["text"]


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        jpeg_bytes = self.rfile.read(length)

        try:
            filename    = str(int(time.time())) + ".jpg"
            blob_url    = blob_upload(filename, jpeg_bytes)
            description = ask_claude(jpeg_bytes)

            item = {
                "filename":    filename,
                "url":         blob_url,
                "description": description,
                "time":        time.strftime("%B %d, %Y at %I:%M %p", time.localtime()),
            }

            items = kv_get_items()
            kv_set_items([item] + items[:99])

            print("Saved: " + filename)
            print("Claude: " + description)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            print("Upload error: " + str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        pass
