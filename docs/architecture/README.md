# The architecture model

`workspace.dsl` is a [Structurizr](https://structurizr.com) model of the
deployed invoice-analyzer service: what an attendee reaches, and what the
service reaches out to. It covers the deployed half of the workshop only —
`adk web`, the developer UI and the sandbox as a model backend are
deliberately outside it, for the reasons in
[ADR-0005](../adr/0005-the-architecture-model-covers-the-deployed-system-only.md).

Names come from [`CONTEXT.md`](../../CONTEXT.md) at the repo root, spelled
the way the glossary spells them.

## Rendering it

```bash
./scripts/export_diagrams.sh
```

Two steps in two containers: Structurizr exports each view to
PlantUML, then PlantUML renders it to an SVG under `svg/`. Those SVGs are
committed, so a reader on GitHub sees the current model without running
anything.

Docker and python3 are the only dependencies, and both container steps
run with `--network none`. The
Google Cloud theme is vendored here as `google-cloud-theme.json` rather than
referenced by URL, and only the icons the model actually uses are committed
under `icons/`, because the Structurizr parser requires every icon a theme
names to exist beside it. The plain Structurizr PlantUML flavour is used rather than
the C4-PlantUML one, which would fetch its library at render time.

Containers run as the calling user, so nothing root-owned lands in the
working copy.

One thing vendoring does not buy: the icons reach the interactive viewer but
not the committed SVGs. The plain Structurizr PlantUML flavour carries the
theme's colours and drops its icons, and the C4-PlantUML flavour that would
carry them is the one that fetches its library over the network. Every box
therefore names its technology, which is what a reader without an icon needs.

Any other Structurizr subcommand goes through the same script, so the docker
invocation never has to be remembered:

```bash
./scripts/export_diagrams.sh validate
./scripts/export_diagrams.sh inspect -workspace workspace.dsl
```

`inspect` is advisory. It currently reports fifteen relationships with no
technology label, which is deliberate: a component calling a component is a
Python function call, and saying so on every arrow is noise.

## Exploring it

```bash
./scripts/export_diagrams.sh serve
```

Structurizr on <http://localhost:8090>: the same views, with the
elements draggable and the layout yours to fix. Port 8090 because the three
obvious ports are taken during the hour — 8000 is the ADK developer UI under
`adk web`, 8080 is the deployable and the Origin shim in front of it, and
8081 is the second shim, pointed at the sandbox. Ctrl-C stops it.

The viewer writes layout back into `workspace.json` beside the DSL, which is
git-ignored: `workspace.dsl` stays the source of truth.

## The glossary, and not the decision log

[`CONTEXT.md`](../../CONTEXT.md) is attached to the workspace, so a term met
on a diagram can be read in the viewer without opening another file. That is
why both containers see the repo root rather than this directory.

The decision log is deliberately not attached. Structurizr's `!adrs` importer
wants a `## Status` section and a date, and without them it imports every ADR
silently as *Proposed*, dated at the moment of export. Both are false. The
ADRs are not going to grow front matter to please a diagram tool, so each
element names its ADR in its own description instead. Do not attempt the
attachment again without changing the ADRs first.
