"""The deployed application, written here rather than built by ADK.

This used to call ADK's `get_fast_api_app`, which meant the container served
the developer UI and ADK's REST API. It no longer does either. The developer UI
cannot be opened in a browser against a private Cloud Run service anyway, and
it is a large Angular application the workshop uses one button of, so the
deployed service serves pages of our own instead. See ADR-0001.

The developer UI is still where the hour's payoff happens. It just happens
locally, under `adk web`, against the same agent package, unchanged.

So this is a plain FastAPI app with the records page mounted on it (issue #9)
and the upload page and its analyze endpoint beside it (issue #57), run by
uvicorn the way Cloud Run needs: the port comes from `$PORT` rather than a
flag, and the app binds `0.0.0.0`, because a container that binds localhost
fails its startup probe. Sessions live in memory, since a Cloud Run instance's
disk is memory and anything that matters is written to Firestore by the
persistence tool.
"""

import os

import uvicorn
from fastapi import FastAPI

from invoice_agent import records, upload

app = FastAPI(title="Invoice agent")

app.include_router(records.router)
app.include_router(upload.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
