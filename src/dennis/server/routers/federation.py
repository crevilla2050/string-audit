from fastapi import APIRouter, Query
import mysql.connector

router = APIRouter(prefix="/api/federation", tags=["federation"])

DB_CONFIG = {
    "host": "localhost",
    "user": "dennis",
    "password": "dennis",
    "database": "db_dennis_core"
}


def get_db():
    # This function establishes a connection to the MySQL database using the configuration provided in DB_CONFIG
    # It returns a connection object that can be used to interact with the database
    # The ** operator unpacks the DB_CONFIG dictionary into keyword arguments for the connect function
    return mysql.connector.connect(**DB_CONFIG)


# --------------------------------------------------------
# FEDERATION FEED
# --------------------------------------------------------
@router.get("/artifacts")
def federation_artifacts(
    since: str | None = Query(default=None),
    limit: int = Query(default=100)
):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if since:
        cur.execute(
            """
            SELECT chr_artifact_hash AS artifact_hash,
                   chr_payload_hash AS payload_hash,
                   ts_created
            FROM tbl_artifact_objects
            WHERE ts_created > %s
            ORDER BY ts_created ASC
            LIMIT %s
            """,
            (since, limit),
        )
    else:
        cur.execute(
            """
            SELECT chr_artifact_hash AS artifact_hash,
                   chr_payload_hash AS payload_hash,
                   ts_created
            FROM tbl_artifact_objects
            ORDER BY ts_created ASC
            LIMIT %s
            """,
            (limit,),
        )

    rows = cur.fetchall()
    conn.close()

    return {"artifacts": rows}


# --------------------------------------------------------
# FEDERATION ARTIFACT METADATA
# --------------------------------------------------------
@router.get("/artifacts/{artifact_hash}")
def federation_artifact_metadata(artifact_hash: str):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT chr_artifact_hash AS artifact_hash,
               chr_payload_hash AS payload_hash,
               int_size_bytes AS size_bytes,
               ts_created
        FROM tbl_artifact_objects
        WHERE chr_artifact_hash = %s
        """,
        (artifact_hash,),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"error": "artifact not found"}

    return row