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

`server.py` calls the same app factory the CLI calls, `get_fast_api_app`, so
the developer UI is identical to the local one. **This is what makes the
records page free:** it is a route added to that same FastAPI app (issue #9),
served by the same process on the same port 8080. One container, one service,
one URL.

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

gcloud run services proxy invoice-agent \
  --region europe-west1 --project "$PROJECT_ID"  # 4. reach it
```

Then, in another terminal, drive it and look at what it filed:

```bash
python scripts/probe_deployed.py samples/invoices/04-halden-rigged-total.pdf
```

and open <http://localhost:8080/records>.

## The developer UI does not load through the proxy on its own

Cloud Run's front door answers `403 Forbidden: origin not allowed` to any
authenticated request carrying a cross-origin `Origin` header. The Angular
bundles are `type="module"` and module scripts are always fetched in CORS mode,
so every one of them is refused and the page loads styled and blank. The
document and the stylesheet are not fetched that way, which is why it looks
like a broken app rather than a rejected request.

This is not a proxy bug: `gcloud run services proxy` attaches the identity
token either way. The evidence is in
[`research/cloud-run-origin-403.md`](research/cloud-run-origin-403.md)
([#52](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/52)).

**So the two surfaces the hour relies on** are `/records` in a browser and the
HTTP API that `scripts/probe_deployed.py` drives. Neither sends an `Origin`,
which is exactly why both work. Nothing about the agent changes — the deployed
run still checks the arithmetic twice and still files the flagged record.

### Getting the developer UI anyway

Deleting that one request header is enough. Chain
`scripts/strip_origin_proxy.py` in front of the proxy and browse the shim:

```bash
gcloud run services proxy invoice-agent --region europe-west1 --port 8080
python scripts/strip_origin_proxy.py          # then open localhost:8090
```

Proved on a live service: the UI loads, an uploaded PDF runs, and the trace
pane shows both arithmetic checks. It rewrites bytes rather than parsing
requests, so server-sent events and file uploads pass through untouched.

**Keep it off the clock.** This is a second hand-rolled process in the hot path
at 0:41, and the run of show deliberately does not depend on it. Use it when
you want to show the deployed agent's trace in the UI, or to debug a deployed
service on your own time.

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

This is the way you run an invoice against the deployed service, not a fallback
for when a browser is unavailable — the browser route does not exist, for the
reason above.

`scripts/probe_deployed.py` drives the deployed service over the same HTTP API
the developer UI uses: it creates a session, uploads one invoice as inline
bytes, and prints the tool calls, the elapsed time and the finished record. It
sends no `Origin`, which is exactly why it works where the UI does not.

```bash
python scripts/probe_deployed.py samples/invoices/04-halden-rigged-total.pdf
```

It defaults to `http://localhost:8080`, which is where the proxy puts the
service. Pass a second argument to point it somewhere else, such as a container
you are running locally, or the `run.app` URL:

```bash
INVOICE_ID_TOKEN="$(gcloud auth print-identity-token)" \
  python scripts/probe_deployed.py samples/invoices/04-halden-rigged-total.pdf \
  "$(gcloud run services describe invoice-agent --region europe-west1 \
     --project "$PROJECT_ID" --format='value(status.url)')"
```

Through the proxy no token is needed, because the proxy signs each request.

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
