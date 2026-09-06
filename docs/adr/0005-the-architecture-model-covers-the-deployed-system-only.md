# The architecture model covers the deployed system only

`docs/architecture/workspace.dsl` models what an attendee applies to their own
Google Cloud project, and the two things outside it that the deployed
service depends on: the Origin shim on the path in (ADR-0004) and Vertex AI
Gemini behind it. The local half of the hour is deliberately absent:
`adk web`, the developer UI, and the sandbox standing in as a model backend
for a cold arrival.

The local half is the part of the workshop nobody needs a diagram of. It is
one command, one browser tab and a trace an attendee is reading line by line,
and it is documented where it is used, in `docs/PREFLIGHT.md` and the host
runbook. The deployed half is the part with a boundary worth drawing: a
private service, a proxy in front of it, a model API beside it, and three
Google Cloud resources an attendee has never wired together before. A model
that covered both would spend most of its elements on the half that needs
them least.

## Consequences

The store's two backends are a code fact the model does not show. On a laptop
`invoice_agent/store.py` appends records to `.local_records.jsonl` and copies
the analysed document into `.local_archive/`; on Cloud Run, with
`FIRESTORE_DATABASE` set, the same two calls write to Firestore and Cloud
Storage. The model draws only the second, so a reader who has just run the
agent locally will not find the files they saw appear. The docstring at the
top of `store.py` and the "Where the records go" section of the README carry
that; the diagrams do not.

Every view added later inherits this scope, the container view included.
Putting the local half back is a decision to be taken again in a new ADR,
not a diagram someone quietly extends.
