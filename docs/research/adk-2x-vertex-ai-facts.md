# ADK 2.x + Vertex AI (no API key) — pinned facts for the invoice-analysis workshop kit

Research date: **2026-09-03**. Every claim below carries a primary-source URL.
Anything I could not verify from a primary source is listed in the final section
and marked UNVERIFIED.

---

## Bottom line for the kit

**Install line** (nothing extra is needed for Vertex AI — there is no `vertexai` extra):

```bash
pip install "google-adk~=2.8"
```

- `google-adk` latest is **2.8.0**, uploaded **2026-08-26T23:26:17Z**, `requires_python >=3.10`.
  Source: `https://pypi.org/pypi/google-adk/json` (fetched 2026-09-03), and
  <https://pypi.org/project/google-adk/>
- It pins `google-genai<3,>=2.19`, which pip resolves to **google-genai 2.22.0**
  (uploaded 2026-09-02T18:06:00Z). Source: `https://pypi.org/pypi/google-genai/json`

**Env vars** (`.env` next to the agent package, loaded by ADK):

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=TRUE     # new name; GOOGLE_GENAI_USE_VERTEXAI=TRUE still works
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

plus, once, on the workstation:

```bash
gcloud auth application-default login
```

**Model id:** `gemini-3.5-flash` — GA, released 2026-05-19, 1,048,576-token context,
accepts `application/pdf` and `image/png|jpeg|webp|heic|heif`, supports structured
output and function calling.
<https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash>

**The single biggest gotcha:** `gemini-3.5-flash` is **not served from `us-central1`**.
Its documented availability is `global`, the `us` and `eu` multi-regions,
`northamerica-northeast1`, `europe-west2`, `europe-west3`, `asia-northeast1`,
`asia-south1`, `asia-southeast1`. Every ADK blog post and most ADK docs samples say
`GOOGLE_CLOUD_LOCATION=us-central1`, which will 404/NOT_FOUND for this model. Use
`global`. (Same source as above; region list quoted verbatim in §2.)

**Runner-up gotcha:** the ADK-1.x rule "`output_schema` disables tools and agent
transfer" is **dead**. It was removed in ADK Python **1.32.0** and on Vertex AI the
two now work together natively. See §5 — this changes the workshop's whole design space.

---

## 1. Package names and versions

| Package | Latest | Uploaded (UTC) | Python |
|---|---|---|---|
| `google-adk` | **2.8.0** | 2026-08-26T23:26:17 | `>=3.10` |
| `google-genai` | **2.22.0** | 2026-09-02T18:06:00 | `>=3.10` |

Source: PyPI JSON API, `https://pypi.org/pypi/google-adk/json` and
`https://pypi.org/pypi/google-genai/json`, fetched 2026-09-03.
Human pages: <https://pypi.org/project/google-adk/>, <https://pypi.org/project/google-genai/>

**ADK 2.0.0 GA was 2026-05-19.**
<https://github.com/google/adk-python/releases/tag/v2.0.0> and
<https://google.github.io/adk-docs/2.0/> ("ADK Python 2.0 is released for general
availability as of May 19, 2026.")

**1.x is still actively released in parallel.** Recent tags interleave:
`v2.7.1` (2026-08-17), `v1.39.0` (2026-08-17), `v2.8.0` (2026-08-26), `v1.39.1` (2026-08-27).
So "latest google-adk" is genuinely ambiguous unless you pin. Pin `~=2.8`.
<https://github.com/google/adk-python/releases>

**Extras.** `provides_extra` on 2.8.0 is exactly:

```
a2a, agent-identity, all, antigravity, benchmark, bigquery-analytics, community,
daytona, db, dev, docs, e2b, eval, extensions, gcp, mcp, oci, otel-gcp, redis,
slack, test, toolbox, tools
```

**There is no `vertexai` extra.** Talking to Vertex AI needs only the base package:
`google-genai` and `google-auth[pyopenssl]>=2.47` are unconditional core dependencies.
The `gcp` extra pulls `google-cloud-aiplatform[agent-engines]<2,>=1.148.1`, which you
only need for Agent Engine / Agent Runtime deployment, **not** for calling Gemini on
Vertex AI. Source: `requires_dist` in `https://pypi.org/pypi/google-adk/json`.

Other core pins worth knowing for the kit's `requirements.txt`:
`pydantic<3,>=2.12`, `fastapi<1,>=0.133`, `google-genai<3,>=2.19`, `authlib<2,>=1.6.6`.

---

## 2. Model id, document/vision capability, and regions

Target: **`gemini-3.5-flash`**.

All facts in this section from
<https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash>
(fetched 2026-09-03), quoted from the page's spec tables:

- **Model ID:** `gemini-3.5-flash`
- **Launch stage: GA.** Release date **May 19, 2026**. Retirement date "May 19, 2027 or later".
- **Modalities:** Text (in/out), Image (in), Audio (in), Video (in).
- **Context window:** 1,048,576. **Max output tokens:** 65,536.
- **Capabilities:** Structured output — Supported. Function calling — Supported.
  Thinking — Supported. System instructions — Supported. Context caching — Supported.
- **Document ("Text") limits — this is the PDF path:**
  - Max files per prompt: **3,000**
  - Max pages per file: **3,000**
  - Max file size per file for the API or Cloud Storage imports:
    **50 MB (`application/pdf`) or 7 MB (`text/plain`)**
  - Max file size per file for direct uploads through the console: **7 MB**
  - Supported MIME types: **`application/pdf`, `text/plain`**
- **Image limits:**
  - Max images per prompt: **3,000**
  - Max file size per file for inline data or console upload: **7 MB**
  - Max file size per file from Google Cloud Storage: **30 MB**
  - Supported MIME types: **`image/png`, `image/jpeg`, `image/webp`, `image/heic`, `image/heif`**

### Region availability (verbatim from the "Supported regions" table)

```
Model availability
  Global:        global
  Multi-region:  us, eu
  Americas:      northamerica-northeast1
  Europe:        europe-west2, europe-west3
  Asia Pacific:  asia-northeast1, asia-south1, asia-southeast1

Standard PayGo
  Global:        global
  Multi-region:  us, eu
```

**`us-central1` is not on that list.** For pay-as-you-go (what a workshop uses),
the *only* documented options are `global`, `us`, and `eu`. Use
`GOOGLE_CLOUD_LOCATION=global`.

### Is `global` an option? Yes, and it is the SDK default.

- Google Cloud: "Google also offers a global endpoint to improve overall availability
  and reduce error rates. The global endpoint can have a separate set of quotas from
  the regional endpoint and doesn't support data residency requirements." When using
  the global endpoint the URL is
  `https://aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/global/publishers/google/models/${MODEL_ID}:generateContent`
  rather than `https://${LOCATION}-aiplatform.googleapis.com`.
  <https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations>
- In the SDK, if `GOOGLE_CLOUD_LOCATION` is unset and no API key is set, the client
  **defaults `self.location = 'global'`**, and routes to `https://aiplatform.googleapis.com/`.
  Source (verbatim code):
  <https://github.com/googleapis/python-genai/blob/v2.22.0/google/genai/_api_client.py>
  ```python
  if not self.location and not self.api_key:
      if not self.custom_base_url:
          self.location = 'global'
  ...
  if ((self.api_key and not self.location) or self.location == 'global') and not self.custom_base_url:
      self._http_options.base_url = f'https://aiplatform.googleapis.com/'
  ```

### Do NOT use `gemini-flash-latest` in this kit

ADK docs samples use `gemini-flash-latest`, but the docs themselves warn:

> "Most code examples in ADK documentation use `gemini-flash-latest` to select the
> latest available Gemini Flash version. However, if you access Gemini from a regional
> endpoint, such as `us-central1`, this selection string may not work. In that case,
> use a specific model version string..."

<https://github.com/google/adk-docs/blob/main/docs/agents/models/google-gemini.md>

A `-latest` alias also hot-swaps under you: "This alias will get hot-swapped with every
new release of a specific model variation." A workshop kit must pin an explicit id.
<https://ai.google.dev/gemini-api/docs/models>

---

## 3. Vertex AI with no API key: env vars, ADC, IAM, Cloud Run

### The environment variable was renamed

`GOOGLE_GENAI_USE_VERTEXAI` → **`GOOGLE_GENAI_USE_ENTERPRISE`**. The ADK docs state:

> "`GOOGLE_GENAI_USE_ENTERPRISE` was previously `GOOGLE_GENAI_USE_VERTEXAI` — These
> variable names are equivalent and do the same thing. If you set
> `GOOGLE_GENAI_USE_ENTERPRISE` and your agent does not connect to Agent Platform,
> you're on an older ADK version. Use `GOOGLE_GENAI_USE_VERTEXAI` instead, or update
> to a newer version of ADK."

<https://github.com/google/adk-docs/blob/main/docs/get-started/google-cloud.md>

Confirmed in `google-genai` 2.22.0 source — **both are read, `USE_ENTERPRISE` wins**,
and a conflict emits a warning:

```python
env_enterprise_str = os.environ.get('GOOGLE_GENAI_USE_ENTERPRISE', None)
env_vertexai_str   = os.environ.get('GOOGLE_GENAI_USE_VERTEXAI', None)
...
warnings.warn('Warning: Both GOOGLE_GENAI_USE_ENTERPRISE and GOOGLE_GENAI_USE_VERTEXAI '
              'are set with conflicting values. The value of GOOGLE_GENAI_USE_ENTERPRISE '
              'will be used.')
...
if env_enterprise is not None:
    self.vertexai = env_enterprise
elif env_vertexai is not None:
    self.vertexai = env_vertexai
```

<https://github.com/googleapis/python-genai/blob/v2.22.0/google/genai/_api_client.py>

Accepted truthy values are `'true'` and `'1'`, case-insensitive
(`env_str.lower() in ['true', '1']`). Note `TRUE` works; `yes`/`on` do **not**.

### Exact `.env` for the kit

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

The project/location vars are read directly:
```python
env_project  = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
env_location = os.environ.get('GOOGLE_CLOUD_LOCATION', None)
```
and if project is still unset the SDK falls back to the project embedded in ADC
(`credentials, self.project = load_auth(project=None)`).
<https://github.com/googleapis/python-genai/blob/v2.22.0/google/genai/_api_client.py>

Do **not** set `GOOGLE_API_KEY` / `GOOGLE_GENAI_API_KEY` — with `USE_ENTERPRISE` those
switch you to Vertex AI **Express Mode** (API-key auth), which is a different, weaker
setup. <https://github.com/google/adk-docs/blob/main/docs/get-started/google-cloud.md>

### Application Default Credentials

```bash
gcloud auth application-default login
```

> "Authenticate your local workstation using Application Default Credentials (ADC)
> *before* running your ADK agent application."

<https://github.com/google/adk-docs/blob/main/docs/get-started/google-cloud.md>

### API to enable, and IAM role

- **API:** "Google Cloud Project with the **Agent Platform API** (`aiplatform.googleapis.com`) enabled."
  <https://github.com/google/adk-docs/blob/main/docs/get-started/google-cloud.md>
  ```bash
  gcloud services enable aiplatform.googleapis.com
  ```
- **Role:** ADK docs say to grant the service account the **`Agent Platform User`** role.
  The role id is **`roles/aiplatform.user`** (formerly displayed as "Vertex AI User").
  <https://docs.cloud.google.com/iam/docs/roles-permissions/aiplatform> and
  <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/access-control>

### How this differs on Cloud Run

Nothing about the app changes except *where credentials come from*. ADK docs:

> "**Deployed on Google Cloud (Agent Runtime, Cloud Run, GKE):** The environment
> automatically provides the credentials. No key file configuration is necessary."
> "**Running externally:** Generate a service account key file (`.json`) and configure
> the `GOOGLE_APPLICATION_CREDENTIALS` environment variable."

<https://github.com/google/adk-docs/blob/main/docs/get-started/google-cloud.md>

So on Cloud Run: **no `gcloud auth application-default login`, no key file.** ADC
resolves to the revision's runtime service account. You still must set the three env
vars on the service. The ADK Cloud Run doc does exactly that:

```bash
gcloud run deploy $SERVICE_NAME \
  --region $GOOGLE_CLOUD_LOCATION \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_GENAI_USE_ENTERPRISE=$GOOGLE_GENAI_USE_ENTERPRISE"
```

<https://github.com/google/adk-docs/blob/main/docs/deploy/cloud-run.md>

Caveat for the kit: `--region` for Cloud Run and `GOOGLE_CLOUD_LOCATION` for the model
are **not the same thing**. The doc reuses one variable for both, which is fine only
when the model is served from that region. With `gemini-3.5-flash` you want the model
location to be `global` while Cloud Run runs in a real region — so use two variables.

Also, `adk deploy cloud_run` builds via Cloud Build, so the deploying service account
needs `roles/cloudbuild.builds.builder`:
```bash
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="serviceAccount:...-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```
<https://github.com/google/adk-docs/blob/main/docs/deploy/cloud-run.md>

---

## 4. How `adk web` gets an uploaded PDF/image to the model

**Answer: as an inline `Part` with `inline_data`, base64-encoded in the JSON request
body. It does not go through the artifact service by default.**

### Client side (the ADK dev UI, `google/adk-web`)

The file picker has **no `accept` attribute** — no MIME allowlist, no client-side
size cap:

```html
<input type="file" multiple hidden (change)="fileSelect.emit($event)" #fileInput />
```
<https://github.com/google/adk-web/blob/main/src/app/components/chat-panel/chat-panel.component.html>

Each selected file is turned into an inline part, with the MIME type taken straight
from the browser's `File.type`:

```ts
async createMessagePartFromFile(file: File): Promise<any> {
  return {
    inlineData: {
      displayName: file.name,
      data: await this.readFileAsBytes(file),   // base64, from FileReader.readAsDataURL
      mimeType: file.type,
    },
  };
}
```
<https://github.com/google/adk-web/blob/main/src/app/core/services/local-file.service.ts>

### Server side (`google-adk` 2.8.0)

The part lands verbatim in the run request's `new_message`:

```python
class RunAgentRequest(common.BaseModel):
  app_name: Optional[str] = None
  user_id: str
  session_id: str
  new_message: Optional[types.Content] = None
  ...
```
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/cli/api_server.py>

From there it is handed to the model unchanged. **`types.Content` with a
`types.Part(inline_data=types.Blob(mime_type=..., data=...))` is exactly the artifact
representation ADK documents**, so the same bytes work either way:

```python
image_artifact = types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes))
# convenience: types.Part.from_bytes(data=image_bytes, mime_type="image/png")
```
<https://github.com/google/adk-docs/blob/main/docs/artifacts/index.md>

### Does an ArtifactService need configuring? No.

Two independent reasons:

1. **The model sees the bytes inline regardless of any artifact service.** Persisting
   an upload as an artifact is done by an **opt-in** plugin,
   `SaveFilesAsArtifactsPlugin`, which is *not* registered by default by `adk web` /
   `DevServer` / `ApiServer` (only `--extra_plugins` / `plugins.yaml` / `App.plugins`
   add plugins). <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/cli/api_server.py>
2. **`adk web` creates an artifact service for you anyway.** With no
   `--artifact_service_uri` it defaults to per-agent local storage at
   `<agents_root>/<agent>/.adk/artifacts`, falling back to `InMemoryArtifactService`.
   <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/cli/utils/service_factory.py>

If you *do* enable `SaveFilesAsArtifactsPlugin`, note its behaviour and its hard cap:

```python
# Maximum file size for inline_data (20MB as per Gemini API documentation)
_MAX_INLINE_DATA_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
```
It uses `Blob.display_name` as the artifact filename, replaces the file part in the
user message with a text placeholder, and warns + no-ops if no artifact service is set
("Artifact service is not set. SaveFilesAsArtifactsPlugin will not be enabled."). It
also documents that you likely want the `load_artifacts` tool on the agent so the model
can fetch the file back.
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/plugins/save_files_as_artifacts_plugin.py>

### Effective size / MIME limits for the workshop

There is no ADK-side or UI-side MIME filter or size cap on the plain inline path. The
binding limits are the model's (§2): `application/pdf` up to **50 MB** via the API,
3,000 pages; images up to **7 MB** inline. ADK's own inline constant is **20 MB**
(only enforced by the optional artifact plugin). Tell workshop attendees to bring
invoices well under 7 MB and it never matters.

---

## 5. Structured JSON output — and the constraint that is no longer a constraint

### How you declare it

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent

class CapitalOutput(BaseModel):
    capital: str = Field(description="The capital of the country.")

structured_capital_agent = LlmAgent(
    # ... name, model, description
    instruction="""...respond ONLY with a JSON object...""",
    output_schema=CapitalOutput,   # Enforce JSON output
    output_key="found_capital",    # Store result in state['found_capital']
)
```
<https://github.com/google/adk-docs/blob/main/docs/agents/llm-agents.md>

Field declaration in ADK 2.8.0:

```python
output_schema: Optional[SchemaType] = None
"""The output schema when agent replies.

Supports all schema types that the underlying Google GenAI API supports:
  - type[BaseModel]: e.g., MySchema
  - list[type[BaseModel]]: e.g., list[MySchema]
  - list[primitive]: e.g., list[str], list[int]
  - dict: Raw dict schemas
  - Schema: Google's Schema type
"""
```
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/llm_agent.py>

So a Pydantic `BaseModel` is the *typical* form but no longer the only one — `dict`,
`list[BaseModel]`, `list[str]` and `types.Schema` are accepted. Python validates the
response against the Pydantic model, so constraints declared on it (`pattern`,
`minLength`, `minimum`) **are** enforced — unlike Java/Kotlin, which check structure only.
<https://github.com/google/adk-docs/blob/main/docs/agents/llm-agents.md>

`output_key` stores the **parsed dict** (not the text) when `output_schema` is set:
> "When `output_schema` is also set, the *parsed* response is stored instead of the
> text: a `dict` in Python, and a `Map` in Java and Kotlin."

Do **not** set the schema on `generate_content_config` — ADK raises:
> "Response schema must be set via `LlmAgent.output_schema`, not ... schema to
> `LlmAgent(output_schema=...)`."
(and similarly for tools: "All tools must be set via `LlmAgent.tools`, not via
`generate_content_config.tools`.")
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/llm_agent.py>

### The constraint: it was real in 1.x, and it was removed in 1.32.0

I diffed the `output_schema` docstring across tags:

| Tag | Docstring |
|---|---|
| v1.0.0 – **v1.31.0** | "NOTE: when this is set, agent can **ONLY reply and CANNOT use any tools**, such as function tools, RAGs, agent transfer, etc." |
| **v1.32.0** onward, incl. v1.39.1 and **v2.8.0** | "NOTE: The ADK **supports using `output_schema` and `tools` together**. It works by exposing tools during the thought loop and enforcing structure only on the final output." |

Verified by fetching
`https://raw.githubusercontent.com/google/adk-python/<tag>/src/google/adk/agents/llm_agent.py`
for tags v1.0.0, v1.10.0, v1.15.0, v1.20.0, v1.25.0, v1.30.0, v1.31.0, v1.32.0,
v1.33.0, v1.34.0, v1.39.1, v2.8.0 on 2026-09-03. v1.32.0 was released 2026-05-01
(<https://github.com/google/adk-python/releases/tag/v1.32.0>). Compare
<https://github.com/google/adk-python/blob/v1.31.0/src/google/adk/agents/llm_agent.py>
against
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/llm_agent.py>.

**This is the fact most likely to be wrong in copied-from-blog code.** Almost every ADK
tutorial written before May 2026 says "output_schema means no tools," and many designs
work around it with a two-agent split. That workaround is now unnecessary.

### But there IS still a caveat — and on Vertex AI it works in your favour

The current docs carry this warning:

> **Warning: Using `output_schema` with `tools`** — "Using `output_schema` with `tools`
> in the same LLM request is only supported by specific models, including Gemini 3.0.
> For other models, ADK falls back to a `set_model_response` function tool to collect
> the structured output, which may not work reliably. In such cases, consider using
> sub-agents that handle output formatting separately."

<https://github.com/google/adk-docs/blob/main/docs/agents/llm-agents.md>

The implementation is more generous than that warning. The fallback processor bails out
(i.e. **native** schema+tools is used) when the model reports the capability:

```python
if (not agent.output_schema
    or not agent.tools
    or agent.canonical_model.capabilities.output_schema_and_tools
    or getattr(agent, 'mode', None) == 'task'):
  return
```
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/flows/llm_flows/_output_schema_processor.py>

and that capability is computed as:

```python
def gemini_output_schema_and_tools(model_name: str) -> bool:
  return (get_google_llm_variant() == GoogleLLMVariant.VERTEX_AI
          and is_gemini_model(model_name))
```
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/models/_capabilities.py>
(consumed by `Gemini.capabilities` in
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/models/google_llm.py>)

**Reading:** on the **Vertex AI backend** with **any Gemini model**,
`output_schema` + `tools` uses the native path — no `set_model_response` shim, no
reliability caveat. On the Gemini API (AI-Studio key) backend it falls back to the shim.
Note the docs text and the code disagree in scope; the code is the ground truth for 2.8.0.
This is a genuinely strong argument for running the workshop on Vertex AI rather than
an API key: the kit can use tools *and* a schema in one agent.

(If the fallback does engage, ADK appends a `set_model_response` tool plus an
instruction telling the model to finish by calling it.
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/flows/llm_flows/_output_schema_processor.py>)

---

## 6. Defining tools

### Plain functions, not `FunctionTool`

> "Transforming a Python function into a tool is a straightforward way to integrate
> custom logic into your agents. When you assign a function to an agent's `tools` list,
> the framework automatically wraps it as a `FunctionTool`."
>
> "The ADK framework automatically inspects your Python function's signature—including
> its name, docstring, parameters, type hints, and default values—to generate a schema.
> This schema is what the LLM uses to understand the tool's purpose, when to use it, and
> what arguments it requires."

<https://github.com/google/adk-docs/blob/main/docs/tools-custom/function-tools.md>

So: **just pass the function.** `FunctionTool` is the automatic wrapper; you construct it
by hand only when you need to override name/description or use its subclasses
(`LongRunningFunctionTool`, `AgentTool`).

### Docstrings and type hints

- Docstring **is** the tool description sent to the LLM: "The docstring of your function
  serves as the tool's **description** and is sent to the LLM. Therefore, a well-written
  and comprehensive docstring is crucial." Parameter descriptions are taken from the
  docstring's `Args:` section.
- **Required** parameter = has a type hint and **no default value**.
- **Optional** parameter = has a default value, or `typing.Optional[T]` / `T | None`.
  "Use defaults only for values that are truly optional. Do not add defaults for
  information the model should derive from the user request."
- If the LLM omits a required arg, "ADK will return an error to the LLM, prompting it to
  correct the call."

<https://github.com/google/adk-docs/blob/main/docs/tools-custom/function-tools.md>

### Return type convention: a dict

> "The preferred return type for a Function Tool is a **dictionary** in Python... If your
> function returns a type other than a dictionary or map, the framework automatically
> wraps it into a dictionary with a single key named **`result`**."
>
> "As a best practice, include a `status` key in your return dictionary to indicate the
> overall outcome (e.g., `success`, `error`, `pending`)."

<https://github.com/google/adk-docs/blob/main/docs/tools-custom/function-tools.md>

### `ToolContext`

Add a parameter annotated `ToolContext`; ADK injects it and **hides it from the LLM**:

```python
from google.adk.tools import ToolContext

def my_tool(arg1: str, tool_context: ToolContext):
    user_id = tool_context.state.get("user_id")
    # tool_context.actions.transfer_to_agent = "secondary_agent"
```

> "ADK automatically injects the context data before your function runs and ensures this
> parameter is **not visible to the LLM**."
> "By default, the injected parameter is called `tool_context`, but you can name the
> parameter anything you want. ADK detects it by its `ToolContext` **type annotation**
> rather than by name."

It gives access to:
- **`state`** — dict-like session-scoped data (use a `temp:` prefix to pass data between
  tools within one invocation)
- **`actions`** — controls agent behaviour, e.g. `transfer_to_agent`
- **artifact methods** — `load_artifact`, `save_artifact`

<https://github.com/google/adk-docs/blob/main/docs/tools-custom/function-tools.md>

**2.x structural change:** `ToolContext` is now an **alias for
`google.adk.agents.context.Context`** — the standalone 1.x class is gone:

```python
# src/google/adk/tools/tool_context.py, v2.8.0
from ..agents.context import Context
ToolContext = Context
```
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/tools/tool_context.py>

`from google.adk.tools import ToolContext` still works, and `isinstance` checks still
pass, but anything that subclassed the old `ToolContext` or relied on its MRO will break.
The `Context` object exposes considerably more than the docs list, including
`state`, `actions`, `session`, `function_call_id`, `branch`, `custom_metadata`,
`tool_confirmation`, `node`, `node_path`, `run_id`, `attempt_count`, `resume_inputs`,
`error`, `output`, `route`, `interrupt_ids`, and methods
`load_artifact`, `save_artifact`, `get_artifact_version`, `list_artifacts`,
`save_credential`, `load_credential`, `request_credential`, `request_confirmation`,
`search_memory`, `add_memory`, `add_session_to_memory`, `render_ui_widget`, `run_node`.
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/context.py>

### Attaching tools to an agent

```python
agent = LlmAgent(
    name="invoice_agent",
    model="gemini-3.5-flash",
    instruction="...",
    tools=[my_function, another_function],   # plain callables; auto-wrapped
)
```
`tools: list[ToolUnion] = Field(default_factory=list)` — "Tools available to this agent."
<https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/llm_agent.py>

### One remaining "one tool per agent" limitation

Built-in Google Search / Agent Search / Code Execution historically could not be combined
with other tools. For **Search**, this "only applies to ... ADK Python v1.15.0 and lower;
ADK Python release v1.16.0 and higher provides a built-in workaround." Code Execution with
the Gemini API is still listed as exclusive.
<https://github.com/google/adk-docs/blob/main/docs/tools/limitations.md>
Not relevant to this kit (no built-in tools planned), but worth a slide footnote.

---

## 7. What changed 1.x → 2.x, and what will break copied-from-blog code

Primary source for all of this section:
<https://google.github.io/adk-docs/2.0/> (raw:
<https://github.com/google/adk-docs/blob/main/docs/2.0/index.md>)

> "The ADK 2.0 release introduces the **Workflow Runtime**, transitioning ADK from a
> hierarchical agent executor to a **graph-based execution engine**. In this new
> architecture, your Agents, Tools, and Functions are evaluated as individual *nodes*
> within a workflow graph."

Documented Python breaking changes:

1. **Event schema.** New `node_info` and `output` fields on `Event`. Breaks custom
   `BaseSessionService` implementations with rigid SQL columns, and any downstream
   validator using `additionalProperties: false`. (JSON-blob session stores are fine.)
2. **`BaseAgent` now subclasses `BaseNode`.** "Custom overrides of 1.x abstract methods,
   such as `_run_async_impl()` or `generate_content()`, are no longer the correct way to
   drive execution. The Workflow Graph engine completely bypasses these legacy overrides
   ... those calls are **silently ignored**." Move logic to `BeforeAgentCallback` /
   `AfterAgentCallback`.
3. **No manual event appending.** `context.session.events.append(...)` and `enqueue_event`
   are out; you must `yield` the event from the node/agent.
4. **Error handling inverted.** "if you migrate a tool and leave a broad
   `except Exception:` block inside it, this code masks the failure from the framework,
   **permanently disabling the new 2.0 automatic retry mechanisms** for that step."
   Catching `BaseException` also traps `NodeInterruptedError` and breaks human-in-the-loop
   pauses. Let exceptions propagate; configure `RetryConfig(max_attempts=3)`.

Additional breakages I found in the source that the migration page does **not** list for Python:

5. **`SequentialAgent` is deprecated in Python too** (the migration page only says this for
   TypeScript):
   ```python
   @deprecated('SequentialAgent is deprecated in favor of Workflow and will be removed ...')
   ```
   <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/sequential_agent.py>
   `ParallelAgent` and `LoopAgent` carry the same decorator, with an extra caveat:
   > "ParallelAgent is deprecated in favor of Workflow and will be removed in a future
   > version. **Workflow cannot yet be used as an LlmAgent sub-agent.**"

   <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/parallel_agent.py>,
   <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/agents/loop_agent.py>

   So all three workflow agents are deprecated, but the replacement (`Workflow`) cannot
   yet be nested under an `LlmAgent` — meaning the deprecated classes are still the only
   option for some shapes. Every "orchestrate with SequentialAgent" blog post now emits a
   deprecation warning.
6. **`ToolContext` collapsed into `Context`** (see §6).
7. **`AdkWebServer` is deprecated:**
   ```python
   @deprecated("AdkWebServer is deprecated and has been refactored into ApiServer and "
               "DevServer. Use DevServer instead.")
   ```
   <https://github.com/google/adk-python/blob/v2.8.0/src/google/adk/cli/adk_web_server.py>
8. **`output_schema` + `tools` is now allowed** (changed in 1.32.0 — see §5). Blog posts
   telling you to split into two agents are solving a dead problem.
9. **`GOOGLE_GENAI_USE_VERTEXAI` → `GOOGLE_GENAI_USE_ENTERPRISE`** and the whole product is
   rebranded from "Vertex AI" to "Gemini Enterprise Agent Platform" (see §3). Old var still
   works; the docs URLs and console labels have all moved.

Pinning 1.x if you need to: `pip install "google-adk~=1.0"`.
<https://google.github.io/adk-docs/2.0/#install>

### Also note: the docs site moved

`https://google.github.io/adk-docs/...` now **301-redirects to `https://adk.dev/...`**
(observed 2026-09-03 fetching `/agents/llm-agents/`). Both work; use `adk.dev` in kit
handouts. The raw markdown at `github.com/google/adk-docs` is the most stable citation.

---

## UNVERIFIED / needs a hands-on check

1. ~~`ParallelAgent` / `LoopAgent` deprecation~~ — **VERIFIED**, both carry `@deprecated`
   in v2.8.0. Folded into §7.
2. **Whether `gemini-3.5-flash` actually resolves with `GOOGLE_CLOUD_LOCATION=global`
   for a fresh project.** The docs say `global` is supported for Standard PayGo; I could
   not make a live API call. **Needs a hands-on check** — this is the kit's critical path
   and should be smoke-tested against a real project before the workshop.
3. **Whether `us-central1` genuinely fails for `gemini-3.5-flash`.** Inferred from its
   absence in the supported-regions table, not from an observed error. **UNVERIFIED.**
4. **Exact runtime behaviour of `output_schema` + `tools` on Vertex AI.** The code path is
   unambiguous, but I have not observed a real invocation producing schema-conforming JSON
   after a tool call. **Needs a hands-on check** — this underpins the workshop design.
5. **Upload size ceiling in the `adk web` UI end to end.** No client cap and no server cap
   found on the plain inline path, but a large base64 body may hit a FastAPI/uvicorn or
   Cloud Run request-body limit before it reaches the model. **UNVERIFIED** — test with a
   ~10 MB PDF.
6. **Which exact MIME string Chrome reports for a `.pdf`** (`application/pdf` expected)
   and whether the model rejects an empty `file.type` for unusual files. **UNVERIFIED.**
7. **Whether `adk web`'s default per-agent local artifact store writes into the agent
   source dir** (`<agents_root>/<agent>/.adk/artifacts`) in a way that needs `.gitignore`
   in the kit repo. Read from `service_factory.py`; not observed. **Needs a hands-on check.**
8. **`google-genai` version actually resolved by pip** — 2.22.0 satisfies `<3,>=2.19`, but
   dependency resolution with other packages could land elsewhere. Pin it explicitly in
   the kit's `requirements.txt` if reproducibility matters.
9. **A GA "latest"-style alias on Vertex.** I found no `gemini-flash-latest` entry on the
   Agent Platform Google-models page and ADK docs warn it may not work on regional
   endpoints, but I could not find a positive statement that it is unsupported on Vertex.
   **UNVERIFIED** — irrelevant if you pin `gemini-3.5-flash` as recommended.
10. **Whether `docs.cloud.google.com` model spec pages are stable URLs.** The Vertex AI →
    Gemini Enterprise Agent Platform rebrand is clearly mid-flight (both
    `cloud.google.com/vertex-ai/...` and `docs.cloud.google.com/gemini-enterprise-agent-platform/...`
    serve the same pages). Re-check links shortly before the workshop.
