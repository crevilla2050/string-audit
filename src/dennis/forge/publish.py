import os
import urllib.request

from dennis.forge.config import load_config


def publish_artifact(path: str):
    if not os.path.exists(path):
        raise Exception("Artifact not found")

    config = load_config()
    server = config.get("server")
    token = config.get("token")

    if not server:
        raise Exception("No server configured")

    if not token:
        raise Exception("Not authenticated")

    with open(path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        f"{server}/artifacts/upload",
        method="POST",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
    )

    urllib.request.urlopen(req)