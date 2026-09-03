# GCP project pre-flight and cost — ADK invoice-analyzer workshop

**Research date: 2026-09-03.** All prices USD, list rates, no committed-use discounts. Pricing is
region-specific; figures below are for `us-central1` (Iowa) with `europe-west1` (Belgium) deltas
called out. Re-verify before the workshop.

**Question answered:** what must be true of a brand-new Google Cloud project before `terraform apply`
of the workshop stack can succeed, and what does it cost?

**Stack under test:** ADK 2.x Python agent (dev UI) on Cloud Run · container image in Artifact
Registry · Firestore Native for invoice records · Cloud Storage for archived originals · Vertex AI
as the model backend via application default credentials, no API key.

> **Three URL/branding changes that affect every link in the kit.** (1) `cloud.google.com/*` now
> 301-redirects to `docs.cloud.google.com/*`. (2) Vertex AI generative-AI docs are rebranded
> **"Gemini Enterprise Agent Platform"** and have moved, e.g.
> `cloud.google.com/vertex-ai/generative-ai/docs/learn/locations` →
> <https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations>. (3)
> `google.github.io/adk-docs` 301-redirects to <https://adk.dev/>.

---

## 1. What this means for the workshop

### 1.1 The five things that will actually break

Ranked by expected number of attendees affected.

1. **Gemini 3.x is not available in any single region.** `us-central1` and `europe-west1` serve only
   the Gemini **2.5** family. Every Gemini 3.x model is `global`- or multi-region-only. You cannot
   co-locate Cloud Run + Firestore + GCS + Vertex in one region *and* use a current model. **Make
   `GOOGLE_CLOUD_LOCATION` (model endpoint) a separate Terraform variable from the infra `region`.**
   See §5.
2. **`GOOGLE_GENAI_USE_VERTEXAI` is deprecated in ADK 2.x.** ADK 2.8.0 honours it but emits a
   `DeprecationWarning`; the current name is `GOOGLE_GENAI_USE_ENTERPRISE`. See §6.1.
3. **Corporate Workspace attendees cannot make the Cloud Run URL public.** Organizations created on
   or after 2024-05-03 enforce `constraints/iam.allowedPolicyMemberDomains` by default, which blocks
   `allUsers`. See §7.2 — and note the ADK dev UI arguably should not be public anyway (§6.2).
4. **API enablement is eventually consistent, and "just-created projects may experience longer
   service activation times"** — HashiCorp's own words, and 40 fresh projects is the worst case. See
   §2.3.
5. **`cloudresourcemanager.googleapis.com` is not enabled by default** and the stack does project-level
   IAM bindings. Likely first-apply failure. See §2.1.

### 1.2 Headline cost number

**Per attendee, the workshop hour costs $0.11–$0.21** — and *all of it* is Vertex AI Gemini tokens.
Every other service in the stack (Cloud Run, Cloud Build, Firestore, Cloud Storage in a US region,
Cloud Logging) is fully absorbed by Always Free tiers at this volume. Vertex AI has **no** free tier.

- 40 attendees, Gemini 2.5 Flash: **~$4.50 total**
- 40 attendees, Gemini 3.8 Flash (intro pricing, global): **~$8.60 total**
- 40 attendees, Gemini 2.5 Pro: **~$18.50 total**

**Leaving the stack running idle for a week afterwards:**

| | per attendee/week | per attendee/month | 40 attendees/month |
|---|---|---|---|
| `min-instances = 0` | **~$0.02** | **~$0.10** | **~$4.00** |
| `min-instances = 1`, 512 MiB | ~$1.09 | ~$8.61 | ~$344 |

**`min_instance_count = 0` is the single biggest cost lever in the whole kit — an 86× difference.**
Hard-code it. Full arithmetic in §8.

### 1.3 Pre-flight checklist (the day before)

Each attendee, on their own project:

- [ ] A billing account is **linked and active**. Not optional — unlinked projects "can't use Google
      Cloud … services, even if you only use services that are free"
      (<https://docs.cloud.google.com/billing/docs/how-to/modify-project>).
- [ ] `gcloud config set project PROJECT_ID` **before** `gcloud auth application-default login` —
      this is what makes the quota project get written automatically (§4.3).
- [ ] `gcloud auth application-default login` completed, and `GOOGLE_APPLICATION_CREDENTIALS` is
      **unset** in their shell profile (it silently overrides ADC).
- [ ] All required APIs enabled **≥10 minutes before** the apply (§2.1), by a single
      `gcloud services enable` line — not by Terraform.
- [ ] `roles/owner` on the project (§3.1).
- [ ] Org-policy scan clean, or exceptions understood (§7).
- [ ] Region choice fixed, and the Firestore location decision made — **it is immutable** (§5.4).
- [ ] Terraform ≥ the version pinned by the kit, and `gcloud` on a recent release.

### 1.4 Design decisions this research forces on the Terraform stack

| Decision | Why |
|---|---|
| **User-managed runtime service account**, not the Compute Engine default SA | Removes the post-May-2024 org-policy variance in whether the default SA has Editor, and the question of whether it exists at all before `compute.googleapis.com` is on (§3.3, §3.4) |
| **Enable `compute.googleapis.com` explicitly** | It is what creates the default SA and what Cloud Build's docs require (§2.1) |
| **`min_instance_count = 0`**, request-based billing | 86× cost difference (§8.3) |
| **`uniform_bucket_level_access = true`** on the bucket | `constraints/storage.uniformBucketLevelAccess` is a new-org default (§7.6) |
| **Never create a service account key** | `iam.managed.disableServiceAccountKeyCreation` is a new-org default (§7.1) |
| **`region` and `GOOGLE_CLOUD_LOCATION` as separate variables** | Gemini 3.x has no single-region availability (§5) |
| **`deletion_policy = "DELETE"` + `delete_protection_state` disabled** on Firestore | Defaults to `ABANDON`; otherwise `terraform destroy` leaves the DB behind (§2.4) |
| **`disable_on_destroy = false`** on `google_project_service` | Prevents a destroy from tearing down APIs (§2.4) |

---

## 2. Required APIs

### 2.1 The exact set

**Already enabled by default** on projects created via console or gcloud, per
<https://docs.cloud.google.com/service-usage/docs/enabled-service>:
`serviceusage.googleapis.com`, `storage.googleapis.com`, `storage-api.googleapis.com`,
`storage-component.googleapis.com`, `logging.googleapis.com`, `monitoring.googleapis.com`,
`datastore.googleapis.com`, `cloudapis.googleapis.com`.

> Caveat: that default list is documented for projects created **via console or gcloud CLI**.
> Whether the same defaults apply to API-created projects is **UNVERIFIED**.

**Must be enabled** (none of these are in the default list):

| API | For | Primary citation |
|---|---|---|
| `run.googleapis.com` | Cloud Run service | <https://docs.cloud.google.com/run/docs/deploying-source-code> |
| `artifactregistry.googleapis.com` | Image repository | <https://docs.cloud.google.com/artifact-registry/docs/enable-service> |
| `cloudbuild.googleapis.com` | Only if the image is built by Cloud Build (`gcloud run deploy --source`, `adk deploy cloud_run`) | <https://docs.cloud.google.com/run/docs/deploying-source-code> |
| `compute.googleapis.com` | Creates the Compute Engine default SA; required by Cloud Build's own before-you-begin | <https://docs.cloud.google.com/build/docs/build-push-docker-image> · <https://docs.cloud.google.com/compute/docs/access/service-accounts> |
| `firestore.googleapis.com` | Firestore Native database | Terraform `google_firestore_database` documents it as required: <https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_database> |
| `aiplatform.googleapis.com` | Vertex AI / Agent Platform model backend | <https://docs.cloud.google.com/vertex-ai/docs/start/cloud-environment> · ADK: <https://adk.dev/get-started/google-cloud/> |
| `iam.googleapis.com` | Creating service accounts | <https://docs.cloud.google.com/iam/docs/service-accounts-create> |
| `cloudresourcemanager.googleapis.com` | Project-level IAM bindings (`projects.setIamPolicy`) | See note below |
| `secretmanager.googleapis.com` | **Not needed.** ADK's Cloud Run page only uses Secret Manager to store a `GOOGLE_API_KEY`; with ADC + Vertex there is no key. | <https://adk.dev/deploy/cloud-run/> |

**Note on `cloudresourcemanager.googleapis.com`:** it is not in the default-enabled list, and
`google_project_iam_*` calls `projects.setIamPolicy`, which is the Resource Manager v1 API
(<https://docs.cloud.google.com/resource-manager/reference/rest/v1/projects/setIamPolicy>). The
necessity is **strongly implied but not verbatim-cited** — Google does not publish a
"you must enable cloudresourcemanager" sentence. **Verify by test-applying against one clean
project.** This is the single most likely first-apply failure.

**Does Cloud Run itself need `compute.googleapis.com`?** No Cloud Run doc says so. Enable it anyway,
for two independent reasons: Cloud Build's before-you-begin requires it
(<https://docs.cloud.google.com/build/docs/build-push-docker-image>), and the Compute Engine default
service account is "Automatically created … and added to your project **when you enable the Compute
Engine API**" (<https://docs.cloud.google.com/compute/docs/access/service-accounts>). Whether
enabling `run.googleapis.com` transitively enables `compute.googleapis.com` is **UNVERIFIED**.

**Suggested single pre-flight line:**

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

### 2.2 What ADK's own docs say

- Prerequisite: "a Google Cloud Project with the **Agent Platform API** (`aiplatform.googleapis.com`)
  enabled" plus the gcloud CLI — <https://adk.dev/get-started/google-cloud/>.
- ADK's Cloud Run page gives no `gcloud services enable` line, but does require granting the Cloud
  Build compute SA `roles/cloudbuild.builds.builder`:

  ```bash
  gcloud projects add-iam-policy-binding [PROJECT_ID] \
      --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" \
      --role="roles/cloudbuild.builds.builder"
  ```

  Source: <https://adk.dev/deploy/cloud-run/> (verified against the raw markdown at
  `github.com/google/adk-docs/blob/main/docs/deploy/cloud-run.md`).
- The closest ADK-blessed enable list is on the GKE page:
  `gcloud services enable container.googleapis.com artifactregistry.googleapis.com
  cloudbuild.googleapis.com aiplatform.googleapis.com` (<https://adk.dev/deploy/gke/>). Swap
  `container` for `run` and that is essentially the set.

### 2.3 Enablement latency and propagation lag

The most explicit primary source is HashiCorp's own user guide,
<https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/google_project_service>:

> `Error: Error creating <Resource>: googleapi: Error 403: <Service> API has not been used in project
> <Project> before or it is disabled.`
>
> "Activating a service is eventually consistent in GCP. Terraform attempts to mitigate this in
> `google_project_service` by waiting for the activation API's long-running operation to finish and
> verifying that the service appears in a list of activated services. Despite these checks, service
> activation is not guaranteed by the time the `google_project_service` resource is done
> provisioning."
>
> "At the time of writing, there is no way for the provider to completely verify service activation.
> The time before `google_project_service` returns successfully may vary depending on the service,
> GCP-internal caching, and other circumstances. **In particular, just-created projects may
> experience longer service activation times.**"

Google's own wording of the error, from
<https://docs.cloud.google.com/service-health/docs/troubleshooting>:

> "… **If you enabled this API recently, wait a few minutes for the action to propagate to our
> systems and retry.**"

**There is no primary source giving a concrete SLA or duration.** "A few minutes" is the only figure
Google publishes, and only inside per-service error text.
<https://docs.cloud.google.com/service-usage/docs/enable-disable> models enablement as a long-running
operation with a `done` field and states no propagation window. Any specific number (30 s, 2 min) is
**UNVERIFIED**.

Documented mitigations, from the same HashiCorp guide: the `time_sleep` resource with
`create_duration` + `depends_on`, or a `null_resource` with a `local-exec` `sleep 60` provisioner.

**A second, independent propagation race: IAM binding propagation.** Cloud Run's own docs say
"**Granting the Cloud Run builder role … takes a couple of minutes to propagate**"
(<https://docs.cloud.google.com/run/docs/deploying-source-code>). Terraform that creates an SA, binds
roles, and immediately deploys a service using it is racing this too.

**Workshop recommendation: take API enablement out of Terraform entirely.** Have attendees run one
`gcloud services enable` line during the pre-flight, ≥10 minutes before the apply. Terraform can then
still declare the same services idempotently — documented safe: "*Note that unlike other resources
that fail if they already exist, `terraform apply` can be successfully used to verify already enabled
services.*"

### 2.4 The serviceusage chicken-and-egg, and `google_project_service` specifics

From <https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_service>:

- **"This resource requires the Service Usage API to use."** ← the chicken-and-egg root. Terraform
  cannot enable anything unless `serviceusage.googleapis.com` is already on. It *is* on by default
  for console/gcloud-created projects, so in practice this is safe — but an attendee who "cleaned up"
  their project by disabling APIs is bricked and can only recover via console or
  `gcloud services enable serviceusage.googleapis.com`.
- Google's confirmation: "By default, the Service Usage API is enabled for projects, but if you
  disabled it for the project that's performing the request to enable a service, you receive an
  error" — <https://docs.cloud.google.com/service-usage/docs/enable-disable>.
- `disable_on_destroy` — "If `true`, disable the service when the Terraform resource is destroyed. If
  `false` or unset, the service will be left enabled … It should generally only be `true` in
  configurations that manage the `google_project` resource itself." **Set it explicitly to `false`.**
- `disable_dependent_services` — "If `true`, services that are enabled and which depend on this
  service should also be disabled when this service is destroyed. If `false` or unset, an error will
  be returned if any enabled services depend on this service when attempting to destroy it."
- `deletion_policy` — defaults to `"DELETE"`; `"PREVENT"` / `"ABANDON"` available.
- Default timeouts: create 20 min, read 10 min, update 20 min, delete 20 min. The docs' own example
  raises create to `30m`.
- Batching: "the Google provider will batch multiple changes into a single request when possible."
  Use `for_each = toset(var.services)` rather than N separate resources.
- Request-rate quota: "The service management API called by the `google_project_service` resource
  uses request rate quota on the project of the account used to call the API (i.e. against the
  Terraform credentials) by default." Fine for 40 separate projects/credentials; **not** fine if you
  pre-bake a shared bootstrap identity.

**`google_firestore_database` gotcha** (<https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_database>):
`deletion_policy` "Defaults to ABANDON". For `terraform destroy` to actually remove the database you
must set `deletion_policy = "DELETE"` **and** ensure `delete_protection_state` is not
`DELETE_PROTECTION_ENABLED`. `location_id` and `type` (`FIRESTORE_NATIVE`) are required with no
defaults.

---

## 3. IAM roles the attendee needs

### 3.1 The simple answer

**`roles/owner` on their own project.** Per
<https://docs.cloud.google.com/iam/docs/roles-overview>, Owner is "All Editor permissions, plus
permissions for actions like the following: … **Managing roles and permissions for a project and all
resources within the project**; Setting up billing for a project." The IAM-management clause is what
makes Owner sufficient — **Editor alone cannot `setIamPolicy`**, so an attendee granted only Editor
will fail on the role bindings. Caveat from the same page: "The Owner role doesn't contain all
permissions for all Google Cloud resources."

For a workshop where each attendee owns a throwaway project, Owner is the correct recommendation.

### 3.2 Least-privilege list (for org-constrained environments)

| Capability | Role | Citation |
|---|---|---|
| Enable APIs | `roles/serviceusage.serviceUsageAdmin` | <https://docs.cloud.google.com/service-usage/docs/enable-disable> |
| Consume APIs / set quota project | `roles/serviceusage.serviceUsageConsumer` | <https://docs.cloud.google.com/docs/quotas/set-quota-project> |
| Deploy Cloud Run service | `roles/run.developer` (or `roles/run.admin`; `roles/run.sourceDeveloper` for `--source`) | <https://docs.cloud.google.com/run/docs/deploying> |
| Attach runtime SA to the service | `roles/iam.serviceAccountUser` **on the service identity** | §3.3 |
| Create Artifact Registry repo | `roles/artifactregistry.admin` | <https://docs.cloud.google.com/artifact-registry/docs/access-control> |
| Push images | `roles/artifactregistry.writer` | same |
| Cloud Run pulls image | `roles/artifactregistry.reader` on the repo | <https://docs.cloud.google.com/run/docs/deploying> |
| Create Firestore database | `roles/datastore.owner` (grants `datastore.databases.create`) | <https://docs.cloud.google.com/firestore/native/docs/manage-databases> |
| Create GCS bucket | `roles/storage.admin` (`storage.buckets.create`) | <https://docs.cloud.google.com/storage/docs/creating-buckets> |
| Create service accounts | `roles/iam.serviceAccountCreator` | <https://docs.cloud.google.com/iam/docs/service-accounts-create> |
| Bind project IAM roles | `roles/resourcemanager.projectIamAdmin` | same page |
| View logs during the workshop | `roles/logging.viewer` | <https://docs.cloud.google.com/run/docs/quickstarts/functions/deploy-functions-gcloud> |

### 3.3 `roles/iam.serviceAccountUser` and the `actAs` requirement

Verbatim from <https://docs.cloud.google.com/run/docs/deploying>, the deployer needs:

> - "Cloud Run Developer (`roles/run.developer`) on the Cloud Run service"
> - "**Service Account User (`roles/iam.serviceAccountUser`) on the service identity**"
> - "Artifact Registry Reader (`roles/artifactregistry.reader`) on the Artifact Registry repository"

<https://docs.cloud.google.com/run/docs/configuring/services/service-identity> states the deployer
must have `roles/iam.serviceAccountUser` on the service account used as the service identity, because
that role contains the **`iam.serviceAccounts.actAs`** permission needed to attach a service account
to a service or revision.

Cross-project deployments additionally need `roles/iam.serviceAccountTokenCreator` on the service
identity — not relevant for single-project attendees, but relevant if you pre-provision a shared
image registry project.

**Workshop failure mode:** if Terraform creates a dedicated runtime SA and then creates the Cloud Run
service in the same apply, the applying principal needs `serviceAccountUser` on that just-created SA.
Owner covers it. Under least privilege, add an explicit `google_service_account_iam_member` plus a
`depends_on` — and remember this grant is itself subject to the IAM propagation lag in §2.3.

### 3.4 Cloud Run's default compute service account behaviour

- **What it runs as by default:** "If you don't specify a service account when the Cloud Run resource
  is created, Cloud Run uses this service account" — the Compute Engine default service account,
  `PROJECT_NUMBER-compute@developer.gserviceaccount.com`
  (<https://docs.cloud.google.com/run/docs/securing/service-identity>). Terraform's own docs agree:
  `service_account` is optional and "If not provided, the revision will use the project's default
  service account" (<https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service>).
- **Does it exist on a fresh project?** Only once `compute.googleapis.com` is enabled: it is
  "Automatically created … and added to your project **when you enable the Compute Engine API**"
  (<https://docs.cloud.google.com/compute/docs/access/service-accounts>). `compute.googleapis.com` is
  **not** on by default.
- **The Editor grant is no longer guaranteed.** The default SA "**might** automatically be granted
  the Editor role on your project", and Google "strongly recommend[s] … enforcing the
  `iam.automaticIamGrantsForDefaultServiceAccounts` organization policy constraint". Critically:
  "**If you created your organization after May 3, 2024, this constraint is enforced by default**"
  (<https://docs.cloud.google.com/compute/docs/access/service-accounts>).

  → Attendees in a post-May-2024 org get a default SA with **no Editor role**. Any workshop material
  that silently relies on Editor will fail for some attendees and not others — the worst kind of
  workshop bug.
- **Google's recommendation, and the workshop's:** a user-managed, per-service SA — "You manually
  create this service account and determine the most minimal set of permissions that the service
  account needs" (<https://docs.cloud.google.com/run/docs/securing/service-identity>). **This removes
  the org-policy variance entirely and is the right choice for the kit.**

### 3.5 Runtime roles the Cloud Run service account needs

| Purpose | Role | Citation |
|---|---|---|
| Call Gemini via ADC | `roles/aiplatform.user` — display name now "Gemini Enterprise Agent Platform User"; carries `aiplatform.endpoints.predict`. ADK: "Create a service account with the `Agent Platform User` IAM role." | <https://adk.dev/get-started/google-cloud/> · <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/access-control> · <https://docs.cloud.google.com/vertex-ai/docs/general/iam-permissions> |
| Firestore read/write | `roles/datastore.user` — "Read/write access to data in a Firestore database. **Intended for application developers and service accounts.**" | <https://docs.cloud.google.com/firestore/native/docs/security/iam> |
| GCS objects | `roles/storage.objectAdmin` ("full control of objects"), or tighter `roles/storage.objectUser`. **Do not** use `roles/storage.admin` for the runtime identity — it grants bucket control. | <https://docs.cloud.google.com/storage/docs/access-control/iam-roles> |
| Pull the image | `roles/artifactregistry.reader` on the repo | <https://docs.cloud.google.com/run/docs/deploying> |

If you build with Cloud Build there is a **documented disagreement between two Google docs** on the
role name: Cloud Run's source-deploy page prescribes `roles/run.builder`
(<https://docs.cloud.google.com/run/docs/deploying-source-code>), while ADK's Cloud Run page
prescribes `roles/cloudbuild.builds.builder` on the compute default SA
(<https://adk.dev/deploy/cloud-run/>). **Grant both** if you use Cloud Build.

---

## 4. The quota-project trap for application default credentials

### 4.1 What `gcloud auth application-default login` does

- Purpose, verbatim: "Obtains user access credentials via a web flow and puts them in the well-known
  location for Application Default Credentials (ADC)."
  (<https://docs.cloud.google.com/sdk/gcloud/reference/auth/application-default/login>)
- **It is a separate credential store from `gcloud auth login`.** Same page: "This command has no
  effect on the user account(s) set up by the `gcloud auth login` command."
- **The gcloud CLI itself does not use ADC**: "The gcloud CLI itself doesn't use ADC to access Google
  Cloud resources." (<https://docs.cloud.google.com/docs/authentication/provide-credentials-adc>).
  Restated in the troubleshooting doc: "When you use the gcloud CLI, you are using the credentials
  you provided to the gcloud CLI by using the `gcloud auth login` command. You are not using the
  credentials you provided to ADC."
  (<https://docs.cloud.google.com/docs/authentication/troubleshoot-adc>)

  → This is why "but `gcloud` works fine!" is not evidence that Terraform or the agent will work.
- **File paths** (<https://docs.cloud.google.com/docs/authentication/application-default-credentials>):
  - Linux/macOS `$HOME/.config/gcloud/application_default_credentials.json`
  - Windows `%APPDATA%\gcloud\application_default_credentials.json`
- The login command *tries* to write a quota project automatically, but may silently not: it offers
  `--disable-quota-project` for accounts lacking permission, and writes no quota project at all when
  `--client-id-file` is used.
- Warning from the same page, relevant to anyone who has previously used a service-account key: "Do
  not set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable if you want to use the
  credentials generated by this command in your local development."

### 4.2 ADC lookup order

From <https://docs.cloud.google.com/docs/authentication/application-default-credentials>:

1. `GOOGLE_APPLICATION_CREDENTIALS` environment variable (path to a credential JSON file)
2. The local ADC file created by `gcloud auth application-default login`
3. The **attached service account, retrieved from the metadata server**

"Using the credentials from the attached service account is the preferred method for finding
credentials in a production environment on Google Cloud."

**Gotcha:** "The credentials pointed to by the environment variable take precedence over other
credentials" (<https://docs.cloud.google.com/docs/authentication/troubleshoot-adc>) — a stale
`GOOGLE_APPLICATION_CREDENTIALS` in a shell profile silently overrides the ADC login the attendee
just did. **The pre-flight script must check this.**

### 4.3 The "requires a quota project" error

**The literal error string is not present in any Google primary doc — UNVERIFIED against a primary
source.** Google's docs describe the condition but not the message.

- What Google does say (<https://docs.cloud.google.com/docs/authentication/troubleshoot-adc>, "User
  credentials not working"): "If your API request returns an error message about user credentials not
  being supported by this API, the API not being enabled in the project, or no quota project being
  set…"
- The mechanism (<https://docs.cloud.google.com/docs/quotas/quota-project>): APIs are either
  **resource-based** (quota comes from the project containing the resource; not changeable) or
  **client-based** (quota comes from the *client's* project). "When you provide user credentials to
  authenticate to a client-based API, you must specify the project to use for billing and quota. This
  project is called the quota project." And: "If none of the previous checks yield a quota project,
  the request fails."
- Precedence for resolving a quota project on a client-based API: (1) specified in request, (2) API
  key's project, (3) gcloud CLI shared project, (4) **service account's project**, (5) workforce
  identity federation user project.
- **Anecdotal evidence of the literal message** (flagged as non-primary): the string
  `The <api>.googleapis.com API requires a quota project, which is not set by default` recurs in
  `hashicorp/terraform-provider-google` issues for `securitycenter`, `memcache`, `firebase`,
  `apikeys`, `cloudidentity`, `fcm` — e.g.
  <https://github.com/hashicorp/terraform-provider-google/issues/20644>,
  <https://github.com/hashicorp/terraform-provider-google/issues/24500> — and in
  <https://github.com/googleapis/google-auth-library-python/issues/1459>. Widespread and
  well-attested, but not confirmed on a cloud.google.com page.
- **UNVERIFIED: whether `aiplatform.googleapis.com` is client-based and therefore raises this.**
  Evidence leans *no*: the Gemini call targets a project-scoped resource path
  (`projects/{P}/locations/{L}/publishers/google/models/...`), characteristic of a resource-based API.
  Treat "the agent's Vertex call fails on quota project" as **unproven**. The likely place attendees
  hit it is Terraform (§4.6).
- Useful diagnostic, verbatim: "Project 764086051850 is the project used by the gcloud CLI. If you
  see authentication errors referencing this project, you are trying to use a client-based API and you
  have not set both your project and your quota project for your configuration."
  (<https://docs.cloud.google.com/docs/authentication/troubleshoot-adc>) — **grep for `764086051850`
  in any attendee error report.**

### 4.4 Setting the quota project, and the permission it needs

- <https://docs.cloud.google.com/sdk/gcloud/reference/auth/application-default/set-quota-project>:
  "update or add a quota project in application default credentials (ADC)" … "The existing
  application default credentials must have the **`serviceusage.services.use`** permission on the
  given project."
- The role: "ask your administrator to grant you the Service Usage Consumer
  (`roles/serviceusage.serviceUsageConsumer`) IAM role on the project… This predefined role contains
  the `serviceusage.services.use` permission, which is required to set a project as the quota project"
  (<https://docs.cloud.google.com/docs/quotas/set-quota-project>).
- **The JSON field is literally `quota_project_id`** — verified from the reference implementation:
  `google/oauth2/credentials.py` in `googleapis/google-auth-library-python` reads
  `quota_project_id=info.get("quota_project_id")` in `from_authorized_user_info`. (Google's own docs
  do not name the field; this is the primary implementation source.)
- **Good news for this workshop, quoted directly:** "If you use a project you created as your quota
  project, you have the necessary permissions." Each attendee owns their own project, so this trap
  should largely self-resolve — **provided** `gcloud config set project` runs *before*
  `gcloud auth application-default login`, because: "If you have the project set in your Google Cloud
  CLI config, and you have the required permissions on that project, the quota project is set by
  default when you create the local ADC file."
  (<https://docs.cloud.google.com/docs/quotas/set-quota-project>)

  > **This ordering is the single most actionable pre-flight instruction in this document.**
- Fixes if it goes wrong (<https://docs.cloud.google.com/docs/authentication/troubleshoot-adc>):
  `gcloud auth application-default set-quota-project PROJECT_ID`;
  `gcloud config set billing/quota_project PROJECT_ID` (gcloud CLI only); the `x-goog-user-project`
  header for direct REST; the `--billing-project` flag per command.
- Python/Go/Java/Node/C#/PHP client-library override env var: **`GOOGLE_CLOUD_QUOTA_PROJECT`**
  (<https://docs.cloud.google.com/docs/quotas/set-quota-project>). Precedence: programmatic > env var
  > credentials.

### 4.5 Why this is a non-issue on Cloud Run

- On Cloud Run, ADC resolves to step 3 — the **attached service account via the metadata server**.
- No quota project is needed, because "**Service account:** If the principal for the API call is a
  service account, including by impersonation, the project associated with the service account is
  used as the quota project." (<https://docs.cloud.google.com/docs/quotas/quota-project>)
- ADK agrees operationally: "When deploying on Google Cloud infrastructure (Agent Runtime, Cloud Run,
  GKE), credentials are automatically provided." (<https://adk.dev/get-started/google-cloud/>)

**Workshop implication: the quota-project trap is strictly a laptop problem.** Code that works in
Cloud Run can fail locally and vice versa. Say this explicitly so attendees don't debug the wrong
layer.

### 4.6 Terraform's google provider and quota project

From the provider reference (source of truth:
`github.com/hashicorp/terraform-provider-google/blob/main/website/docs/guides/provider_reference.html.markdown`;
the Registry rendering at
<https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/provider_reference> is
JS-rendered and not plain-HTTP fetchable):

- `user_project_override` — "Controls the [quota project] used in requests to GCP APIs for the purpose
  of preconditions, quota, and billing." **Defaults to `false`.** Env var `USER_PROJECT_OVERRIDE`.
  When true the provider sends `X-Goog-User-Project`.
- `billing_project` — "A quota project to send in `user_project_override`, used for all requests sent
  from the provider." **Ignored if `user_project_override` is false or unset.** Env var
  `GOOGLE_BILLING_PROJECT`.
- **Notable:** the provider docs contain a *commented-out* paragraph about reading the quota project
  from ADC, with the inline note `TODO: quota project is not currently read from ADC file
  b/360405077`. In other words, **`gcloud auth application-default set-quota-project` does not fix
  Terraform** — you need `user_project_override` + `billing_project`. This is the substance of
  <https://github.com/hashicorp/terraform-provider-google/issues/24500> and
  <https://github.com/hashicorp/terraform-provider-google/issues/7351> (issue-tracker evidence,
  flagged as anecdotal; the commented-out TODO in the provider's own docs source is primary).

For this stack — Cloud Run, Firestore, GCS, Artifact Registry, all resource-based — you should **not**
need `user_project_override`. It matters for client-based APIs (`apikeys`, `cloudidentity`,
`firebase`, `securitycenter`).

---

## 5. Vertex AI regional availability — the finding that reshapes the region choice

Primary source for §5.1–5.3: <https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations>
(availability matrix parsed from page source).

### 5.1 Headline: current Gemini models have no US regional availability, and almost none in Europe

**Every Gemini 3.x model has zero regional-endpoint availability in the United States.**

| Model | `us-central1` and all other US regions |
|---|---|
| `gemini-3.8-flash`, `3.7-flash`, `3.6-flash`, `3.5-flash`, `3.5-flash-lite`, `3.1-flash-lite`, `3.1-pro-preview`, `3-flash-preview` | **NONE** |
| `gemini-2.5-pro`, `2.5-flash`, `2.5-flash-lite`, `2.5-flash-image` | all 7 US regions |

Europe:

| Model | European regional availability |
|---|---|
| `gemini-3.5-flash` | **`europe-west2` (London) and `europe-west3` (Frankfurt) ONLY** |
| all other Gemini 3.x | **NONE** |
| `gemini-2.5-flash` | 9 European regions incl. `europe-west1` |
| `gemini-2.5-pro` | `europe-west1`, `-west4`, `-north1`, `-central2`, `-west8`, `-southwest1`, `-west9` |

**So: `us-central1` and `europe-west1` each serve only the Gemini 2.5 family.**

### 5.2 The `global` endpoint

- "Global endpoints cover the entire world and provide higher availability and reliability than single
  regions." … "Selecting a global endpoint for your requests can improve overall availability while
  reducing resource exhausted (429) errors. Don't use the global endpoint if you have ML processing
  requirements, because you can't control or know which region your ML processing requests are sent
  to."
- Banner: "Endpoints don't guarantee data residency or in-region ML processing."
- **Every current Gemini text model supports `global`**, including all 3.x and all 2.5.
- Documented limitations, verbatim: "The following capabilities are not available when using the
  global endpoint: Tuning; Batch prediction for Anthropic and OpenMaaS models; Retrieval-augmented
  generation (RAG) corpus (RAG requests are supported)." Provisioned Throughput on global is limited
  to a model subset (**UNVERIFIED** — the list is collapsed on the page).
- Google's recommendation: "for applications deployed across multiple Google Cloud regions, you should
  strongly consider using the global endpoint for a consistent API call and more robust design,
  unless your desired model or feature is only available regionally."
- Usage: `GOOGLE_CLOUD_LOCATION=global`; hostname drops the region prefix
  (`https://aiplatform.googleapis.com`).

### 5.3 Multi-region (jurisdictional) endpoints — the middle ground

| Multi-region | Location value | Hostname |
|---|---|---|
| United States | `us` | `https://aiplatform.us.rep.googleapis.com` |
| European Union | `eu` | `https://aiplatform.eu.rep.googleapis.com` |

Gemini 3.x on `us`/`eu` (both): `gemini-3.8-flash`, `3.7-flash`, `3.6-flash`, `3.5-flash-lite`,
`3.5-flash`, `3.1-flash-lite`, `3.1-flash-image`, `gemini-embedding-2`. Notably **the entire Gemini
2.5 family is NOT on `us`/`eu`** — it is regional-or-global only. Private Google Access is not
supported for multi-region endpoints.

For EU residency: `GOOGLE_CLOUD_LOCATION=eu` with `gemini-3.5-flash` is confirmed supported on both
the locations and the data-residency tables
(<https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/data-residency>). Note the
explicit caveat there: "The European Union multi-region (eu) endpoint strictly covers data residency
within EU member states. Geographies outside the European Union political boundary, including the
United Kingdom and Switzerland, are excluded."

### 5.4 What this means for co-locating the stack

`europe-west1` and `us-central1` both support all four infrastructure services:

| Service | `europe-west1` | Source |
|---|---|---|
| Cloud Run | ✅ Tier 1 pricing | <https://docs.cloud.google.com/run/docs/locations> |
| Firestore | ✅ regional (Belgium) | <https://docs.cloud.google.com/firestore/native/docs/locations> |
| Cloud Storage | ✅ | <https://docs.cloud.google.com/storage/docs/locations> |
| Artifact Registry | ✅ | <https://docs.cloud.google.com/artifact-registry/docs/repositories/repo-locations> |
| Gemini | ⚠️ **2.5 family only** | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations> |

**Conclusion: full single-region co-location is impossible if you want a Gemini 3.x model.** The
workable pattern is to pin Cloud Run + Firestore + GCS + Artifact Registry to one region and set the
model location independently to `global` (or `eu`/`us`).

**If the kit reuses one variable for both, attendees will get "model not found in location" errors.**

Recommended default: **`gemini-3.5-flash` on `global`** — GA, on the global endpoint, and the only
3.x model with any European regional fallback. Alternative for maximum stability and lowest cost:
`gemini-2.5-flash` in-region, which does co-locate.

**Firestore location gotchas** (<https://docs.cloud.google.com/firestore/native/docs/locations>):

- "Be aware that once you provision a database instance, **you cannot change its location setting**."
  For 40 fresh projects a wrong default is unrecoverable short of deleting the database.
- Multi-region composition: `eur3` = `europe-west1` + `europe-west4` (witness `europe-north1`);
  `nam5` = `us-central1` + `us-central2` (witness `us-east1`); `nam7` = `us-central1` + `us-east4`.
  SLA: multi-region ≥ 99.999%, regional ≥ 99.99%.
- **The "location of default Google Cloud resources" trap:** "when you provision your default
  Firestore database, its location might have already been set, either during project creation or when
  setting up another service that shares this location dependency." It is immutable and App
  Engine-linked. "Any non-default Firestore database instances in your project do not share this
  location dependency."

> ⚠️ **Unresolved tension — decide this before the workshop.** Using a *named* (non-default) Firestore
> database avoids the location trap above, but Firestore's pricing page says named databases "**do not
> qualify for the free quota**" (§8.1). Using `(default)` keeps the free quota but inherits the
> location dependency. At workshop volumes the Firestore bill is a fraction of a cent either way, so
> **prefer the named database for determinism** — but verify the location behaviour on one clean
> project first, and note that this makes Firestore a (tiny) billed line item.

---

## 6. ADK 2.x specifics verified against source

Verified directly against `google/adk-python` at version **2.8.0** (`src/google/adk/version.py`).

### 6.1 `GOOGLE_GENAI_USE_VERTEXAI` is deprecated — resolved

The task brief assumed `GOOGLE_GENAI_USE_VERTEXAI=TRUE`. In ADK 2.x the variable has been renamed.
From `src/google/adk/utils/env_utils.py`:

```python
def is_enterprise_mode_enabled() -> bool:
  if 'GOOGLE_GENAI_USE_ENTERPRISE' in os.environ:
    return is_env_enabled('GOOGLE_GENAI_USE_ENTERPRISE')
  if 'GOOGLE_GENAI_USE_VERTEXAI' in os.environ:
    warnings.warn(
        'GOOGLE_GENAI_USE_VERTEXAI is deprecated, please use'
        ' GOOGLE_GENAI_USE_ENTERPRISE instead',
        DeprecationWarning, stacklevel=2)
    return is_env_enabled('GOOGLE_GENAI_USE_VERTEXAI')
  return False
```

So: **`GOOGLE_GENAI_USE_VERTEXAI` still works** (this resolves an open question), but emits a
`DeprecationWarning`, and `GOOGLE_GENAI_USE_ENTERPRISE` takes precedence if both are set. Accepted
truthy values are `"true"` or `"1"` (case-insensitive) — note that `"TRUE"` works, `"yes"` does not.

ADK's docs confirm and explain the rename (<https://adk.dev/get-started/google-cloud/>):

> "`GOOGLE_GENAI_USE_ENTERPRISE` was previously `GOOGLE_GENAI_USE_VERTEXAI`. These variable names are
> equivalent and do the same thing. If you set `GOOGLE_GENAI_USE_ENTERPRISE` and your agent does not
> connect to Agent Platform, you're on an older ADK version."

**Recommendation for the kit: set `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`.** Setting both is safe if you
want to tolerate older ADK versions, at the cost of a deprecation warning in the logs.

The generated Cloud Run Dockerfile (`cli_deploy.py`, `_DOCKERFILE_TEMPLATE`) bakes in:

```dockerfile
ENV GOOGLE_GENAI_USE_ENTERPRISE=1
ENV GOOGLE_CLOUD_PROJECT={gcp_project_id}
ENV GOOGLE_CLOUD_LOCATION={gcp_region}
```

Google's own docs now show the client constructor as `genai.Client(enterprise=True, project=...,
location=...)`, not `vertexai=True`.

### 6.2 The dev UI is opt-in, and ADK warns against deploying it

From `src/google/adk/cli/cli_tools_click.py` in 2.8.0, the `--with_ui` flag is
`is_flag=True, default=False` with help text:

> "Optional. Deploy ADK Web UI if set. (default: deploy ADK API server only). WARNING: The web UI is
> for development and testing only — do not use in production."

and a runtime warning:

> "ADK Web is for development purposes. It has access to all data and should not be used in
> production."

The generated Dockerfile also actively strips dev endpoints: `# Remove dev_server.py to ensure
production-safe endpoints only (disabling dev endpoints in production)`.

**Workshop implication:** the dev UI must be explicitly enabled, and combining it with a public
`allUsers` Cloud Run URL exposes an interface that "has access to all data" to the internet. For a
40-person workshop, prefer keeping the service private and having attendees reach it via
`gcloud run services proxy` (authenticated local proxy). This also sidesteps the domain-restricted-
sharing problem in §7.2 entirely — **strongly recommended**.

### 6.3 What `adk deploy cloud_run` actually runs

From `cli_deploy.py`: it generates a Dockerfile then shells out to

```
gcloud run deploy SERVICE --source TEMP_DIR --project P [--region R] --port PORT --verbosity V
```

`gcloud run deploy --source` builds via Cloud Build and pushes to an Artifact Registry repo. Default
container port is 8000. If your Terraform builds and pushes the image itself, you bypass all of this
— but then you must bake `--with_ui` into your own image if you want the dev UI.

---

## 7. Organization-policy defaults that bite corporate Workspace users

### 7.0 The "secure by default" baseline — verified

> "**Google Cloud security baseline constraints are enforced for all organizations created on or
> after May 3, 2024.**" Organizations created between February and April 2024 "might also have these
> default policy enforcements set."
> — <https://docs.cloud.google.com/resource-manager/docs/manage-baseline-constraints>

The seven baseline constraints applied automatically:

1. `constraints/iam.managed.disableServiceAccountKeyCreation`
2. `constraints/iam.disableServiceAccountKeyUpload`
3. `constraints/iam.automaticIamGrantsForDefaultServiceAccounts`
4. **`constraints/iam.allowedPolicyMemberDomains`**
5. `constraints/essentialcontacts.managed.allowedContactDomains`
6. `constraints/compute.managed.restrictProtocolForwardingCreationForTypes`
7. `constraints/storage.uniformBucketLevelAccess`

The two that break this workshop are **#4** (blocks a public Cloud Run URL) and **#1** (blocks SA
keys). **#3** and **#7** change behaviour silently.

### 7.1 `iam.disableServiceAccountKeyCreation`

- "prevent all users from creating and uploading service account keys, **including those with
  `iam.serviceAccountKeys.create` permission**"
  (<https://docs.cloud.google.com/iam/docs/best-practices-service-accounts>).
- Default: enforced by default (as the *managed* variant) for orgs created on/after 2024-05-03.
- **Symptom (detectable):** gcloud and REST both return
  `Key creation is not allowed on this service account.` (HTTP 400) —
  <https://docs.cloud.google.com/iam/docs/troubleshoot-org-policies>.

**Workshop impact:** if the kit or the local-dev instructions ever run
`gcloud iam service-accounts keys create`, corporate attendees fail. **Design the kit entirely around
ADC + Cloud Run's attached service account. Never a downloaded key.** (The stack already does this.)

### 7.2 `iam.allowedPolicyMemberDomains` (domain restricted sharing) — the big one

- Restricts which principals can be granted IAM roles. Supports **allow values only** — "does not
  support Deny values."
- **Default:** "**If your organization was created on or after May 3, 2024, then the
  `iam.allowedPolicyMemberDomains` legacy managed constraint is enforced by default, with your domain
  listed as the only allowed value.**"
- **`allUsers` / `allAuthenticatedUsers` are blocked by default.** "When using domain-restricted
  sharing, `allUsers` and `allAuthenticatedUsers` principals are blocked by default." The doc
  explicitly names "public Cloud Run services" among the cases needing an exception.
  Sources: <https://docs.cloud.google.com/organization-policy/restrict-domains>
- **Cloud Run's own confirmation, verbatim:** "These instructions won't succeed if your project is
  under a domain restricted sharing organization policy that restricts granting IAM roles to the
  `allUsers` member type." — <https://docs.cloud.google.com/run/docs/authenticating/public>
- **Exact symptom, ready for a regex:**

  ```
  ERROR: (gcloud.projects.set-iam-policy) FAILED_PRECONDITION: One or more users named in the policy
  do not belong to a permitted customer.
  ```

  Match on `do not belong to a permitted customer`.

**The documented workaround** — disable the Cloud Run invoker IAM check, now the *recommended* way to
make a service public (<https://docs.cloud.google.com/run/docs/authenticating/public>):

```bash
gcloud run deploy SERVICE --no-invoker-iam-check
gcloud run services update SERVICE --no-invoker-iam-check
# YAML/Terraform annotation: run.googleapis.com/invoker-iam-disabled: 'true'
```

> ⚠️ **Security callout.** `--no-invoker-iam-check` makes the service fully public with *no auth at
> all*. Combined with the ADK dev UI, which "has access to all data" (§6.2), that is worse than
> `allUsers` + IAM. **For this workshop, prefer a private service reached via
> `gcloud run services proxy`.** That works identically for gmail and corporate attendees and needs
> no org-policy exception.

Other escape hatches (conditional org policy + resource tags; temporarily disabling DRS) require
org-admin rights an attendee will not have.

### 7.3 `run.allowedIngress`

- "Administrators can restrict the ingress settings that developers can select by setting the
  `run.allowedIngress` organization policy." Values: `all`, `internal`,
  `internal-and-cloud-load-balancing`. "only applies to new deployments."
  (<https://docs.cloud.google.com/run/docs/securing/ingress>)
- **Default: UNVERIFIED as an explicit statement.** It is **not** in the security baseline, so it is
  not enforced by default on new organizations — but mature corporate orgs very commonly set it to
  `is:internal-and-cloud-load-balancing`.
- **Symptom: UNVERIFIED** — no primary doc gives the literal string. It follows the generic form in
  §7.9 with HTTP 412 / `FAILED_PRECONDITION`. **Detect via `describe --effective`, not error
  matching.**

### 7.4 `compute.vmExternalIpAccess`

- List constraint defining which VMs may use public IPs; blanket block is `allValues = DENY`.
  Newer managed variant `constraints/compute.managed.vmExternalIpAccess` is boolean.
  (<https://docs.cloud.google.com/organization-policy/reference/org-policy-constraints>)
- **Default:** unset (all VMs may use external IPs). Not in the security baseline. Not applied
  retroactively.
- Symptom is downstream rather than crisp; the documented GKE example reads "The effective policy for
  `constraints/compute.vmExternalIpAccess` is set to DENY_ALL."
- **Workshop relevance: LOW.** This stack provisions no Compute Engine VMs. It matters only if Cloud
  Build uses a VM-backed private pool. Report it for completeness; not a blocker.

### 7.5 `iam.automaticIamGrantsForDefaultServiceAccounts`

- "prevents the default service accounts from being granted roles automatically" — specifically
  prevents the Compute Engine / App Engine default SAs from automatically receiving `roles/editor`.
  (<https://docs.cloud.google.com/organization-policy/restrict-service-accounts>)
- **Default: "If you created your organization after May 3, 2024, this constraint is enforced by
  default."**
- **Critical side effect, verbatim:** "If you enforce this constraint in a project, then **some Google
  Cloud services cannot automatically create default service accounts**. As a result, if the project
  runs workloads that need to impersonate a service account, the project might not contain a service
  account that the workload can use."
- **Symptom:** the constraint "does not generate direct errors." Failures surface **downstream** as
  opaque `PERMISSION_DENIED` from whatever the runtime SA tried to do
  (<https://docs.cloud.google.com/iam/docs/troubleshoot-org-policies>).

**Workshop impact — HIGH and silent.** This is why the kit must use a **user-managed runtime service
account with explicit role grants** (§3.4) rather than leaning on the default SA being Editor.

### 7.6 `storage.publicAccessPrevention` and uniform bucket-level access

- **publicAccessPrevention:** buckets default to `inherited`; the constraint "is not set by default."
  Not in the security baseline. **Symptom, verbatim:** "Requests to add `allUsers` and
  `allAuthenticatedUsers` to an IAM policy or ACL fail with **`412 Precondition Failed`**."
  (<https://docs.cloud.google.com/storage/docs/public-access-prevention>)
- **uniformBucketLevelAccess IS a new-org default** — item 7 of the baseline, "Prevents per-object
  ACLs in Cloud Storage buckets."

  **Terraform impact:** set `uniform_bucket_level_access = true` on the bucket and never use
  `google_storage_object_acl` / `google_storage_bucket_acl`. Harmless on gmail projects, required on
  corporate ones. **Make it the kit default.**

### 7.7 `gcp.resourceLocations`

- "limits the physical location of a new resource." Value groups use an `in:` prefix —
  `in:us-locations`, `in:europe-locations`, etc. Applies only to newly created resources.
- **Default: UNVERIFIED as an explicit statement.** Not in the security baseline, so not
  auto-enforced — but it is one of the most commonly set constraints in EU-regulated corporates.
- **Symptom, verbatim pattern (HTTP 412):**

  ```
  Location ZONE:us-east1-b violates constraint constraints/gcp.resourceLocations on the resource
  projects/policy-violation-test/zones/us-east1-b/instances/instance-3.
  ```

  Match on `violates constraint constraints/gcp.resourceLocations`.
  (<https://docs.cloud.google.com/resource-manager/docs/organization-policy/defining-locations>)
- **Which of this stack's services enforce it — all but Vertex AI**
  (<https://docs.cloud.google.com/resource-manager/docs/organization-policy/defining-locations-supported-services>):
  Cloud Run ("when you create a top-level resource, such as a `Service`"), Firestore, Artifact
  Registry ("when you create a repository"), Cloud Build, Cloud Storage ("when you create a `bucket`
  resource"). Vertex AI is not listed.

  > **Doc inconsistency to flag:** the `defining-locations` page says Cloud Storage is excluded from
  > enforcement; the supported-services page lists bucket creation as enforced. Assume GCS **is**
  > enforced.

**Workshop impact — HIGH for corporate attendees.** If the stack hardcodes `us-central1` and the
attendee's org is pinned to `in:europe-locations`, five of six resources fail. **Region must be a
variable, and the pre-flight must read this constraint.**

### 7.8 Can a corporate Workspace user create a project?

**Yes by default.** Verbatim: "**The Project Creator role is granted by default to the entire domain
of a new organization resource and to free trial users.**"
(<https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects>) Required permission
`resourcemanager.projects.create`, in `roles/resourcemanager.projectCreator`. A personal-gmail user
with no organization can create the project "as the top level of its own resource hierarchy."

**Caveat:** the default grant happens at *organization creation time*, and mature corporate orgs
frequently revoke domain-wide `projectCreator` as a hardening step. **Test empirically in the
pre-flight; don't assume.** (Exact error string when the permission is missing: **UNVERIFIED**.)

### 7.9 Reading effective org policies from the CLI

```
gcloud org-policies describe CONSTRAINT
    (--folder=FOLDER_ID | --organization=ORGANIZATION_ID | --project=PROJECT_ID)
    [--effective]
```
<https://docs.cloud.google.com/sdk/gcloud/reference/org-policies/describe>. Legacy equivalent:
`gcloud resource-manager org-policies describe ORG_POLICY_ID --project=P --effective`
(<https://docs.cloud.google.com/sdk/gcloud/reference/resource-manager/org-policies/describe>).

Generic violation error shape, verbatim from
<https://docs.cloud.google.com/organization-policy/troubleshoot-policies>:

```
Organization Policy check failure: the external IP of this instance violates the
constraints/sql.restrictPublicIp enforced at the 123456789 project.
```

Constraint names appear directly in API error responses, so a pre-flight can regex
`constraints/[a-zA-Z.]+` out of any failure.

**UNVERIFIED:** whether a plain project-level user always holds `orgpolicy.policy.get`. If the
describe call itself returns `PERMISSION_DENIED`, treat that as "corporate org, ask your admin" —
**not** as "no policy set."

---

## 8. Cost

**Checked 2026-09-03.** us-central1 headline; europe-west1 deltas noted. Two billing topologies are
costed separately because several free tiers are **per billing account**, not per project:

- **Topology A** — each attendee on their own billing account (typical: everyone uses their own $300
  trial).
- **Topology B** — all 40 projects on one shared corporate billing account.

### 8.1 Unit prices

**Cloud Run** (<https://cloud.google.com/run/pricing>) — `us-central1` and `europe-west1` are both
Tier 1 and the request-based table is numerically identical.

| Resource | us-central1 / europe-west1 |
|---|---|
| CPU, **active** | $0.000024 per vCPU-second |
| CPU, **idle** (min instance) | $0.0000025 per vCPU-second |
| Memory, active or idle | $0.0000025 per GiB-second |
| Requests | $0.40 per million (verified us-central1) |

Free tier: "CPU – First 180,000 vCPU-seconds free per month / RAM – First 360,000 GiB-seconds free
per month / Requests – 2 million requests free per month." Critically: "The free tier usage is
**aggregated across projects by billing account**."

**CPU is not billed when idle with `min-instances=0`:** "By default, Cloud Run only charges for the
CPU and memory allocated to an instance when: The instance is starting. The instance is gracefully
shutting down… At least one request is being processed." And: "Idle instances that are not minimum
instances are not charged."

Instance-based billing (opt-in, bills the entire container lifetime): $0.000018/vCPU-s,
$0.000002/GiB-s, free tier 240,000 vCPU-s + 450,000 GiB-s. Networking: "There is no charge for data
transfer to Google Cloud resources in the same region."

**Artifact Registry** (<https://cloud.google.com/artifact-registry/pricing>): 0 → 0.5 GiB-month free;
above that **$0.10/GiB-month** ($0.000136986/GiB-hour). Same-location data transfer $0.00/GiB (so
Cloud Run pulling an in-region image is free). **"Pricing applies to billing accounts, not individual
Google Cloud projects… the limit for the storage free tier is for total usage across all the attached
projects."** ← the key gotcha for Topology B.

**Firestore** (<https://cloud.google.com/firestore/pricing>):

| Item | us-central1 | europe-west1 |
|---|---|---|
| Reads | $0.03 / 100k | $0.033 / 100k |
| Writes | $0.09 / 100k | $0.099 / 100k |
| Deletes | $0.01 / 100k | $0.011 / 100k |
| Stored data | $0.15 / GiB-month | $0.165 / GiB-month |

Free quota (same in both regions): 1 GiB stored, 50,000 reads/day, 20,000 writes/day, 20,000
deletes/day, 10 GiB egress/month — **per project** ("Firestore allows exactly one free database per
project"). 40 projects get 40× the quota. **Trap:** "To create a named (non-default) database, you
must enable billing… those databases **do not qualify for the free quota**." See the tension noted in
§5.4. Also: minimum one document read per query even with zero results.

**Cloud Storage** (<https://cloud.google.com/storage/pricing>): Standard single-region **$0.020/GiB-
month** in both us-central1 and europe-west1. Class A $0.005/1,000 ops; Class B $0.0004/1,000 ops
(flat namespace).

**Always-free is US-only:** "5 GB-months of regional storage (**US regions only**)… 5,000 Class A
Operations per month. 50,000 Class B Operations per month" and "Free Tier benefits for Cloud Storage
apply only to usage in the `us-east1`, `us-west1`, and `us-central1` regions."
(<https://cloud.google.com/free/docs/free-cloud-features>) → **a europe-west1 bucket gets no free
tier** (amounts here are still fractions of a cent).

**Vertex AI Gemini** — note the URL moved:
`cloud.google.com/vertex-ai/generative-ai/pricing` → <https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing>.
Per 1M tokens; the `≤200K` / `>200K` split is the long-context tier.

| Model | Region | Input ≤200K | Output ≤200K |
|---|---|---|---|
| Gemini 3.1 Pro Preview | Global | $2.00 | $12.00 |
| Gemini 3.8 Flash (intro, thru 2026-12-31) | Global | $0.75 | $3.75 |
| Gemini 3.8 Flash (intro) | Non-global | $0.825 | $4.125 |
| Gemini 3.5 Flash | Global | $1.50 | $9.00 |
| Gemini 3.5 Flash-Lite | Global | $0.30 | $2.50 |
| Gemini 2.5 Pro | — | $1.25 (>200K: $2.50) | $10.00 (>200K: $15.00) |
| Gemini 2.5 Flash | — | $0.30 | $2.50 |

> Banner, verbatim: "Gemini 3.8 Flash, Gemini 3.7 Flash, Gemini 3.6 Flash… are offered with
> introductory pricing of $0.75 / $3.75 per 1M tokens input / output through December 31, 2026.
> Starting January 1, 2027, standard pricing of $1.5 / $7.5 per 1M tokens input / output will apply."
> **Budget a 2× step on 2027-01-01 if the kit is reused.**

Note the Gemini 3 table charges ~10% more for pinned regional endpoints than for `global`.

**PDF input, verbatim:** "**PDFs are billed as image input, with one PDF page equivalent to one
image.**" The pricing page gives no tokens-per-image figure for text models — only for
image-*generation* models (e.g. "Gemini 3 Pro Image charges 560 tokens per input image"). The
document-understanding doc says only that "With Gemini 3 models, document tokenization uses a
variable sequence length which replaces the Pan and Scan method used in previous models."

> **Tokens per PDF page: UNVERIFIED.** The arithmetic below uses a 258–1,120 tok/page sensitivity
> band. It moves the per-attendee total by **under 2 cents**, so it does not matter here — but run
> `countTokens` against a real invoice before quoting a figure.

**Vertex AI has NO free tier.** It does not appear in the Always Free product list. The Gemini API
free tier (AI Studio, `generativelanguage.googleapis.com`) is a *different product* and does not
apply. Inference bills from the first token; the $300 trial credit is what absorbs attendee spend.

**Cloud Build** (<https://cloud.google.com/build/pricing>): "Each billing account comes with **2,500
free build-minutes per month**" for `e2-standard-2` in the default pool; above that **$0.006/build-
minute**. Note: *per month*, not per day — the marketing `/free` page's "120 build-minutes/day" is
inconsistent; trust the pricing/docs page.

**Cloud Logging** (<https://cloud.google.com/products/observability/pricing>): $0.50/GiB with "First
50 GiB/**project**/month" free. 40 projects = 40× 50 GiB. Zero risk.

### 8.2 Scenario (a) — the workshop hour, per attendee

**Assumptions, all of them:** `us-central1`; Cloud Run request-based billing, 1 vCPU / 512 MiB,
`min-instances=0`; container awake 30 min = 1,800 s; 200 requests; one image build of 5 build-minutes
on `e2-standard-2`; image 1.5 GiB; 30 agent turns of 4,000 in + 800 out; 5 further document turns of
4,000 text in + 2 PDF pages + 800 out; every request under 200K input tokens; 300 Firestore reads +
300 writes + 50 deletes on a `(default)` database; 20 GCS objects × 200 KB = 4 MB, 20 Class A + 100
Class B ops; logging well under 50 GiB.

**Cloud Run**
- `1 vCPU × 1,800 s = 1,800 vCPU-s × $0.000024` = **$0.0432**
- `0.5 GiB × 1,800 s = 900 GiB-s × $0.0000025` = **$0.00225**
- `200 / 1,000,000 × $0.40` = **$0.00008**
- List subtotal **$0.04553** → free tier: 1,800 ≪ 180,000 ✓, 900 ≪ 360,000 ✓ → **$0.00**
- Topology B: `40 × 1,800 = 72,000 < 180,000` ✓; `40 × 900 = 36,000 < 360,000` ✓ → **still $0.00**

**Cloud Build** — `5 min × $0.006 = $0.030` list; free 2,500 min/month; Topology B `40 × 5 = 200` ✓ →
**$0.00**. (If attendees build locally and push, $0 either way.)

**Artifact Registry**
- List: `1.5 GiB × 1 h × $0.000136986` = $0.000205
- Topology A (0.5 GiB free): `1.0 × $0.000136986` = **$0.000137**
- Topology B (one 0.5 GiB allotment for the account): `(40×1.5 − 0.5) = 59.5 GiB × $0.000136986` =
  **$0.00815 for the whole cohort-hour**
- Image pull by Cloud Run in-region: **$0.00**

**Vertex AI Gemini** — token totals: input `30×4,000 + 5×4,000 = 140,000` text plus `10` page-images
at 258–1,120 tok each = **142,580 – 151,200 input**; output `35 × 800` = **28,000**.

| Model | Input | Output | **Per attendee** | **× 40** |
|---|---|---|---|---|
| Gemini 2.5 Flash ($0.30/$2.50) | $0.0428–$0.0454 | $0.0700 | **$0.113 – $0.115** | **~$4.5 – $4.6** |
| Gemini 3.8 Flash, global, intro ($0.75/$3.75) | $0.1069–$0.1134 | $0.1050 | **$0.212 – $0.218** | **~$8.5 – $8.7** |
| Gemini 3.8 Flash, non-global ($0.825/$4.125) | $0.1176–$0.1247 | $0.1155 | $0.233 – $0.240 | ~$9.3 – $9.6 |
| Gemini 3.5 Flash-Lite ($0.30/$2.50) | $0.0428–$0.0454 | $0.0700 | $0.113 – $0.115 | ~$4.5 – $4.6 |
| Gemini 2.5 Pro ($1.25/$10.00) | $0.1782–$0.1890 | $0.2800 | **$0.458 – $0.469** | **~$18.3 – $18.8** |
| Gemini 3.1 Pro Preview ($2.00/$12.00) | $0.2852–$0.3024 | $0.3360 | **$0.621 – $0.638** | **~$24.8 – $25.5** |

Note how insensitive this is to the PDF-token unknown: the 258→1,120 swing moves the flagship total
by 1.7 cents. **Output tokens dominate.**

**Firestore** — reads `300/100,000 × $0.03 = $0.00009`; writes `300/100,000 × $0.09 = $0.00027`;
deletes `50/100,000 × $0.01 = $0.000005`; list total **$0.000365**. Free daily quota is per project
(300 ≪ 50,000; 300 ≪ 20,000; 50 ≪ 20,000) → **$0.00** in both topologies and both regions.
(europe-west1 list would be $0.000402 — also absorbed.)

**Cloud Storage** — Class A `20/1,000 × $0.005 = $0.0001`; Class B `100/1,000 × $0.0004 = $0.00004`;
1 h storage `0.00391 GiB × $0.000027397 ≈ $0.0000001`. List ≈ **$0.00014**. us-central1: absorbed by
5,000 Class A + 50,000 Class B free → **$0.00** (Topology B: `40 × 20 = 800 < 5,000` ✓).
**europe-west1: no free tier → $0.00014/attendee = $0.0056 for all 40.** Immaterial.

**Cloud Logging** — **$0.00**.

#### Workshop-hour totals

| | Per attendee | × 40 |
|---|---|---|
| Everything except Vertex AI (us-central1) | **$0.00** | **$0.00** (Topology B adds ~$0.008 Artifact Registry) |
| + Gemini 2.5 Flash | ~$0.11 | **~$4.50** |
| + Gemini 3.8 Flash (intro, global) | ~$0.21 | **~$8.60** |
| + Gemini 2.5 Pro | ~$0.46 | ~$18.50 |
| + Gemini 3.1 Pro Preview | ~$0.63 | ~$25 |

**The free tiers absorb 100% of Cloud Run, Cloud Build, Firestore, Cloud Storage (US region) and
Cloud Logging.** The entire bill is Gemini tokens. If attendees are on their own $300 trial credits,
out-of-pocket cost for the workshop hour is **$0**.

### 8.3 Scenario (b) — stack left idle for a week

168 h = 604,800 s; 1 month = 730 h = 2,628,000 s (Google's own GiB-hour → GiB-month factor).

**`min-instances = 0`**

| Component | Week | Month |
|---|---|---|
| Cloud Run compute | **$0.00** — no requests, no billable instance time | **$0.00** |
| Artifact Registry, Topology A (1.5 − 0.5 = 1.0 GiB billable) | `1.0 × 168 × $0.000136986` = **$0.0230** | `1.0 × $0.10` = **$0.100** |
| Artifact Registry, Topology B (59.5 GiB billable) | `59.5 × 168 × $0.000136986` = **$1.369 cohort** ($0.034 ea) | `59.5 × $0.10` = **$5.95 cohort** ($0.149 ea) |
| Firestore storage (≪1 GiB free/project) | $0.00 | $0.00 |
| GCS us-central1 (0.0039 GiB, 5 GB-mo free) | $0.00 | $0.00 |
| GCS europe-west1 (no free tier) | $0.000018 | $0.000078 |
| Cloud Logging | $0.00 | $0.00 |

→ **~$0.02/attendee/week, ~$0.10/attendee/month. For 40: ~$0.92/week, ~$4.00/month** (own accounts)
or ~$1.37/week, ~$5.95/month on one shared account. **It is essentially $0, and it is entirely the
Docker image sitting in Artifact Registry.** Deleting the images takes it to a true $0.

**`min-instances = 1`** (request-based billing, idle rate; 1 vCPU / 512 MiB)

Week: CPU `604,800 × $0.0000025 = $1.5120`; memory `302,400 × $0.0000025 = $0.7560`; list
**$2.2680/attendee/week**.

Applying the free tier (Topology A, 180,000 vCPU-s + 360,000 GiB-s/month):
- CPU billable `604,800 − 180,000 = 424,800 × $0.0000025` = **$1.0620**
- Memory `302,400 < 360,000` → **$0.00**
- \+ Artifact Registry $0.0230 → **≈ $1.085/attendee/week ≈ $43 for 40 for one week**

> **UNVERIFIED nuance:** the pricing page says "The free tier is applied as a **spending based
> discount** using Tier 1 pricing" but does not say which SKU rate values the discount. If the 180,000
> vCPU-seconds are valued at the *active* rate ($0.000024 → $4.32 of discount) rather than the idle
> rate, a week of idle would be fully absorbed and the answer would be **$0**. Treat $1.06/week as the
> conservative figure.

Month (Topology A): CPU `2,448,000 × $0.0000025 = $6.120`; memory `954,000 × $0.0000025 = $2.385`;
Cloud Run **$8.505** + AR $0.100 → **≈ $8.61/attendee/month ≈ $344 for 40**.

Topology B (shared free tier, consumed in ~2 days by one attendee): **≈ $91/week, ≈ $399/month for the
cohort**.

At 1 GiB memory instead of 512 MiB: ~$1.70/attendee/week, ~$11.89/attendee/month (~$476 for 40).

**⚠️ Instance-based billing + min-instances=1** removes the idle rate — you pay full instance rate for
the whole container lifetime: `2,628,000 × $0.000018 = $47.30` CPU + `1,314,000 × $0.000002 = $2.63`
memory, less the free tier → **~$44.7/attendee/month, ~$1,790 for 40.** **Keep the stack on
request-based billing.**

#### Idle summary

| Setting | /attendee/week | /attendee/month | 40 /month |
|---|---|---|---|
| **`min-instances=0`** | **~$0.02** | **~$0.10** | **~$4.00** (own) / ~$5.95 (shared) |
| `min-instances=1`, 512 MiB | ~$1.09 | ~$8.61 | ~$344 / ~$399 |
| `min-instances=1`, 1 GiB | ~$1.70 | ~$11.89 | ~$476 |
| `min-instances=1` + instance-based | ~$10.3 | ~$44.7 | ~$1,790 |

---

## 9. Is a free-trial billing account sufficient?

**Yes — comfortably.** The workshop hour costs $0.11–$0.63 of a $300 credit.

### 9.1 Trial terms

| Fact | Value |
|---|---|
| Credit | **$300 "Welcome credit"** |
| Duration | **90 days** |
| Credit card | Required at signup |
| Auto-charge at end | **No** — "no automatic charges, no commitment" |

Source: <https://docs.cloud.google.com/free/docs/free-cloud-features>

At 90 days or credit exhaustion: "your Free Trial billing account will be closed and **all of its
associated projects and resources will be stopped**," followed by a **30-day grace period** to upgrade
to a Paid account; otherwise "your Free Trial resources are **permanently deleted**." Upgrading is
**not** mandatory during the trial.

**Eligibility gate — matters for ~40 attendees:** you qualify only if "You've never been a paying user
of Google Cloud, Google Maps Platform, or Firebase" **and** "You haven't previously signed up for the
Free Trial."

> **Do not assume the $300 covers everyone.** Any attendee who has used GCP before is not eligible and
> will be on a paid billing account — or, worse, none at all. The pre-flight must check that billing
> is *linked and enabled*, not that a trial exists.

### 9.2 Trial restrictions (verbatim)

While on a Free Trial you cannot: "Add GPUs to your VM instances"; "Use Google Cloud Marketplace";
"**Request a quota increase**"; "Create VM instances that are based on Windows Server images"; "Create
Google Cloud VMware Engine resources." Also "GPUs and TPUs are not included in the Free Tier offer."

Credit-scope exclusions on the same page: the $300 "can't be used for Gemini API in AI Studio costs"
(that is AI Studio / `generativelanguage.googleapis.com`, **not** Vertex AI), and cannot be used for
"a generative AI partner model that is offered as a managed API, which is also known as model as a
service" (Anthropic/Llama-as-API in Model Garden).

**Can a trial account use Vertex AI Gemini? Yes.** The restrictions list contains **no** restriction on
Vertex AI first-party Gemini models; the two excluded categories are AI Studio and *partner* MaaS.
Google's own product page: "New customers get up to $300 in free credits to try Vertex AI and other
Google Cloud products." **A free-trial billing account can call Vertex AI Gemini and the credit pays
for it.**

> **UNVERIFIED:** the numeric default Gemini RPM/TPM quotas for a brand-new project, and whether trial
> accounts get *reduced* Vertex AI quota. Assume default per-project RPM quotas exist and that a trial
> account **cannot raise them** (quota increases are a listed trial restriction). Low risk here since
> each attendee has their own project — it would only bite if they shared one.
>
> **UNVERIFIED:** any trial-specific restriction on "Gemini for Google Cloud" (Code Assist / Cloud
> Assist). No primary doc found; do not claim one.

### 9.3 Project creation

- Signup provisions "My First Project."
- "**The Project Creator role is granted by default to the entire domain of a new organization
  resource and to free trial users.**"
- Quota mechanics: "If you create a project outside an organization resource, the quota on your user
  account is used." The console shows remaining quota once fewer than 30 remain.
  (<https://docs.cloud.google.com/resource-manager/docs/limits>)
- Free-trial users may request more (<https://support.google.com/cloud/answer/6330231>).

> **UNVERIFIED — the exact default project quota.** Google does not publish it. Community figures of
> ~12–30 are anecdotal; **do not put a number in the kit.** Low risk: each attendee needs one project.

### 9.4 Always Free tier summary

From <https://docs.cloud.google.com/free/docs/free-cloud-features>: Cloud Run 2M requests + 360,000
GB-seconds memory/month; Cloud Storage 5 GB-months regional (**US regions only**); Firestore 1 GiB
storage + 50,000 reads / 20,000 writes / 20,000 deletes per day **per project**; Artifact Registry
0.5 GB storage/month; Cloud Build 2,500 build-minutes/month.

> **Doc inconsistency:** the marketing page `cloud.google.com/free` says Cloud Build "120
> build-minutes/day"; the docs page and the Cloud Build pricing page both say 2,500/month. Trust the
> docs page.
>
> **Vertex AI / Gemini has no Always Free allowance.**

### 9.5 Billing must be enabled before APIs

- "A Google Cloud billing account is required to access the Google Cloud Free Tier."
- "Projects that aren't linked to an active Cloud Billing account **can't use Google Cloud … services,
  even if you only use services that are free**."
  (<https://docs.cloud.google.com/billing/docs/how-to/modify-project>)
- Billing is enabled "when the project is linked to an active Cloud Billing account in good standing."
  (<https://docs.cloud.google.com/billing/docs/how-to/verify-billing-enabled>)

> **UNVERIFIED:** the literal error string for enabling `aiplatform.googleapis.com` without billing.
> It is a `FAILED_PRECONDITION` / HTTP 400 from Service Usage; **match on `FAILED_PRECONDITION` +
> `billing`, not on an exact string.**

---

## 10. Proposed pre-flight verification script checks

Each check lists the detecting call and the symptom it prevents. Intended to run the day before, on
the attendee's laptop, against their own project.

### 10.1 Environment

| # | Check | Command | Prevents |
|---|---|---|---|
| 1 | gcloud installed and recent | `gcloud version --format=json` | Missing/ancient CLI lacking `org-policies`, `--no-invoker-iam-check` |
| 2 | Terraform installed and ≥ pinned version | `terraform version -json` | Provider constraint failures mid-workshop |
| 3 | `PROJECT_ID` resolves and gcloud is pointed at it | `gcloud config get-value project` | Everything silently applied to the wrong project |
| 4 | `GOOGLE_APPLICATION_CREDENTIALS` is **unset** | `[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]` | A stale SA key silently overrides ADC (§4.2) |
| 5 | ADC file exists | `test -f "$HOME/.config/gcloud/application_default_credentials.json"` | "Could not automatically determine credentials" at apply time |
| 6 | ADC has a quota project | `jq -r '.quota_project_id // "MISSING"' "$HOME/.config/gcloud/application_default_credentials.json"` | The quota-project error class (§4.3). Field name verified in `google-auth-library-python`. |
| 7 | ADC actually works | `gcloud auth application-default print-access-token >/dev/null` | Expired/revoked ADC discovered at apply time |

Remediation for 5–6, in this order (order matters, §4.4):
`gcloud config set project $PROJECT_ID && gcloud auth application-default login`.

### 10.2 Project and billing

| # | Check | Command | Prevents |
|---|---|---|---|
| 8 | Project exists and is ACTIVE | `gcloud projects describe "$PROJECT_ID" --format='value(lifecycleState)'` | Applying to a deleted/pending project |
| 9 | **Billing linked and enabled** | `gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)'` → must be `True` | `FAILED_PRECONDITION` + "billing" on API enablement; "can't use Google Cloud services even if free" (§9.5) |
| 10 | Project is/isn't in an organization | `gcloud projects describe "$PROJECT_ID" --format='value(parent.type,parent.id)'` | Branches the whole org-policy section; tells the attendee which failure class to expect |

### 10.3 APIs

| # | Check | Command | Prevents |
|---|---|---|---|
| 11 | Every required API enabled | `gcloud services list --enabled --project="$PROJECT_ID" --format='value(config.name)'` and diff against the §2.1 list | `Error 403: <Service> API has not been used in project <P> before or it is disabled` (§2.3) |
| 12 | `serviceusage.googleapis.com` specifically | same output, grep for it | Terraform cannot enable anything at all — the chicken-and-egg (§2.4) |
| 13 | **Enablement was ≥10 min ago** | Record a timestamp when the enable command runs; warn if the apply is within 10 min | The eventual-consistency race, worst on just-created projects (§2.3) |

### 10.4 IAM

| # | Check | Command | Prevents |
|---|---|---|---|
| 14 | Attendee is Owner (or has the §3.2 set) | `gcloud projects get-iam-policy "$PROJECT_ID" --flatten=bindings[].members --filter="bindings.members:user:$(gcloud config get-value account)" --format='value(bindings.role)'` | `setIamPolicy` denials; Editor-only attendees failing on role bindings (§3.1) |
| 15 | Permission probe (authoritative) | `cloudresourcemanager.projects.testIamPermissions` via REST — see below | Catches custom roles and conditional bindings that a role-name check misses |
| 16 | Compute default SA exists (if the stack uses it) | `gcloud iam service-accounts list --project="$PROJECT_ID" --filter='email~-compute@developer'` | Opaque `PERMISSION_DENIED` from a runtime identity that doesn't exist (§3.4, §7.5) |

> **There is no `gcloud projects test-iam-permissions` subcommand** — verified against
> <https://docs.cloud.google.com/sdk/gcloud/reference/projects> (12 subcommands, none is
> `test-iam-permissions`). Use the REST method, which "requires no pre-existing permissions on the
> target resource" and rejects wildcards
> (<https://docs.cloud.google.com/resource-manager/reference/rest/v3/projects/testIamPermissions>):

```bash
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://cloudresourcemanager.googleapis.com/v3/projects/${PROJECT_ID}:testIamPermissions" \
  -d '{"permissions":[
        "resourcemanager.projects.setIamPolicy",
        "iam.serviceAccounts.create",
        "iam.serviceAccounts.actAs",
        "run.services.create",
        "artifactregistry.repositories.create",
        "datastore.databases.create",
        "storage.buckets.create",
        "serviceusage.services.enable",
        "serviceusage.services.use",
        "aiplatform.endpoints.predict"
      ]}'
```

Any permission **absent from the response** is not held. `iam.serviceAccounts.actAs` is the one
attendees most often lack (§3.3).

### 10.5 Organization policies

| # | Constraint | Symptom it prevents |
|---|---|---|
| 17 | `iam.allowedPolicyMemberDomains` | `FAILED_PRECONDITION: One or more users named in the policy do not belong to a permitted customer` when granting `allUsers` `run.invoker` (§7.2) |
| 18 | `iam.disableServiceAccountKeyCreation` **and** `iam.managed.disableServiceAccountKeyCreation` | `Key creation is not allowed on this service account.` (§7.1) — check **both** variants |
| 19 | `iam.automaticIamGrantsForDefaultServiceAccounts` | Silent, downstream `PERMISSION_DENIED` from the runtime SA (§7.5) |
| 20 | `gcp.resourceLocations` | `violates constraint constraints/gcp.resourceLocations` on 5 of 6 resources if the region is wrong (§7.7) |
| 21 | `run.allowedIngress` | Cloud Run created with an ingress the org forbids (§7.3) |
| 22 | `storage.uniformBucketLevelAccess` | Bucket creation failing unless `uniform_bucket_level_access = true` (§7.6) |
| 23 | `storage.publicAccessPrevention` | `412 Precondition Failed` when adding `allUsers` to a bucket (§7.6) |
| 24 | `compute.vmExternalIpAccess` | Low relevance — report only (§7.4) |

```bash
for C in iam.allowedPolicyMemberDomains \
         iam.disableServiceAccountKeyCreation \
         iam.managed.disableServiceAccountKeyCreation \
         iam.automaticIamGrantsForDefaultServiceAccounts \
         gcp.resourceLocations \
         run.allowedIngress \
         storage.uniformBucketLevelAccess \
         storage.publicAccessPrevention \
         compute.vmExternalIpAccess; do
  printf '=== %s ===\n' "$C"
  gcloud org-policies describe "$C" --project="$PROJECT_ID" --effective 2>&1
done
```

Interpretation rules for the script:
- `NOT_FOUND` / no policy → unset → permissive → **PASS**.
- `PERMISSION_DENIED` on the describe itself → the attendee lacks `orgpolicy.policy.get` → report
  **"corporate org, ask your admin"**, *not* "no policy." (Whether an ordinary project user always
  holds this permission is **UNVERIFIED**.)
- Skip the whole block if check 10 showed the project has no organization parent.

### 10.6 Region and model reachability

| # | Check | Command | Prevents |
|---|---|---|---|
| 25 | Chosen infra region valid for all four services | `gcloud run regions list`; `gcloud artifacts locations list`; Firestore/GCS location lists | An apply that gets 4 of 6 resources in |
| 26 | Firestore database does not already exist / location not pre-pinned | `gcloud firestore databases list --project="$PROJECT_ID"` | The immutable-location trap (§5.4) — unrecoverable once wrong |
| 27 | **The model is actually callable end-to-end** | A single minimal `generateContent` against `$GOOGLE_CLOUD_LOCATION` and the configured model ID | Catches, in one shot: API not enabled, propagation lag, missing `aiplatform.user`, wrong region for a Gemini 3.x model, quota-project errors, and billing not enabled |

**Check 27 is the highest-value check in the whole script.** It exercises the exact path the workshop
depends on. Assert on the *specific* failure so the message is actionable:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/publishers/google/models/${MODEL_ID}:generateContent" \
  -d '{"contents":[{"role":"user","parts":[{"text":"ping"}]}]}'
```

(Use the global hostname for `location=global`; for a regional location use
`https://${LOC}-aiplatform.googleapis.com` and the matching path. Note the explicit
`x-goog-user-project` header, which is the header form of the quota project — §4.4.)

Suggested exit contract: **0** = ready to apply; **1** = attendee-fixable (re-run ADC login, enable
APIs, wait for propagation); **2** = needs an org admin (org policy or missing project-level role).

---

## 11. Open questions and unverified items

Carried forward from the research, with the recommended resolution.

| # | Item | Resolution |
|---|---|---|
| 1 | Is `cloudresourcemanager.googleapis.com` strictly required? Implied by `projects.setIamPolicy`, not verbatim-documented | **Test-apply against one clean project.** Highest-value dry run you can do. |
| 2 | Tokens per PDF page for Gemini 3.x text models | Run `countTokens` against a real 2-page invoice. Moves the total by <2¢. |
| 3 | Is the Cloud Run free-tier discount valued at the active or the idle CPU rate? | Affects only the `min-instances=1` figure. Irrelevant if you hard-code `min-instances=0`. |
| 4 | Literal "requires a quota project" error string on a Google page | Only found in issue trackers. Match on the condition, not the string. |
| 5 | Is `aiplatform.googleapis.com` client-based (and thus quota-project-sensitive)? | Evidence leans **no**. Pre-flight check 27 settles it empirically. |
| 6 | Concrete API propagation SLA | None published. "A few minutes" is all Google says. Budget 10 min. |
| 7 | Defaults for `run.allowedIngress` and `gcp.resourceLocations` | Not in the security baseline → permissive on a new org (sound inference, not a quoted default). Detect, don't assume. |
| 8 | Does an ordinary project user hold `orgpolicy.policy.get`? | Handle `PERMISSION_DENIED` explicitly in the script (§10.5). |
| 9 | Default project-creation quota for a new/trial account | Not published. Don't quote a number. |
| 10 | Default Gemini RPM/TPM quotas for a fresh project; trial-account reductions | Not retrievable. Low risk with one project per attendee. |
| 11 | Whether Terraform's provider will ever read `quota_project_id` from ADC | Provider docs carry `TODO … b/360405077`. Use `user_project_override` + `billing_project` if needed. |
| 12 | Named vs `(default)` Firestore database — location trap vs free quota | Decide before the workshop (§5.4). Cost impact is sub-cent either way. |

### Doc inconsistencies worth knowing

- **Cloud Build free tier:** 2,500 build-minutes/month (docs, pricing page) vs 120 build-minutes/day
  (marketing `/free`). Trust the docs.
- **`gcp.resourceLocations` and Cloud Storage:** `defining-locations` says GCS is excluded from
  enforcement; `defining-locations-supported-services` says bucket creation *is* enforced. Assume
  enforced.
- **Cloud Build role for ADK deploys:** Cloud Run docs say `roles/run.builder`; ADK docs say
  `roles/cloudbuild.builds.builder`. Grant both.
- **`iam.disableServiceAccountKeyCreation`:** the security baseline enforces the *managed* variant;
  most scripts and docs reference the legacy one. Check both.
