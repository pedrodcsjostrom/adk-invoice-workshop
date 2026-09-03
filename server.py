"""One process, one port: the ADK developer UI and the records page.

`adk web` is a convenience wrapper around this same FastAPI app. The container
calls the app factory directly instead, for three reasons that only show up on
Cloud Run: the port comes from `$PORT`, the app must bind `0.0.0.0` rather than
localhost, and the session store must not be a file on a disk that disappears
when the instance scales to zero.

Because it is one app, the records page is a route on it (issue #9), served by
the same command on the same port. Nothing else needs to be deployed.
"""

import os

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# The directory holding agent packages, not the package itself.
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,
    # No session_service_uri: sessions live in memory. A Cloud Run instance is
    # disposable, and a sqlite file in the image would give each instance its
    # own private history while pretending to be durable. What matters survives
    # in Firestore, written by the persistence tool.
    session_service_uri=None,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8080")),
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
