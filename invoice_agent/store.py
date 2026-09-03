"""Where saved records go, and where the original document is archived.

Two backends behind one pair of functions. On a laptop, with no cloud
configured, records append to a local JSON Lines file and documents copy into a
local folder: the first half of the workshop needs no project at all. On Cloud
Run, `FIRESTORE_DATABASE` is set by Terraform and the same calls write to
Firestore and Cloud Storage instead. Nothing above this module changes when the
backend does — the tool, the agent and the records page cannot tell.
"""

import json
import os
import uuid
from datetime import datetime, timezone

COLLECTION = "invoices"

# Newest first, and capped: the records page is a workshop surface, not a
# reporting tool, and nobody scrolls past the invoices they just filed.
PAGE_LIMIT = 200

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_PATH = os.environ.get(
    "INVOICE_RECORDS_PATH", os.path.join(_ROOT, ".local_records.jsonl")
)
LOCAL_ARCHIVE = os.environ.get(
    "INVOICE_ARCHIVE_PATH", os.path.join(_ROOT, ".local_archive")
)

_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/plain": ".txt",
}

_client = None


def cloud() -> bool:
    """Is this process backed by Firestore, or by the local file?

    Read at call time rather than at import, so a test or a notebook can flip
    the environment without reloading the module.
    """
    return bool(os.environ.get("FIRESTORE_DATABASE"))


def save(record: dict, validation_passed: bool, source_uri: str | None = None) -> str:
    """Store one document and return its id.

    The metadata block is written here rather than by the model, so it is
    trustworthy: `validation_passed` reflects the arithmetic check this process
    ran, not what the agent claims about it.
    """
    document = {
        **record,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_uri": source_uri,
        "validation_passed": validation_passed,
    }
    if cloud():
        _, reference = _collection().add(document)
        return reference.id
    return _save_local(document)


def read_all() -> list[dict]:
    """Stored documents, newest first. The records page reads this."""
    if cloud():
        from google.cloud.firestore import Query

        snapshots = (
            _collection()
            .order_by("extracted_at", direction=Query.DESCENDING)
            .limit(PAGE_LIMIT)
            .stream()
        )
        return [{**snapshot.to_dict(), "id": snapshot.id} for snapshot in snapshots]

    if not os.path.exists(LOCAL_PATH):
        return []
    with open(LOCAL_PATH, encoding="utf-8") as handle:
        documents = [json.loads(line) for line in handle if line.strip()]
    documents.reverse()
    return documents[:PAGE_LIMIT]


def archive_source(data: bytes, mime_type: str, filename: str | None = None) -> str:
    """Keep the document the record was read from, and return where it went.

    The archive is what makes a stored record auditable: without the original,
    a disputed number has nothing to check against.
    """
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    name = f"{day}/{uuid.uuid4().hex[:12]}{_extension(mime_type, filename)}"

    bucket_name = os.environ.get("INVOICE_BUCKET")
    if bucket_name:
        from google.cloud import storage

        blob = storage.Client().bucket(bucket_name).blob(name)
        blob.upload_from_string(data, content_type=mime_type)
        return f"gs://{bucket_name}/{name}"

    path = os.path.join(LOCAL_ARCHIVE, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return f"file://{path}"


def _extension(mime_type: str, filename: str | None) -> str:
    if filename and "." in os.path.basename(filename):
        return "." + filename.rsplit(".", 1)[1].lower()
    return _EXTENSIONS.get(mime_type, ".bin")


def _collection():
    """The Firestore collection, on the named database Terraform created.

    The database name is not optional: the client defaults to `(default)`, and
    the stack deliberately does not create that one.
    """
    global _client
    database = os.environ.get("FIRESTORE_DATABASE")
    if _client is None or _client._database != database:
        from google.cloud import firestore

        _client = firestore.Client(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), database=database
        )
    return _client.collection(COLLECTION)


def _save_local(document: dict) -> str:
    document = {**document, "id": uuid.uuid4().hex[:12]}
    os.makedirs(os.path.dirname(LOCAL_PATH) or ".", exist_ok=True)
    with open(LOCAL_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(document) + "\n")
    return document["id"]
