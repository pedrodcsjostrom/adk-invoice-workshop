# One agent run per invoice, even when a batch is uploaded

A batch is picked in the browser and sent one document per request, each in its
own fresh session with no history carried between documents. The agent never
sees a batch.

The re-read is the whole workshop, and it depends on the model going back to a
single document after a failed arithmetic check. Put eight invoices in one
context and the second look has eight documents to confuse. Keeping one run per
invoice also leaves the agent instruction and its single-record output schema
exactly as attendees typed them.

## Consequences

A batch is slower than it would be batched into one call, and it costs one
model call per document. Both are acceptable at the documented cap of twenty
documents. In exchange, one bad document fails one row rather than the batch,
and per-document progress is free.
