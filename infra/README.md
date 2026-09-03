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

The first apply takes six or seven minutes, almost all of it Firestore.

There is no agent image yet, because the repository that holds it is created by
this same apply. The service therefore starts on Google's public hello
container. That is deliberate: it proves the stack, the private service and the
proxy before any of your own code exists.

```bash
gcloud run services proxy invoice-agent --region europe-west1 --project "$PROJECT_ID"
```

Open <http://localhost:8080> and you should see the hello page. Leave the proxy
running; it is how you reach the agent for the rest of the session.

## Swapping in the agent

Build, push, and re-apply with the image you pushed:

```bash
IMAGE="$(terraform output -raw image_repository)/agent:v1"
gcloud builds submit --tag "$IMAGE" ..
terraform apply -var "image=$IMAGE"
```

## Two things the agent code must honour

- **The Firestore database is named `invoices`, not `(default)`.** The client
  library defaults to `(default)`, which this stack does not create, so the
  persistence tool has to pass the name from `FIRESTORE_DATABASE`.
- **The region and the model endpoint are different variables.**
  `GOOGLE_CLOUD_LOCATION` is `global` because no region serves
  `gemini-3.5-flash`. Reusing the infrastructure region gives a 404 that reads
  like a permissions problem.

## Tearing down

```bash
terraform destroy
```

The bucket has `force_destroy` and the database has `deletion_policy = "DELETE"`,
so this leaves nothing behind. APIs stay enabled, which costs nothing.
