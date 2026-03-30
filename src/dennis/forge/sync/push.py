from string_audit.forge.storage.plan_storage import PlanStorage
from string_audit.forge.sync.client import SyncClient


def push_all(storage: PlanStorage, remote: str):
    client = SyncClient(remote)

    plans_root = storage.plans_dir
    uploaded = 0
    skipped = 0

    for path in plans_root.rglob("*.json"):
        hash_hex = path.stem
        data = path.read_bytes()

        if client.has(hash_hex):
            skipped += 1
            continue

        client.upload(hash_hex, data)
        uploaded += 1

    return uploaded, skipped