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
## The two fill-ins

This repo ships with two gaps in it, on purpose. Everything else is written.
Each gap is a fenced block that names its file, and both fences carry the one
command that gets you out of trouble.

1. **`check_invoice_arithmetic` in `invoice_agent/tools.py`.** The signature is
   given; the docstring and the one-line body are yours. The lesson is that a
   tool docstring is prompt text — the model reads it to decide when to call the
   tool. Check yourself in about five seconds, no cloud calls:

   ```bash
   uv run pytest tests/test_gap_arithmetic.py
   ```

   On a fresh clone that test **fails**, and that is correct. It goes green when
   you have written the tool.

2. **Steps 3 and 4 of the instruction in `invoice_agent/agent.py`.** The
   re-read: when the arithmetic check comes back `ok=false`, send the agent back
   to the document and make it check a second time. Prose, not code. It has no
   test on purpose — you verify it by running the agent and watching it call the
   arithmetic tool twice.

Fall behind, and recovery is one command per gap. It is idempotent and it does
not care how dirty your working copy is:

```bash
cp solutions/tools.py invoice_agent/tools.py
cp solutions/agent.py invoice_agent/agent.py
```

`solutions/` is visible from minute zero and holds the finished version of
exactly those two files. `tests/test_solutions_in_step.py` guards it: the
solution and the shipped file must be byte-identical outside the fence, so a
copy never silently reverts anything else.

## The pinned tag

Attendees clone in the pre-flight, the day before, and nobody pulls during the
hour. The tag is cut at the tip of the default branch, so the spoken instruction
is just a clone (#27):

```bash
git clone https://github.com/pedrodcsjostrom/adk-invoice-workshop.git
```

To pin explicitly — worth doing if a fix tag was cut after someone cloned:

```bash
git clone --branch <tag> --depth 1 https://github.com/pedrodcsjostrom/adk-invoice-workshop.git
```

Cut the tag from `main` with `scripts/cut_workshop_tag.sh workshop-YYYY-MM-DD`.
It refuses to tag a dirty or unpushed tree, runs the drift guard, and checks the
gaps are still gaps. A morning-of fix is a **new** tag — `workshop-2026-09-17.1`
— announced as a re-clone. Never a `git pull` into forty working copies.

## Layout

- `invoice_agent/` — the agent: one `LlmAgent`, three tools, one output schema
- `invoice_agent/store.py` — records and archived documents, local or cloud
- `invoice_agent/records.py` — the records page
- `invoice_agent/server.py` — the deployable: developer UI plus records page
- `scripts/make_invoice.py` — generates the sample invoice, `--big` for a 10 MB one
- `solutions/` — the finished `tools.py` and `agent.py`, the escape hatch
- `scripts/smoke.py` — headless end-to-end check
- `scripts/preflight_check.sh` — what every attendee runs the day before
- `scripts/teardown.sh` — destroys the stack and proves the project is empty
- `docs/PREFLIGHT.md` — the attendee-facing setup, and `docs/preflight-email.md` for the host
- `infra/` — the Terraform stack every attendee applies to their own project
- `docs/COST.md` — what the hour costs, and what survives a teardown
- `scripts/cut_workshop_tag.sh` — cuts the tag attendees clone
- `docs/research/` — what was verified, and how

Planning for the kit lives on the issue tracker as
[Map: 60-minute Google ADK invoice-analyzer workshop kit](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/1).

## Licence

MIT — see [LICENSE](LICENSE). Take it home and build on it.
