# adk-invoice-workshop

The 60-minute Google ADK invoice-analyzer workshop kit. Right now it holds the
thinnest end-to-end slice: an invoice PDF goes in, a structured JSON record comes
out, via one ADK agent running on Vertex AI.

## Attending the workshop?

Do [docs/PREFLIGHT.md](docs/PREFLIGHT.md) the day before — 30 minutes, and it
ends with one script that says whether tomorrow will work:

```bash
./scripts/preflight_check.sh
```

## Run it

You need a GCP project with billing and the Vertex AI API enabled.

```bash
gcloud services enable aiplatform.googleapis.com
gcloud config set project <your-project-id>
gcloud auth application-default login

cp invoice_agent/.env.example invoice_agent/.env   # then set GOOGLE_CLOUD_PROJECT
uv sync
uv run python scripts/make_invoice.py              # writes samples/sample_invoice.pdf
```

Headless, which prints every tool call and checks the JSON against the schema:

```bash
uv run python scripts/smoke.py
```

The developer UI, where you upload the PDF yourself:

```bash
uv run adk web .
```

Or the deployable, which is the same UI plus the records page on one port — the
form Cloud Run runs:

```bash
uv run python -m invoice_agent.server   # http://localhost:8080/records
```

## Where the records go

Nothing is configured on a laptop: saved records append to `.local_records.jsonl`
and the analysed document is copied into `.local_archive/`. On Cloud Run,
Terraform sets `FIRESTORE_DATABASE` and `INVOICE_BUCKET`, and the same calls
write to Firestore and Cloud Storage instead. The records page reads whichever
backend is live through the service's own identity, so there is no browser
sign-in.

Keep `GOOGLE_CLOUD_LOCATION=global`. `gemini-3.5-flash` is not served from
`us-central1`, whatever the blog posts say.

## What it costs, and how to stop it

The hour costs **$0.11 to $0.21**, all of it Gemini tokens; everything else in
the stack is free at this volume. On the $300 free trial you cannot be billed
at all, because Google closes a trial account rather than upgrading it.

When you are finished, run this and read what it prints:

```bash
scripts/teardown.sh
```

It destroys the stack, deletes the Cloud Build staging bucket that
`terraform destroy` leaves behind, and then lists anything still alive in the
project. [docs/COST.md](docs/COST.md) has the details, including the
`--delete-project` option, which is the surer end to a project you created only
for this workshop.

## Layout

- `invoice_agent/` — the agent: one `LlmAgent`, three tools, one output schema
- `invoice_agent/store.py` — records and archived documents, local or cloud
- `invoice_agent/records.py` — the records page
- `invoice_agent/server.py` — the deployable: developer UI plus records page
- `scripts/make_invoice.py` — generates the sample invoice, `--big` for a 10 MB one
- `scripts/smoke.py` — headless end-to-end check
- `scripts/preflight_check.sh` — what every attendee runs the day before
- `scripts/teardown.sh` — destroys the stack and proves the project is empty
- `docs/PREFLIGHT.md` — the attendee-facing setup, and `docs/preflight-email.md` for the host
- `docs/host-runbook.md` — what the host does, day before and day of, with the commands
- `infra/` — the Terraform stack every attendee applies to their own project
- `docs/COST.md` — what the hour costs, and what survives a teardown
- `docs/research/` — what was verified, and how

`CONTEXT.md` at the root is the glossary the docs share.

Planning for the kit lives on the issue tracker as
[Map: 60-minute Google ADK invoice-analyzer workshop kit](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/1).

## Licence

MIT — see [LICENSE](LICENSE). Take it home and build on it.
