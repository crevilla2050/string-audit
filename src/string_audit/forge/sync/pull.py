from string_audit.forge.storage.plan_storage import PlanStorage
from string_audit.forge.sync.client import SyncClient


def pull_hashes(storage: PlanStorage, remote: str, hashes: list[str]):
    client = SyncClient(remote)

    downloaded = 0

    for h in hashes:
        if storage.exists(h):
            continue

        data = client.download(h)
        storage.put(data, expected_hash=h)
        downloaded += 1

    return downloaded