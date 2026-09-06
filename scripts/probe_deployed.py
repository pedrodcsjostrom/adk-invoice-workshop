"""Drive the deployed agent over HTTP, the way the upload page does.

Point it at a running Origin shim (or a local container) and it uploads one
invoice, waits for the answer and prints the record plus a timing. It exists so
the deploy path can be proved without a human at a browser, and so the run of
show has a number for "how long does the first analysis take".

    python scripts/probe_deployed.py samples/invoices/01-northwind-clean.pdf
    python scripts/probe_deployed.py <invoice> http://localhost:8099

It used to create a session and post to ADK's `/run`. The deployed application
no longer mounts ADK's REST API (ADR-0002), so it posts the file to `/analyze`
instead — one multipart request, one record back, which is the same contract the
upload page uses and therefore the thing worth proving (#55).
"""

import json
import mimetypes
import os
import sys
import time
import urllib.request
import uuid

BASE = "http://localhost:8080"


def _multipart(path: str) -> tuple[bytes, str]:
    """One file as a multipart body, built by hand.

    The kit's scripts run on a clean laptop with nothing pip-installed, so this
    stays on the standard library rather than reaching for `requests`.
    """
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path)[0] or "application/pdf"
    with open(path, "rb") as handle:
        document = handle.read()

    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{os.path.basename(path)}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            document,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _headers(content_type: str) -> dict:
    """Auth, only when talking to the service without the shim.

    Through the Origin shim there is nothing to send: the proxy it runs signs
    each request. Set INVOICE_ID_TOKEN to `$(gcloud auth print-identity-token)`
    to hit the run.app URL directly, which is what you do when the
    cloud-run-proxy component will not install.
    """
    headers = {"Content-Type": content_type}
    token = os.environ.get("INVOICE_ID_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def main(path: str) -> int:
    body, content_type = _multipart(path)
    request = urllib.request.Request(
        f"{BASE}/analyze", data=body, headers=_headers(content_type), method="POST"
    )

    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read())
    elapsed = time.monotonic() - started

    # Every outcome comes back as 200 carrying the same shape, refusals
    # included (#58), so a failure is read off the body rather than off a
    # status code.
    print(f"trace: {result.get('trace_summary') or 'none'}")
    print(f"elapsed: {elapsed:.1f}s")

    record = result.get("record")
    if record is None:
        print(result.get("message") or "no record returned", file=sys.stderr)
        return 1

    print(f"adds up: {'yes' if result.get('validation_passed') else 'no'}")
    print(f"archived: {result.get('source_uri') or 'nothing archived'}")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    if len(sys.argv) > 2:
        BASE = sys.argv[2]
    raise SystemExit(main(sys.argv[1]))
