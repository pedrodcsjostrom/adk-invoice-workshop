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
| First `terraform apply` (nine resources, hello image) | 50s |
| `gcloud builds submit`, cold cache | 52s |
| Second `terraform apply` (image swap) | not yet measured |
| Cold start plus first invoice analysis | not yet measured |

Local reference points, same image: it builds in 19 seconds with a warm Docker
cache, weighs 224 MB, and analyses `01-northwind-clean.pdf` in about 17
seconds against Vertex AI.

The first apply is quoted from issue #8's run; this session reproduced
everything through the build.

## Proving it without a browser

`scripts/probe_deployed.py` drives the deployed service over the same HTTP API
the developer UI uses: it creates a session, uploads one invoice as inline
bytes, and prints the tool calls, the elapsed time and the finished record.

```bash
python scripts/probe_deployed.py samples/invoices/04-halden-rigged-total.pdf
```

It defaults to `http://localhost:8080`, which is where the proxy puts the
service. Pass a second argument to point it somewhere else, such as a container
you are running locally.

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
