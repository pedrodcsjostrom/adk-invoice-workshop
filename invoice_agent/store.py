"""Where saved records go.

The first half of the workshop runs entirely on a laptop, so the default store
is a local JSON Lines file. Issue #9 adds the Firestore and Cloud Storage
backend behind this same `save` function; nothing above it changes.
"""

import json
import os
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_PATH = os.environ.get(
    "INVOICE_RECORDS_PATH", os.path.join(_ROOT, ".local_records.jsonl")
)


def save(record: dict, validation_passed: bool, source_uri: str | None = None) -> str:
    """Append one stored document and return its id.

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
    with open(LOCAL_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(document) + "\n")
    return f"local:{os.path.basename(LOCAL_PATH)}#{_count()}"


def _count() -> int:
    if not os.path.exists(LOCAL_PATH):
        return 0
    with open(LOCAL_PATH, encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def read_all() -> list[dict]:
    """Every stored document, oldest first. The records page reads this."""
    if not os.path.exists(LOCAL_PATH):
        return []
    with open(LOCAL_PATH, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
