# The deployed service serves its own upload page, not the ADK developer UI

The developer UI cannot be opened in a browser against a private Cloud Run
service, for the reason in [ADR-0004](0004-origin-shim-is-the-way-in.md), and
even with that resolved it is a large Angular application the workshop uses one
button of. The deployed service therefore serves an upload page and a records
page of our own, and drops the developer UI.

The developer UI stays as the local tool and nothing about the local half of
the hour changes. That split is the point: the payoff at 0:31 is an attendee
watching the arithmetic check called twice in the developer UI's trace, and no
page written this week should be load-bearing under it.

## Consequences

The deployed service is a plain FastAPI application rather than one built by
ADK's `get_fast_api_app`, so ADK's REST API is no longer mounted anywhere in
the deployed path. Anything wanting to drive the deployed agent programmatically
now goes through our own endpoint. The upload page shows a one-line trace
summary per document, built from the runner's events, which is a deliberate
sliver of what the developer UI shows rather than a reimplementation of it.
