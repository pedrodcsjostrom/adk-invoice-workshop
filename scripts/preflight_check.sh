#!/usr/bin/env bash
#
# Pre-flight verification for the 60-minute ADK invoice-analyzer workshop.
#
#   ./scripts/preflight_check.sh [PROJECT_ID]
#
# Run this the day before, from your clone of the workshop repo, and send the
# whole REPORT block at the end to the workshop host. If it says READY, the
# hour works. If it does not, the report says exactly what to fix.
#
# Read-only, with one exception: it asks Gemini to say "ping", which is the
# only check that proves the whole path the workshop depends on. That costs a
# fraction of a cent.
#
# Exit codes:  0 = ready   1 = fix it yourself   2 = you need a cloud admin
#
# Every check here traces to docs/research/gcp-project-preflight-and-cost.md
# section 10, which records why each one earns its place.

set -uo pipefail

VERSION="1"

# ---------------------------------------------------------------- settings --

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# Defaults are read out of infra/variables.tf where it is available, so this
# script cannot drift from the Terraform the room applies.
tf_default() {
  local name="$1" fallback="$2" value=""
  if [[ -f "$REPO_ROOT/infra/variables.tf" ]]; then
    value=$(awk -v v="variable \"$name\"" '
      $0 ~ v {inblock=1}
      inblock && /default/ {gsub(/.*= *"/,""); gsub(/".*/,""); print; exit}
      inblock && /^}/ {exit}
    ' "$REPO_ROOT/infra/variables.tf")
  fi
  printf '%s' "${value:-$fallback}"
}

REGION="${REGION:-$(tf_default region europe-west1)}"
MODEL="${MODEL:-$(tf_default model gemini-3.5-flash)}"
MODEL_LOCATION="${MODEL_LOCATION:-$(tf_default model_location global)}"
MIN_TERRAFORM="1.5"
MIN_PYTHON="3.10"
API_MARKER="$HOME/.config/adk-workshop/apis-enabled-at"

REQUIRED_APIS=(
  run.googleapis.com
  artifactregistry.googleapis.com
  cloudbuild.googleapis.com
  compute.googleapis.com
  firestore.googleapis.com
  aiplatform.googleapis.com
  iam.googleapis.com
  cloudresourcemanager.googleapis.com
  serviceusage.googleapis.com
)

REQUIRED_PERMISSIONS=(
  resourcemanager.projects.setIamPolicy
  iam.serviceAccounts.create
  iam.serviceAccounts.actAs
  run.services.create
  artifactregistry.repositories.create
  datastore.databases.create
  storage.buckets.create
  serviceusage.services.enable
  serviceusage.services.use
  aiplatform.endpoints.predict
)

ORG_CONSTRAINTS=(
  iam.allowedPolicyMemberDomains
  iam.disableServiceAccountKeyCreation
  iam.managed.disableServiceAccountKeyCreation
  iam.automaticIamGrantsForDefaultServiceAccounts
  gcp.resourceLocations
  run.allowedIngress
  storage.uniformBucketLevelAccess
  storage.publicAccessPrevention
)

# ------------------------------------------------------------- bookkeeping --

BLOCKING=()
ADMIN=()
SOFT=()

section() { printf '\n== %s\n' "$1"; }
pass()    { printf '  PASS  %s\n' "$1"; }
info()    { printf '  ----  %s\n' "$1"; }
note()    { printf '        %s\n' "$1"; }

# fail <one-line summary> [remedy lines...]
fail() {
  local summary="$1"; shift
  printf '  FAIL  %s\n' "$summary"
  local line; for line in "$@"; do note "$line"; done
  BLOCKING+=("$summary")
}

# admin <one-line summary> [explanation lines...]
admin() {
  local summary="$1"; shift
  printf '  ADMIN %s\n' "$summary"
  local line; for line in "$@"; do note "$line"; done
  ADMIN+=("$summary")
}

# warn <one-line summary> [remedy lines...]
warn() {
  local summary="$1"; shift
  printf '  WARN  %s\n' "$summary"
  local line; for line in "$@"; do note "$line"; done
  SOFT+=("$summary")
}

have() { command -v "$1" >/dev/null 2>&1; }

# at_least <have> <want> — true when <have> is >= <want> as a version string
at_least() {
  [[ "$1" == "$2" ]] && return 0
  [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" == "$2" ]]
}

# ------------------------------------------------------------------- start --

printf 'Pre-flight for the ADK invoice-analyzer workshop (script v%s)\n' "$VERSION"
printf 'Repo: %s\n' "$REPO_ROOT"

section "1. Tools on this machine"

GCLOUD_VERSION="not installed"
if ! have gcloud; then
  fail "gcloud is not installed" \
       "Install it: https://docs.cloud.google.com/sdk/docs/install" \
       "Nothing else in this script can run without it."
else
  GCLOUD_VERSION=$(gcloud version 2>/dev/null | awk '/^Google Cloud SDK/{print $NF; exit}')
  if [[ -z "$GCLOUD_VERSION" ]]; then
    GCLOUD_VERSION="unknown"
    warn "gcloud will not report a version" "It is installed, but something is wrong with it."
  elif at_least "$GCLOUD_VERSION" "500.0.0"; then
    pass "gcloud $GCLOUD_VERSION"
  else
    warn "gcloud $GCLOUD_VERSION is old" \
         "Run: gcloud components update   (or update your system package)"
  fi
fi

TERRAFORM_VERSION="not installed"
if ! have terraform; then
  fail "terraform is not installed" \
       "Install it: https://developer.hashicorp.com/terraform/install" \
       "You apply the stack to your own project during the hour."
else
  TERRAFORM_VERSION=$(terraform version -json 2>/dev/null | jq -r '.terraform_version' 2>/dev/null)
  if [[ -z "$TERRAFORM_VERSION" || "$TERRAFORM_VERSION" == "null" ]]; then
    TERRAFORM_VERSION=$(terraform version 2>/dev/null | awk 'NR==1{gsub(/^v/,"",$2); print $2}')
  fi
  if [[ -z "$TERRAFORM_VERSION" ]]; then
    # A version manager with no version selected lands here — the binary is on
    # PATH and does nothing at all.
    TERRAFORM_VERSION="unusable"
    fail "terraform is on your PATH but will not report a version" \
         "It says: $(terraform version 2>&1 | head -1)" \
         "If you use asdf, tfenv or mise, select a version: terraform $MIN_TERRAFORM or newer."
  elif at_least "$TERRAFORM_VERSION" "$MIN_TERRAFORM"; then
    pass "terraform $TERRAFORM_VERSION"
  else
    fail "terraform $TERRAFORM_VERSION is below the $MIN_TERRAFORM this kit needs" \
         "Upgrade: https://developer.hashicorp.com/terraform/install"
  fi
fi

PYTHON_VERSION=""
if have python3; then
  PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)
fi
if [[ -z "$PYTHON_VERSION" ]]; then
  fail "python3 is not installed" "The kit needs Python $MIN_PYTHON or newer."
elif at_least "$PYTHON_VERSION" "$MIN_PYTHON"; then
  pass "python $PYTHON_VERSION"
else
  fail "python $PYTHON_VERSION is below the $MIN_PYTHON this kit needs" \
       "Install a newer Python, or let uv fetch one: uv python install 3.12"
fi

if have uv; then
  pass "uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
  fail "uv is not installed" \
       "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" \
       "uv is how the kit installs its dependencies, in seconds rather than minutes."
fi

if have git; then
  pass "git $(git --version | awk '{print $3}')"
else
  fail "git is not installed"
fi
have jq   || warn "jq is not installed" "Not required, but it makes several messages below sharper."
have curl || fail "curl is not installed" "Two checks in this script call Google APIs directly."

# The single most important item on this list. The service you deploy is
# private, and `gcloud run services proxy` is the only way you reach it — but
# the proxy is a separate component that is NOT part of a stock gcloud.
SDK_ROOT=$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null)
proxy_installed=false
if [[ -n "$SDK_ROOT" && -x "$SDK_ROOT/bin/cloud-run-proxy" ]]; then
  proxy_installed=true
elif gcloud components list --only-local-state --format='value(id)' 2>/dev/null | grep -qx 'cloud-run-proxy'; then
  proxy_installed=true
elif dpkg -s google-cloud-cli-cloud-run-proxy >/dev/null 2>&1; then
  proxy_installed=true
fi

if $proxy_installed; then
  pass "cloud-run-proxy component is installed"
elif ! have gcloud; then
  : # already failed above
elif dpkg -s google-cloud-cli >/dev/null 2>&1; then
  fail "cloud-run-proxy is missing — you could not open your deployed agent" \
       "Your gcloud came from apt, so install the matching package:" \
       "  sudo apt-get install google-cloud-cli-cloud-run-proxy" \
       "Then re-run this script."
elif have snap && snap list google-cloud-cli >/dev/null 2>&1; then
  fail "cloud-run-proxy is missing — you could not open your deployed agent" \
       "Your gcloud came from snap, which cannot add components." \
       "Remove it and install the tarball SDK, then: gcloud components install cloud-run-proxy" \
       "  https://docs.cloud.google.com/sdk/docs/install"
else
  fail "cloud-run-proxy is missing — you could not open your deployed agent" \
       "Run: gcloud components install cloud-run-proxy" \
       "If that says components are managed externally, use your package manager:" \
       "  apt: sudo apt-get install google-cloud-cli-cloud-run-proxy" \
       "  otherwise install the tarball SDK: https://docs.cloud.google.com/sdk/docs/install"
fi

section "2. Credentials"

ACCOUNT=$(gcloud config get-value account 2>/dev/null | tail -1)
[[ "$ACCOUNT" == "(unset)" ]] && ACCOUNT=""
if [[ -n "$ACCOUNT" ]]; then
  pass "signed in as $ACCOUNT"
else
  fail "gcloud is not signed in" "Run: gcloud auth login"
fi

if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  fail "GOOGLE_APPLICATION_CREDENTIALS is set — it silently overrides your login" \
       "It points at: $GOOGLE_APPLICATION_CREDENTIALS" \
       "Unset it in this shell and in your shell profile:  unset GOOGLE_APPLICATION_CREDENTIALS"
else
  pass "GOOGLE_APPLICATION_CREDENTIALS is unset"
fi

# Resolve the project before the credential checks, because the remedy for bad
# credentials is project-specific and the order of the two commands matters.
PROJECT_ID="${1:-${PROJECT_ID:-}}"
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null | tail -1)
  [[ "$PROJECT_ID" == "(unset)" ]] && PROJECT_ID=""
fi

if [[ -z "$PROJECT_ID" ]]; then
  fail "no project selected" \
       "Run: gcloud config set project YOUR_PROJECT_ID" \
       "Then re-run this script. Everything below depends on it."
  PROJECT_ID="(none)"
else
  pass "project is $PROJECT_ID"
fi

ADC_FILE="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud}/application_default_credentials.json"
ADC_TOKEN=""
QUOTA_PROJECT=""
if [[ ! -f "$ADC_FILE" ]]; then
  fail "no application default credentials" \
       "Run these two, in this order — the order is what sets the quota project:" \
       "  gcloud config set project $PROJECT_ID" \
       "  gcloud auth application-default login"
else
  if have jq; then
    QUOTA_PROJECT=$(jq -r '.quota_project_id // ""' "$ADC_FILE" 2>/dev/null)
  else
    QUOTA_PROJECT=$(grep -o '"quota_project_id"[^,]*' "$ADC_FILE" 2>/dev/null | cut -d'"' -f4)
  fi

  if [[ -z "$QUOTA_PROJECT" ]]; then
    fail "your credentials carry no quota project" \
         "This fails at apply time with a 'requires a quota project' error." \
         "Fix it in this order:" \
         "  gcloud config set project $PROJECT_ID" \
         "  gcloud auth application-default login"
  elif [[ "$QUOTA_PROJECT" != "$PROJECT_ID" ]]; then
    warn "credentials bill quota to $QUOTA_PROJECT, not $PROJECT_ID" \
         "Usually harmless, but it is a surprise you do not want tomorrow. To align them:" \
         "  gcloud auth application-default set-quota-project $PROJECT_ID"
  else
    pass "credentials carry the right quota project"
  fi

  ADC_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null)
  if [[ ${#ADC_TOKEN} -gt 50 ]]; then
    pass "credentials are live"
  else
    ADC_TOKEN=""
    fail "your saved credentials no longer work" \
         "Run: gcloud auth application-default login"
  fi
fi

section "3. Project and billing"

PROJECT_STATE=""
PARENT=""
PROJECT_OK=false
if [[ "$PROJECT_ID" != "(none)" ]]; then
  PROJECT_STATE=$(gcloud projects describe "$PROJECT_ID" --format='value(lifecycleState)' 2>/dev/null)
  if [[ "$PROJECT_STATE" == "ACTIVE" ]]; then
    PROJECT_OK=true
    pass "project $PROJECT_ID is active"
  else
    fail "project $PROJECT_ID is not reachable or not active" \
         "Check the id for typos, and that your signed-in account can see it:" \
         "  gcloud projects describe $PROJECT_ID" \
         "Everything below this line is skipped until the project resolves."
  fi
fi

if $PROJECT_OK; then
  PARENT=$(gcloud projects describe "$PROJECT_ID" --format='value(parent.type,parent.id)' 2>/dev/null | tr '\t' ':' | tr -d ' ')
  if [[ -z "$PARENT" || "$PARENT" == ":" ]]; then
    PARENT="none"
    info "project has no organization — no org policy can block you"
  else
    info "project sits under $PARENT — org policies are checked in section 6"
  fi

  BILLING=$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null)
  if [[ "$BILLING" == "True" ]]; then
    pass "billing is linked and enabled"
  elif [[ -z "$BILLING" ]]; then
    fail "cannot read billing for $PROJECT_ID" \
         "Either no billing account is linked, or your account cannot see it." \
         "Link one: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID" \
         "The free trial is ample — the whole hour costs about 20 cents."
  else
    fail "no active billing account on $PROJECT_ID" \
         "Without billing the project cannot use Google Cloud at all, free tier included." \
         "Link one: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
  fi
fi

section "4. Your permissions on the project"

MISSING_PERMS=()
if ! $PROJECT_OK; then
  info "skipped — the project above did not resolve"
elif [[ -n "$ACCOUNT" ]] && have curl; then
  ROLES=$(gcloud projects get-iam-policy "$PROJECT_ID" \
            --flatten='bindings[].members' \
            --filter="bindings.members:user:$ACCOUNT" \
            --format='value(bindings.role)' 2>/dev/null | tr '\n' ' ')
  [[ -n "$ROLES" ]] && info "roles: $ROLES"

  USER_TOKEN=$(gcloud auth print-access-token 2>/dev/null)
  if [[ ${#USER_TOKEN} -gt 50 ]]; then
    payload=$(printf '"%s",' "${REQUIRED_PERMISSIONS[@]}")
    granted=$(curl -s -X POST \
      -H "Authorization: Bearer $USER_TOKEN" \
      -H "Content-Type: application/json" \
      "https://cloudresourcemanager.googleapis.com/v3/projects/${PROJECT_ID}:testIamPermissions" \
      -d "{\"permissions\":[${payload%,}]}" 2>/dev/null)

    for perm in "${REQUIRED_PERMISSIONS[@]}"; do
      grep -q "\"$perm\"" <<<"$granted" || MISSING_PERMS+=("$perm")
    done

    if [[ ${#MISSING_PERMS[@]} -eq 0 ]]; then
      pass "you hold all ${#REQUIRED_PERMISSIONS[@]} permissions the apply needs"
    else
      admin "missing ${#MISSING_PERMS[@]} permission(s): ${MISSING_PERMS[*]}" \
            "Ask whoever owns this project for roles/owner on it, or use a project you created yourself." \
            "iam.serviceAccounts.actAs is the one people most often lack."
    fi
  else
    warn "could not test permissions — no access token"
  fi
fi

section "5. APIs"

ENABLED=""
MISSING_APIS=()
if ! $PROJECT_OK; then
  info "skipped — the project above did not resolve"
else
  ENABLED=$(gcloud services list --enabled --project="$PROJECT_ID" --format='value(config.name)' 2>/dev/null)
  if [[ -z "$ENABLED" ]]; then
    fail "could not list enabled APIs on $PROJECT_ID" \
         "Usually billing, or a permission problem — see the two sections above."
  else
    for api in "${REQUIRED_APIS[@]}"; do
      grep -qx "$api" <<<"$ENABLED" || MISSING_APIS+=("$api")
    done
    if [[ ${#MISSING_APIS[@]} -eq 0 ]]; then
      pass "all ${#REQUIRED_APIS[@]} required APIs are enabled"
    else
      fail "${#MISSING_APIS[@]} API(s) not enabled: ${MISSING_APIS[*]}" \
           "Enable them all in one line, then wait ten minutes:" \
           "  gcloud services enable ${MISSING_APIS[*]} --project=$PROJECT_ID" \
           "  mkdir -p ${API_MARKER%/*} && date +%s > $API_MARKER"
    fi
  fi

  # Enablement is eventually consistent, and worst on a just-created project.
  if [[ -f "$API_MARKER" ]]; then
    then_ts=$(cat "$API_MARKER" 2>/dev/null)
    now_ts=$(date +%s)
    if [[ "$then_ts" =~ ^[0-9]+$ ]]; then
      mins=$(( (now_ts - then_ts) / 60 ))
      if (( mins >= 10 )); then
        pass "APIs were enabled $mins minutes ago"
      else
        warn "APIs were enabled only $mins minute(s) ago" \
             "Enablement takes a few minutes to propagate. Re-run this script in $((10 - mins)) minutes."
      fi
    fi
  elif [[ ${#MISSING_APIS[@]} -eq 0 ]]; then
    info "no record of when the APIs were enabled — if it was in the last ten minutes, re-run this"
  fi

  # The Firestore location is immutable once the database exists.
  DBS=$(gcloud firestore databases list --project="$PROJECT_ID" \
          --format='value(name,locationId)' 2>/dev/null | tr '\t' ' ')
  if [[ -z "$DBS" ]]; then
    pass "no Firestore database yet — Terraform will create it in $REGION"
  else
    info "Firestore already has: $DBS"
    if grep -q '/invoices' <<<"$DBS"; then
      warn "a database named 'invoices' already exists" \
           "Its location cannot be changed. If it is not in $REGION, tell the host before the session."
    fi
  fi
fi

section "6. Organization policies"

if ! $PROJECT_OK; then
  info "skipped — the project above did not resolve"
elif [[ "$PARENT" == "none" || -z "$PARENT" ]]; then
  pass "skipped — this project is not in an organization"
elif ! have gcloud; then
  :
else
  denied=false
  restrictive=()
  for c in "${ORG_CONSTRAINTS[@]}"; do
    out=$(gcloud org-policies describe "$c" --project="$PROJECT_ID" --effective 2>&1)
    if grep -qi 'PERMISSION_DENIED\|does not have permission' <<<"$out"; then
      denied=true
    elif grep -qi 'NOT_FOUND\|not found' <<<"$out"; then
      : # unset means permissive
    elif grep -qi 'enforce: *true\|deniedValues\|allowedValues' <<<"$out"; then
      restrictive+=("$c")
    fi
  done

  if $denied; then
    warn "cannot read org policies on this project" \
         "That itself says you are on a corporate organization. The workshop is designed to survive" \
         "the common restrictions: the deployed service is private and no service account key is" \
         "ever created. Tell the host you are on a corporate account."
  fi

  if [[ ${#restrictive[@]} -eq 0 ]]; then
    pass "no restrictive org policy found"
  else
    for c in "${restrictive[@]}"; do
      case "$c" in
        gcp.resourceLocations)
          admin "gcp.resourceLocations is enforced" \
                "Your org restricts where resources may live. Check that $REGION is allowed;" \
                "if it is not, ask which region is, and tell the host before the session." ;;
        run.allowedIngress)
          admin "run.allowedIngress is enforced" \
                "Your org restricts how Cloud Run services can be reached. The kit deploys a private" \
                "service reached through the proxy, which is the least restrictive case, but confirm" \
                "with your admin that you can create a Cloud Run service at all." ;;
        *)
          info "$c is enforced — expected on a corporate org, and this kit is built for it" ;;
      esac
    done
  fi
fi

section "7. Can this machine actually call Gemini?"

MODEL_OK=false
if [[ -z "$ADC_TOKEN" ]] || ! $PROJECT_OK || ! have curl; then
  fail "skipped the model check — fix the failures above first" \
       "This is the check that matters most. Re-run once the rest is green."
else
  if [[ "$MODEL_LOCATION" == "global" ]]; then
    endpoint="https://aiplatform.googleapis.com"
  else
    endpoint="https://${MODEL_LOCATION}-aiplatform.googleapis.com"
  fi
  url="$endpoint/v1/projects/$PROJECT_ID/locations/$MODEL_LOCATION/publishers/google/models/$MODEL:generateContent"
  body=$(mktemp)
  code=$(curl -s -o "$body" -w '%{http_code}' -X POST \
    -H "Authorization: Bearer $ADC_TOKEN" \
    -H "Content-Type: application/json" \
    -H "x-goog-user-project: $PROJECT_ID" \
    "$url" \
    -d '{"contents":[{"role":"user","parts":[{"text":"ping"}]}],"generationConfig":{"maxOutputTokens":16}}' 2>/dev/null)

  case "$code" in
    200)
      MODEL_OK=true
      pass "$MODEL answered at $MODEL_LOCATION — this is the check that proves the hour works" ;;
    403)
      if grep -qi 'has not been used in project\|is disabled' "$body"; then
        fail "Vertex AI is not enabled, or not propagated yet" \
             "Enable it and wait ten minutes:" \
             "  gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID"
      else
        admin "Vertex AI refused this account (403)" \
              "You can reach the API but are not allowed to call the model." \
              "Ask for roles/aiplatform.user on $PROJECT_ID." \
              "$(head -c 300 "$body")"
      fi ;;
    404)
      fail "$MODEL is not served at $MODEL_LOCATION (404)" \
           "The model endpoint is a separate setting from the infrastructure region." \
           "Leave GOOGLE_CLOUD_LOCATION=global. us-central1 does not serve this model." ;;
    429)
      warn "rate-limited on the first call (429)" \
           "Not a blocker on its own, but mention it to the host." ;;
    *)
      fail "the model call failed with HTTP $code" \
           "$(head -c 300 "$body")" ;;
  esac
  rm -f "$body"
fi

section "8. The workshop kit itself"

KIT_VERSION=""
if [[ ! -f "$REPO_ROOT/invoice_agent/agent.py" ]]; then
  fail "this is not a clone of the workshop repo" \
       "Clone it and run this script from inside:" \
       "  git clone https://github.com/pedrodcsjostrom/adk-invoice-workshop.git" \
       "  cd adk-invoice-workshop && ./scripts/preflight_check.sh"
else
  KIT_VERSION=$(git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null)
  pass "clone is at ${KIT_VERSION:-unknown}"

  if [[ -f "$REPO_ROOT/invoice_agent/.env" ]]; then
    if grep -q '^GOOGLE_CLOUD_PROJECT=.\+' "$REPO_ROOT/invoice_agent/.env" && \
       ! grep -q '^GOOGLE_CLOUD_PROJECT=your-project-id' "$REPO_ROOT/invoice_agent/.env"; then
      pass "invoice_agent/.env names a project"
    else
      fail "invoice_agent/.env still has the placeholder project" \
           "Edit it and set GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    fi
    if grep -q '^GOOGLE_API_KEY=\|^GOOGLE_GENAI_API_KEY=' "$REPO_ROOT/invoice_agent/.env"; then
      fail "invoice_agent/.env sets an API key" \
           "An API key switches the agent off Vertex AI. Delete that line."
    fi
  else
    fail "invoice_agent/.env does not exist" \
         "Run: cp invoice_agent/.env.example invoice_agent/.env" \
         "Then set GOOGLE_CLOUD_PROJECT=$PROJECT_ID in it."
  fi

  if have uv && (cd "$REPO_ROOT" && uv run --no-sync python -c 'import google.adk' >/dev/null 2>&1); then
    pass "dependencies are installed"
  else
    fail "dependencies are not installed" \
         "Run: uv sync" \
         "Do it today. Forty laptops downloading this at once on conference wifi will not work."
  fi

  if [[ -d "$REPO_ROOT/infra/.terraform" ]]; then
    pass "terraform init has been run"
  else
    fail "terraform init has not been run" \
         "Run: terraform -chdir=infra init" \
         "This puts the provider on disk. There is no room in the hour to download it."
  fi

  if [[ -f "$REPO_ROOT/tests/test_gap_arithmetic.py" ]]; then
    if have uv && (cd "$REPO_ROOT" && uv run --no-sync pytest -q tests/test_gap_arithmetic.py >/dev/null 2>&1); then
      info "the arithmetic gap test passes — you have already filled in the first gap"
    else
      pass "the arithmetic gap test fails, which is correct on a fresh clone"
    fi
  fi

  if [[ -e "$REPO_ROOT/invoice_agent/.adk" || -e "$REPO_ROOT/.adk" || -e "$HOME/.adk" ]]; then
    pass "the developer UI has been run at least once here"
  else
    warn "the developer UI has never been run on this machine" \
         "Run it once today and dismiss the telemetry consent dialog it shows:" \
         "  uv run adk web ." \
         "Doing this now means the room does not hit that dialog forty times at once tomorrow."
  fi
fi

# ------------------------------------------------------------------ report --

if   [[ ${#ADMIN[@]}    -gt 0 ]]; then RESULT="NOT READY — needs a cloud admin"; CODE=2
elif [[ ${#BLOCKING[@]} -gt 0 ]]; then RESULT="NOT READY — ${#BLOCKING[@]} thing(s) to fix"; CODE=1
elif [[ ${#SOFT[@]}     -gt 0 ]]; then RESULT="READY — with ${#SOFT[@]} warning(s)"; CODE=0
else                                   RESULT="READY"; CODE=0
fi

printf '\n'
printf '================= PRE-FLIGHT REPORT =================\n'
printf 'RESULT      : %s\n' "$RESULT"
printf 'when        : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'script      : preflight_check.sh v%s\n' "$VERSION"
printf 'kit         : %s\n' "${KIT_VERSION:-not a clone of the kit}"
printf 'account     : %s\n' "${ACCOUNT:-none}"
printf 'project     : %s (state %s, parent %s)\n' "$PROJECT_ID" "${PROJECT_STATE:-unknown}" "${PARENT:-unknown}"
printf 'region      : %s\n' "$REGION"
printf 'model       : %s @ %s  reachable=%s\n' "$MODEL" "$MODEL_LOCATION" "$MODEL_OK"
printf 'gcloud      : %s\n' "$GCLOUD_VERSION"
printf 'terraform   : %s\n' "$TERRAFORM_VERSION"
printf 'python      : %s\n' "${PYTHON_VERSION:-none}"
printf 'os          : %s\n' "$(uname -srm)"

if [[ ${#BLOCKING[@]} -gt 0 ]]; then
  printf 'fix yourself:\n'
  printf '  - %s\n' "${BLOCKING[@]}"
fi
if [[ ${#ADMIN[@]} -gt 0 ]]; then
  printf 'needs an admin:\n'
  printf '  - %s\n' "${ADMIN[@]}"
fi
if [[ ${#SOFT[@]} -gt 0 ]]; then
  printf 'warnings:\n'
  printf '  - %s\n' "${SOFT[@]}"
fi
printf '=====================================================\n'

if [[ $CODE -eq 0 ]]; then
  printf '\nSend the block above to the host. Nothing else to do — see you tomorrow.\n'
else
  printf '\nFix what is listed above, re-run this, and send the block either way.\n'
  printf 'Send it today even if it still fails: that is what the sandbox fallback is for.\n'
fi

exit $CODE
