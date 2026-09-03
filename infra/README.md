# The Terraform stack

One directory, one state file, three commands in the room. State is local, so
there is no bootstrap bucket and nothing to create before Terraform runs.

## What it creates

| Resource | Purpose |
|---|---|
| Artifact Registry repository | Holds the agent image you build |
| Service account | The identity the agent runs as |
| Firestore database `invoices` | Invoice records |
| Cloud Storage bucket | Archived original documents |
| Cloud Run service | The ADK developer UI and the records page |

Roles on the service account: `aiplatform.user`, `datastore.user`,
`storage.objectUser` on the bucket, `artifactregistry.reader` on the repository.

## Before you apply

Terraform does not enable APIs. Enablement lags behind the API call by up to
several minutes, which is fine the day before and disastrous mid-workshop, so
it belongs to the pre-flight. Run this at least ten minutes ahead:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="$PROJECT_ID"
```

You also need `roles/owner` on the project, and credentials Terraform can use:

```bash
gcloud config set project "$PROJECT_ID"
gcloud auth application-default login
```

Setting the project first matters. Application default credentials pick up
their quota project from the active configuration, and without one the provider
fails on the first API call.

## Applying

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # then set project_id
terraform init
terraform apply
```

Measured against a genuinely fresh project on 2026-09-03: the first apply took
50 seconds for all nine resources. Firestore, the resource most likely to be
slow, took 4. Artifact Registry at 23 seconds was the longest. Budget a couple
of minutes in the run of show, not the ten you might expect.

There is no agent image yet, because the repository that holds it is created by
this same apply. The service therefore starts on Google's public hello
container. That is deliberate: it proves the stack, the private service and the
proxy before any of your own code exists.

```bash
gcloud run services proxy invoice-agent --region europe-west1 --project "$PROJECT_ID"
```

Open <http://localhost:8080> and you should see the hello page. Leave the proxy
running; it is how you reach the agent for the rest of the session.

> **The proxy is a separate gcloud component, and this bites.** `gcloud run
> services proxy` is not part of the base install. On a Debian or Ubuntu gcloud
> installed from apt, the component manager is disabled and the interactive
> "install it now?" prompt fails outright, telling you to run
> `sudo apt-get install google-cloud-cli-cloud-run-proxy`. Attendees on a
> managed laptop may not have that sudo. On other installs,
> `gcloud components install cloud-run-proxy` is enough. Since every attendee
> now reaches the service this way, this belongs in the pre-flight check, not
> in the room.

## Swapping in the agent

Build, push, and re-apply with the image you pushed:

```bash
IMAGE="$(terraform output -raw image_repository)/agent:v1"
gcloud builds submit --tag "$IMAGE" ..
terraform apply -var "image=$IMAGE"
```

The build takes 52 seconds on a fresh project, and what it builds — the
Dockerfile, the entrypoint, and why the entrypoint is not `adk web` — is
[docs/DEPLOY.md](../docs/DEPLOY.md).

## Two things the agent code must honour

- **The Firestore database is named `invoices`, not `(default)`.** The client
  library defaults to `(default)`, which this stack does not create, so the
  persistence tool has to pass the name from `FIRESTORE_DATABASE`.
- **The region and the model endpoint are different variables.**
  `GOOGLE_CLOUD_LOCATION` is `global` because no region serves
  `gemini-3.5-flash`. Reusing the infrastructure region gives a 404 that reads
  like a permissions problem.

## Tearing down

Use the script, not the bare command:

```bash
../scripts/teardown.sh
```

`terraform destroy` does take everything this stack owns. The bucket has
`force_destroy` and the database has `deletion_policy = "DELETE"`, and on the
fresh project, with an object already in the bucket, nine resources went in
under a minute with no database, bucket or service surviving.

What it cannot take is anything Terraform did not create. `gcloud builds
submit` stages your source into `gs://<PROJECT_ID>_cloudbuild`, a bucket it
makes for itself on the first build; a destroy leaves it, and nothing expires
what is inside. The script deletes it, then lists whatever is still alive in
the project instead of asserting that nothing is. Enabled APIs also survive,
and should — they cost nothing.

See [docs/COST.md](../docs/COST.md) for what the hour costs and for the
`--delete-project` option, which is the surer end to a project created only for
this workshop.
