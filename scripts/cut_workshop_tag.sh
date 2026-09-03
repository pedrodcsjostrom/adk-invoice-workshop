#!/usr/bin/env bash
#
# Cut the pinned tag the pre-flight and the room both clone.
#
#   scripts/cut_workshop_tag.sh workshop-2026-09-17
#
# Nobody pulls during the hour. A morning-of fix is a NEW tag, announced from
# the front of the room as a re-clone — never a `git pull` into forty working
# copies mid-session. Use a `.1`, `.2` suffix for those: workshop-2026-09-17.1
#
# The tag is what the attendee clones:
#
#   git clone --branch <tag> --depth 1 https://github.com/pedrodcsjostrom/invoice_analysis.git
#
set -euo pipefail

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  echo "usage: scripts/cut_workshop_tag.sh workshop-YYYY-MM-DD[.N]" >&2
  exit 2
fi

if [[ ! "$TAG" =~ ^workshop-[0-9]{4}-[0-9]{2}-[0-9]{2}(\.[0-9]+)?$ ]]; then
  echo "tag must look like workshop-2026-09-17 or workshop-2026-09-17.1" >&2
  exit 2
fi

cd "$(git rev-parse --show-toplevel)"

branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "main" ]]; then
  echo "on '$branch' — cut the tag from main" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty — commit or clean it first" >&2
  exit 1
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "tag $TAG already exists — a fix means the next suffix, never a moved tag" >&2
  exit 1
fi

git fetch --quiet origin
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
  echo "HEAD is not origin/main — push first, so the tag points at what attendees clone" >&2
  exit 1
fi

echo "==> the two gaps are fenced and solutions/ is in step"
uv run pytest -q tests/test_solutions_in_step.py

echo "==> everything except fill-in one's check, which is red by design"
uv run pytest -q --ignore=tests/test_gap_arithmetic.py

echo "==> fill-in one's check is red on a fresh clone, as attendees will find it"
if uv run pytest -q tests/test_gap_arithmetic.py >/dev/null 2>&1; then
  echo "tests/test_gap_arithmetic.py PASSES — the answer is committed, not the gap" >&2
  exit 1
fi

git tag -a "$TAG" -m "Workshop kit pinned for the session: $TAG"
git push origin "$TAG"

cat <<EOF

Cut and pushed: $TAG

Put this in the pre-flight, and read it out to anyone arriving cold:

  git clone --branch $TAG --depth 1 https://github.com/pedrodcsjostrom/invoice_analysis.git
  cd invoice_analysis && uv sync

EOF
