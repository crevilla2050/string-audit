import urllib.request
import json
import mysql.connector


DB_CONFIG = {
    "host": "localhost",
    "user": "dennis",
    "password": "dennis",
    "database": "db_dennis_core"
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_remote_artifacts(url):

    endpoint = url.rstrip("/") + "/api/federation/artifacts"
    with urllib.request.urlopen(endpoint) as resp:
        data = json.loads(resp.read())

    return data.get("artifacts", [])


def sync_remote(remote_url):

    artifacts = fetch_remote_artifacts(remote_url)

    conn = get_db()
    cur = conn.cursor()

    for a in artifacts:
        artifact_hash = a["artifact_hash"]
        cur.execute(
            "SELECT 1 FROM tbl_artifact_objects WHERE chr_artifact_hash = %s",
            (artifact_hash,),
        )
        if cur.fetchone():
            continue
        print(f"Federation discovered new artifact: {artifact_hash}")

    conn.close()