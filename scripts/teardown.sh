#!/usr/bin/env bash
#
# Tear the workshop down so nothing keeps billing.
#
#   scripts/teardown.sh                   destroy the stack, sweep the residue, verify
#   scripts/teardown.sh --yes             same, no prompts
#   scripts/teardown.sh --delete-project  also shut the whole project down
#
# terraform destroy is not the whole story. Cloud Build stages every source
# upload into a bucket it creates itself, outside Terraform, which a destroy
# therefore leaves behind. This script removes that too, then proves the
# project is empty rather than asserting it.

set -euo pipefail

ASSUME_YES=false
DELETE_PROJECT=false
for arg in "$@"; do
  case "$arg" in
    --yes|-y)         ASSUME_YES=true ;;
    --delete-project) DELETE_PROJECT=true ;;
    -h|--help)        sed -n '3,7p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$REPO_ROOT/infra"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
warn() { printf '  \033[33m! %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mv %s\033[0m\n' "$*"; }

confirm() {
  $ASSUME_YES && return 0
  read -r -p "  $1 [y/N] " reply
  [[ "$reply" == [yY] ]]
}

# --- which project ----------------------------------------------------------
# terraform.tfvars is the source of truth, because it is what the apply used.
# The gcloud config is only a fallback.
PROJECT_ID="${PROJECT_ID:-}"
if [[ -z "$PROJECT_ID" && -f "$INFRA/terraform.tfvars" ]]; then
  PROJECT_ID="$(sed -n 's/^[[:space:]]*project_id[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$INFRA/terraform.tfvars" | head -1)"
fi
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "No project. Set PROJECT_ID, or project_id in infra/terraform.tfvars." >&2
  exit 1
fi

REGION="$(sed -n 's/^[[:space:]]*region[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$INFRA/terraform.tfvars" 2>/dev/null | head -1)"
REGION="${REGION:-europe-west1}"

say "Tearing down $PROJECT_ID (region $REGION)"

# --- 1. the stack -----------------------------------------------------------
say "1. terraform destroy"
if [[ -f "$INFRA/terraform.tfstate" ]]; then
  if $ASSUME_YES; then
    terraform -chdir="$INFRA" destroy -auto-approve
  else
    terraform -chdir="$INFRA" destroy
  fi
  ok "stack destroyed"
else
  warn "no terraform.tfstate in infra/ - nothing Terraform owns, continuing to the sweep"
fi

# --- 2. what Terraform never owned ------------------------------------------
# gcloud builds submit stages source into gs://<project>_cloudbuild, or
# gs://<project>_<region>_cloudbuild under regional bucket behaviour. gcloud
# creates it on the first build, Terraform never sees it, and nothing expires
# the tarballs inside it.
say "2. Cloud Build staging buckets"
for bucket in "gs://${PROJECT_ID}_cloudbuild" "gs://${PROJECT_ID}_${REGION}_cloudbuild"; do
  if gcloud storage buckets describe "$bucket" --project="$PROJECT_ID" >/dev/null 2>&1; then
    if confirm "delete $bucket and everything in it?"; then
      gcloud storage rm --recursive "$bucket" --project="$PROJECT_ID" --quiet
      ok "deleted $bucket"
    else
      warn "kept $bucket - it will keep charging for storage"
    fi
  else
    ok "$bucket does not exist"
  fi
done

# --- 3. prove it ------------------------------------------------------------
# Asserting "destroy leaves nothing behind" is worth less than listing what is
# actually left. Every API here may legitimately be disabled, which is itself
# proof that nothing is running, so a failed call is not an error.
say "3. What is left in the project"
RESIDUE=0
report() { # <label> <newline-separated output>
  if [[ -n "$2" ]]; then
    warn "$1:"
    printf '      %s\n' $2
    RESIDUE=1
  else
    ok "no $1"
  fi
}
report "Cloud Run services" \
  "$(gcloud run services list --project="$PROJECT_ID" --region="$REGION" --format='value(name)' 2>/dev/null || true)"
report "storage buckets" \
  "$(gcloud storage buckets list --project="$PROJECT_ID" --format='value(name)' 2>/dev/null || true)"
report "Artifact Registry repositories" \
  "$(gcloud artifacts repositories list --project="$PROJECT_ID" --format='value(name)' 2>/dev/null || true)"
report "Firestore databases" \
  "$(gcloud firestore databases list --project="$PROJECT_ID" --format='value(name)' 2>/dev/null || true)"
report "workshop service accounts" \
  "$(gcloud iam service-accounts list --project="$PROJECT_ID" --format='value(email)' --filter='email~invoice-agent' 2>/dev/null || true)"

# --- 4. the local side ------------------------------------------------------
say "4. On your laptop"
for path in "$INFRA/terraform.tfstate" "$INFRA/terraform.tfstate.backup" \
            "$REPO_ROOT/invoice_agent/.env" "$REPO_ROOT/.adk"; do
  [[ -e "$path" ]] && warn "still present: ${path#"$REPO_ROOT"/}"
done
echo "      Credentials outlive the workshop. To hand them back:"
echo "        gcloud auth application-default revoke"

# --- 5. the whole project ---------------------------------------------------
if $DELETE_PROJECT; then
  say "5. Shutting the project down"
  echo "  This disconnects billing immediately and starts a 30-day recovery window."
  if confirm "shut down $PROJECT_ID entirely?"; then
    gcloud projects delete "$PROJECT_ID" --quiet
    ok "$PROJECT_ID shut down; restore within 30 days with: gcloud projects undelete $PROJECT_ID"
    exit 0
  fi
  warn "left $PROJECT_ID running"
else
  say "5. The surer option"
  echo "  A project created only for this workshop does not need to survive it."
  echo "  Shutting it down stops billing on everything at once, including anything"
  echo "  this script missed, and is reversible for 30 days:"
  echo "        scripts/teardown.sh --delete-project"
fi

if (( RESIDUE )); then
  say "Something survived. See the list above, or shut the project down."
  exit 1
fi
say "Nothing billable left in $PROJECT_ID."
