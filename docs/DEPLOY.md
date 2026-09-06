# The deploy path

Terraform creates everything except the thing the room came to see. This is how
the agent source becomes the image the Cloud Run service runs, and how long
each step takes.

## The container

Three files: `Dockerfile`, `requirements.txt`, `server.py`.

**Why a Dockerfile rather than source deploys.** `gcloud run deploy --source`
would build with buildpacks and no Dockerfile at all, but it decides the start
command for you, and the one decision this container has to get right is the
start command. Twenty explicit lines beat a convention nobody in the room can
see.

**Why Cloud Build rather than a local `docker build`.** `gcloud builds submit`
needs nothing on an attendee's laptop but gcloud, which the pre-flight already
requires. Assuming a working Docker daemon on a managed corporate laptop is how
you lose ten minutes.

**Why `requirements.txt` when the project uses uv.** The image installs a
deployed subset with pip. `pyproject.toml` keeps the dev dependencies —
`pytest`, `reportlab` — that have no business in a runtime image, and pip is
already in the base image. `pyproject.toml` stays the source of truth for
development; the two lists must be kept honest by hand, which at two entries is
not a burden.

**Why `server.py` rather than `CMD ["adk", "web"]`.** Three things Cloud Run
requires that the CLI does not do on its own:

- The port comes from `$PORT`, not a flag.
- The app binds `0.0.0.0`. `adk web` binds localhost, and a Cloud Run container
  that binds localhost fails its startup probe with a message about the port.
- Sessions stay in memory. `adk web` writes `.adk/session.db` beside the agent
  source; on Cloud Run that disk is memory, so the file is a durable-looking
  store that vanishes at the next scale-to-zero. What matters is written to
  Firestore by the persistence tool instead.

`server.py` builds a plain FastAPI application of our own and mounts two pages
on it: the **upload page** at `/`, which is a file picker and a results table,
and the **records page** at `/records` (issues #9 and #60). It used to call the
CLI's app factory and serve the developer UI along with it; it no longer does,
because the workshop uses one button of that UI and a browser could not open it
on a private service anyway (ADR-0001). ADK's REST API is not mounted either,
so the deployed agent is driven through `POST /analyze` and nothing else
(ADR-0002). The developer UI stays local, under `adk web`. One container, one
service, one URL, on port 8080.

## The sequence

Four commands, in this order, on a project that has been through the
[pre-flight](research/gcp-project-preflight-and-cost.md).

```bash
cd infra
terraform init
terraform apply                                  # 1. the stack, on hello

IMAGE="$(terraform output -raw image_repository)/agent:v1"
gcloud builds submit --tag "$IMAGE" ..           # 2. build and push

terraform apply -var "image=$IMAGE"              # 3. swap the image in

python scripts/origin_shim.py \
  --project "$PROJECT_ID"                        # 4. reach it
```

The fourth command prints one URL. Open it: that is the upload page on your own
service. Pick an invoice, press the button, and follow the link to
`/records` to see what the agent filed.

## The Origin shim is the way in

The service is private and always will be — domain restricted sharing blocks an
`allUsers` invoker binding for corporate attendees, so `gcloud run services
proxy` is in the path for everyone. That proxy is necessary and not sufficient.
Cloud Run's front door answers `403 Forbidden: origin not allowed` to any
authenticated request carrying a cross-origin `Origin` header, and a browser
attaches that header to every request that is not a plain page load — including
a same-origin form post, which is what an upload is. So the proxy alone gets
you a page that renders and then fails on its first upload.

The shim closes exactly that gap, and nothing else:

```bash
python scripts/origin_shim.py
python scripts/origin_shim.py --service invoice-agent --region europe-west1 \
  --project my-project --port 8080          # the defaults, spelled out
```

It starts the proxy as a child on a port of its own, listens on the port you
browse, deletes `Origin` from everything on the way through, prints the URL,
and takes the proxy down with it on Ctrl-C. It rewrites bytes rather than
parsing requests, so uploads and server-sent events pass through untouched, and
it checks for the proxy binary, the `cloud-run-proxy` component and the service
before it starts, so a missing piece is a sentence rather than a stack trace.

It used to be two processes and two ports, kept off the clock as a debugging
tool. It is one command now and it is the documented way in
([#61](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/61),
ADR-0004). The evidence for the header rule, including the diagnoses that were
rejected on the way, is in
[`research/cloud-run-origin-403.md`](research/cloud-run-origin-403.md)
([#52](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/52)).

**The developer UI is not on the deployed service to open.** It is a local tool
under `adk web`, which is where the hour's trace lives and where it stays
(ADR-0001).

The first apply runs on Google's hello container because the registry that
holds your image is created by that same apply. See
[infra/README.md](../infra/README.md).

`gcloud builds submit` uploads the working directory. `.gcloudignore` keeps
that to the three container files, `invoice_agent/` and `data/` — 175 KiB
rather than the several megabytes of sample invoices. Without the file gcloud
falls back to `.gitignore`, which excludes none of it.

## Measured timings

On a genuinely fresh project, europe-west1, 2026-09-03. These are the numbers
the run of show should budget from.

| Step | Time |
|---|---|
| Project create and billing link | 35s |
| Enable the eight APIs | 69s |
| `terraform init` | 6s |
| First `terraform apply` (nine resources, hello image) | 38s (#22), **58s** on a second project (#15) |
| `gcloud builds submit`, cold cache | 52s (#22), 59s (#15); warm 44s |
| `gcloud builds submit --async` returns the terminal | 4-8s |
| Second `terraform apply` (image swap), container start included | 41s |
| Container start to serving, 224 MB pull included | 11s |
| First invoice analysed, clean | 16s |
| The rigged invoice, which checks twice | 18s |

Under four minutes from an empty project to a working agent, and half of that
is the two waits that belong to the pre-flight rather than the room: API
enablement and the first build.

Local reference points, same image: it builds in 19 seconds with a warm Docker
cache, weighs 224 MB, and analyses `01-northwind-clean.pdf` in about 17
seconds — indistinguishable from Cloud Run, because the time is the model's.

Two things the run of show should not read into this. The analysis timings are
one run each, not a distribution; the ten-run study is in
[failure-then-retry-tuning.md](research/failure-then-retry-tuning.md). And the
11-second container start is paid again by every attendee whose service has
been idle, because `min_instance_count` is 0 — see [COST.md](COST.md) for why
that trade is the right one.

## What the proving run also found

**`save_invoice_record` writes nowhere durable yet.** The deployed container
still uses the local JSON Lines store, so a saved record lands in the
container's `/tmp` and dies with the instance. The Firestore and Cloud Storage
backend is issue #9. The stack is ready for it: the service account already
holds `datastore.user` and `storage.objectUser`, and `FIRESTORE_DATABASE` and
`INVOICE_BUCKET` are already in the container's environment.

**The proxy component was missing on that machine.** On the apt-installed
gcloud used for the #22 run, `gcloud run services proxy` was not present, so it
reached the service directly at its `run.app` URL with an identity token
instead. #12 later found `google-cloud-cli-cloud-run-proxy` is a package in the
repo Google already ships, and #15 opened the deployed service through the
resulting proxy. The pre-flight check on issue #12 is still the thing standing
between an attendee and a service they cannot reach.

**The service is private and behaves like it.** Unauthenticated requests to
the `run.app` URL get 403. With an identity token the same request gets 200.

**The failure-then-retry moment survives the deploy.** On Cloud Run, running
as the stack's service account rather than as a human, the rigged invoice
produced two `check_invoice_arithmetic` calls before the lookup and the save.
The demo works where it has to work.

## Driving the deployed agent

**In a browser, on the upload page.** That is the way, and it is the way the
run of show uses at 0:42. Pick one invoice or a **batch** of them, press the
button, and rows appear one at a time as each document comes back: supplier,
invoice number, date, line count, total, whether it adds up, and one line of
trace summary — *checked once, adds up*, or *checked twice, still over by
1,400.00*. A document the agent could not process is a red row carrying the
reason, and the rest of the batch carries on.

The limits are PDF, PNG and JPEG, ten megabytes a document, twenty documents a
batch. They are declared once in `invoice_agent/upload.py`, interpolated into
the page from there, and enforced again on the server, so the page and the
service cannot disagree about them.

**Programmatically**, the endpoint is one multipart POST per document:

```bash
curl -F file=@samples/invoices/04-halden-rigged-total.pdf \
  http://localhost:8080/analyze
```

It answers with the finished record, whether validation passed, the archive
pointer and the trace summary. One document in, one record out, one agent run
per document in a fresh session — see ADR-0003 for why a batch is sequenced in
the browser rather than handed to the agent whole.

**`scripts/probe_deployed.py` posts to `/analyze` now.** It used to create a
session and post to ADK's streaming run endpoint, which the deployed
application does not mount any more (ADR-0002). It sends the same multipart
request the upload page sends, which makes it a check of the contract that
actually ships rather than of one nothing uses. Point it at the Origin shim,
or at any base URL as a second argument.

## Running the container on your own machine

Worth doing once before the room, because it separates a broken container from
a broken deploy.

```bash
docker build -t invoice-agent:local .
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  -e GOOGLE_GENAI_USE_ENTERPRISE=TRUE \
  -e GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
  -e GOOGLE_CLOUD_LOCATION=global \
  invoice-agent:local
```

Mounting the gcloud config is what stands in for the service account: locally
the container calls Vertex AI as you, on Cloud Run as the stack's runtime
service account. Nothing else differs.
