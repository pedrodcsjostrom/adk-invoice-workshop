# invoice_analysis

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

- `invoice_agent/` — the agent: one `LlmAgent`, one tool, one output schema
- `scripts/make_invoice.py` — generates the sample invoice, `--big` for a 10 MB one
- `scripts/smoke.py` — headless end-to-end check
- `scripts/preflight_check.sh` — what every attendee runs the day before
- `scripts/teardown.sh` — destroys the stack and proves the project is empty
- `docs/PREFLIGHT.md` — the attendee-facing setup, and `docs/preflight-email.md` for the host
- `infra/` — the Terraform stack every attendee applies to their own project
- `docs/COST.md` — what the hour costs, and what survives a teardown
- `docs/research/` — what was verified, and how

Planning for the kit lives on the issue tracker as
[Map: 60-minute Google ADK invoice-analyzer workshop kit](https://github.com/pedrodcsjostrom/invoice_analysis/issues/1).
