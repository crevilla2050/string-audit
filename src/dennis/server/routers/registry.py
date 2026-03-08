from fastapi import APIRouter
import mysql.connector
import uuid

router = APIRouter(prefix="/api/registry", tags=["registry"])


DB_CONFIG = {
    "host": "localhost",
    "user": "dennis",
    "password": "dennis",
    "database": "db_dennis_core"
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


@router.post("/remotes")
def add_remote(data: dict):

    conn = get_db()
    cur = conn.cursor()

    uuid_remote = uuid.uuid4().bytes

    cur.execute(
        """
        INSERT INTO tbl_registry_remotes
        (uuid_remote, chr_remote_url)
        VALUES (%s, %s)
        """,
        (uuid_remote, data["url"]),
    )

    conn.commit()
    conn.close()

    return {"status": "ok", "url": data["url"]}


@router.get("/remotes")
def list_remotes():

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT chr_remote_url AS url
        FROM tbl_registry_remotes
        """
    )

    rows = cur.fetchall()
    conn.close()

    return {"remotes": rows}


@router.post("/sync")
def trigger_sync():

    from dennis.server.federation_sync import sync_remote

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT chr_remote_url FROM tbl_registry_remotes")

    remotes = cur.fetchall()

    for r in remotes:
        sync_remote(r["chr_remote_url"])

    conn.close()

    return {"status": "sync triggered"}