#!/usr/bin/env python3
import http.server
import json
import os
from urllib.parse import urlparse

STORAGE_DIR = ".dennis_forge"


def ensure_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def plan_path(hash_hex):
    return os.path.join(STORAGE_DIR, f"{hash_hex}.json")


class ForgeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/plans":
            self.list_plans()
        elif parsed.path.startswith("/plan/"):
            hash_hex = parsed.path.split("/")[-1]
            self.get_plan(hash_hex)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/plan":
            self.put_plan()
        else:
            self.send_error(404)

    def list_plans(self):
        ensure_storage()
        hashes = [
            f.replace(".json", "")
            for f in os.listdir(STORAGE_DIR)
            if f.endswith(".json")
        ]
        self.respond_json(hashes)

    def get_plan(self, hash_hex):
        path = plan_path(hash_hex)
        if not os.path.exists(path):
            self.send_error(404)
            return
        with open(path, "rb") as f:
            data = f.read()
        self.respond_bytes(data)

    def put_plan(self):
        ensure_storage()  # ← ADD THIS LINE

        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        try:
            obj = json.loads(data.decode("utf-8"))
        except Exception:
            self.send_error(400, "Invalid JSON")
            return

        from string_audit.forge.hash.canonical import canonical_hash

        hash_hex = canonical_hash(obj)
        path = plan_path(hash_hex)

        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(data)

        self.respond_json({"hash": hash_hex})

    def respond_json(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_bytes(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print("🔥 Dennis Mini Forge running on http://localhost:8000")
    http.server.HTTPServer(("0.0.0.0", 8000), ForgeHandler).serve_forever()