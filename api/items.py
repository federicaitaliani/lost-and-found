from http.server import BaseHTTPRequestHandler
import os, json, urllib.request

KV_REST_API_URL   = os.environ["KV_REST_API_URL"]
KV_REST_API_TOKEN = os.environ["KV_REST_API_TOKEN"]


def kv_get_items():
    req = urllib.request.Request(
        KV_REST_API_URL,
        data=json.dumps(["GET", "items"]).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        raw = json.loads(resp.read()).get("result")
    return json.loads(raw) if raw else []


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        items = kv_get_items()
        body = json.dumps(items, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass
