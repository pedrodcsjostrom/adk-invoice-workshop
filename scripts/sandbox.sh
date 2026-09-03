#!/usr/bin/env bash
#
# Stand up the fallback sandbox — the safety net for attendees who arrive
# without a working pre-flight.
#
#   scripts/sandbox.sh              create the project, deploy the agent, open it up
#   scripts/sandbox.sh --teardown   shut the whole project down
#
# What the sandbox is: one Cloud Run service running the finished agent, open
# to any signed-in Google account, reached with `gcloud run services proxy`.
# A cold attendee uses Peter's deployed agent. They do not get a project of
# their own, and they cannot run the agent locally — see the note on the grants
# below for why Google makes that impossible, and what it costs the hour.
#
# Run it the MORNING OF the workshop, not before, and tear it down the same day.
# The service answers to every Google account on earth, and every invocation
# spends Gemini tokens on Peter's billing account. The repo is public (#27), so
# the project id cannot live in it either: the id is generated with a random
# suffix here, printed once, and belongs on a slide and nowhere else.
#
# Requires: gcloud authenticated as the account that owns the billing account,
# terraform, and an open billing account. The account must be OUTSIDE any
# organization — inside one, domain restricted sharing blocks the
# allAuthenticatedUsers grants and this script fails at that step (#18).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$REPO_ROOT/infra"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-invoice-agent}"

# State lives outside the repo. It is not committed and it is not the recovery
# path either — teardown deletes the project, which needs no state at all.
STATE_DIR="${SANDBOX_STATE_DIR:-$HOME/.adk-invoice-sandbox}"
STATE="$STATE_DIR/terraform.tfstate"
ID_FILE="$STATE_DIR/project-id"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mv %s\033[0m\n' "$*"; }
warn() { printf '  \033[33m! %s\033[0m\n' "$*"; }

mkdir -p "$STATE_DIR"

# --- teardown ---------------------------------------------------------------
if [[ "${1:-}" == "--teardown" ]]; then
  PROJECT_ID="${SANDBOX_PROJECT:-$(cat "$ID_FILE" 2>/dev/null || true)}"
  if [[ -z "$PROJECT_ID" ]]; then
    echo "No project id. Set SANDBOX_PROJECT, or check $ID_FILE." >&2
    exit 1
  fi
  say "Shutting down $PROJECT_ID"
  # Deleting the project is the whole teardown. terraform destroy is not used
  # here: it would leave the Cloud Build staging bucket behind (#14) and it
  # depends on a state file that a deleted project does not need.
  gcloud projects delete "$PROJECT_ID" --quiet
  rm -f "$STATE" "$ID_FILE"
  ok "Project scheduled for deletion. The open IAM grants die with it."
  warn "Deletion is reversible for 30 days: gcloud projects undelete $PROJECT_ID"
  exit 0
fi

# --- 1. the project ---------------------------------------------------------
# Random suffix, because the id is the only thing standing between a public
# repo and an open Gemini budget.
PROJECT_ID="${SANDBOX_PROJECT:-adk-sandbox-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' \n')}"
# No --limit here. gcloud applies it BEFORE the filter, so --limit=1 takes the
# first account and then filters it out, silently yielding nothing.
BILLING="${BILLING_ACCOUNT:-$(gcloud billing accounts list --filter=open=true --format='value(name)' | head -1)}"
if [[ -z "$BILLING" ]]; then
  echo "No open billing account found. Set BILLING_ACCOUNT." >&2
  exit 1
fi

say "Creating $PROJECT_ID"
gcloud projects create "$PROJECT_ID" --name="ADK Invoice Workshop Sandbox"
echo "$PROJECT_ID" > "$ID_FILE"

# No parent means no organization, which is what keeps the grants below legal.
PARENT="$(gcloud projects describe "$PROJECT_ID" --format='value(parent)')"
if [[ -n "$PARENT" ]]; then
  echo "Project has a parent ($PARENT). It must be created outside any organization (#18)." >&2
  exit 1
fi
ok "Outside any organization"

gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING" >/dev/null
ok "Billing linked to $BILLING"

# --- 2. the APIs ------------------------------------------------------------
# The same eight the pre-flight asks an attendee for (#3).
say "Enabling APIs (about 70 seconds)"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project "$PROJECT_ID"
ok "Eight APIs on"

# --- 3. the stack -----------------------------------------------------------
# Same Terraform every attendee applies, same two-apply shape (#8, #22).
say "Applying the stack"
terraform -chdir="$INFRA" init -input=false >/dev/null
terraform -chdir="$INFRA" apply -auto-approve -input=false \
  -state="$STATE" -var "project_id=$PROJECT_ID" -var "region=$REGION"

IMAGE="$(terraform -chdir="$INFRA" output -state="$STATE" -raw image_repository)/agent:v1"

say "Building the agent image"
gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID" "$REPO_ROOT"

say "Swapping the image in"
terraform -chdir="$INFRA" apply -auto-approve -input=false \
  -state="$STATE" -var "project_id=$PROJECT_ID" -var "region=$REGION" -var "image=$IMAGE"
ok "Agent deployed"

# --- 4. the grants ----------------------------------------------------------
# allAuthenticatedUsers, not named accounts. The fallback attendee is by
# definition the one who skipped pre-flight, so their email is unknown ahead of
# the session and pre-granting by identity is impossible (#18).
say "Opening it to any signed-in Google account"

# Reaching the deployed UI through the proxy. run.viewer is here because the
# proxy resolves the service before it connects; invoker alone is not enough.
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member=allAuthenticatedUsers --role=roles/run.invoker >/dev/null
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member=allAuthenticatedUsers --role=roles/run.viewer >/dev/null
ok "run.invoker + run.viewer on $SERVICE"

# What is NOT granted, because Google does not allow it. Opening Vertex to an
# unknown Google account would need roles/aiplatform.user on the PROJECT, and
# Cloud Resource Manager refuses the member type outright:
#
#   PROJECT_SET_IAM_DISALLOWED_MEMBER_TYPE
#   Policy members must be prefixed of the form '<type>:<value>', where <type>
#   is 'domain', 'group', 'serviceAccount', or 'user'.
#
# This has nothing to do with organization policy — it is true on this org-free
# project. allUsers and allAuthenticatedUsers are accepted on a *resource*
# policy, like the Cloud Run service above, and refused on a *project* policy.
#
# The consequence is a hole this script cannot close. A cold attendee reaches
# the deployed agent, but cannot run `adk web` against this project, so they
# never run an agent of their own — and the hour's one mandatory exercise (#11)
# is watching *your own* agent check the arithmetic twice. Closing it needs a
# named identity: Peter adding each cold arrival by email during the session, or
# a group prepared in advance. That is a decision, not a provisioning step; it
# is left as an open question on #13.

# --- 5. the handout ---------------------------------------------------------
say "The handout — put this on a slide, not in the repo"
cat <<HANDOUT

  Project:  $PROJECT_ID
  Region:   $REGION
  Service:  $SERVICE

  No credentials. Sign in with any Google account, then reach the agent:

    gcloud auth login
    gcloud run services proxy $SERVICE --region $REGION --project $PROJECT_ID

  Open http://localhost:8080 and use the agent there.

  The proxy needs one component, which is a separate package on apt gcloud:

    sudo apt-get install google-cloud-cli-cloud-run-proxy

HANDOUT

warn "Tear it down the same day: scripts/sandbox.sh --teardown"
