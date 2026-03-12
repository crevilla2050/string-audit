print("ARTIFACTS MODULE LOADED FROM:", __file__)

from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import shutil
import hashlib
import uuid

from dennis.dex import manifest
from dennis.dex.importer import import_dex
from dennis.server.storage import artifact_path, ensure_artifact_dirs
from dennis.server.db import get_connection

router = APIRouter()



@router.post("/api/artifacts")
async def upload_artifact(file: UploadFile, origin: str | None = None):

    if not file.filename.endswith(".dex"):
        raise HTTPException(status_code=400, detail="Only .dex artifacts allowed")

    try:
        print("----- DEBUG DEX INGEST V.2 -----")
        # ----------------------------------------
        # Normalize origin registry
        # ----------------------------------------

        origin_registry = origin.strip() if origin else None

        # ----------------------------------------
        # Save uploaded artifact temporarily
        # ----------------------------------------

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)


        # ----------------------------------------
        # Validate artifact
        # ----------------------------------------
        
        manifest, payload_bytes = import_dex(tmp_path)

        print("----- DEBUG DEX INGEST -----")
        print("Manifest payload:", manifest["payload"])
        print("Payload bytes length:", len(payload_bytes))
        print("Payload bytes preview:", payload_bytes[:200])
        
        payload = manifest["payload"]

        artifact_hash = payload["hash"]["value"]
        payload_hash = artifact_hash
        payload_type = payload["type"]

        if not manifest:
            raise Exception("manifest missing payload hash")
        
        # compute canonical payload hash
        import json
        from dennis.core.hash import canonical_hash
        
        payload_obj = json.loads(payload_bytes)
        
        computed_hash = canonical_hash(payload_obj)
        # manifest_hash = manifest["payload"]["hash"]

        print("Computed hash:", computed_hash)
        print("Manifest hash:", manifest_hash)
        print("-----------------------------")
        
        if computed_hash != manifest_hash:
            raise Exception("payload hash mismatch")
        
        artifact_hash = computed_hash
        payload_hash = computed_hash

        # -------------------------------------------------
        # Extract lineage parent
        # -------------------------------------------------

        provenance = manifest.get("provenance", {})
        parent_hash = provenance.get("parent")

        # ----------------------------------------
        # Determine storage path
        # ----------------------------------------

        storage_path = ensure_artifact_dirs(artifact_hash)

        if not storage_path.exists():
            shutil.move(tmp_path, storage_path)
        else:
            tmp_path.unlink(missing_ok=True)

        file_size = storage_path.stat().st_size

        # ----------------------------------------
        # Database insert
        # ----------------------------------------

        conn = get_connection()
        cur = conn.cursor()

        artifact_uuid = uuid.uuid4().bytes
        storage_uuid = uuid.uuid4().bytes

        # insert artifact object
        cur.execute(
            """
            INSERT IGNORE INTO tbl_artifact_objects (
                uuid_artifact_object,
                chr_artifact_hash,
                chr_parent_hash,
                chr_chain_status,
                chr_payload_hash,
                chr_payload_type,
                int_size_bytes,
                chr_origin_registry
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                artifact_uuid,
                artifact_hash,
                None,
                "valid",
                payload_hash,
                payload_type,
                file_size,
                origin_registry,
            ),
        )

        # insert storage metadata
        cur.execute(
            """
            INSERT INTO tbl_artifact_storage (
                uuid_storage,
                uuid_artifact_object,
                chr_storage_backend,
                chr_storage_uri,
                int_size_bytes,
                bit_primary
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                storage_uuid,
                artifact_uuid,
                "filesystem",
                f"file://{storage_path}",
                file_size,
                1,
            ),
        )

        conn.commit()

        cur.close()
        conn.close()

        # ----------------------------------------
        # Response
        # ----------------------------------------

        return {
            "artifact_hash": artifact_hash,
            "status": "stored",
            "payload_type": manifest["payload"]["type"],
            "size_bytes": file_size,
            "origin_registry": origin_registry or "local",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


    
from fastapi.responses import FileResponse
from datetime import datetime
import hashlib

from dennis.server.storage import artifact_path
from dennis.dex.importer import import_dex

@router.get("/api/artifacts")
def list_artifacts(
    limit: int = 20,
    offset: int = 0,
    payload_type: str | None = None,
    hash: str | None = None
):

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    base_query = """
        SELECT
            chr_artifact_hash,
            chr_payload_hash,
            chr_payload_type,
            int_size_bytes,
            ts_created
        FROM tbl_artifact_objects
    """

    conditions = []
    params = []

    if payload_type:
        conditions.append("chr_payload_type = %s")
        params.append(payload_type)

    if hash:
        conditions.append("chr_artifact_hash LIKE %s")
        params.append(hash + "%")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY ts_created DESC LIMIT %s OFFSET %s"

    params.extend([limit, offset])

    cur.execute(base_query, tuple(params))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    artifacts = []

    for r in rows:
        artifacts.append({
            "artifact_hash": r["chr_artifact_hash"],
            "payload_hash": r["chr_payload_hash"],
            "payload_type": r["chr_payload_type"],
            "size_bytes": r["int_size_bytes"],
            "created_at": r["ts_created"],
        })

    return {
        "count": len(artifacts),
        "limit": limit,
        "offset": offset,
        "artifacts": artifacts
    }

from fastapi.responses import HTMLResponse


@router.get("/artifact/{artifact_hash}", response_class=HTMLResponse)
def artifact_page(artifact_hash: str):

    path = artifact_path(artifact_hash)

    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return f"""
    <html>
    <head>
        <title>Dennis Artifact {artifact_hash[:8]}</title>
        <style>
        body {{
            font-family: monospace;
            background: #0e1117;
            color: #e6edf3;
            padding: 40px;
        }}
        a {{ color: #58a6ff; }}
        </style>
    </head>

    <body>

    <h2>Dennis Artifact</h2>

    <p><b>Hash:</b><br>{artifact_hash}</p>

    <p>
    <a href="/api/artifacts/{artifact_hash}">Download DEX</a>
    </p>

    <p>
    Metadata:
    <br>
    <a href="/api/artifacts/{artifact_hash}/metadata">metadata</a>
    <br>
    <a href="/api/artifacts/{artifact_hash}/signatures">signatures</a>
    <br>
    <a href="/api/artifacts/{artifact_hash}/lineage">lineage</a>
    </p>

    </body>
    </html>
    """

from fastapi.responses import FileResponse

@router.get("/api/artifacts/{artifact_hash}")
def download_artifact(artifact_hash: str):

    path = artifact_path(artifact_hash)

    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Generate the nice download filename
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"dennis-plan-v1-{ts}-{artifact_hash[:8]}.dex"

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=filename
    )

@router.get("/api/artifacts/{artifact_hash}/metadata")
def artifact_metadata(artifact_hash: str):

    path = artifact_path(artifact_hash)

    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        manifest, payload_bytes = import_dex(path)

        meta = manifest.get("meta", {})
        payload = manifest.get("payload", {})
        provenance = manifest.get("provenance", {})
        signatures = manifest.get("signatures", [])

        # ----------------------------------------
        # Registry metadata lookup
        # ----------------------------------------

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """
            SELECT
                chr_origin_registry,
                chr_chain_status,
                ts_created
            FROM tbl_artifact_objects
            WHERE chr_artifact_hash = %s
            """,
            (artifact_hash,),
        )

        row = cur.fetchone()

        cur.close()
        conn.close()

        registry_meta = None

        if row:
            registry_meta = {
                "origin_registry": row["chr_origin_registry"] or "local",
                "chain_status": row["chr_chain_status"],
                "stored_at": row["ts_created"].isoformat() if row["ts_created"] else None,
            }

        # ----------------------------------------
        # Response
        # ----------------------------------------

        metadata = {
            "artifact_hash": artifact_hash,

            "meta": {
                "format": meta.get("format"),
                "version": meta.get("version"),
                "created_at": meta.get("created_at"),
                "created_by": meta.get("created_by"),
            },

            "payload": {
                "type": payload.get("type"),
                "hash": payload.get("hash", {}).get("value"),
                "size_bytes": len(payload_bytes),
            },

            "provenance": provenance,
            "signatures": signatures,

            # registry context (not part of artifact)
            "registry": registry_meta,
        }

        return metadata

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/api/artifacts/{artifact_hash}/signatures")
def artifact_signatures(artifact_hash: str):

    artifact = artifact_metadata(artifact_hash)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {
        "artifact_hash": artifact_hash,
        "signatures": artifact.get("signatures", [])
    }

@router.get("/api/artifacts/{artifact_hash}/lineage")
def artifact_lineage(artifact_hash: str):

    chain = []
    current = artifact_hash

    while current:

        artifact = artifact_metadata(current)

        if not artifact:
            break

        chain.append({
            "artifact_hash": current,
            "payload_type": artifact.get("payload", {}).get("type"),
            "created_at": artifact.get("meta", {}).get("created_at"),
        })

        provenance = artifact.get("provenance", {})
        current = provenance.get("parent_hash")

    return {
        "root": artifact_hash,
        "lineage": chain
    }