#!/usr/bin/env bash
# Renders docs/architecture/workspace.dsl to committed SVGs, and serves the
# interactive viewer.
#
#   scripts/export_diagrams.sh              exports and renders docs/architecture/svg
#   scripts/export_diagrams.sh serve        serves the viewer on http://localhost:8090
#   scripts/export_diagrams.sh validate     parses the workspace and says nothing if it is fine
#
# Anything else is handed to the Structurizr container as its own subcommand,
# so the docker invocation never has to be remembered:
#
#   scripts/export_diagrams.sh inspect -workspace workspace.dsl
#   scripts/export_diagrams.sh export -workspace workspace.dsl -format json -output .
#
# Both steps run entirely offline: the Structurizr theme is vendored beside the
# workspace, and the plain Structurizr PlantUML flavour is used rather than the
# C4-PlantUML one, which would fetch its library at render time.
#
# The repo root is what the containers see, not just docs/architecture: the
# workspace attaches CONTEXT.md as its documentation, from two levels up.
#
# Docker and python3 are the only dependencies. Containers run as the calling
# user so nothing root-owned lands in the working copy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHITECTURE="$ROOT/docs/architecture"
SVG="$ARCHITECTURE/svg"
PUML="$ARCHITECTURE/.puml"

# 8090, because the three obvious ports are all taken during the hour. Which,
# and why, is in docs/architecture/README.md.
PORT=8090

STRUCTURIZR_IMAGE=structurizr/structurizr:latest
PLANTUML_IMAGE=plantuml/plantuml:latest

if [ "${1:-export}" = "serve" ]; then
  echo "Serving the workspace on http://localhost:$PORT — Ctrl-C to stop."
  exec docker run --rm -it \
    -u "$(id -u):$(id -g)" \
    -p "$PORT:8080" \
    -v "$ROOT:/usr/local/structurizr" \
    "$STRUCTURIZR_IMAGE" local docs/architecture
fi

# Both containers see the repo root, run offline, and run as the calling user.
offline() {
  docker run --rm --network none \
    -u "$(id -u):$(id -g)" \
    -v "$ROOT:/work" -w /work/docs/architecture \
    "$@"
}

if [ "${1:-export}" = "validate" ]; then
  offline "$STRUCTURIZR_IMAGE" validate -workspace workspace.dsl
  exit $?
fi

# Any other subcommand goes straight to Structurizr, working directory already
# on the workspace, so `-workspace workspace.dsl` is all the path it needs.
if [ $# -gt 0 ]; then
  offline "$STRUCTURIZR_IMAGE" "$@"
  exit $?
fi

mkdir -p "$SVG" "$PUML"
rm -f "$PUML"/*.puml

# 1. Export each view to a PlantUML source file.
offline "$STRUCTURIZR_IMAGE" export \
  -workspace workspace.dsl \
  -format plantuml/structurizr \
  -output .puml

# The exporter puts the view title and its description on one PlantUML title
# line, which renders as one very wide line of text. Wrap it, keeping each
# wrapped line inside its own size tag: PlantUML does not carry a tag across a
# line break, and an unclosed one is printed as literal text.
python3 - "$PUML" <<'WRAP'
import glob, os, re, sys, textwrap

for path in glob.glob(os.path.join(sys.argv[1], "*.puml")):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()

    def rewrap(match):
        size, text = match.group(1), match.group(2)
        lines = []
        for part in text.split("\\n"):
            lines += textwrap.wrap(re.sub(r"</?size[^>]*>", "", part), 80) or [""]
        return "title " + "\\n".join(f"<size:{size}>{line}</size>" for line in lines)

    source = re.sub(r"title <size:(\d+)>(.*)$", rewrap, source, count=1, flags=re.MULTILINE)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)
WRAP

# The generated diagram keys repeat the styles on every view; the views
# themselves are what gets read.
rm -f "$PUML"/*-key.puml

# Renaming a view would otherwise leave its old SVG behind, committed and
# wrong.
rm -f "$SVG"/*.svg

# 2. Render each one to SVG.
offline "$PLANTUML_IMAGE" -tsvg -nometadata -o "/work/docs/architecture/svg" ".puml/*.puml"

rm -rf "$PUML"

echo "Rendered:"
ls -1 "$SVG"
