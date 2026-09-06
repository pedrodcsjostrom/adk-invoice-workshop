# The upload page posts to an endpoint of ours, not to ADK's REST API

The upload page could speak ADK's own REST API from the browser: create a
session, base64-encode the document into an inline data part, post to the
streaming run endpoint and parse server-sent events. Instead it posts the file
to a single endpoint of ours, which builds the message, drives the agent with an
ADK `Runner`, and returns the finished record as JSON.

Two reasons, in order. Attendees read this code during the hour, and a short
endpoint plus a short page is readable where a hand-written event-stream client
is not. And a repo that is cloned at a pinned tag and re-run months later should
not depend on the shape of ADK's HTTP API staying still.

## Consequences

Streaming is given up. The page waits for a document to finish rather than
watching it think. Progress comes instead from the batch being sequenced one
document per request, so rows appear as they land. See
[ADR-0003](0003-one-agent-run-per-invoice.md).
