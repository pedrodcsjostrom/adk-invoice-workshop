# Tuning the failure-then-retry moment

What was observed while building the three tools and trying to make the
workshop's centrepiece dependable, on 2026-09-03. Every number below came from
`scripts/trials.py` against Vertex AI, not from reasoning about the model.

Configuration: `google-adk` 2.8.0, `gemini-3.5-flash` at `GOOGLE_CLOUD_LOCATION=global`,
application default credentials, project `adk-invoice-wkshp-dev`.

## The headline

**The agent will not misread these invoices, so the demo cannot be built on it
misreading one.** Across every document in the corpus and every trap built for
this ticket, extraction was correct on the first pass:

| Document | Trap | Runs | Correct first pass |
| --- | --- | --- | --- |
| `05-vertex-missable-line.pdf` | Charge row below the table rule in small print | 10 | 10 |
| `10-ridgeway-terms-charge.pdf` | Charge stated as a sentence in the terms, no row | 6 | 6 |
| `11-kestrel-credit-line.pdf` | Credit printed as `620.00 CR`, not as a negative | 6 | 6 |
| `06-meridian-multipage.pdf` | 23 lines over 3 pages, total on the last | 3 | 3 |
| `07-tallgrass-scan.jpg` | Rotated, grainy, unevenly lit photograph | 3 | 3 |
| `01`, `09` | Clean baselines | 6 | 6 |

Thirty-three for thirty-three. Files 10 and 11 were built specifically for this
ticket, after 05 turned out to be too easy, and they were no harder.

This is worth stating plainly because the instinct is to keep making the
document harder. Do not. A document just hard enough to defeat the first pass
would defeat the second pass at a similar rate, which turns the best minute of
the hour into a coin flip in front of a room.

## What the demo does instead

The failure that is real and repeatable is the one in the document, not in the
agent. `04-halden-rigged-total.pdf` has line arithmetic that is internally
correct and a stated total 1,400.00 above the sum of its lines. Nothing can
reconcile it, and the agent handles that correctly and identically every time.

The tuned instruction makes the second look explicit. Before this change the
agent failed the check once and went straight to saving, reasoning quite
sensibly that a total which does not match cannot be argued with. Correct, but
invisible: the room saw one failed tool call and then a save. The instruction
now requires a second call to the arithmetic check after re-reading, even when
the second reading is unchanged, because that second call is what puts "the
agent went back to the document" on screen.

Observed on stage, in the developer UI event pane:

```
check_invoice_arithmetic  5 lines, total 12,671.00  ->  ok: false, short by 1,400.00
check_invoice_arithmetic  5 lines, total 12,671.00  ->  ok: false, short by 1,400.00
lookup_supplier           "Halden Industrial Fasteners AS"  ->  SUP-0004
save_invoice_record       ->  validation_passed: false
```

Ten consecutive runs produced exactly that shape, with no run ever attempting a
third check. Wall clock was 27 to 34 seconds per run, meaningfully slower than
the 11 to 20 seconds a clean invoice takes, because of the extra round trip.

**Ten consecutive clean runs were observed.** That is the number the ticket
asked for.

## What happens when it cannot reconcile

It saves anyway, flagged. The record keeps every number exactly as printed,
discrepancy included, and `save_invoice_record` recomputes the arithmetic itself
and stores `validation_passed: false` alongside. The agent is never allowed to
adjust a number to close a gap, and never allowed to drop or invent a line.

Two reasons for saving rather than refusing. A refusal gives the room nothing to
look at afterwards, whereas a flagged row on the records page is pointable. And
an accounts payable system that silently discards invoices it dislikes is the
wrong lesson to teach.

The store, not the agent, decides `validation_passed`. The agent reports what it
read; the process checks it. That distinction is worth a sentence on stage.

## Consequences for the rest of the kit

**The run of show needs to budget 30 seconds of silence.** The rigged invoice
takes half a minute because it makes an extra model round trip. That is a long
time in front of a room and needs something to say over it.

**Vertex AI needs billing linked, not just the API enabled.** Enabling
`aiplatform.googleapis.com` on a project with no billing account gives a
`SERVICE_DISABLED` 403; linking billing then gives a second, different 403 until
it propagates. Both errors name the fix in their message. The pre-flight should
have attendees confirm billing is linked, not merely that APIs are on.

## What was not covered

Cloud Run, Firestore and Cloud Storage. The persistence tool here writes to a
local JSON Lines file behind `invoice_agent/store.py`; the real backend and the
records page belong to their own ticket. Nothing above it changes when they land.
