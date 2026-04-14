from http.server import BaseHTTPRequestHandler
import os, json, urllib.request, urllib.parse

BLOB_READ_WRITE_TOKEN = os.environ["BLOB_READ_WRITE_TOKEN"]
KV_REST_API_URL       = os.environ["KV_REST_API_URL"]
KV_REST_API_TOKEN     = os.environ["KV_REST_API_TOKEN"]


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


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # Filename passed as query param: POST /api/claim?filename=1234567890.jpg
        parsed   = urllib.parse.urlparse(self.path)
        params   = urllib.parse.parse_qs(parsed.query)
        filename = (params.get("filename") or [""])[0]

        if not filename:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"missing filename")
            return

        try:
            items = kv_get_items()
            match = next((i for i in items if i["filename"] == filename), None)

            if not match:
                self.send_response(404)
                self.end_headers()
                return

            # Remove from list
            kv_set_items([i for i in items if i["filename"] != filename])

            # Delete blob
            blob_delete(match["url"])

            print(f"Claimed and deleted: {filename}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            print("Claim error:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        pass
