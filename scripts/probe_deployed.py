"""Drive the deployed agent over HTTP, the way the browser does.

Point it at a running `gcloud run services proxy` (or a local container) and it
uploads one invoice, waits for the answer and prints the record plus a timing.
It exists so the deploy path can be proved without a human at a browser, and so
the run of show has a number for "how long does the first analysis take".

    python scripts/probe_deployed.py samples/invoices/01-northwind-clean.pdf
    python scripts/probe_deployed.py <invoice> http://localhost:8099
"""

import base64
import json
import mimetypes
import sys
import time
import urllib.request

BASE = "http://localhost:8080"
APP = "invoice_agent"
USER = "probe"


def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main(path: str) -> int:
    session_id = f"probe-{int(time.time())}"
    _post(f"/apps/{APP}/users/{USER}/sessions/{session_id}", {})

    with open(path, "rb") as handle:
        document = base64.b64encode(handle.read()).decode()
    mime = mimetypes.guess_type(path)[0] or "application/pdf"

    started = time.monotonic()
    events = _post(
        "/run",
        {
            "app_name": APP,
            "user_id": USER,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [
                    {"text": "Process this invoice."},
                    {"inline_data": {"mime_type": mime, "data": document}},
                ],
            },
        },
    )
    elapsed = time.monotonic() - started

    # The REST API serialises by alias, so parts carry `functionCall`, not the
    # `function_call` the Python objects use. Accept both.
    calls = [
        (part.get("functionCall") or part.get("function_call"))["name"]
        for event in events
        for part in (event.get("content") or {}).get("parts") or []
        if part.get("functionCall") or part.get("function_call")
    ]
    texts = [
        part["text"]
        for event in events
        for part in (event.get("content") or {}).get("parts") or []
        if part.get("text")
    ]

    print(f"tool calls: {' -> '.join(calls) or 'none'}")
    print(f"elapsed: {elapsed:.1f}s")
    if not texts:
        print("no answer returned", file=sys.stderr)
        return 1
    print(texts[-1])
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    if len(sys.argv) > 2:
        BASE = sys.argv[2]
    raise SystemExit(main(sys.argv[1]))
