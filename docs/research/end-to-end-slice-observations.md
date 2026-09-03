# The end-to-end slice: what actually happened

Observations from the first working run of an ADK invoice agent against Vertex AI
from a laptop, on 2026-09-03. This is the observed companion to
`adk-2x-vertex-ai-facts.md`, which was assembled from documentation and source.
Every claim below was seen, not read.

## The configuration that worked

| Component | Observed |
| --- | --- |
| google-adk | 2.8.0 |
| google-genai | 2.22.0 |
| pydantic | 2.13.5 |
| Python | 3.12.3 |
| Model | `gemini-3.5-flash` |
| Location | `global` |
| Dev UI version banner | Agent Development Kit 2.8.0 |

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=<project-id>
GOOGLE_CLOUD_LOCATION=global
```

Authentication was application default credentials only. No API key was set at
any point.

```bash
uv sync
uv run python scripts/smoke.py            # headless
uv run adk web .                          # developer UI
```

## The five things this slice was asked to confirm

### 1. `gemini-3.5-flash` resolves at location `global` — confirmed

First call succeeded, 8.8 seconds wall clock for a one-page invoice including one
tool round trip. No allowlisting, no quota request, no model-garden enablement
step. Enabling `aiplatform.googleapis.com` was sufficient.

### 2. `us-central1` genuinely fails — confirmed

Verbatim, and worth putting on a slide because it is what an attendee who copies
a blog post will see:

```
google.genai.errors.ClientError: 404 NOT_FOUND. {'error': {'code': 404,
'message': 'Publisher model `projects/<project>/locations/us-central1/publishers/google/models/gemini-3.5-flash`
was not found or your project does not have access to it. Ensure you are using a
valid model name and that the model is available in the specified region. For
more information, see: https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations.',
'status': 'NOT_FOUND'}}
```

Two teaching points. The message names the full model path including the region,
so it is self-diagnosing if you read it. But ADK 2.x retries through `tenacity`
first, so the failure arrives after a delay and behind a long traceback with the
useful line last. Attendees will need to be told to read the bottom.

### 3. `output_schema` together with `tools` — confirmed

This was the riskiest assumption in the kit and it holds. One `LlmAgent` with
`tools=[lookup_vendor]` and `output_schema=InvoiceRecord` called the tool, used
the tool's return value in its answer, and emitted JSON that validated against
the Pydantic model. The `vendor_id` field in the output came from the tool, not
from the document, which proves the tool result genuinely reached the final
structured answer.

The one-agent, three-tool design needs no workaround.

### 4. Upload ceiling — no ceiling found below 10 MB

A 10,807,128-byte PDF went through the inline path and returned a correct record.
The developer UI accepted a small PDF through a real browser upload. Note the
model's own documented limits still apply: 50 MB and 3,000 pages.

One caveat: the 10 MB file was exercised through the same inline-bytes path the
UI uses, but sent headlessly. A browser upload of a 10 MB file was not performed,
so a request-body limit in the UI's own transport at that size remains untested.
It is unlikely to matter, since workshop invoices are a few hundred kilobytes.

### 5. Local artifact storage — writes into the agent source directory

`adk web` defaults to `--use_local_storage`, which creates:

```
invoice_agent/.adk/session.db
```

That is inside the agent package, so the kit repository needs `.adk/` in
`.gitignore`. Added. Attendees who clone and run will otherwise see an untracked
SQLite file appear next to their agent code. `--artifact_service_uri memory://`
suppresses it if the workshop would rather leave no trace.

## Three things that surprised us

**The ADC quota project does not have to match.** The machine's application
default credentials carried `quota_project_id` for an unrelated project while
`GOOGLE_CLOUD_PROJECT` named the Vertex project, and the run still succeeded.
The pre-flight advice to run `gcloud config set project` before
`application-default login` is still worth keeping, because it makes the two
agree and removes a whole class of confusion, but a mismatch is not automatically
fatal. Do not teach it as one.

**Two warnings print on every single run.** Both are harmless and both look
alarming to a beginner. Decide whether to suppress them or explain them, but do
not let attendees meet them cold:

```
UserWarning: [EXPERIMENTAL] feature FeatureName.JSON_SCHEMA_FOR_FUNC_DECL is enabled.
Warning: there are non-text parts in the response: ['function_call'], returning
concatenated text result from text parts. Check the full candidates.content.parts
accessor to get the full model response.
```

The second one fires precisely because the agent used a tool, which is the
centrepiece of the workshop. It will be on screen during the best moment of the
hour.

**The dev UI opens with a telemetry consent dialog.** First load shows "Help
Improve ADK!" with Enable and No Thanks. Every attendee will hit it
simultaneously. It should be one line in the pre-flight, along with the fact that
`adk telemetry disable` settles it from the CLI.

## Also worth knowing

The developer UI's event view is a better teaching surface than expected. It
showed the invocation as four numbered events — the user message with the
attached PDF, the `lookup_vendor` call with its argument, the tool result, then
the final JSON — beside a rendered graph of `invoice_analyzer` pointing at
`lookup_vendor`. The failure-then-retry moment the workshop is built around will
be legible in that pane without any extra tooling.

`tools=[lookup_vendor]` keeps the plain function on the agent object; the
`FunctionTool` wrapping happens later, so `root_agent.tools[0].name` raises
`AttributeError` on a freshly constructed agent. Only matters if the kit writes
tests that introspect the agent.

## What this slice did not cover

Cloud Run deployment, Firestore, Cloud Storage, the records page, the arithmetic
validation tool and the rigged invoice. All belong to their own tickets. This was
the thinnest slice that proves the foundation.

The run used an existing billed project rather than a freshly created one, so the
"fresh project" path in the pre-flight is still confirmed only as far as
enabling `aiplatform.googleapis.com` and using application default credentials.
