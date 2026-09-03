"""The one deployable: the ADK developer UI and the records page, one process.

`adk web` is a thin wrapper around the same FastAPI application this module
builds, so mounting one extra route onto it costs a deployment rather than
buying one. Cloud Run runs this with uvicorn on $PORT.
"""

import os

from google.adk.cli.fast_api import get_fast_api_app

from invoice_agent.records import router

# The directory holding agent packages — the repo root, which holds
# `invoice_agent/`. The UI lists it as the "invoice_agent" app.
AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = get_fast_api_app(agents_dir=AGENTS_DIR, web=True)

# Before the UI's own routes, because the web UI claims a catch-all.
app.include_router(router)


def main() -> None:
    """Run the service the way Cloud Run does, for checking it locally."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))


if __name__ == "__main__":
    main()
