# What this costs, and how to stop it

Read this before you apply anything. It is short on purpose.

**The workshop hour costs you between $0.11 and $0.21.** All of it is Vertex AI
Gemini tokens. Every other service in the stack is free at this volume, and if
you are on the Google Cloud free trial you cannot be billed at all — see
[The two kinds of attendee](#the-two-kinds-of-attendee).

When you are done: `scripts/teardown.sh`.

---

## What is free and what is not

| Service | At workshop volume | Why |
|---|---|---|
| **Vertex AI (Gemini)** | **$0.11–$0.21 per person** | The only line on the bill. Vertex AI has no free tier at all. |
| Cloud Run | free | Scales to zero between requests, and the free tier covers 2M requests a month. |
| Firestore | free | A handful of documents. |
| Cloud Storage | free | Nine invoices, and a 7-day lifecycle rule deletes them. |
| Artifact Registry | free | One image, well under the 0.5 GB free allowance. |
| Cloud Build | free | 2,500 build-minutes a month are free; you will use two. |
| Cloud Logging | free | 50 GiB a month free, 30-day retention. |

The per-attendee figure moves with the model. Across a room of 40:

| Model | Room total |
|---|---|
| Gemini 2.5 Flash | ~$4.50 |
| Gemini 3.8 Flash | ~$8.60 |
| Gemini 2.5 Pro | ~$18.50 |

Arithmetic and sources are in
[the pre-flight research](research/gcp-project-preflight-and-cost.md), §8.

### The one setting that matters

`min_instance_count = 0` in `infra/service.tf`. A Cloud Run service kept warm
costs about **86 times** more over a quiet week than one that scales to zero:
$1.09 a week against $0.02. It is hard-coded, and it is the reason forgetting
to tear down is an annoyance rather than a bill. Do not raise it to fix a cold
start.

## The two kinds of attendee

**On the $300 free trial, a surprise bill is not possible.** Google does not
roll a trial into a paid account by itself. When the credit runs out or 90 days
pass, "your Free Trial billing account will be closed" and "all resources you
created during the trial are stopped". You have to actively choose to upgrade
before anything charges you.

**On an existing paid billing account, it is possible** — a corporate project,
or a personal account you upgraded years ago. This is the case teardown is
written for. If you are in it, do the teardown on the day, and consider
[a budget alert](#optional-a-budget-alert) beforehand.

## What `terraform destroy` does not remove

The stack was built so that a destroy takes everything with it: the bucket has
`force_destroy`, the Firestore database has `deletion_policy = "DELETE"`, and a
destroy against a fresh project removed all nine resources in under a minute.

Two things still survive it, because Terraform never created them:

- **`gs://<PROJECT_ID>_cloudbuild`.** `gcloud builds submit` stages your source
  into a bucket it makes for itself the first time you build. Terraform never
  sees it, nothing expires the tarballs inside it, and the bucket keeps
  charging for storage. Under regional bucket behaviour the name is
  `gs://<PROJECT_ID>_<REGION>_cloudbuild` instead. `scripts/teardown.sh`
  deletes both.
- **Enabled APIs.** These cost nothing, and disabling them would only make the
  project harder to reuse. Leave them.

Your laptop keeps some residue too: `infra/terraform.tfstate`,
`invoice_agent/.env`, and the `.adk/` session database the developer UI writes
next to the agent source. None of them cost money, but the application default
credentials you created do let anything on that machine spend against your
project. `gcloud auth application-default revoke` hands them back.

## Tearing down

```bash
scripts/teardown.sh
```

It runs the destroy, deletes the Cloud Build staging buckets, then lists
whatever is still alive in the project rather than telling you it is empty.
If the list is not empty, it exits non-zero.

**The surer option is to shut the whole project down.** A project created for
this workshop does not need to outlive it, and deleting it stops billing on
everything at once, including anything the script missed:

```bash
scripts/teardown.sh --delete-project
```

Shutting a project down disconnects its billing account immediately and starts
a 30-day recovery window; `gcloud projects undelete <PROJECT_ID>` brings it
back within that window. Do not do this to a project that had anything else in
it.

## Optional: a budget alert

Worth five minutes if you are on a paid billing account and want a tripwire
rather than trust. In the console, **Billing → Budgets & alerts → Create
budget**, scope it to your workshop project, set the amount to $5, and leave
the default 50/90/100% email thresholds. It notifies; it does not cap spend.

Cloud Billing's programmatic budgets need the Billing Budget API and the
Billing Account Administrator role, which is why this is a console step and not
part of the pre-flight script.

---

## Sources

- [Google Cloud Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features) — trial closure, no automatic upgrade, Always Free tiers
- [Create and manage projects](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects) and [Delete and restore projects](https://docs.cloud.google.com/resource-manager/docs/delete-restore-projects) — shutdown, billing, the 30-day window
- [`gcloud builds submit`](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit) — the `gs://[PROJECT_ID]_cloudbuild/source` default staging bucket
- [GCP project pre-flight and cost](research/gcp-project-preflight-and-cost.md) — the per-attendee arithmetic and the idle-cost comparison
