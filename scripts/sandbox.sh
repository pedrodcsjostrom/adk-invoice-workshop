#!/usr/bin/env bash
#
# Stand up the fallback sandbox — the safety net for attendees who arrive
# without a working pre-flight.
#
#   scripts/sandbox.sh              create the project, deploy the agent, open it up
#   scripts/sandbox.sh --teardown   shut the whole project down
#
# The sandbox is two things, and #37 is the ticket that pulled them apart:
#
#   1. One Cloud Run service running the finished agent, open to any signed-in
#      Google account, reached with `gcloud run services proxy`. This is what a
#      cold attendee watches during the three cloud blocks they cannot do.
#   2. A plain model backend for an agent running on the attendee's OWN laptop.
#      This is the important one. Everything from 0:05 to 0:18 is cloud-free,
#      so a cold arrival points GOOGLE_CLOUD_PROJECT at this project and does
#      the whole local half of the hour hands-on, in lockstep with the room.
#
# The second affordance needs a NAMED identity on the project policy, which is
# why this script grants an open-join Google Group rather than a wildcard — see
# the note in section 4 for the member types Google refuses and why.
#
# Run it the MORNING OF the workshop, not before, and tear it down the same day.
# The service answers to every Google account on earth, and every invocation
# spends Gemini tokens on Peter's billing account. The repo is public (#27), so
# the project id cannot live in it either: the id is generated with a random
# suffix here, printed once, and belongs on a slide and nowhere else. The group
# address has the same posture and for the same reason, so it is read from the
# environment or from state, never hardcoded here.
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

# The access group (#37). Created ONCE by hand at groups.google.com on Peter's
# account, join policy "anyone on the web can join" so a cold arrival joins
# themselves off a QR code and Peter does no live admin. It outlives every
# sandbox, which is exactly why it is not generated here: the project id is
# regenerated per run, the group is not.
GROUP_FILE="$STATE_DIR/access-group"
GROUP="${SANDBOX_GROUP:-$(cat "$GROUP_FILE" 2>/dev/null || true)}"

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

  # The group does NOT die with the project, and that is the whole hazard. Its
  # binding does — the policy went with the project — but the membership list
  # survives, so the next stand-up would re-grant this workshop's attendees on
  # a fresh project without anyone asking for it. Empty it.
  #
  # This step is manual because a consumer @googlegroups.com group belongs to
  # no Cloud Identity customer, so `gcloud identity groups memberships` cannot
  # reach it. Checked against the real group with the Cloud Identity API on:
  #
  #   ERROR: (gcloud.identity.groups.memberships.list) Invalid value for
  #   [--group-email]: There is no such a group associated with the specified
  #   argument
  #
  # There is no CLI for this; the UI is the API.
  if [[ -n "$GROUP" ]]; then
    warn "NOT DONE FOR YOU — empty the access group, or this workshop's"
    warn "attendees are pre-granted on the next sandbox:"
    printf '\n    https://groups.google.com/g/%s/members\n\n' "${GROUP%@*}"
    printf '    Select all, Remove members. Keep the group and its join policy.\n\n'
  fi
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

# --- 4b. Vertex for agents running on attendee laptops ----------------------
# Wildcards are refused on a PROJECT policy, which is what #13 hit:
#
#   PROJECT_SET_IAM_DISALLOWED_MEMBER_TYPE
#   Policy members must be prefixed of the form '<type>:<value>', where <type>
#   is 'domain', 'group', 'serviceAccount', or 'user'.
#
# Nothing to do with organization policy — it is true on this org-free project.
# allUsers and allAuthenticatedUsers work on a *resource* policy, like the
# Cloud Run service above, and are refused on a *project* policy. But `group`
# is on the allowed list, which is the door the refusal message was holding
# open all along (#37). An open-join group is a named identity that a stranger
# can put themselves inside.
#
# TWO roles, and the second is not optional. roles/aiplatform.user carries 446
# permissions and not one of them is under serviceusage, checked against the
# live role definition. Both `application-default login` and the
# x-goog-user-project header the global endpoint needs (#12) require
# serviceusage.services.use on the quota project, so a group granted only the
# first role gets a 403 at 0:18 — in the middle of the segment this exists to
# protect.
if [[ -z "$GROUP" ]]; then
  warn "No access group. Set SANDBOX_GROUP or write $GROUP_FILE."
  warn "The deployed service still works, but a cold attendee CANNOT run their"
  warn "own agent — which is the one thing #11 says everyone must leave having"
  warn "done. Fallback is per-email, once you have their address:"
  printf '\n    gcloud projects add-iam-policy-binding %s \\\n' "$PROJECT_ID"
  printf '      --member=user:THEIR_EMAIL --role=roles/aiplatform.user\n'
  printf '    gcloud projects add-iam-policy-binding %s \\\n' "$PROJECT_ID"
  printf '      --member=user:THEIR_EMAIL --role=roles/serviceusage.serviceUsageConsumer\n\n'
else
  say "Granting Vertex to the access group"
  for ROLE in roles/aiplatform.user roles/serviceusage.serviceUsageConsumer; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="group:$GROUP" --role="$ROLE" >/dev/null
    ok "$ROLE on group:$GROUP"
  done

  # Membership propagates to IAM on Google's schedule, not on ours. The run of
  # show leans on the thirteen minutes between triage at 0:01 and the first
  # model call at 0:18 absorbing it.
  warn "Group membership takes minutes to reach IAM. Existing members are"
  warn "granted from now; anyone joining during the session waits."
fi

# --- 5. the handout ---------------------------------------------------------
say "The handout — put this on a slide, not in the repo"
cat <<HANDOUT

  Project:  $PROJECT_ID
  Group:    ${GROUP:-<none — cold attendees cannot run their own agent>}

  What a cold arrival does, in this order. No credentials, no project of
  their own. They run the whole local half of the hour on their laptop.

  1. Join the group, FIRST, before the clone — membership needs minutes to
     reach IAM and the clone is what fills them.

  2. Two lines in .env:

       GOOGLE_CLOUD_PROJECT=$PROJECT_ID
       GOOGLE_CLOUD_LOCATION=global

  3. Sign in and point the quota project at the sandbox:

       gcloud auth application-default login
       gcloud auth application-default set-quota-project $PROJECT_ID

  Then clone and do exactly what the room does, from 0:05 to 0:39.

  During the three cloud blocks they have nothing to apply, so that is when
  they watch the deployed service — including the records page, which is the
  one thing the local JSON Lines default cannot show them:

    gcloud run services proxy $SERVICE --region $REGION --project $PROJECT_ID

  The proxy needs one component, a separate package on apt gcloud:

    sudo apt-get install google-cloud-cli-cloud-run-proxy

HANDOUT

warn "Tear it down the same day: scripts/sandbox.sh --teardown"
warn "Teardown deletes the project but cannot empty the group — it prints that"
warn "step for you to do by hand. Do it, or these attendees are pre-granted on"
warn "the next sandbox."
