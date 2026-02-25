import urllib.request
import urllib.error


class SyncClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def has(self, hash_hex: str) -> bool:
        req = urllib.request.Request(
            f"{self.base}/plans/{hash_hex}",
            method="HEAD"
        )
        try:
            urllib.request.urlopen(req)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

    def upload(self, hash_hex: str, data: bytes):
        req = urllib.request.Request(
            f"{self.base}/plans/{hash_hex}",
            method="PUT",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)

    def download(self, hash_hex: str) -> bytes:
        with urllib.request.urlopen(f"{self.base}/plans/{hash_hex}") as r:
            return r.read()